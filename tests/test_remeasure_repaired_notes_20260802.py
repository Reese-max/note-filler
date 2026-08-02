"""固定 before／after 封存必須能在不讀版本歷史下重跑。"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "metrics_output/repair_measurement_2026-08-02"
SCRIPT = ROOT / "scripts/remeasure_repaired_notes_20260802.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fixed_snapshots_remeasure_without_version_history():
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT)],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert "MEASUREMENT_COMPLETE notes=5" in completed.stdout
    assert "HEAD^" not in SCRIPT.read_text(encoding="utf-8")
    assert "subprocess" not in SCRIPT.read_text(encoding="utf-8")

    comparison = json.loads((PACKAGE / "comparison.json").read_text(encoding="utf-8"))
    assert comparison["snapshot_mode"] == "fixed_before_after_paths_only"
    assert comparison["note_count"] == len(comparison["notes"]) == 5
    assert comparison["all_conditions_met"] is True
    for note in comparison["notes"]:
        before = ROOT / note["before_artifact_path"]
        after = ROOT / note["after_artifact_path"]
        assert _sha256(before) == note["before_content_hash"]
        assert _sha256(after) == note["after_content_hash"]
        assert _sha256(ROOT / note["source_product_path"]) == note["after_content_hash"]
        assert _sha256(ROOT / note["original_content_path"]) == note["original_content_hash"]
        assert note["traceability_after"] > note["traceability_before"]
        assert note["angles_per_topic_after"] >= note["angles_per_topic_before"]
        assert all(note["gates"].values())
