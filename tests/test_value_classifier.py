"""驗收測試：高價值筆記 vs 形式完整低效益筆記之分類器。

測試範圍：
1. UsageEffectivenessScore 計算邏輯
2. NoteValueClassification 分類邏輯
3. 對整個標註資料集的評估（混淆矩陣、精確率、召回率）
4. 門檻掃描找出最佳 F1
5. 邊界案例驗證（形式好但零使用 vs 形式普通但高使用）
6. 代表性誤判案例盤點
"""
from __future__ import annotations

from pathlib import Path

import pytest

from note_filler.metrics import (
    FUNCTIONAL_GAP_THRESHOLD,
    USER_VALUE_THRESHOLD,
    SOURCE_BINDING_THRESHOLD,
    calculate_polaris_metrics,
)
from note_filler.value_classifier import (
    USAGE_SIGNAL_CONFIG,
    USAGE_SIGNAL_DEFAULTS,
    NoteValueClassification,
    calculate_usage_effectiveness,
    classify_note_value,
    compute_confusion_matrix,
    evaluate_classifier_on_dataset,
    find_optimal_thresholds,
    fixture_to_binding_report,
    generate_classification_misclassification_report,
    load_annotation_fixture,
    normalize_usage_signal,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "polaris_annotation"


# ══════════════════════════════════════════════════════════════════════════════
# 1.  使用成效訊號正規化與計算
# ══════════════════════════════════════════════════════════════════════════════

class TestUsageSignalNormalization:

    def test_normalize_zero(self):
        assert normalize_usage_signal(0, 10) == 0.0

    def test_normalize_half(self):
        assert normalize_usage_signal(5, 10) == 0.5

    def test_normalize_full(self):
        assert normalize_usage_signal(10, 10) == 1.0

    def test_normalize_clip_above_max(self):
        assert normalize_usage_signal(15, 10) == 1.0

    def test_normalize_negative_clip_to_zero(self):
        assert normalize_usage_signal(-5, 10) == 0.0

    def test_normalize_boolean_true(self):
        assert normalize_usage_signal(True, 1) == 1.0

    def test_normalize_boolean_false(self):
        assert normalize_usage_signal(False, 1) == 0.0

    def test_normalize_none_falls_to_zero(self):
        assert normalize_usage_signal(None, 10) == 0.0

    def test_normalize_string_falls_to_zero(self):
        assert normalize_usage_signal("high", 10) == 0.0


class TestUsageEffectivenessScore:

    def test_missing_signals_returns_missing_data(self):
        score = calculate_usage_effectiveness(None)
        assert score.status == "missing_data"
        assert score.score == 0.0
        assert score.passes_threshold is False

    def test_empty_signals_returns_missing_data(self):
        score = calculate_usage_effectiveness({})
        assert score.status == "missing_data"
        assert score.score == 0.0

    def test_all_signals_max(self):
        signals = {
            "citation_count": 20,
            "reuse_count": 10,
            "regeneration_avoided": True,
            "user_feedback_positive": True,
            "completion_rate": 1.0,
            "reference_in_other_notes_count": 15,
            "search_click_count": 50,
        }
        score = calculate_usage_effectiveness(signals)
        assert score.status == "calculated"
        assert score.score >= 0.9
        assert score.passes_threshold is True

    def test_all_signals_zero(self):
        signals = {
            "citation_count": 0,
            "reuse_count": 0,
            "regeneration_avoided": False,
            "user_feedback_positive": False,
            "completion_rate": 0.0,
            "reference_in_other_notes_count": 0,
            "search_click_count": 0,
        }
        score = calculate_usage_effectiveness(signals)
        assert score.status == "calculated"
        assert score.score == 0.0
        assert score.passes_threshold is False

    def test_mixed_signals(self):
        signals = {
            "citation_count": 5,
            "reuse_count": 3,
            "regeneration_avoided": True,
            "user_feedback_positive": False,
            "completion_rate": 0.7,
            "reference_in_other_notes_count": 2,
            "search_click_count": 10,
        }
        score = calculate_usage_effectiveness(signals)
        assert score.status == "calculated"
        assert 0.3 < score.score < 0.8
        assert abs(score.score - sum(
            score.signal_breakdown[k]["weighted_score"]
            for k in score.signal_breakdown
        )) < 0.001

    def test_breakdown_consistency(self):
        signals = {"citation_count": 5, "reuse_count": 2}
        score = calculate_usage_effectiveness(signals)
        total_weight = sum(score.signal_breakdown[k]["weight"]
                           for k in score.signal_breakdown)
        assert abs(total_weight - 1.0) < 0.001


# ══════════════════════════════════════════════════════════════════════════════
# 2.  複合價值分類
# ══════════════════════════════════════════════════════════════════════════════

class TestNoteValueClassification:

    def test_high_value_classification(self):
        """polaris + usage 皆高 → high_value。"""
        result = classify_note_value(
            note_id="test_001",
            ground_truth="high_value",
            polaris_metrics={
                "overall_score": 0.8,
                "core_metrics_pass_count": 4,
                "overall_status": "good",
            },
            usage_signals={
                "citation_count": 10,
                "reuse_count": 5,
                "regeneration_avoided": True,
                "user_feedback_positive": True,
                "completion_rate": 0.9,
                "reference_in_other_notes_count": 8,
                "search_click_count": 30,
            },
        )
        assert result.predicted_label == "high_value"
        assert result.is_correct is True
        assert result.composite_score >= 0.5

    def test_low_benefit_classification(self):
        """polaris + usage 皆低 → low_benefit。"""
        result = classify_note_value(
            note_id="test_002",
            ground_truth="low_benefit",
            polaris_metrics={
                "overall_score": 0.3,
                "core_metrics_pass_count": 1,
                "overall_status": "poor",
            },
            usage_signals={
                "citation_count": 0,
                "reuse_count": 0,
                "regeneration_avoided": False,
                "user_feedback_positive": False,
                "completion_rate": 0.0,
                "reference_in_other_notes_count": 0,
                "search_click_count": 0,
            },
        )
        assert result.predicted_label == "low_benefit"
        assert result.is_correct is True
        assert result.composite_score < 0.5

    def test_polaris_borderline_with_high_usage(self):
        """polaris 邊緣但使用高 → 可能 high_value。"""
        result = classify_note_value(
            note_id="test_003",
            ground_truth="high_value",
            polaris_metrics={
                "overall_score": 0.45,
                "core_metrics_pass_count": 2,
                "overall_status": "acceptable",
            },
            usage_signals={
                "citation_count": 18,
                "reuse_count": 9,
                "regeneration_avoided": True,
                "user_feedback_positive": True,
                "completion_rate": 0.95,
                "reference_in_other_notes_count": 14,
                "search_click_count": 45,
            },
        )
        # Usage 高分應拉升 composite 過門檻
        assert result.composite_score >= 0.5

    def test_polaris_excellent_with_zero_usage(self):
        """polaris 優秀但使用歸零 → 應降級為 low_benefit。"""
        result = classify_note_value(
            note_id="test_004",
            ground_truth="low_benefit",
            polaris_metrics={
                "overall_score": 0.85,
                "core_metrics_pass_count": 5,
                "overall_status": "excellent",
            },
            usage_signals={
                "citation_count": 0,
                "reuse_count": 0,
                "regeneration_avoided": False,
                "user_feedback_positive": False,
                "completion_rate": 0.0,
                "reference_in_other_notes_count": 0,
                "search_click_count": 0,
            },
        )
        composite = result.composite_score
        expected = 0.5 * 0.85 + 0.5 * 0.0
        assert abs(composite - expected) < 0.01
        assert result.predicted_label == "low_benefit", (
            f"polaris 優秀但使用歸零時 composite={composite:.3f} 應低於門檻"
        )
        assert result.is_correct is True

    def test_classification_contract_fields(self):
        """分類結果必須包含所有約定欄位。"""
        result = classify_note_value(
            note_id="contract_test",
            ground_truth="high_value",
            polaris_metrics={"overall_score": 0.7},
            usage_signals={"citation_count": 5},
        )
        assert result.note_id == "contract_test"
        assert result.ground_truth == "high_value"
        assert isinstance(result.polaris_overall_score, float)
        assert isinstance(result.usage_effectiveness_score, float)
        assert isinstance(result.composite_score, float)
        assert isinstance(result.polaris_threshold, float)
        assert isinstance(result.usage_threshold, float)
        assert isinstance(result.composite_threshold, float)
        assert isinstance(result.polaris_metrics, dict)
        assert isinstance(result.is_correct, bool)

    def test_classification_empty_usage(self):
        """無使用訊號時 usage=0，複合分數全靠 polaris。"""
        result = classify_note_value(
            note_id="no_usage",
            ground_truth="high_value",
            polaris_metrics={"overall_score": 0.8},
            usage_signals=None,
        )
        expected = 0.5 * 0.8 + 0.5 * 0.0
        assert abs(result.composite_score - expected) < 0.01
        assert result.usage_effectiveness_score == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# 3.  混淆矩陣與評估
# ══════════════════════════════════════════════════════════════════════════════

class TestConfusionMatrix:

    def test_empty_matrix(self):
        cm = compute_confusion_matrix([])
        assert cm.total == 0
        assert cm.precision == 0.0
        assert cm.recall == 0.0
        assert cm.accuracy == 0.0
        assert cm.f1_score == 0.0

    def test_perfect_classification(self):
        results = [
            NoteValueClassification("a", "high_value", "high_value", 0.8, 0.7, 0.76, 0.5, 0.5, 0.5),
            NoteValueClassification("b", "high_value", "high_value", 0.7, 0.6, 0.66, 0.5, 0.5, 0.5),
            NoteValueClassification("c", "low_benefit", "low_benefit", 0.3, 0.2, 0.26, 0.5, 0.5, 0.5),
            NoteValueClassification("d", "low_benefit", "low_benefit", 0.2, 0.1, 0.16, 0.5, 0.5, 0.5),
        ]
        cm = compute_confusion_matrix(results)
        assert cm.true_positive == 2
        assert cm.true_negative == 2
        assert cm.false_positive == 0
        assert cm.false_negative == 0
        assert cm.precision == 1.0
        assert cm.recall == 1.0
        assert cm.f1_score == 1.0

    def test_with_misclassifications(self):
        results = [
            NoteValueClassification("a", "high_value", "high_value", 0.8, 0.7, 0.76, 0.5, 0.5, 0.5),
            NoteValueClassification("b", "high_value", "low_benefit", 0.4, 0.3, 0.36, 0.5, 0.5, 0.5),
            NoteValueClassification("c", "low_benefit", "low_benefit", 0.3, 0.2, 0.26, 0.5, 0.5, 0.5),
            NoteValueClassification("d", "low_benefit", "high_value", 0.6, 0.5, 0.56, 0.5, 0.5, 0.5),
        ]
        cm = compute_confusion_matrix(results)
        assert cm.true_positive == 1
        assert cm.true_negative == 1
        assert cm.false_positive == 1
        assert cm.false_negative == 1
        assert cm.total == 4
        assert cm.precision == 0.5
        assert cm.recall == 0.5
        assert abs(cm.accuracy - 0.5) < 0.001

    def test_to_dict_contains_all_keys(self):
        cm = compute_confusion_matrix([])
        d = cm.to_dict()
        for key in ("true_positive", "true_negative", "false_positive", "false_negative",
                     "total", "precision", "recall", "specificity", "accuracy", "f1_score"):
            assert key in d


# ══════════════════════════════════════════════════════════════════════════════
# 4.  標註資料集端到端評估
# ══════════════════════════════════════════════════════════════════════════════

class TestDatasetEvaluation:

    def test_all_fixtures_loadable(self):
        """所有 fixture 必須能載入且含有必要欄位。"""
        for subdir in ("high_value", "low_benefit"):
            d = FIXTURE_DIR / subdir
            for f in sorted(d.glob("*.json")):
                data = load_annotation_fixture(f)
                assert "note_id" in data
                assert "arguments" in data
                assert len(data["arguments"]) >= 1
                assert data.get("ground_truth") in ("high_value", "low_benefit")
                assert "usage_signals" in data

    def test_full_dataset_evaluation(self):
        """對整個標註資料集進行評估，並回報混淆矩陣。"""
        results, cm = evaluate_classifier_on_dataset(FIXTURE_DIR)
        assert len(results) >= 9, f"應至少有 9 筆標註資料，實際 {len(results)}"
        assert cm.total == len(results)

        # 基本效能門檻
        assert cm.f1_score >= 0.7, (
            f"F1 分數 {cm.f1_score:.3f} 應 >= 0.7"
        )
        assert cm.accuracy >= 0.7, (
            f"準確率 {cm.accuracy:.3f} 應 >= 0.7"
        )

    def test_dataset_class_distribution(self):
        """驗證資料集類別平衡性。"""
        results, cm = evaluate_classifier_on_dataset(FIXTURE_DIR)
        total = len(results)
        fp_fn = cm.false_positive + cm.false_negative
        assert fp_fn / total <= 0.4, (
            f"誤判率 {fp_fn}/{total} = {fp_fn/total:.3f} 應 <= 0.4"
        )

    def test_misclassification_report_generated(self):
        """誤判案例報告必須能產生。"""
        results, cm = evaluate_classifier_on_dataset(FIXTURE_DIR)
        mis = generate_classification_misclassification_report(results)
        total = len(results)
        correct = sum(1 for r in results if r.is_correct)
        assert correct + len(mis) == total
        for m in mis:
            for key in ("note_id", "ground_truth", "predicted",
                         "polaris_overall_score", "usage_effectiveness_score",
                         "composite_score"):
                assert key in m, f"誤判報告缺少 {key}"


# ══════════════════════════════════════════════════════════════════════════════
# 5.  門檻掃描
# ══════════════════════════════════════════════════════════════════════════════

class TestThresholdOptimization:

    def test_find_optimal_thresholds(self):
        """掃描門檻組合應能找出最佳 F1 對應的門檻值。"""
        optimal = find_optimal_thresholds(
            FIXTURE_DIR,
            polaris_thresholds=[0.3, 0.5, 0.7],
            composite_thresholds=[0.3, 0.5, 0.7],
        )
        assert optimal["f1_score"] > 0
        assert "polaris_threshold" in optimal
        assert "composite_threshold" in optimal
        assert "confusion_matrix" in optimal

    def test_default_threshold_acceptance(self):
        """預設門檻 (0.5/0.5) 必須滿足最低效能標準。"""
        results, cm = evaluate_classifier_on_dataset(FIXTURE_DIR)
        assert cm.f1_score >= 0.65, (
            f"預設門檻 F1 {cm.f1_score:.3f} < 0.65"
        )
        assert cm.precision >= 0.6, (
            f"預設門檻 precision {cm.precision:.3f} < 0.6"
        )
        assert cm.recall >= 0.6, (
            f"預設門檻 recall {cm.recall:.3f} < 0.6"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 6.  邊界案例驗證
# ══════════════════════════════════════════════════════════════════════════════

class TestBoundaryCases:

    def test_form_complete_zero_usage_downgraded(self):
        """形式完整（polaris 優秀）但使用訊號歸零 → 降級為 low_benefit。"""
        data = load_annotation_fixture(
            FIXTURE_DIR / "low_benefit" / "note_005.json"
        )
        assert data["ground_truth"] == "low_benefit"

        br = fixture_to_binding_report(data)
        delivery = {
            "primary_note_ready": True,
            "user_channel_sent": True,
            "local_fallback_written": True,
        }
        polaris = calculate_polaris_metrics(br, delivery).to_dict()

        result = classify_note_value(
            note_id=data["note_id"],
            ground_truth=data["ground_truth"],
            polaris_metrics=polaris,
            usage_signals=data["usage_signals"],
        )

        assert result.is_correct, (
            f"形式完整零使用案例應被降級為 low_benefit，但預測為 {result.predicted_label}"
        )
        # polaris 應高但 usage 為 0
        assert result.polaris_overall_score >= 0.5
        assert result.usage_effectiveness_score == 0.0
        assert result.predicted_label == "low_benefit"

    def test_usage_signal_raises_borderline_polaris(self):
        """polaris 邊緣但使用訊號強 → 可能拉升為 high_value。"""
        data = load_annotation_fixture(
            FIXTURE_DIR / "high_value" / "note_003.json"
        )
        assert data["ground_truth"] == "high_value"
        br = fixture_to_binding_report(data)
        delivery = {
            "primary_note_ready": True,
            "user_channel_sent": True,
            "local_fallback_written": True,
        }
        polaris = calculate_polaris_metrics(br, delivery).to_dict()

        result = classify_note_value(
            note_id=data["note_id"],
            ground_truth=data["ground_truth"],
            polaris_metrics=polaris,
            usage_signals=data["usage_signals"],
        )

        assert result.usage_effectiveness_score >= 0.7, (
            f"高使用案例 usage score {result.usage_effectiveness_score:.3f} 應 >= 0.7"
        )
        assert result.predicted_label == "high_value"


# ══════════════════════════════════════════════════════════════════════════════
# 7.  整合性驗收：對照低效益 vs 高價值
# ══════════════════════════════════════════════════════════════════════════════

class TestHighVsLowDiscrimination:

    def test_purely_formal_note_with_usage_signals_does_not_pass_as_high(self):
        """純形式完整但 usage=0 的筆記不得被分類為高價值。"""
        results, cm = evaluate_classifier_on_dataset(FIXTURE_DIR)
        for r in results:
            if r.ground_truth == "low_benefit":
                if r.polaris_overall_score >= 0.6 and r.usage_effectiveness_score < 0.1:
                    assert r.predicted_label == "low_benefit", (
                        f"{r.note_id}: polaris={r.polaris_overall_score:.3f} "
                        f"但 usage={r.usage_effectiveness_score:.3f} 應降級"
                    )

    def test_dataset_precision_recall_bounds(self):
        """資料集整體精確率與召回率必須在合理範圍。"""
        results, cm = evaluate_classifier_on_dataset(FIXTURE_DIR)
        assert 0.0 <= cm.precision <= 1.0
        assert 0.0 <= cm.recall <= 1.0

    def test_ground_truth_vs_predicted_label_pairs(self):
        """每筆資料的 ground_truth 與 predicted_label 必須是有效值。"""
        results, cm = evaluate_classifier_on_dataset(FIXTURE_DIR)
        for r in results:
            assert r.ground_truth in ("high_value", "low_benefit")
            assert r.predicted_label in ("high_value", "low_benefit")


# ══════════════════════════════════════════════════════════════════════════════
# 8.  舊有 fixture backward-compatibility
# ══════════════════════════════════════════════════════════════════════════════

class TestExtendedFixtureBackwardCompatibility:

    def test_original_fixtures_still_loadable(self):
        """原始的 4 個 fixture 在新的 loader 下仍可正常載入。"""
        id_to_file = {
            "high_value_001": ("high_value", "note_001.json"),
            "high_value_002": ("high_value", "note_002.json"),
            "low_benefit_001": ("low_benefit", "note_001.json"),
            "low_benefit_002": ("low_benefit", "note_002.json"),
        }
        for note_id, (subdir, filename) in id_to_file.items():
            p = FIXTURE_DIR / subdir / filename
            assert p.exists(), f"找不到原始 fixture {p}"
            data = load_annotation_fixture(p)
            assert data["note_id"] == note_id
            assert data.get("ground_truth") in ("high_value", "low_benefit")
            br = fixture_to_binding_report(data)
            assert br["argument_count"] >= 1

    def test_new_fixtures_have_usage_signals(self):
        """新的 fixture 必須包含 usage_signals 欄位。"""
        for subdir in ("high_value", "low_benefit"):
            for f in sorted(FIXTURE_DIR.glob(f"{subdir}/*.json")):
                data = load_annotation_fixture(f)
                assert "usage_signals" in data, (
                    f"{f.name} 缺少 usage_signals"
                )
