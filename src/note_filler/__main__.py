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
from .binding_report import build_binding_report, write_binding_report
from .export import to_docx, to_json, to_markdown
from .knowledge.law_lookup import LawLookup
from .llm import GrokClient
from .metrics import calculate_polaris_metrics
from .pipeline import require_non_empty_note_product, run_pipeline
from .retrieve.twinkle import TwinkleClient
from .sidecars import (
    DELIVERY_MANIFEST_NAME,
    binding_report_path,
    delivery_manifest_path,
    may_write_latest_copy,
    migrate_legacy_sidecars,
)
from .task_state import TaskStage, TaskStateManager, build_task_key

logger = logging.getLogger(__name__)

_SUFFIXES = {".txt", ".docx"}

MANIFEST_NAME = DELIVERY_MANIFEST_NAME
TASK_STATE_DIR = Path(os.environ.get("NOTE_FILLER_TASK_STATE", ".task_state"))


def _delivery_status(
    *,
    primary_note_ready: bool = False,
    user_channel_sent: bool = False,
    local_fallback_written: bool = False,
    segment_delivery_details: list[dict] | None = None,
) -> dict:
    """建立固定欄位的機器可讀送達狀態。

    segment_delivery_details 為逐段降級摘要：每筆含 question, confidence,
    has_sources, degraded 三個布林欄位，讓下游可分辨哪些片段是降級補齊
    而非中斷流程。
    """
    result: dict = {
        "primary_note_ready": primary_note_ready,
        "user_channel_sent": user_channel_sent,
        "local_fallback_written": local_fallback_written,
    }
    if segment_delivery_details is not None:
        result["segment_delivery_details"] = segment_delivery_details
    return result


def _build_segment_delivery_details(correction) -> list[dict]:
    """從 CorrectionDoc 建立逐段降級摘要，供 delivery_status 使用。

    每筆記錄：
      - question: 原始段落索引（original）或缺口問題字串（supplement）
      - confidence: verified / pending_evidence
      - has_sources: 是否有引用來源
      - degraded: 是否為降級補齊（pending_evidence 或無來源）
    """
    details: list[dict] = []
    for seg in getattr(correction, "segments", []):
        if seg.type == "original":
            details.append({
                "question": f"paragraph:{getattr(seg, 'anchor_idx', '?')}",
                "confidence": seg.confidence,
                "has_sources": False,
                "degraded": False,
            })
        else:
            has_src = bool(getattr(seg, "sources", None))
            degraded = seg.confidence == "pending_evidence" or not has_src
            details.append({
                "question": getattr(seg, "argument_id", "") or "",
                "confidence": seg.confidence,
                "has_sources": has_src,
                "degraded": degraded,
            })
    return details


def _is_non_empty_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _content_hash_file(path: Path) -> str:
    """回傳檔案內容的全長 sha256；不存在或不可讀時回傳空字串。"""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""


