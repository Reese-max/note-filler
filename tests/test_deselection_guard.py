"""Deselection guard — ensures the integration-test allowlist stays stable.

Runs ``pytest --collect-only -m integration -q`` to list every test marked
``integration`` (i.e. the ones deselected by the default ``-m "not integration"``),
then compares the collected set against a pinned allowlist.  Fails if any
test is added to / removed from / reclassified out of the ``integration``
marker set.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# ── pinned allowlist (sorted for determinism) ──────────────────────────
ALLOWED_INTEGRATION_TESTS: list[str] = sorted(
    [
        "tests/test_domain.py::test_detect_domain_real_grok_returns_law",
        "tests/test_e2e_acceptance.py::test_e2e_acceptance_real",
        "tests/test_gap.py::test_detect_gaps_real_grok",
        "tests/test_llm.py::test_grok_pong_integration",
        "tests/test_pipeline.py::test_run_pipeline_real_grok",
        "tests/test_questions.py::test_generate_questions_real_grok",
        "tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke",
        "tests/test_twinkle.py::test_search_real_twinkle_hub",
    ],
)

_PYTHON = sys.executable
_REPO_ROOT = Path(__file__).resolve().parent.parent
# Matches lines like  tests/test_foo.py::test_bar  (optionally with [param])
_TEST_ID_RE = re.compile(r"^tests/[^:]+::\S+$")


def _collect_integration_tests() -> list[str]:
    """Run ``pytest --collect-only -m integration -q`` and return the sorted
    list of collected test ids."""
    result = subprocess.run(
        [
            _PYTHON,
            "-X",
            "utf8",
            "-m",
            "pytest",
            "--collect-only",
            "-m",
            "integration",
            "-q",
        ],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    tests: list[str] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if _TEST_ID_RE.match(stripped):
            tests.append(stripped)
    return sorted(tests)


def test_integration_allowlist_is_stable() -> None:
    """The set of integration-marked tests must match the allowlist exactly.

    If this fails it means a test was added with ``@pytest.mark.integration``,
    removed, or moved to / from the integration category.  Update the allowlist
    only after confirming the change is intentional.
    """
    actual = _collect_integration_tests()
    added = sorted(set(actual) - set(ALLOWED_INTEGRATION_TESTS))
    removed = sorted(set(ALLOWED_INTEGRATION_TESTS) - set(actual))
    assert not added and not removed, (
        f"Integration test allowlist mismatch "
        f"(expected {len(ALLOWED_INTEGRATION_TESTS)}, got {len(actual)}).\n"
        f"  Newly marked integration (add to allowlist): {added}\n"
        f"  No longer integration (remove from allowlist): {removed}"
    )
