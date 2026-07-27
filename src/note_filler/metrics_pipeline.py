"""北極星指標週期性計算管線。

提供持續計算北極星品質指標的資料蒐集、轉換與彙總功能：
- 從 delivery_manifest.json 蒐集指標資料
- 轉換與彙總週期性結果
- 儲存可查詢的結果
- 執行失敗告警
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MetricsCollectionConfig:
    """指標蒐集配置。"""
    # 掃描目錄
    scan_dirs: list[Path] = field(default_factory=list)
    # 輸出目錄
    output_dir: Path = field(default_factory=lambda: Path("metrics_output"))
    # 是否遞迴掃描子目錄
    recursive: bool = True
    # 檔案模式
    file_pattern: str = "delivery_manifest.json"
    # 告警門檻
    alert_thresholds: dict[str, float] = field(default_factory=lambda: {
        "functional_gap_score": 0.5,
        "user_value_score": 0.5,
        "source_binding_integrity": 0.7,
        "angle_diversity_index": 0.4,
        "delivery_success_rate": 0.8,
    })


@dataclass
class MetricsRecord:
    """單筆指標記錄。"""
    # 來源資訊
    source_path: str
    manifest_path: str
    collection_time: str
    
    # 北極星指標
    polaris_metrics: dict[str, Any]
    
    # 原始 delivery_manifest 資料
    delivery_manifest: dict[str, Any]


@dataclass
class MetricsSummary:
    """指標彙總統計。"""
    # 彙總時間
    summary_time: str
    
    # 統計期間
    period_start: str
    period_end: str
    
    # 處理統計
    total_manifests: int = 0
    successful_collections: int = 0
    failed_collections: int = 0
    
    # 指標統計
    metrics_records: list[MetricsRecord] = field(default_factory=list)
    
    # 平均分數
    average_scores: dict[str, float] = field(default_factory=dict)
    
    # 品質分佈
    quality_distribution: dict[str, int] = field(default_factory=dict)
    
    # 告警記錄
    alerts: list[dict[str, Any]] = field(default_factory=list)


def collect_metrics_from_manifest(
    manifest_path: Path,
    config: MetricsCollectionConfig,
) -> MetricsRecord | None:
    """從單一 delivery_manifest 蒐集指標。
    
    回傳 MetricsRecord 或 None（若蒐集失敗）。
    """
    try:
        if not manifest_path.exists():
            logger.warning(f"Manifest 不存在: {manifest_path}")
            return None
        
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        
        # 檢查是否包含 polaris_metrics
        polaris_metrics = manifest_data.get("polaris_metrics")
        if not polaris_metrics:
            logger.warning(f"Manifest 缺少 polaris_metrics: {manifest_path}")
            return None
        
        # 檢查 schema 版本
        schema = polaris_metrics.get("schema")
        if schema != "note_filler.polaris_metrics.v1":
            logger.warning(
                f"Manifest schema 版本不符: {manifest_path}, "
                f"期望 note_filler.polaris_metrics.v1, 實際 {schema}"
            )
            return None
        
        source_path = manifest_data.get("input_path", "")
        collection_time = datetime.now(timezone.utc).isoformat()
        
        return MetricsRecord(
            source_path=source_path,
            manifest_path=str(manifest_path),
            collection_time=collection_time,
            polaris_metrics=polaris_metrics,
            delivery_manifest=manifest_data,
        )
    except Exception as e:
        logger.error(f"蒐集指標失敗: {manifest_path}, 錯誤: {e}")
        return None


def scan_and_collect_metrics(
    config: MetricsCollectionConfig,
) -> list[MetricsRecord]:
    """掃描目錄並蒐集所有指標。
    
    回傳成功蒐集的 MetricsRecord 列表。
    """
    records: list[MetricsRecord] = []
    
    for scan_dir in config.scan_dirs:
        if not scan_dir.exists():
            logger.warning(f"掃描目錄不存在: {scan_dir}")
            continue
        
        # 遞迴或非遞迴掃描
        if config.recursive:
            manifest_files = list(scan_dir.glob(f"**/{config.file_pattern}"))
        else:
            manifest_files = list(scan_dir.glob(config.file_pattern))
        
        logger.info(f"在 {scan_dir} 找到 {len(manifest_files)} 個 manifest 檔案")
        
        for manifest_path in manifest_files:
            record = collect_metrics_from_manifest(manifest_path, config)
            if record:
                records.append(record)
    
    return records


def calculate_summary_statistics(
    records: list[MetricsRecord],
    config: MetricsCollectionConfig,
) -> MetricsSummary:
    """計算指標彙總統計。"""
    if not records:
        return MetricsSummary(
            summary_time=datetime.now(timezone.utc).isoformat(),
            period_start="",
            period_end="",
        )
    
    # 計算時間範圍
    collection_times = [
        datetime.fromisoformat(r.collection_time.replace("Z", "+00:00"))
        for r in records
    ]
    period_start = min(collection_times).isoformat()
    period_end = max(collection_times).isoformat()
    
    # 初始化統計
    summary = MetricsSummary(
        summary_time=datetime.now(timezone.utc).isoformat(),
        period_start=period_start,
        period_end=period_end,
        total_manifests=len(records),
        successful_collections=len(records),
        failed_collections=0,
        metrics_records=records,
    )
    
    # 計算平均分數
    metric_names = [
        "functional_gap_score",
        "user_value_score",
        "source_binding_integrity",
        "angle_diversity_index",
        "delivery_success_rate",
    ]
    
    for metric_name in metric_names:
        scores = []
        for record in records:
            metric_data = record.polaris_metrics.get(metric_name, {})
            if metric_data.get("status") == "calculated":
                scores.append(metric_data.get("score", 0.0))
        
        if scores:
            summary.average_scores[metric_name] = sum(scores) / len(scores)
        else:
            summary.average_scores[metric_name] = 0.0
    
    # 統計品質分佈
    quality_counts = {"excellent": 0, "good": 0, "acceptable": 0, "poor": 0, "error": 0}
    for record in records:
        overall_status = record.polaris_metrics.get("overall_status", "error")
        if overall_status in quality_counts:
            quality_counts[overall_status] += 1
        else:
            quality_counts["error"] += 1
    summary.quality_distribution = quality_counts
    
    # 檢查告警門檻
    for metric_name, threshold in config.alert_thresholds.items():
        avg_score = summary.average_scores.get(metric_name, 0.0)
        if avg_score < threshold:
            alert = {
                "metric_name": metric_name,
                "threshold": threshold,
                "actual_value": avg_score,
                "alert_time": datetime.now(timezone.utc).isoformat(),
                "severity": "warning" if avg_score >= threshold * 0.8 else "critical",
            }
            summary.alerts.append(alert)
            logger.warning(
                f"告警: {metric_name} 平均分數 {avg_score:.3f} 低於門檻 {threshold}"
            )
    
    return summary


def save_metrics_summary(
    summary: MetricsSummary,
    config: MetricsCollectionConfig,
) -> Path:
    """儲存指標彙總結果。"""
    config.output_dir.mkdir(parents=True, exist_ok=True)
    
    # 產生檔名（含時間戳）
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = config.output_dir / f"metrics_summary_{timestamp}.json"
    
    # 序列化
    summary_data = {
        "summary_time": summary.summary_time,
        "period_start": summary.period_start,
        "period_end": summary.period_end,
        "total_manifests": summary.total_manifests,
        "successful_collections": summary.successful_collections,
        "failed_collections": summary.failed_collections,
        "average_scores": summary.average_scores,
        "quality_distribution": summary.quality_distribution,
        "alerts": summary.alerts,
        "records_count": len(summary.metrics_records),
    }
    
    output_path.write_text(
        json.dumps(summary_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    
    logger.info(f"指標彙總已儲存至: {output_path}")
    return output_path


def save_detailed_records(
    records: list[MetricsRecord],
    config: MetricsCollectionConfig,
) -> Path:
    """儲存詳細指標記錄。"""
    config.output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = config.output_dir / f"metrics_records_{timestamp}.json"
    
    # 序列化記錄
    records_data = [
        {
            "source_path": r.source_path,
            "manifest_path": r.manifest_path,
            "collection_time": r.collection_time,
            "polaris_metrics": r.polaris_metrics,
        }
        for r in records
    ]
    
    output_path.write_text(
        json.dumps(records_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    
    logger.info(f"詳細記錄已儲存至: {output_path}")
    return output_path


def run_metrics_pipeline(config: MetricsCollectionConfig) -> MetricsSummary:
    """執行完整的指標計算管線。
    
    步驟：
    1. 掃描目錄並蒐集指標
    2. 計算彙總統計
    3. 儲存彙總結果
    4. 儲存詳細記錄
    5. 檢查並發送告警
    
    回傳 MetricsSummary。
    """
    logger.info("開始執行指標計算管線")
    
    # 1. 蒐集指標
    records = scan_and_collect_metrics(config)
    logger.info(f"成功蒐集 {len(records)} 筆指標記錄")
    
    # 2. 計算彙總
    summary = calculate_summary_statistics(records, config)
    
    # 3. 儲存結果
    save_metrics_summary(summary, config)
    save_detailed_records(records, config)
    
    # 4. 處理告警
    if summary.alerts:
        logger.warning(f"觸發 {len(summary.alerts)} 個告警")
        for alert in summary.alerts:
            logger.warning(
                f"告警: {alert['metric_name']} = {alert['actual_value']:.3f} "
                f"< {alert['threshold']} (嚴重性: {alert['severity']})"
            )
    
    logger.info("指標計算管線執行完成")
    return summary


def query_metrics_history(
    config: MetricsCollectionConfig,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """查詢歷史指標彙總。
    
    回傳最近的 limit 筆彙總記錄。
    """
    if not config.output_dir.exists():
        return []
    
    # 找出所有彙總檔案
    summary_files = sorted(
        config.output_dir.glob("metrics_summary_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    
    # 讀取最近的 limit 筆
    histories = []
    for summary_file in summary_files[:limit]:
        try:
            data = json.loads(summary_file.read_text(encoding="utf-8"))
            data["source_file"] = str(summary_file)
            histories.append(data)
        except Exception as e:
            logger.error(f"讀取彙總檔案失敗: {summary_file}, 錯誤: {e}")
    
    return histories


def query_latest_summary(config: MetricsCollectionConfig) -> dict[str, Any] | None:
    """查詢最新的指標彙總。
    
    回傳最新的彙總記錄，若無則回傳 None。
    """
    histories = query_metrics_history(config, limit=1)
    return histories[0] if histories else None
