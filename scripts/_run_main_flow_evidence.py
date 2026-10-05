"""Run the main flow pipeline once and collect evidence artifacts."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

os.chdir(r"D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2ece58c4")
sys.path.insert(0, "src")

from note_filler.__main__ import MANIFEST_NAME, process_file, write_delivery_receipt
from note_filler.knowledge.law_lookup import LawLookup
from note_filler.llm import GrokClient
from note_filler.pipeline import require_non_empty_note_product, run_pipeline
from note_filler.retrieve.twinkle import TwinkleClient
from note_filler.sidecars import resolve_delivery_manifest_path


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    out_dir = Path("output") / f"main-flow-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path("tests/fixtures/real_note.txt")
    db_path = Path("data/law_index.db")

    llm = GrokClient()
    twinkle = TwinkleClient(token=os.environ.get("TWINKLE_HUB_TOKEN", ""))
    law = LawLookup(str(db_path))

    start = datetime.now(timezone.utc)
    print(f"START: {start.isoformat()}")
    print(f"INPUT: {input_path}")
    print(f"OUTPUT_DIR: {out_dir}")
    print(f"DB: {db_path} (exists={db_path.exists()})")

    result = None
    error = None
    tb_str = None

    try:
        result = process_file(input_path, llm, twinkle, law, out_dir, "md")
        print(f"SUCCESS: {json.dumps(result, ensure_ascii=False)}")
    except Exception as e:
        error = e
        tb_str = traceback.format_exc()
        print(f"ERROR: {type(e).__name__}: {e}")
        print(tb_str, file=sys.stderr)

    end = datetime.now(timezone.utc)
    print(f"END: {end.isoformat()}")
    print(f"DURATION: {(end - start).total_seconds():.1f}s")

    # Verify artifacts
    print("\n=== ARTIFACT VERIFICATION ===")
    md_files = list(out_dir.glob("*.md"))
    # Verify the receipt of the note this run produced, not whichever output
    # happens to sort first; the directory-level manifest is only a
    # latest-output convenience copy (see docs/batch-sidecars.md).
    produced_output = Path(result["output"]) if result and result.get("output") else None
    manifest_path = (
        resolve_delivery_manifest_path(produced_output)
        if produced_output is not None
        else out_dir / MANIFEST_NAME
    )

    for f in out_dir.iterdir():
        print(f"  {f.name} ({f.stat().st_size} bytes)")

    note_product = None
    content = ""
    stripped = ""
    content_hash = ""
    if md_files:
        note_product = md_files[0]
        content = note_product.read_text(encoding="utf-8")
        stripped = content.strip()
        print(f"\n  NOTE_PRODUCT: {note_product.name}")
        print(f"  SIZE: {len(content)} chars / {note_product.stat().st_size} bytes")
        print(f"  NON_EMPTY: {bool(stripped)}")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        print(f"  HASH_16: {content_hash}")
    else:
        print("\n  NOTE_PRODUCT: MISSING")

    manifest_data = None
    if manifest_path.exists():
        manifest_raw = manifest_path.read_text(encoding="utf-8")
        manifest_data = json.loads(manifest_raw)
        print(f"\n  MANIFEST: {manifest_path.name}")
        print(f"  STATUS: {manifest_data.get('status')}")
        print(f"  CONTENT_HASH: {manifest_data.get('content_hash')}")
        print(f"  SUPPLEMENTS: {manifest_data.get('supplements')}")
        print(f"  VERIFIED: {manifest_data.get('verified')}")
    else:
        print(f"\n  MANIFEST: NOT FOUND at {manifest_path}")

    # Write run-meta
    meta = {
        "timestamp_start": start.isoformat(),
        "timestamp_end": end.isoformat(),
        "duration_seconds": round((end - start).total_seconds(), 1),
        "input": str(input_path),
        "output_dir": str(out_dir),
        "db": str(db_path),
        "format": "md",
        "exit_code": 0 if result else 1,
        "error": str(error) if error else None,
        "note_product_file": str(note_product) if note_product else None,
        "note_product_size": note_product.stat().st_size if note_product else 0,
        "note_product_hash": content_hash,
        "manifest_exists": manifest_path.exists(),
        "manifest_status": manifest_data.get("status") if manifest_data else None,
        "supplements": manifest_data.get("supplements") if manifest_data else 0,
        "verified": manifest_data.get("verified") if manifest_data else 0,
        "command": f"python -X utf8 -m note_filler tests/fixtures/real_note.txt -o {out_dir} --db data/law_index.db --format md",
    }
    meta_path = out_dir / "run-meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  RUN_META: {meta_path}")

    # Write verification.json
    errors_list = []
    if not md_files:
        errors_list.append("note_product_missing")
    elif not stripped if note_product else True:
        errors_list.append("note_product_empty")
    if not manifest_path.exists():
        errors_list.append("manifest_missing")
    elif manifest_data and manifest_data.get("status") != "delivered":
        errors_list.append(f"manifest_status={manifest_data.get('status')}")
    if manifest_data and manifest_data.get("content_hash") != content_hash:
        errors_list.append("hash_mismatch")

    verification = {
        "ok": len(errors_list) == 0,
        "errors": errors_list,
        "note_product_exists": bool(md_files),
        "note_product_non_empty": bool(stripped if note_product else False),
        "manifest_exists": manifest_path.exists(),
        "manifest_delivered": manifest_data.get("status") == "delivered" if manifest_data else False,
        "hash_match": manifest_data.get("content_hash") == content_hash if manifest_data else False,
    }
    ver_path = out_dir / "verification.json"
    ver_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  VERIFICATION: {ver_path}")
    print(f"  VERIFICATION_OK: {verification['ok']}")
    if errors_list:
        print(f"  VERIFICATION_ERRORS: {errors_list}")

    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
