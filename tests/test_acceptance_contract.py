"""離線自動化驗收：品質公式、缺資料、穩定產出、分類與改善排序。"""
from __future__ import annotations

import json

import pytest
from docx import Document as DocxDocument

from note_filler.improvement_tracker import generate_improvement_items
from note_filler.llm import FakeLLM
from note_filler.metrics import (
    calculate_functional_gap_score,
    calculate_polaris_metrics,
    calculate_source_binding_integrity,
)
from note_filler.pipeline import run_pipeline
from note_filler.value_classifier import classify_note_value
from test_pipeline import FakeLaw, FakeTwinkle


def _argument(
    argument_id: str,
    *,
    functional_gap: str = "原稿未說明行政程序的具體適用要件與限制",
    user_value: str = "讓讀者能理解行政程序並判斷適用情境",
    binding_status: str = "pass",
) -> dict:
    return {
        "argument_id": argument_id,
        "functional_gap": functional_gap,
        "user_value": user_value,
        "source_ids": [f"source:{argument_id}"] if binding_status == "pass" else [],
        "binding_status": binding_status,
        "checks": {
            "at_least_one_source": binding_status == "pass",
            "source_traceable": binding_status == "pass",
            "no_omitted_traces": True,
            "no_extra_traces": True,
            "has_functional_gap": True,
            "has_user_value": True,
            "has_related_knowledge": True,
            "related_knowledge_consistent": True,
        },
        "angle_coverage": {
            "covered_facets": [
                "necessity:functional_gap",
                "necessity:user_value",
            ],
            "effective_angle_count": 1,
        },
    }


def _passing_metrics() -> dict:
    return {
        "traceability_score": {"score": 1.0, "status": "calculated"},
        "functional_gap_score": {"score": 1.0, "status": "calculated"},
        "user_value_score": {"score": 1.0, "status": "calculated"},
        "source_binding_integrity": {"score": 1.0, "status": "calculated"},
        "angle_diversity_index": {"score": 1.0, "status": "calculated"},
        "delivery_success_rate": {"score": 1.0, "status": "calculated"},
    }


def test_quality_formulas_use_the_documented_weights_and_denominator():
    complete = _argument("complete")
    unclear = _argument("unclear", functional_gap="短")

    functional_gap = calculate_functional_gap_score([complete, unclear])
    source_binding = calculate_source_binding_integrity(
        [complete, _argument("pending", binding_status="pending_evidence")]
    )

    assert functional_gap.status == "calculated"
    assert functional_gap.score == pytest.approx(0.875)
    assert {
        name: detail["score"] for name, detail in functional_gap.subscores.items()
    } == {
        "traceability": 1.0,
        "coverage_breadth": 1.0,
        "necessity_clarity": 0.5,
        "decision_support": 1.0,
    }
    assert source_binding.score == pytest.approx(0.5)
    assert source_binding.arguments_pending == 1


def test_missing_sources_preserve_original_and_become_pending_evidence(tmp_path):
    note_path = tmp_path / "source-missing.docx"
    document = DocxDocument()
    document.add_paragraph("行政程序應受正當程序拘束。")
    document.save(str(note_path))
    llm = FakeLLM([
        "admin",
        "正當程序的要件為何？",
        json.dumps([{
            "question": "正當程序的要件為何？",
            "status": "missing",
            "reason": "原稿未說明",
        }], ensure_ascii=False),
        '{"keyword": "正當程序", "law_name": null}',
        "【待補證】沒有可實際引用的來源。",
    ])

    result = run_pipeline(str(note_path), llm, FakeTwinkle([[]]), FakeLaw())
    originals = [segment.text for segment in result.segments if segment.type == "original"]
    supplements = [segment for segment in result.segments if segment.type == "supplement"]

    assert originals == ["行政程序應受正當程序拘束。"]
    assert len(supplements) == 1
    assert supplements[0].text.startswith("【待補證】")
    assert supplements[0].confidence == "pending_evidence"
    assert supplements[0].sources == []
    assert supplements[0].source_ids == []


def test_repeated_metric_output_is_stable_except_for_its_timestamp():
    report = {
        "arguments": [_argument("stable")],
        "angle_coverage_summary": {
            "unique_angle_types": ["definition"],
            "effective_angle_count": 1,
            "duplicate_ratio": 0.0,
        },
    }
    delivery = {
        "primary_note_ready": True,
        "user_channel_sent": True,
        "local_fallback_written": True,
    }
    first = calculate_polaris_metrics(report, delivery).to_dict()
    second = calculate_polaris_metrics(report, delivery).to_dict()

    assert first.pop("calculated_at")
    assert second.pop("calculated_at")
    assert first == second


def test_high_value_and_low_benefit_notes_remain_distinguishable():
    high_value = classify_note_value(
        "high", "high_value", {"overall_score": 0.9},
        {"citation_count": 20, "reuse_count": 10, "completion_rate": 1.0},
    )
    low_benefit = classify_note_value(
        "low", "low_benefit", {"overall_score": 0.9},
        {"citation_count": 0, "reuse_count": 0, "completion_rate": 0.0},
    )

    assert high_value.predicted_label == "high_value"
    assert high_value.is_correct
    assert low_benefit.predicted_label == "low_benefit"
    assert low_benefit.is_correct


def test_improvement_items_sort_blocking_work_before_lower_roi_work():
    metrics = _passing_metrics()
    metrics["traceability_score"] = {"score": 0.0, "status": "calculated"}
    metrics["functional_gap_score"] = {"score": 0.0, "status": "calculated"}
    metrics["angle_diversity_index"] = {"score": 0.0, "status": "calculated"}

    items = generate_improvement_items(metrics)

    assert [item.metric_name for item in items] == [
        "traceability_score",
        "functional_gap_score",
        "angle_diversity_index",
    ]
    assert [item.roi_score for item in items] == sorted(
        (item.roi_score for item in items), reverse=True
    )
