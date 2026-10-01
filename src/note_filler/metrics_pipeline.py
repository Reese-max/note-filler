"""北極星指標週期性計算管線。

提供持續計算北極星品質指標的資料蒐集、轉換與彙總功能：
- 從 delivery_manifest.json 蒐集指標資料（含 note_id 識別碼）
- 轉換與彙總週期性結果
- 儲存可查詢的歷史結果（帶時間戳與筆記識別碼）
- 提供可重跑機制（rerun_note）
- 執行結構化失敗告警（MetricsAlert）
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .sidecars import (
    DELIVERY_MANIFEST_NAME,
    delivery_manifest_path,
    is_receipt_file_name,
    output_identity_key,
    receipt_input_identity,
    receipt_matches_output,
    receipt_output_identity,
    resolve_binding_report_path,
    resolve_delivery_manifest_path,
    resolve_manifest_for_update,
    write_manifest_and_latest,
)

logger = logging.getLogger(__name__)

PIPELINE_METRICS_HISTORY_NAME = "metrics_history.jsonl"
OUTPUT_MARKDOWN_BASELINE_NAME = "output_markdown_baseline.jsonl"
QUALITY_DEBT_LEADERBOARD_NAME = "quality_debt_leaderboard.json"


def derive_note_id(source_path: str) -> str:
    """從輸入路徑產生穩定的筆記識別碼。

    使用路徑的 sha256 前 12 碼，確保同一筆記在不同環境下 ID 一致。
    """
    normalized = source_path.replace("\\", "/").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


@contextmanager
def _locked_history(history_path: Path):
    """鎖住單一 JSONL 歷史檔，讓查重與追加成為同一交易。"""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a+", encoding="utf-8", newline="") as history:
        history.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(history.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield history
            finally:
                history.seek(0)
                msvcrt.locking(history.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(history.fileno(), fcntl.LOCK_EX)
            try:
                yield history
            finally:
                fcntl.flock(history.fileno(), fcntl.LOCK_UN)


def _pipeline_product_hash(correction, binding_report: dict[str, Any]) -> str:
    """以成品內容與既有綁定報告建立穩定識別，不改寫成品。"""
    product = {
        "segments": [
            {
                "type": getattr(segment, "type", None),
                "text": getattr(segment, "text", None),
                "confidence": getattr(segment, "confidence", None),
                "source_id": getattr(segment, "source_id", None),
                "source_ids": list(getattr(segment, "source_ids", None) or []),
                "traceability": list(getattr(segment, "traceability", None) or []),
                "citation_spans": list(getattr(segment, "citation_spans", None) or []),
            }
            for segment in getattr(correction, "segments", ())
        ],
        "binding_report": binding_report,
    }
    payload = json.dumps(
        product,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_pipeline_metrics(source_path: str, correction) -> dict[str, Any]:
    """以既有量測模組記錄正式管線成品；同一成品只追加一次。"""
    from .binding_report import build_binding_report
    from .metrics import calculate_polaris_metrics

    canonical_source_path = str(Path(source_path).resolve())
    try:
        binding_report = build_binding_report(correction)
    except ValueError as exc:
        logger.warning(
            "metrics_unavailable note_id=%s reason=%s",
            derive_note_id(canonical_source_path),
            exc,
        )
        binding_report = {"metrics_unavailable": str(exc)}

    arguments = binding_report.get("arguments")
    metrics_available = isinstance(arguments, list) and bool(arguments)
    polaris_metrics = (
        calculate_polaris_metrics(binding_report).to_dict()
        if metrics_available
        else None
    )
    history_path = Path(source_path).parent / PIPELINE_METRICS_HISTORY_NAME
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note_id": derive_note_id(canonical_source_path),
        "product_hash": _pipeline_product_hash(correction, binding_report),
        "status": "calculated" if metrics_available else "metrics_unavailable",
        "traceability": (
            polaris_metrics["traceability_score"]["score"]
            if polaris_metrics is not None
            else None
        ),
        "angles_per_topic": (
            polaris_metrics["angle_diversity_index"]["effective_angle_count"]
            if polaris_metrics is not None
            else None
        ),
    }

    try:
        with _locked_history(history_path) as history:
            history.seek(0)
            history_text = history.read()
            for line_number, line in enumerate(history_text.splitlines(), 1):
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "metrics_history_corrupt_line line=%d path=%s error=%s",
                        line_number,
                        history_path,
                        exc,
                    )
                    raise ValueError(
                        f"指標歷史含損壞 JSONL 第 {line_number} 行: {history_path}"
                    ) from exc
                if not isinstance(existing, dict):
                    logger.warning(
                        "metrics_history_corrupt_line line=%d path=%s non-object",
                        line_number,
                        history_path,
                    )
                    raise ValueError(
                        f"指標歷史含非物件 JSONL 第 {line_number} 行: {history_path}"
                    )
                if (
                    existing.get("note_id") == record["note_id"]
                    and existing.get("product_hash") == record["product_hash"]
                ):
                    return existing

            history.seek(0, 2)
            if history_text and not history_text.endswith(("\n", "\r")):
                history.write("\n")
            history.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        logger.exception(
            "metrics_history_write_failed note_id=%s path=%s",
            record["note_id"],
            history_path,
        )
        raise
    return record


@dataclass
class OutputMarkdownBaselineScan:
    """唯讀成品掃描結果。"""

    scanned_count: int
    created_count: int
    records: list[dict[str, Any]]


def _load_quality_debt_metrics(
    markdown_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """讀取既有結構化 Markdown 量測；舊格式絕不猜測主題。"""
    from .markdown_quality_metrics import measure_markdown_quality_file

    quality = measure_markdown_quality_file(markdown_path)
    if quality["status"] != "calculated":
        return {
            "quality_debt_status": "unknown",
            "quality_debt_reason": quality["reason"],
            "unqualified_source_argument_count": None,
            "single_angle_topic_count": None,
            "gap_details": quality["gap_details"],
        }, quality

    return {
        "quality_debt_status": "calculated",
        "quality_debt_reason": None,
        "unqualified_source_argument_count": quality[
            "unqualified_source_argument_count"
        ],
        "single_angle_topic_count": quality["single_angle_topic_count"],
        "gap_details": quality["gap_details"],
    }, quality


def _load_output_metrics(
    markdown_path: Path,
    content_hash: str,
) -> tuple[str, float | None, float | None, dict[str, Any]]:
    """讀取既有結構化量測，舊旁車格式保留相容但主題標為 unknown。"""
    from .binding_report import parse_binding_report
    from .metrics import calculate_polaris_metrics

    quality_debt, quality = _load_quality_debt_metrics(markdown_path)
    if quality_debt["quality_debt_status"] == "calculated":
        return (
            "calculated",
            float(quality["traceability"]),
            float(quality["angles_per_topic"]),
            quality_debt,
        )

    manifest_path = resolve_delivery_manifest_path(markdown_path)
    if not manifest_path.exists():
        return "metrics_unavailable", None, None, quality_debt

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "output_metrics_unavailable path=%s reason=%s",
            markdown_path,
            exc,
        )
        return "metrics_unavailable", None, None, quality_debt

    if not isinstance(manifest, dict):
        return "metrics_unavailable", None, None, quality_debt
    if receipt_output_identity(manifest) and not receipt_matches_output(manifest, markdown_path):
        logger.warning("output_metrics_unavailable path=%s reason=wrong_note_receipt", markdown_path)
        return "metrics_unavailable", None, None, quality_debt
    manifest_hash = manifest.get("content_hash")
    if manifest_hash and manifest_hash != content_hash[:16]:
        logger.warning("output_metrics_unavailable path=%s reason=content_hash_mismatch", markdown_path)
        return "metrics_unavailable", None, None, quality_debt

    report_path = resolve_binding_report_path(markdown_path, manifest)
    if not report_path.exists():
        return "metrics_unavailable", None, None, quality_debt
    expected_report_hash = manifest.get("binding_report_content_hash")
    if expected_report_hash:
        try:
            actual_report_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()
        except OSError:
            return "metrics_unavailable", None, None, quality_debt
        if actual_report_hash != expected_report_hash:
            logger.warning("output_metrics_unavailable path=%s reason=report_hash_mismatch", markdown_path)
            return "metrics_unavailable", None, None, quality_debt

    try:
        binding_report = parse_binding_report(
            json.loads(report_path.read_text(encoding="utf-8"))
        )
        if not binding_report["arguments"]:
            return "metrics_unavailable", None, None, quality_debt
        delivery_status = manifest.get("delivery_status")
        metrics = calculate_polaris_metrics(
            binding_report,
            delivery_status if isinstance(delivery_status, dict) else None,
        ).to_dict()
        traceability = metrics["traceability_score"]["score"]
        angles_per_topic = metrics["angle_diversity_index"]["effective_angle_count"]
    except (json.JSONDecodeError, OSError, ValueError, KeyError, TypeError) as exc:
        logger.warning(
            "output_metrics_unavailable path=%s reason=%s",
            markdown_path,
            exc,
        )
        return "metrics_unavailable", None, None, quality_debt

    if (
        not isinstance(traceability, (int, float))
        or isinstance(traceability, bool)
        or not isinstance(angles_per_topic, (int, float))
        or isinstance(angles_per_topic, bool)
    ):
        return "metrics_unavailable", None, None, quality_debt
    return "calculated", float(traceability), float(angles_per_topic), quality_debt


def scan_output_markdown_baselines(
    output_root: Path,
    history_path: Path,
    *,
    batch_size: int | None = None,
) -> OutputMarkdownBaselineScan:
    """掃描成品 Markdown，追加路徑與內容都唯一的唯讀基線紀錄。"""
    if batch_size is not None and batch_size <= 0:
        raise ValueError("batch_size 必須為正整數")
    if not output_root.is_dir():
        raise FileNotFoundError(f"成品目錄不存在: {output_root}")

    markdown_paths = sorted(
        path for path in output_root.rglob("*")
        if path.is_file() and path.suffix.lower() == ".md"
    )

    try:
        with _locked_history(history_path) as history:
            history.seek(0)
            history_text = history.read()
            existing_keys = set()
            for line_number, line in enumerate(history_text.splitlines(), 1):
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "output_metrics_baseline_corrupt_line line=%d path=%s error=%s",
                        line_number,
                        history_path,
                        exc,
                    )
                    raise ValueError(
                        f"成品基線含損壞 JSONL 第 {line_number} 行: {history_path}"
                    ) from exc
                if not isinstance(existing, dict):
                    raise ValueError(
                        f"成品基線含非物件 JSONL 第 {line_number} 行: {history_path}"
                    )
                existing_keys.add((existing.get("artifact_path"), existing.get("content_hash")))

            candidates = []
            for markdown_path in markdown_paths:
                artifact_path = markdown_path.relative_to(output_root).as_posix()
                content_hash = hashlib.sha256(markdown_path.read_bytes()).hexdigest()
                if (artifact_path, content_hash) in existing_keys:
                    continue
                if batch_size is not None and len(candidates) >= batch_size:
                    break
                status, traceability, angles_per_topic, quality_debt = _load_output_metrics(
                    markdown_path,
                    content_hash,
                )
                candidates.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "note_id": derive_note_id(artifact_path),
                    "artifact_path": artifact_path,
                    "content_hash": content_hash,
                    "status": status,
                    "traceability": traceability,
                    "angles_per_topic": angles_per_topic,
                    **quality_debt,
                })

            if candidates:
                history.seek(0, 2)
                if history_text and not history_text.endswith(("\n", "\r")):
                    history.write("\n")
                for record in candidates:
                    history.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        logger.exception(
            "output_metrics_baseline_write_failed path=%s",
            history_path,
        )
        raise

    return OutputMarkdownBaselineScan(
        scanned_count=len(candidates),
        created_count=len(candidates),
        records=candidates,
    )


def generate_quality_debt_leaderboard(
    baseline_path: Path,
    leaderboard_path: Path,
) -> dict[str, Any]:
    """從完整成品基線產生排行榜；不重建既有量測或推測主題。"""
    baseline_path = Path(baseline_path)
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        baseline_path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"成品基線含損壞 JSONL 第 {line_number} 行: {baseline_path}"
            ) from exc
        if not isinstance(record, dict):
            raise ValueError(f"成品基線第 {line_number} 行必須為 JSON 物件")
        for key in ("note_id", "artifact_path", "content_hash", "status"):
            if not isinstance(record.get(key), str) or not record[key]:
                raise ValueError(f"成品基線第 {line_number} 行缺少 {key}")
        if record["status"] not in ("calculated", "metrics_unavailable"):
            raise ValueError(f"成品基線第 {line_number} 行 status 非法")

        traceability = record.get("traceability")
        if traceability is not None and (
            not isinstance(traceability, (int, float))
            or isinstance(traceability, bool)
        ):
            raise ValueError(f"成品基線第 {line_number} 行 traceability 型別錯誤")
        angles = record.get("angles_per_topic")
        if angles is not None and (
            not isinstance(angles, (int, float)) or isinstance(angles, bool)
        ):
            raise ValueError(f"成品基線第 {line_number} 行 angles_per_topic 型別錯誤")

        quality_debt_keys = {
            "quality_debt_status",
            "quality_debt_reason",
            "unqualified_source_argument_count",
            "single_angle_topic_count",
            "gap_details",
        }
        if not quality_debt_keys & record.keys():
            # 舊基線沒有可靠 topic 欄位，僅能如實列為 unknown。
            record.update({
                "quality_debt_status": "unknown",
                "quality_debt_reason": "legacy_baseline_missing_structured_quality_metadata",
                "unqualified_source_argument_count": None,
                "single_angle_topic_count": None,
                "gap_details": [{
                    "kind": "topic_assignment_unknown",
                    "reason": "legacy_baseline_missing_structured_quality_metadata",
                }],
            })
        elif quality_debt_keys - record.keys():
            raise ValueError(f"成品基線第 {line_number} 行品質欠債欄位不完整")

        debt_status = record["quality_debt_status"]
        debt_reason = record["quality_debt_reason"]
        unqualified_count = record["unqualified_source_argument_count"]
        single_angle_count = record["single_angle_topic_count"]
        gap_details = record["gap_details"]
        if debt_status not in ("calculated", "unknown"):
            raise ValueError(f"成品基線第 {line_number} 行 quality_debt_status 非法")
        if not isinstance(gap_details, list) or not all(
            isinstance(detail, dict) for detail in gap_details
        ):
            raise ValueError(f"成品基線第 {line_number} 行 gap_details 型別錯誤")
        if debt_status == "unknown":
            if not isinstance(debt_reason, str) or not debt_reason:
                raise ValueError(f"成品基線第 {line_number} 行 unknown 缺少原因")
            if unqualified_count is not None or single_angle_count is not None:
                raise ValueError(f"成品基線第 {line_number} 行 unknown 不可猜測欠債計數")
        else:
            if debt_reason is not None:
                raise ValueError(f"成品基線第 {line_number} 行 calculated 不可含 unknown 原因")
            if (
                type(unqualified_count) is not int
                or unqualified_count < 0
                or type(single_angle_count) is not int
                or single_angle_count < 0
            ):
                raise ValueError(f"成品基線第 {line_number} 行品質欠債計數錯誤")
            if unqualified_count != sum(
                detail.get("kind") == "unqualified_source_argument"
                for detail in gap_details
            ):
                raise ValueError(f"成品基線第 {line_number} 行無合格來源論點計數不一致")
            if single_angle_count != sum(
                detail.get("kind") == "single_angle_topic"
                for detail in gap_details
            ):
                raise ValueError(f"成品基線第 {line_number} 行單角度主題計數不一致")
        records.append(dict(record))

    ranked_records = [
        record for record in records if record["status"] == "calculated"
    ]
    metrics_unavailable_records = [
        record for record in records if record["status"] == "metrics_unavailable"
    ]
    ranked_records.sort(key=lambda item: (
        item["traceability"] is None,
        item["traceability"] if item["traceability"] is not None else float("inf"),
        item["angles_per_topic"] is None,
        item["angles_per_topic"] if item["angles_per_topic"] is not None else float("inf"),
        item["artifact_path"],
        item["content_hash"],
    ))
    for rank, record in enumerate(ranked_records, 1):
        record["rank"] = rank
    metrics_unavailable_records.sort(key=lambda item: (
        item["artifact_path"],
        item["content_hash"],
    ))

    leaderboard = {
        "schema": "note_filler.quality_debt_leaderboard.v3",
        "source_baseline": baseline_path.name,
        "record_count": len(records),
        "ranked_record_count": len(ranked_records),
        "metrics_unavailable_record_count": len(metrics_unavailable_records),
        "metrics_unavailable_records": [
            {
                "note_id": record["note_id"],
                "artifact_path": record["artifact_path"],
                "reason": (
                    record["quality_debt_reason"]
                    or "baseline_metrics_unavailable"
                ),
            }
            for record in metrics_unavailable_records
        ],
        "unknown_record_count": sum(
            record["quality_debt_status"] == "unknown" for record in ranked_records
        ),
        "unknown_records": [
            {
                "note_id": record["note_id"],
                "artifact_path": record["artifact_path"],
                "reason": record["quality_debt_reason"],
            }
            for record in ranked_records
            if record["quality_debt_status"] == "unknown"
        ],
        "records": ranked_records,
    }
    leaderboard_path = Path(leaderboard_path)
    leaderboard_path.parent.mkdir(parents=True, exist_ok=True)
    leaderboard_path.write_text(
        json.dumps(leaderboard, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return leaderboard


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
    file_pattern: str = "*delivery_manifest.json"
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
    note_id: str  # 穩定的筆記識別碼（sha256 前 12 碼）
    
    # 北極星指標
    polaris_metrics: dict[str, Any]
    
    # 原始 delivery_manifest 資料
    delivery_manifest: dict[str, Any]


@dataclass
class MetricsAlert:
    """結構化指標告警記錄。"""
    alert_id: str  # 唯一告警識別碼
    alert_time: str  # ISO 8601 UTC
    alert_type: str  # threshold_breach | collection_failure | rerun_failure | pipeline_error
    severity: str  # warning | critical
    metric_name: str  # 受影響指標名稱（pipeline_error 時為 "pipeline"）
    note_id: str  # 受影響筆記識別碼
    source_path: str  # 受影響筆記路徑
    threshold: float | None  # 門檻值（threshold_breach 時有值）
    actual_value: float | None  # 實際值（threshold_breach 時有值）
    error_message: str  # 錯誤訊息（failure 時有值）
    resolved: bool = False  # 是否已解決


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
    
    # 筆記識別碼清單（去重、排序）
    note_ids: list[str] = field(default_factory=list)
    
    # 平均分數
    average_scores: dict[str, float] = field(default_factory=dict)
    
    # 品質分佈
    quality_distribution: dict[str, int] = field(default_factory=dict)
    
    # 告警記錄
    alerts: list[dict[str, Any]] = field(default_factory=list)

    # 因追溯性不足而降分的逐筆改善排序
    traceability_degraded_count: int = 0
    improvement_priorities: list[dict[str, Any]] = field(default_factory=list)


def _traceability_improvement_priorities(
    records: list[MetricsRecord],
) -> list[dict[str, Any]]:
    """依追溯扣分、總分及路徑產生穩定且可驗收的逐筆排序。"""
    priorities = []
    seen_manifests: set[str] = set()
    for record in records:
        metrics = record.polaris_metrics
        traceability = metrics.get("traceability_score")
        if not isinstance(traceability, dict) or traceability.get("degraded") is not True:
            continue
        penalty = traceability.get("penalty")
        score = traceability.get("score")
        overall_score = metrics.get("overall_score")
        if not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in (penalty, score, overall_score)
        ):
            continue
        complete_score = metrics.get("score_if_traceability_complete")
        if not (
            isinstance(complete_score, (int, float))
            and not isinstance(complete_score, bool)
        ):
            complete_score = overall_score + penalty
        affected_argument_ids = traceability.get("affected_argument_ids")
        repair_fields = traceability.get("source_fields")
        acceptance = traceability.get("acceptance")
        if record.manifest_path in seen_manifests:
            continue
        seen_manifests.add(record.manifest_path)
        priorities.append({
            "note_id": record.note_id,
            "source_path": record.source_path,
            "manifest_path": record.manifest_path,
            "reason": "traceability_below_target",
            "overall_score": float(overall_score),
            "score_if_traceability_complete": float(complete_score),
            "traceability_score": float(score),
            "score_penalty": float(penalty),
            "affected_argument_ids": (
                list(affected_argument_ids)
                if isinstance(affected_argument_ids, list)
                else []
            ),
            "repair_fields": list(repair_fields) if isinstance(repair_fields, list) else [],
            "acceptance": dict(acceptance) if isinstance(acceptance, dict) else {},
        })

    priorities.sort(key=lambda item: (
        -item["score_penalty"],
        item["overall_score"],
        item["source_path"],
        item["manifest_path"],
    ))
    for rank, item in enumerate(priorities, 1):
        item["rank"] = rank
    return priorities


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
        
        source_path = receipt_input_identity(manifest_data) or ""
        note_id = derive_note_id(source_path)
        collection_time = datetime.now(timezone.utc).isoformat()
        
        return MetricsRecord(
            source_path=source_path,
            manifest_path=str(manifest_path),
            collection_time=collection_time,
            note_id=note_id,
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
    seen_keys: set[str] = set()

    for scan_dir in config.scan_dirs:
        if not scan_dir.exists():
            logger.warning(f"掃描目錄不存在: {scan_dir}")
            continue

        # 遞迴或非遞迴掃描
        if config.recursive:
            manifest_files = list(scan_dir.glob(f"**/{config.file_pattern}"))
        else:
            manifest_files = list(scan_dir.glob(config.file_pattern))

        # A legacy latest-only copy is scanned only when its note-owned receipt
        # is not also in this scan. Otherwise one delivery would count twice.
        # Note-owned receipts sort first so deduplication always keeps them.
        found = set(manifest_files)
        filtered = []
        for manifest_path in sorted(
            manifest_files,
            key=lambda p: (p.name == DELIVERY_MANIFEST_NAME, str(p)),
        ):
            if manifest_path.name.endswith(DELIVERY_MANIFEST_NAME) and not is_receipt_file_name(
                manifest_path.name
            ):
                # A file such as ``mydelivery_manifest.json`` only matched the
                # broad default pattern; it is not a receipt.
                continue
            try:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                manifest_data = None
            if not isinstance(manifest_data, dict):
                # Unreadable or non-object receipts stay in the scan so the
                # collector reports them per file instead of aborting the scan.
                filtered.append(manifest_path)
                continue
            declared = manifest_data.get("sidecar_for_output") or receipt_output_identity(manifest_data)
            if (
                manifest_path.name == DELIVERY_MANIFEST_NAME
                and isinstance(declared, str)
                and declared
                and delivery_manifest_path(manifest_path.parent / Path(declared).name) in found
            ):
                continue
            key = output_identity_key(manifest_path, manifest_data)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            filtered.append(manifest_path)
        manifest_files = sorted(filtered)
        
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
        note_ids=sorted({r.note_id for r in records}),
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

    overall_scores = [
        float(score)
        for record in records
        if isinstance((score := record.polaris_metrics.get("overall_score")), (int, float))
        and not isinstance(score, bool)
    ]
    summary.average_scores["overall_score"] = (
        sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
    )
    
    # 統計品質分佈
    quality_counts = {"excellent": 0, "good": 0, "acceptable": 0, "poor": 0, "error": 0}
    for record in records:
        overall_status = record.polaris_metrics.get("overall_status", "error")
        if overall_status in quality_counts:
            quality_counts[overall_status] += 1
        else:
            quality_counts["error"] += 1
    summary.quality_distribution = quality_counts

    summary.improvement_priorities = _traceability_improvement_priorities(records)
    summary.traceability_degraded_count = len(summary.improvement_priorities)
    
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
        "note_ids": summary.note_ids,
        "average_scores": summary.average_scores,
        "quality_distribution": summary.quality_distribution,
        "alerts": summary.alerts,
        "traceability_degraded_count": summary.traceability_degraded_count,
        "improvement_priorities": summary.improvement_priorities,
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
            "note_id": r.note_id,
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
    5. 檢查並發送告警（結構化 MetricsAlert）
    6. 儲存告警記錄
    
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
    
    # 4. 轉換告警為結構化 MetricsAlert
    alerts: list[MetricsAlert] = []
    for alert_data in summary.alerts:
        _emit_alert(
            alerts,
            alert_type="threshold_breach",
            severity=alert_data.get("severity", "warning"),
            metric_name=alert_data.get("metric_name", ""),
            note_id="aggregate",
            source_path="",
            threshold=alert_data.get("threshold"),
            actual_value=alert_data.get("actual_value"),
            error_message=(
                f"{alert_data.get('metric_name', '')} 平均分數 "
                f"{alert_data.get('actual_value', 0):.3f} 低於門檻 "
                f"{alert_data.get('threshold', 0)}"
            ),
        )
    
    # 5. 儲存告警
    if alerts:
        save_alerts(alerts, config)
        logger.warning(f"觸發 {len(alerts)} 個告警")
        for alert in alerts:
            logger.warning(
                f"告警: {alert.metric_name} = {alert.actual_value:.3f} "
                f"< {alert.threshold} (嚴重性: {alert.severity})"
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


def save_alerts(
    alerts: list[MetricsAlert],
    config: MetricsCollectionConfig,
) -> Path:
    """儲存告警記錄到 JSON 檔案。

    每次儲存會追加到現有告警檔案（冪等：同 alert_id 不重複寫入）。
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)
    alerts_path = config.output_dir / "metrics_alerts.json"

    existing: list[dict[str, Any]] = []
    if alerts_path.exists():
        try:
            existing = json.loads(alerts_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []

    existing_ids = {a.get("alert_id") for a in existing}
    new_alerts = [
        {
            "alert_id": a.alert_id,
            "alert_time": a.alert_time,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "metric_name": a.metric_name,
            "note_id": a.note_id,
            "source_path": a.source_path,
            "threshold": a.threshold,
            "actual_value": a.actual_value,
            "error_message": a.error_message,
            "resolved": a.resolved,
        }
        for a in alerts
        if a.alert_id not in existing_ids
    ]

    existing.extend(new_alerts)
    alerts_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    logger.info(f"告警記錄已儲存: {alerts_path} (+{len(new_alerts)} new)")
    return alerts_path


def load_alerts(config: MetricsCollectionConfig) -> list[MetricsAlert]:
    """載入所有告警記錄。"""
    alerts_path = config.output_dir / "metrics_alerts.json"
    if not alerts_path.exists():
        return []

    try:
        data = json.loads(alerts_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    return [
        MetricsAlert(
            alert_id=a["alert_id"],
            alert_time=a["alert_time"],
            alert_type=a["alert_type"],
            severity=a["severity"],
            metric_name=a["metric_name"],
            note_id=a["note_id"],
            source_path=a["source_path"],
            threshold=a.get("threshold"),
            actual_value=a.get("actual_value"),
            error_message=a["error_message"],
            resolved=a.get("resolved", False),
        )
        for a in data
    ]


def _emit_alert(
    alerts: list[MetricsAlert],
    *,
    alert_type: str,
    severity: str,
    metric_name: str,
    note_id: str,
    source_path: str,
    threshold: float | None = None,
    actual_value: float | None = None,
    error_message: str = "",
) -> MetricsAlert:
    """建立並加入告警到清單。"""
    alert_id = hashlib.sha256(
        f"{alert_type}:{note_id}:{metric_name}:{datetime.now(timezone.utc).isoformat()}".encode()
    ).hexdigest()[:16]
    alert = MetricsAlert(
        alert_id=alert_id,
        alert_time=datetime.now(timezone.utc).isoformat(),
        alert_type=alert_type,
        severity=severity,
        metric_name=metric_name,
        note_id=note_id,
        source_path=source_path,
        threshold=threshold,
        actual_value=actual_value,
        error_message=error_message,
    )
    alerts.append(alert)
    return alert


def rerun_note(
    manifest_path: Path,
    config: MetricsCollectionConfig,
) -> tuple[MetricsRecord | None, list[MetricsAlert]]:
    """重跑單筆筆記的指標計算。

    從既有 delivery_manifest.json 讀取 binding_report 資料，
    重新計算北極星指標，更新 manifest 並回傳新的 MetricsRecord。

    回傳 (record, alerts)：
      - record: 成功時回傳 MetricsRecord，失敗時回傳 None
      - alerts: 告警清單（可能為空）
    """
    alerts: list[MetricsAlert] = []
    requested_path = Path(manifest_path)
    manifest_path = resolve_manifest_for_update(requested_path)

    if not manifest_path.exists():
        _emit_alert(
            alerts,
            alert_type="rerun_failure",
            severity="critical",
            metric_name="pipeline",
            note_id="unknown",
            source_path=str(requested_path),
            error_message=f"Manifest 檔案不存在: {manifest_path}",
        )
        return None, alerts

    # The authoritative receipt is read as well as written: a stale or
    # hand-edited latest copy must never revert recorded recovery state.
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _emit_alert(
            alerts,
            alert_type="rerun_failure",
            severity="critical",
            metric_name="pipeline",
            note_id=derive_note_id(str(manifest_path)),
            source_path=str(manifest_path),
            error_message=f"Manifest 讀取失敗: {exc}",
        )
        return None, alerts

    source_path = receipt_input_identity(manifest_data) or str(manifest_path)
    note_id = derive_note_id(source_path)

    # Prefer the report for this output; a receipt that states no report of its
    # own never borrows the directory-level copy.
    output_path = receipt_output_identity(manifest_data)
    if output_path:
        report_path = resolve_binding_report_path(
            manifest_path.parent / Path(output_path).name, manifest_data
        )
    else:
        report_path = manifest_path.parent / "binding_report.json"
    binding_report_path = report_path
    if not binding_report_path.exists():
        _emit_alert(
            alerts,
            alert_type="rerun_failure",
            severity="warning",
            metric_name="pipeline",
            note_id=note_id,
            source_path=source_path,
            error_message=f"binding_report.json 不存在: {binding_report_path}",
        )
        return None, alerts

    try:
        binding_report = json.loads(binding_report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _emit_alert(
            alerts,
            alert_type="rerun_failure",
            severity="critical",
            metric_name="pipeline",
            note_id=note_id,
            source_path=source_path,
            error_message=f"binding_report.json 讀取失敗: {exc}",
        )
        return None, alerts

    expected_report_hash = manifest_data.get("binding_report_content_hash")
    if expected_report_hash:
        try:
            actual_report_hash = hashlib.sha256(binding_report_path.read_bytes()).hexdigest()
        except OSError as exc:
            _emit_alert(
                alerts,
                alert_type="rerun_failure",
                severity="critical",
                metric_name="pipeline",
                note_id=note_id,
                source_path=source_path,
                error_message=f"binding_report.json 讀取失敗: {exc}",
            )
            return None, alerts
        if actual_report_hash != expected_report_hash:
            _emit_alert(
                alerts,
                alert_type="rerun_failure",
                severity="critical",
                metric_name="pipeline",
                note_id=note_id,
                source_path=source_path,
                error_message=f"binding_report.json 內容雜湊不符: {binding_report_path}",
            )
            return None, alerts

    # 從 manifest 取得 delivery_status
    delivery_status = manifest_data.get("delivery_status")

    # 重新計算指標
    try:
        from .metrics import calculate_polaris_metrics
        polaris_metrics = calculate_polaris_metrics(
            binding_report=binding_report,
            delivery_status=delivery_status,
        ).to_dict()
    except Exception as exc:
        _emit_alert(
            alerts,
            alert_type="rerun_failure",
            severity="critical",
            metric_name="pipeline",
            note_id=note_id,
            source_path=source_path,
            error_message=f"指標計算失敗: {type(exc).__name__}: {exc}",
        )
        return None, alerts

    # 更新 manifest 中的 polaris_metrics
    manifest_data["polaris_metrics"] = polaris_metrics
    manifest_data["metrics_rerun_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest_and_latest(manifest_path, manifest_data)

    collection_time = datetime.now(timezone.utc).isoformat()
    record = MetricsRecord(
        source_path=source_path,
        manifest_path=str(manifest_path),
        collection_time=collection_time,
        note_id=note_id,
        polaris_metrics=polaris_metrics,
        delivery_manifest=manifest_data,
    )

    # 檢查指標是否低於門檻並產生告警
    for metric_name, threshold in config.alert_thresholds.items():
        metric_data = polaris_metrics.get(metric_name, {})
        if metric_data.get("status") == "calculated":
            score = metric_data.get("score", 0.0)
            if score < threshold:
                severity = "warning" if score >= threshold * 0.8 else "critical"
                _emit_alert(
                    alerts,
                    alert_type="threshold_breach",
                    severity=severity,
                    metric_name=metric_name,
                    note_id=note_id,
                    source_path=source_path,
                    threshold=threshold,
                    actual_value=score,
                    error_message=f"{metric_name}={score:.3f} < {threshold}",
                )

    logger.info(f"Rerun 完成: {note_id} ({source_path})")
    return record, alerts
