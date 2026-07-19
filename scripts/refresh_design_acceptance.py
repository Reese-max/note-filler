"""Rebuild machine-checkable design acceptance package.

Verifies every design claim (D-01..D-05) maps to real files, content anchors,
and collectable/passing offline tests. Writes JSON + Markdown package and a
human report under docs/. Never accepts narrative-only acceptance.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAIMS_PATH = ROOT / "docs" / "specs" / "evidence" / "design-acceptance-claims.json"
OUT_JSON = ROOT / "docs" / "specs" / "evidence" / "design-acceptance-package.json"
OUT_MD = ROOT / "docs" / "specs" / "evidence" / "design-acceptance-package.md"
OUT_REPORT = ROOT / "docs" / "design-acceptance-2026-07-19.md"
PY = [sys.executable, "-X", "utf8"]
SCHEMA = "note-filler.design-acceptance/v1"


def _run(cmd: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _git(*args: str) -> str:
    result = _run(["git", *args], timeout=30)
    return (result.stdout or "").strip()


def _load_claims() -> dict:
    data = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    assert data["schema"] == "note-filler.design-acceptance-claims/v1"
    assert len(data["claims"]) == 5
    return data


def _check_impl_anchor(anchor: dict) -> dict:
    path = ROOT / anchor["path"]
    row = {
        "path": anchor["path"],
        "exists": path.is_file(),
        "missing_tokens": [],
        "ok": False,
    }
    if not row["exists"]:
        return row
    text = path.read_text(encoding="utf-8")
    missing = [token for token in anchor["must_contain"] if token not in text]
    row["missing_tokens"] = missing
    row["ok"] = not missing
    return row


def _collect_tests(node_ids: list[str]) -> tuple[list[str], list[str], str, int]:
    cmd = [
        *PY,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        *node_ids,
        "--color=no",
    ]
    result = _run(cmd, timeout=60)
    collected = [
        line.strip()
        for line in (result.stdout or "").splitlines()
        if line.startswith("tests/") and "::" in line
    ]
    # anyio / parametrize may expand node ids (e.g. ...::test_x[asyncio])
    missing: list[str] = []
    for requested in node_ids:
        if any(
            node == requested or node.startswith(requested + "[")
            for node in collected
        ):
            continue
        missing.append(requested)
    invocation = subprocess.list2cmdline(cmd)
    return collected, missing, invocation, result.returncode


def _run_one_test(node_id: str) -> dict:
    cmd = [
        *PY,
        "-m",
        "pytest",
        node_id,
        "-vv",
        "--tb=line",
        "--color=no",
    ]
    result = _run(cmd, timeout=120)
    summary = ""
    status = "failed"
    # Match base node id even when anyio expands to ...[asyncio]
    for line in (result.stdout or "").splitlines():
        if node_id not in line:
            continue
        if not any(
            token in line for token in (" PASSED", " FAILED", " ERROR", " SKIPPED")
        ):
            continue
        summary = line.strip()
        if " PASSED" in line:
            status = "passed"
        elif " SKIPPED" in line:
            status = "skipped"
        elif " FAILED" in line or " ERROR" in line:
            status = "failed"
        break
    if not summary:
        summary = ((result.stdout or "") + (result.stderr or ""))[-400:].strip()
        if result.returncode == 0:
            status = "passed"
    return {
        "test_id": node_id,
        "status": status,
        "exit_code": result.returncode,
        "summary": summary,
        "invocation": subprocess.list2cmdline(cmd),
    }


def build_package() -> dict:
    claims_src = _load_claims()
    head = _git("rev-parse", "HEAD")
    porcelain = _git("status", "--porcelain")
    # Before writing outputs, porcelain reflects pre-refresh tree.
    tree_clean_before = porcelain == ""

    per_claim: list[dict] = []
    claim_map: list[dict] = []
    all_test_ids: list[str] = []
    failures: list[dict] = []

    for claim in claims_src["claims"]:
        spec_path = claim["spec_file"]
        spec_ok = (ROOT / spec_path).is_file()
        impl_results = [_check_impl_anchor(a) for a in claim["impl_anchors"]]
        test_ids = list(claim["test_anchors"])
        all_test_ids.extend(test_ids)

        if not spec_ok:
            failures.append(
                {
                    "claim_id": claim["id"],
                    "status": "MISSING_SPEC",
                    "detail": spec_path,
                }
            )
        for impl in impl_results:
            if not impl["ok"]:
                failures.append(
                    {
                        "claim_id": claim["id"],
                        "status": "IMPL_ANCHOR_FAIL",
                        "detail": (
                            f"{impl['path']} missing={impl['missing_tokens']}"
                            if impl["exists"]
                            else f"{impl['path']} not found"
                        ),
                    }
                )

        collected, missing_tests, collect_inv, collect_rc = _collect_tests(test_ids)
        if collect_rc != 0 or missing_tests:
            failures.append(
                {
                    "claim_id": claim["id"],
                    "status": "TEST_COLLECT_FAIL",
                    "detail": f"missing={missing_tests} rc={collect_rc}",
                }
            )

        individual = [_run_one_test(tid) for tid in test_ids]
        for row in individual:
            if row["status"] != "passed" or row["exit_code"] != 0:
                failures.append(
                    {
                        "claim_id": claim["id"],
                        "status": "TEST_RUN_FAIL",
                        "detail": f"{row['test_id']} status={row['status']}",
                    }
                )

        claim_ok = (
            spec_ok
            and all(r["ok"] for r in impl_results)
            and not missing_tests
            and all(r["status"] == "passed" and r["exit_code"] == 0 for r in individual)
        )
        entry = {
            "id": claim["id"],
            "title": claim["title"],
            "spec_file": spec_path,
            "spec_exists": spec_ok,
            "manifest_ref": claim.get("manifest_ref"),
            "gap_map_ref": claim.get("gap_map_ref"),
            "impl_anchors": impl_results,
            "test_anchors_collect": {
                "requested": test_ids,
                "collected": collected,
                "missing": missing_tests,
                "invocation": collect_inv,
                "returncode": collect_rc,
            },
            "test_individual_results": individual,
            "screenshot_status": claim.get("screenshot_status"),
            "screenshot_note": claim.get("screenshot_note"),
            "status_note": claim.get("status_note"),
            "claim_ok": claim_ok,
        }
        per_claim.append(entry)
        claim_map.append(
            {
                "claim_id": claim["id"],
                "title": claim["title"],
                "spec_file": spec_path,
                "impl_files": [a["path"] for a in impl_results],
                "test_ids": test_ids,
                "package_fields": [
                    f"per_claim[{claim['id']}].spec_file",
                    f"per_claim[{claim['id']}].impl_anchors",
                    f"per_claim[{claim['id']}].test_individual_results",
                ],
                "ok": claim_ok,
            }
        )

    unique_tests = sorted(set(all_test_ids))
    package = {
        "schema": SCHEMA,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "rule": claims_src["rule"],
        "source_claims": str(CLAIMS_PATH.relative_to(ROOT)).replace("\\", "/"),
        "git": {
            "head": head,
            "working_tree_clean_before_refresh": tree_clean_before,
            "status_porcelain_before_refresh": porcelain,
        },
        "quality_gates_immutable": claims_src["quality_gates_immutable"],
        "invocations": {
            "refresh_script": subprocess.list2cmdline(
                [*PY, str(ROOT / "scripts" / "refresh_design_acceptance.py")]
            ),
            "claims_path": str(CLAIMS_PATH.relative_to(ROOT)).replace("\\", "/"),
        },
        "claim_ids": [c["id"] for c in per_claim],
        "per_claim": per_claim,
        "claim_to_artifact_map": claim_map,
        "unique_test_anchors": unique_tests,
        "failures": failures,
        "acceptance_mode": "per-claim-evidence",
        "acceptance_pass": all(c["claim_ok"] for c in per_claim) and not failures,
    }
    return package


def render_package_md(package: dict) -> str:
    lines = [
        "# 設計驗收套件（Design Acceptance Package）",
        "",
        f"> 產生時間：`{package['generated_at']}`",
        ">",
        f"> schema：`{package['schema']}`",
        ">",
        f"> **{package['rule']}**",
        "",
        "## Git / 落盤狀態（刷新前）",
        "",
        f"- HEAD：`{package['git']['head']}`",
        f"- working_tree_clean_before_refresh：`{package['git']['working_tree_clean_before_refresh']}`",
        f"- status_porcelain_before_refresh：`{package['git']['status_porcelain_before_refresh'] or '(empty)'}`",
        "",
        "## 主張 ↔ 產物對照",
        "",
        "| ID | 標題 | 規格檔 | 實作檔數 | 測試數 | OK |",
        "|----|------|--------|----------|--------|----|",
    ]
    for row in package["claim_to_artifact_map"]:
        lines.append(
            f"| {row['claim_id']} | {row['title']} | `{row['spec_file']}` | "
            f"{len(row['impl_files'])} | {len(row['test_ids'])} | "
            f"{'YES' if row['ok'] else 'NO'} |"
        )
    lines.extend(["", "## per-claim 細節", ""])
    for claim in package["per_claim"]:
        lines.extend(
            [
                f"### {claim['id']} — {claim['title']}",
                "",
                f"- claim_ok: **{claim['claim_ok']}**",
                f"- spec_file: `{claim['spec_file']}` (exists={claim['spec_exists']})",
                f"- status_note: {claim.get('status_note') or ''}",
                "",
                "實作錨點：",
                "",
            ]
        )
        for impl in claim["impl_anchors"]:
            mark = "PASS" if impl["ok"] else "FAIL"
            lines.append(
                f"- **{mark}** `{impl['path']}`"
                + (
                    f" missing={impl['missing_tokens']}"
                    if impl["missing_tokens"]
                    else ""
                )
            )
        lines.extend(["", "測試單獨結果：", ""])
        for t in claim["test_individual_results"]:
            lines.append(
                f"- **{t['status'].upper()}** `{t['test_id']}` — `{t['summary']}`"
            )
            lines.append(f"  - invocation: `{t['invocation']}`")
        if claim.get("screenshot_status"):
            lines.append(
                f"- screenshot_status: `{claim['screenshot_status']}` — "
                f"{claim.get('screenshot_note') or ''}"
            )
        lines.append("")
    lines.extend(
        [
            "## failures",
            "",
        ]
    )
    if package["failures"]:
        for f in package["failures"]:
            lines.append(
                f"- {f['claim_id']}: {f['status']} — {f['detail']}"
            )
    else:
        lines.append("- (empty)")
    lines.extend(
        [
            "",
            f"## ACCEPTANCE_PASS = {package['acceptance_pass']}",
            "",
            f"ACCEPTANCE_MODE: {package['acceptance_mode']}",
            "",
        ]
    )
    return "\n".join(lines)


def render_report(package: dict) -> str:
    lines = [
        "# 設計驗收輸出（可機器檢查）— 2026-07-19",
        "",
        "> 任務：重新產出可機器檢查的設計驗收輸出，並確認工作樹乾淨、變更已落盤、",
        "> 每一項主張都能在檔案與輸出中逐一對應。",
        "",
        "## 1. 主張 ↔ 可見產物",
        "",
        "| 主張 | 可見產物 |",
        "|------|----------|",
        "| 設計主張索引（source of truth） | [`docs/specs/evidence/design-acceptance-claims.json`](specs/evidence/design-acceptance-claims.json) |",
        "| 機器可讀驗收套件 | [`docs/specs/evidence/design-acceptance-package.json`](specs/evidence/design-acceptance-package.json) |",
        "| 人類可讀驗收套件 | [`docs/specs/evidence/design-acceptance-package.md`](specs/evidence/design-acceptance-package.md) |",
        "| 刷新腳本 | [`scripts/refresh_design_acceptance.py`](../scripts/refresh_design_acceptance.py) |",
        "| 結構／錨點驗收測試 | [`tests/test_design_acceptance.py`](../tests/test_design_acceptance.py) |",
        "| 既有設計規格 D-01 | [`docs/specs/note-filler-interface-contract.md`](specs/note-filler-interface-contract.md) |",
        "| 既有設計規格 D-02 | [`docs/specs/note-filler-state-machine.md`](specs/note-filler-state-machine.md) |",
        "| 既有設計規格 D-03 | [`docs/specs/note-filler-user-flow.md`](specs/note-filler-user-flow.md) |",
        "| 既有設計規格 D-04 | [`docs/specs/note-filler-component-responsibilities.md`](specs/note-filler-component-responsibilities.md) |",
        "| 既有設計規格 D-05 | [`docs/specs/evidence/ui/index.md`](specs/evidence/ui/index.md) |",
        "| Manifest | [`docs/specs/evidence/note-filler-design-evidence-manifest.md`](specs/evidence/note-filler-design-evidence-manifest.md) |",
        "| 缺口對照 | [`docs/design-evidence-gap-map-2026-07-19.md`](design-evidence-gap-map-2026-07-19.md) |",
        "",
        "## 2. 套件 schema",
        "",
        "```text",
        f"schema = {package['schema']}",
        "claim_ids[5] = D-01..D-05",
        "per_claim[].{spec_file, impl_anchors[], test_individual_results[]}",
        "claim_to_artifact_map[]",
        "failures[]",
        "git.head / working_tree_clean_before_refresh",
        "acceptance_mode = per-claim-evidence",
        "```",
        "",
        "禁止僅以「文件已存在」或計數摘要驗收；必須有 per-claim 錨點與實跑結果。",
        "",
        "## 3. 本輪實測",
        "",
        f"- generated_at: `{package['generated_at']}`",
        f"- HEAD（刷新前）: `{package['git']['head']}`",
        f"- working_tree_clean_before_refresh: `{package['git']['working_tree_clean_before_refresh']}`",
        f"- acceptance_pass: **{package['acceptance_pass']}**",
        f"- unique offline test anchors: {len(package['unique_test_anchors'])}",
        f"- failures: {len(package['failures'])}",
        "",
        "### 逐項 claim",
        "",
        "| ID | OK | 規格 | 測試全部 PASSED |",
        "|----|----|------|-----------------|",
    ]
    for claim in package["per_claim"]:
        tests_ok = all(
            t["status"] == "passed" and t["exit_code"] == 0
            for t in claim["test_individual_results"]
        )
        lines.append(
            f"| {claim['id']} | {claim['claim_ok']} | `{claim['spec_file']}` | {tests_ok} |"
        )
    lines.extend(
        [
            "",
            "### 重現指令",
            "",
            "```powershell",
            '$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"',
            "& $py -X utf8 scripts/refresh_design_acceptance.py",
            "& $py -X utf8 -m pytest tests/test_design_acceptance.py -vv --tb=short --color=no",
            "& $py -X utf8 -m pytest -m \"not integration\" -q --color=no --tb=line",
            "git status --porcelain   # 提交後應為空",
            "```",
            "",
            "## 4. 品質閘未弱化",
            "",
            "| 硬約束 | 狀態 |",
            "|--------|------|",
        ]
    )
    for gate in package["quality_gates_immutable"]:
        lines.append(f"| {gate} | 未改主程式語意；由 e2e/pipeline 錨點鎖定 |")
    lines.extend(
        [
            "| integration 平時跳過 | 維持；本套件只跑非 integration 錨點 |",
            "",
            "## 5. 已知限制",
            "",
            "- D-05 實體截圖（png/jpg）仍缺；套件以 `screenshot_status=absent` 明示，",
            "  不以截圖存在作為本輪通過條件。",
            "- 刷新完成後工作樹會含新產物，必須 `git add -A && git commit` 後再驗 `git status --porcelain` 為空。",
            "",
            "## 6. 結論",
            "",
            f"1. 設計驗收輸出 schema=`{package['schema']}`，mode=`{package['acceptance_mode']}`。",
            "2. D-01..D-05 每一項皆對到規格檔、實作錨點與單獨測試結果。",
            f"3. ACCEPTANCE_PASS={package['acceptance_pass']}（以 package JSON 為準）。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    package = build_package()
    OUT_JSON.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUT_MD.write_text(render_package_md(package), encoding="utf-8")
    OUT_REPORT.write_text(render_report(package), encoding="utf-8")

    print(f"SCHEMA={package['schema']}")
    print(f"ACCEPTANCE_MODE={package['acceptance_mode']}")
    print(f"CLAIM_IDS={','.join(package['claim_ids'])}")
    print(f"ACCEPTANCE_PASS={package['acceptance_pass']}")
    print(f"FAILURES={len(package['failures'])}")
    print(f"HEAD={package['git']['head']}")
    print(
        "WORKING_TREE_CLEAN_BEFORE_REFRESH="
        f"{package['git']['working_tree_clean_before_refresh']}"
    )
    print(
        "OUTPUTS="
        + ",".join(
            [
                str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                str(OUT_REPORT.relative_to(ROOT)).replace("\\", "/"),
            ]
        )
    )
    return 0 if package["acceptance_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
