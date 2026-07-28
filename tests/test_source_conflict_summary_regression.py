"""來源衝突摘要的機械可解析回歸測試。"""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from note_filler.binding_report import build_binding_report, parse_binding_report
from note_filler.correction import assemble_correction
from note_filler.gap import Gap
from note_filler.parse import Document, Paragraph
from note_filler.retrieve.models import Source
from note_filler.verify import cross_validate
from note_filler.write import WrittenSupplement


# 驗收端獨立硬編碼契約；禁止改成匯入 production 常數，否則同步漂移不會失敗。
EXPECTED_V1_ARGUMENT_KEY_ORDER = (
    "argument_index",
    "argument_id",
    "segment_index",
    "argument_text",
    "summary",
    "confidence",
    "cardinality",
    "source_count",
    "source_ids",
    "trace_source_ids",
    "source_fragments",
    "citation_spans",
    "source_id_field",
    "checks",
    "binding_status",
    "binding_ok",
    "functional_gap",
    "user_value",
    "related_knowledge",
    "angle_coverage",
    "extended_readings",
    "extended_readings_status",
    "pending_evidence_reason",
    "openable_links_count",
    "openable_links_status",
    "openable_links_incomplete_reason",
    "angle_tags",
    "valid_angle_count",
    "deduped_angle_count",
    "duplicate_angles",
    "angle_field_issues",
)
EXPECTED_CONFLICT_SUMMARY_FIELD_ORDER = (
    "source_conflicts",
    "source_preference_reason",
    "applicable_conditions",
    "readable_conclusion",
)
EXPECTED_V2_ARGUMENT_KEY_ORDER = (
    EXPECTED_V1_ARGUMENT_KEY_ORDER + EXPECTED_CONFLICT_SUMMARY_FIELD_ORDER
)
EXPECTED_SOURCE_CONFLICT_KEY_ORDER = (
    "kind",
    "status",
    "source_ids",
    "detector",
    "rule",
    "message",
)
EXPECTED_SOURCE_PREFERENCE_KEY_ORDER = (
    "status",
    "preferred_source_id",
    "reason_code",
    "detail",
)
EXPECTED_APPLICABLE_CONDITIONS_KEY_ORDER = ("status", "items")


def _source(source_id: str, title: str, content: str) -> Source:
    return Source(
        id=source_id,
        title=title,
        url=f"https://law.example.test/{source_id}",
        level="A",
        content=content,
        fetched_date="2026-07-28",
        doc_date=None,
        distance=0.1,
    )


def _product(*, single_actual_source: bool = False):
    original_text = "原稿逐字保留。"
    conflict_sources = [
        _source("law:allow", "來源甲", "申請人得提出申請。"),
        _source("law:deny", "來源乙", "申請人不得提出申請。"),
    ]
    ordinary_source = _source("law:definition", "來源丙", "行政程序應依法進行。")
    used_conflict_sources = conflict_sources[:1] if single_actual_source else conflict_sources
    conflict_gap = Gap("申請資格是否成立？", "missing", "原稿未說明申請資格")
    ordinary_gap = Gap("程序依據為何？", "missing", "原稿未說明程序依據")
    conflict_text = (
        "現有資料對申請資格互有衝突。[^1]"
        if single_actual_source
        else "現有資料對申請資格互有衝突。[^1][^2]"
    )
    return assemble_correction(
        Document("input/note.txt", (Paragraph(0, original_text),), original_text),
        [conflict_gap, ordinary_gap],
        {
            conflict_gap.question: conflict_sources,
            ordinary_gap.question: [ordinary_source],
        },
        {
            conflict_gap.question: WrittenSupplement(
                conflict_text, [source.id for source in used_conflict_sources]
            ),
            ordinary_gap.question: WrittenSupplement(
                "行政程序應依法進行。[^1]", [ordinary_source.id]
            ),
        },
        {
            conflict_gap.question: cross_validate(
                conflict_gap.question, conflict_sources
            ),
            ordinary_gap.question: cross_validate(
                ordinary_gap.question, [ordinary_source]
            ),
        },
    )


def _parsed_report(*, single_actual_source: bool = False) -> dict:
    raw = build_binding_report(_product(single_actual_source=single_actual_source))
    return parse_binding_report(json.loads(json.dumps(raw, ensure_ascii=False)))


def test_source_conflict_summary_is_extractable_per_argument_id():
    report = _parsed_report()
    arguments = {
        argument["argument_id"]: argument for argument in report["arguments"]
    }

    assert report["schema"] == "note_filler.binding_report.v2"
    assert list(arguments) == ["argument:0", "argument:1"]
    conflict = arguments["argument:0"]["source_conflicts"]
    assert len(conflict) == 1
    assert tuple(conflict[0]) == EXPECTED_SOURCE_CONFLICT_KEY_ORDER
    assert conflict[0]["source_ids"] == ["law:allow", "law:deny"]
    assert conflict[0]["source_ids"] == arguments["argument:0"]["source_ids"]
    assert arguments["argument:0"]["source_preference_reason"]["status"] == "not_selected"
    assert arguments["argument:1"]["source_conflicts"] == []
    assert arguments["argument:1"]["source_preference_reason"]["status"] == "not_applicable"
    assert {
        argument_id: argument["source_conflicts"]
        for argument_id, argument in arguments.items()
        if argument["source_conflicts"]
    } == {"argument:0": conflict}


def test_source_conflict_summary_uses_independently_locked_field_order():
    report = _parsed_report()

    for argument in report["arguments"]:
        assert tuple(argument) == EXPECTED_V2_ARGUMENT_KEY_ORDER
        assert tuple(argument["source_preference_reason"]) == (
            EXPECTED_SOURCE_PREFERENCE_KEY_ORDER
        )
        assert tuple(argument["applicable_conditions"]) == (
            EXPECTED_APPLICABLE_CONDITIONS_KEY_ORDER
        )

    drifted = deepcopy(report)
    argument = drifted["arguments"][0]
    drifted["arguments"][0] = {
        "argument_id": argument["argument_id"],
        **{
            key: argument[key]
            for key in EXPECTED_V2_ARGUMENT_KEY_ORDER
            if key != "argument_id"
        },
    }
    with pytest.raises(ValueError, match="欄位順序漂移"):
        parse_binding_report(drifted)


def test_single_actual_source_with_conflict_note_stays_parseable():
    product = _product(single_actual_source=True)
    supplement = next(seg for seg in product.segments if seg.type == "supplement")

    assert supplement.conflict_note
    assert [source.id for source in supplement.sources] == ["law:allow"]
    argument = _parsed_report(single_actual_source=True)["arguments"][0]
    assert argument["source_ids"] == ["law:allow"]
    assert argument["source_conflicts"] == []
    assert argument["source_preference_reason"] == {
        "status": "not_applicable",
        "preferred_source_id": None,
        "reason_code": "insufficient_conflict_sources",
        "detail": "實際引用來源不足兩個，未建立來源衝突摘要。",
    }


def test_v1_report_remains_parseable_after_conflict_summary_upgrade():
    legacy = deepcopy(_parsed_report())
    legacy["schema"] = "note_filler.binding_report.v1"
    legacy["arguments"] = [
        {key: argument[key] for key in EXPECTED_V1_ARGUMENT_KEY_ORDER}
        for argument in legacy["arguments"]
    ]

    parsed = parse_binding_report(legacy)
    assert parsed["schema"] == "note_filler.binding_report.v1"
    assert all(
        tuple(argument) == EXPECTED_V1_ARGUMENT_KEY_ORDER
        for argument in parsed["arguments"]
    )
