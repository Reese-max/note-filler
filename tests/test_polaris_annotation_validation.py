"""標註測試資料集驗證：驗證北極星指標能有效區分高價值與低效益筆記。

本測試載入人工標註的測試資料集，計算北極星品質指標，驗證：
1. 高價值筆記的指標分數高於門檻
2. 低效益筆記的指標分數低於門檻
3. 兩類筆記的指標差距顯著
4. 整體品質判定符合預期
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from note_filler.metrics import (
    FUNCTIONAL_GAP_THRESHOLD,
    USER_VALUE_THRESHOLD,
    SOURCE_BINDING_THRESHOLD,
    calculate_polaris_metrics,
)


def _load_annotation_data(fixture_path: Path) -> dict:
    """載入標註資料並轉換為 binding_report 格式。"""
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    
    # 建構模擬的 binding_report
    arguments = []
    for arg in data["arguments"]:
        argument = {
            "argument_id": arg["argument_id"],
            "argument_index": arg["argument_index"],
            "argument_text": arg["argument_text"],
            "summary": arg["argument_text"],
            "functional_gap": arg["functional_gap"],
            "user_value": arg["user_value"],
            "related_knowledge": arg["related_knowledge"],
            "source_ids": arg["sources"],
            "source_count": len(arg["sources"]),
            "binding_status": arg["binding_status"],
            "cardinality": arg["cardinality"],
            "confidence": "verified" if arg["binding_status"] == "pass" else "pending_evidence",
            "checks": arg["checks"],
            "angle_coverage": arg["angle_coverage"],
            "angle_tags": arg["angle_coverage"]["covered_facets"],
            "valid_angle_count": 1,
            "deduped_angle_count": 1,
            "duplicate_angles": [],
            "angle_field_issues": [],
        }
        arguments.append(argument)
    
    # 建構 angle_coverage_summary
    unique_angle_types = sorted({
        arg["angle_coverage"]["angle_type"] for arg in arguments
    })
    
    binding_report = {
        "schema": "note_filler.binding_report.v1",
        "source_path": f"annotation:{data['note_id']}",
        "argument_count": len(arguments),
        "summary": {
            "one_to_one": sum(1 for arg in arguments if arg["cardinality"] == "one_to_one"),
            "one_to_many": sum(1 for arg in arguments if arg["cardinality"] == "one_to_many"),
            "none": sum(1 for arg in arguments if arg["cardinality"] == "none"),
            "pass": sum(1 for arg in arguments if arg["binding_status"] == "pass"),
            "fail": sum(1 for arg in arguments if arg["binding_status"] == "fail"),
            "pending_evidence": sum(1 for arg in arguments if arg["binding_status"] == "pending_evidence"),
            "all_sourced_arguments_ok": all(
                arg["binding_status"] == "pass" for arg in arguments if arg["source_ids"]
            ) if any(arg["source_ids"] for arg in arguments) else True,
            "all_arguments_ok": all(arg["binding_status"] == "pass" for arg in arguments) if arguments else True,
        },
        "arguments": arguments,
        "source_usage": {},
        "angle_coverage_summary": {
            "unique_angle_types": unique_angle_types,
            "covered_facets_union": sorted({
                facet for arg in arguments for facet in arg["angle_coverage"]["covered_facets"]
            }),
            "duplicate_pairs": [],
            "synonym_pairs": [],
            "argument_count_with_angles": len(arguments),
            "effective_angle_count": len(arguments),
            "excluded_angle_count": 0,
            "duplicate_ratio": 0.0,
            "required_effective_angle_count": 2,
            "max_duplicate_ratio": 0.5,
            "has_sufficient_angles": len(arguments) >= 2,
            "has_acceptable_duplicate_ratio": True,
            "coverage_ok": len(arguments) >= 2,
        },
    }
    
    return binding_report


def _calculate_metrics_from_annotation(fixture_path: Path):
    """從標註資料計算北極星指標。"""
    binding_report = _load_annotation_data(fixture_path)
    delivery_status = {
        "primary_note_ready": True,
        "user_channel_sent": True,
        "local_fallback_written": True,
    }
    return calculate_polaris_metrics(binding_report, delivery_status)


class TestHighValueAnnotation:
    """驗證高價值筆記標註資料的指標表現。"""
    
    def test_high_value_note_001_metrics(self):
        """高價值筆記 001：所有核心指標應通過門檻。"""
        fixture_path = Path(__file__).parent / "fixtures" / "polaris_annotation" / "high_value" / "note_001.json"
        metrics = _calculate_metrics_from_annotation(fixture_path)
        
        # 驗證功能缺口分數
        assert metrics.functional_gap_score.status == "calculated"
        assert metrics.functional_gap_score.score >= FUNCTIONAL_GAP_THRESHOLD, (
            f"高價值筆記 001 功能缺口分數 {metrics.functional_gap_score.score:.3f} 應 >= {FUNCTIONAL_GAP_THRESHOLD}"
        )
        assert metrics.functional_gap_score.passes_threshold is True
        
        # 驗證使用者價值分數
        assert metrics.user_value_score.status == "calculated"
        assert metrics.user_value_score.score >= USER_VALUE_THRESHOLD, (
            f"高價值筆記 001 使用者價值分數 {metrics.user_value_score.score:.3f} 應 >= {USER_VALUE_THRESHOLD}"
        )
        assert metrics.user_value_score.passes_threshold is True
        
        # 驗證來源綁定完整性
        assert metrics.source_binding_integrity.status == "calculated"
        assert metrics.source_binding_integrity.score >= SOURCE_BINDING_THRESHOLD, (
            f"高價值筆記 001 來源綁定完整性 {metrics.source_binding_integrity.score:.3f} 應 >= {SOURCE_BINDING_THRESHOLD}"
        )
        assert metrics.source_binding_integrity.passes_threshold is True
        
        # 驗證整體品質判定
        assert metrics.overall_status in ("excellent", "good"), (
            f"高價值筆記 001 整體品質應為 excellent 或 good，實際為 {metrics.overall_status}"
        )
        assert metrics.core_metrics_pass_count >= 3, (
            f"高價值筆記 001 應至少通過 3 個核心指標，實際通過 {metrics.core_metrics_pass_count} 個"
        )
    
    def test_high_value_note_002_metrics(self):
        """高價值筆記 002：所有核心指標應通過門檻。"""
        fixture_path = Path(__file__).parent / "fixtures" / "polaris_annotation" / "high_value" / "note_002.json"
        metrics = _calculate_metrics_from_annotation(fixture_path)
        
        # 驗證功能缺口分數
        assert metrics.functional_gap_score.status == "calculated"
        assert metrics.functional_gap_score.score >= FUNCTIONAL_GAP_THRESHOLD, (
            f"高價值筆記 002 功能缺口分數 {metrics.functional_gap_score.score:.3f} 應 >= {FUNCTIONAL_GAP_THRESHOLD}"
        )
        assert metrics.functional_gap_score.passes_threshold is True
        
        # 驗證使用者價值分數
        assert metrics.user_value_score.status == "calculated"
        assert metrics.user_value_score.score >= USER_VALUE_THRESHOLD, (
            f"高價值筆記 002 使用者價值分數 {metrics.user_value_score.score:.3f} 應 >= {USER_VALUE_THRESHOLD}"
        )
        assert metrics.user_value_score.passes_threshold is True
        
        # 驗證來源綁定完整性
        assert metrics.source_binding_integrity.status == "calculated"
        assert metrics.source_binding_integrity.score >= SOURCE_BINDING_THRESHOLD, (
            f"高價值筆記 002 來源綁定完整性 {metrics.source_binding_integrity.score:.3f} 應 >= {SOURCE_BINDING_THRESHOLD}"
        )
        assert metrics.source_binding_integrity.passes_threshold is True
        
        # 驗證整體品質判定
        assert metrics.overall_status in ("excellent", "good"), (
            f"高價值筆記 002 整體品質應為 excellent 或 good，實際為 {metrics.overall_status}"
        )
        assert metrics.core_metrics_pass_count >= 3, (
            f"高價值筆記 002 應至少通過 3 個核心指標，實際通過 {metrics.core_metrics_pass_count} 個"
        )


class TestLowBenefitAnnotation:
    """驗證低效益筆記標註資料的指標表現。"""
    
    def test_low_benefit_note_001_metrics(self):
        """低效益筆記 001：核心指標應低於門檻。"""
        fixture_path = Path(__file__).parent / "fixtures" / "polaris_annotation" / "low_benefit" / "note_001.json"
        metrics = _calculate_metrics_from_annotation(fixture_path)
        
        # 驗證功能缺口分數
        assert metrics.functional_gap_score.status == "calculated"
        assert metrics.functional_gap_score.score < FUNCTIONAL_GAP_THRESHOLD, (
            f"低效益筆記 001 功能缺口分數 {metrics.functional_gap_score.score:.3f} 應 < {FUNCTIONAL_GAP_THRESHOLD}"
        )
        assert metrics.functional_gap_score.passes_threshold is False
        assert metrics.functional_gap_score.arguments_with_concrete_gap == 0
        
        # 驗證使用者價值分數
        assert metrics.user_value_score.status == "calculated"
        assert metrics.user_value_score.score < USER_VALUE_THRESHOLD, (
            f"低效益筆記 001 使用者價值分數 {metrics.user_value_score.score:.3f} 應 < {USER_VALUE_THRESHOLD}"
        )
        assert metrics.user_value_score.passes_threshold is False
        assert metrics.user_value_score.arguments_with_clear_value == 0
        
        # 驗證來源綁定完整性
        assert metrics.source_binding_integrity.status == "calculated"
        assert metrics.source_binding_integrity.score < SOURCE_BINDING_THRESHOLD, (
            f"低效益筆記 001 來源綁定完整性 {metrics.source_binding_integrity.score:.3f} 應 < {SOURCE_BINDING_THRESHOLD}"
        )
        assert metrics.source_binding_integrity.passes_threshold is False
        
        # 驗證整體品質判定
        assert metrics.overall_status in ("poor", "acceptable"), (
            f"低效益筆記 001 整體品質應為 poor 或 acceptable，實際為 {metrics.overall_status}"
        )
    
    def test_low_benefit_note_002_metrics(self):
        """低效益筆記 002：核心指標應低於門檻。"""
        fixture_path = Path(__file__).parent / "fixtures" / "polaris_annotation" / "low_benefit" / "note_002.json"
        metrics = _calculate_metrics_from_annotation(fixture_path)
        
        # 驗證功能缺口分數
        assert metrics.functional_gap_score.status == "calculated"
        assert metrics.functional_gap_score.score < FUNCTIONAL_GAP_THRESHOLD, (
            f"低效益筆記 002 功能缺口分數 {metrics.functional_gap_score.score:.3f} 應 < {FUNCTIONAL_GAP_THRESHOLD}"
        )
        assert metrics.functional_gap_score.passes_threshold is False
        assert metrics.functional_gap_score.arguments_with_concrete_gap == 0
        
        # 驗證使用者價值分數
        assert metrics.user_value_score.status == "calculated"
        assert metrics.user_value_score.score < USER_VALUE_THRESHOLD, (
            f"低效益筆記 002 使用者價值分數 {metrics.user_value_score.score:.3f} 應 < {USER_VALUE_THRESHOLD}"
        )
        assert metrics.user_value_score.passes_threshold is False
        assert metrics.user_value_score.arguments_with_clear_value == 0
        
        # 驗證來源綁定完整性
        assert metrics.source_binding_integrity.status == "calculated"
        assert metrics.source_binding_integrity.score < SOURCE_BINDING_THRESHOLD, (
            f"低效益筆記 002 來源綁定完整性 {metrics.source_binding_integrity.score:.3f} 應 < {SOURCE_BINDING_THRESHOLD}"
        )
        assert metrics.source_binding_integrity.passes_threshold is False
        
        # 驗證整體品質判定
        assert metrics.overall_status in ("poor", "acceptable"), (
            f"低效益筆記 002 整體品質應為 poor 或 acceptable，實際為 {metrics.overall_status}"
        )


class TestAnnotationDiscrimination:
    """驗證標註資料集的區分能力。"""
    
    def test_high_vs_low_value_discrimination(self):
        """驗證高價值與低效益筆記的指標差距顯著。"""
        high_001_path = Path(__file__).parent / "fixtures" / "polaris_annotation" / "high_value" / "note_001.json"
        low_001_path = Path(__file__).parent / "fixtures" / "polaris_annotation" / "low_benefit" / "note_001.json"
        
        high_metrics = _calculate_metrics_from_annotation(high_001_path)
        low_metrics = _calculate_metrics_from_annotation(low_001_path)
        
        # 驗證功能缺口分數差距
        fg_gap = high_metrics.functional_gap_score.score - low_metrics.functional_gap_score.score
        assert fg_gap >= 0.5, (
            f"功能缺口分數差距應 >= 0.5，實際差距 {fg_gap:.3f}"
        )
        
        # 驗證使用者價值分數差距
        uv_gap = high_metrics.user_value_score.score - low_metrics.user_value_score.score
        assert uv_gap >= 0.5, (
            f"使用者價值分數差距應 >= 0.5，實際差距 {uv_gap:.3f}"
        )
        
        # 驗證來源綁定完整性差距
        sb_gap = high_metrics.source_binding_integrity.score - low_metrics.source_binding_integrity.score
        assert sb_gap >= 0.5, (
            f"來源綁定完整性差距應 >= 0.5，實際差距 {sb_gap:.3f}"
        )
        
        # 驗證通過門檻的指標數量差距
        pass_count_gap = high_metrics.core_metrics_pass_count - low_metrics.core_metrics_pass_count
        assert pass_count_gap >= 2, (
            f"通過門檻的指標數量差距應 >= 2，實際差距 {pass_count_gap}"
        )
        
        # 驗證整體品質判定差距
        assert high_metrics.overall_status in ("excellent", "good"), (
            "高價值筆記整體品質應為 excellent 或 good"
        )
        assert low_metrics.overall_status in ("poor", "acceptable"), (
            "低效益筆記整體品質應為 poor 或 acceptable"
        )
    
    def test_annotation_data_integrity(self):
        """驗證標註資料的完整性與一致性。"""
        high_001_path = Path(__file__).parent / "fixtures" / "polaris_annotation" / "high_value" / "note_001.json"
        low_001_path = Path(__file__).parent / "fixtures" / "polaris_annotation" / "low_benefit" / "note_001.json"
        
        # 驗證高價值筆記資料完整性
        with open(high_001_path, encoding="utf-8") as f:
            high_data = json.load(f)
        
        assert high_data.get("ground_truth", high_data["category"]) == "high_value"
        assert len(high_data["arguments"]) >= 2
        for arg in high_data["arguments"]:
            assert len(arg["functional_gap"]) >= 10, "高價值筆記功能缺口應 >= 10 字元"
            assert any(kw in arg["user_value"] for kw in ["讀者", "說明", "理解"]), "高價值筆記使用者價值應包含關鍵詞"
            assert len(arg["sources"]) >= 1, "高價值筆記應有至少 1 個來源"
            assert arg["binding_status"] == "pass", "高價值筆記綁定狀態應為 pass"
        
        # 驗證低效益筆記資料完整性
        with open(low_001_path, encoding="utf-8") as f:
            low_data = json.load(f)
        
        assert low_data.get("ground_truth", low_data["category"]) == "low_benefit"
        assert len(low_data["arguments"]) >= 2
        for arg in low_data["arguments"]:
            assert len(arg["functional_gap"]) < 10, "低效益筆記功能缺口應 < 10 字元"
            assert not any(kw in arg["user_value"] for kw in ["讀者", "說明", "理解"]), "低效益筆記使用者價值不應包含關鍵詞"
            assert arg["binding_status"] in ("fail", "pending_evidence"), "低效益筆記綁定狀態應為 fail 或 pending_evidence"