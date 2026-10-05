"""Research replay must track actual source and reject unsafe historical assumptions."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/research_law_snapshot.py"


def test_repaired_replay_has_current_source_and_unknown_corpus_authority():
    proc = subprocess.run([sys.executable, str(SCRIPT), "--expect", "repaired"], cwd=ROOT,
                          capture_output=True, text=True, check=True)
    receipt = json.loads(proc.stdout)
    assert receipt["source_contract"] == "repaired"
    assert receipt["source_repo_sha"] == subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
    ).strip()
    assert receipt["provider_calls"] == receipt["replay_network_requests"] == 0
    changed, control = receipt["results"]
    assert not changed["text_matches_official"] and control["text_matches_official"]
    assert all(r["local_source"]["fetched_date"] is None and r["is_stale_30_days"]
               and r["supplement_confidence"] == "pending_evidence" for r in receipt["results"])


def test_repaired_source_cannot_be_claimed_as_baseline_replay():
    proc = subprocess.run([sys.executable, str(SCRIPT), "--expect", "baseline"], cwd=ROOT,
                          capture_output=True, text=True)
    assert proc.returncode != 0
    assert "Expected baseline, got repaired" in proc.stderr


def test_historical_baseline_receipt_remains_explicitly_historical():
    fixture = json.loads((ROOT / "tests/fixtures/law-currentness/official-comparison.json").read_text())
    historical = json.loads((ROOT / "docs/research/issue-9-law-currentness-receipt.json").read_text())
    assert historical["baseline_repo_sha"] == fixture["repo_sha"]
    assert all(r["supplement_confidence"] == "verified" and not r["is_stale_30_days"]
               for r in historical["results"])
