"""只讀成品 Markdown 的筆記品質量測。

每個 ``【補充】`` 論點區塊必須在同一區塊的 ``**角度覆蓋**`` 行末提供
``quality_metadata=<JSON>``。JSON 固定含 ``argument_id``、``topic``、
``angle_tags`` 與 ``qualified_source_ids``；解析器只按區塊的行序綁定資料，
不會以論點內容搜尋或推測位置。

traceability = 有合格來源的論點數 / 總論點數
angles_per_topic = 各主題角度數的平均

任一論點區塊不完整時，回傳固定 schema 且 ``status=metrics_unavailable``。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCHEMA = "note_filler.markdown_quality_metrics.v2"

_SUPPLEMENT_START = re.compile(
    r"^\s*(?:>\s*)?【補充】(?:⚠待補證\s*)?(?P<claim>.*)$"
)
_QUALITY_METADATA = re.compile(
    r"(?:^|[；：])quality_metadata=(?P<payload>\{.*\})\s*$"
)
_BLOCK_LABELS = (
    "追溯",
    "功能缺口",
    "使用者價值",
    "關聯知識",
    "來源清單",
    "摘要可見",
    "角度覆蓋",
    "論點追溯",
    "論點ID",
    "來源比較",
    "差異分析",
    "適用條件",
    "結論",
    "延伸閱讀",
    "待補證原因",
)


def _result(
    *,
    status: str,
    arguments: list[dict[str, Any]] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    arguments = arguments or []
    if status != "calculated":
        unavailable_reason = reason or "incomplete_argument_block"
        return {
            "schema": SCHEMA,
            "status": "metrics_unavailable",
            "reason": unavailable_reason,
            "argument_count": 0,
            "qualified_argument_count": 0,
            "topic_count": 0,
            "traceability": None,
            "angles_per_topic": None,
            "unqualified_source_argument_count": None,
            "single_angle_topic_count": None,
            "gap_details": [{
                "kind": "topic_assignment_unknown",
                "reason": unavailable_reason,
            }],
            "arguments": [],
        }

    qualified_argument_count = sum(bool(item["qualified_source_ids"]) for item in arguments)
    topic_arguments: dict[str, list[dict[str, Any]]] = {}
    topic_angles: dict[str, list[str]] = {}
    for item in arguments:
        topic = item["topic"]
        topic_arguments.setdefault(topic, []).append(item)
        angles = topic_angles.setdefault(topic, [])
        for angle in item["angle_tags"]:
            if angle not in angles:
                angles.append(angle)

    gap_details = [
        {
            "kind": "unqualified_source_argument",
            "argument_id": item["argument_id"],
            "topic": item["topic"],
            "claim": item["claim"],
        }
        for item in arguments
        if not item["qualified_source_ids"]
    ]
    single_angle_topics = [
        (topic, topic_arguments[topic], angles)
        for topic, angles in topic_angles.items()
        if len(angles) == 1
    ]
    gap_details.extend(
        {
            "kind": "single_angle_topic",
            "topic": topic,
            "argument_ids": [item["argument_id"] for item in topic_items],
            "angle_tags": angles,
        }
        for topic, topic_items, angles in single_angle_topics
    )
    argument_count = len(arguments)
    return {
        "schema": SCHEMA,
        "status": "calculated",
        "reason": None,
        "argument_count": argument_count,
        "qualified_argument_count": qualified_argument_count,
        "topic_count": len(topic_angles),
        "traceability": qualified_argument_count / argument_count,
        "angles_per_topic": sum(map(len, topic_angles.values())) / len(topic_angles),
        "unqualified_source_argument_count": argument_count - qualified_argument_count,
        "single_angle_topic_count": len(single_angle_topics),
        "gap_details": gap_details,
        "arguments": arguments,
    }


def _strip_quote(line: str) -> str:
    return re.sub(r"^\s*>\s?", "", line).strip()


def _is_block_label(line: str) -> bool:
    plain = _strip_quote(line)
    return any(
        plain.startswith((f"**{label}**：", f"{label}："))
        for label in _BLOCK_LABELS
    )


def _metadata_argument(claim_lines: list[str], payload: object) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    argument_id = payload.get("argument_id")
    topic = payload.get("topic")
    angle_tags = payload.get("angle_tags")
    qualified_source_ids = payload.get("qualified_source_ids")
    if not (
        isinstance(argument_id, str)
        and argument_id.strip()
        and isinstance(topic, str)
        and topic.strip()
        and isinstance(angle_tags, list)
        and angle_tags
        and isinstance(qualified_source_ids, list)
    ):
        return None
    if not all(isinstance(item, str) and item.strip() for item in angle_tags):
        return None
    if not all(isinstance(item, str) and item.strip() for item in qualified_source_ids):
        return None
    if len(angle_tags) != len(set(angle_tags)):
        return None
    if len(qualified_source_ids) != len(set(qualified_source_ids)):
        return None
    claim = "\n".join(line for line in claim_lines if line).strip()
    if not claim:
        return None
    return {
        "argument_id": argument_id.strip(),
        "claim": claim,
        "qualified_source_ids": list(qualified_source_ids),
        "topic": topic.strip(),
        "angle_tags": list(angle_tags),
    }


def measure_markdown_quality(markdown: str) -> dict[str, Any]:
    """量測一份成品 Markdown；所有資料只取自傳入的 Markdown 字串。"""
    if not isinstance(markdown, str):
        return _result(status="metrics_unavailable", reason="markdown_not_text")

    arguments: list[dict[str, Any]] = []
    current_claim_lines: list[str] | None = None
    current_metadata: object | None = None
    claim_open = False

    def finish_current() -> bool:
        nonlocal current_claim_lines, current_metadata, claim_open
        if current_claim_lines is None or current_metadata is None:
            return False
        argument = _metadata_argument(current_claim_lines, current_metadata)
        if argument is None or any(
            item["argument_id"] == argument["argument_id"] for item in arguments
        ):
            return False
        arguments.append(argument)
        current_claim_lines = None
        current_metadata = None
        claim_open = False
        return True

    try:
        for raw_line in markdown.splitlines():
            start = _SUPPLEMENT_START.match(raw_line)
            if start:
                if current_claim_lines is not None and not finish_current():
                    return _result(status="metrics_unavailable")
                current_claim_lines = [start.group("claim").strip()]
                current_metadata = None
                claim_open = True
                continue
            if current_claim_lines is None:
                continue

            plain = _strip_quote(raw_line)
            if plain.startswith("**角度覆蓋**："):
                match = _QUALITY_METADATA.search(plain)
                if match is None or current_metadata is not None:
                    return _result(status="metrics_unavailable")
                current_metadata = json.loads(match.group("payload"))
                claim_open = False
                continue
            if _is_block_label(raw_line):
                claim_open = False
                continue
            if claim_open and plain:
                current_claim_lines.append(plain)
    except (json.JSONDecodeError, TypeError, ValueError):
        return _result(status="metrics_unavailable")

    if current_claim_lines is None or not finish_current():
        return _result(status="metrics_unavailable")
    return _result(status="calculated", arguments=arguments)


def measure_markdown_quality_file(path: str | Path) -> dict[str, Any]:
    """唯讀 .md 成品檔並回傳與 ``measure_markdown_quality`` 相同的 JSON schema。"""
    markdown_path = Path(path)
    if markdown_path.suffix.lower() != ".md":
        return _result(status="metrics_unavailable", reason="not_markdown")
    try:
        return measure_markdown_quality(markdown_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return _result(status="metrics_unavailable", reason="markdown_unreadable")
