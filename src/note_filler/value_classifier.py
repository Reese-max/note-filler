"""筆記價值分類模組：區分高價值筆記與形式完整但低效益筆記。

整合北極星品質指標與實際使用成效訊號，提供：
- 使用成效評分：將 citation_count、reuse_count 等訊號正規化為 0~1 分數
- 複合價值分類：結合 Polaris 指標與使用訊號的加權分類
- 混淆矩陣與評估：支援分類器效能評估
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from note_filler.metrics import (
    FUNCTIONAL_GAP_THRESHOLD,
    USER_VALUE_THRESHOLD,
    SOURCE_BINDING_THRESHOLD,
    ANGLE_DIVERSITY_THRESHOLD,
    DELIVERY_SUCCESS_THRESHOLD,
    calculate_polaris_metrics,
)

# ── 使用成效訊號模型 ──────────────────────────────────────────────────────────

UsageSignalKey = Literal[
    "citation_count",
    "reuse_count",
    "regeneration_avoided",
    "user_feedback_positive",
    "completion_rate",
    "reference_in_other_notes_count",
    "search_click_count",
]

USAGE_SIGNAL_DEFAULTS: dict[UsageSignalKey, float | bool] = {
    "citation_count": 0,
    "reuse_count": 0,
    "regeneration_avoided": False,
    "user_feedback_positive": False,
    "completion_rate": 0.0,
    "reference_in_other_notes_count": 0,
    "search_click_count": 0,
}

# 各訊號正規化參數（最大合理值 / 權重）
USAGE_SIGNAL_CONFIG: dict[str, dict[str, Any]] = {
    "citation_count": {"max_expected": 20, "weight": 0.20},
    "reuse_count": {"max_expected": 10, "weight": 0.20},
    "regeneration_avoided": {"max_expected": 1, "weight": 0.15},
    "user_feedback_positive": {"max_expected": 1, "weight": 0.15},
    "completion_rate": {"max_expected": 1, "weight": 0.10},
    "reference_in_other_notes_count": {"max_expected": 15, "weight": 0.10},
    "search_click_count": {"max_expected": 50, "weight": 0.10},
}


@dataclass
class UsageEffectivenessScore:
    """使用成效分數：將使用訊號正規化為 0~1 分數。"""
    score: float
    status: Literal["calculated", "missing_data"]
    threshold: float = 0.5
    passes_threshold: bool = False

    raw_signals: dict[str, Any] = field(default_factory=dict)
    normalized_signals: dict[str, float] = field(default_factory=dict)
    signal_breakdown: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        if self.status == "calculated":
            self.passes_threshold = self.score >= self.threshold


def normalize_usage_signal(
    value: Any,
    max_expected: float,
) -> float:
    """將單一使用訊號正規化為 0~1 分數。"""
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if not isinstance(value, (int, float)):
        return 0.0
    if max_expected <= 0:
        return 0.0
    clipped = min(max(0.0, float(value)), max_expected)
    return clipped / max_expected


def calculate_usage_effectiveness(
    usage_signals: dict[str, Any] | None,
) -> UsageEffectivenessScore:
    """從使用訊號計算使用成效分數。"""
    if not usage_signals:
        return UsageEffectivenessScore(
            score=0.0,
            status="missing_data",
            threshold=0.5,
            passes_threshold=False,
        )

    merged = dict(USAGE_SIGNAL_DEFAULTS)
    merged.update(usage_signals)

    normalized: dict[str, float] = {}
    breakdown: dict[str, dict[str, Any]] = {}
    weighted_sum = 0.0
    total_weight = 0.0

    for key, config in USAGE_SIGNAL_CONFIG.items():
        raw = merged.get(key, USAGE_SIGNAL_DEFAULTS.get(key, 0))
        norm = normalize_usage_signal(raw, config["max_expected"])
        normalized[key] = norm
        weight = config["weight"]
        weighted_sum += norm * weight
        total_weight += weight
        breakdown[key] = {
            "raw_value": raw,
            "normalized": norm,
            "weight": weight,
            "weighted_score": norm * weight,
        }

    score = weighted_sum / total_weight if total_weight > 0 else 0.0
    score = min(1.0, max(0.0, score))

    return UsageEffectivenessScore(
        score=score,
        status="calculated",
        threshold=0.5,
        passes_threshold=score >= 0.5,
        raw_signals=merged,
        normalized_signals=normalized,
        signal_breakdown=breakdown,
    )


# ── 複合價值分類 ──────────────────────────────────────────────────────────────

# 預設分類門檻
POLARIS_OVERALL_THRESHOLD = 0.5
USAGE_EFFECTIVENESS_THRESHOLD = 0.5
COMPOSITE_THRESHOLD = 0.5

# 北極星指標在複合分數中的權重（其餘為使用成效）
# 等權重設計：形式品質與實際使用同等重要
POLARIS_COMPOSITE_WEIGHT = 0.5
USAGE_COMPOSITE_WEIGHT = 0.5

ValueLabel = Literal["high_value", "low_benefit"]


@dataclass
class NoteValueClassification:
    """單筆筆記的價值分類結果。"""
    note_id: str
    ground_truth: ValueLabel
    predicted_label: ValueLabel

    # 分項分數
    polaris_overall_score: float
    usage_effectiveness_score: float
    composite_score: float

    # 門檻設定
    polaris_threshold: float
    usage_threshold: float
    composite_threshold: float

    # 詳細資料
    polaris_metrics: dict[str, Any] = field(default_factory=dict)
    usage_score_detail: UsageEffectivenessScore | None = None
    is_correct: bool = False

    def __post_init__(self):
        self.is_correct = self.predicted_label == self.ground_truth


@dataclass
class ConfusionMatrix:
    """二元分類混淆矩陣。"""
    true_positive: int = 0   # 正確預測 high_value
    true_negative: int = 0   # 正確預測 low_benefit
    false_positive: int = 0  # 實際 low_benefit 但預測 high_value
    false_negative: int = 0  # 實際 high_value 但預測 low_benefit

    @property
    def total(self) -> int:
        return self.true_positive + self.true_negative + self.false_positive + self.false_negative

    @property
    def precision(self) -> float:
        denom = self.true_positive + self.false_positive
        return self.true_positive / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positive + self.false_negative
        return self.true_positive / denom if denom else 0.0

    @property
    def specificity(self) -> float:
        denom = self.true_negative + self.false_positive
        return self.true_negative / denom if denom else 0.0

    @property
    def accuracy(self) -> float:
        return (self.true_positive + self.true_negative) / self.total if self.total else 0.0

    @property
    def f1_score(self) -> float:
        p = self.precision
        r = self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "true_positive": self.true_positive,
            "true_negative": self.true_negative,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "total": self.total,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "specificity": round(self.specificity, 4),
            "accuracy": round(self.accuracy, 4),
            "f1_score": round(self.f1_score, 4),
        }


def classify_note_value(
    note_id: str,
    ground_truth: ValueLabel,
    polaris_metrics: dict[str, Any],
    usage_signals: dict[str, Any] | None = None,
    *,
    polaris_threshold: float = POLARIS_OVERALL_THRESHOLD,
    usage_threshold: float = USAGE_EFFECTIVENESS_THRESHOLD,
    composite_threshold: float = COMPOSITE_THRESHOLD,
    polaris_weight: float = POLARIS_COMPOSITE_WEIGHT,
    usage_weight: float = USAGE_COMPOSITE_WEIGHT,
) -> NoteValueClassification:
    """對單筆筆記進行價值分類。

    分類規則：
    1. 計算北極星指標 overall_score（既有 Polaris 系統）
    2. 計算使用成效分數（usage signals）
    3. 計算複合分數 = polaris_weight * overall_score + usage_weight * usage_score
    4. 複合分數 >= composite_threshold → high_value，否則 low_benefit
    """
    overall_score = polaris_metrics.get("overall_score", 0.0)
    if not isinstance(overall_score, (int, float)) or isinstance(overall_score, bool):
        overall_score = 0.0
    overall_score = min(1.0, max(0.0, float(overall_score)))

    usage_score_obj = calculate_usage_effectiveness(usage_signals)
    usage_score = usage_score_obj.score

    composite = polaris_weight * overall_score + usage_weight * usage_score
    predicted: ValueLabel = "high_value" if composite >= composite_threshold else "low_benefit"

    return NoteValueClassification(
        note_id=note_id,
        ground_truth=ground_truth,
        predicted_label=predicted,
        polaris_overall_score=overall_score,
        usage_effectiveness_score=usage_score,
        composite_score=composite,
        polaris_threshold=polaris_threshold,
        usage_threshold=usage_threshold,
        composite_threshold=composite_threshold,
        polaris_metrics=polaris_metrics,
        usage_score_detail=usage_score_obj,
    )


def compute_confusion_matrix(
    results: list[NoteValueClassification],
) -> ConfusionMatrix:
    """從分類結果列表計算混淆矩陣。"""
    cm = ConfusionMatrix()
    for r in results:
        if r.ground_truth == "high_value" and r.predicted_label == "high_value":
            cm.true_positive += 1
        elif r.ground_truth == "low_benefit" and r.predicted_label == "low_benefit":
            cm.true_negative += 1
        elif r.ground_truth == "low_benefit" and r.predicted_label == "high_value":
            cm.false_positive += 1
        elif r.ground_truth == "high_value" and r.predicted_label == "low_benefit":
            cm.false_negative += 1
    return cm


def load_annotation_fixture(path: Path) -> dict[str, Any]:
    """載入標註 fixture JSON 檔案。"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fixture_to_binding_report(data: dict[str, Any]) -> dict[str, Any]:
    """將標註資料轉換為 binding_report 格式。"""
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

    unique_angle_types = sorted({
        arg["angle_coverage"]["angle_type"] for arg in arguments
    })

    return {
        "schema": "note_filler.binding_report.v1",
        "source_path": f"annotation:{data['note_id']}",
        "argument_count": len(arguments),
        "summary": {
            "one_to_one": sum(1 for a in arguments if a["cardinality"] == "one_to_one"),
            "one_to_many": sum(1 for a in arguments if a["cardinality"] == "one_to_many"),
            "none": sum(1 for a in arguments if a["cardinality"] == "none"),
            "pass": sum(1 for a in arguments if a["binding_status"] == "pass"),
            "fail": sum(1 for a in arguments if a["binding_status"] == "fail"),
            "pending_evidence": sum(1 for a in arguments if a["binding_status"] == "pending_evidence"),
            "all_sourced_arguments_ok": all(
                a["binding_status"] == "pass" for a in arguments if a["source_ids"]
            ) if any(a["source_ids"] for a in arguments) else True,
            "all_arguments_ok": all(a["binding_status"] == "pass" for a in arguments) if arguments else True,
        },
        "arguments": arguments,
        "source_usage": {},
        "angle_coverage_summary": {
            "unique_angle_types": unique_angle_types,
            "covered_facets_union": sorted({
                f for a in arguments for f in a["angle_coverage"]["covered_facets"]
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


def calculate_polaris_from_fixture(data: dict[str, Any]) -> dict[str, Any]:
    """從標註 fixture 計算北極星指標。"""
    binding_report = fixture_to_binding_report(data)
    delivery_status = {
        "primary_note_ready": True,
        "user_channel_sent": True,
        "local_fallback_written": True,
    }
    metrics = calculate_polaris_metrics(binding_report, delivery_status)
    return metrics.to_dict()


def evaluate_classifier_on_dataset(
    fixture_dir: Path,
    *,
    polaris_threshold: float = POLARIS_OVERALL_THRESHOLD,
    usage_threshold: float = USAGE_EFFECTIVENESS_THRESHOLD,
    composite_threshold: float = COMPOSITE_THRESHOLD,
) -> tuple[list[NoteValueClassification], ConfusionMatrix]:
    """在整個標註資料集上評估分類器。"""
    results: list[NoteValueClassification] = []

    for subdir in ["high_value", "low_benefit"]:
        dir_path = fixture_dir / subdir
        if not dir_path.exists():
            continue
        for fixture_file in sorted(dir_path.glob("*.json")):
            data = load_annotation_fixture(fixture_file)
            note_id = data["note_id"]
            ground_truth = data["ground_truth"]
            usage_signals = data.get("usage_signals")

            polaris_metrics = calculate_polaris_from_fixture(data)

            result = classify_note_value(
                note_id=note_id,
                ground_truth=ground_truth,
                polaris_metrics=polaris_metrics,
                usage_signals=usage_signals,
                polaris_threshold=polaris_threshold,
                usage_threshold=usage_threshold,
                composite_threshold=composite_threshold,
            )
            results.append(result)

    cm = compute_confusion_matrix(results)
    return results, cm


def find_optimal_thresholds(
    fixture_dir: Path,
    *,
    polaris_thresholds: list[float] | None = None,
    composite_thresholds: list[float] | None = None,
) -> dict[str, Any]:
    """掃描門檻組合，找出最佳 F1 分數對應的門檻值。"""
    if polaris_thresholds is None:
        polaris_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    if composite_thresholds is None:
        composite_thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]

    best: dict[str, Any] = {
        "f1_score": 0.0,
        "polaris_threshold": 0.5,
        "composite_threshold": 0.5,
        "confusion_matrix": {},
    }

    for pt in polaris_thresholds:
        for ct in composite_thresholds:
            _, cm = evaluate_classifier_on_dataset(
                fixture_dir,
                polaris_threshold=pt,
                composite_threshold=ct,
            )
            if cm.f1_score > best["f1_score"]:
                best = {
                    "f1_score": cm.f1_score,
                    "polaris_threshold": pt,
                    "composite_threshold": ct,
                    "confusion_matrix": cm.to_dict(),
                }

    return best


def generate_classification_misclassification_report(
    results: list[NoteValueClassification],
) -> list[dict[str, Any]]:
    """列出誤判案例及其詳細資訊。"""
    misclassifications = []
    for r in results:
        if not r.is_correct:
            misclassifications.append({
                "note_id": r.note_id,
                "ground_truth": r.ground_truth,
                "predicted": r.predicted_label,
                "polaris_overall_score": round(r.polaris_overall_score, 4),
                "usage_effectiveness_score": round(r.usage_effectiveness_score, 4),
                "composite_score": round(r.composite_score, 4),
                "polaris_pass_count": r.polaris_metrics.get("core_metrics_pass_count", 0),
                "polaris_overall_status": r.polaris_metrics.get("overall_status", ""),
            })
    return misclassifications
