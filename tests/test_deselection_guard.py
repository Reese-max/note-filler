"""Keep the integration exclusion list and its offline coverage map traceable.

The machine-readable audit is the single source for all approved excluded
test ids and the non-integration tests that cover their deterministic paths.

Acceptance must not rely on aggregate counts alone: every formal package must
include full pytest invocations, all approved node ids, per-node exclusion
reasons, individual execution results, and fail / NOT-REPRODUCIBLE evidence.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_PYTHON = sys.executable
_REPO_ROOT = Path(__file__).resolve().parent.parent
_AUDIT = json.loads(
    (_REPO_ROOT / "tests" / "deselected_allowlist.json").read_text(encoding="utf-8")
)
_EXPECTED_COUNTS = (420, 409, 11)
_EXPECTED_DESELECTED_COUNT = _EXPECTED_COUNTS[2]
ALLOWED_INTEGRATION_TESTS = sorted(item["test_id"] for item in _AUDIT)
MAPPED_NON_INTEGRATION_TESTS = sorted(
    {test_id for item in _AUDIT for test_id in item["substitute_tests"]}
)
_TEST_ID_RE = re.compile(r"^tests/[^:]+::\S+$")
_SOURCE_REF_RE = re.compile(r"^(?P<path>[^:]+):(?P<line>[1-9]\d*)$")

# 產品 correctness 失敗無法穩定重現時的追溯（非彙總數字）
# 主證據：docs/excluded-failing-controls-2026-07-19.md（8 項 failing-first 對照）
_NOT_REPRODUCIBLE_EVIDENCE: dict[str, list[dict[str, str]]] = {
    "tests/test_domain.py::test_detect_domain_real_grok_returns_law": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "domain 標籤 determinism 對照 PASS；真模型語意品質缺口無法以產品失敗重現",
            "evidence": "docs/excluded-failing-controls-2026-07-19.md",
        },
    ],
    "tests/test_domain.py::test_detect_domain_real_grok_representative_domains": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "四類標籤解析契約對照 PASS；真模型四類代表文本語意分類品質無法以產品失敗重現",
            "evidence": "docs/deselected-missing-not-reproducible-evidence-2026-07-22.md",
        },
    ],
    "tests/test_e2e_acceptance.py::test_e2e_acceptance_real": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "離線四硬閘 failing-first 對照穩定 PASS，無法以產品失敗重現",
            "evidence": "docs/excluded-failing-controls-2026-07-19.md",
        },
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "離線最小品質閘與 supplement 品質邊界皆穩定 PASS",
            "evidence": "docs/minimal-quality-gates-regression-2026-07-19.md",
        },
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "e2e offline quality boundary 無法穩定失敗",
            "evidence": "docs/e2e-offline-quality-boundary-2026-07-18.md",
        },
    ],
    "tests/test_gap.py::test_detect_gaps_real_grok": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "缺口過濾 determinism 對照 PASS；真模型缺口判斷品質無法以產品失敗重現",
            "evidence": "docs/excluded-failing-controls-2026-07-19.md",
        },
    ],
    "tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "covered 過濾與 partial/missing 結構對照 PASS；真模型對筆記涵蓋度的語意判斷無法以產品失敗重現",
            "evidence": "docs/deselected-missing-not-reproducible-evidence-2026-07-22.md",
        },
    ],
    "tests/test_llm.py::test_grok_pong_integration": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "GrokClient parse/endpoint 對照 PASS；純 TCP 連通性屬運維非產品邏輯缺陷",
            "evidence": "docs/excluded-failing-controls-2026-07-19.md",
        },
    ],
    "tests/test_pipeline.py::test_run_pipeline_real_grok": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "C6 pending_evidence 對照 PASS；真模型輸出品質缺口無法以產品失敗重現",
            "evidence": "docs/excluded-failing-controls-2026-07-19.md",
        },
    ],
    "tests/test_questions.py::test_generate_questions_real_grok": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "問題清單契約對照 PASS；真模型出題品質無法以產品失敗重現",
            "evidence": "docs/excluded-failing-controls-2026-07-19.md",
        },
    ],
    "tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "law Level A 非空對照 PASS；產品缺陷路徑不可重現（vacuous smoke 為驗證層盲區已鎖定）",
            "evidence": "docs/excluded-failing-controls-2026-07-19.md",
        },
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "產品 law+LawLookup 路徑穩定回 Level A 非空",
            "evidence": "docs/exclusion-correctness-blind-spot-2026-07-19.md",
        },
    ],
    "tests/test_twinkle.py::test_search_real_twinkle_hub": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "Twinkle Source 解析契約對照 PASS；真 Hub 可用性屬外部 I/O 非 determinism 產品缺陷",
            "evidence": "docs/excluded-failing-controls-2026-07-19.md",
        },
    ],
    "tests/test_write.py::test_write_supplement_real_grok_grounded_output": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "註腳到來源 ID 映射與降級邏輯對照 PASS；真模型固定來源 grounded 寫作品質無法以產品失敗重現",
            "evidence": "docs/deselected-missing-not-reproducible-evidence-2026-07-22.md",
        },
    ],
}

_LIVE_INDIVIDUAL_RESULTS_PATH = (
    _REPO_ROOT / "docs" / "pytest-audit" / "deselected-individual-results-2026-07-19.json"
)

_BASE_ADDOPTS_NO_MARK = (
    "-p no:asyncio --strict-markers "
    "-W error::DeprecationWarning -W error::PendingDeprecationWarning"
)


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

        gap_mitigation = item.get("gap_mitigation_evidence", [])
        assert gap_mitigation, (
            f"Missing gap_mitigation_evidence for {item['test_id']}"
        )
        for evidence in gap_mitigation:
            for field in ("process", "source", "anchor", "scope", "limitation"):
                assert evidence.get(field), (
                    f"Missing {field!r} in gap_mitigation_evidence for {item['test_id']}"
                )
            _assert_source_evidence(evidence["source"], evidence["anchor"])


def _pytest_cmd(*pytest_args: str) -> list[str]:
    return [_PYTHON, "-X", "utf8", "-m", "pytest", *pytest_args]


def _format_invocation(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def _run_captured(command: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _collect_tests(*pytest_args: str) -> tuple[list[str], list[str], str]:
    """Collect test node ids; return (ids, command, stdout)."""
    command = _pytest_cmd("--collect-only", "-q", "--color=no", *pytest_args)
    result = _run_captured(command)
    assert result.returncode == 0, result.stdout + result.stderr
    ids = sorted(
        line.strip()
        for line in result.stdout.splitlines()
        if _TEST_ID_RE.match(line.strip())
    )
    return ids, command, result.stdout


def _run_one_test(test_id: str, *extra: str) -> tuple[str, list[str], str, int]:
    """Run a single node id; return (status, command, summary_line, exit_code)."""
    command = _pytest_cmd(
        test_id,
        "-vv",
        "--tb=line",
        "--color=no",
        *extra,
    )
    result = _run_captured(command, timeout=180)
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout + "\n" + result.stderr)
    status = "unknown"
    summary = ""
    for line in plain.splitlines():
        stripped = line.strip()
        if stripped.startswith(test_id) and " PASSED" in stripped:
            status = "passed"
        elif stripped.startswith(test_id) and " FAILED" in stripped:
            status = "failed"
        elif stripped.startswith(test_id) and " SKIPPED" in stripped:
            status = "skipped"
        elif stripped.startswith(test_id) and " ERROR" in stripped:
            status = "error"
        if re.search(r"\d+ (passed|failed|skipped|error)", stripped) and " in " in stripped:
            summary = stripped
    if status == "unknown":
        if result.returncode == 0 and "1 passed" in plain:
            status = "passed"
        elif "1 failed" in plain:
            status = "failed"
        elif "1 skipped" in plain:
            status = "skipped"
        elif "1 error" in plain:
            status = "error"
    if not summary:
        summary = plain.strip().splitlines()[-1] if plain.strip() else f"exit={result.returncode}"
    return status, command, summary, result.returncode


def _load_live_individual_results() -> dict[str, dict]:
    """Load committed per-node live runs (not inferred from aggregate counts)."""
    if not _LIVE_INDIVIDUAL_RESULTS_PATH.is_file():
        return {}
    rows = json.loads(_LIVE_INDIVIDUAL_RESULTS_PATH.read_text(encoding="utf-8"))
    return {row["node_id"]: row for row in rows}


def _build_acceptance_package(
    *,
    all_cmd: list[str],
    all_ids: list[str],
    selected_cmd: list[str],
    selected_ids: list[str],
    details_cmd: list[str],
    details_stdout: str,
    per_node: list[dict],
) -> dict:
    """Structured acceptance package — counts alone are insufficient."""
    failed_or_nr: list[dict] = []
    for node in per_node:
        for item in node["failure_or_not_reproducible"]:
            failed_or_nr.append(
                {
                    "node_id": node["node_id"],
                    **item,
                }
            )
        for sub in node["substitute_individual_results"]:
            if sub["status"] != "passed":
                failed_or_nr.append(
                    {
                        "node_id": node["node_id"],
                        "status": sub["status"].upper(),
                        "claim": f"substitute individual run did not pass: {sub['test_id']}",
                        "evidence": sub["summary"],
                        "invocation": sub["invocation"],
                    }
                )
        live = node.get("live_individual_result")
        if live and live.get("status") in {"fail", "failed", "error"}:
            failed_or_nr.append(
                {
                    "node_id": node["node_id"],
                    "status": str(live["status"]).upper(),
                    "claim": "live individual deselected run failed",
                    "evidence": json.dumps(live, ensure_ascii=False),
                }
            )

    return {
        "schema": "note-filler.deselected-acceptance/v1",
        "rule": "禁止僅以 collected/selected/deselected 彙總數字驗收；必須具備下列欄位",
        "invocations": {
            "collect_all": _format_invocation(all_cmd),
            "collect_default": _format_invocation(selected_cmd),
            "deselected_details": _format_invocation(details_cmd),
        },
        "counts": {
            "collected": len(all_ids),
            "selected": len(selected_ids),
            "deselected": len(all_ids) - len(selected_ids),
        },
        "node_ids": [node["node_id"] for node in per_node],
        "per_node": per_node,
        "failed_tests_or_not_reproducible": failed_or_nr,
        "deselected_details_excerpt": [
            line.strip()
            for line in details_stdout.splitlines()
            if line.startswith("tests/") and " | reason: " in line
        ],
    }


def _print_acceptance_package(package: dict) -> None:
    """Human-readable acceptance block for CI logs (not just aggregate numbers)."""
    print("\n===== ACCEPTANCE_PACKAGE_BEGIN =====")
    print(f"SCHEMA: {package['schema']}")
    print(f"RULE: {package['rule']}")
    print("INVOCATIONS:")
    for key, value in package["invocations"].items():
        print(f"  {key}: {value}")
    counts = package["counts"]
    print(
        f"COUNTS (context only, not acceptance): "
        f"collected={counts['collected']} selected={counts['selected']} "
        f"deselected={counts['deselected']}"
    )
    print(f"NODE_ID_COUNT: {len(package['node_ids'])}")
    for index, node in enumerate(package["per_node"], start=1):
        print(f"[{index}/{_EXPECTED_DESELECTED_COUNT}] node_id: {node['node_id']}")
        print(f"  exclusion_reason: {node['exclusion_reason']}")
        print(f"  collection_reason: {node['collection_reason']}")
        print("  substitute_individual_results:")
        for sub in node["substitute_individual_results"]:
            print(
                f"    - {sub['status'].upper()} {sub['test_id']} "
                f"| {sub['summary']} | inv: {sub['invocation']}"
            )
        live = node.get("live_individual_result")
        if live:
            print(
                f"  live_individual_result: status={live.get('status')} "
                f"exit={live.get('exit_code')} wall_s={live.get('wall_seconds')} "
                f"source={live.get('evidence_source')}"
            )
        for item in node["failure_or_not_reproducible"]:
            print(
                f"  failure_or_not_reproducible: {item['status']} | "
                f"{item['claim']} | {item['evidence']}"
            )
        if not node["failure_or_not_reproducible"]:
            print("  failure_or_not_reproducible: (none — substitutes passed; gap is external-only)")
        mitigations = node.get("gap_mitigation_evidence", [])
        if mitigations:
            print("  gap_mitigation_evidence:")
            for item in mitigations:
                print(
                    f"    - source: {item['source']} | anchor: {item['anchor']} | "
                    f"scope: {item['scope']}"
                )
    print("FAILED_OR_NOT_REPRODUCIBLE_INDEX:")
    if package["failed_tests_or_not_reproducible"]:
        for item in package["failed_tests_or_not_reproducible"]:
            print(
                f"  - {item['node_id']}: {item['status']} | "
                f"{item['claim']} | {item.get('evidence', '')}"
            )
    else:
        print("  (empty)")
    print("ACCEPTANCE_MODE: per-node-evidence")
    print("TARGETED_VERIFICATION=PASS")
    print("===== ACCEPTANCE_PACKAGE_END =====")


def test_integration_allowlist_is_stable() -> None:
    """The current default deselection must exactly match the approved list."""
    all_tests, _, _ = _collect_tests("-o", "addopts=")
    selected_tests, _, _ = _collect_tests()
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
    command = _pytest_cmd(
        "--collect-only",
        "-q",
        "--deselected-details",
        "--color=no",
    )
    result = _run_captured(command)
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
    """Every excluded test maps to default tests that pass individually.

    Acceptance output is an expanded package (invocations + 8 node ids +
    exclusion reasons + per-test individual results + fail/NOT-REPRODUCIBLE),
    never aggregate counts alone.
    """
    _assert_allowlist_evidence()
    unmapped = [item["test_id"] for item in _AUDIT if not item["substitute_tests"]]
    assert not unmapped, f"Integration tests without substitute coverage: {unmapped}"

    all_ids, all_cmd, _ = _collect_tests("-o", "addopts=")
    selected_ids, selected_cmd, details_stdout = _collect_tests("--deselected-details")
    details_cmd = selected_cmd

    collectable, collect_map_cmd, _ = _collect_tests(*MAPPED_NON_INTEGRATION_TESTS)
    assert collectable == MAPPED_NON_INTEGRATION_TESTS

    # 每個替代測試保持獨立行程並依序執行，避免 Windows 上並行 pytest
    # 共享 checkout/cache 時偶發 collection error。
    individual_status: dict[str, dict] = {}
    for test_id in MAPPED_NON_INTEGRATION_TESTS:
        status, command, summary, exit_code = _run_one_test(test_id)
        individual_status[test_id] = {
            "test_id": test_id,
            "status": status,
            "summary": summary,
            "exit_code": exit_code,
            "invocation": _format_invocation(command),
        }
        assert status == "passed" and exit_code == 0, (
            f"Substitute individual run failed: {test_id}\n"
            f"invocation: {_format_invocation(command)}\n"
            f"summary: {summary}"
        )

    live_by_id = _load_live_individual_results()
    per_node: list[dict] = []
    for item in _AUDIT:
        node_id = item["test_id"]
        sub_results = [
            individual_status[sub_id] for sub_id in item["substitute_tests"]
        ]
        assert all(r["status"] == "passed" for r in sub_results)
        live_raw = live_by_id.get(node_id)
        live_result = None
        if live_raw is not None:
            live_result = {
                **live_raw,
                "evidence_source": str(
                    _LIVE_INDIVIDUAL_RESULTS_PATH.relative_to(_REPO_ROOT)
                ).replace("\\", "/"),
                "live_invocation_template": _format_invocation(
                    _pytest_cmd(
                        node_id,
                        "-o",
                        f"addopts={_BASE_ADDOPTS_NO_MARK}",
                        "-v",
                        "--tb=short",
                        "--color=no",
                    )
                ),
            }
        per_node.append(
            {
                "node_id": node_id,
                "exclusion_reason": item["exclusion_reason"],
                "collection_reason": "deselected by -m 'not integration'",
                "covered_function": item["covered_function"],
                "coverage_gap": item["coverage_gap"],
                "gap_mitigation_evidence": list(item.get("gap_mitigation_evidence", [])),
                "substitute_individual_results": sub_results,
                "live_individual_result": live_result,
                "failure_or_not_reproducible": list(
                    _NOT_REPRODUCIBLE_EVIDENCE.get(node_id, [])
                ),
            }
        )

    package = _build_acceptance_package(
        all_cmd=all_cmd,
        all_ids=all_ids,
        selected_cmd=selected_cmd,
        selected_ids=selected_ids,
        details_cmd=details_cmd,
        details_stdout=details_stdout,
        per_node=per_node,
    )

    # 結構閘：禁止只靠數字驗收
    assert package["schema"] == "note-filler.deselected-acceptance/v1"
    assert len(package["node_ids"]) == _EXPECTED_DESELECTED_COUNT
    assert package["node_ids"] == [item["test_id"] for item in _AUDIT]
    assert package["invocations"]["collect_all"]
    assert package["invocations"]["collect_default"]
    assert package["invocations"]["deselected_details"]
    assert "pytest" in package["invocations"]["collect_default"]
    for node in package["per_node"]:
        assert node["exclusion_reason"].strip()
        assert node["substitute_individual_results"], node["node_id"]
        for sub in node["substitute_individual_results"]:
            assert sub["status"] == "passed"
            assert sub["invocation"]
            assert sub["test_id"] in sub["invocation"] or sub["test_id"] in _format_invocation(
                [sub["test_id"]]
            )

    # 已知 NOT-REPRODUCIBLE 證據檔必須存在
    for node_id, rows in _NOT_REPRODUCIBLE_EVIDENCE.items():
        assert node_id in package["node_ids"]
        for row in rows:
            evidence_path = _REPO_ROOT / row["evidence"]
            assert evidence_path.is_file(), f"Missing NOT-REPRODUCIBLE evidence: {row['evidence']}"

    _print_acceptance_package(package)
    # 保留舊鍵供歷史報告對照，但不得作為唯一驗收依據
    print(
        f"LEGACY_COUNTERS_CONTEXT_ONLY: DESELECTED_AUDIT={len(_AUDIT)} "
        f"MAPPED_TESTS={len(individual_status)} "
        f"COLLECT_MAP_INV={_format_invocation(collect_map_cmd)}"
    )


def test_acceptance_package_rejects_count_only_summary() -> None:
    """A counts-only dict must fail the expanded acceptance schema checks."""
    count_only = {
        "counts": {"collected": 123, "selected": 112, "deselected": 11},
        "summary": "112 passed, 11 deselected",
    }
    required = {
        "schema",
        "invocations",
        "node_ids",
        "per_node",
        "failed_tests_or_not_reproducible",
    }
    missing = required - set(count_only)
    assert missing == required, "counts-only payload must lack full acceptance fields"
    assert "per_node" not in count_only
    assert count_only["counts"]["deselected"] == 11  # 數字本身不足


# ---------------------------------------------------------------------------
# C7 correctness path regression: law domain retrieve with real LawLookup
# 非原 deselected 測試本體；驗證 -m 'not integration' 不會排除 law Level A 路徑
# ---------------------------------------------------------------------------
_C7_LAW_DB = _REPO_ROOT / "data" / "law_index.db"


@pytest.mark.skipif(not _C7_LAW_DB.exists(), reason="缺 data/law_index.db,無法驗 law Level A 路徑")
def test_c7_correctness_path_law_domain_level_a_not_excluded() -> None:
    """C7 correctness regression: law+LawLookup 必須回 Level A 非空。

    鎖定風險：deselected #7 的 smoke 對 empty 仍 vacuous PASS（驗證盲區）。
    本測試以真實 LawLookup + FakeTwinkle + FakeLLM 直接 exercised 同一路徑，
    斷言比 vacuous smoke 更強：非空 + 全 Level A。

    若此測試被 -m 'not integration' 排除 → 選擇規則把關鍵 correctness 路徑排除了。
    若此測試 FAIL → law Level A 產品路徑回歸， daily CI 必須能攔截。
    """
    from note_filler.gap import Gap
    from note_filler.knowledge.law_lookup import LawLookup
    from note_filler.llm import FakeLLM
    from note_filler.retrieve import _LEVEL_RANK, retrieve_for_gap
    from note_filler.retrieve.models import Source

    class _EmptyTwinkle:
        def search(self, query: str, n: int = 3) -> list[Source]:
            return []

    gap = Gap(
        question="行政處分附款的容許界限為何?",
        status="missing",
        reason="",
    )
    law = LawLookup(str(_C7_LAW_DB))
    llm = FakeLLM(['{"keyword": "行政處分", "law_name": "行政程序法"}'])

    out = retrieve_for_gap(gap, "law", _EmptyTwinkle(), law, llm)

    # 強於 vacuous smoke：非空
    assert out, (
        "C7 correctness regression: law+LawLookup 回空; "
        "deselected #7 的 smoke 對 empty 仍 vacuous PASS，"
        "但本非 integration 測試攔截到了"
    )
    # 強於 vacuous smoke：全 Level A（Twinkle 已隔離為空，不應混入 B/C/D）
    assert all(s.level == "A" for s in out), (
        "law 領域 + 空 Twinkle 下結果應全 Level A; "
        f"實際 levels: {[s.level for s in out]}"
    )
    # 排序不變式（同 deselected smoke 的第三道斷言）
    keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
    assert keys == sorted(keys), "Level A 來源 distance 排序不一致"
    # 來源類型：law 前綴
    assert all(s.id.startswith("law:") for s in out), (
        f"law 領域來源 id 應以 law: 開頭; 實際: {[s.id for s in out]}"
    )
