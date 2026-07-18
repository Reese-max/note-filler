"""Keep the integration exclusion list and its offline coverage map traceable.

The machine-readable audit is the single source for both the eight excluded
test ids and the non-integration tests that cover their deterministic paths.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

_PYTHON = sys.executable
_REPO_ROOT = Path(__file__).resolve().parent.parent
_AUDIT = json.loads(
    (_REPO_ROOT / "tests" / "deselected_allowlist.json").read_text(encoding="utf-8")
)
_EXPECTED_COUNTS = (117, 109, 8)
_EXPECTED_DESELECTED_COUNT = _EXPECTED_COUNTS[2]
ALLOWED_INTEGRATION_TESTS = sorted(item["test_id"] for item in _AUDIT)
MAPPED_NON_INTEGRATION_TESTS = sorted(
    {test_id for item in _AUDIT for test_id in item["substitute_tests"]}
)
_TEST_ID_RE = re.compile(r"^tests/[^:]+::\S+$")
_SOURCE_REF_RE = re.compile(r"^(?P<path>[^:]+):(?P<line>[1-9]\d*)$")


def _assert_source_evidence(source_ref: str, anchor: str) -> None:
    """Ensure an evidence reference still points at the claimed source line."""
    match = _SOURCE_REF_RE.fullmatch(source_ref)
    assert match, f"Invalid source reference: {source_ref!r}"
    relative = Path(match["path"])
    assert not relative.is_absolute() and ".." not in relative.parts, (
        f"Source reference must stay inside repo: {source_ref!r}"
    )
    source = _REPO_ROOT / relative
    assert source.is_file(), f"Missing source evidence file: {source_ref!r}"
    lines = source.read_text(encoding="utf-8").splitlines()
    line_number = int(match["line"])
    assert line_number <= len(lines), f"Source evidence line out of range: {source_ref!r}"
    assert anchor in lines[line_number - 1], (
        f"Source evidence anchor missing at {source_ref}: {anchor!r}"
    )


def _assert_allowlist_evidence() -> None:
    """Validate the code-to-substitute evidence chain for every deselected test."""
    for item in _AUDIT:
        assert item["marker"] == "integration"
        assert item["decision"] == "acceptable_unexecuted"
        assert item["exclusion_reason"].strip()

        exclusion_evidence = item["exclusion_evidence"]
        assert exclusion_evidence, f"Missing exclusion evidence: {item['test_id']}"
        for evidence in exclusion_evidence:
            assert evidence["claim"].strip()
            _assert_source_evidence(evidence["source"], evidence["anchor"])

        substitute_ids = item["substitute_tests"]
        evidence_ids = [evidence["test_id"] for evidence in item["substitute_evidence"]]
        assert evidence_ids == substitute_ids, (
            f"Substitute evidence order mismatch for {item['test_id']}: "
            f"expected {substitute_ids}, got {evidence_ids}"
        )
        for evidence in item["substitute_evidence"]:
            assert evidence["claim"].strip()
            _assert_source_evidence(evidence["source"], evidence["anchor"])


def _collect_tests(*pytest_args: str) -> list[str]:
    """Collect test node ids with the supplied pytest arguments."""
    command = [
        _PYTHON,
        "-X",
        "utf8",
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "--color=no",
        *pytest_args,
    ]
    result = subprocess.run(
        command,
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return sorted(
        line.strip()
        for line in result.stdout.splitlines()
        if _TEST_ID_RE.match(line.strip())
    )


def _run_tests(*test_ids: str) -> set[str]:
    """Run the mapped tests once and return the node ids that passed."""
    command = [
        _PYTHON,
        "-X",
        "utf8",
        "-m",
        "pytest",
        "-vv",
        "--tb=short",
        "--color=no",
        *test_ids,
    ]
    result = subprocess.run(
        command,
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    # 去 ANSI，避免 color-on 時 " PASSED" 字面比對落空（回歸：passed=set()）
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    return {
        line.split(" PASSED", 1)[0].strip()
        for line in plain.splitlines()
        if " PASSED" in line
    }


def test_integration_allowlist_is_stable() -> None:
    """The current default deselection must exactly match the audited eight."""
    all_tests = _collect_tests("-o", "addopts=")
    selected_tests = _collect_tests()
    actual = sorted(set(all_tests) - set(selected_tests))
    counts = (len(all_tests), len(selected_tests), len(actual))
    added = sorted(set(actual) - set(ALLOWED_INTEGRATION_TESTS))
    removed = sorted(set(ALLOWED_INTEGRATION_TESTS) - set(actual))
    assert (
        counts == _EXPECTED_COUNTS
        and actual == ALLOWED_INTEGRATION_TESTS
    ), (
        f"Deselected test allowlist mismatch "
        f"(collected/selected/deselected: expected {_EXPECTED_COUNTS}, "
        f"got {counts}).\n"
        f"  Newly deselected (add to allowlist): {added}\n"
        f"  No longer deselected (remove from allowlist): {removed}"
    )


def test_deselected_details_lists_node_ids_and_reasons() -> None:
    """The opt-in report must expose every deselected node and its filter."""
    command = [
        _PYTHON,
        "-X",
        "utf8",
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "--deselected-details",
    ]
    result = subprocess.run(
        command,
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    detail_lines = {
        line.strip()
        for line in result.stdout.splitlines()
        if line.startswith("tests/") and " | reason: " in line
    }
    expected = {
        f"{test_id} | reason: deselected by -m 'not integration'"
        for test_id in ALLOWED_INTEGRATION_TESTS
    }
    assert detail_lines == expected


def test_substitute_mapping_is_complete_and_collectable() -> None:
    """Every excluded test maps to default tests that pass in one targeted run."""
    _assert_allowlist_evidence()
    unmapped = [item["test_id"] for item in _AUDIT if not item["substitute_tests"]]
    assert not unmapped, f"Integration tests without substitute coverage: {unmapped}"
    assert _collect_tests(*MAPPED_NON_INTEGRATION_TESTS) == MAPPED_NON_INTEGRATION_TESTS

    passed = _run_tests(*MAPPED_NON_INTEGRATION_TESTS)
    assert passed == set(MAPPED_NON_INTEGRATION_TESTS)

    print(f"\nDESELECTED_AUDIT={len(_AUDIT)} MAPPED_TESTS={len(passed)}")
    for index, item in enumerate(_AUDIT, start=1):
        covered = item["substitute_tests"]
        assert item["exclusion_reason"].strip()
        assert item["coverage_gap"].strip()
        assert set(covered) <= passed
        print(f"[{index}/{_EXPECTED_DESELECTED_COUNT}] 未納入: {item['test_id']}")
        print(f"  原因: {item['exclusion_reason']}")
        for exclusion in item["exclusion_evidence"]:
            print(
                f"  程式碼排除證據: {exclusion['source']} "
                f"({exclusion['anchor']}) — {exclusion['claim']}"
            )
        for substitute in item["substitute_evidence"]:
            print(
                f"  覆蓋證據: PASS {substitute['test_id']} "
                f"({substitute['source']}, {substitute['anchor']}) — "
                f"{substitute['claim']}"
            )
        print(f"  整合邊界: {item['coverage_gap']}")
    print("TARGETED_VERIFICATION=PASS")
