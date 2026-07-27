"""北極星筆記品質指標計算模組。

提供可機器讀取的筆記品質指標，包含：
- 功能缺口分數（Functional Gap Score）
- 使用者價值分數（User Value Score）
- 來源綁定完整性（Source Binding Integrity）
- 角度多樣性指數（Angle Diversity Index）
- 端到端送達成功率（End-to-End Delivery Success Rate）

所有指標均具備明確的計算公式、判定規則、資料來源與缺值處理方式。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# 指標計算結果狀態
MetricStatus = Literal["calculated", "missing_data", "error"]

# 功能缺口分數門檻
FUNCTIONAL_GAP_THRESHOLD = 0.7  # 70% 以上為合格
# 使用者價值分數門檻
USER_VALUE_THRESHOLD = 0.7  # 70% 以上為合格
# 來源綁定完整性門檻
SOURCE_BINDING_THRESHOLD = 0.8  # 80% 以上為合格
# 角度多樣性門檻
ANGLE_DIVERSITY_THRESHOLD = 0.6  # 60% 以上為合格
# 端到端送達成功率門檻
DELIVERY_SUCCESS_THRESHOLD = 0.9  # 90% 以上為合格

# 功能缺口與使用者價值共用的四面向量化公式；等權重避免隱藏偏好。
QUALITY_SUBSCORE_WEIGHTS = {
    "traceability": 0.25,
    "coverage_breadth": 0.25,
    "necessity_clarity": 0.25,
    "decision_support": 0.25,
}
QUALITY_SCORE_FORMULA = (
    "traceability*0.25 + coverage_breadth*0.25 + "
    "necessity_clarity*0.25 + decision_support*0.25"
)

# 公式、門檻或來源欄位語意改變時必須升版，讓歷次成品可重算與比較。
POLARIS_FORMULA_VERSION = "1.1"
POLARIS_METRIC_DEFINITIONS: dict[str, dict[str, Any]] = {
    "functional_gap_score": {
        "formula": QUALITY_SCORE_FORMULA,
        "source_fields": (
            "binding_report.arguments[].functional_gap",
            "binding_report.arguments[].source_ids",
            "binding_report.arguments[].checks.at_least_one_source",
            "binding_report.arguments[].checks.source_traceable",
            "binding_report.arguments[].checks.no_omitted_traces",
            "binding_report.arguments[].checks.no_extra_traces",
            "binding_report.arguments[].checks.has_functional_gap",
            "binding_report.arguments[].checks.has_related_knowledge",
            "binding_report.arguments[].checks.related_knowledge_consistent",
            "binding_report.arguments[].angle_coverage.covered_facets",
            "binding_report.arguments[].angle_coverage.effective_angle_count",
        ),
    },
    "user_value_score": {
        "formula": QUALITY_SCORE_FORMULA,
        "source_fields": (
            "binding_report.arguments[].user_value",
            "binding_report.arguments[].source_ids",
            "binding_report.arguments[].checks.at_least_one_source",
            "binding_report.arguments[].checks.source_traceable",
            "binding_report.arguments[].checks.no_omitted_traces",
            "binding_report.arguments[].checks.no_extra_traces",
            "binding_report.arguments[].checks.has_user_value",
            "binding_report.arguments[].checks.has_related_knowledge",
            "binding_report.arguments[].checks.related_knowledge_consistent",
            "binding_report.arguments[].angle_coverage.covered_facets",
            "binding_report.arguments[].angle_coverage.effective_angle_count",
        ),
    },
    "source_binding_integrity": {
        "formula": "arguments_pass / total_arguments",
        "source_fields": ("binding_report.arguments[].binding_status",),
    },
    "angle_diversity_index": {
        "formula": "unique_angle_types / expected_angle_types",
        "source_fields": ("binding_report.angle_coverage_summary.unique_angle_types",),
    },
    "delivery_success_rate": {
        "formula": "successful_deliveries / total_attempts",
        "source_fields": (
            "delivery_manifest.delivery_status.primary_note_ready",
            "delivery_manifest.delivery_status.user_channel_sent",
            "delivery_manifest.delivery_status.local_fallback_written",
        ),
    },
}
POLARIS_OVERALL_DECISION_RULE = (
    "error if any metric status=error; poor if any metric status=missing_data; "
    "excellent if pass_count=5; "
    "good if pass_count>=3; acceptable if pass_count>=2; otherwise poor"
)


def _metric_contract(
    metric_name: str,
    *,
    status: MetricStatus,
    passes_threshold: bool,
) -> dict[str, Any]:
    definition = POLARIS_METRIC_DEFINITIONS[metric_name]
    decision = status if status != "calculated" else ("pass" if passes_threshold else "fail")
    return {
        "formula_version": POLARIS_FORMULA_VERSION,
        "formula": definition["formula"],
        "source_fields": list(definition["source_fields"]),
        "decision": decision,
    }


@dataclass
class FunctionalGapScore:
    """功能缺口分數。
    
    計算公式：
        功能缺口分數 = 可追溯性×0.25 + 覆蓋廣度×0.25
                         + 必要性明確度×0.25 + 決策助益×0.25
    
    判定規則：
        - 具體描述：functional_gap 欄位非空且長度 >= 10 字元
        - 分數範圍：0.0 ~ 1.0
        - 合格門檻：>= FUNCTIONAL_GAP_THRESHOLD (0.7)
    
    資料來源：
        - binding_report.arguments[].functional_gap
        - binding_report.arguments[].source_ids / checks / angle_coverage
    
    缺值處理：
        - functional_gap 為空字串：視為無具體描述，不計入分子
        - 論點無 functional_gap 欄位：該論點必要性明確度為 0
        - 總論點數為 0：status = missing_data
    """
    score: float  # 0.0 ~ 1.0
    status: MetricStatus
    threshold: float = FUNCTIONAL_GAP_THRESHOLD
    passes_threshold: bool = False
    
    # 詳細統計
    total_arguments: int = 0
    arguments_with_concrete_gap: int = 0
    arguments_with_empty_gap: int = 0
    arguments_missing_field: int = 0
    
    # 原始資料（用於驗證與追溯）
    raw_functional_gaps: list[str] = field(default_factory=list)
    formula: str = QUALITY_SCORE_FORMULA
    subscores: dict[str, dict[str, Any]] = field(default_factory=dict)
    calculation_basis: list[dict[str, Any]] = field(default_factory=list)
    basis_mode: str = "binding_report"
    
    def __post_init__(self):
        if self.status == "calculated":
            self.passes_threshold = self.score >= self.threshold


@dataclass
class UserValueScore:
    """使用者價值分數。
    
    計算公式：
        使用者價值分數 = 可追溯性×0.25 + 覆蓋廣度×0.25
                         + 必要性明確度×0.25 + 決策助益×0.25
    
    判定規則：
        - 明確使用者價值：user_value 欄位非空且包含關鍵詞「讀者」、「說明」、「理解」
        - 分數範圍：0.0 ~ 1.0
        - 合格門檻：>= USER_VALUE_THRESHOLD (0.7)
    
    資料來源：
        - binding_report.arguments[].user_value
        - binding_report.arguments[].source_ids / checks / angle_coverage
    
    缺值處理：
        - user_value 為空字串：視為無明確價值，不計入分子
        - 論點無 user_value 欄位：該論點必要性明確度為 0
        - 總論點數為 0：status = missing_data
    """
    score: float  # 0.0 ~ 1.0
    status: MetricStatus
    threshold: float = USER_VALUE_THRESHOLD
    passes_threshold: bool = False
    
    # 詳細統計
    total_arguments: int = 0
    arguments_with_clear_value: int = 0
    arguments_with_empty_value: int = 0
    arguments_missing_field: int = 0
    
    # 原始資料（用於驗證與追溯）
    raw_user_values: list[str] = field(default_factory=list)
    formula: str = QUALITY_SCORE_FORMULA
    subscores: dict[str, dict[str, Any]] = field(default_factory=dict)
    calculation_basis: list[dict[str, Any]] = field(default_factory=list)
    basis_mode: str = "binding_report"
    
    def __post_init__(self):
        if self.status == "calculated":
            self.passes_threshold = self.score >= self.threshold


@dataclass
class SourceBindingIntegrity:
    """來源綁定完整性。
    
    計算公式：
        來源綁定完整性 = (binding_status=pass 的論點數) / (總論點數)
    
    判定規則：
        - 只計算 binding_status = "pass" 的論點
        - 分數範圍：0.0 ~ 1.0
        - 合格門檻：>= SOURCE_BINDING_THRESHOLD (0.8)
    
    資料來源：
        - binding_report.arguments[].binding_status
        - binding_report.summary
    
    缺值處理：
        - 論點無 binding_status 欄位：視為缺值，status = missing_data
        - 總論點數為 0：status = missing_data
    """
    score: float  # 0.0 ~ 1.0
    status: MetricStatus
    threshold: float = SOURCE_BINDING_THRESHOLD
    passes_threshold: bool = False
    
    # 詳細統計
    total_arguments: int = 0
    arguments_pass: int = 0
    arguments_fail: int = 0
    arguments_pending: int = 0
    arguments_missing_status: int = 0
    
    def __post_init__(self):
        if self.status == "calculated":
            self.passes_threshold = self.score >= self.threshold


@dataclass
class AngleDiversityIndex:
    """角度多樣性指數。
    
    計算公式：
        角度多樣性 = (唯一角度類型數) / (預期角度類型數)
    
    判定規則：
        - 唯一角度類型數：angle_coverage_summary.unique_angle_types 長度
        - 預期角度類型數：固定為 8（definition, limitation, requirement, effect, procedure, exception, comparison, application）
        - 分數範圍：0.0 ~ 1.0
        - 合格門檻：>= ANGLE_DIVERSITY_THRESHOLD (0.6)
    
    資料來源：
        - binding_report.angle_coverage_summary.unique_angle_types
        - binding_report.angle_coverage_summary.effective_angle_count
    
    缺值處理：
        - angle_coverage_summary 缺失：status = missing_data
        - unique_angle_types 為空：分數為 0.0
    """
    score: float  # 0.0 ~ 1.0
    status: MetricStatus
    threshold: float = ANGLE_DIVERSITY_THRESHOLD
    passes_threshold: bool = False
    
    # 詳細統計
    unique_angle_types: int = 0
    expected_angle_types: int = 8  # 固定預期值
    effective_angle_count: int = 0
    duplicate_ratio: float = 0.0
    
    # 原始資料
    unique_angle_type_names: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.status == "calculated":
            self.passes_threshold = self.score >= self.threshold


@dataclass
class DeliverySuccessRate:
    """端到端送達成功率。
    
    計算公式：
        送達成功率 = (delivery_status 所有布林欄位皆為 True 的次數) / (總處理次數)
    
    判定規則：
        - 所有布林欄位：primary_note_ready, user_channel_sent, local_fallback_written
        - 分數範圍：0.0 ~ 1.0
        - 合格門檻：>= DELIVERY_SUCCESS_THRESHOLD (0.9)
    
    資料來源：
        - delivery_manifest.delivery_status
        - delivery_manifest.status
    
    缺值處理：
        - delivery_status 缺失：status = missing_data
        - 總處理次數為 0：status = missing_data
    """
    score: float  # 0.0 ~ 1.0
    status: MetricStatus
    threshold: float = DELIVERY_SUCCESS_THRESHOLD
    passes_threshold: bool = False
    
    # 詳細統計
    total_attempts: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    
    # 原始資料
    delivery_status_details: list[dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if self.status == "calculated":
            self.passes_threshold = self.score >= self.threshold


@dataclass
class PolarisMetrics:
    """北極星筆記品質指標總覽。
    
    聚合所有品質指標，提供整體品質評估。
    
    整體品質判定：
        - 任一核心指標資料不足：overall_status = "poor"
        - 所有核心指標皆通過門檻：overall_status = "excellent"
        - 至少 3 個核心指標通過門檻：overall_status = "good"
        - 至少 2 個核心指標通過門檻：overall_status = "acceptable"
        - 少於 2 個核心指標通過門檻：overall_status = "poor"
    
    核心指標：
        1. 功能缺口分數
        2. 使用者價值分數
        3. 來源綁定完整性
        4. 角度多樣性指數
        5. 端到端送達成功率
    """
    functional_gap_score: FunctionalGapScore
    user_value_score: UserValueScore
    source_binding_integrity: SourceBindingIntegrity
    angle_diversity_index: AngleDiversityIndex
    delivery_success_rate: DeliverySuccessRate

    # 成品追溯資料；由 binding_report 原樣帶入，不在指標層重新推測。
    traceability_markers: list[dict[str, Any]] = field(default_factory=list)
    claim_source_map: dict[str, list[str]] = field(default_factory=dict)
    citation_span_map: list[dict[str, Any]] = field(default_factory=list)
    
    # 整體評估
    overall_status: Literal["excellent", "good", "acceptable", "poor", "error"] = "poor"
    core_metrics_pass_count: int = 0
    core_metrics_total_count: int = 5
    
    # 計算時間戳
    calculated_at: str = ""
    
    def __post_init__(self):
        # 計算通過門檻的核心指標數量
        core_metrics = [
            self.functional_gap_score,
            self.user_value_score,
            self.source_binding_integrity,
            self.angle_diversity_index,
            self.delivery_success_rate,
        ]
        
        pass_count = sum(
            1 for m in core_metrics 
            if m.status == "calculated" and m.passes_threshold
        )
        self.core_metrics_pass_count = pass_count
        
        # 判定整體品質
        if any(m.status == "error" for m in core_metrics):
            self.overall_status = "error"
        elif any(m.status == "missing_data" for m in core_metrics):
            self.overall_status = "poor"
        elif pass_count == 5:
            self.overall_status = "excellent"
        elif pass_count >= 3:
            self.overall_status = "good"
        elif pass_count >= 2:
            self.overall_status = "acceptable"
        else:
            self.overall_status = "poor"
    
    def to_dict(self) -> dict[str, Any]:
        """序列化為 dict，便於 JSON 輸出。"""
        return {
            "schema": "note_filler.polaris_metrics.v1",
            "formula_version": POLARIS_FORMULA_VERSION,
            "overall_status": self.overall_status,
            "decision": self.overall_status,
            "decision_rule": POLARIS_OVERALL_DECISION_RULE,
            "core_metrics_pass_count": self.core_metrics_pass_count,
            "core_metrics_total_count": self.core_metrics_total_count,
            "calculated_at": self.calculated_at,
            "functional_gap_score": {
                **_metric_contract(
                    "functional_gap_score",
                    status=self.functional_gap_score.status,
                    passes_threshold=self.functional_gap_score.passes_threshold,
                ),
                "score": self.functional_gap_score.score,
                "total_score": self.functional_gap_score.score,
                "status": self.functional_gap_score.status,
                "threshold": self.functional_gap_score.threshold,
                "passes_threshold": self.functional_gap_score.passes_threshold,
                "subscores": self.functional_gap_score.subscores,
                "calculation_basis": self.functional_gap_score.calculation_basis,
                "basis_mode": self.functional_gap_score.basis_mode,
                "total_arguments": self.functional_gap_score.total_arguments,
                "arguments_with_concrete_gap": self.functional_gap_score.arguments_with_concrete_gap,
                "arguments_with_empty_gap": self.functional_gap_score.arguments_with_empty_gap,
                "arguments_missing_field": self.functional_gap_score.arguments_missing_field,
            },
            "user_value_score": {
                **_metric_contract(
                    "user_value_score",
                    status=self.user_value_score.status,
                    passes_threshold=self.user_value_score.passes_threshold,
                ),
                "score": self.user_value_score.score,
                "total_score": self.user_value_score.score,
                "status": self.user_value_score.status,
                "threshold": self.user_value_score.threshold,
                "passes_threshold": self.user_value_score.passes_threshold,
                "subscores": self.user_value_score.subscores,
                "calculation_basis": self.user_value_score.calculation_basis,
                "basis_mode": self.user_value_score.basis_mode,
                "total_arguments": self.user_value_score.total_arguments,
                "arguments_with_clear_value": self.user_value_score.arguments_with_clear_value,
                "arguments_with_empty_value": self.user_value_score.arguments_with_empty_value,
                "arguments_missing_field": self.user_value_score.arguments_missing_field,
            },
            "source_binding_integrity": {
                **_metric_contract(
                    "source_binding_integrity",
                    status=self.source_binding_integrity.status,
                    passes_threshold=self.source_binding_integrity.passes_threshold,
                ),
                "score": self.source_binding_integrity.score,
                "status": self.source_binding_integrity.status,
                "threshold": self.source_binding_integrity.threshold,
                "passes_threshold": self.source_binding_integrity.passes_threshold,
                "total_arguments": self.source_binding_integrity.total_arguments,
                "arguments_pass": self.source_binding_integrity.arguments_pass,
                "arguments_fail": self.source_binding_integrity.arguments_fail,
                "arguments_pending": self.source_binding_integrity.arguments_pending,
                "arguments_missing_status": self.source_binding_integrity.arguments_missing_status,
            },
            "angle_diversity_index": {
                **_metric_contract(
                    "angle_diversity_index",
                    status=self.angle_diversity_index.status,
                    passes_threshold=self.angle_diversity_index.passes_threshold,
                ),
                "score": self.angle_diversity_index.score,
                "status": self.angle_diversity_index.status,
                "threshold": self.angle_diversity_index.threshold,
                "passes_threshold": self.angle_diversity_index.passes_threshold,
                "unique_angle_types": self.angle_diversity_index.unique_angle_types,
                "expected_angle_types": self.angle_diversity_index.expected_angle_types,
                "effective_angle_count": self.angle_diversity_index.effective_angle_count,
                "duplicate_ratio": self.angle_diversity_index.duplicate_ratio,
                "unique_angle_type_names": list(self.angle_diversity_index.unique_angle_type_names),
            },
            "delivery_success_rate": {
                **_metric_contract(
                    "delivery_success_rate",
                    status=self.delivery_success_rate.status,
                    passes_threshold=self.delivery_success_rate.passes_threshold,
                ),
                "score": self.delivery_success_rate.score,
                "status": self.delivery_success_rate.status,
                "threshold": self.delivery_success_rate.threshold,
                "passes_threshold": self.delivery_success_rate.passes_threshold,
                "total_attempts": self.delivery_success_rate.total_attempts,
                "successful_deliveries": self.delivery_success_rate.successful_deliveries,
                "failed_deliveries": self.delivery_success_rate.failed_deliveries,
            },
            "traceability_markers": [
                dict(marker) for marker in self.traceability_markers
            ],
            "claim_source_map": {
                argument_id: list(source_ids)
                for argument_id, source_ids in self.claim_source_map.items()
            },
            "citation_span_map": [dict(span) for span in self.citation_span_map],
        }


_QUALITY_BASIS_CHECKS = (
    "at_least_one_source",
    "source_traceable",
    "no_omitted_traces",
    "no_extra_traces",
    "has_related_knowledge",
    "related_knowledge_consistent",
)


def _has_quantifiable_quality_basis(arg: dict[str, Any], facet: str) -> bool:
    """確認四面向分數所需的布林、清單與數值依據皆可重算。"""
    checks = arg.get("checks")
    coverage = arg.get("angle_coverage")
    facet_check = (
        "has_functional_gap"
        if facet == "necessity:functional_gap"
        else "has_user_value"
    )
    return bool(
        isinstance(arg.get("source_ids"), list)
        and isinstance(checks, dict)
        and all(
            isinstance(checks.get(name), bool)
            for name in (*_QUALITY_BASIS_CHECKS, facet_check)
        )
        and isinstance(coverage, dict)
        and isinstance(coverage.get("covered_facets"), list)
        and all(isinstance(item, str) for item in coverage["covered_facets"])
        and type(coverage.get("effective_angle_count")) is int
    )


def _quality_score_breakdown(
    arguments: list[dict[str, Any]],
    *,
    facet: str,
    clarity_flags: list[bool],
    coverage_rule: str,
    clarity_rule: str,
) -> tuple[float, dict[str, dict[str, Any]], list[dict[str, Any]], str]:
    """以既有 binding_report 訊號產生四子分數與逐論點依據。"""
    total = len(arguments)
    complete_basis = [
        _has_quantifiable_quality_basis(arg, facet) for arg in arguments
    ]
    has_any_basis = any(
        "source_ids" in arg
        or isinstance(arg.get("checks"), dict)
        or isinstance(arg.get("angle_coverage"), dict)
        for arg in arguments
    )

    traceability_flags: list[bool] = []
    coverage_flags: list[bool] = []
    decision_flags: list[bool] = []
    basis: list[dict[str, Any]] = []

    for index, (arg, necessity_clear) in enumerate(zip(arguments, clarity_flags)):
        checks = arg.get("checks") if isinstance(arg.get("checks"), dict) else {}
        coverage = (
            arg.get("angle_coverage")
            if isinstance(arg.get("angle_coverage"), dict)
            else {}
        )
        source_ids = [
            source_id
            for source_id in arg.get("source_ids", [])
            if isinstance(source_id, str) and source_id.strip()
        ] if isinstance(arg.get("source_ids"), list) else []

        if complete_basis[index]:
            traceable = bool(
                source_ids
                and checks.get("at_least_one_source") is True
                and checks.get("source_traceable") is True
                and checks.get("no_omitted_traces") is True
                and checks.get("no_extra_traces") is True
            )
            covered_facets = coverage.get("covered_facets", [])
            covered = bool(
                coverage.get("effective_angle_count") == 1
                and isinstance(covered_facets, list)
                and facet in covered_facets
            )
            decision_support = bool(
                checks.get("has_related_knowledge") is True
                and checks.get("related_knowledge_consistent") is True
            )
        elif has_any_basis:
            traceable = covered = decision_support = False
        else:
            # 保留單項計分函式的舊精簡呼叫；正式聚合會將 fallback 標為 missing_data。
            traceable = covered = decision_support = necessity_clear

        traceability_flags.append(traceable)
        coverage_flags.append(covered)
        decision_flags.append(decision_support)
        basis.append(
            {
                "argument_id": arg.get("argument_id", f"argument:{index}"),
                "source_ids": source_ids,
                "binding_status": arg.get("binding_status"),
                "traceability": traceable,
                "coverage_breadth": covered,
                "necessity_clarity": necessity_clear,
                "decision_support": decision_support,
            }
        )

    rules = {
        "traceability": "有實際來源且來源與追溯識別碼完整對齊的論點比例",
        "coverage_breadth": coverage_rule,
        "necessity_clarity": clarity_rule,
        "decision_support": "關聯知識明示決策助益且與功能缺口及使用者價值一致的論點比例",
    }
    flag_groups = {
        "traceability": traceability_flags,
        "coverage_breadth": coverage_flags,
        "necessity_clarity": clarity_flags,
        "decision_support": decision_flags,
    }
    subscores: dict[str, dict[str, Any]] = {}
    for name, flags in flag_groups.items():
        numerator = sum(flags)
        score = numerator / total if total else 0.0
        weight = QUALITY_SUBSCORE_WEIGHTS[name]
        subscores[name] = {
            "score": score,
            "weight": weight,
            "weighted_score": score * weight,
            "numerator": numerator,
            "denominator": total,
            "rule": rules[name],
        }

    total_score = sum(item["weighted_score"] for item in subscores.values())
    basis_mode = (
        "missing_data" if not arguments
        else "binding_report" if all(complete_basis)
        else "partial_binding_report" if has_any_basis
        else "primary_field_fallback"
    )
    return total_score, subscores, basis, basis_mode


def calculate_functional_gap_score(arguments: list[dict[str, Any]]) -> FunctionalGapScore:
    """計算功能缺口分數。"""
    if not arguments:
        score, subscores, basis, basis_mode = _quality_score_breakdown(
            [],
            facet="necessity:functional_gap",
            clarity_flags=[],
            coverage_rule="具有效且未去重角度及功能缺口 facet 的論點比例",
            clarity_rule="功能缺口非空且至少 10 字元的論點比例",
        )
        return FunctionalGapScore(
            score=score,
            status="missing_data",
            total_arguments=0,
            arguments_with_concrete_gap=0,
            arguments_with_empty_gap=0,
            arguments_missing_field=0,
            raw_functional_gaps=[],
            subscores=subscores,
            calculation_basis=basis,
            basis_mode=basis_mode,
        )
    
    total = len(arguments)
    concrete_count = 0
    empty_count = 0
    missing_count = 0
    raw_gaps = []
    clarity_flags: list[bool] = []
    
    for arg in arguments:
        if "functional_gap" not in arg:
            missing_count += 1
            clarity_flags.append(False)
            continue
        
        gap = arg.get("functional_gap", "")
        raw_gaps.append(gap)
        
        if not isinstance(gap, str):
            gap = str(gap)
        
        # 具體描述：非空且長度 >= 10 字元
        checks = arg.get("checks") if isinstance(arg.get("checks"), dict) else {}
        necessity_clear = bool(
            gap.strip()
            and len(gap.strip()) >= 10
            and checks.get("has_functional_gap") is not False
        )
        clarity_flags.append(necessity_clear)
        if necessity_clear:
            concrete_count += 1
        else:
            empty_count += 1
    
    score, subscores, basis, basis_mode = _quality_score_breakdown(
        arguments,
        facet="necessity:functional_gap",
        clarity_flags=clarity_flags,
        coverage_rule="具有效且未去重角度及功能缺口 facet 的論點比例",
        clarity_rule="功能缺口非空且至少 10 字元的論點比例",
    )
    
    return FunctionalGapScore(
        score=score,
        status="calculated",
        total_arguments=total,
        arguments_with_concrete_gap=concrete_count,
        arguments_with_empty_gap=empty_count,
        arguments_missing_field=missing_count,
        raw_functional_gaps=raw_gaps,
        subscores=subscores,
        calculation_basis=basis,
        basis_mode=basis_mode,
    )


def calculate_user_value_score(arguments: list[dict[str, Any]]) -> UserValueScore:
    """計算使用者價值分數。"""
    if not arguments:
        score, subscores, basis, basis_mode = _quality_score_breakdown(
            [],
            facet="necessity:user_value",
            clarity_flags=[],
            coverage_rule="具有效且未去重角度及使用者價值 facet 的論點比例",
            clarity_rule="使用者價值非空且含讀者、說明或理解語意的論點比例",
        )
        return UserValueScore(
            score=score,
            status="missing_data",
            total_arguments=0,
            arguments_with_clear_value=0,
            arguments_with_empty_value=0,
            arguments_missing_field=0,
            raw_user_values=[],
            subscores=subscores,
            calculation_basis=basis,
            basis_mode=basis_mode,
        )
    
    total = len(arguments)
    clear_count = 0
    empty_count = 0
    missing_count = 0
    raw_values = []
    clarity_flags: list[bool] = []
    
    # 關鍵詞判斷明確使用者價值（支援中英文）
    value_keywords = ["讀者", "說明", "理解", "reader", "understand", "explanation"]
    
    for arg in arguments:
        if "user_value" not in arg:
            missing_count += 1
            clarity_flags.append(False)
            continue
        
        value = arg.get("user_value", "")
        raw_values.append(value)
        
        if not isinstance(value, str):
            value = str(value)
        
        # 明確使用者價值：非空且包含關鍵詞
        checks = arg.get("checks") if isinstance(arg.get("checks"), dict) else {}
        necessity_clear = bool(
            value.strip()
            and any(keyword in value for keyword in value_keywords)
            and checks.get("has_user_value") is not False
        )
        clarity_flags.append(necessity_clear)
        if necessity_clear:
            clear_count += 1
        else:
            empty_count += 1
    
    score, subscores, basis, basis_mode = _quality_score_breakdown(
        arguments,
        facet="necessity:user_value",
        clarity_flags=clarity_flags,
        coverage_rule="具有效且未去重角度及使用者價值 facet 的論點比例",
        clarity_rule="使用者價值非空且含讀者、說明或理解語意的論點比例",
    )
    
    return UserValueScore(
        score=score,
        status="calculated",
        total_arguments=total,
        arguments_with_clear_value=clear_count,
        arguments_with_empty_value=empty_count,
        arguments_missing_field=missing_count,
        raw_user_values=raw_values,
        subscores=subscores,
        calculation_basis=basis,
        basis_mode=basis_mode,
    )


def calculate_source_binding_integrity(arguments: list[dict[str, Any]]) -> SourceBindingIntegrity:
    """計算來源綁定完整性。"""
    if not arguments:
        return SourceBindingIntegrity(
            score=0.0,
            status="missing_data",
            total_arguments=0,
            arguments_pass=0,
            arguments_fail=0,
            arguments_pending=0,
            arguments_missing_status=0,
        )
    
    total = len(arguments)
    pass_count = 0
    fail_count = 0
    pending_count = 0
    missing_count = 0
    
    for arg in arguments:
        status = arg.get("binding_status")
        if status not in ("pass", "fail", "pending_evidence"):
            missing_count += 1
            continue
        
        if status == "pass":
            pass_count += 1
        elif status == "fail":
            fail_count += 1
        elif status == "pending_evidence":
            pending_count += 1
    
    if total == 0:
        return SourceBindingIntegrity(
            score=0.0,
            status="missing_data",
            total_arguments=0,
            arguments_pass=0,
            arguments_fail=0,
            arguments_pending=0,
            arguments_missing_status=0,
        )
    
    score = pass_count / total if total > 0 else 0.0
    
    return SourceBindingIntegrity(
        score=score,
        status="calculated",
        total_arguments=total,
        arguments_pass=pass_count,
        arguments_fail=fail_count,
        arguments_pending=pending_count,
        arguments_missing_status=missing_count,
    )


def calculate_angle_diversity_index(angle_coverage_summary: dict[str, Any]) -> AngleDiversityIndex:
    """計算角度多樣性指數。"""
    if not angle_coverage_summary:
        return AngleDiversityIndex(
            score=0.0,
            status="missing_data",
            unique_angle_types=0,
            expected_angle_types=8,
            effective_angle_count=0,
            duplicate_ratio=0.0,
            unique_angle_type_names=[],
        )
    
    unique_types = angle_coverage_summary.get("unique_angle_types", [])
    effective_count = angle_coverage_summary.get("effective_angle_count", 0)
    duplicate_ratio = angle_coverage_summary.get("duplicate_ratio", 0.0)
    
    if not isinstance(unique_types, list):
        unique_types = []
    
    unique_count = len(unique_types)
    expected_count = 8  # 固定預期值
    
    score = unique_count / expected_count if expected_count > 0 else 0.0
    
    return AngleDiversityIndex(
        score=score,
        status="calculated",
        unique_angle_types=unique_count,
        expected_angle_types=expected_count,
        effective_angle_count=effective_count,
        duplicate_ratio=duplicate_ratio,
        unique_angle_type_names=list(unique_types),
    )


def calculate_delivery_success_rate(delivery_status: dict[str, Any] | None) -> DeliverySuccessRate:
    """計算端到端送達成功率。"""
    if not delivery_status:
        return DeliverySuccessRate(
            score=0.0,
            status="missing_data",
            total_attempts=0,
            successful_deliveries=0,
            failed_deliveries=0,
            delivery_status_details=[],
        )
    
    # 檢查所有布林欄位是否皆為 True
    required_fields = ["primary_note_ready", "user_channel_sent", "local_fallback_written"]
    all_true = all(delivery_status.get(field, False) for field in required_fields)
    
    total_attempts = 1  # 單次處理
    successful = 1 if all_true else 0
    failed = 1 if not all_true else 0
    
    score = successful / total_attempts if total_attempts > 0 else 0.0
    
    return DeliverySuccessRate(
        score=score,
        status="calculated",
        total_attempts=total_attempts,
        successful_deliveries=successful,
        failed_deliveries=failed,
        delivery_status_details=[delivery_status],
    )


def calculate_polaris_metrics(
    binding_report: dict[str, Any],
    delivery_status: dict[str, Any] | None = None,
) -> PolarisMetrics:
    """從 binding_report 與 delivery_status 計算所有北極星指標。"""
    from datetime import datetime
    
    arguments = binding_report.get("arguments", [])
    angle_summary = binding_report.get("angle_coverage_summary", {})
    
    functional_gap_score = calculate_functional_gap_score(arguments)
    user_value_score = calculate_user_value_score(arguments)
    for metric in (functional_gap_score, user_value_score):
        if metric.basis_mode != "binding_report":
            metric.status = "missing_data"
            metric.passes_threshold = False
    source_binding_integrity = calculate_source_binding_integrity(arguments)
    angle_diversity_index = calculate_angle_diversity_index(angle_summary)
    delivery_success_rate = calculate_delivery_success_rate(delivery_status)
    
    return PolarisMetrics(
        functional_gap_score=functional_gap_score,
        user_value_score=user_value_score,
        source_binding_integrity=source_binding_integrity,
        angle_diversity_index=angle_diversity_index,
        delivery_success_rate=delivery_success_rate,
        traceability_markers=list(binding_report.get("traceability_markers") or []),
        claim_source_map=dict(binding_report.get("claim_source_map") or {}),
        citation_span_map=list(binding_report.get("citation_span_map") or []),
        calculated_at=datetime.utcnow().isoformat(),
    )
