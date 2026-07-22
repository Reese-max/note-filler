"""CI 防漏跑閘：校驗 deselected node ID 白名單、預期數量與替代覆蓋。

單一真實來源：tests/deselected_allowlist.json（清單本身即核准集合與預期數量）。

在以下情況使流程失敗：
1. 實際 deselected 與 allowlist 不一致（未核准的新增排除、數量漂移）。
2. allowlist 中既有測試從全量 collection 消失。
3. 替代覆蓋測試未出現在預設 selected 集合（等同替代覆蓋未執行）。
4. CI workflow 缺少會跑預設（含替代）覆蓋的 job／步驟。
5. 高/中風險（security_risk）測試未在 allowlist 內被可接受核准。

此驗證只做集合稽核與證據輸出，不改變既有 pytest 測試邏輯。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_ID_RE = re.compile(r"^tests/[^:]+::\S+$")
DETAILS_RE = re.compile(r"^(tests/[^:|]+::\S+)\s+\| reason: (.*)$")
AUTHORIZED_REASON = "deselected by -m 'not integration'"
DEFAULT_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
REQUIRED_COVERAGE_JOBS = ("test-pinned", "test-latest")


def _run_collect(*args: str) -> str:
    command = [
        sys.executable,
        "-X",
        "utf8",
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "--color=no",
        *args,
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    output = result.stdout
    if result.stderr:
        output += ("" if not output.endswith("\n") else "") + result.stderr
    if result.returncode:
        raise RuntimeError(
            f"pytest collect failed ({subprocess.list2cmdline(command)}):\n{output}"
        )
    if not output.strip():
        raise RuntimeError(
            f"pytest collect 空輸出（exit={result.returncode}）："
            f"{subprocess.list2cmdline(command)}"
        )
    return output


def _parse_node_ids(text: str) -> list[str]:
    return [
        line.strip().replace("\\", "/")
        for line in text.splitlines()
        if NODE_ID_RE.fullmatch(line.strip())
    ]


def _parse_deselected_details(text: str) -> dict[str, str]:
    details = {}
    for line in text.splitlines():
        match = DETAILS_RE.match(line.strip())
        if match:
            test_id = match.group(1).replace("\\", "/")
            details[test_id] = match.group(2).strip()
    return details


def _load_json(path: Path, *, label: str) -> dict | list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"讀不到 {label} 檔：{path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} JSON 解析失敗：{path}") from exc


def _normalize_allowlist(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        raise RuntimeError("allowlist 檔案格式錯誤：必須是 list")
    for index, row in enumerate(raw):
        if not isinstance(row, dict):
            raise RuntimeError(f"allowlist[{index}] 必須是 object")
        if not row.get("test_id"):
            raise RuntimeError(f"allowlist[{index}] 缺少 test_id")
    return raw  # type: ignore[return-value]


def validate_workflow_coverage_jobs(workflow_text: str) -> list[str]:
    """靜態檢查 CI 仍含會執行替代覆蓋的預設 job。"""
    failures: list[str] = []
    if not workflow_text.strip():
        return ["CI workflow 內容為空，無法確認替代覆蓋 job"]

    for job in REQUIRED_COVERAGE_JOBS:
        # job key at start of line: "  test-pinned:"
        if re.search(rf"(?m)^\s*{re.escape(job)}\s*:", workflow_text) is None:
            failures.append(f"CI workflow 缺少替代覆蓋 job：{job}")

    if "validate_deselection_ci.py" not in workflow_text:
        failures.append(
            "CI workflow 未呼叫 validate_deselection_ci.py（防漏跑檢查未掛載）"
        )

    # 預設 suite 必須以 not integration 選入替代測試
    if "-m \"not integration\"" not in workflow_text and (
        "-m 'not integration'" not in workflow_text
    ):
        failures.append(
            "CI workflow 預設測試未使用 -m \"not integration\"，"
            "替代覆蓋可能不會執行"
        )

    return failures


def evaluate_deselection_policy(
    *,
    all_ids: list[str],
    selected_ids: list[str],
    details: dict[str, str],
    allowlist: list[dict],
    matrix: dict,
    critical_risks: set[str],
    workflow_text: str | None = None,
) -> list[str]:
    """純函式政策評估：回傳失敗訊息列表（空=通過）。"""
    failures: list[str] = []
    allowmap = {row["test_id"]: row for row in allowlist}
    matrix_map = {
        row["node_id"]: row for row in matrix.get("tests", []) if "node_id" in row
    }

    all_set = set(all_ids)
    selected_set = set(selected_ids)
    deselected_ids = sorted(all_set - selected_set)
    allow_ids = [row["test_id"] for row in allowlist]
    allow_sorted = sorted(allowmap)
    expected_count = len(allowlist)

    # 1) 預期數量：allowlist 長度即單一真實來源
    if len(deselected_ids) != expected_count:
        failures.append(
            f"deselected 數量異常：實際 {len(deselected_ids)}，"
            f"allowlist/預期 {expected_count}"
        )

    # 2) allowlist 欄位完整性
    for row in allowlist:
        node_id = row["test_id"]
        if not row.get("collection_reason"):
            failures.append(f"allowlist 缺少 collection_reason：{node_id}")
        substitutes = row.get("substitute_tests")
        if not substitutes:
            failures.append(f"allowlist 缺少 substitute_tests：{node_id}")
        elif not isinstance(substitutes, list):
            failures.append(f"allowlist substitute_tests 格式錯誤：{node_id}")

    # 3) 既有測試消失 vs 未再被 deselected vs 未核准新增排除
    missing_from_collection = sorted(set(allow_sorted) - all_set)
    if missing_from_collection:
        failures.append(f"allowlist 中既有測試已消失：{missing_from_collection}")

    still_collected = set(allow_sorted) & all_set
    no_longer_deselected = sorted(still_collected - set(deselected_ids))
    if no_longer_deselected:
        failures.append(
            f"allowlist 中預期 deselected 未出現（已回到 selected）："
            f"{no_longer_deselected}"
        )

    unexpected = sorted(set(deselected_ids) - set(allow_sorted))
    if unexpected:
        failures.append(f"未核准 deselected：{unexpected}")

    # 向後相容：若集合不一致且上面未細分，保留總覽訊息
    if deselected_ids != allow_sorted and not (
        missing_from_collection or no_longer_deselected or unexpected
    ):
        failures.append(
            f"deselected 集合與 allowlist 不一致："
            f"actual={deselected_ids} allowlist={allow_sorted}"
        )

    # 4) 替代覆蓋必須可收集且落在預設 selected（會被日常 CI job 執行）
    for row in allowlist:
        node_id = row["test_id"]
        substitutes = row.get("substitute_tests") or []
        if not isinstance(substitutes, list):
            continue
        for sub_id in substitutes:
            if not isinstance(sub_id, str) or not sub_id.strip():
                failures.append(
                    f"substitute_tests 含無效 node id：{node_id} -> {sub_id!r}"
                )
                continue
            if sub_id not in all_set:
                failures.append(
                    f"替代覆蓋測試不存在（無法執行）：{node_id} -> {sub_id}"
                )
            elif sub_id not in selected_set:
                failures.append(
                    f"替代覆蓋測試未被預設 selected（等同 job 未執行）："
                    f"{node_id} -> {sub_id}"
                )

    # 5) 關鍵風險仍須核准
    for node_id in deselected_ids:
        row = matrix_map.get(node_id)
        risk = row["security_risk"] if row else "未知"
        approved = allowmap.get(node_id, {}).get("decision") == "acceptable_unexecuted"
        if risk in critical_risks and not approved:
            failures.append(
                f"關鍵/安全測試未核准仍遭排除：{node_id} (security_risk={risk})"
            )

    # 6) 原因摘要完整且與 allowlist 對齊
    for node_id, detail in details.items():
        if node_id not in all_set:
            failures.append(f"deselected-details 含不存在的 node id：{node_id}")
        if node_id not in deselected_ids:
            failures.append(f"deselected-details 含非 deselected node id：{node_id}")
        if not detail.strip():
            failures.append(f"deselected node 無原因摘要：{node_id}")

    for node_id in deselected_ids:
        detail = details.get(node_id)
        if detail is None:
            failures.append(f"缺少 deselected reason：{node_id}")
            continue
        allow_entry = allowmap.get(node_id)
        if allow_entry:
            expected = allow_entry.get("collection_reason")
            if expected is not None and detail != expected:
                failures.append(
                    f"deselected reason 與 allowlist 不符：{node_id} "
                    f"(actual={detail!r}, expected={expected!r})"
                )
        elif detail != AUTHORIZED_REASON:
            failures.append(
                f"deselected reason 未授權 (不在 allowlist)：{node_id} "
                f"(reason={detail!r})"
            )

    # 7) 替代覆蓋 job 靜態掛載
    if workflow_text is not None:
        failures.extend(validate_workflow_coverage_jobs(workflow_text))

    # 去重但保序
    seen: set[str] = set()
    unique: list[str] = []
    for item in failures:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _build_markdown(
    *,
    all_ids: list[str],
    selected_ids: list[str],
    deselected_ids: list[str],
    details: dict[str, str],
    allowlist: list[dict],
    matrix: dict,
    failures: list[str],
) -> str:
    allowmap = {row["test_id"]: row for row in allowlist}
    matrix_tests = {row["node_id"]: row for row in matrix.get("tests", [])}

    lines: list[str] = [
        "## CI Deselected 測試稽核（防漏跑）\n",
        f"- 產生時間: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S%z')}\n",
        f"- 工具: {Path(sys.argv[0]).name}\n\n",
        f"- 全量 collected: {len(all_ids)}\n",
        f"- 預設 selected: {len(selected_ids)}\n",
        f"- 預設 deselected: {len(deselected_ids)}\n",
        f"- allowlist/預期數量: {len(allowlist)}\n\n",
    ]
    lines.append("### 本次 deselected 清單（含原因）\n")
    for index, test_id in enumerate(sorted(deselected_ids), start=1):
        allow = allowmap.get(test_id)
        matrix_row = matrix_tests.get(test_id)
        lines.extend(
            [
                f"{index}. `{test_id}`\n",
                f"   - 採集原因: {details.get(test_id, 'unknown')}\n",
                f"   - 核准決策: {allow.get('decision') if allow else '未核准'}\n",
                f"   - 安全風險: {matrix_row.get('security_risk') if matrix_row else '未在 requirements matrix 中'}\n",
                f"   - 憑證: {allow.get('exclusion_reason', '未提供') if allow else '未提供'}\n",
                f"   - 替代覆蓋數: {len(allow.get('substitute_tests', [])) if allow else 0}\n\n",
            ]
        )

    lines.append("### 失敗原因\n")
    if failures:
        for item in failures:
            lines.append(f"- {item}\n")
    else:
        lines.append("- （無）\n")

    return "".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate pytest deselection anti-leak policy for CI"
    )
    parser.add_argument(
        "--allowlist",
        default=ROOT / "tests" / "deselected_allowlist.json",
        type=Path,
    )
    parser.add_argument(
        "--matrix",
        default=ROOT / "docs" / "pytest-audit" / "requirements-test-coverage-2026-07-19.json",
        type=Path,
    )
    parser.add_argument(
        "--report",
        default=ROOT / "docs" / "pytest-audit" / "deselected-ci-gate.md",
        type=Path,
    )
    parser.add_argument(
        "--workflow",
        default=DEFAULT_WORKFLOW,
        type=Path,
        help="CI workflow 路徑；用於確認替代覆蓋 job 仍掛載",
    )
    parser.add_argument(
        "--skip-workflow-check",
        action="store_true",
        help="略過 CI workflow 靜態檢查（僅供單元測試）",
    )
    parser.add_argument(
        "--critical-risk",
        nargs="+",
        default=["高", "中"],
        help="判定為關鍵/安全測試的 security_risk 等級",
    )
    args = parser.parse_args()

    allowlist = _normalize_allowlist(_load_json(args.allowlist, label="allowlist"))
    matrix = _load_json(args.matrix, label="matrix")
    if not isinstance(matrix, dict):
        raise RuntimeError("matrix 檔案格式錯誤：必須是 object")

    all_ids = _parse_node_ids(_run_collect("-o", "addopts="))
    selected_text = _run_collect("--deselected-details")
    selected_ids = _parse_node_ids(selected_text)
    details = _parse_deselected_details(selected_text)
    deselected_ids = sorted(set(all_ids) - set(selected_ids))

    workflow_text: str | None = None
    if not args.skip_workflow_check:
        try:
            workflow_text = args.workflow.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise RuntimeError(f"讀不到 CI workflow：{args.workflow}") from exc

    failures = evaluate_deselection_policy(
        all_ids=all_ids,
        selected_ids=selected_ids,
        details=details,
        allowlist=allowlist,
        matrix=matrix,
        critical_risks=set(args.critical_risk),
        workflow_text=workflow_text,
    )

    allowmap = {row["test_id"]: row for row in allowlist}
    matrix_map = {row["node_id"]: row for row in matrix.get("tests", [])}

    # 同步輸出，作為 CI log，非僅彙總數字
    print(
        f"[gate] total={len(all_ids)} selected={len(selected_ids)} "
        f"deselected={len(deselected_ids)} expected={len(allowlist)}"
    )
    print("[gate] deselected list:")
    for index, node_id in enumerate(deselected_ids, start=1):
        reason = details.get(node_id)
        risk = matrix_map.get(node_id, {}).get("security_risk", "未知")
        decision = allowmap.get(node_id, {}).get("decision", "未核准")
        subs = allowmap.get(node_id, {}).get("substitute_tests") or []
        print(
            f"  {index:02d}. {node_id} | reason={reason!s} | "
            f"security_risk={risk} | decision={decision} | substitutes={len(subs)}"
        )

    # 替代覆蓋摘要（防漏跑證據）
    all_subs = sorted(
        {
            sub
            for row in allowlist
            for sub in (row.get("substitute_tests") or [])
            if isinstance(sub, str)
        }
    )
    selected_set = set(selected_ids)
    missing_subs = [s for s in all_subs if s not in selected_set]
    print(
        f"[gate] substitute_coverage: unique={len(all_subs)} "
        f"selected={len(all_subs) - len(missing_subs)} "
        f"missing={len(missing_subs)}"
    )
    if missing_subs:
        for sub in missing_subs:
            print(f"  MISSING_SUB: {sub}")

    if failures:
        print("[gate] FAIL: " + " | ".join(failures))
    else:
        print("[gate] PASS: deselected 防漏跑政策核驗通過")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        _build_markdown(
            all_ids=all_ids,
            selected_ids=selected_ids,
            deselected_ids=deselected_ids,
            details=details,
            allowlist=allowlist,
            matrix=matrix,
            failures=failures,
        ),
        encoding="utf-8",
    )

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
