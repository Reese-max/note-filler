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
ALLOWED_INTEGRATION_TESTS = sorted(item["test_id"] for item in _AUDIT)
MAPPED_NON_INTEGRATION_TESTS = sorted(
    {test_id for item in _AUDIT for test_id in item["substitute_tests"]}
)
_TEST_ID_RE = re.compile(r"^tests/[^:]+::\S+$")


def _collect_tests(marker: str, test_ids: list[str] | None = None) -> list[str]:
    """Collect matching test ids, optionally limited to an explicit mapping."""
    command = [
        _PYTHON,
        "-X",
        "utf8",
        "-m",
        "pytest",
        "--collect-only",
        "-m",
        marker,
        "-q",
    ]
    if test_ids:
        command.extend(test_ids)
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
    """The integration-marked set must exactly match the audited list."""
    actual = _collect_tests("integration")
    added = sorted(set(actual) - set(ALLOWED_INTEGRATION_TESTS))
    removed = sorted(set(ALLOWED_INTEGRATION_TESTS) - set(actual))
    assert actual == ALLOWED_INTEGRATION_TESTS, (
        f"Integration test allowlist mismatch "
        f"(expected {len(ALLOWED_INTEGRATION_TESTS)}, got {len(actual)}).\n"
        f"  Newly marked integration (add to allowlist): {added}\n"
        f"  No longer integration (remove from allowlist): {removed}"
    )


def test_substitute_mapping_is_complete_and_collectable() -> None:
    """Every excluded test maps to existing tests in the default test set."""
    unmapped = [item["test_id"] for item in _AUDIT if not item["substitute_tests"]]
    assert not unmapped, f"Integration tests without substitute coverage: {unmapped}"
    assert _collect_tests(
        "not integration", MAPPED_NON_INTEGRATION_TESTS
    ) == MAPPED_NON_INTEGRATION_TESTS
