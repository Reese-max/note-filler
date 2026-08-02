"""Markdown-only 筆記品質量測的區塊邊界回歸測試。"""
from __future__ import annotations

import json

from note_filler.markdown_quality_metrics import SCHEMA, measure_markdown_quality


def _block(
    argument_id: str,
    claim: str,
    *,
    topic: str,
    angle_tags: list[str],
    qualified_source_ids: list[str],
) -> str:
    metadata = json.dumps(
        {
            "argument_id": argument_id,
            "topic": topic,
            "angle_tags": angle_tags,
            "qualified_source_ids": qualified_source_ids,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    quoted_claim = claim.replace("\n", "\n> ")
    return (
        f"> 【補充】{quoted_claim}\n"
        f"> **角度覆蓋**：quality_metadata={metadata}"
    )


def test_repeated_multiline_claims_keep_their_own_metadata_by_block_order():
    repeated_claim = "相同論點的第一行。\n相同論點的第二行。"
    markdown = "\n\n".join([
        _block(
            "argument:0",
            repeated_claim,
            topic="程序甲",
            angle_tags=["definition"],
            qualified_source_ids=["law:a"],
        ),
        _block(
            "argument:1",
            repeated_claim,
            topic="程序乙",
            angle_tags=["exception"],
            qualified_source_ids=["law:b"],
        ),
        _block(
            "argument:2",
            "程序甲的限制論點。",
            topic="程序甲",
            angle_tags=["limitation"],
            qualified_source_ids=["law:c"],
        ),
    ])

    result = measure_markdown_quality(markdown)

    assert list(result) == [
        "schema",
        "status",
        "reason",
        "argument_count",
        "qualified_argument_count",
        "topic_count",
        "traceability",
        "angles_per_topic",
        "arguments",
    ]
    assert result["schema"] == SCHEMA
    assert result["status"] == "calculated"
    assert result["traceability"] == 1.0
    assert result["angles_per_topic"] == 1.5
    assert result["arguments"] == [
        {
            "argument_id": "argument:0",
            "claim": repeated_claim,
            "qualified_source_ids": ["law:a"],
            "topic": "程序甲",
            "angle_tags": ["definition"],
        },
        {
            "argument_id": "argument:1",
            "claim": repeated_claim,
            "qualified_source_ids": ["law:b"],
            "topic": "程序乙",
            "angle_tags": ["exception"],
        },
        {
            "argument_id": "argument:2",
            "claim": "程序甲的限制論點。",
            "qualified_source_ids": ["law:c"],
            "topic": "程序甲",
            "angle_tags": ["limitation"],
        },
    ]
    assert json.loads(json.dumps(result, ensure_ascii=False)) == result


def test_incomplete_argument_block_returns_fixed_metrics_unavailable_schema():
    result = measure_markdown_quality(
        "> 【補充】缺少品質標記的論點。\n> **角度覆蓋**：angle_tags=definition"
    )

    assert result == {
        "schema": SCHEMA,
        "status": "metrics_unavailable",
        "reason": "incomplete_argument_block",
        "argument_count": 0,
        "qualified_argument_count": 0,
        "topic_count": 0,
        "traceability": None,
        "angles_per_topic": None,
        "arguments": [],
    }