def _check_no_leaked_errors(content: str) -> None:
    """檢查內容是否外洩底層錯誤訊息，若有則拒絕送達。
    
    防止靜默失敗被錯誤訊息污染成品筆記，若內容中出現以下字樣直接視為失敗：
    - traceback
    - provider error
    - connection error
    """
    error_patterns = [
        "traceback",
        "provider error", 
        "connection error",
    ]
    content_lower = content.lower()
    for pattern in error_patterns:
        if pattern in content_lower:
            raise RuntimeError(
                f"成品筆記內容檢測到底層錯誤訊息('{pattern}')，"
                f"拒絕視為送達成功以避免錯誤訊息污染成品"
            )


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
    polaris_metrics: dict[str, Any] | None = None,
) -> Path:
    """寫出成品專屬回執，並更新舊路徑作為最新一筆的相容副本。

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
      - polaris_metrics: 北極星筆記品質指標（可選）
    使用者可透過讀取此 manifest 確認交付已完成,而非只依賴本機檔案存在。
    """
    manifest_path = delivery_manifest_path(output_path)
    legacy_path = output_path.parent / MANIFEST_NAME
    # A pre-upgrade note sharing this directory keeps its own receipt and report
    # before the latest-output copies below are replaced.
    for migrated in migrate_legacy_sidecars(output_path.parent):
        audit_event(
            logger,
            "legacy_sidecar_migrated",
            input_path,
            level=logging.INFO,
            manifest_path=migrated,
            reason="directory-level evidence promoted to its note-owned path",
        )

    content_hash = ""
    if content is not None:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    carried = _carried_forward(manifest_path, output_path, input_path) if status != "delivered" else {}

    status_data = delivery_status or {}
    final_delivery_status = _delivery_status(
        primary_note_ready=bool(
            status_data.get("primary_note_ready", status == "delivered")
        ),
        user_channel_sent=bool(status_data.get("user_channel_sent", False)),
        local_fallback_written=bool(
            status_data.get("local_fallback_written", _is_non_empty_file(output_path))
        ),
        segment_delivery_details=status_data.get("segment_delivery_details"),
    )
    receipt = {
        "output_path": str(output_path),
        "input_path": str(input_path),
        "output_canonical_path": str(output_path.resolve()),
        "input_canonical_path": str(input_path.resolve()),
        "authoritative": True,
        "sidecar_scope": "output",
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_hash": content_hash,
        "format": fmt,
        "supplements": supplements,
        "verified": verified,
        "delivery_status": final_delivery_status,
        # 已持久化 artifact 的內容雜湊：生成成品、來源、傳輸確認
        "output_content_hash": _content_hash_file(output_path),
        "input_content_hash": _content_hash_file(input_path),
        "binding_report_path": (
            str(binding_report_path(output_path)) if status == "delivered" else ""
        ),
        "binding_report_canonical_path": (
            str(binding_report_path(output_path).resolve()) if status == "delivered" else ""
        ),
        "binding_report_content_hash": (
            _content_hash_file(binding_report_path(output_path))
            if status == "delivered" else ""
        ),
        "transmission_confirmation_hash": (
            hashlib.sha256(
                json.dumps(
                    final_delivery_status,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        ),
    }
    if status == "delivered" and not receipt["binding_report_content_hash"]:
        audit_event(
            logger,
            "binding_report_hash_unavailable",
            input_path,
            level=logging.WARNING,
            manifest_path=binding_report_path(output_path),
            reason="binding report exists but could not be hashed; readers fall back to its note-owned path",
        )
    receipt.update(carried)
    if error is not None:
        receipt["error"] = error
    if polaris_metrics is not None:
        receipt["polaris_metrics"] = polaris_metrics

    manifest_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    legacy_receipt = dict(receipt)
    legacy_receipt.update(
        {
            "authoritative": False,
            "sidecar_scope": "directory_latest",
            "sidecar_for_output": str(output_path),
        }
    )
    copy_refreshed = may_write_latest_copy(legacy_path, legacy_receipt)
    replaced_path = (
        manifest_path
        if manifest_path.exists()
        else legacy_path if copy_refreshed else None
    )
    if replaced_path is not None:
        audit_event(
            logger,
            "delivery_receipt_replaced",
            input_path,
            level=logging.INFO,
            manifest_path=replaced_path,
            reason=(
                "receipt for the same output note is being refreshed"
                if replaced_path == manifest_path
                else "legacy latest receipt is being refreshed"
            ),
        )
    if copy_refreshed:
        legacy_path.write_text(
            json.dumps(legacy_receipt, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
    else:
        audit_event(
            logger,
            "delivery_receipt_latest_copy_preserved",
            input_path,
            level=logging.INFO,
            manifest_path=legacy_path,
            reason="another note's delivery is the current latest copy",
        )
    return manifest_path


def _carried_forward(manifest_path: Path, output_path: Path, input_path: Path) -> dict:
    """Keep this note's recorded delivery facts when a later attempt fails.

    A failed re-run of a note that already delivered must not erase its
    recovery history or its binding report identity. The replaced receipt is
    also archived next to it, so the delivered record is never lost.
    """
    try:
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(previous, dict):
        return {}
    recorded_input = previous.get("input_canonical_path") or previous.get("input_path")
    if not isinstance(recorded_input, str) or not recorded_input:
        return {}
    try:
        if Path(recorded_input).resolve() != input_path.resolve():
            return {}
    except OSError:
        return {}
    # Recorded recovery history belongs to the note, not to one attempt, and
    # the metrics of an earlier delivery must not be advertised by a failure.
    carried = {
        key: previous[key]
        for key in ("recovery_attempts", "recovered_at")
        if previous.get(key)
    }
    report = binding_report_path(output_path)
    report_hash = previous.get("binding_report_content_hash")
    if report_hash and _content_hash_file(report) == report_hash:
        carried.update(
            {
                "binding_report_path": str(report),
                "binding_report_canonical_path": str(report.resolve()),
                "binding_report_content_hash": report_hash,
            }
        )
    archive = manifest_path.with_name(f"{manifest_path.name}.prev")
    if not archive.exists():
        try:
            archive.write_bytes(manifest_path.read_bytes())
        except OSError as exc:  # the archive is best effort; the receipt still lands
            audit_event(
                logger,
                "delivery_receipt_archive_failed",
                input_path,
                level=logging.WARNING,
                manifest_path=archive,
                error=str(exc),
            )
    if archive.is_file():
        carried["previous_receipt_archive"] = archive.name
    return carried


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


def _output_for_input(path: Path, dest_dir: Path, fmt: str) -> Path:
    """Keep a prior note's output when two source folders share a filename.

    Ownership comes from the note's own receipt, so it never depends on the
    shared directory-level copy that a later note may legitimately replace. A
    pre-upgrade output keeps its name while the copy still names it; when no
    evidence attributes the name to any note, an existing output is left alone.
    """
    base = dest_dir / f"{path.stem}.訂正稿.{fmt}"
    source_id = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:12]
    alternate = dest_dir / f"{path.stem}.{source_id}.訂正稿.{fmt}"
    resolved_input = path.resolve()

    def records_this_input(receipt: dict, base: Path) -> bool:
        """Whether a receipt was written for this input.

        Legacy receipts recorded the input relative to their own working
        directory, so a relative path is resolved against the receipt's
        directory and the current directory before giving up.
        """
        recorded_input = receipt.get("input_canonical_path") or receipt.get("input_path")
        if not isinstance(recorded_input, str) or not recorded_input:
            return False
        recorded_path = Path(recorded_input)
        if recorded_path.is_absolute():
            try:
                return recorded_path.resolve() == resolved_input
            except OSError:
                return False
        # Legacy receipts recorded the input relative to their own working
        # directory. A bare name can only mean that working directory, while a
        # path with a directory component may point at the output's own
        # directory (a common run shape: cwd = the output directory).
        bases = {Path.cwd()}
        if recorded_path.parent != Path("."):
            bases |= {base, base.parent}
        for candidate_base in bases:
            try:
                if (candidate_base / recorded_path).resolve() == resolved_input:
                    return True
            except OSError:
                continue
        return False

    def read_receipt(receipt_path: Path) -> dict | None:
        if not receipt_path.is_file():
            return None
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return receipt if isinstance(receipt, dict) else None

    def claims_name(candidate: Path) -> str:
        """``this`` / ``other`` / ``unknown`` ownership evidence for a name."""
        receipt = read_receipt(delivery_manifest_path(candidate))
        if receipt is not None:
            return "this" if records_this_input(receipt, candidate.parent) else "other"
        latest = read_receipt(candidate.parent / MANIFEST_NAME)
        if latest is None:
            return "unknown"
        latest_output = latest.get("sidecar_for_output") or latest.get("output_path")
        if not isinstance(latest_output, str) or Path(latest_output).name != candidate.name:
            return "unknown"
        if records_this_input(latest, candidate.parent):
            return "this"
        # The copy alone keeps a name only while that note's own artifacts
        # survive; once they are gone the name is free again.
        return "other" if occupied(candidate) else "unknown"

    def occupied(candidate: Path) -> bool:
        return candidate.exists() or binding_report_path(candidate).exists()

    base_claim = claims_name(base)
    alternate_claim = claims_name(alternate)
    if base_claim == "this":
        return base
    if alternate_claim == "this":
        return alternate
    if base_claim == "unknown" and not occupied(base):
        return base
    # The source-suffixed name belongs to this input alone; an existing file
    # there that no receipt attributes to it is another note's output.
    if alternate_claim == "other" or (alternate_claim == "unknown" and occupied(alternate)):
        raise RuntimeError(f"輸出檔名衝突，拒絕覆寫既有訂正稿: {alternate}")
    return alternate


def process_file(
    path: Path,
    llm,
    twinkle,
    law,
    out_dir: Path | None,
    fmt: str,
    *,
    state_dir: Path | None = None,
    dest: Path | None = None,
) -> dict:
    """跑單檔 pipeline、寫出輸出檔、寫 delivery receipt,回統計 dict。

    交付回執(manifest)寫在輸出檔同目錄,作為可查詢的送達紀錄;
    使用者可讀取 manifest 確認交付狀態,而非只依賴本機檔案存在。
    """
    task_key = build_task_key(str(path))
    task_mgr = TaskStateManager(state_dir or TASK_STATE_DIR)

    # 記錄 generation 階段開始
    task_mgr.start_task(task_key, stage=TaskStage.GENERATION, source_locator=str(path))

    try:
        doc = run_pipeline(str(path), llm, twinkle, law)
    except Exception as exc:
        # 生成例外：持久化失敗，不得吞沒後標成功
        task_mgr.fail(
            task_key,
            stage=TaskStage.GENERATION,
            error_type=type(exc).__name__,
            error_message=str(exc),
            recoverable=False,
        )
        raise

    # 防禦層：即使 pipeline 被 stub，交付前仍硬性要求非空實際筆記
    require_non_empty_note_product(doc, source=path)
    supp = [s for s in doc.segments if s.type == "supplement"]
    ver = sum(1 for s in supp if s.confidence == "verified")

    dest_dir = out_dir if out_dir is not None else path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    # A caller that already planned this note's destination keeps it, so the
    # plan and the executed receipt can never disagree.
    dest = dest if dest is not None else _output_for_input(path, dest_dir, fmt)

    # stdout 的使用者送達內容；DOCX 另以 Markdown 提供可直接閱讀的完整筆記。
    body = json.dumps(to_json(doc), ensure_ascii=False, indent=2) if fmt == "json" else to_markdown(doc)
    if not body.strip():
        task_mgr.fail(
            task_key,
            stage=TaskStage.TRANSMISSION,
            error_type="RuntimeError",
            error_message="訂正稿內容為空",
            recoverable=False,
        )
        raise RuntimeError(f"訂正稿內容為空,拒絕視為送達成功:{path}")
    
    # 防禦層：檢查內容是否外洩底層錯誤訊息（JSON 與 Markdown 都需檢查）
    try:
        _check_no_leaked_errors(body)
    except RuntimeError as exc:
        task_mgr.fail(
            task_key,
            stage=TaskStage.TRANSMISSION,
            error_type="RuntimeError",
            error_message=str(exc),
            recoverable=False,
        )
        raise

    seg_details = _build_segment_delivery_details(doc)
    delivery_status = _delivery_status(
        primary_note_ready=True,
        segment_delivery_details=seg_details,
    )

    if fmt == "docx":
        try:
            to_docx(doc, str(dest))
        except Exception as exc:
            task_mgr.fail(
                task_key,
                stage=TaskStage.TRANSMISSION,
                error_type=type(exc).__name__,
                error_message=f"DOCX write failed: {exc}",
                recoverable=False,
            )
            raise
        # 送達後再驗：空檔不得當成功（digest 已生成但未真正送達）
        if not dest.is_file() or dest.stat().st_size == 0:
            task_mgr.fail(
                task_key,
                stage=TaskStage.TRANSMISSION,
                error_type="RuntimeError",
                error_message=f"DOCX output empty: {dest}",
                recoverable=False,
            )
            raise RuntimeError(f"訂正稿寫出失敗或為空,拒絕視為送達成功:{dest}")
        # DOCX 也需檢查 Markdown 內容是否外洩錯誤
        _check_no_leaked_errors(body)
    else:
        try:
            dest.write_text(body, encoding="utf-8", newline="\n")
        except Exception as exc:
            task_mgr.fail(
                task_key,
                stage=TaskStage.TRANSMISSION,
                error_type=type(exc).__name__,
                error_message=f"file write failed: {exc}",
                recoverable=False,
            )
            raise
    delivery_status["local_fallback_written"] = True

    # 先寫並驗收綁定報告；角度門檻失敗不得留下 delivered 回執。
    write_binding_report(dest, doc)
    
    # 計算北極星品質指標
    binding_report = build_binding_report(doc)
    polaris_metrics = calculate_polaris_metrics(
        binding_report=binding_report,
        delivery_status=delivery_status,
    ).to_dict()

    # 送達後寫 delivery receipt:提供可查詢的交付回執,不只靠本機檔案存在
    write_delivery_receipt(
        dest, path,
        status="delivered",
        content=body if fmt != "docx" else None,
        fmt=fmt,
        supplements=len(supp),
        verified=ver,
        delivery_status=delivery_status,
        polaris_metrics=polaris_metrics,
    )

    # 標記任務成功
    task_mgr.succeed(
        task_key,
        artifact_path=str(dest),
        content=body if fmt != "docx" else "",
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
        planned_dest = None
        try:
            planned_dir = out_dir if out_dir is not None else f.parent
            planned_dest = _output_for_input(f, planned_dir, args.format)
            r = process_file(f, llm, twinkle, law, out_dir, args.format, dest=planned_dest)
            delivery_status = r.setdefault(
                "delivery_status",
                _delivery_status(
                    primary_note_ready=bool(str(r.get("content", "")).strip()),
                    local_fallback_written=_is_non_empty_file(Path(r["output"])),
                ),
            )
            print(r["content"], flush=True)
            delivery_status["user_channel_sent"] = True
            manifest_path = delivery_manifest_path(Path(r["output"]))
            if manifest_path.exists():
                # 重新計算 polaris_metrics（因為 user_channel_sent 狀態已更新）
                polaris_metrics = None
                try:
                    # 嘗試從已存在的 binding_report 重新計算
                    report_path = binding_report_path(Path(r["output"]))
                    if report_path.exists():
                        import json
                        binding_report = json.loads(report_path.read_text(encoding="utf-8"))
                        polaris_metrics = calculate_polaris_metrics(
                            binding_report=binding_report,
                            delivery_status=delivery_status,
                        ).to_dict()
                except Exception:
                    # 若無法重新計算，則不包含 polaris_metrics
                    polaris_metrics = None
                
                write_delivery_receipt(
                    Path(r["output"]), f,
                    status="delivered",
                    content=r["content"] if args.format != "docx" else None,
                    fmt=args.format,
                    supplements=r["supplements"],
                    verified=r["verified"],
                    delivery_status=delivery_status,
                    polaris_metrics=polaris_metrics,
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
            try:
                dest = planned_dest or _output_for_input(f, dest_dir, args.format)
            except RuntimeError as collision:
                # Both candidate names belong to other notes, so no receipt can
                # be written for this input without destroying their evidence.
                audit_event(
                    logger,
                    "delivery_receipt_not_written_name_collision",
                    f,
                    level=logging.ERROR,
                    error_type=type(collision).__name__,
                    error=str(collision),
                    reason="every candidate output name is owned by another note",
                )
                print(f"❌ {f}:失敗回執無法安全定位:{collision}", file=sys.stderr)
                continue
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
                # 失敗時不計算 polaris_metrics（因為可能沒有完整的 binding_report）
                write_delivery_receipt(
                    dest, f,
                    status="failed",
                    content=None,
                    fmt=args.format,
                    supplements=0,
                    verified=0,
                    error=f"{type(e).__name__}: {e}",
                    delivery_status=delivery_status,
                    polaris_metrics=None,
                )
            except Exception as receipt_error:  # 回執持久化失敗不得吞掉或中斷後續檔案
                audit_event(
                    logger,
                    "delivery_receipt_persist_failed",
                    f,
                    level=logging.ERROR,
                    manifest_path=delivery_manifest_path(dest),
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
