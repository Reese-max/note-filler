"""Refresh committed pytest collection, marker, and test-run evidence.

Also emits an expanded acceptance package that must include full pytest
invocations, all eight deselected node ids, per-node exclusion reasons,
individual substitute results, and fail / NOT-REPRODUCIBLE evidence —
never aggregate counts alone.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "pytest-audit"
PYTEST = [sys.executable, "-X", "utf8", "-m", "pytest"]
RESULTS = ("PASSED", "SKIPPED", "XFAIL", "XPASS", "FAILED", "ERROR")
LIVE_INDIVIDUAL = OUTPUT_DIR / "deselected-individual-results-2026-07-19.json"
NOT_REPRODUCIBLE: dict[str, list[dict[str, str]]] = {
    "tests/test_domain.py::test_detect_domain_real_grok_returns_law": [
        {
            "status": "NOT-REPRODUCIBLE",
            "claim": "domain 標籤 determinism 對照 PASS；真模型語意品質缺口無法以產品失敗重現",
            "evidence": "docs/excluded-failing-controls-2026-07-19.md",
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
}


def run_pytest(*args: str, timeout: int = 180) -> tuple[list[str], str]:
    command = [*PYTEST, *args]
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    output = result.stdout
    if result.stderr:
        output += ("" if not output or output.endswith("\n") else "\n") + result.stderr
    output = "\n".join(line.rstrip() for line in output.splitlines()).rstrip() + "\n"
    if result.returncode:
        raise RuntimeError(
            f"pytest failed ({subprocess.list2cmdline(command)}):\n{output}"
        )
    return command, output


def node_ids(output: str) -> list[str]:
    return [
        line.strip()
        for line in output.splitlines()
        if line.startswith("tests/") and "::" in line
    ]


def deselection_details(output: str) -> list[dict[str, str]]:
    marker = " | reason: "
    details = []
    for line in output.splitlines():
        if line.startswith("tests/") and marker in line:
            test_id, reason = line.split(marker, 1)
            details.append({"test_id": test_id, "reason": reason})
    return details


def command_block(label: str, command: list[str], output: str) -> str:
    return (
        f"===== {label} =====\n"
        f"COMMAND: {subprocess.list2cmdline(command)}\n"
        "EXIT_CODE: 0\n\n"
        f"{output}"
    )


def evidence_report(
    *,
    all_ids: list[str],
    selected_ids: list[str],
    deselected_ids: list[str],
    integration_ids: list[str],
    allowlist: list[dict],
    outcomes: dict[str, str],
    result_lines: dict[str, str],
    invocations: dict[str, str],
    acceptance_package: dict,
) -> str:
    """Render the committed code-to-output chain for every deselected test."""
    allowlist_ids = [item["test_id"] for item in allowlist]
    assert sorted(allowlist_ids) == sorted(deselected_ids)
    lines = [
        "# Deselected 可接受未執行追溯證據",
        "",
        "> 本檔由 `scripts/refresh_pytest_audit.py` 產生；每一項都同時列出",
        "> 排除程式碼 anchor、替代測試程式碼 anchor，以及該替代測試在本次測試輸出中的結果。",
        ">",
        "> **驗收規則**：禁止僅以 `passed/deselected` 彙總數字驗收。完整套件見",
        "> [`acceptance-package.json`](acceptance-package.json) 與下方 invocation／逐項結果。",
        "",
        "## 完整 pytest invocation",
        "",
        f"- collect all: `{invocations['collect_all']}`",
        f"- collect default: `{invocations['collect_default']}`",
        f"- collect integration: `{invocations['collect_integration']}`",
        f"- deselected details: `{invocations['deselected_details']}`",
        f"- default test run: `{invocations['default_test_run']}`",
        "",
        "## 集合判定（僅上下文，非唯一驗收依據）",
        "",
        f"- 全量 collection：`{len(all_ids)}`",
        f"- 預設 selected：`{len(selected_ids)}`",
        f"- `deselected`：`{len(deselected_ids)}`",
        f"- `integration` 集合：`{len(integration_ids)}`",
        f"- allowlist 與實際 `deselected` 完全相等：`{sorted(allowlist_ids) == sorted(deselected_ids)}`",
        "- collection 原始輸出：[`collection.txt`](collection.txt)",
        "- 預設測試原始輸出：[`test-report.txt`](test-report.txt)",
        "- deselection 詳情原始輸出：[`deselected-details.txt`](deselected-details.txt)",
        "- 擴充驗收套件：[`acceptance-package.json`](acceptance-package.json)",
        "",
        "## 8 個 node ID 與排除原因",
        "",
    ]
    for index, item in enumerate(allowlist, start=1):
        lines.append(
            f"{index}. `{item['test_id']}` — {item['exclusion_reason']}"
        )
    lines.extend(["", "## 逐項證據鏈", ""])
    for index, item in enumerate(allowlist, start=1):
        node_id = item["test_id"]
        lines.extend(
            [
                f"### {index}. `{node_id}`",
                "",
                f"- 判定：`{item['decision']}`",
                f"- 排除理由：{item['exclusion_reason']}",
                "- 排除程式碼證據：",
            ]
        )
        for evidence in item["exclusion_evidence"]:
            lines.append(
                f"  - `{evidence['source']}` — `{evidence['anchor']}`："
                f"{evidence['claim']}"
            )
        lines.append("- 替代測試證據（單獨結果，非彙總）：")
        for evidence in item["substitute_evidence"]:
            test_id = evidence["test_id"]
            assert outcomes.get(test_id) == "PASSED", (
                f"Substitute did not pass: {test_id} ({outcomes.get(test_id)})"
            )
            lines.extend(
                [
                    f"  - `{test_id}` — `{evidence['source']}` — "
                    f"`{evidence['anchor']}`：{evidence['claim']} — **PASSED**",
                    f"    - 測試輸出：`{result_lines[test_id]}`",
                ]
            )
        live = next(
            (
                n.get("live_individual_result")
                for n in acceptance_package["per_node"]
                if n["node_id"] == node_id
            ),
            None,
        )
        if live:
            lines.append(
                f"- 單獨 live 執行結果：`{live.get('status')}` "
                f"(exit={live.get('exit_code')}, wall_s={live.get('wall_seconds')}, "
                f"source=`{live.get('evidence_source')}`)"
            )
        nr = NOT_REPRODUCIBLE.get(node_id, [])
        if nr:
            lines.append("- 失敗／NOT-REPRODUCIBLE 證據：")
            for row in nr:
                lines.append(
                    f"  - **{row['status']}** — {row['claim']} — `{row['evidence']}`"
                )
        else:
            lines.append(
                "- 失敗／NOT-REPRODUCIBLE 證據：（無；替代測試 PASSED，剩餘為外部依賴邊界）"
            )
        lines.extend(
            [
                f"- 未覆蓋邊界：{item['coverage_gap']}",
            ]
        )
        mitigations = item.get("gap_mitigation_evidence", [])
        if mitigations:
            lines.append("- 缺口替代驗證流程：")
            for ev in mitigations:
                lines.append(
                    f"  - `{ev['source']}` `{ev['anchor']}`：{ev['process']} — "
                    f"scope: {ev['scope']} | limitation: {ev['limitation']}"
                )
        lines.extend(
            [
                "- 結論：替代測試已保護確定性程式契約；剩餘邊界屬真實模型／外部服務，故可接受未執行。",
                "",
            ]
        )
    return "\n".join(lines)


def build_acceptance_package(
    *,
    invocations: dict[str, str],
    all_ids: list[str],
    selected_ids: list[str],
    deselected_ids: list[str],
    allowlist: list[dict],
    outcomes: dict[str, str],
    result_lines: dict[str, str],
    details: list[dict[str, str]],
) -> dict:
    """Machine-readable expanded acceptance package."""
    live_rows: dict[str, dict] = {}
    if LIVE_INDIVIDUAL.is_file():
        for row in json.loads(LIVE_INDIVIDUAL.read_text(encoding="utf-8")):
            live_rows[row["node_id"]] = row

    per_node = []
    failed_or_nr: list[dict] = []
    for item in allowlist:
        node_id = item["test_id"]
        sub_results = []
        for test_id in item["substitute_tests"]:
            status = outcomes.get(test_id, "MISSING").lower()
            sub_results.append(
                {
                    "test_id": test_id,
                    "status": status,
                    "summary": result_lines.get(test_id, ""),
                    "invocation": (
                        f"{subprocess.list2cmdline(PYTEST)} {test_id} "
                        f"-vv --tb=line --color=no"
                    ),
                }
            )
            if status != "passed":
                failed_or_nr.append(
                    {
                        "node_id": node_id,
                        "status": status.upper(),
                        "claim": f"substitute did not pass: {test_id}",
                        "evidence": result_lines.get(test_id, ""),
                    }
                )
        live = live_rows.get(node_id)
        live_result = None
        if live is not None:
            live_result = {
                **live,
                "evidence_source": str(LIVE_INDIVIDUAL.relative_to(ROOT)).replace(
                    "\\", "/"
                ),
                "live_invocation_template": (
                    f"{subprocess.list2cmdline(PYTEST)} {node_id} "
                    f'-o "addopts=-p no:asyncio --strict-markers '
                    f"-W error::DeprecationWarning "
                    f'-W error::PendingDeprecationWarning" -v --tb=short'
                ),
            }
            if live.get("status") in {"fail", "failed", "error"}:
                failed_or_nr.append(
                    {
                        "node_id": node_id,
                        "status": str(live["status"]).upper(),
                        "claim": "live individual deselected run failed",
                        "evidence": json.dumps(live, ensure_ascii=False),
                    }
                )
        nr_rows = list(NOT_REPRODUCIBLE.get(node_id, []))
        for row in nr_rows:
            failed_or_nr.append({"node_id": node_id, **row})
        per_node.append(
            {
                "node_id": node_id,
                "exclusion_reason": item["exclusion_reason"],
                "gap_mitigation_evidence": list(item.get("gap_mitigation_evidence", [])),
                "collection_reason": next(
                    (
                        d["reason"]
                        for d in details
                        if d["test_id"] == node_id
                    ),
                    "deselected by -m 'not integration'",
                ),
                "substitute_individual_results": sub_results,
                "live_individual_result": live_result,
                "failure_or_not_reproducible": nr_rows,
            }
        )

    return {
        "schema": "note-filler.deselected-acceptance/v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "rule": "禁止僅以 collected/selected/deselected 彙總數字驗收；必須具備下列欄位",
        "invocations": invocations,
        "counts": {
            "collected": len(all_ids),
            "selected": len(selected_ids),
            "deselected": len(deselected_ids),
        },
        "node_ids": [item["test_id"] for item in allowlist],
        "per_node": per_node,
        "failed_tests_or_not_reproducible": failed_or_nr,
        "acceptance_mode": "per-node-evidence",
    }


def render_acceptance_markdown(package: dict) -> str:
    """Human-readable acceptance package companion."""
    lines = [
        "# 擴充驗收套件（Acceptance Package）",
        "",
        f"> 產生時間：`{package['generated_at']}`",
        f">",
        f"> schema：`{package['schema']}`",
        f">",
        f"> **{package['rule']}**",
        "",
        "## 完整 pytest invocation",
        "",
    ]
    for key, value in package["invocations"].items():
        lines.append(f"- **{key}**: `{value}`")
    counts = package["counts"]
    lines.extend(
        [
            "",
            "## 彙總數字（僅上下文）",
            "",
            f"`collected={counts['collected']} selected={counts['selected']} "
            f"deselected={counts['deselected']}`",
            "",
            "上述數字**不可**單獨作為驗收通過依據。",
            "",
            "## 8 個 node ID × 排除原因 × 單獨結果 × 失敗/NOT-REPRODUCIBLE",
            "",
        ]
    )
    for index, node in enumerate(package["per_node"], start=1):
        lines.extend(
            [
                f"### {index}. `{node['node_id']}`",
                "",
                f"- 排除原因：{node['exclusion_reason']}",
                f"- collection 原因：`{node['collection_reason']}`",
                "- 替代測試單獨結果：",
            ]
        )
        for sub in node["substitute_individual_results"]:
            lines.append(
                f"  - **{sub['status'].upper()}** `{sub['test_id']}` — "
                f"`{sub['summary']}`"
            )
            lines.append(f"    - invocation: `{sub['invocation']}`")
        live = node.get("live_individual_result")
        if live:
            lines.append(
                f"- live 單獨執行：`{live.get('status')}` "
                f"(exit={live.get('exit_code')}, wall_s={live.get('wall_seconds')})"
            )
            lines.append(f"  - source: `{live.get('evidence_source')}`")
            lines.append(f"  - invocation template: `{live.get('live_invocation_template')}`")
        if node["failure_or_not_reproducible"]:
            lines.append("- 失敗／NOT-REPRODUCIBLE：")
            for row in node["failure_or_not_reproducible"]:
                lines.append(
                    f"  - **{row['status']}** — {row['claim']} — `{row['evidence']}`"
                )
        else:
            lines.append("- 失敗／NOT-REPRODUCIBLE：（無）")
        mitigations = node.get("gap_mitigation_evidence", [])
        if mitigations:
            lines.append("- 缺口替代驗證流程：")
            for ev in mitigations:
                lines.append(
                    f"  - `{ev['source']}` `{ev['anchor']}`：{ev['process']} — "
                    f"scope: {ev['scope']} | limitation: {ev['limitation']}"
                )
        lines.append("")
    lines.extend(
        [
            "## 失敗測試或 NOT-REPRODUCIBLE 索引",
            "",
        ]
    )
    if package["failed_tests_or_not_reproducible"]:
        for row in package["failed_tests_or_not_reproducible"]:
            lines.append(
                f"- `{row['node_id']}` — **{row['status']}** — "
                f"{row['claim']} — `{row.get('evidence', '')}`"
            )
    else:
        lines.append("- （空）")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "tool"
    ]["pytest"]["ini_options"]
    addopts = config["addopts"]
    markers = config["markers"]
    assert "--strict-markers" in addopts
    assert "-m 'not integration'" in addopts
    assert any(marker.startswith("integration:") for marker in markers)

    collection_runs = {
        "ALL": run_pytest(
            "--collect-only", "-q", "-o", "addopts=", "--strict-markers"
        ),
        "DEFAULT": run_pytest("--collect-only", "-q"),
        "INTEGRATION": run_pytest(
            "--collect-only",
            "-q",
            "-o",
            "addopts=",
            "--strict-markers",
            "-m",
            "integration",
        ),
    }
    all_ids = node_ids(collection_runs["ALL"][1])
    selected_ids = node_ids(collection_runs["DEFAULT"][1])
    integration_ids = node_ids(collection_runs["INTEGRATION"][1])
    selected = set(selected_ids)
    deselected_ids = [test_id for test_id in all_ids if test_id not in selected]

    assert len(all_ids) == len(set(all_ids))
    assert selected.isdisjoint(deselected_ids)
    assert selected | set(deselected_ids) == set(all_ids)
    assert integration_ids == deselected_ids

    details_command, details_output = run_pytest(
        "--collect-only", "-q", "--deselected-details"
    )
    details = deselection_details(details_output)
    assert sorted(detail["test_id"] for detail in details) == sorted(deselected_ids)
    assert all(
        detail["reason"] == "deselected by -m 'not integration'"
        for detail in details
    )

    allowlist = json.loads(
        (ROOT / "tests" / "deselected_allowlist.json").read_text(encoding="utf-8")
    )
    assert sorted(item["test_id"] for item in allowlist) == sorted(deselected_ids)

    marker_command, marker_output = run_pytest("--markers")
    assert "@pytest.mark.integration:" in marker_output

    # Guard 會對替代測試逐一 subprocess 重跑，預設全集需較長 timeout
    report_command, report_output = run_pytest(
        "-vv",
        "--no-header",
        "--tb=short",
        "--deselected-details",
        "--color=no",
        timeout=600,
    )
    # 去 ANSI，避免 color 殘留導致 " PASSED" 字面比對落空
    report_plain = re.sub(r"\x1b\[[0-9;]*m", "", report_output)
    report_lines = report_plain.splitlines()
    outcomes = {}
    result_lines = {}
    for test_id in selected_ids:
        line = next(
            (
                line
                for line in report_lines
                if line.startswith(f"{test_id} ")
                or line.startswith(f"{test_id}\t")
            ),
            "",
        )
        outcome = next((result for result in RESULTS if f" {result}" in line), "")
        if not outcome and line:
            # 相容 "PASSED [xx%]" 同一行或尾端空白
            for result in RESULTS:
                if result in line:
                    outcome = result
                    break
        assert outcome, (
            f"Missing test result for {test_id}\n"
            f"matched_line={line!r}\n"
            f"report_head=\n" + "\n".join(report_lines[:30])
        )
        outcomes[test_id] = outcome
        result_lines[test_id] = line.strip()

    invocations = {
        "collect_all": subprocess.list2cmdline(collection_runs["ALL"][0]),
        "collect_default": subprocess.list2cmdline(collection_runs["DEFAULT"][0]),
        "collect_integration": subprocess.list2cmdline(
            collection_runs["INTEGRATION"][0]
        ),
        "deselected_details": subprocess.list2cmdline(details_command),
        "default_test_run": subprocess.list2cmdline(report_command),
        "markers": subprocess.list2cmdline(marker_command),
    }

    acceptance_package = build_acceptance_package(
        invocations=invocations,
        all_ids=all_ids,
        selected_ids=selected_ids,
        deselected_ids=deselected_ids,
        allowlist=allowlist,
        outcomes=outcomes,
        result_lines=result_lines,
        details=details,
    )
    # Structural gate: refuse count-only acceptance
    assert acceptance_package["schema"] == "note-filler.deselected-acceptance/v1"
    assert len(acceptance_package["node_ids"]) == 8
    assert all(n["exclusion_reason"].strip() for n in acceptance_package["per_node"])
    assert all(
        n["substitute_individual_results"] for n in acceptance_package["per_node"]
    )
    for path in {
        row["evidence"]
        for rows in NOT_REPRODUCIBLE.values()
        for row in rows
    }:
        assert (ROOT / path).is_file(), f"Missing NOT-REPRODUCIBLE evidence: {path}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = OUTPUT_DIR / "deselected-evidence.md"
    evidence_path.write_text(
        evidence_report(
            all_ids=all_ids,
            selected_ids=selected_ids,
            deselected_ids=deselected_ids,
            integration_ids=integration_ids,
            allowlist=allowlist,
            outcomes=outcomes,
            result_lines=result_lines,
            invocations=invocations,
            acceptance_package=acceptance_package,
        ),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "acceptance-package.json").write_text(
        json.dumps(acceptance_package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "acceptance-package.md").write_text(
        render_acceptance_markdown(acceptance_package),
        encoding="utf-8",
    )

    (OUTPUT_DIR / "collection.txt").write_text(
        "\n".join(
            command_block(label, command, output).rstrip()
            for label, (command, output) in collection_runs.items()
        )
        + "\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "markers.txt").write_text(
        command_block("MARKERS", marker_command, marker_output), encoding="utf-8"
    )
    (OUTPUT_DIR / "test-report.txt").write_text(
        command_block("DEFAULT TEST RUN", report_command, report_output),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "deselected-details.txt").write_text(
        command_block("DESELECTED DETAILS", details_command, details_output),
        encoding="utf-8",
    )

    summary = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "config": {
            "source": "pyproject.toml",
            "addopts": addopts,
            "markers": markers,
        },
        "counts": {
            "collected": len(all_ids),
            "selected": len(selected_ids),
            "deselected": len(deselected_ids),
        },
        "acceptance_mode": "per-node-evidence",
        "acceptance_schema": acceptance_package["schema"],
        "collected": all_ids,
        "selected": selected_ids,
        "deselected": deselected_ids,
        "deselection_details": details,
        "invocations": invocations,
        "outcomes": [
            {"test_id": test_id, "result": outcomes[test_id]}
            for test_id in selected_ids
        ],
        "artifacts": [
            "docs/pytest-audit/collection.txt",
            "docs/pytest-audit/markers.txt",
            "docs/pytest-audit/test-report.txt",
            "docs/pytest-audit/deselected-details.txt",
            "docs/pytest-audit/deselected-evidence.md",
            "docs/pytest-audit/acceptance-package.json",
            "docs/pytest-audit/acceptance-package.md",
        ],
    }
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"COLLECTED={len(all_ids)} SELECTED={len(selected_ids)} "
        f"DESELECTED={len(deselected_ids)}"
    )
    print("ACCEPTANCE_MODE=per-node-evidence")
    print(f"ACCEPTANCE_NODES={len(acceptance_package['node_ids'])}")
    print(
        "FAILED_OR_NR="
        f"{len(acceptance_package['failed_tests_or_not_reproducible'])}"
    )
    print("PYTEST_AUDIT=PASS")


if __name__ == "__main__":
    main()
