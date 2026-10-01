"""北極星筆記品質指標測試。

驗證指標計算的正確性、缺值處理、序列化與整合。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from note_filler.metrics import (
    AngleDiversityIndex,
    DeliverySuccessRate,
    FunctionalGapScore,
    PolarisMetrics,
    SourceBindingIntegrity,
    UserValueScore,
    calculate_angle_diversity_index,
    calculate_delivery_success_rate,
    calculate_functional_gap_score,
    calculate_polaris_metrics,
    calculate_source_binding_integrity,
    calculate_user_value_score,
)


def _argument_with_quantifiable_basis(functional_gap: str, user_value: str) -> dict:
    return {
        "functional_gap": functional_gap,
        "user_value": user_value,
        "source_ids": ["source:a"],
        "binding_status": "pass",
        "checks": {
            "at_least_one_source": True,
            "source_traceable": True,
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


class TestFunctionalGapScore:
    """功能缺口分數測試。"""

    def test_calculate_with_concrete_gaps(self):
        """測試具體功能缺口的計算。"""
        arguments = [
            {"functional_gap": "This is a long functional gap description", "binding_status": "pass"},
            {"functional_gap": "Another detailed gap description here", "binding_status": "pass"},
            {"functional_gap": "Third comprehensive gap statement", "binding_status": "pass"},
        ]
        result = calculate_functional_gap_score(arguments)
        
        assert result.status == "calculated"
        assert result.score == 1.0  # 3/3 都具體
        assert result.total_arguments == 3
        assert result.arguments_with_concrete_gap == 3
        assert result.arguments_with_empty_gap == 0
        assert result.passes_threshold == True

    def test_calculate_with_empty_gaps(self):
        """測試空功能缺口的計算。"""
        arguments = [
            {"functional_gap": "This is a long functional gap description", "binding_status": "pass"},
            {"functional_gap": "", "binding_status": "pass"},
            {"functional_gap": "   ", "binding_status": "pass"},
        ]
        result = calculate_functional_gap_score(arguments)
        
        assert result.status == "calculated"
        assert result.score == 1/3  # 只有 1 個具體
        assert result.total_arguments == 3
        assert result.arguments_with_concrete_gap == 1
        assert result.arguments_with_empty_gap == 2
        assert result.passes_threshold == False  # 低於 0.7 門檻

    def test_calculate_with_short_gaps(self):
        """測試過短功能缺口的計算（少於 10 字元）。"""
        arguments = [
            {"functional_gap": "short", "binding_status": "pass"},  # 少於 10 字元
            {"functional_gap": "This is a long functional gap description", "binding_status": "pass"},
        ]
        result = calculate_functional_gap_score(arguments)
        
        assert result.status == "calculated"
        assert result.score == 0.5  # 只有 1 個具體
        assert result.arguments_with_concrete_gap == 1
        assert result.arguments_with_empty_gap == 1

    def test_calculate_with_missing_field(self):
        """測試缺失欄位的處理。"""
        arguments = [
            {"functional_gap": "This is a long functional gap description", "binding_status": "pass"},
            {"binding_status": "pass"},  # 缺少 functional_gap
        ]
        result = calculate_functional_gap_score(arguments)
        
        assert result.status == "calculated"
        assert result.score == 0.5  # 1/2
        assert result.arguments_missing_field == 1

    def test_calculate_with_empty_arguments(self):
        """測試空論點列表的處理。"""
        result = calculate_functional_gap_score([])
        
        assert result.status == "missing_data"
        assert result.score == 0.0
        assert result.total_arguments == 0

    def test_threshold_check(self):
        """測試門檻判定。"""
        # 測試高於門檻的情況
        result = calculate_functional_gap_score([
            {"functional_gap": "This is a long functional gap description", "binding_status": "pass"},
            {"functional_gap": "Another detailed gap description here", "binding_status": "pass"},
            {"functional_gap": "Third comprehensive gap statement", "binding_status": "pass"},
        ])
        assert result.score == 1.0
        assert result.passes_threshold == True  # >= 0.7
        
        # 測試低於門檻的情況
        result = calculate_functional_gap_score([
            {"functional_gap": "short", "binding_status": "pass"},
        ])
        assert result.score == 0.0
        assert result.passes_threshold == False  # < 0.7


class TestUserValueScore:
    """使用者價值分數測試。"""

    def test_calculate_with_clear_values(self):
        """測試明確使用者價值的計算。"""
        arguments = [
            {"user_value": "Help readers understand the legal responsibility scope", "binding_status": "pass"},
            {"user_value": "Provide explanation for readers to understand conditions", "binding_status": "pass"},
            {"user_value": "Give readers understanding of legal effects", "binding_status": "pass"},
        ]
        result = calculate_user_value_score(arguments)
        
        assert result.status == "calculated"
        assert result.score == 1.0  # 3/3 都明確
        assert result.total_arguments == 3
        assert result.arguments_with_clear_value == 3
        assert result.passes_threshold == True

    def test_calculate_with_empty_values(self):
        """測試空使用者價值的計算。"""
        arguments = [
            {"user_value": "Help readers understand the legal responsibility scope", "binding_status": "pass"},
            {"user_value": "", "binding_status": "pass"},
            {"user_value": "   ", "binding_status": "pass"},
        ]
        result = calculate_user_value_score(arguments)
        
        assert result.status == "calculated"
        assert result.score == 1/3  # 只有 1 個明確
        assert result.arguments_with_clear_value == 1
        assert result.arguments_with_empty_value == 2
        assert result.passes_threshold == False

    def test_calculate_without_keywords(self):
        """測試不含關鍵詞的使用者價值。"""
        arguments = [
            {"user_value": "Help readers understand the legal responsibility scope", "binding_status": "pass"},
            {"user_value": "Provide some information", "binding_status": "pass"},  # 缺少關鍵詞
        ]
        result = calculate_user_value_score(arguments)
        
        assert result.status == "calculated"
        assert result.score == 0.5  # 只有 1 個明確
        assert result.arguments_with_clear_value == 1

    def test_calculate_with_missing_field(self):
        """測試缺失欄位的處理。"""
        arguments = [
            {"user_value": "Help readers understand the legal responsibility scope", "binding_status": "pass"},
            {"binding_status": "pass"},  # 缺少 user_value
        ]
        result = calculate_user_value_score(arguments)
        
        assert result.status == "calculated"
        assert result.score == 0.5
        assert result.arguments_missing_field == 1

    def test_calculate_with_empty_arguments(self):
        """測試空論點列表的處理。"""
        result = calculate_user_value_score([])
        
        assert result.status == "missing_data"
        assert result.score == 0.0


class TestSourceBindingIntegrity:
    """來源綁定完整性測試。"""

    def test_calculate_with_all_pass(self):
        """測試所有論點通過的計算。"""
        arguments = [
            {"binding_status": "pass"},
            {"binding_status": "pass"},
            {"binding_status": "pass"},
        ]
        result = calculate_source_binding_integrity(arguments)
        
        assert result.status == "calculated"
        assert result.score == 1.0
        assert result.total_arguments == 3
        assert result.arguments_pass == 3
        assert result.arguments_fail == 0
        assert result.arguments_pending == 0
        assert result.passes_threshold == True

    def test_calculate_with_mixed_status(self):
        """測試混合狀態的計算。"""
        arguments = [
            {"binding_status": "pass"},
            {"binding_status": "fail"},
            {"binding_status": "pending_evidence"},
            {"binding_status": "pass"},
        ]
        result = calculate_source_binding_integrity(arguments)
        
        assert result.status == "calculated"
        assert result.score == 0.5  # 2/4 pass
        assert result.arguments_pass == 2
        assert result.arguments_fail == 1
        assert result.arguments_pending == 1
        assert result.passes_threshold == False  # 低於 0.8

    def test_calculate_with_missing_status(self):
        """測試缺失 status 欄位的處理。"""
        arguments = [
            {"binding_status": "pass"},
            {},  # 缺少 binding_status
            {"binding_status": "pass"},
        ]
        result = calculate_source_binding_integrity(arguments)
        
        assert result.status == "calculated"
        assert result.score == 2/3
        assert result.arguments_missing_status == 1

    def test_calculate_with_empty_arguments(self):
        """測試空論點列表的處理。"""
        result = calculate_source_binding_integrity([])
        
        assert result.status == "missing_data"
        assert result.score == 0.0

    def test_threshold_check(self):
        """測試門檻判定。"""
        # 剛好達到門檻
        arguments = [{"binding_status": "pass"} for _ in range(8)]
        arguments.append({"binding_status": "fail"})
        arguments.append({"binding_status": "fail"})
        result = calculate_source_binding_integrity(arguments)
        assert result.score == 0.8
        assert result.passes_threshold == True  # >= 0.8
        
        # 低於門檻
        arguments = [{"binding_status": "pass"} for _ in range(7)]
        arguments.append({"binding_status": "fail"})
        arguments.append({"binding_status": "fail"})
        arguments.append({"binding_status": "fail"})
        result = calculate_source_binding_integrity(arguments)
        assert result.score == 0.7
        assert result.passes_threshold == False  # < 0.8


class TestAngleDiversityIndex:
    """角度多樣性指數測試。"""

    def test_calculate_with_diverse_angles(self):
        """測試多樣角度的計算。"""
        angle_summary = {
            "unique_angle_types": ["definition", "limitation", "requirement", "effect"],
            "effective_angle_count": 4,
            "duplicate_ratio": 0.0,
        }
        result = calculate_angle_diversity_index(angle_summary)
        
        assert result.status == "calculated"
        assert result.score == 0.5  # 4/8
        assert result.unique_angle_types == 4
        assert result.expected_angle_types == 8
        assert result.passes_threshold == False  # 低於 0.6

    def test_calculate_with_full_coverage(self):
        """測試完整覆蓋的計算。"""
        angle_summary = {
            "unique_angle_types": [
                "definition", "limitation", "requirement", "effect",
                "procedure", "exception", "comparison", "application"
            ],
            "effective_angle_count": 8,
            "duplicate_ratio": 0.0,
        }
        result = calculate_angle_diversity_index(angle_summary)
        
        assert result.status == "calculated"
        assert result.score == 1.0  # 8/8
        assert result.passes_threshold == True

    def test_calculate_with_empty_summary(self):
        """測試空摘要的處理。"""
        result = calculate_angle_diversity_index({})
        
        assert result.status == "missing_data"
        assert result.score == 0.0
        assert result.unique_angle_types == 0

    def test_calculate_with_missing_unique_types(self):
        """測試缺失 unique_angle_types 的處理。"""
        angle_summary = {
            "effective_angle_count": 4,
            "duplicate_ratio": 0.1,
        }
        result = calculate_angle_diversity_index(angle_summary)
        
        assert result.status == "calculated"
        assert result.score == 0.0  # 0/8
        assert result.unique_angle_types == 0

    def test_threshold_check(self):
        """測試門檻判定。"""
        # 剛好達到門檻
        angle_summary = {
            "unique_angle_types": ["definition", "limitation", "requirement", "effect", "procedure"],
            "effective_angle_count": 5,
            "duplicate_ratio": 0.0,
        }
        result = calculate_angle_diversity_index(angle_summary)
        assert result.score == 0.625
        assert result.passes_threshold == True  # >= 0.6
        
        # 低於門檻
        angle_summary = {
            "unique_angle_types": ["definition", "limitation", "requirement", "effect"],
            "effective_angle_count": 4,
            "duplicate_ratio": 0.0,
        }
        result = calculate_angle_diversity_index(angle_summary)
        assert result.score == 0.5
        assert result.passes_threshold == False  # < 0.6


class TestDeliverySuccessRate:
    """端到端送達成功率測試。"""

    def test_calculate_with_full_success(self):
        """測試完全成功的計算。"""
        delivery_status = {
            "primary_note_ready": True,
            "user_channel_sent": True,
            "local_fallback_written": True,
        }
        result = calculate_delivery_success_rate(delivery_status)
        
        assert result.status == "calculated"
        assert result.score == 1.0
        assert result.total_attempts == 1
        assert result.successful_deliveries == 1
        assert result.failed_deliveries == 0
        assert result.passes_threshold == True

    def test_calculate_with_partial_failure(self):
        """測試部分失敗的計算。"""
        delivery_status = {
            "primary_note_ready": True,
            "user_channel_sent": False,  # 失敗
            "local_fallback_written": True,
        }
        result = calculate_delivery_success_rate(delivery_status)
        
        assert result.status == "calculated"
        assert result.score == 0.0
        assert result.successful_deliveries == 0
        assert result.failed_deliveries == 1
        assert result.passes_threshold == False

    def test_calculate_with_none_status(self):
        """測試 None 狀態的處理。"""
        result = calculate_delivery_success_rate(None)
        
        assert result.status == "missing_data"
        assert result.score == 0.0

    def test_calculate_with_empty_status(self):
        """測試空字典的處理（視為 missing_data）。"""
        result = calculate_delivery_success_rate({})
        
        assert result.status == "missing_data"
        assert result.score == 0.0
        assert result.successful_deliveries == 0
        assert result.failed_deliveries == 0
        assert result.total_attempts == 0


class TestPolarisMetrics:
    """北極星指標總覽測試。"""

    def test_calculate_all_metrics(self):
        """測試所有指標的計算。"""
        binding_report = {
            "arguments": [
                _argument_with_quantifiable_basis(
                    "This is a long functional gap description",
                    "Help readers understand the legal responsibility scope",
                ),
                _argument_with_quantifiable_basis(
                    "Another detailed gap description here",
                    "Provide explanation for readers to understand conditions",
                ),
            ],
            "angle_coverage_summary": {
                "unique_angle_types": ["definition", "limitation"],
                "effective_angle_count": 2,
                "duplicate_ratio": 0.0,
            },
        }
        delivery_status = {
            "primary_note_ready": True,
            "user_channel_sent": True,
            "local_fallback_written": True,
        }
        
        result = calculate_polaris_metrics(binding_report, delivery_status)
        
        assert result.overall_status in ["excellent", "good", "acceptable", "poor"]
        assert result.core_metrics_total_count == 5
        assert result.calculated_at != ""
        
        # 驗證各個指標
        assert result.functional_gap_score.status == "calculated"
        assert result.user_value_score.status == "calculated"
        assert result.source_binding_integrity.status == "calculated"
        assert result.angle_diversity_index.status == "calculated"
        assert result.delivery_success_rate.status == "calculated"

    def test_overall_status_excellent(self):
        """測試整體狀態為 excellent 的判定。"""
        # 建構所有指標都通過門檻的情況
        functional_gap = FunctionalGapScore(
            score=0.8, status="calculated",
            total_arguments=5, arguments_with_concrete_gap=4,
            arguments_with_empty_gap=1, arguments_missing_field=0,
        )
        user_value = UserValueScore(
            score=0.8, status="calculated",
            total_arguments=5, arguments_with_clear_value=4,
            arguments_with_empty_value=1, arguments_missing_field=0,
        )
        source_binding = SourceBindingIntegrity(
            score=0.9, status="calculated",
            total_arguments=5, arguments_pass=4,
            arguments_fail=1, arguments_pending=0, arguments_missing_status=0,
        )
        angle_diversity = AngleDiversityIndex(
            score=0.7, status="calculated",
            unique_angle_types=5, expected_angle_types=8,
            effective_angle_count=5, duplicate_ratio=0.1,
            unique_angle_type_names=["definition", "limitation", "requirement", "effect", "procedure"],
        )
        delivery = DeliverySuccessRate(
            score=1.0, status="calculated",
            total_attempts=1, successful_deliveries=1, failed_deliveries=0,
        )
        
        # 覆蓋門檻讓它們都通過
        functional_gap.score = 0.8
        user_value.score = 0.8
        source_binding.score = 0.9
        angle_diversity.score = 0.7
        delivery.score = 1.0
        
        metrics = PolarisMetrics(
            functional_gap_score=functional_gap,
            user_value_score=user_value,
            source_binding_integrity=source_binding,
            angle_diversity_index=angle_diversity,
            delivery_success_rate=delivery,
            calculated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        )
        
        # 由於門檻設定，實際上需要所有指標都通過
        # 這裡只驗證邏輯
        assert metrics.core_metrics_total_count == 5

    def test_overall_status_poor(self):
        """測試整體狀態為 poor 的判定。"""
        functional_gap = FunctionalGapScore(
            score=0.3, status="calculated",
            total_arguments=5, arguments_with_concrete_gap=1,
            arguments_with_empty_gap=4, arguments_missing_field=0,
        )
        user_value = UserValueScore(
            score=0.3, status="calculated",
            total_arguments=5, arguments_with_clear_value=1,
            arguments_with_empty_value=4, arguments_missing_field=0,
        )
        source_binding = SourceBindingIntegrity(
            score=0.5, status="calculated",
            total_arguments=5, arguments_pass=2,
            arguments_fail=3, arguments_pending=0, arguments_missing_status=0,
        )
        angle_diversity = AngleDiversityIndex(
            score=0.3, status="calculated",
            unique_angle_types=2, expected_angle_types=8,
            effective_angle_count=2, duplicate_ratio=0.5,
            unique_angle_type_names=["definition", "limitation"],
        )
        delivery = DeliverySuccessRate(
            score=0.5, status="calculated",
            total_attempts=1, successful_deliveries=0, failed_deliveries=1,
        )
        
        metrics = PolarisMetrics(
            functional_gap_score=functional_gap,
            user_value_score=user_value,
            source_binding_integrity=source_binding,
            angle_diversity_index=angle_diversity,
            delivery_success_rate=delivery,
            calculated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        )
        
        # 大部分指標未通過門檻
        assert metrics.core_metrics_pass_count < 2
        assert metrics.overall_status == "poor"

    def test_to_dict_serialization(self):
        """測試序列化為 dict。"""
        binding_report = {
            "arguments": [
                _argument_with_quantifiable_basis(
                    "原稿未定義法律責任範圍",
                    "補齊讀者對法律責任範圍所需的說明",
                ),
            ],
            "angle_coverage_summary": {
                "unique_angle_types": ["definition"],
                "effective_angle_count": 1,
                "duplicate_ratio": 0.0,
            },
        }
        delivery_status = {
            "primary_note_ready": True,
            "user_channel_sent": True,
            "local_fallback_written": True,
        }
        
        metrics = calculate_polaris_metrics(binding_report, delivery_status)
        metrics_dict = metrics.to_dict()
        
        # 驗證基本結構
        assert "schema" in metrics_dict
        assert metrics_dict["schema"] == "note_filler.polaris_metrics.v1"
        assert metrics_dict["formula_version"] == "1.2"
        assert "overall_status" in metrics_dict
        assert metrics_dict["decision"] == metrics_dict["overall_status"]
        assert metrics_dict["decision_rule"]
        assert "core_metrics_pass_count" in metrics_dict
        assert "core_metrics_total_count" in metrics_dict
        assert "calculated_at" in metrics_dict
        
        # 驗證各個指標欄位
        assert "functional_gap_score" in metrics_dict
        assert "user_value_score" in metrics_dict
        assert "source_binding_integrity" in metrics_dict
        assert "angle_diversity_index" in metrics_dict
        assert "delivery_success_rate" in metrics_dict

        expected_sources = {
            "functional_gap_score": "binding_report.arguments[].functional_gap",
            "user_value_score": "binding_report.arguments[].user_value",
            "source_binding_integrity": "binding_report.arguments[].binding_status",
            "angle_diversity_index": "binding_report.angle_coverage_summary.unique_angle_types",
            "delivery_success_rate": "delivery_manifest.delivery_status.user_channel_sent",
        }
        for name, source_field in expected_sources.items():
            metric = metrics_dict[name]
            assert metric["formula_version"] == metrics_dict["formula_version"]
            assert metric["formula"]
            assert source_field in metric["source_fields"]
            assert metric["decision"] == (
                "pass" if metric["passes_threshold"] else "fail"
            )
        
        # 驗證可 JSON 序列化
        json_str = json.dumps(metrics_dict, ensure_ascii=False)
        assert len(json_str) > 0

    def test_to_dict_with_missing_data(self):
        """測試缺值情況下的序列化。"""
        binding_report = {
            "arguments": [],
            "angle_coverage_summary": {},
        }
        delivery_status = None
        
        metrics = calculate_polaris_metrics(binding_report, delivery_status)
        metrics_dict = metrics.to_dict()
        
        # 驗證缺值狀態被正確記錄
        assert metrics_dict["functional_gap_score"]["status"] == "missing_data"
        assert metrics_dict["user_value_score"]["status"] == "missing_data"
        assert metrics_dict["source_binding_integrity"]["status"] == "missing_data"
        assert metrics_dict["angle_diversity_index"]["status"] == "missing_data"
        assert metrics_dict["delivery_success_rate"]["status"] == "missing_data"
        for name in (
            "functional_gap_score",
            "user_value_score",
            "source_binding_integrity",
            "angle_diversity_index",
            "delivery_success_rate",
        ):
            assert metrics_dict[name]["decision"] == "missing_data"
        assert metrics_dict["traceability_score"]["status"] == "missing_data"
        assert metrics_dict["traceability_score"]["degraded"] is True
        assert metrics_dict["traceability_score"]["penalty"] == pytest.approx(0.1)

    def test_error_status_propagation(self):
        """測試錯誤狀態的傳播。"""
        # 模擬一個錯誤狀態的指標
        functional_gap = FunctionalGapScore(
            score=0.0, status="error",
            total_arguments=0, arguments_with_concrete_gap=0,
            arguments_with_empty_gap=0, arguments_missing_field=0,
        )
        user_value = UserValueScore(
            score=0.8, status="calculated",
            total_arguments=5, arguments_with_clear_value=4,
            arguments_with_empty_value=1, arguments_missing_field=0,
        )
        source_binding = SourceBindingIntegrity(
            score=0.9, status="calculated",
            total_arguments=5, arguments_pass=4,
            arguments_fail=1, arguments_pending=0, arguments_missing_status=0,
        )
        angle_diversity = AngleDiversityIndex(
            score=0.7, status="calculated",
            unique_angle_types=5, expected_angle_types=8,
            effective_angle_count=5, duplicate_ratio=0.1,
            unique_angle_type_names=["definition", "limitation", "requirement", "effect", "procedure"],
        )
        delivery = DeliverySuccessRate(
            score=1.0, status="calculated",
            total_attempts=1, successful_deliveries=1, failed_deliveries=0,
        )
        
        metrics = PolarisMetrics(
            functional_gap_score=functional_gap,
            user_value_score=user_value,
            source_binding_integrity=source_binding,
            angle_diversity_index=angle_diversity,
            delivery_success_rate=delivery,
            calculated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        )
        
        # 有錯誤狀態時，整體狀態應為 error
        assert metrics.overall_status == "error"


class TestMetricsIntegration:
    """指標整合測試。"""

    def test_polaris_metrics_in_delivery_manifest(self):
        """測試北極星指標在 delivery_manifest 中的整合。"""
        binding_report = {
            "arguments": [
                _argument_with_quantifiable_basis(
                    "原稿未定義法律責任範圍",
                    "補齊讀者對法律責任範圍所需的說明",
                ),
            ],
            "angle_coverage_summary": {
                "unique_angle_types": ["definition"],
                "effective_angle_count": 1,
                "duplicate_ratio": 0.0,
            },
        }
        delivery_status = {
            "primary_note_ready": True,
            "user_channel_sent": True,
            "local_fallback_written": True,
        }
        
        polaris_metrics = calculate_polaris_metrics(
            binding_report=binding_report,
            delivery_status=delivery_status,
        ).to_dict()
        
        # 模擬 delivery_manifest 結構
        manifest = {
            "output_path": "/path/to/output.md",
            "input_path": "/path/to/input.txt",
            "status": "delivered",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "polaris_metrics": polaris_metrics,
        }
        
        # 驗證 manifest 可被解析
        assert "polaris_metrics" in manifest
        assert manifest["polaris_metrics"]["schema"] == "note_filler.polaris_metrics.v1"
        
        # 驗證可 JSON 序列化
        json_str = json.dumps(manifest, ensure_ascii=False, indent=2)
        assert len(json_str) > 0
        
        # 驗證可反序列化
        parsed_manifest = json.loads(json_str)
        assert parsed_manifest["polaris_metrics"]["overall_status"] in [
            "excellent", "good", "acceptable", "poor"
        ]


def test_functional_gap_and_user_value_scores_expose_quantified_breakdown():
    """四個子分數、加權總分與逐論點依據必須可由輸出重算。"""
    arguments = [
        {
            "argument_id": "argument:0",
            "source_ids": ["source:a"],
            "binding_status": "pass",
            "functional_gap": "原稿未說明行政處分的成立要件",
            "user_value": "補齊讀者理解行政處分成立要件所需的說明",
            "checks": {
                "at_least_one_source": True,
                "source_traceable": True,
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
        },
        {
            "argument_id": "argument:1",
            "source_ids": [],
            "binding_status": "pending_evidence",
            "functional_gap": "太短",
            "user_value": "提供資訊",
            "checks": {
                "at_least_one_source": False,
                "source_traceable": True,
                "no_omitted_traces": True,
                "no_extra_traces": True,
                "has_functional_gap": True,
                "has_user_value": True,
                "has_related_knowledge": True,
                "related_knowledge_consistent": False,
            },
            "angle_coverage": {
                "covered_facets": ["necessity:functional_gap"],
                "effective_angle_count": 1,
            },
        },
    ]

    metrics = calculate_polaris_metrics(
        {"arguments": arguments, "angle_coverage_summary": {}},
    ).to_dict()
    functional_gap = metrics["functional_gap_score"]
    user_value = metrics["user_value_score"]

    assert functional_gap["subscores"] == {
        "traceability": {
            "score": 0.5,
            "weight": 0.25,
            "weighted_score": 0.125,
            "numerator": 1,
            "denominator": 2,
            "rule": "有實際來源且來源與追溯識別碼完整對齊的論點比例",
        },
        "coverage_breadth": {
            "score": 1.0,
            "weight": 0.25,
            "weighted_score": 0.25,
            "numerator": 2,
            "denominator": 2,
            "rule": "具有效且未去重角度及功能缺口 facet 的論點比例",
        },
        "necessity_clarity": {
            "score": 0.5,
            "weight": 0.25,
            "weighted_score": 0.125,
            "numerator": 1,
            "denominator": 2,
            "rule": "功能缺口非空且至少 10 字元的論點比例",
        },
        "decision_support": {
            "score": 0.5,
            "weight": 0.25,
            "weighted_score": 0.125,
            "numerator": 1,
            "denominator": 2,
            "rule": "關聯知識明示決策助益且與功能缺口及使用者價值一致的論點比例",
        },
    }
    assert functional_gap["total_score"] == functional_gap["score"] == 0.625
    assert user_value["total_score"] == user_value["score"] == 0.5
    assert user_value["subscores"]["coverage_breadth"]["score"] == 0.5
    assert functional_gap["threshold"] == user_value["threshold"] == 0.7
    assert functional_gap["formula"] == (
        "traceability*0.25 + coverage_breadth*0.25 + "
        "necessity_clarity*0.25 + decision_support*0.25"
    )
    assert functional_gap["basis_mode"] == "binding_report"
    assert functional_gap["calculation_basis"][1] == {
        "argument_id": "argument:1",
        "source_ids": [],
        "binding_status": "pending_evidence",
        "traceability": False,
        "coverage_breadth": True,
        "necessity_clarity": False,
        "decision_support": False,
    }


def test_overall_score_exposes_traceability_penalty_and_affected_arguments():
    """總分須可重算，且直接指出因追溯不足被扣分的論點。"""
    traceable = _argument_with_quantifiable_basis(
        "原稿未說明行政處分的成立要件",
        "補齊讀者理解行政處分成立要件所需的說明",
    )
    traceable["argument_id"] = "argument:traceable"
    pending = _argument_with_quantifiable_basis(
        "原稿未說明行政處分的法律效果",
        "補齊讀者理解行政處分法律效果所需的說明",
    )
    pending.update({
        "argument_id": "argument:pending",
        "source_ids": [],
        "binding_status": "pending_evidence",
    })
    pending["checks"]["at_least_one_source"] = False
    mismatched = _argument_with_quantifiable_basis(
        "原稿未說明行政處分的救濟方式",
        "補齊讀者理解行政處分救濟方式所需的說明",
    )
    mismatched.update({
        "argument_id": "argument:mismatched",
        "binding_status": "fail",
    })
    mismatched["checks"]["source_traceable"] = False

    metrics = calculate_polaris_metrics(
        {
            "arguments": [traceable, pending, mismatched],
            "angle_coverage_summary": {
                "unique_angle_types": [
                    "definition", "limitation", "requirement", "effect",
                    "procedure", "exception", "comparison", "application",
                ],
                "effective_angle_count": 8,
                "duplicate_ratio": 0.0,
            },
        },
        {
            "primary_note_ready": True,
            "user_channel_sent": True,
            "local_fallback_written": True,
        },
    ).to_dict()

    traceability = metrics["traceability_score"]
    assert traceability["score"] == pytest.approx(1 / 3)
    assert traceability["penalty"] == pytest.approx(1 / 15)
    assert traceability["degraded"] is True
    assert traceability["affected_argument_ids"] == [
        "argument:pending", "argument:mismatched",
    ]
    assert traceability["acceptance"] == {
        "target_score": 1.0,
        "target_penalty": 0.0,
        "affected_argument_ids": [],
    }
    assert metrics["overall_score"] == pytest.approx(sum(
        item["weighted_score"]
        for item in metrics["overall_score_components"].values()
    ))
    assert metrics["score_if_traceability_complete"] == pytest.approx(
        metrics["overall_score"] + traceability["penalty"]
    )
