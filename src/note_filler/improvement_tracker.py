"""改善追蹤器——依指標分數與功能缺口產生改善優先級報表。

提供可追蹤的改善項目、優先級、責任範圍與驗收條件，輸出機器可讀 JSON。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

# ── 指標定義 ──────────────────────────────────────────────
# P0/P1/P2/P3 權重：阻斷性 > 核心 > 輔助 > 優化
METRIC_PRIORITY_LEVEL: dict[str, str] = {
    "traceability_score": "P0",
    "functional_gap_score": "P1",
    "user_value_score": "P1",
    "source_binding_integrity": "P1",
    "angle_diversity_index": "P2",
    "delivery_success_rate": "P2",
}

METRIC_PRIORITY_WEIGHT: dict[str, float] = {
    "P0": 3.0,
    "P1": 2.0,
    "P2": 1.0,
    "P3": 0.5,
}

METRIC_THRESHOLD: dict[str, float] = {
    "traceability_score": 1.0,
    "functional_gap_score": 0.7,
    "user_value_score": 0.7,
    "source_binding_integrity": 0.8,
    "angle_diversity_index": 0.6,
    "delivery_success_rate": 0.9,
}

# 指標對應的改善項目模板
IMPROVEMENT_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "traceability_score": [
        {
            "id_prefix": "TRC",
            "title": "補齊追溯性不足的論點來源綁定",
            "responsible_scope": [
                "binding_report.arguments[].source_ids",
                "binding_report.arguments[].checks.source_traceable",
            ],
            "impact": {"module": "高", "data": "高", "user": "高"},
            "cost": {"dev": "中", "test": "中", "risk": "中", "dep": "低"},
            "acceptance_query": "traceability_score.degraded == false && traceability_score.penalty == 0.0",
        },
    ],
    "functional_gap_score": [
        {
            "id_prefix": "FGS",
            "title": "提升功能缺口分數至門檻",
            "responsible_scope": [
                "binding_report.arguments[].functional_gap",
                "binding_report.arguments[].angle_coverage",
            ],
            "impact": {"module": "高", "data": "中", "user": "中"},
            "cost": {"dev": "中", "test": "中", "risk": "低", "dep": "低"},
            "acceptance_query": "functional_gap_score.passes_threshold == true",
        },
    ],
    "user_value_score": [
        {
            "id_prefix": "UVS",
            "title": "提升使用者價值分數至門檻",
            "responsible_scope": [
                "binding_report.arguments[].user_value",
                "binding_report.arguments[].angle_coverage",
            ],
            "impact": {"module": "高", "data": "中", "user": "中"},
            "cost": {"dev": "中", "test": "中", "risk": "低", "dep": "低"},
            "acceptance_query": "user_value_score.passes_threshold == true",
        },
    ],
    "source_binding_integrity": [
        {
            "id_prefix": "SBI",
            "title": "提升來源綁定完整性至門檻",
            "responsible_scope": [
                "binding_report.arguments[].binding_status",
            ],
            "impact": {"module": "高", "data": "中", "user": "中"},
            "cost": {"dev": "中", "test": "中", "risk": "低", "dep": "低"},
            "acceptance_query": "source_binding_integrity.passes_threshold == true",
        },
    ],
    "angle_diversity_index": [
        {
            "id_prefix": "ADI",
            "title": "提升角度多樣性指數至門檻",
            "responsible_scope": [
                "binding_report.angle_coverage_summary.unique_angle_types",
            ],
            "impact": {"module": "中", "data": "中", "user": "低"},
            "cost": {"dev": "低", "test": "低", "risk": "低", "dep": "低"},
            "acceptance_query": "angle_diversity_index.passes_threshold == true",
        },
    ],
    "delivery_success_rate": [
        {
            "id_prefix": "DSR",
            "title": "提升端到端送達成功率至門檻",
            "responsible_scope": [
                "delivery_manifest.delivery_status",
            ],
            "impact": {"module": "高", "data": "高", "user": "高"},
            "cost": {"dev": "中", "test": "中", "risk": "低", "dep": "低"},
            "acceptance_query": "delivery_success_rate.passes_threshold == true",
        },
    ],
}


# ── 資料結構 ──────────────────────────────────────────────

LEVEL_SCORE = {"高": 3, "中": 2, "低": 1}


@dataclass
class ImpactAssessment:
    """影響範圍評估。"""
    module_impact: str  # 高/中/低
    data_impact: str  # 高/中/低
    user_impact: str  # 高/中/低

    @property
    def total_score(self) -> float:
        return (
            LEVEL_SCORE.get(self.module_impact, 2)
            + LEVEL_SCORE.get(self.data_impact, 2)
            + LEVEL_SCORE.get(self.user_impact, 2)
        ) / 3


@dataclass
class CostAssessment:
    """改善成本評估。"""
    dev_time: str  # 高/中/低
    test_cost: str  # 高/中/低
    risk_level: str  # 高/中/低
    dependency_complexity: str  # 高/中/低

    @property
    def total_score(self) -> float:
        return (
            LEVEL_SCORE.get(self.dev_time, 2)
            + LEVEL_SCORE.get(self.test_cost, 2)
            + LEVEL_SCORE.get(self.risk_level, 2)
            + LEVEL_SCORE.get(self.dependency_complexity, 2)
        ) / 4


@dataclass
class ImprovementItem:
    """單一改善項目。"""
    id: str
    title: str
    priority_level: str  # P0/P1/P2/P3
    metric_name: str
    baseline_value: float
    target_value: float
    current_value: float | None
    gap_to_threshold: float
    responsible_scope: list[str]
    impact: ImpactAssessment
    cost: CostAssessment
    roi_score: float
    acceptance_query: str
    status: str = "pending"
    assigned_to: str | None = None
    created_at: str = ""
    updated_at: str = ""
    completed_at: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "priority_level": self.priority_level,
            "metric_name": self.metric_name,
            "baseline_value": self.baseline_value,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "gap_to_threshold": self.gap_to_threshold,
            "responsible_scope": list(self.responsible_scope),
            "impact_assessment": {
                "module_impact": self.impact.module_impact,
                "data_impact": self.impact.data_impact,
                "user_impact": self.impact.user_impact,
                "total_impact_score": self.impact.total_score,
            },
            "cost_assessment": {
                "dev_time": self.cost.dev_time,
                "test_cost": self.cost.test_cost,
                "risk_level": self.cost.risk_level,
                "dependency_complexity": self.cost.dependency_complexity,
                "total_cost_score": self.cost.total_score,
            },
            "roi_score": self.roi_score,
            "acceptance_query": self.acceptance_query,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "notes": list(self.notes),
        }


@dataclass
class ImprovementReport:
    """改善追蹤報告。"""
    generated_at: str
    formula_version: str
    total_items: int
    by_priority: dict[str, int]
    by_status: dict[str, int]
    by_metric: dict[str, int]
    items: list[ImprovementItem]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "formula_version": self.formula_version,
            "summary": {
                "total_items": self.total_items,
                "by_priority": dict(self.by_priority),
                "by_status": dict(self.by_status),
                "by_metric": dict(self.by_metric),
            },
            "improvement_items": [item.to_dict() for item in self.items],
        }


# ── 核心邏輯 ──────────────────────────────────────────────

def _extract_metric_score(
    polaris_metrics: dict[str, Any],
    metric_name: str,
) -> tuple[float | None, str]:
    """從 polaris_metrics 提取指標分數與狀態。

    回傳 (score, status)。
    """
    metric_data = polaris_metrics.get(metric_name, {})
    if not isinstance(metric_data, dict):
        return None, "missing_data"
    score = metric_data.get("score")
    status = metric_data.get("status", "missing_data")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        return float(score), str(status)
    return None, str(status)


def _calculate_roi(
    impact_score: float,
    priority_weight: float,
    cost_score: float,
) -> float:
    """計算 ROI = (影響範圍 × 指標權重) / 改善成本。"""
    if cost_score <= 0:
        return 0.0
    return (impact_score * priority_weight) / cost_score


def generate_improvement_items(
    polaris_metrics: dict[str, Any],
    *,
    note_id: str = "",
    source_path: str = "",
) -> list[ImprovementItem]:
    """從單筆 polaris_metrics 產生改善項目。

    只為未通過門檻的指標建立改善項目。
    """
    items: list[ImprovementItem] = []
    now = datetime.now(timezone.utc).isoformat()

    for metric_name, threshold in METRIC_THRESHOLD.items():
        score, status = _extract_metric_score(polaris_metrics, metric_name)
        if score is None:
            # 缺值也是改善項目
            score = 0.0
            status = "missing_data"

        if status == "calculated" and score >= threshold:
            continue  # 已通過門檻，不需要改善

        templates = IMPROVEMENT_TEMPLATES.get(metric_name, [])
        if not templates:
            continue

        template = templates[0]
        priority_level = METRIC_PRIORITY_LEVEL.get(metric_name, "P3")
        priority_weight = METRIC_PRIORITY_WEIGHT.get(priority_level, 0.5)
        gap = threshold - score if score is not None else threshold

        impact = ImpactAssessment(
            module_impact=template["impact"]["module"],
            data_impact=template["impact"]["data"],
            user_impact=template["impact"]["user"],
        )
        cost = CostAssessment(
            dev_time=template["cost"]["dev"],
            test_cost=template["cost"]["test"],
            risk_level=template["cost"]["risk"],
            dependency_complexity=template["cost"]["dep"],
        )
        roi = _calculate_roi(impact.total_score, priority_weight, cost.total_score)

        item_id = f"{template['id_prefix']}-001"
        items.append(ImprovementItem(
            id=item_id,
            title=template["title"],
            priority_level=priority_level,
            metric_name=metric_name,
            baseline_value=score,
            target_value=threshold,
            current_value=score,
            gap_to_threshold=gap,
            responsible_scope=template["responsible_scope"],
            impact=impact,
            cost=cost,
            roi_score=roi,
            acceptance_query=template["acceptance_query"],
            status="pending",
            created_at=now,
            updated_at=now,
            notes=[],
        ))

    # 排序：ROI 降序 > 優先級 > 門檻差距
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    items.sort(key=lambda x: (
        -x.roi_score,
        priority_order.get(x.priority_level, 9),
        -x.gap_to_threshold,
    ))

    return items


def generate_improvement_report(
    records: list[dict[str, Any]],
    *,
    formula_version: str = "1.2",
) -> ImprovementReport:
    """從多筆 MetricsRecord 產生改善追蹤報告。

    records: MetricsRecord 的 to_dict() 結果列表（含 polaris_metrics）。
    """
    all_items: list[ImprovementItem] = []
    seen_metrics: set[str] = set()

    for record in records:
        polaris_metrics = record.get("polaris_metrics", {})
        note_id = record.get("note_id", "")
        source_path = record.get("source_path", "")

        items = generate_improvement_items(
            polaris_metrics,
            note_id=note_id,
            source_path=source_path,
        )
        for item in items:
            # 去重：同一指標只保留最差的改善項目
            key = item.metric_name
            if key not in seen_metrics:
                seen_metrics.add(key)
                all_items.append(item)

    # 統計
    by_priority: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_metric: dict[str, int] = {}
    for item in all_items:
        by_priority[item.priority_level] = by_priority.get(item.priority_level, 0) + 1
        by_status[item.status] = by_status.get(item.status, 0) + 1
        by_metric[item.metric_name] = by_metric.get(item.metric_name, 0) + 1

    return ImprovementReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        formula_version=formula_version,
        total_items=len(all_items),
        by_priority=by_priority,
        by_status=by_status,
        by_metric=by_metric,
        items=all_items,
    )
