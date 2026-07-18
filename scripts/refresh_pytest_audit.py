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


def command_block(label: str, command: list[str], output: str) -> str:
    return (
        f"===== {label} =====\n"
        f"COMMAND: {subprocess.list2cmdline(command)}\n"
        "EXIT_CODE: 0\n\n"
        f"{output}"
    )


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

    allowlist = json.loads(
        (ROOT / "tests" / "deselected_allowlist.json").read_text(encoding="utf-8")
    )
    assert sorted(item["test_id"] for item in allowlist) == sorted(deselected_ids)

    marker_command, marker_output = run_pytest("--markers")
    assert "@pytest.mark.integration:" in marker_output

    report_command, report_output = run_pytest(
        "-vv", "--no-header", "--tb=short"
    )
    report_lines = report_output.splitlines()
    outcomes = {}
    for test_id in selected_ids:
        line = next(
            (line for line in report_lines if line.startswith(f"{test_id} ")),
            "",
        )
        outcome = next((result for result in RESULTS if f" {result}" in line), "")
        assert outcome, f"Missing test result for {test_id}"
        outcomes[test_id] = outcome

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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
        "outcomes": [
            {"test_id": test_id, "result": outcomes[test_id]}
            for test_id in selected_ids
        ],
        "artifacts": [
            "docs/pytest-audit/collection.txt",
            "docs/pytest-audit/markers.txt",
            "docs/pytest-audit/test-report.txt",
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
