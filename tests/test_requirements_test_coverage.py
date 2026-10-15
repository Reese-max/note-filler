"""守住 8 個原始 deselected 測試與最小補測的等價覆蓋。"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
from validate_deselection_ci import _parse_node_ids  # noqa: E402

_MATRIX = _REPO / "docs" / "pytest-audit" / "requirements-test-coverage-2026-07-19.json"
_PATH_AUDIT = (
    _REPO
    / "docs"
    / "pytest-audit"
    / "deselected-correctness-path-equivalence-2026-07-21.json"
)
_ALLOWLIST = _REPO / "tests" / "deselected_allowlist.json"
_SUPPLEMENTAL_INTEGRATION_IDS = {
    "tests/test_domain.py::test_detect_domain_real_grok_representative_domains",
    "tests/test_export.py::test_conflicting_arguments_final_product_reading_links_are_open",
    "tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix",
    "tests/test_write.py::test_write_supplement_real_grok_grounded_output",
}


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
            "--collection-record-json",
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
    return set(_parse_node_ids(result.stdout))


def test_coverage_matrix_classifies_all_eight_and_has_no_missing_requirement() -> None:
    matrix = _load(_MATRIX)
    path_audit = _load(_PATH_AUDIT)
    allowlist = _load(_ALLOWLIST)
    assert isinstance(matrix, dict)
    assert isinstance(allowlist, list)

    assert isinstance(path_audit, dict)
    assert path_audit["schema"] == (
        "note-filler.deselected-correctness-path-equivalence/v1"
    )
    audited = path_audit["tests"]
    assert len(audited) == 8
    audited_ids = {row["node_id"] for row in audited}
    allowlist_ids = {row["test_id"] for row in allowlist}
    assert audited_ids <= allowlist_ids
    assert allowlist_ids - audited_ids == _SUPPLEMENTAL_INTEGRATION_IDS
    paths = [path for row in audited for path in row["paths"]]
    assert len(paths) == len({path["id"] for path in paths}) == 23
    statuses = {
        "equivalent_coverage": 23,
        "regression_protection_insufficient": 0,
        "not_covered": 0,
    }
    assert {
        status: sum(path["status"] == status for path in paths)
        for status in statuses
    } == statuses
    assert path_audit["summary"] == {
        "target_tests": 8,
        "correctness_paths": 23,
        **statuses,
        "targets_without_singleton_or_uncovered_path": [
            "tests/test_domain.py::test_detect_domain_real_grok_returns_law",
            "tests/test_e2e_acceptance.py::test_e2e_acceptance_real",
            "tests/test_gap.py::test_detect_gaps_real_grok",
            "tests/test_llm.py::test_grok_pong_integration",
            "tests/test_pipeline.py::test_run_pipeline_real_grok",
            "tests/test_questions.py::test_generate_questions_real_grok",
            "tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke",
            "tests/test_twinkle.py::test_search_real_twinkle_hub",
        ],
    }
    for path in paths:
        points = path["coverage_points"]
        if path["status"] == "equivalent_coverage":
            assert len(points) >= 2
        elif path["status"] == "regression_protection_insufficient":
            assert len(points) == 1
            assert path["status_label"] == "回歸保護不足"
            assert path["minimal_test_location"]
            assert path["minimal_test_change"]
        else:
            assert points == []
            assert path["status_label"] == "未覆蓋"
            assert path["minimal_test_location"]
            assert path["minimal_test_change"]

    allowlist_by_id = {row["test_id"]: row for row in allowlist}
    rows = matrix["tests"]
    assert len(rows) == 8
    assert {row["node_id"] for row in rows} <= set(allowlist_by_id)
    assert matrix["missing_requirements"] == []
    assert matrix["summary"] == {
        "excluded_tests": 8,
        "classified_tests": 8,
        "requirements": 14,
        "requirements_covered_by_default": 14,
        "requirements_missing": 0,
        "equivalent_coverage_complete": True,
        "verification_design_gaps_explicitly_tracked": 1,
    }

    requirements = {row["id"]: row for row in matrix["requirements"]}
    assert len(requirements) == 14
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
    path_audit = _load(_PATH_AUDIT)
    allowlist_ids = {row["test_id"] for row in _load(_ALLOWLIST)}
    default_ids = _default_collected_ids()
    all_ids = default_ids | allowlist_ids

    expected = matrix["default_gate"]["expected_collection"]
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

    for row in path_audit["tests"]:
        assert set(row["same_group_siblings"]) <= all_ids
        for path in row["paths"]:
            assert set(path["coverage_points"]) <= all_ids
            assert set(path["equivalent_default_tests"]) <= default_ids
