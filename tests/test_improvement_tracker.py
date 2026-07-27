"""改善追蹤器測試。

驗證依指標分數與功能缺口產生改善優先級報表的功能。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from note_filler.improvement_tracker import (
    ImprovementItem,
    ImprovementReport,
    ImpactAssessment,
    CostAssessment,
    METRIC_THRESHOLD,
    METRIC_PRIORITY_LEVEL,
    generate_improvement_items,
    generate_improvement_report,
    _extract_metric_score,
    _calculate_roi,
)


def _make_polaris_metrics(
    *,
    functional_gap: float = 0.8,
    user_value: float = 0.8,
    source_binding: float = 0.9,
    angle_diversity: float = 0.75,
    delivery_success: float = 1.0,
    traceability: float = 1.0,
) -> dict:
    """建立測試用 polaris_metrics。"""
    overall_score = (
        functional_gap + user_value + source_binding
        + angle_diversity + delivery_success
    ) / 5
    return {
        "schema": "note_filler.polaris_metrics.v1",
        "formula_version": "1.2",
        "overall_status": "good",
        "overall_score": overall_score,
        "functional_gap_score": {
            "score": functional_gap,
            "status": "calculated",
            "threshold": 0.7,
            "passes_threshold": functional_gap >= 0.7,
        },
        "user_value_score": {
            "score": user_value,
            "status": "calculated",
            "threshold": 0.7,
            "passes_threshold": user_value >= 0.7,
        },
        "source_binding_integrity": {
            "score": source_binding,
            "status": "calculated",
            "threshold": 0.8,
            "passes_threshold": source_binding >= 0.8,
        },
        "angle_diversity_index": {
            "score": angle_diversity,
            "status": "calculated",
            "threshold": 0.6,
            "passes_threshold": angle_diversity >= 0.6,
        },
        "delivery_success_rate": {
            "score": delivery_success,
            "status": "calculated",
            "threshold": 0.9,
            "passes_threshold": delivery_success >= 0.9,
        },
        "traceability_score": {
            "score": traceability,
            "status": "calculated",
            "degraded": traceability < 1.0,
            "penalty": 1.0 - traceability,
        },
    }


class TestExtractMetricScore:
    """測試指標分數提取。"""

    def test_extract_valid_score(self):
        metrics = _make_polaris_metrics(functional_gap=0.85)
        score, status = _extract_metric_score(metrics, "functional_gap_score")
        assert score == 0.85
        assert status == "calculated"

    def test_extract_missing_metric(self):
        metrics = _make_polaris_metrics()
        score, status = _extract_metric_score(metrics, "nonexistent_metric")
        assert score is None
        assert status == "missing_data"

    def test_extract_missing_data_status(self):
        metrics = {
            "functional_gap_score": {"status": "missing_data"},
        }
        score, status = _extract_metric_score(metrics, "functional_gap_score")
        assert score is None
        assert status == "missing_data"

    def test_extract_non_numeric_score(self):
        metrics = {
            "functional_gap_score": {"score": "invalid", "status": "calculated"},
        }
        score, status = _extract_metric_score(metrics, "functional_gap_score")
        assert score is None
        assert status == "calculated"


class TestCalculateROI:
    """測試 ROI 計算。"""

    def test_basic_roi(self):
        roi = _calculate_roi(impact_score=3.0, priority_weight=2.0, cost_score=2.0)
        assert roi == pytest.approx(3.0)

    def test_zero_cost(self):
        roi = _calculate_roi(impact_score=3.0, priority_weight=2.0, cost_score=0.0)
        assert roi == 0.0

    def test_high_impact_low_cost(self):
        roi = _calculate_roi(impact_score=3.0, priority_weight=3.0, cost_score=1.0)
        assert roi == pytest.approx(9.0)


class TestGenerateImprovementItems:
    """測試改善項目產生。"""

    def test_all_passing_no_items(self):
        """所有指標通過門檻時不產生改善項目。"""
        metrics = _make_polaris_metrics()
        items = generate_improvement_items(metrics)
        assert items == []

    def test_below_threshold_creates_item(self):
        """低於門檻的指標會產生改善項目。"""
        metrics = _make_polaris_metrics(functional_gap=0.5)
        items = generate_improvement_items(metrics)
        assert len(items) == 1
        assert items[0].metric_name == "functional_gap_score"
        assert items[0].priority_level == "P1"
        assert items[0].gap_to_threshold == pytest.approx(0.2)

    def test_multiple_below_threshold(self):
        """多個指標低於門檻時產生多個改善項目。"""
        metrics = _make_polaris_metrics(
            functional_gap=0.5,
            user_value=0.4,
            source_binding=0.6,
        )
        items = generate_improvement_items(metrics)
        assert len(items) == 3
        metric_names = {item.metric_name for item in items}
        assert "functional_gap_score" in metric_names
        assert "user_value_score" in metric_names
        assert "source_binding_integrity" in metric_names

    def test_sorted_by_roi_desc(self):
        """改善項目按 ROI 降序排列。"""
        metrics = _make_polaris_metrics(
            functional_gap=0.3,
            angle_diversity=0.3,
        )
        items = generate_improvement_items(metrics)
        if len(items) >= 2:
            assert items[0].roi_score >= items[1].roi_score

    def test_missing_data_creates_item(self):
        """缺失資料的指標也會產生改善項目。"""
        metrics = {
            "functional_gap_score": {"status": "missing_data"},
            "user_value_score": {
                "score": 0.8,
                "status": "calculated",
                "threshold": 0.7,
                "passes_threshold": True,
            },
            "source_binding_integrity": {
                "score": 0.9,
                "status": "calculated",
                "threshold": 0.8,
                "passes_threshold": True,
            },
            "angle_diversity_index": {
                "score": 0.75,
                "status": "calculated",
                "threshold": 0.6,
                "passes_threshold": True,
            },
            "delivery_success_rate": {
                "score": 1.0,
                "status": "calculated",
                "threshold": 0.9,
                "passes_threshold": True,
            },
            "traceability_score": {
                "score": 1.0,
                "status": "calculated",
                "degraded": False,
                "penalty": 0.0,
            },
        }
        items = generate_improvement_items(metrics)
        assert len(items) == 1
        assert items[0].metric_name == "functional_gap_score"
        assert items[0].baseline_value == 0.0

    def test_item_has_required_fields(self):
        """改善項目包含所有必要欄位。"""
        metrics = _make_polaris_metrics(functional_gap=0.5)
        items = generate_improvement_items(metrics)
        assert len(items) == 1
        item = items[0]
        assert item.id
        assert item.title
        assert item.priority_level in ("P0", "P1", "P2", "P3")
        assert item.metric_name
        assert isinstance(item.baseline_value, float)
        assert isinstance(item.target_value, float)
        assert isinstance(item.gap_to_threshold, float)
        assert item.responsible_scope
        assert item.impact
        assert item.cost
        assert item.roi_score >= 0
        assert item.acceptance_query
        assert item.status == "pending"
        assert item.created_at

    def test_item_to_dict(self):
        """改善項目可序列化為 dict。"""
        metrics = _make_polaris_metrics(functional_gap=0.5)
        items = generate_improvement_items(metrics)
        d = items[0].to_dict()
        assert isinstance(d, dict)
        assert d["id"] == items[0].id
        assert d["metric_name"] == "functional_gap_score"
        assert "impact_assessment" in d
        assert "cost_assessment" in d

    def test_traceability_below_target(self):
        """追溯性低於目標時產生 P0 改善項目。"""
        metrics = _make_polaris_metrics(traceability=0.5)
        items = generate_improvement_items(metrics)
        trc_items = [i for i in items if i.metric_name == "traceability_score"]
        assert len(trc_items) == 1
        assert trc_items[0].priority_level == "P0"
        assert trc_items[0].target_value == 1.0
        assert trc_items[0].gap_to_threshold == pytest.approx(0.5)


class TestGenerateImprovementReport:
    """測試改善追蹤報告產生。"""

    def test_empty_records(self):
        """空記錄產生空報告。"""
        report = generate_improvement_report([])
        assert report.total_items == 0
        assert report.items == []

    def test_single_record_all_passing(self):
        """單筆記錄所有指標通過。"""
        record = {
            "source_path": "input.txt",
            "note_id": "abc123",
            "polaris_metrics": _make_polaris_metrics(),
        }
        report = generate_improvement_report([record])
        assert report.total_items == 0

    def test_single_record_with_gaps(self):
        """單筆記錄有指標缺口。"""
        record = {
            "source_path": "input.txt",
            "note_id": "abc123",
            "polaris_metrics": _make_polaris_metrics(functional_gap=0.5),
        }
        report = generate_improvement_report([record])
        assert report.total_items == 1
        assert report.by_metric["functional_gap_score"] == 1

    def test_deduplication_across_records(self):
        """跨記錄去重：同一指標只保留最差的改善項目。"""
        records = [
            {
                "source_path": "a.txt",
                "note_id": "a123",
                "polaris_metrics": _make_polaris_metrics(functional_gap=0.5),
            },
            {
                "source_path": "b.txt",
                "note_id": "b456",
                "polaris_metrics": _make_polaris_metrics(functional_gap=0.6),
            },
        ]
        report = generate_improvement_report(records)
        fgs_items = [i for i in report.items if i.metric_name == "functional_gap_score"]
        assert len(fgs_items) == 1
        # 保留最差的（0.5）
        assert fgs_items[0].baseline_value == 0.5

    def test_report_summary_counts(self):
        """報告摘要計數正確。"""
        record = {
            "source_path": "input.txt",
            "note_id": "abc123",
            "polaris_metrics": _make_polaris_metrics(
                functional_gap=0.5,
                user_value=0.4,
                angle_diversity=0.3,
            ),
        }
        report = generate_improvement_report([record])
        assert report.total_items == 3
        assert report.by_priority.get("P1", 0) >= 1
        assert report.by_priority.get("P2", 0) >= 1
        assert all(v == "pending" for v in report.by_status)

    def test_report_to_dict(self):
        """報告可序列化為 dict。"""
        record = {
            "source_path": "input.txt",
            "note_id": "abc123",
            "polaris_metrics": _make_polaris_metrics(functional_gap=0.5),
        }
        report = generate_improvement_report([record])
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "summary" in d
        assert "improvement_items" in d
        assert d["summary"]["total_items"] == 1
        assert d["formula_version"] == "1.2"

    def test_report_json_roundtrip(self):
        """報告可序列化為 JSON 並還原。"""
        record = {
            "source_path": "input.txt",
            "note_id": "abc123",
            "polaris_metrics": _make_polaris_metrics(functional_gap=0.5),
        }
        report = generate_improvement_report([record])
        json_str = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
        data = json.loads(json_str)
        assert data["summary"]["total_items"] == 1
        assert data["improvement_items"][0]["metric_name"] == "functional_gap_score"


class TestImpactAndCostAssessment:
    """測試影響範圍與成本評估。"""

    def test_high_impact_score(self):
        impact = ImpactAssessment(module_impact="高", data_impact="高", user_impact="高")
        assert impact.total_score == pytest.approx(3.0)

    def test_low_impact_score(self):
        impact = ImpactAssessment(module_impact="低", data_impact="低", user_impact="低")
        assert impact.total_score == pytest.approx(1.0)

    def test_mixed_impact_score(self):
        impact = ImpactAssessment(module_impact="高", data_impact="中", user_impact="低")
        assert impact.total_score == pytest.approx(2.0)

    def test_low_cost_score(self):
        cost = CostAssessment(dev_time="低", test_cost="低", risk_level="低", dependency_complexity="低")
        assert cost.total_score == pytest.approx(1.0)

    def test_high_cost_score(self):
        cost = CostAssessment(dev_time="高", test_cost="高", risk_level="高", dependency_complexity="高")
        assert cost.total_score == pytest.approx(3.0)


class TestThresholdDefinitions:
    """測試門檻定義完整性。"""

    def test_all_metrics_have_thresholds(self):
        expected = {
            "traceability_score",
            "functional_gap_score",
            "user_value_score",
            "source_binding_integrity",
            "angle_diversity_index",
            "delivery_success_rate",
        }
        assert set(METRIC_THRESHOLD.keys()) == expected

    def test_all_metrics_have_priority_levels(self):
        expected = {
            "traceability_score",
            "functional_gap_score",
            "user_value_score",
            "source_binding_integrity",
            "angle_diversity_index",
            "delivery_success_rate",
        }
        assert set(METRIC_PRIORITY_LEVEL.keys()) == expected

    def test_thresholds_in_valid_range(self):
        for name, threshold in METRIC_THRESHOLD.items():
            assert 0.0 <= threshold <= 1.0, f"{name} threshold {threshold} out of range"

    def test_priority_levels_valid(self):
        for name, level in METRIC_PRIORITY_LEVEL.items():
            assert level in ("P0", "P1", "P2", "P3"), f"{name} has invalid priority {level}"
