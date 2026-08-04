"""第3棒：驗證 2026-08-04 修復筆記量測產物存在且欄位完整。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "metrics_output" / "repair_measurement_2026-08-04"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_comparison_json_exists_and_valid():
    comparison_path = PACKAGE / "comparison.json"
    assert comparison_path.is_file(), f"comparison.json 不存在: {comparison_path}"
    data = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert data["schema"] == "note_filler.repair_measurement_comparison.v2"
    assert data["note_count"] >= 2
    assert data["all_conditions_met"] is True
    for note in data["notes"]:
        assert "note_id" in note
        assert "traceability_before" in note
        assert "traceability_after" in note
        assert "angles_per_topic_before" in note
        assert "angles_per_topic_after" in note
        assert "before_artifact_path" in note
        assert "after_artifact_path" in note
        assert "original_content_hash" in note
        assert "before_measurement_time" in note
        assert "after_measurement_time" in note
        assert note["traceability_after"] > note["traceability_before"]
        assert note["angles_per_topic_after"] >= note["angles_per_topic_before"]
        assert note["gates"]["traceability_after_gt_before"] is True
        assert note["gates"]["angles_per_topic_after_gte_before"] is True


def test_artifact_files_exist():
    comparison_path = PACKAGE / "comparison.json"
    data = json.loads(comparison_path.read_text(encoding="utf-8"))
    for note in data["notes"]:
        before_path = ROOT / note["before_artifact_path"]
        after_path = ROOT / note["after_artifact_path"]
        assert before_path.is_file(), f"before 檔案不存在: {before_path}"
        assert after_path.is_file(), f"after 檔案不存在: {after_path}"
        assert _sha256(before_path) == note["before_content_hash"]
        assert _sha256(after_path) == note["after_content_hash"]


def test_after_matches_source_product():
    comparison_path = PACKAGE / "comparison.json"
    data = json.loads(comparison_path.read_text(encoding="utf-8"))
    for note in data["notes"]:
        source_path = ROOT / note["source_product_path"]
        after_path = ROOT / note["after_artifact_path"]
        assert source_path.is_file(), f"source 不存在: {source_path}"
        assert _sha256(source_path) == note["after_content_hash"]


def test_baseline_files_exist():
    assert (PACKAGE / "before_baseline.jsonl").is_file()
    assert (PACKAGE / "after_baseline.jsonl").is_file()
    assert (PACKAGE / "README.md").is_file()
