"""以固定封存的 before／after 成品重跑五筆正式品質量測。"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from note_filler.metrics_pipeline import derive_note_id, scan_output_markdown_baselines


PACKAGE = Path("metrics_output/repair_measurement_2026-08-02")
ORIGINAL = Path("tests/fixtures/real_note.txt")
NOTES = (
    ("output/clean-repro-3x-2026-07-24/run-1/real_note.訂正稿.md", "clean-repro-3x-2026-07-24/run-1/real_note.訂正稿.md"),
    ("output/clean-repro-3x-2026-07-24/run-2/real_note.訂正稿.md", "clean-repro-3x-2026-07-24/run-2/real_note.訂正稿.md"),
    ("output/clean-repro-3x-2026-07-24/run-3/real_note.訂正稿.md", "clean-repro-3x-2026-07-24/run-3/real_note.訂正稿.md"),
    ("output/main-flow-2026-07-24/real_note.訂正稿.md", "main-flow-2026-07-24/real_note.訂正稿.md"),
    ("output/main-flow-2026-07-24T061023Z/real_note.訂正稿.md", "main-flow-2026-07-24T061023Z/real_note.訂正稿.md"),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path) -> str:
    return path.as_posix()


def _scan(snapshot: Path, baseline: Path) -> dict[str, dict]:
    """每次自固定快照重建基線，拒絕沿用舊量測結果。"""
    baseline.unlink(missing_ok=True)
    result = scan_output_markdown_baselines(snapshot, baseline)
    if result.created_count != len(NOTES) or result.scanned_count != len(NOTES):
        raise RuntimeError(f"正式量測筆數錯誤：{snapshot}，{result}")
    records = {
        record["note_id"]: record
        for record in result.records
    }
    if len(records) != len(NOTES):
        raise RuntimeError(f"正式量測 note_id 不完整：{snapshot}")
    return records


def _metric(record: dict, name: str) -> float:
    value = record.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise RuntimeError(f"正式量測缺少 {name}：{record}")
    return float(value)


def main() -> int:
    package = PACKAGE
    before_root = package / "before"
    after_root = package / "after"
    original_hash = _sha256(ORIGINAL)
    before_records = _scan(before_root, package / "before_baseline.jsonl")
    after_records = _scan(after_root, package / "after_baseline.jsonl")
    notes: list[dict] = []

    for source_product, source_artifact in NOTES:
        note_id = derive_note_id(source_artifact)
        before = before_root / source_artifact
        after = after_root / source_artifact
        source = Path(source_product)
        if not before.is_file() or not after.is_file():
            raise RuntimeError(f"固定成品快照不存在：{note_id}")
        if _sha256(source) != _sha256(after):
            raise RuntimeError(f"after 快照未對應目前成品：{note_id}")

        before_record = before_records[note_id]
        after_record = after_records[note_id]
        if before_record["status"] != "calculated" or after_record["status"] != "calculated":
            raise RuntimeError(f"正式量測失敗：{note_id}")
        traceability_before = _metric(before_record, "traceability")
        traceability_after = _metric(after_record, "traceability")
        angles_before = _metric(before_record, "angles_per_topic")
        angles_after = _metric(after_record, "angles_per_topic")
        if traceability_after <= traceability_before:
            raise RuntimeError(f"追溯性未改善：{note_id}")
        if angles_after < angles_before:
            raise RuntimeError(f"每主題角度數下降：{note_id}")

        notes.append({
            "note_id": note_id,
            "source_product_path": source_product,
            "before_artifact_path": _relative(before),
            "after_artifact_path": _relative(after),
            "original_content_path": _relative(ORIGINAL),
            "original_content_hash": original_hash,
            "before_content_hash": _sha256(before),
            "after_content_hash": _sha256(after),
            "before_measurement_time": before_record["timestamp"],
            "after_measurement_time": after_record["timestamp"],
            "traceability_before": traceability_before,
            "traceability_after": traceability_after,
            "angles_per_topic_before": angles_before,
            "angles_per_topic_after": angles_after,
            "gates": {
                "traceability_after_gt_before": True,
                "angles_per_topic_after_gte_before": True,
            },
        })

    report = {
        "schema": "note_filler.repair_measurement_comparison.v2",
        "measurement_engine": "scan_output_markdown_baselines",
        "snapshot_mode": "fixed_before_after_paths_only",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "note_count": len(notes),
        "all_conditions_met": True,
        "notes": notes,
    }
    (package / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    rows = [
        "# 五筆修復筆記正式量測（2026-08-02）",
        "",
        "重跑入口只讀已提交的固定 `before/`、`after/` 成品與佐證；不依賴版本歷史。",
        "",
        "| note_id | traceability | angles_per_topic | before / after |",
        "| --- | --- | --- | --- |",
    ]
    rows.extend(
        f"| `{note['note_id']}` | {note['traceability_before']} → {note['traceability_after']} | "
        f"{note['angles_per_topic_before']} → {note['angles_per_topic_after']} | "
        f"`{note['before_artifact_path']}` / `{note['after_artifact_path']}` |"
        for note in notes
    )
    rows.extend([
        "",
        "完整雜湊、逐筆量測時間與正式基線紀錄見 `comparison.json`、`before_baseline.jsonl`、`after_baseline.jsonl`。",
    ])
    (package / "README.md").write_text(
        "\n".join(rows) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"MEASUREMENT_COMPLETE notes={len(notes)} package={package.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
