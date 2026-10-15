"""Acceptance checks for the CI deselected anti-leak policy gate.

The gate must fail before the regular test run when:
- an unapproved node is deselected
- the deselected count drifts from the allowlist (single source of truth)
- an allowlisted test disappears from collection
- a substitute coverage test is missing or not selected under the default suite
- the CI workflow no longer mounts jobs that run substitute coverage
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "validate_deselection_ci.py"
_ALLOWLIST = _REPO_ROOT / "tests" / "deselected_allowlist.json"
_MATRIX = _REPO_ROOT / "docs" / "pytest-audit" / "requirements-test-coverage-2026-07-19.json"
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"

# Import pure evaluators for unit-level failure semantics without re-collecting.
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
from validate_deselection_ci import (  # noqa: E402
    _parse_node_ids,
    _parse_deselected_details,
    _run_collect,
    evaluate_deselection_policy,
    validate_workflow_coverage_jobs,
)


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


def _base_ids_from_allowlist(allowlist: list[dict]) -> tuple[list[str], list[str], dict[str, str]]:
    """Build a synthetic collection that matches allowlist deselection."""
    deselected = [row["test_id"] for row in allowlist]
    selected: list[str] = []
    for row in allowlist:
        for sub in row.get("substitute_tests") or []:
            if sub not in selected and sub not in deselected:
                selected.append(sub)
    # Ensure at least one non-related selected node exists for swap tests
    anchor = "tests/test_parse.py::test_parse_txt_splits_on_blank_lines"
    if anchor not in selected:
        selected.append(anchor)
    all_ids = sorted(set(deselected) | set(selected))
    details = {
        node_id: row.get("collection_reason", "deselected by -m 'not integration'")
        for row in allowlist
        for node_id in [row["test_id"]]
    }
    return all_ids, selected, details


def test_ci_gate_accepts_only_authorized_deselected_nodes_with_reasons(tmp_path: Path) -> None:
    allowlist = _load_allowlist()

    result = _run_gate(tmp_path)
    combined = result.stdout + result.stderr

    assert result.returncode == 0, combined
    assert "[gate] total=" in result.stdout
    assert f"deselected={len(allowlist)}" in result.stdout
    assert f"expected={len(allowlist)}" in result.stdout
    assert "[gate] PASS" in result.stdout
    assert "reason=None" not in result.stdout
    assert "substitute_coverage:" in result.stdout
    for row in allowlist:
        assert row["test_id"] in result.stdout
        assert "reason=deselected by -m 'not integration'" in result.stdout

    report = (tmp_path / "deselected-ci-gate.md").read_text(encoding="utf-8")
    assert f"- 預設 deselected: {len(allowlist)}" in report
    assert f"- allowlist/預期數量: {len(allowlist)}" in report
    assert "- （無）" in report
    assert "採集原因: unknown" not in report


def test_ci_gate_fails_when_deselected_count_differs_from_allowlist(tmp_path: Path) -> None:
    allowlist = _load_allowlist()
    short_allowlist = allowlist[:-1]
    bad_allowlist = tmp_path / "deselected_allowlist_missing_one.json"
    bad_allowlist.write_text(
        json.dumps(short_allowlist, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = _run_gate(tmp_path, "--allowlist", str(bad_allowlist))
    combined = result.stdout + result.stderr

    assert result.returncode != 0
    assert (
        f"deselected 數量異常：實際 {len(allowlist)}，"
        f"allowlist/預期 {len(short_allowlist)}"
    ) in combined
    assert "未核准 deselected" in combined
    assert allowlist[-1]["test_id"] in combined


def test_ci_gate_fails_when_deselected_allowlist_contains_non_deselected_node(
    tmp_path: Path,
) -> None:
    allowlist = _load_allowlist()
    removed = allowlist[0]
    # 必須是真實存在、且預設 selected 的 node，才能驗證「回到 selected」分支
    selected_but_not_deselected = (
        "tests/test_parse.py::test_parse_txt_splits_on_blank_lines"
    )
    unexpected = {
        **removed,
        "test_id": selected_but_not_deselected,
        "exclusion_reason": "測試用：此節點不應出現在預設 deselected 清單",
        "substitute_tests": list(removed.get("substitute_tests") or []),
    }
    bad_allowlist = tmp_path / "deselected_allowlist_equal_count_swap.json"
    bad_allowlist.write_text(
        json.dumps([unexpected, *allowlist[1:]], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = _run_gate(tmp_path, "--allowlist", str(bad_allowlist))
    combined = result.stdout + result.stderr

    assert result.returncode != 0
    assert "deselected 數量異常" not in combined
    assert "未核准 deselected" in combined
    assert removed["test_id"] in combined
    assert "allowlist 中預期 deselected 未出現" in combined
    assert "已回到 selected" in combined
    assert unexpected["test_id"] in combined


def test_ci_gate_fails_when_deselected_reason_changes_or_is_missing(tmp_path: Path) -> None:
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

    modified = [dict(entry) for entry in allowlist]
    missing_reason_id = modified[0]["test_id"]
    modified[0].pop("collection_reason")
    bad_allowlist = tmp_path / "deselected_allowlist_missing_reason.json"
    bad_allowlist.write_text(
        json.dumps(modified, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = _run_gate(tmp_path, "--allowlist", str(bad_allowlist))
    combined = result.stdout + result.stderr

    assert result.returncode != 0
    assert f"allowlist 缺少 collection_reason：{missing_reason_id}" in combined


def test_policy_fails_when_allowlisted_test_disappears_from_collection() -> None:
    allowlist = _load_allowlist()
    all_ids, selected, details = _base_ids_from_allowlist(allowlist)
    vanished = allowlist[0]["test_id"]
    all_ids = [node for node in all_ids if node != vanished]
    # vanished is no longer in collection; keep other deselected + selected
    remaining_deselected = [row["test_id"] for row in allowlist[1:]]
    selected = [node for node in selected if node != vanished]

    failures = evaluate_deselection_policy(
        all_ids=all_ids,
        selected_ids=selected,
        details={k: v for k, v in details.items() if k != vanished},
        allowlist=allowlist,
        matrix={"tests": []},
        critical_risks=set(),
        workflow_text=None,
    )

    assert any("allowlist 中既有測試已消失" in item for item in failures), failures
    assert vanished in " | ".join(failures)
    # Must not only report generic set mismatch without the disappear signal
    assert any(vanished in item and "已消失" in item for item in failures)


def test_policy_fails_when_unapproved_new_exclusion_appears() -> None:
    allowlist = _load_allowlist()
    all_ids, selected, details = _base_ids_from_allowlist(allowlist)
    rogue = "tests/test_cli.py::test_rogue_unapproved_deselect"
    all_ids = sorted(set(all_ids) | {rogue})
    # leave rogue out of selected → it becomes deselected
    details = {
        **details,
        rogue: "deselected by -m 'not integration'",
    }

    failures = evaluate_deselection_policy(
        all_ids=all_ids,
        selected_ids=selected,
        details=details,
        allowlist=allowlist,
        matrix={"tests": []},
        critical_risks=set(),
        workflow_text=None,
    )

    assert any("未核准 deselected" in item for item in failures), failures
    assert rogue in " | ".join(failures)
    assert any("數量異常" in item for item in failures)


def test_policy_fails_when_substitute_coverage_not_selected() -> None:
    allowlist = _load_allowlist()
    all_ids, selected, details = _base_ids_from_allowlist(allowlist)
    first = allowlist[0]
    sub_id = first["substitute_tests"][0]
    # Drop substitute from selected → simulates substitute coverage job not running it
    selected = [node for node in selected if node != sub_id]
    # Keep it collectable (still in all_ids) but deselected
    if sub_id not in all_ids:
        all_ids = sorted(set(all_ids) | {sub_id})

    failures = evaluate_deselection_policy(
        all_ids=all_ids,
        selected_ids=selected,
        details=details,
        allowlist=allowlist,
        matrix={"tests": []},
        critical_risks=set(),
        workflow_text=None,
    )

    joined = " | ".join(failures)
    assert "替代覆蓋測試未被預設 selected（等同 job 未執行）" in joined
    assert sub_id in joined
    assert first["test_id"] in joined


def test_policy_fails_when_substitute_coverage_test_missing() -> None:
    allowlist = _load_allowlist()
    all_ids, selected, details = _base_ids_from_allowlist(allowlist)
    first = allowlist[0]
    ghost = "tests/test_missing.py::test_substitute_gone"
    mutated = [dict(row) for row in allowlist]
    mutated[0] = {
        **mutated[0],
        "substitute_tests": [ghost, *first["substitute_tests"][1:]],
    }

    failures = evaluate_deselection_policy(
        all_ids=all_ids,
        selected_ids=selected,
        details=details,
        allowlist=mutated,
        matrix={"tests": []},
        critical_risks=set(),
        workflow_text=None,
    )

    joined = " | ".join(failures)
    assert "替代覆蓋測試不存在（無法執行）" in joined
    assert ghost in joined


def test_policy_fails_when_substitute_tests_empty() -> None:
    allowlist = _load_allowlist()
    all_ids, selected, details = _base_ids_from_allowlist(allowlist)
    mutated = [dict(row) for row in allowlist]
    target = mutated[0]["test_id"]
    mutated[0] = {**mutated[0], "substitute_tests": []}

    failures = evaluate_deselection_policy(
        all_ids=all_ids,
        selected_ids=selected,
        details=details,
        allowlist=mutated,
        matrix={"tests": []},
        critical_risks=set(),
        workflow_text=None,
    )

    assert f"allowlist 缺少 substitute_tests：{target}" in failures


def test_workflow_check_requires_coverage_jobs_and_gate_step() -> None:
    good = _WORKFLOW.read_text(encoding="utf-8")
    assert validate_workflow_coverage_jobs(good) == []

    missing_job = good.replace("test-pinned:", "test-pinned-removed:")
    failures = validate_workflow_coverage_jobs(missing_job)
    assert any("缺少替代覆蓋 job：test-pinned" in item for item in failures)

    no_gate = good.replace("validate_deselection_ci.py", "other_script.py")
    failures = validate_workflow_coverage_jobs(no_gate)
    assert any("防漏跑檢查未掛載" in item for item in failures)

    no_marker = good.replace('-m "not integration"', '-m "integration"')
    failures = validate_workflow_coverage_jobs(no_marker)
    assert any("not integration" in item for item in failures)

    assert validate_workflow_coverage_jobs("") == [
        "CI workflow 內容為空，無法確認替代覆蓋 job"
    ]


def test_ci_gate_fails_when_workflow_coverage_job_missing(tmp_path: Path) -> None:
    bad_workflow = tmp_path / "ci.yml"
    bad_workflow.write_text(
        "name: CI\njobs:\n  only-other:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )

    result = _run_gate(tmp_path, "--workflow", str(bad_workflow))
    combined = result.stdout + result.stderr

    assert result.returncode != 0
    assert "CI workflow 缺少替代覆蓋 job：test-pinned" in combined
    assert "CI workflow 缺少替代覆蓋 job：test-latest" in combined
    assert "防漏跑檢查未掛載" in combined


def test_live_gate_with_skip_workflow_still_enforces_allowlist(tmp_path: Path) -> None:
    """Regression: --skip-workflow-check must not silence allowlist failures."""
    allowlist = _load_allowlist()
    short = allowlist[:1]
    bad = tmp_path / "short.json"
    bad.write_text(json.dumps(short, ensure_ascii=False, indent=2), encoding="utf-8")

    result = _run_gate(
        tmp_path,
        "--allowlist",
        str(bad),
        "--skip-workflow-check",
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "未核准 deselected" in combined or "數量異常" in combined


# Additive JSON collection controls; original gate/policy controls above are retained.
_CURRENT_WHITESPACE_IDS = [
    "tests/test_metrics_pipeline.py::TestRerunNote::test_rerun_non_object_manifest_returns_alert_without_rewriting[delivery_manifest.json-not an object]",
    "tests/test_metrics_pipeline.py::TestRerunNote::test_rerun_non_object_manifest_returns_alert_without_rewriting[note.md.delivery_manifest.json-not an object]",
    r"tests/test_traceability.py::test_traceability_gate_rejects_missing_wrong_or_shifted_span[<lambda>-citation_spans \u907a\u6f0f\u4f86\u6e90]",
    r"tests/test_traceability.py::test_traceability_gate_rejects_missing_wrong_or_shifted_span[<lambda>-\u7bc4\u570d\u8207 marker_text \u4e0d\u4e00\u81f4]",
]


def _machine_record(selected: list[str], details: dict[str, str] | None = None) -> str:
    return "NOTE_FILLER_COLLECTION_JSON_V1=" + json.dumps({
        "schema": "note-filler.pytest-collection/v1",
        "selected": selected,
        "deselected": [{"node_id": node, "reason": reason}
                       for node, reason in (details or {}).items()],
    }) + "\n"


def test_collection_record_preserves_actual_whitespace_and_arbitrary_labels() -> None:
    ids = [*_CURRENT_WHITESPACE_IDS,
           "tests/test_owned.py::test_label[a\tb]",
           "tests/test_owned.py::test_label[a | reason: b]",
           r"tests\test_owned.py::test_label[C:\owned\new\file]"]
    assert _parse_node_ids(_machine_record(ids)) == ids


def test_actual_collection_machine_record_captures_all_four_current_ids() -> None:
    text = _run_collect("-o", "addopts=", *_CURRENT_WHITESPACE_IDS)
    assert _parse_node_ids(text) == _CURRENT_WHITESPACE_IDS
    assert _parse_deselected_details(text) == {}


def test_collection_record_ignores_human_details_footer_and_warning_rows() -> None:
    actual = "tests/test_owned.py::test_selected[has spaces]"
    text = ("tests/test_owned.py::test_human_only\n"
            + _machine_record([actual])
            + "=== deselected details ===\n"
            + "tests/test_owned.py::test_other[x y] | reason: deselected by -m 'not integration'\n"
            + "tests/test_owned.py::test_warning_only\n"
            + "1 test collected in 0.1s\n")
    assert _parse_node_ids(text) == [actual]
    assert _parse_deselected_details(text) == {}


@pytest.mark.parametrize("bad_text", [
    "tests/test_owned.py::test_human_only\n",
    _machine_record([]) + _machine_record([]),
    "NOTE_FILLER_COLLECTION_JSON_V1={\n",
    'NOTE_FILLER_COLLECTION_JSON_V1={"schema":"wrong","selected":[],"deselected":[]}\n',
    'NOTE_FILLER_COLLECTION_JSON_V1={"schema":"note-filler.pytest-collection/v1","selected":[],"selected":[],"deselected":[]}\n',
    'NOTE_FILLER_COLLECTION_JSON_V1={"schema":"note-filler.pytest-collection/v1","selected":[1],"deselected":[]}\n',
    'NOTE_FILLER_COLLECTION_JSON_V1={"schema":"note-filler.pytest-collection/v1","selected":[],"deselected":[],"extra":true}\n',
    _machine_record(["tests/test_owned.py::test_same", "tests/test_owned.py::test_same"]),
    _machine_record(["tests/test_owned.py::test_same"], {"tests/test_owned.py::test_same": "reason"}),
])
def test_collection_record_fails_closed_on_missing_duplicate_or_malformed_record(bad_text: str) -> None:
    with pytest.raises(RuntimeError):
        _parse_node_ids(bad_text)
    with pytest.raises(RuntimeError):
        _parse_deselected_details(bad_text)


def test_policy_rejects_unapproved_whitespace_exclusion_after_machine_parse() -> None:
    allowlist = _load_allowlist()
    all_ids, selected, details = _base_ids_from_allowlist(allowlist)
    rogue = "tests/test_owned.py::test_unapproved[has spaces]"
    all_ids.append(rogue)
    details[rogue] = "deselected by -m 'not integration'"
    failures = evaluate_deselection_policy(
        all_ids=_parse_node_ids(_machine_record(all_ids)),
        selected_ids=_parse_node_ids(_machine_record(selected, details)),
        details=_parse_deselected_details(_machine_record(selected, details)),
        allowlist=allowlist, matrix={"tests": []}, critical_risks=set(),
    )
    assert any("未核准 deselected" in item and rogue in item for item in failures)


def test_policy_rejects_missing_whitespace_allowlisted_reason_after_machine_parse() -> None:
    allowlist = [dict(row) for row in _load_allowlist()]
    missing = "tests/test_owned.py::test_allowlisted[has spaces]"
    allowlist[0]["test_id"] = missing
    all_ids, selected, details = _base_ids_from_allowlist(allowlist)
    details.pop(missing)
    failures = evaluate_deselection_policy(
        all_ids=_parse_node_ids(_machine_record(all_ids)),
        selected_ids=_parse_node_ids(_machine_record(selected, details)),
        details=_parse_deselected_details(_machine_record(selected, details)),
        allowlist=allowlist, matrix={"tests": []}, critical_risks=set(),
    )
    assert f"缺少 deselected reason：{missing}" in failures


@pytest.mark.parametrize("present_but_unselected", [False, True])
def test_policy_rejects_missing_or_unselected_whitespace_substitute_after_machine_parse(present_but_unselected: bool) -> None:
    allowlist = [dict(row) for row in _load_allowlist()]
    all_ids, selected, details = _base_ids_from_allowlist(allowlist)
    sub = "tests/test_owned.py::test_substitute[has spaces]"
    allowlist[0]["substitute_tests"] = [sub]
    if present_but_unselected:
        all_ids.append(sub)
        details[sub] = "deselected by -m 'not integration'"
    failures = evaluate_deselection_policy(
        all_ids=_parse_node_ids(_machine_record(all_ids)),
        selected_ids=_parse_node_ids(_machine_record(selected, details)),
        details=_parse_deselected_details(_machine_record(selected, details)),
        allowlist=allowlist, matrix={"tests": []}, critical_risks=set(),
    )
    expected = "替代覆蓋測試未被預設 selected" if present_but_unselected else "替代覆蓋測試不存在"
    assert any(expected in item and sub in item for item in failures)


def test_collection_record_preserves_whitespace_reason_and_label_delimiter() -> None:
    node = "tests/test_owned.py::test_deselected[a | reason: b]"
    reason = "deselected by -k 'has spaces'"
    text = _machine_record([], {node: reason})
    assert _parse_node_ids(text) == []
    assert _parse_deselected_details(text) == {node: reason}
