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


@dataclass
class FunctionalGapScore:
    """功能缺口分數。
    
    計算公式：
        功能缺口分數 = (具體描述的功能缺口數) / (總論點數)
    
    判定規則：
        - 具體描述：functional_gap 欄位非空且長度 >= 10 字元
        - 分數範圍：0.0 ~ 1.0
        - 合格門檻：>= FUNCTIONAL_GAP_THRESHOLD (0.7)
    
    資料來源：
        - binding_report.arguments[].functional_gap
        - binding_report.arguments[].binding_status
    
    缺值處理：
        - functional_gap 為空字串：視為無具體描述，不計入分子
        - 論點無 functional_gap 欄位：視為缺值，status = missing_data
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
    
    def __post_init__(self):
        if self.status == "calculated":
            self.passes_threshold = self.score >= self.threshold


@dataclass
class UserValueScore:
    """使用者價值分數。
    
    計算公式：
        使用者價值分數 = (明確使用者價值的論點數) / (總論點數)
    
    判定規則：
        - 明確使用者價值：user_value 欄位非空且包含關鍵詞「讀者」、「說明」、「理解」
        - 分數範圍：0.0 ~ 1.0
        - 合格門檻：>= USER_VALUE_THRESHOLD (0.7)
    
    資料來源：
        - binding_report.arguments[].user_value
        - binding_report.arguments[].binding_status
    
    缺值處理：
        - user_value 為空字串：視為無明確價值，不計入分子
        - 論點無 user_value 欄位：視為缺值，status = missing_data
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
            "overall_status": self.overall_status,
            "core_metrics_pass_count": self.core_metrics_pass_count,
            "core_metrics_total_count": self.core_metrics_total_count,
            "calculated_at": self.calculated_at,
            "functional_gap_score": {
                "score": self.functional_gap_score.score,
                "status": self.functional_gap_score.status,
                "threshold": self.functional_gap_score.threshold,
                "passes_threshold": self.functional_gap_score.passes_threshold,
                "total_arguments": self.functional_gap_score.total_arguments,
                "arguments_with_concrete_gap": self.functional_gap_score.arguments_with_concrete_gap,
                "arguments_with_empty_gap": self.functional_gap_score.arguments_with_empty_gap,
                "arguments_missing_field": self.functional_gap_score.arguments_missing_field,
            },
            "user_value_score": {
                "score": self.user_value_score.score,
                "status": self.user_value_score.status,
                "threshold": self.user_value_score.threshold,
                "passes_threshold": self.user_value_score.passes_threshold,
                "total_arguments": self.user_value_score.total_arguments,
                "arguments_with_clear_value": self.user_value_score.arguments_with_clear_value,
                "arguments_with_empty_value": self.user_value_score.arguments_with_empty_value,
                "arguments_missing_field": self.user_value_score.arguments_missing_field,
            },
            "source_binding_integrity": {
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
                "score": self.delivery_success_rate.score,
                "status": self.delivery_success_rate.status,
                "threshold": self.delivery_success_rate.threshold,
                "passes_threshold": self.delivery_success_rate.passes_threshold,
                "total_attempts": self.delivery_success_rate.total_attempts,
                "successful_deliveries": self.delivery_success_rate.successful_deliveries,
                "failed_deliveries": self.delivery_success_rate.failed_deliveries,
            },
        }


def calculate_functional_gap_score(arguments: list[dict[str, Any]]) -> FunctionalGapScore:
    """計算功能缺口分數。"""
    if not arguments:
        return FunctionalGapScore(
            score=0.0,
            status="missing_data",
            total_arguments=0,
            arguments_with_concrete_gap=0,
            arguments_with_empty_gap=0,
            arguments_missing_field=0,
            raw_functional_gaps=[],
        )
    
    total = len(arguments)
    concrete_count = 0
    empty_count = 0
    missing_count = 0
    raw_gaps = []
    
    for arg in arguments:
        if "functional_gap" not in arg:
            missing_count += 1
            continue
        
        gap = arg.get("functional_gap", "")
        raw_gaps.append(gap)
        
        if not isinstance(gap, str):
            gap = str(gap)
        
        # 具體描述：非空且長度 >= 10 字元
        if gap.strip() and len(gap.strip()) >= 10:
            concrete_count += 1
        else:
            empty_count += 1
    
    if total == 0:
        return FunctionalGapScore(
            score=0.0,
            status="missing_data",
            total_arguments=0,
            arguments_with_concrete_gap=0,
            arguments_with_empty_gap=0,
            arguments_missing_field=0,
            raw_functional_gaps=[],
        )
    
    score = concrete_count / total if total > 0 else 0.0
    
    return FunctionalGapScore(
        score=score,
        status="calculated",
        total_arguments=total,
        arguments_with_concrete_gap=concrete_count,
        arguments_with_empty_gap=empty_count,
        arguments_missing_field=missing_count,
        raw_functional_gaps=raw_gaps,
    )


def calculate_user_value_score(arguments: list[dict[str, Any]]) -> UserValueScore:
    """計算使用者價值分數。"""
    if not arguments:
        return UserValueScore(
            score=0.0,
            status="missing_data",
            total_arguments=0,
            arguments_with_clear_value=0,
            arguments_with_empty_value=0,
            arguments_missing_field=0,
            raw_user_values=[],
        )
    
    total = len(arguments)
    clear_count = 0
    empty_count = 0
    missing_count = 0
    raw_values = []
    
    # 關鍵詞判斷明確使用者價值（支援中英文）
    value_keywords = ["讀者", "說明", "理解", "reader", "understand", "explanation"]
    
    for arg in arguments:
        if "user_value" not in arg:
            missing_count += 1
            continue
        
        value = arg.get("user_value", "")
        raw_values.append(value)
        
        if not isinstance(value, str):
            value = str(value)
        
        # 明確使用者價值：非空且包含關鍵詞
        if value.strip() and any(keyword in value for keyword in value_keywords):
            clear_count += 1
        else:
            empty_count += 1
    
    if total == 0:
        return UserValueScore(
            score=0.0,
            status="missing_data",
            total_arguments=0,
            arguments_with_clear_value=0,
            arguments_with_empty_value=0,
            arguments_missing_field=0,
            raw_user_values=[],
        )
    
    score = clear_count / total if total > 0 else 0.0
    
    return UserValueScore(
        score=score,
        status="calculated",
        total_arguments=total,
        arguments_with_clear_value=clear_count,
        arguments_with_empty_value=empty_count,
        arguments_missing_field=missing_count,
        raw_user_values=raw_values,
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
    source_binding_integrity = calculate_source_binding_integrity(arguments)
    angle_diversity_index = calculate_angle_diversity_index(angle_summary)
    delivery_success_rate = calculate_delivery_success_rate(delivery_status)
    
    return PolarisMetrics(
        functional_gap_score=functional_gap_score,
        user_value_score=user_value_score,
        source_binding_integrity=source_binding_integrity,
        angle_diversity_index=angle_diversity_index,
        delivery_success_rate=delivery_success_rate,
        calculated_at=datetime.utcnow().isoformat(),
    )
