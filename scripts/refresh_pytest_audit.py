"""Refresh committed pytest collection, marker, and test-run evidence."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "pytest-audit"
PYTEST = [sys.executable, "-X", "utf8", "-m", "pytest"]
RESULTS = ("PASSED", "SKIPPED", "XFAIL", "XPASS", "FAILED", "ERROR")


def run_pytest(*args: str) -> tuple[list[str], str]:
    command = [*PYTEST, *args]
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
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
) -> str:
    """Render the committed code-to-output chain for every deselected test."""
    allowlist_ids = [item["test_id"] for item in allowlist]
    assert sorted(allowlist_ids) == sorted(deselected_ids)
    lines = [
        "# Deselected 可接受未執行追溯證據",
        "",
        "> 本檔由 `scripts/refresh_pytest_audit.py` 產生；每一項都同時列出",
        "> 排除程式碼 anchor、替代測試程式碼 anchor，以及該替代測試在本次測試輸出中的結果。",
        "",
        "## 集合判定",
        "",
        f"- 全量 collection：`{len(all_ids)}`",
        f"- 預設 selected：`{len(selected_ids)}`",
        f"- `deselected`：`{len(deselected_ids)}`",
        f"- `integration` 集合：`{len(integration_ids)}`",
        f"- allowlist 與實際 `deselected` 完全相等：`{sorted(allowlist_ids) == sorted(deselected_ids)}`",
        "- collection 原始輸出：[`collection.txt`](collection.txt)",
        "- 預設測試原始輸出：[`test-report.txt`](test-report.txt)",
        "- deselection 詳情原始輸出：[`deselected-details.txt`](deselected-details.txt)",
        "",
        "## 逐項證據鏈",
        "",
    ]
    for index, item in enumerate(allowlist, start=1):
        lines.extend(
            [
                f"### {index}. `{item['test_id']}`",
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
        lines.extend(
            [
                "- 替代測試證據：",
            ]
        )
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
        lines.extend(
            [
                f"- 未覆蓋邊界：{item['coverage_gap']}",
                "- 結論：替代測試已保護確定性程式契約；剩餘邊界屬真實模型／外部服務，故可接受未執行。",
                "",
            ]
        )
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

    report_command, report_output = run_pytest(
        "-vv", "--no-header", "--tb=short", "--deselected-details"
    )
    report_lines = report_output.splitlines()
    outcomes = {}
    result_lines = {}
    for test_id in selected_ids:
        line = next(
            (line for line in report_lines if line.startswith(f"{test_id} ")),
            "",
        )
        outcome = next((result for result in RESULTS if f" {result}" in line), "")
        assert outcome, f"Missing test result for {test_id}"
        outcomes[test_id] = outcome
        result_lines[test_id] = line.strip()

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
        ),
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
        "collected": all_ids,
        "selected": selected_ids,
        "deselected": deselected_ids,
        "deselection_details": details,
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
        ],
    }
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"COLLECTED={len(all_ids)} SELECTED={len(selected_ids)} "
        f"DESELECTED={len(deselected_ids)}"
    )
    print("PYTEST_AUDIT=PASS")


if __name__ == "__main__":
    main()
