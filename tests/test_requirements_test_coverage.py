"""守住 8 個 deselected 測試的需求分類與預設等價覆蓋。"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


_REPO = Path(__file__).resolve().parents[1]
_MATRIX = _REPO / "docs" / "pytest-audit" / "requirements-test-coverage-2026-07-19.json"
_ALLOWLIST = _REPO / "tests" / "deselected_allowlist.json"
_NODE_ID_RE = re.compile(r"^tests/[^:]+::\S+$")


def _load(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_collected_ids() -> set[str]:
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--color=no",
        ],
        cwd=_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return {
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if _NODE_ID_RE.fullmatch(line.strip().replace("\\", "/"))
    }


def test_coverage_matrix_classifies_all_eight_and_has_no_missing_requirement() -> None:
    matrix = _load(_MATRIX)
    allowlist = _load(_ALLOWLIST)
    assert isinstance(matrix, dict)
    assert isinstance(allowlist, list)

    allowlist_by_id = {row["test_id"]: row for row in allowlist}
    rows = matrix["tests"]
    assert len(rows) == 8
    assert {row["node_id"] for row in rows} == set(allowlist_by_id)
    assert matrix["missing_requirements"] == []
    assert matrix["summary"] == {
        "excluded_tests": 8,
        "classified_tests": 8,
        "requirements": 13,
        "requirements_covered_by_default": 13,
        "requirements_missing": 0,
        "equivalent_coverage_complete": True,
        "verification_design_gaps_explicitly_tracked": 1,
    }

    requirements = {row["id"]: row for row in matrix["requirements"]}
    assert len(requirements) == 13
    assert all(row["status"] == "covered_by_default" for row in requirements.values())

    for row in rows:
        assert row["function_area"].strip()
        assert row["covered_function"].strip()
        assert row["critical_path"] in {path["id"] for path in matrix["paths"]}
        assert row["security_risk"] in {"高", "中", "低"}
        assert row["risk_basis"].strip()
        assert row["requirements"]
        assert set(row["requirements"]) <= set(requirements)
        assert row["equivalent_default_tests"]
        assert not set(row["equivalent_default_tests"]) & set(
            row["verification_gap_tests"]
        )
        assert set(allowlist_by_id[row["node_id"]]["substitute_tests"]) <= (
            set(row["equivalent_default_tests"]) | set(row["verification_gap_tests"])
        )

    for requirement in requirements.values():
        assert requirement["covered_by"]
        assert requirement["critical_path"] in {path["id"] for path in matrix["paths"]}


def test_default_gate_collects_every_equivalent_and_safety_regression() -> None:
    matrix = _load(_MATRIX)
    allowlist_ids = {row["test_id"] for row in _load(_ALLOWLIST)}
    default_ids = _default_collected_ids()

    expected = matrix["default_gate"]["expected_collection"]
    assert len(default_ids) == expected["default_selected"]
    assert len(allowlist_ids) == expected["deselected"]
    assert not default_ids & allowlist_ids

    all_default_requirements = set()
    for row in matrix["tests"]:
        equivalents = set(row["equivalent_default_tests"])
        gap_controls = set(row["verification_gap_tests"])
        assert equivalents <= default_ids, (
            f"等價測試未進預設集合：{row['node_id']} -> "
            f"{sorted(equivalents - default_ids)}"
        )
        assert gap_controls <= default_ids
        all_default_requirements.update(row["requirements"])

    for requirement in matrix["requirements"]:
        covered_by = set(requirement["covered_by"])
        assert covered_by <= default_ids, (
            f"需求未由預設測試覆蓋：{requirement['id']} -> "
            f"{sorted(covered_by - default_ids)}"
        )
        assert requirement["id"] in all_default_requirements
