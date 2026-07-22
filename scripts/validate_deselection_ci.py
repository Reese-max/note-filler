"""CI gate for pytest deselected-node policy.

輸出本次執行預設集合下的 deselected 測試清單與排除原因，並在以下情況失敗：

1. 實際 deselected 與 allowlist 不一致。
2. 刪除/新增的 deselected 導致數量異常。
3. 高/中風險（`security_risk`）測試未在 allowlist 內被可接受核准。

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
        "## CI Deselected 測試稽核\n",
        f"- 產生時間: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S%z')}\n",
        f"- 工具: {Path(sys.argv[0]).name}\n\n",
        f"- 全量 collected: {len(all_ids)}\n",
        f"- 預設 selected: {len(selected_ids)}\n",
        f"- 預設 deselected: {len(deselected_ids)}\n",
        f"- allowlist 數: {len(allowlist)}\n\n",
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
                f"   - 憑證: {allow.get('exclusion_reason', '未提供') if allow else '未提供'}\n\n",
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
    parser = argparse.ArgumentParser(description="Validate pytest deselection policy")
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
        "--critical-risk",
        nargs="+",
        default=["高", "中"],
        help="判定為關鍵/安全測試的 security_risk 等級",
    )
    args = parser.parse_args()

    allowlist = _load_json(args.allowlist, label="allowlist")
    matrix = _load_json(args.matrix, label="matrix")

    if not isinstance(allowlist, list):
        raise RuntimeError("allowlist 檔案格式錯誤：必須是 list")
    if not isinstance(matrix, dict):
        raise RuntimeError("matrix 檔案格式錯誤：必須是 object")

    allowmap = {row["test_id"]: row for row in allowlist}
    matrix_map = {row["node_id"]: row for row in matrix.get("tests", [])}

    all_ids = _parse_node_ids(_run_collect("-o", "addopts="))
    selected_text = _run_collect("--deselected-details")
    selected_ids = _parse_node_ids(selected_text)
    details = _parse_deselected_details(selected_text)

    deselected_ids = sorted(set(all_ids) - set(selected_ids))
    failures: list[str] = []

    if len(deselected_ids) != len(allowlist):
        failures.append(
            f"deselected 數量異常：實際 {len(deselected_ids)}，allowlist {len(allowlist)}"
        )

    allow_sorted = sorted(allowmap)
    if deselected_ids != allow_sorted:
        unexpected = sorted(set(deselected_ids) - set(allow_sorted))
        missing = sorted(set(allow_sorted) - set(deselected_ids))
        if unexpected:
            failures.append(f"未核准 deselected：{unexpected}")
        if missing:
            failures.append(f"allowlist 中預期 deselected 未出現：{missing}")

    critical_risks = set(args.critical_risk)
    for node_id in deselected_ids:
        row = matrix_map.get(node_id)
        risk = row["security_risk"] if row else "未知"
        approved = allowmap.get(node_id, {}).get("decision") == "acceptable_unexecuted"
        if risk in critical_risks and not approved:
            failures.append(
                f"關鍵/安全測試未核准仍遭排除：{node_id} (security_risk={risk})"
            )

    for node_id, detail in details.items():
        if node_id not in all_ids:
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
            expected = allow_entry.get("collection_reason", AUTHORIZED_REASON)
            if detail != expected:
                failures.append(
                    f"deselected reason 與 allowlist 不符：{node_id} "
                    f"(actual={detail!r}, expected={expected!r})"
                )
        elif detail != AUTHORIZED_REASON:
            failures.append(
                f"deselected reason 未授權 (不在 allowlist)：{node_id} (reason={detail!r})"
            )

    # 同步輸出，作為 CI log，非僅彙總數字
    print(f"[gate] total={len(all_ids)} selected={len(selected_ids)} deselected={len(deselected_ids)}")
    print("[gate] deselected list:")
    for index, node_id in enumerate(deselected_ids, start=1):
        reason = details.get(node_id)
        risk = matrix_map.get(node_id, {}).get("security_risk", "未知")
        decision = allowmap.get(node_id, {}).get("decision", "未核准")
        print(
            f"  {index:02d}. {node_id} | reason={reason!s} | security_risk={risk} | decision={decision}"
        )

    if failures:
        print("[gate] FAIL: " + " | ".join(failures))
    else:
        print("[gate] PASS: deselected policy 核驗通過")

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
