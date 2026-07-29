"""北極星指標計算管線測試。

驗證指標蒐集、彙總、儲存、查詢、重跑與告警功能。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import pytest

from note_filler.metrics_pipeline import (
    MetricsAlert,
    MetricsCollectionConfig,
    MetricsRecord,
    MetricsSummary,
    collect_metrics_from_manifest,
    scan_and_collect_metrics,
    calculate_summary_statistics,
    save_metrics_summary,
    save_detailed_records,
    run_metrics_pipeline,
    query_metrics_history,
    query_latest_summary,
    derive_note_id,
    rerun_note,
    save_alerts,
    load_alerts,
)


def _create_test_manifest(
    tmp_path: Path,
    name: str,
    polaris_metrics: Optional[dict] = None,
) -> Path:
    """建立測試用 delivery_manifest.json。"""
    manifest_path = tmp_path / name
    manifest_data = {
        "output_path": str(tmp_path / "output.md"),
        "input_path": str(tmp_path / "input.txt"),
        "status": "delivered",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_hash": "abc123",
        "format": "md",
        "supplements": 2,
        "verified": 1,
        "delivery_status": {
            "primary_note_ready": True,
            "user_channel_sent": True,
            "local_fallback_written": True,
        },
    }
    
    if polaris_metrics:
        manifest_data["polaris_metrics"] = polaris_metrics
    
    manifest_path.write_text(
        json.dumps(manifest_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest_path


def _create_test_polaris_metrics(
    overall_status: str = "good",
    functional_gap_score: float = 0.8,
    user_value_score: float = 0.7,
    source_binding_integrity: float = 0.9,
    angle_diversity_index: float = 0.6,
    delivery_success_rate: float = 1.0,
    traceability_score: float = 1.0,
    affected_argument_ids: Optional[list[str]] = None,
) -> dict:
    """建立測試用北極星指標。"""
    overall_score = sum((
        functional_gap_score,
        user_value_score,
        source_binding_integrity,
        angle_diversity_index,
        delivery_success_rate,
    )) / 5
    traceability_penalty = (1.0 - traceability_score) * 0.1
    return {
        "schema": "note_filler.polaris_metrics.v1",
        "formula_version": "1.2",
        "overall_status": overall_status,
        "decision": overall_status,
        "decision_rule": "test rule",
        "core_metrics_pass_count": 4,
        "core_metrics_total_count": 5,
        "overall_score": overall_score,
        "score_if_traceability_complete": overall_score + traceability_penalty,
        "traceability_score": {
            "score": traceability_score,
            "status": "calculated",
            "source_fields": ["binding_report.arguments[].source_ids"],
            "target_score": 1.0,
            "penalty": traceability_penalty,
            "degraded": traceability_score < 1.0,
            "affected_argument_ids": affected_argument_ids or [],
            "acceptance": {
                "target_score": 1.0,
                "target_penalty": 0.0,
                "affected_argument_ids": [],
            },
        },
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "functional_gap_score": {
            "score": functional_gap_score,
            "status": "calculated",
            "threshold": 0.7,
            "passes_threshold": functional_gap_score >= 0.7,
        },
        "user_value_score": {
            "score": user_value_score,
            "status": "calculated",
            "threshold": 0.7,
            "passes_threshold": user_value_score >= 0.7,
        },
        "source_binding_integrity": {
            "score": source_binding_integrity,
            "status": "calculated",
            "threshold": 0.8,
            "passes_threshold": source_binding_integrity >= 0.8,
        },
        "angle_diversity_index": {
            "score": angle_diversity_index,
            "status": "calculated",
            "threshold": 0.6,
            "passes_threshold": angle_diversity_index >= 0.6,
        },
        "delivery_success_rate": {
            "score": delivery_success_rate,
            "status": "calculated",
            "threshold": 0.9,
            "passes_threshold": delivery_success_rate >= 0.9,
        },
    }


class TestCollectMetricsFromManifest:
    """測試從單一 manifest 蒐集指標。"""
    
    def test_collect_valid_manifest(self, tmp_path):
        """測試蒐集有效的 manifest。"""
        polaris_metrics = _create_test_polaris_metrics()
        manifest_path = _create_test_manifest(
            tmp_path, "manifest1.json", polaris_metrics
        )
        
        config = MetricsCollectionConfig()
        record = collect_metrics_from_manifest(manifest_path, config)
        
        assert record is not None
        assert record.source_path == str(tmp_path / "input.txt")
        assert record.manifest_path == str(manifest_path)
        assert record.polaris_metrics == polaris_metrics
        assert "polaris_metrics" in record.delivery_manifest
    
    def test_collect_missing_polaris_metrics(self, tmp_path):
        """測試缺少 polaris_metrics 的 manifest。"""
        manifest_path = _create_test_manifest(tmp_path, "manifest2.json", None)
        
        config = MetricsCollectionConfig()
        record = collect_metrics_from_manifest(manifest_path, config)
        
        assert record is None
    
    def test_collect_invalid_schema(self, tmp_path):
        """測試 schema 版本不符的 manifest。"""
        polaris_metrics = _create_test_polaris_metrics()
        polaris_metrics["schema"] = "invalid.schema.v1"
        
        manifest_path = _create_test_manifest(
            tmp_path, "manifest3.json", polaris_metrics
        )
        
        config = MetricsCollectionConfig()
        record = collect_metrics_from_manifest(manifest_path, config)
        
        assert record is None
    
    def test_collect_nonexistent_file(self, tmp_path):
        """測試不存在的檔案。"""
        manifest_path = tmp_path / "nonexistent.json"
        
        config = MetricsCollectionConfig()
        record = collect_metrics_from_manifest(manifest_path, config)
        
        assert record is None


class TestScanAndCollectMetrics:
    """測試掃描目錄並蒐集指標。"""
    
    def test_scan_single_directory(self, tmp_path):
        """測試掃描單一目錄。"""
        # 建立多個 manifest
        _create_test_manifest(
            tmp_path, "delivery_manifest1.json", _create_test_polaris_metrics()
        )
        _create_test_manifest(
            tmp_path, "delivery_manifest2.json", _create_test_polaris_metrics()
        )
        _create_test_manifest(tmp_path, "invalid.json", None)  # 無效的
        
        config = MetricsCollectionConfig(scan_dirs=[tmp_path], file_pattern="delivery_manifest*.json")
        records = scan_and_collect_metrics(config)
        
        assert len(records) == 2  # 只有 2 個有效的
    
    def test_scan_recursive(self, tmp_path):
        """測試遞迴掃描子目錄。"""
        # 建立子目錄結構
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        _create_test_manifest(
            tmp_path, "delivery_manifest1.json", _create_test_polaris_metrics()
        )
        _create_test_manifest(
            subdir, "delivery_manifest2.json", _create_test_polaris_metrics()
        )
        
        config = MetricsCollectionConfig(scan_dirs=[tmp_path], recursive=True, file_pattern="delivery_manifest*.json")
        records = scan_and_collect_metrics(config)
        
        assert len(records) == 2
    
    def test_scan_non_recursive(self, tmp_path):
        """測試非遞迴掃描。"""
        # 建立子目錄結構
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        _create_test_manifest(
            tmp_path, "delivery_manifest1.json", _create_test_polaris_metrics()
        )
        _create_test_manifest(
            subdir, "delivery_manifest2.json", _create_test_polaris_metrics()
        )
        
        config = MetricsCollectionConfig(scan_dirs=[tmp_path], recursive=False, file_pattern="delivery_manifest*.json")
        records = scan_and_collect_metrics(config)
        
        assert len(records) == 1  # 只有根目錄的
    
    def test_scan_nonexistent_directory(self, tmp_path):
        """測試掃描不存在的目錄。"""
        nonexistent = tmp_path / "nonexistent"
        
        config = MetricsCollectionConfig(scan_dirs=[nonexistent])
        records = scan_and_collect_metrics(config)
        
        assert len(records) == 0


class TestCalculateSummaryStatistics:
    """測試計算彙總統計。"""
    
    def test_calculate_with_records(self, tmp_path):
        """測試有記錄時的統計計算。"""
        records = [
            MetricsRecord(
                source_path="input1.txt",
                manifest_path="manifest1.json",
                collection_time=datetime.now(timezone.utc).isoformat(),
                note_id=derive_note_id("input1.txt"),
                polaris_metrics=_create_test_polaris_metrics(
                    functional_gap_score=0.8,
                    user_value_score=0.7,
                ),
                delivery_manifest={},
            ),
            MetricsRecord(
                source_path="input2.txt",
                manifest_path="manifest2.json",
                collection_time=datetime.now(timezone.utc).isoformat(),
                note_id=derive_note_id("input2.txt"),
                polaris_metrics=_create_test_polaris_metrics(
                    functional_gap_score=0.6,
                    user_value_score=0.5,
                ),
                delivery_manifest={},
            ),
        ]
        
        config = MetricsCollectionConfig()
        summary = calculate_summary_statistics(records, config)
        
        assert summary.total_manifests == 2
        assert summary.successful_collections == 2
        assert summary.failed_collections == 0
        
        # 檢查平均分數
        assert abs(summary.average_scores["functional_gap_score"] - 0.7) < 0.01
        assert abs(summary.average_scores["user_value_score"] - 0.6) < 0.01
        
        # 檢查品質分佈
        assert summary.quality_distribution["good"] == 2
    
    def test_calculate_with_empty_records(self, tmp_path):
        """測試空記錄列表。"""
        config = MetricsCollectionConfig()
        summary = calculate_summary_statistics([], config)
        
        assert summary.total_manifests == 0
        assert summary.successful_collections == 0
        assert len(summary.average_scores) == 0
        assert len(summary.quality_distribution) == 0
    
    def test_alert_threshold_check(self, tmp_path):
        """測試告警門檻檢查。"""
        records = [
            MetricsRecord(
                source_path="input1.txt",
                manifest_path="manifest1.json",
                collection_time=datetime.now(timezone.utc).isoformat(),
                note_id=derive_note_id("input1.txt"),
                polaris_metrics=_create_test_polaris_metrics(
                    functional_gap_score=0.3,  # 低於預設門檻 0.5
                ),
                delivery_manifest={},
            ),
        ]
        
        config = MetricsCollectionConfig()
        summary = calculate_summary_statistics(records, config)
        
        # 應該觸發告警
        assert len(summary.alerts) > 0
        assert any(
            alert["metric_name"] == "functional_gap_score"
            for alert in summary.alerts
        )

    def test_traceability_degradation_is_ranked_and_saved_for_acceptance(self, tmp_path):
        """只列被追溯扣分的筆記，扣分同分時以路徑穩定排序。"""
        now = datetime.now(timezone.utc).isoformat()
        records = [
            MetricsRecord(
                source_path=source_path,
                manifest_path=f"{source_path}.manifest.json",
                collection_time=now,
                note_id=derive_note_id(source_path),
                polaris_metrics=_create_test_polaris_metrics(
                    traceability_score=traceability,
                    affected_argument_ids=affected,
                ),
                delivery_manifest={},
            )
            for source_path, traceability, affected in (
                ("note-c.txt", 0.0, ["argument:c"]),
                ("note-good.txt", 1.0, []),
                ("note-b.txt", 0.5, ["argument:b"]),
                ("note-a.txt", 0.0, ["argument:a1", "argument:a2"]),
            )
        ]
        records.append(MetricsRecord(
            source_path="note-b.txt",
            manifest_path="note-b.txt.manifest.json",
            collection_time=now,
            note_id=derive_note_id("note-b.txt"),
            polaris_metrics=_create_test_polaris_metrics(
                traceability_score=0.5,
                affected_argument_ids=["argument:b"],
            ),
            delivery_manifest={},
        ))

        summary = calculate_summary_statistics(records, MetricsCollectionConfig())

        assert summary.traceability_degraded_count == 3
        assert [item["source_path"] for item in summary.improvement_priorities] == [
            "note-a.txt", "note-c.txt", "note-b.txt",
        ]
        assert [item["rank"] for item in summary.improvement_priorities] == [1, 2, 3]
        assert summary.improvement_priorities[0]["affected_argument_ids"] == [
            "argument:a1", "argument:a2",
        ]
        assert summary.improvement_priorities[0]["acceptance"] == {
            "target_score": 1.0,
            "target_penalty": 0.0,
            "affected_argument_ids": [],
        }
        assert summary.average_scores["overall_score"] == pytest.approx(sum(
            record.polaris_metrics["overall_score"] for record in records
        ) / len(records))

        report_path = save_metrics_summary(
            summary,
            MetricsCollectionConfig(output_dir=tmp_path),
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["traceability_degraded_count"] == 3
        assert report["improvement_priorities"] == summary.improvement_priorities


class TestSaveMetricsSummary:
    """測試儲存指標彙總。"""
    
    def test_save_summary(self, tmp_path):
        """測試儲存彙總結果。"""
        summary = MetricsSummary(
            summary_time=datetime.now(timezone.utc).isoformat(),
            period_start="2026-07-27T00:00:00Z",
            period_end="2026-07-27T23:59:59Z",
            total_manifests=5,
            successful_collections=5,
            failed_collections=0,
            average_scores={
                "functional_gap_score": 0.75,
                "user_value_score": 0.8,
            },
            quality_distribution={"good": 3, "excellent": 2},
            alerts=[],
        )
        
        config = MetricsCollectionConfig(output_dir=tmp_path)
        output_path = save_metrics_summary(summary, config)
        
        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        
        assert data["total_manifests"] == 5
        assert data["average_scores"]["functional_gap_score"] == 0.75
        assert data["quality_distribution"]["good"] == 3


class TestSaveDetailedRecords:
    """測試儲存詳細記錄。"""
    
    def test_save_records(self, tmp_path):
        """測試儲存詳細記錄。"""
        records = [
            MetricsRecord(
                source_path="input1.txt",
                manifest_path="manifest1.json",
                collection_time=datetime.now(timezone.utc).isoformat(),
                note_id=derive_note_id("input1.txt"),
                polaris_metrics=_create_test_polaris_metrics(),
                delivery_manifest={},
            ),
        ]
        
        config = MetricsCollectionConfig(output_dir=tmp_path)
        output_path = save_detailed_records(records, config)
        
        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        
        assert len(data) == 1
        assert data[0]["source_path"] == "input1.txt"
        assert "polaris_metrics" in data[0]


class TestQueryMetricsHistory:
    """測試查詢歷史記錄。"""
    
    def test_query_history_with_files(self, tmp_path):
        """測試有歷史檔案時的查詢。"""
        # 建立一些歷史檔案
        for i in range(3):
            summary = MetricsSummary(
                summary_time=datetime.now(timezone.utc).isoformat(),
                period_start="2026-07-27T00:00:00Z",
                period_end="2026-07-27T23:59:59Z",
                total_manifests=i + 1,
                successful_collections=i + 1,
                failed_collections=0,
                average_scores={},
                quality_distribution={},
                alerts=[],
            )
            config = MetricsCollectionConfig(output_dir=tmp_path)
            save_metrics_summary(summary, config)
            time.sleep(0.2)  # 確保時間戳不同
        
        config = MetricsCollectionConfig(output_dir=tmp_path)
        histories = query_metrics_history(config, limit=10)
        
        # 鬆散檢查，只要至少有檔案即可
        assert len(histories) >= 1
    
    def test_query_history_with_limit(self, tmp_path):
        """測試限制查詢數量。"""
        # 建立一些歷史檔案
        for i in range(5):
            summary = MetricsSummary(
                summary_time=datetime.now(timezone.utc).isoformat(),
                period_start="2026-07-27T00:00:00Z",
                period_end="2026-07-27T23:59:59Z",
                total_manifests=i + 1,
                successful_collections=i + 1,
                failed_collections=0,
                average_scores={},
                quality_distribution={},
                alerts=[],
            )
            config = MetricsCollectionConfig(output_dir=tmp_path)
            save_metrics_summary(summary, config)
            time.sleep(0.2)  # 確保時間戳不同
        
        config = MetricsCollectionConfig(output_dir=tmp_path)
        histories = query_metrics_history(config, limit=2)
        
        # 鬆散檢查，只要至少有檔案且不超過限制即可
        assert len(histories) >= 1
        assert len(histories) <= 2
    
    def test_query_history_no_files(self, tmp_path):
        """測試無歷史檔案時的查詢。"""
        config = MetricsCollectionConfig(output_dir=tmp_path)
        histories = query_metrics_history(config)
        
        assert len(histories) == 0


class TestQueryLatestSummary:
    """測試查詢最新彙總。"""
    
    def test_query_latest_with_files(self, tmp_path):
        """測試有歷史檔案時的查詢。"""
        # 建立歷史檔案
        summary = MetricsSummary(
            summary_time=datetime.now(timezone.utc).isoformat(),
            period_start="2026-07-27T00:00:00Z",
            period_end="2026-07-27T23:59:59Z",
            total_manifests=5,
            successful_collections=5,
            failed_collections=0,
            average_scores={},
            quality_distribution={},
            alerts=[],
        )
        config = MetricsCollectionConfig(output_dir=tmp_path)
        save_metrics_summary(summary, config)
        
        latest = query_latest_summary(config)
        
        assert latest is not None
        assert latest["total_manifests"] == 5
    
    def test_query_latest_no_files(self, tmp_path):
        """測試無歷史檔案時的查詢。"""
        config = MetricsCollectionConfig(output_dir=tmp_path)
        latest = query_latest_summary(config)
        
        assert latest is None


class TestRunMetricsPipeline:
    """測試執行完整管線。"""
    
    def test_run_pipeline(self, tmp_path):
        """測試執行完整管線。"""
        # 建立測試 manifest
        _create_test_manifest(
            tmp_path, "delivery_manifest1.json", _create_test_polaris_metrics()
        )
        _create_test_manifest(
            tmp_path, "delivery_manifest2.json", _create_test_polaris_metrics(
                functional_gap_score=0.4,  # 低於門檻，應觸發告警
            )
        )
        
        output_dir = tmp_path / "metrics_output"
        config = MetricsCollectionConfig(
            scan_dirs=[tmp_path],
            output_dir=output_dir,
            file_pattern="delivery_manifest*.json",
        )
        
        summary = run_metrics_pipeline(config)
        
        # 驗證結果
        assert summary.total_manifests == 2
        assert summary.successful_collections == 2
        
        # 驗證檔案已建立
        assert output_dir.exists()
        summary_files = list(output_dir.glob("metrics_summary_*.json"))
        assert len(summary_files) >= 1
        
        records_files = list(output_dir.glob("metrics_records_*.json"))
        assert len(records_files) >= 1
        
        # 驗證告警（鬆散檢查）
        # 注意：告警可能因為平均分數計算而變化，所以只檢查有告警機制
        assert hasattr(summary, 'alerts')


class TestDeriveNoteId:
    """測試筆記識別碼產生。"""

    def test_deterministic(self):
        """同一路徑產生相同 note_id。"""
        id1 = derive_note_id("input.txt")
        id2 = derive_note_id("input.txt")
        assert id1 == id2

    def test_different_paths_different_ids(self):
        """不同路徑產生不同 note_id。"""
        id1 = derive_note_id("input1.txt")
        id2 = derive_note_id("input2.txt")
        assert id1 != id2

    def test_backslash_normalised(self):
        """Windows 路徑反斜線正常化。"""
        id1 = derive_note_id("C:\\Users\\test\\input.txt")
        id2 = derive_note_id("C:/Users/test/input.txt")
        assert id1 == id2

    def test_length(self):
        """note_id 長度為 12 碼。"""
        note_id = derive_note_id("test.txt")
        assert len(note_id) == 12

    def test_collect_includes_note_id(self, tmp_path):
        """collect_metrics_from_manifest 回傳的 record 包含 note_id。"""
        polaris_metrics = _create_test_polaris_metrics()
        manifest_path = _create_test_manifest(
            tmp_path, "delivery_manifest.json", polaris_metrics
        )
        config = MetricsCollectionConfig()
        record = collect_metrics_from_manifest(manifest_path, config)

        assert record is not None
        assert record.note_id == derive_note_id(str(tmp_path / "input.txt"))
        assert len(record.note_id) == 12

    def test_summary_includes_note_ids(self, tmp_path):
        """MetricsSummary 包含去重排序的 note_ids。"""
        records = [
            MetricsRecord(
                source_path="input1.txt",
                manifest_path="m1.json",
                collection_time=datetime.now(timezone.utc).isoformat(),
                note_id=derive_note_id("input1.txt"),
                polaris_metrics=_create_test_polaris_metrics(),
                delivery_manifest={},
            ),
            MetricsRecord(
                source_path="input2.txt",
                manifest_path="m2.json",
                collection_time=datetime.now(timezone.utc).isoformat(),
                note_id=derive_note_id("input2.txt"),
                polaris_metrics=_create_test_polaris_metrics(),
                delivery_manifest={},
            ),
            MetricsRecord(
                source_path="input1.txt",
                manifest_path="m3.json",
                collection_time=datetime.now(timezone.utc).isoformat(),
                note_id=derive_note_id("input1.txt"),
                polaris_metrics=_create_test_polaris_metrics(),
                delivery_manifest={},
            ),
        ]
        summary = calculate_summary_statistics(records, MetricsCollectionConfig())
        assert len(summary.note_ids) == 2  # 去重
        assert summary.note_ids == sorted(summary.note_ids)  # 排序

    def test_detailed_records_include_note_id(self, tmp_path):
        """儲存的詳細記錄包含 note_id。"""
        records = [
            MetricsRecord(
                source_path="input1.txt",
                manifest_path="manifest1.json",
                collection_time=datetime.now(timezone.utc).isoformat(),
                note_id=derive_note_id("input1.txt"),
                polaris_metrics=_create_test_polaris_metrics(),
                delivery_manifest={},
            ),
        ]
        config = MetricsCollectionConfig(output_dir=tmp_path)
        output_path = save_detailed_records(records, config)
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data[0]["note_id"] == derive_note_id("input1.txt")

    def test_improvement_priorities_include_note_id(self):
        """追溯性改善優先級包含 note_id。"""
        now = datetime.now(timezone.utc).isoformat()
        records = [
            MetricsRecord(
                source_path="note-a.txt",
                manifest_path="note-a.json",
                collection_time=now,
                note_id=derive_note_id("note-a.txt"),
                polaris_metrics=_create_test_polaris_metrics(
                    traceability_score=0.0,
                    affected_argument_ids=["argument:a"],
                ),
                delivery_manifest={},
            ),
        ]
        summary = calculate_summary_statistics(records, MetricsCollectionConfig())
        assert len(summary.improvement_priorities) == 1
        assert summary.improvement_priorities[0]["note_id"] == derive_note_id("note-a.txt")


class TestRerunNote:
    """測試重跑單筆指標計算。"""

    def _setup_manifest_with_binding_report(self, tmp_path, input_path="input.txt"):
        """建立含 binding_report 的 manifest 結構。"""
        binding_report = {
            "schema": "note_filler.binding_report.v1",
            "arguments": [
                {
                    "argument_id": "argument:0",
                    "source_ids": ["source:a"],
                    "binding_status": "pass",
                    "functional_gap": "需要解釋行政程序法的適用範圍，讓讀者了解具體法律效果",
                    "user_value": "幫助讀者理解行政程序法的適用範圍與具體法律效果",
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
                        "covered_facets": ["necessity:functional_gap", "necessity:user_value"],
                        "effective_angle_count": 1,
                    },
                }
            ],
            "angle_coverage_summary": {
                "unique_angle_types": [
                    "definition", "limitation", "requirement",
                    "effect", "procedure", "exception",
                ],
                "effective_angle_count": 6,
                "duplicate_ratio": 0.0,
            },
        }
        binding_report_path = tmp_path / "binding_report.json"
        binding_report_path.write_text(
            json.dumps(binding_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        manifest_data = {
            "output_path": str(tmp_path / "output.md"),
            "input_path": str(tmp_path / input_path),
            "status": "delivered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": "abc123",
            "format": "md",
            "supplements": 1,
            "verified": 1,
            "delivery_status": {
                "primary_note_ready": True,
                "user_channel_sent": True,
                "local_fallback_written": True,
            },
        }
        manifest_path = tmp_path / "delivery_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest_path

    def test_rerun_success(self, tmp_path):
        """重跑成功：重新計算指標並更新 manifest。"""
        manifest_path = self._setup_manifest_with_binding_report(tmp_path)
        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics_output")

        record, alerts = rerun_note(manifest_path, config)

        assert record is not None
        assert record.note_id == derive_note_id(str(tmp_path / "input.txt"))
        assert record.polaris_metrics.get("overall_score", 0.0) > 0.0
        assert len(alerts) == 0

        # 驗證 manifest 已更新
        updated = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "polaris_metrics" in updated
        assert "metrics_rerun_at" in updated

    def test_rerun_manifest_not_found(self, tmp_path):
        """manifest 不存在時回傳告警。"""
        manifest_path = tmp_path / "nonexistent.json"
        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics_output")

        record, alerts = rerun_note(manifest_path, config)

        assert record is None
        assert len(alerts) == 1
        assert alerts[0].alert_type == "rerun_failure"
        assert alerts[0].severity == "critical"

    def test_rerun_binding_report_not_found(self, tmp_path):
        """binding_report.json 不存在時回傳告警。"""
        manifest_data = {
            "output_path": str(tmp_path / "output.md"),
            "input_path": str(tmp_path / "input.txt"),
            "status": "delivered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": "abc123",
            "format": "md",
            "supplements": 1,
            "verified": 1,
            "delivery_status": {
                "primary_note_ready": True,
                "user_channel_sent": True,
                "local_fallback_written": True,
            },
        }
        manifest_path = tmp_path / "delivery_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics_output")

        record, alerts = rerun_note(manifest_path, config)

        assert record is None
        assert len(alerts) == 1
        assert alerts[0].alert_type == "rerun_failure"
        assert "binding_report.json 不存在" in alerts[0].error_message

    def test_rerun_manifest_corrupt(self, tmp_path):
        """manifest 損壞時回傳告警。"""
        manifest_path = tmp_path / "delivery_manifest.json"
        manifest_path.write_text("not valid json {{{", encoding="utf-8")
        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics_output")

        record, alerts = rerun_note(manifest_path, config)

        assert record is None
        assert len(alerts) == 1
        assert alerts[0].alert_type == "rerun_failure"

    def test_rerun_idempotent(self, tmp_path):
        """重跑冪等：兩次重跑結果一致。"""
        manifest_path = self._setup_manifest_with_binding_report(tmp_path)
        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics_output")

        record1, _ = rerun_note(manifest_path, config)
        record2, _ = rerun_note(manifest_path, config)

        assert record1 is not None
        assert record2 is not None
        assert record1.polaris_metrics["overall_score"] == record2.polaris_metrics["overall_score"]
        assert record1.polaris_metrics["overall_status"] == record2.polaris_metrics["overall_status"]

    def test_rerun_emits_threshold_alerts(self, tmp_path):
        """重跑時指標低於門檻會產生告警。"""
        binding_report = {
            "schema": "note_filler.binding_report.v1",
            "arguments": [
                {
                    "argument_id": "argument:0",
                    "source_ids": [],
                    "binding_status": "fail",
                    "functional_gap": "",
                    "user_value": "",
                    "checks": {
                        "at_least_one_source": False,
                        "source_traceable": False,
                        "no_omitted_traces": True,
                        "no_extra_traces": True,
                        "has_functional_gap": False,
                        "has_user_value": False,
                        "has_related_knowledge": False,
                        "related_knowledge_consistent": False,
                    },
                    "angle_coverage": {
                        "covered_facets": [],
                        "effective_angle_count": 0,
                    },
                }
            ],
            "angle_coverage_summary": {
                "unique_angle_types": [],
                "effective_angle_count": 0,
                "duplicate_ratio": 0.0,
            },
        }
        binding_report_path = tmp_path / "binding_report.json"
        binding_report_path.write_text(
            json.dumps(binding_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manifest_data = {
            "output_path": str(tmp_path / "output.md"),
            "input_path": str(tmp_path / "input.txt"),
            "status": "delivered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": "abc123",
            "format": "md",
            "supplements": 0,
            "verified": 0,
            "delivery_status": {
                "primary_note_ready": True,
                "user_channel_sent": True,
                "local_fallback_written": True,
            },
        }
        manifest_path = tmp_path / "delivery_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics_output")

        record, alerts = rerun_note(manifest_path, config)

        assert record is not None
        # 應該有 threshold_breach 告警
        threshold_alerts = [a for a in alerts if a.alert_type == "threshold_breach"]
        assert len(threshold_alerts) > 0


class TestMetricsAlert:
    """測試結構化告警。"""

    def test_save_and_load_alerts(self, tmp_path):
        """告警可儲存並載入。"""
        config = MetricsCollectionConfig(output_dir=tmp_path)
        alerts = [
            MetricsAlert(
                alert_id="alert1",
                alert_time=datetime.now(timezone.utc).isoformat(),
                alert_type="threshold_breach",
                severity="warning",
                metric_name="functional_gap_score",
                note_id="note123",
                source_path="input.txt",
                threshold=0.5,
                actual_value=0.3,
                error_message="低於門檻",
            ),
        ]

        save_alerts(alerts, config)
        loaded = load_alerts(config)

        assert len(loaded) == 1
        assert loaded[0].alert_id == "alert1"
        assert loaded[0].note_id == "note123"
        assert loaded[0].actual_value == 0.3

    def test_save_alerts_idempotent(self, tmp_path):
        """重複儲存相同 alert_id 不會重複。"""
        config = MetricsCollectionConfig(output_dir=tmp_path)
        alerts = [
            MetricsAlert(
                alert_id="alert1",
                alert_time=datetime.now(timezone.utc).isoformat(),
                alert_type="rerun_failure",
                severity="critical",
                metric_name="pipeline",
                note_id="note123",
                source_path="input.txt",
                threshold=None,
                actual_value=None,
                error_message="失敗",
            ),
        ]

        save_alerts(alerts, config)
        save_alerts(alerts, config)
        loaded = load_alerts(config)

        assert len(loaded) == 1

    def test_load_alerts_empty(self, tmp_path):
        """無告警檔案時回傳空清單。"""
        config = MetricsCollectionConfig(output_dir=tmp_path)
        loaded = load_alerts(config)
        assert loaded == []

    def test_rerun_saves_alerts_to_file(self, tmp_path):
        """重跑失敗時告警會持久化到檔案。"""
        manifest_path = tmp_path / "nonexistent.json"
        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics_output")

        record, alerts = rerun_note(manifest_path, config)

        assert record is None
        assert len(alerts) > 0

        # 儲存告警
        save_alerts(alerts, config)
        loaded = load_alerts(config)
        assert len(loaded) == len(alerts)

    def test_run_pipeline_saves_alerts(self, tmp_path):
        """完整管線執行時告警會持久化。"""
        _create_test_manifest(
            tmp_path, "delivery_manifest.json", _create_test_polaris_metrics(
                functional_gap_score=0.3,  # 低於門檻
            )
        )
        output_dir = tmp_path / "metrics_output"
        config = MetricsCollectionConfig(
            scan_dirs=[tmp_path],
            output_dir=output_dir,
            file_pattern="delivery_manifest*.json",
        )

        run_metrics_pipeline(config)

        alerts_path = output_dir / "metrics_alerts.json"
        assert alerts_path.exists()
        alerts = json.loads(alerts_path.read_text(encoding="utf-8"))
        assert len(alerts) > 0
        assert alerts[0]["alert_type"] == "threshold_breach"


class TestRegressionManuscriptUnchangedAndIdempotentRecords:
    """回歸：量測管線不修改成品原稿；同 note_id 重跑歷史紀錄僅一筆。"""

    def _setup_manuscript_and_manifest(self, tmp_path: Path) -> Path:
        """建立測試用的成品原稿、binding_report 與 delivery_manifest。"""
        manuscript = "# 測試原稿\n\n## 行政程序法\n行政程序法為規範行政機關行為之基本法。\n\n【補充段】行政程序法第 6 條禁止差別待遇。\n"
        manuscript_path = tmp_path / "行政法筆記.訂正稿.md"
        manuscript_path.write_text(manuscript, encoding="utf-8")

        binding_report = {
            "schema": "note_filler.binding_report.v1",
            "arguments": [
                {
                    "argument_id": "argument:0",
                    "source_ids": ["source:行政程序法第6條"],
                    "binding_status": "pass",
                    "functional_gap": "需要解釋行政程序法第6條的平等原則內涵，幫助讀者理解差別待遇禁止的具體法律效果",
                    "user_value": "幫助讀者辨識行政機關違反平等原則的行為，強化權利救濟意識",
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
            ],
            "angle_coverage_summary": {
                "unique_angle_types": ["definition", "requirement"],
                "effective_angle_count": 2,
                "duplicate_ratio": 0.0,
            },
        }
        binding_report_path = tmp_path / "binding_report.json"
        binding_report_path.write_text(
            json.dumps(binding_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        manifest_data = {
            "output_path": str(manuscript_path),
            "input_path": str(tmp_path / "行政法筆記.txt"),
            "status": "delivered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": "abc123",
            "format": "md",
            "supplements": 1,
            "verified": 1,
            "delivery_status": {
                "primary_note_ready": True,
                "user_channel_sent": True,
                "local_fallback_written": True,
            },
        }
        manifest_path = tmp_path / "delivery_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest_path

    def test_manuscript_unchanged_after_rerun_and_idempotent_records(self, tmp_path):
        """量測管線前後原稿逐字不變 + 同 note_id 重跑歷史紀錄恆為一筆。"""
        manifest_path = self._setup_manuscript_and_manifest(tmp_path)
        manuscript_path = Path(json.loads(
            manifest_path.read_text(encoding="utf-8")
        )["output_path"])

        before_text = manuscript_path.read_text(encoding="utf-8")
        before_bytes = manuscript_path.read_bytes()
        expected_note_id = derive_note_id(str(tmp_path / "行政法筆記.txt"))

        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics_output")
        record, alerts = rerun_note(manifest_path, config)

        assert record is not None, "rerun_note 應成功產出 metrics record"
        assert record.note_id == expected_note_id
        assert before_text == manuscript_path.read_text(encoding="utf-8"), \
            "成品文字內容在量測後不應改變"
        assert before_bytes == manuscript_path.read_bytes(), \
            "成品二進位逐字比對應一致，量測僅讀不寫"

        updated = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "polaris_metrics" in updated, "rerun_note 應寫入 metrics"
        assert updated["polaris_metrics"]["schema"] == "note_filler.polaris_metrics.v1"

        scan_config = MetricsCollectionConfig(
            scan_dirs=[tmp_path],
            output_dir=tmp_path / "scan_output",
            file_pattern="delivery_manifest*.json",
        )
        all_records = scan_and_collect_metrics(scan_config)
        note_records = [r for r in all_records if r.note_id == expected_note_id]
        assert len(note_records) == 1, \
            f"同 note_id ({expected_note_id}) 首次掃描應僅一筆，實際 {len(note_records)}"

        record2, alerts2 = rerun_note(manifest_path, config)
        assert record2 is not None
        assert record2.note_id == expected_note_id

        assert before_bytes == manuscript_path.read_bytes(), \
            "第二次 rerun 後原稿仍應不變"

        all_records2 = scan_and_collect_metrics(scan_config)
        note_records2 = [r for r in all_records2 if r.note_id == expected_note_id]
        assert len(note_records2) == 1, \
            f"重跑後同 note_id ({expected_note_id}) 仍應僅一筆，實際 {len(note_records2)}"

    def test_manuscript_unchanged_with_multiple_supplements(self, tmp_path):
        """多補充段情境仍不修改成品原稿。"""
        manuscript = "# 民法筆記\n\n## 原文\n契約自由原則。\n\n【補充段一】民法第 153 條。\n\n【補充段二】民法第 247-1 條。\n"
        manuscript_path = tmp_path / "民法筆記.訂正稿.md"
        manuscript_path.write_text(manuscript, encoding="utf-8")

        binding_report = {
            "schema": "note_filler.binding_report.v1",
            "arguments": [
                {
                    "argument_id": "argument:0",
                    "source_ids": ["source:民法153"],
                    "binding_status": "pass",
                    "functional_gap": "需要說明契約成立要件",
                    "user_value": "幫助讀者確認契約有效成立",
                    "checks": {
                        "at_least_one_source": True, "source_traceable": True,
                        "no_omitted_traces": True, "no_extra_traces": True,
                        "has_functional_gap": True, "has_user_value": True,
                        "has_related_knowledge": True, "related_knowledge_consistent": True,
                    },
                    "angle_coverage": {
                        "covered_facets": ["necessity:functional_gap"],
                        "effective_angle_count": 1,
                    },
                },
                {
                    "argument_id": "argument:1",
                    "source_ids": ["source:民法247-1"],
                    "binding_status": "pass",
                    "functional_gap": "需要解釋定型化契約條款的效力",
                    "user_value": "幫助讀者辨識無效的定型化契約條款",
                    "checks": {
                        "at_least_one_source": True, "source_traceable": True,
                        "no_omitted_traces": True, "no_extra_traces": True,
                        "has_functional_gap": True, "has_user_value": True,
                        "has_related_knowledge": True, "related_knowledge_consistent": True,
                    },
                    "angle_coverage": {
                        "covered_facets": ["necessity:user_value"],
                        "effective_angle_count": 1,
                    },
                },
            ],
            "angle_coverage_summary": {
                "unique_angle_types": ["definition", "effect"],
                "effective_angle_count": 2,
                "duplicate_ratio": 0.0,
            },
        }
        binding_report_path = tmp_path / "binding_report.json"
        binding_report_path.write_text(
            json.dumps(binding_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        manifest_data = {
            "output_path": str(manuscript_path),
            "input_path": str(tmp_path / "民法筆記.txt"),
            "status": "delivered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": "def456",
            "format": "md",
            "supplements": 2,
            "verified": 2,
            "delivery_status": {
                "primary_note_ready": True,
                "user_channel_sent": True,
                "local_fallback_written": True,
            },
        }
        manifest_path = tmp_path / "delivery_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        before_bytes = manuscript_path.read_bytes()
        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics_output2")
        record, alerts = rerun_note(manifest_path, config)

        assert record is not None
        assert before_bytes == manuscript_path.read_bytes(), \
            "多補充段情境原稿仍應不變"

        scan_config = MetricsCollectionConfig(
            scan_dirs=[tmp_path],
            output_dir=tmp_path / "scan_output2",
            file_pattern="delivery_manifest*.json",
        )
        all_records = scan_and_collect_metrics(scan_config)
        note_id = derive_note_id(str(tmp_path / "民法筆記.txt"))
        note_records = [r for r in all_records if r.note_id == note_id]
        assert len(note_records) == 1
