"""筆記補齊 CLI:讀 .txt/.docx 筆記 → 產訂正稿。

用法:
    python -m note_filler <筆記檔或資料夾> [...] [-o 輸出夾] [--db 法條DB] [--format md|json]

真實接線:grok(127.0.0.1:8318)+ twinkle-hub(TWINKLE_HUB_TOKEN)+ 本地法條 DB。
token 缺省時 twinkle 降級為空結果,法條 Level A 仍可用。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .audit import audit_event
from .binding_report import write_binding_report
from .export import to_docx, to_json, to_markdown
from .knowledge.law_lookup import LawLookup
from .llm import GrokClient
from .pipeline import require_non_empty_note_product, run_pipeline
from .retrieve.twinkle import TwinkleClient

logger = logging.getLogger(__name__)

_SUFFIXES = {".txt", ".docx"}

MANIFEST_NAME = "delivery_manifest.json"


def _delivery_status(
    *,
    primary_note_ready: bool = False,
    user_channel_sent: bool = False,
    local_fallback_written: bool = False,
) -> dict[str, bool]:
    """建立固定欄位的機器可讀送達狀態。"""
    return {
        "primary_note_ready": primary_note_ready,
        "user_channel_sent": user_channel_sent,
        "local_fallback_written": local_fallback_written,
    }


def _is_non_empty_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def write_delivery_receipt(
    output_path: Path,
    input_path: Path,
    *,
    status: str = "delivered",
    content: str | None = None,
    fmt: str = "md",
    supplements: int = 0,
    verified: int = 0,
    error: str | None = None,
    delivery_status: dict[str, bool] | None = None,
) -> Path:
    """寫出 delivery_manifest.json,作為可查詢的交付回執。

    回傳 manifest 路徑。manifest 記錄:
      - output_path: 輸出檔路徑
      - input_path: 輸入筆記路徑
      - status: delivered / failed
      - timestamp: ISO 8601 UTC
      - content_hash: 輸出內容 sha256 前 16 碼
      - format: 輸出格式
      - supplements / verified: 計數
      - error: 失敗時的錯誤訊息(僅 status=failed)
      - delivery_status: 成品就緒、使用者通道、本機後援三個布林狀態
    使用者可透過讀取此 manifest 確認交付已完成,而非只依賴本機檔案存在。
    """
    manifest_dir = output_path.parent
    manifest_path = manifest_dir / MANIFEST_NAME

    if manifest_path.exists():
        audit_event(
            logger,
            "delivery_receipt_replaced",
            input_path,
            level=logging.INFO,
            manifest_path=manifest_path,
            reason="output directory keeps the latest delivery receipt",
        )

    content_hash = ""
    if content is not None:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    status_data = delivery_status or {}
    receipt = {
        "output_path": str(output_path),
        "input_path": str(input_path),
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_hash": content_hash,
        "format": fmt,
        "supplements": supplements,
        "verified": verified,
        "delivery_status": _delivery_status(
            primary_note_ready=bool(
                status_data.get("primary_note_ready", status == "delivered")
            ),
            user_channel_sent=bool(status_data.get("user_channel_sent", False)),
            local_fallback_written=bool(
                status_data.get("local_fallback_written", _is_non_empty_file(output_path))
            ),
        ),
    }
    if error is not None:
        receipt["error"] = error

    manifest_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return manifest_path


def _iter_inputs(paths: list[str]) -> list[Path]:
    """把檔案/資料夾參數展開成去重、排序後的 .txt/.docx 檔清單。

    資料夾 → 遞迴收其下所有 .txt/.docx。單檔不論副檔名都保留(交由 parse 報錯)。
    """
    out: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        cands = sorted(q for q in p.rglob("*") if q.suffix.lower() in _SUFFIXES) if p.is_dir() else [p]
        if p.is_dir() and not cands:
            audit_event(
                logger,
                "input_directory_skipped",
                p,
                reason="no supported note files",
            )
        for q in cands:
            rp = q.resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(q)
            else:
                audit_event(
                    logger,
                    "input_file_deduplicated",
                    rp,
                    level=logging.INFO,
                    reason="same resolved path already queued",
                )
    return out


def process_file(path: Path, llm, twinkle, law, out_dir: Path | None, fmt: str) -> dict:
    """跑單檔 pipeline、寫出輸出檔、寫 delivery receipt,回統計 dict。

    交付回執(manifest)寫在輸出檔同目錄,作為可查詢的送達紀錄;
    使用者可讀取 manifest 確認交付狀態,而非只依賴本機檔案存在。
    """
    doc = run_pipeline(str(path), llm, twinkle, law)
    # 防禦層：即使 pipeline 被 stub，交付前仍硬性要求非空實際筆記
    require_non_empty_note_product(doc, source=path)
    supp = [s for s in doc.segments if s.type == "supplement"]
    ver = sum(1 for s in supp if s.confidence == "verified")

    dest_dir = out_dir if out_dir is not None else path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{path.stem}.訂正稿.{fmt}"

    # stdout 的使用者送達內容；DOCX 另以 Markdown 提供可直接閱讀的完整筆記。
    body = json.dumps(to_json(doc), ensure_ascii=False, indent=2) if fmt == "json" else to_markdown(doc)
    if not body.strip():
        raise RuntimeError(f"訂正稿內容為空,拒絕視為送達成功:{path}")
    delivery_status = _delivery_status(primary_note_ready=True)

    if fmt == "docx":
        to_docx(doc, str(dest))
        # 送達後再驗：空檔不得當成功（digest 已生成但未真正送達）
        if not dest.is_file() or dest.stat().st_size == 0:
            raise RuntimeError(f"訂正稿寫出失敗或為空,拒絕視為送達成功:{dest}")
    else:
        dest.write_text(body, encoding="utf-8", newline="\n")
    delivery_status["local_fallback_written"] = True

    # 先寫並驗收綁定報告；角度門檻失敗不得留下 delivered 回執。
    write_binding_report(dest, doc)

    # 送達後寫 delivery receipt:提供可查詢的交付回執,不只靠本機檔案存在
    write_delivery_receipt(
        dest, path,
        status="delivered",
        content=body if fmt != "docx" else None,
        fmt=fmt,
        supplements=len(supp),
        verified=ver,
        delivery_status=delivery_status,
    )
    return {
        "input": str(path),
        "output": str(dest),
        "content": body,
        "supplements": len(supp),
        "verified": ver,
        "delivery_status": delivery_status,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="note_filler", description="讀筆記,AI 補齊知識缺口並附一手來源,產訂正稿。")
    ap.add_argument("inputs", nargs="+", help=".txt/.docx 筆記檔,或含這些檔的資料夾(可多個)")
    ap.add_argument("-o", "--outdir", default=None, help="輸出夾(預設寫在各輸入檔旁)")
    ap.add_argument("--db", default="data/law_index.db", help="法條索引 DB 路徑(預設 data/law_index.db)")
    ap.add_argument("--format", choices=["md", "json", "docx"], default="md", help="輸出格式(預設 md)")
    ap.add_argument("--token", default=os.environ.get("TWINKLE_HUB_TOKEN", ""), help="twinkle-hub token(預設讀環境變數)")
    args = ap.parse_args(argv)

    files = _iter_inputs(args.inputs)
    if not files:
        print("找不到任何 .txt/.docx 筆記檔。", file=sys.stderr)
        return 2
    if not args.token:
        print("警告:未提供 TWINKLE_HUB_TOKEN,twinkle 立法院來源(Level B)將降級為空;法條 Level A 仍可用。", file=sys.stderr)
    if not Path(args.db).exists():
        print(f"警告:法條 DB 不存在({args.db}),法條 Level A 來源將查無結果。", file=sys.stderr)

    llm = GrokClient()
    twinkle = TwinkleClient(token=args.token)
    law = LawLookup(args.db)
    out_dir = Path(args.outdir) if args.outdir else None

    ok = 0
    for f in files:
        r = None
        try:
            r = process_file(f, llm, twinkle, law, out_dir, args.format)
            delivery_status = r.setdefault(
                "delivery_status",
                _delivery_status(
                    primary_note_ready=bool(str(r.get("content", "")).strip()),
                    local_fallback_written=_is_non_empty_file(Path(r["output"])),
                ),
            )
            print(r["content"], flush=True)
            delivery_status["user_channel_sent"] = True
            manifest_path = Path(r["output"]).parent / MANIFEST_NAME
            if manifest_path.exists():
                write_delivery_receipt(
                    Path(r["output"]), f,
                    status="delivered",
                    content=r["content"] if args.format != "docx" else None,
                    fmt=args.format,
                    supplements=r["supplements"],
                    verified=r["verified"],
                    delivery_status=delivery_status,
                )
            ok += 1
            print(
                f"✅ {r['input']} → {r['output']}(補充 {r['supplements']}、verified {r['verified']})",
                file=sys.stderr,
            )
        except Exception as e:  # 單檔失敗不拖垮整批
            audit_event(
                logger,
                "file_processing_failed",
                f,
                level=logging.ERROR,
                error_type=type(e).__name__,
                error=str(e),
            )
            print(f"❌ {f}:{type(e).__name__}: {e}", file=sys.stderr)
            # 寫 delivery_manifest 失敗回執,讓下游可查詢交付狀態
            dest_dir = out_dir if out_dir is not None else f.parent
            dest = dest_dir / f"{f.stem}.訂正稿.{args.format}"
            if r is not None and isinstance(r.get("delivery_status"), dict):
                delivery_status = r["delivery_status"]
            else:
                local_fallback_written = _is_non_empty_file(dest)
                delivery_status = _delivery_status(
                    primary_note_ready=local_fallback_written,
                    local_fallback_written=local_fallback_written,
                )
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                write_delivery_receipt(
                    dest, f,
                    status="failed",
                    content=None,
                    fmt=args.format,
                    supplements=0,
                    verified=0,
                    error=f"{type(e).__name__}: {e}",
                    delivery_status=delivery_status,
                )
            except Exception as receipt_error:  # 回執持久化失敗不得吞掉或中斷後續檔案
                audit_event(
                    logger,
                    "delivery_receipt_persist_failed",
                    f,
                    level=logging.ERROR,
                    manifest_path=dest.parent / MANIFEST_NAME,
                    error_type=type(receipt_error).__name__,
                    error=str(receipt_error),
                )
                print(
                    f"❌ {f}:失敗回執寫入失敗:{type(receipt_error).__name__}: {receipt_error}",
                    file=sys.stderr,
                )

    print(f"完成 {ok}/{len(files)} 檔。", file=sys.stderr)
    return 0 if ok == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
