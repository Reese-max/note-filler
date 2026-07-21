"""One-shot evidence runner: collect + execute minimal regression nodeids.

Writes full raw outputs under docs/pytest-audit/. Not part of product runtime.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = Path(r"D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe")
REPORT_DATE = "2026-07-21"
OUT = ROOT / "docs" / "pytest-audit"
OUT.mkdir(parents=True, exist_ok=True)

# Primary newly-established minimal / offline regression nodeids
MINIMAL_CORE = [
    "tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression",
    "tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary",
    "tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates",
    "tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot",
    "tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty",
    "tests/test_twinkle.py::test_search_clamps_similarity_input_to_distance_range",
]


def load_substitute_nodeids() -> list[str]:
    allow = json.loads((ROOT / "tests" / "deselected_allowlist.json").read_text(encoding="utf-8"))
    seen: set[str] = set()
    ordered: list[str] = []
    for row in allow:
        for t in row.get("substitute_tests", []):
            if t not in seen:
                seen.add(t)
                ordered.append(t)
    # newest clamp substitute (commit 39e7c15) not yet in allowlist substitute_tests
    extra = "tests/test_twinkle.py::test_search_clamps_similarity_input_to_distance_range"
    if extra not in seen:
        ordered.append(extra)
    return ordered


def capture(label: str, out_name: str, pytest_args: list[str]) -> dict:
    out_path = OUT / out_name
    cmd = [str(PY), "-X", "utf8", "-m", "pytest", *pytest_args]
    start = datetime.now().astimezone().isoformat(timespec="seconds")
    header = (
        f"=== LABEL: {label} ===\n"
        f"=== CMD: {' '.join(cmd)} ===\n"
        f"=== CWD: {ROOT} ===\n"
        f"=== START: {start} ===\n\n"
    )
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    end = datetime.now().astimezone().isoformat(timespec="seconds")
    body = proc.stdout
    if proc.stderr:
        body = body + "\n--- STDERR ---\n" + proc.stderr
    footer = f"\n=== END: {end} ===\n=== EXIT_CODE: {proc.returncode} ===\n"
    text = header + body + footer
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(out_path)
    print(f"{label}: exit={proc.returncode} -> {out_path.name}", flush=True)
    return {
        "step": label,
        "file": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        "exit_code": proc.returncode,
        "cmd": cmd,
    }


def main() -> int:
    all_nodeids = load_substitute_nodeids()

    list_path = OUT / f"minimal-regression-nodeids-{REPORT_DATE}.txt"
    list_path.write_text(
        "=== MINIMAL_REGRESSION_CORE ({n}) ===\n".format(n=len(MINIMAL_CORE))
        + "\n".join(MINIMAL_CORE)
        + "\n\n=== CORRESPONDING_SUBSTITUTE_AND_NEW_NODEIDS ({n}) ===\n".format(n=len(all_nodeids))
        + "\n".join(all_nodeids)
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {list_path.name}", flush=True)

    results = []
    results.append(
        capture(
            "collect-only minimal regression core",
            f"minimal-regression-collect-core-{REPORT_DATE}.txt",
            ["--collect-only", "-q", "--color=no", *MINIMAL_CORE],
        )
    )
    results.append(
        capture(
            "collect-only corresponding substitute nodeids + clamp",
            f"minimal-regression-collect-all-nodeids-{REPORT_DATE}.txt",
            ["--collect-only", "-q", "--color=no", *all_nodeids],
        )
    )
    results.append(
        capture(
            "run minimal regression core #1",
            f"minimal-regression-run-core-1-{REPORT_DATE}.txt",
            ["-vv", "--tb=short", "--color=no", *MINIMAL_CORE],
        )
    )
    results.append(
        capture(
            "run minimal regression core #2",
            f"minimal-regression-run-core-2-{REPORT_DATE}.txt",
            ["-vv", "--tb=short", "--color=no", *MINIMAL_CORE],
        )
    )
    results.append(
        capture(
            "run all corresponding substitute nodeids + clamp",
            f"minimal-regression-run-all-nodeids-{REPORT_DATE}.txt",
            ["-vv", "--tb=short", "--color=no", *all_nodeids],
        )
    )

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout

    summary = {
        "date": REPORT_DATE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": str(PY),
        "cwd": str(ROOT),
        "git_head_at_run": head,
        "git_status_porcelain_at_run": porcelain,
        "expected_minimal_core": MINIMAL_CORE,
        "expected_all_nodeids": all_nodeids,
        "expected_minimal_core_count": len(MINIMAL_CORE),
        "expected_all_nodeids_count": len(all_nodeids),
        "results": results,
        "all_exit_zero": all(r["exit_code"] == 0 for r in results),
        "substantive_regression_risk": (
            "none_observed_in_minimal_and_substitute_set"
            if all(r["exit_code"] == 0 for r in results)
            else "present_or_command_failure"
        ),
    }
    json_path = OUT / f"minimal-regression-evidence-{REPORT_DATE}.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SUMMARY all_exit_zero={summary['all_exit_zero']} risk={summary['substantive_regression_risk']}", flush=True)
    print(f"JSON={json_path}", flush=True)
    return 0 if summary["all_exit_zero"] else 1


if __name__ == "__main__":
    sys.exit(main())
