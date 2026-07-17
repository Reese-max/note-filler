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
_EXPECTED_DESELECTED_COUNT = 8
ALLOWED_INTEGRATION_TESTS = sorted(item["test_id"] for item in _AUDIT)
MAPPED_NON_INTEGRATION_TESTS = sorted(
    {test_id for item in _AUDIT for test_id in item["substitute_tests"]}
)
_TEST_ID_RE = re.compile(r"^tests/[^:]+::\S+$")


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


def test_integration_allowlist_is_stable() -> None:
    """The current default deselection must exactly match the audited eight."""
    all_tests = _collect_tests("-o", "addopts=")
    selected_tests = _collect_tests()
    actual = sorted(set(all_tests) - set(selected_tests))
    added = sorted(set(actual) - set(ALLOWED_INTEGRATION_TESTS))
    removed = sorted(set(ALLOWED_INTEGRATION_TESTS) - set(actual))
    assert (
        len(actual) == _EXPECTED_DESELECTED_COUNT
        and actual == ALLOWED_INTEGRATION_TESTS
    ), (
        f"Deselected test allowlist mismatch "
        f"(expected {_EXPECTED_DESELECTED_COUNT}, got {len(actual)}).\n"
        f"  Newly deselected (add to allowlist): {added}\n"
        f"  No longer deselected (remove from allowlist): {removed}"
    )


def test_substitute_mapping_is_complete_and_collectable() -> None:
    """Every excluded test maps to existing tests in the default test set."""
    unmapped = [item["test_id"] for item in _AUDIT if not item["substitute_tests"]]
    assert not unmapped, f"Integration tests without substitute coverage: {unmapped}"
    assert _collect_tests(*MAPPED_NON_INTEGRATION_TESTS) == MAPPED_NON_INTEGRATION_TESTS
