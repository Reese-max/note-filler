"""筆記補齊 CLI:讀 .txt/.docx 筆記 → 產訂正稿。

用法:
    python -m note_filler <筆記檔或資料夾> [...] [-o 輸出夾] [--db 法條DB] [--format md|json]

真實接線:grok(127.0.0.1:8318)+ twinkle-hub(TWINKLE_HUB_TOKEN)+ 本地法條 DB。
token 缺省時 twinkle 降級為空結果,法條 Level A 仍可用。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .export import to_docx, to_json, to_markdown
from .knowledge.law_lookup import LawLookup
from .llm import GrokClient
from .pipeline import run_pipeline
from .retrieve.twinkle import TwinkleClient

_SUFFIXES = {".txt", ".docx"}


def _iter_inputs(paths: list[str]) -> list[Path]:
    """把檔案/資料夾參數展開成去重、排序後的 .txt/.docx 檔清單。

    資料夾 → 遞迴收其下所有 .txt/.docx。單檔不論副檔名都保留(交由 parse 報錯)。
    """
    out: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        cands = sorted(q for q in p.rglob("*") if q.suffix.lower() in _SUFFIXES) if p.is_dir() else [p]
        for q in cands:
            rp = q.resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(q)
    return out


def process_file(path: Path, llm, twinkle, law, out_dir: Path | None, fmt: str) -> dict:
    """跑單檔 pipeline、寫出輸出檔,回統計 dict。"""
    doc = run_pipeline(str(path), llm, twinkle, law)
    supp = [s for s in doc.segments if s.type == "supplement"]
    ver = sum(1 for s in supp if s.confidence == "verified")

    dest_dir = out_dir if out_dir is not None else path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{path.stem}.訂正稿.{fmt}"
    if fmt == "docx":
        to_docx(doc, str(dest))
    else:
        body = json.dumps(to_json(doc), ensure_ascii=False, indent=2) if fmt == "json" else to_markdown(doc)
        dest.write_text(body, encoding="utf-8", newline="\n")
    return {"input": str(path), "output": str(dest), "supplements": len(supp), "verified": ver}


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
        try:
            r = process_file(f, llm, twinkle, law, out_dir, args.format)
            ok += 1
            print(f"✅ {r['input']} → {r['output']}(補充 {r['supplements']}、verified {r['verified']})")
        except Exception as e:  # 單檔失敗不拖垮整批
            print(f"❌ {f}:{type(e).__name__}: {e}", file=sys.stderr)

    print(f"完成 {ok}/{len(files)} 檔。")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
