"""Acceptance checks for the CI deselected policy gate.

The gate must fail before the regular test run when the default pytest
selection excludes an unapproved node, the count drifts, or exclusion reasons
cannot be attributed to every deselected test.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "validate_deselection_ci.py"
_ALLOWLIST = _REPO_ROOT / "tests" / "deselected_allowlist.json"
_MATRIX = _REPO_ROOT / "docs" / "pytest-audit" / "requirements-test-coverage-2026-07-19.json"


def _run_gate(tmp_path: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(_SCRIPT),
            "--matrix",
            str(_MATRIX),
            "--report",
            str(tmp_path / "deselected-ci-gate.md"),
            *extra_args,
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def _load_allowlist() -> list[dict]:
    return json.loads(_ALLOWLIST.read_text(encoding="utf-8"))


def test_ci_gate_accepts_only_authorized_deselected_nodes_with_reasons(tmp_path: Path) -> None:
    allowlist = _load_allowlist()

    result = _run_gate(tmp_path)
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert f"[gate] total=" in result.stdout
    assert f"deselected={len(allowlist)}" in result.stdout
    assert "[gate] PASS" in result.stdout
    assert "reason=None" not in result.stdout
    for row in allowlist:
        assert row["test_id"] in result.stdout
        assert "reason=deselected by -m 'not integration'" in result.stdout

    report = (tmp_path / "deselected-ci-gate.md").read_text(encoding="utf-8")
    assert f"- 預設 deselected: {len(allowlist)}" in report
    assert "- （無）" in report
    assert "採集原因: unknown" not in report


def test_ci_gate_fails_when_deselected_allowlist_count_is_too_small(tmp_path: Path) -> None:
    allowlist = _load_allowlist()
    bad_allowlist = tmp_path / "deselected_allowlist_missing_one.json"
    bad_allowlist.write_text(
        json.dumps(allowlist[1:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = _run_gate(tmp_path, "--allowlist", str(bad_allowlist))
    combined = result.stdout + result.stderr

    assert result.returncode != 0
    assert "deselected 數量異常" in combined
    assert "未核准 deselected" in combined
    assert allowlist[0]["test_id"] in combined


def test_ci_gate_fails_when_deselected_allowlist_contains_non_deselected_node(tmp_path: Path) -> None:
    allowlist = _load_allowlist()
    unexpected = {
        **allowlist[0],
        "test_id": "tests/test_parse.py::test_parse_segments_basic",
        "exclusion_reason": "測試用：此節點不應出現在預設 deselected 清單",
    }
    bad_allowlist = tmp_path / "deselected_allowlist_extra_node.json"
    bad_allowlist.write_text(
        json.dumps([*allowlist, unexpected], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = _run_gate(tmp_path, "--allowlist", str(bad_allowlist))
    combined = result.stdout + result.stderr

    assert result.returncode != 0
    assert "deselected 數量異常" in combined
    assert "allowlist 中預期 deselected 未出現" in combined
    assert unexpected["test_id"] in combined


def test_ci_gate_fails_when_deselected_reason_changes(tmp_path: Path) -> None:
    allowlist = _load_allowlist()
    modified = [dict(entry) for entry in allowlist]
    modified[0] = {**modified[0], "collection_reason": "deselected by -k 'not test_parse'"}
    bad_allowlist = tmp_path / "deselected_allowlist_reason_changed.json"
    bad_allowlist.write_text(
        json.dumps(modified, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = _run_gate(tmp_path, "--allowlist", str(bad_allowlist))
    combined = result.stdout + result.stderr

    assert result.returncode != 0
    assert "deselected reason 與 allowlist 不符" in combined
    assert modified[0]["test_id"] in combined
