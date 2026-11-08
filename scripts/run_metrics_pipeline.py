"""北極星指標計算管線 CLI。

執行週期性指標計算、查詢歷史結果、重跑單筆指標與告警檢查。
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _print_improvement_priorities(priorities: list[dict]) -> None:
    if not priorities:
        return
    print(f"\n追溯性改善優先級 ({len(priorities)}):")
    for item in priorities:
        affected = ",".join(item["affected_argument_ids"]) or "（缺少可定位論點）"
        note_id = item.get("note_id", "unknown")
        print(
            f"  #{item['rank']} [{note_id}] {item['source_path']}: "
            f"traceability={item['traceability_score']:.3f}, "
            f"overall={item['overall_score']:.3f}, "
            f"扣分={item['score_penalty']:.3f}, "
            f"待修論點={affected}"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="run_metrics_pipeline",
        description="北極星指標週期性計算管線"
    )
    ap.add_argument(
        "command",
        choices=["collect", "query", "latest", "rerun", "alerts", "baseline", "leaderboard"],
        help="指令: collect=蒐集指標, query=查詢歷史, latest=查詢最新, rerun=重跑單筆, alerts=查詢告警, baseline=唯讀掃描成品基線, leaderboard=產生品質欠債排行榜"
    )
    ap.add_argument(
        "--scan-dirs",
        nargs="+",
        default=["."],
        help="掃描目錄（預設當前目錄）"
    )
    ap.add_argument(
        "--output-dir",
        default="metrics_output",
        help="輸出目錄（預設 metrics_output）"
    )
    ap.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="遞迴掃描子目錄（預設啟用）"
    )
    ap.add_argument(
        "--no-recursive",
        action="store_false",
        dest="recursive",
        help="不遞迴掃描子目錄"
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=10,
        help="查詢歷史時的記錄數量限制（預設 10）"
    )
    ap.add_argument(
        "--manifest",
        default=None,
        help=(
            "rerun 指令：指定 delivery_manifest.json 路徑；"
            "目錄級路徑會轉到該筆記自己的權威回執（見 docs/batch-sidecars.md）"
        )
    )
    ap.add_argument(
        "--artifacts-dir",
        default="output",
        help="baseline 指令：成品 Markdown 根目錄（預設 output）"
    )
    ap.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="baseline 指令：本次最多掃描筆數"
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="詳細輸出"
    )
    
    args = ap.parse_args(argv)
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 動態導入（避免依賴問題）
    try:
        from note_filler.metrics_pipeline import (
            MetricsCollectionConfig,
            run_metrics_pipeline,
            query_metrics_history,
            query_latest_summary,
            rerun_note,
            load_alerts,
            OUTPUT_MARKDOWN_BASELINE_NAME,
            QUALITY_DEBT_LEADERBOARD_NAME,
            scan_output_markdown_baselines,
            generate_quality_debt_leaderboard,
        )
    except ImportError as e:
        logger.error(f"無法導入 metrics_pipeline: {e}")
        return 1
    
    # 建立配置
    config = MetricsCollectionConfig(
        scan_dirs=[Path(d) for d in args.scan_dirs],
        output_dir=Path(args.output_dir),
        recursive=args.recursive,
    )
    
    # 執行指令
    if args.command == "collect":
        logger.info("開始蒐集指標...")
        summary = run_metrics_pipeline(config)
        
        # 輸出摘要
        print(f"\n指標蒐集完成:")
        print(f"  處理 manifest 數: {summary.total_manifests}")
        print(f"  成功蒐集: {summary.successful_collections}")
        print(f"  失敗: {summary.failed_collections}")
        print(f"  筆記識別碼數: {len(summary.note_ids)}")
        print(f"  彙總期間: {summary.period_start} ~ {summary.period_end}")
        print(f"\n平均分數:")
        for metric_name, score in summary.average_scores.items():
            print(f"  {metric_name}: {score:.3f}")
        print(f"\n品質分佈:")
        for status, count in summary.quality_distribution.items():
            print(f"  {status}: {count}")
        
        if summary.alerts:
            print(f"\n告警 ({len(summary.alerts)}):")
            for alert in summary.alerts:
                print(
                    f"  {alert['metric_name']}: {alert['actual_value']:.3f} "
                    f"< {alert['threshold']} ({alert['severity']})"
                )
        _print_improvement_priorities(summary.improvement_priorities)
        
        return 0

    elif args.command == "baseline":
        if args.batch_size is not None and args.batch_size <= 0:
            ap.error("--batch-size 必須為正整數")
        result = scan_output_markdown_baselines(
            Path(args.artifacts_dir),
            config.output_dir / OUTPUT_MARKDOWN_BASELINE_NAME,
            batch_size=args.batch_size,
        )
        print(
            f"成品基線掃描完成: 掃描 {result.scanned_count} 筆，"
            f"新增 {result.created_count} 筆"
        )
        return 0

    elif args.command == "leaderboard":
        result = generate_quality_debt_leaderboard(
            config.output_dir / OUTPUT_MARKDOWN_BASELINE_NAME,
            config.output_dir / QUALITY_DEBT_LEADERBOARD_NAME,
        )
        print(f"品質欠債排行榜完成: {result['record_count']} 筆")
        return 0
    
    elif args.command == "query":
        logger.info(f"查詢最近 {args.limit} 筆歷史記錄...")
        histories = query_metrics_history(config, limit=args.limit)
        
        if not histories:
            print("無歷史記錄")
            return 0
        
        print(f"\n找到 {len(histories)} 筆歷史記錄:")
        for i, history in enumerate(histories, 1):
            print(f"\n[{i}] {history['summary_time']}")
            print(f"  期間: {history['period_start']} ~ {history['period_end']}")
            print(f"  處理數: {history['total_manifests']}")
            note_ids = history.get('note_ids', [])
            if note_ids:
                print(f"  筆記識別碼: {', '.join(note_ids[:5])}{'...' if len(note_ids) > 5 else ''}")
            print(f"  平均分數:")
            for metric_name, score in history['average_scores'].items():
                print(f"    {metric_name}: {score:.3f}")
            print(f"  品質分佈:")
            for status, count in history['quality_distribution'].items():
                print(f"    {status}: {count}")
            if history['alerts']:
                print(f"  告警數: {len(history['alerts'])}")
            _print_improvement_priorities(history.get("improvement_priorities", []))
        
        return 0
    
    elif args.command == "latest":
        logger.info("查詢最新指標彙總...")
        latest = query_latest_summary(config)
        
        if not latest:
            print("無最新記錄")
            return 0
        
        print(f"\n最新彙總 ({latest['summary_time']}):")
        print(f"  期間: {latest['period_start']} ~ {latest['period_end']}")
        print(f"  處理數: {latest['total_manifests']}")
        note_ids = latest.get('note_ids', [])
        if note_ids:
            print(f"  筆記識別碼: {', '.join(note_ids[:5])}{'...' if len(note_ids) > 5 else ''}")
        print(f"  平均分數:")
        for metric_name, score in latest['average_scores'].items():
            print(f"    {metric_name}: {score:.3f}")
        print(f"  品質分佈:")
        for status, count in latest['quality_distribution'].items():
            print(f"    {status}: {count}")
        
        if latest['alerts']:
            print(f"\n告警 ({len(latest['alerts'])}):")
            for alert in latest['alerts']:
                print(
                    f"  {alert['metric_name']}: {alert['actual_value']:.3f} "
                    f"< {alert['threshold']} ({alert['severity']})"
                )
        _print_improvement_priorities(latest.get("improvement_priorities", []))
        
        return 0
    
    elif args.command == "rerun":
        if not args.manifest:
            logger.error("rerun 指令需要 --manifest 參數指定 delivery_manifest.json 路徑")
            return 1
        
        manifest_path = Path(args.manifest)
        logger.info(f"重跑指標計算: {manifest_path}")
        record, alerts = rerun_note(manifest_path, config)
        
        if record is None:
            print(f"\n重跑失敗:")
            for alert in alerts:
                print(f"  [{alert.severity}] {alert.error_message}")
            # 儲存告警
            if alerts:
                from note_filler.metrics_pipeline import save_alerts
                save_alerts(alerts, config)
            return 1
        
        print(f"\n重跑完成:")
        print(f"  筆記識別碼: {record.note_id}")
        print(f"  來源路徑: {record.source_path}")
        print(f"  Manifest: {record.manifest_path}")
        
        metrics = record.polaris_metrics
        print(f"  整體狀態: {metrics.get('overall_status', 'unknown')}")
        print(f"  整體分數: {metrics.get('overall_score', 0.0):.3f}")
        
        if alerts:
            print(f"\n告警 ({len(alerts)}):")
            for alert in alerts:
                print(f"  [{alert.severity}] {alert.error_message}")
            from note_filler.metrics_pipeline import save_alerts
            save_alerts(alerts, config)
        
        return 0
    
    elif args.command == "alerts":
        logger.info("查詢告警記錄...")
        alerts = load_alerts(config)
        
        if not alerts:
            print("無告警記錄")
            return 0
        
        print(f"\n告警記錄 ({len(alerts)}):")
        for alert in alerts:
            status = "✓已解決" if alert.resolved else "✗未解決"
            print(
                f"  [{status}] {alert.alert_time} | "
                f"{alert.alert_type} | {alert.severity} | "
                f"{alert.metric_name} | {alert.note_id} | "
                f"{alert.error_message}"
            )
        
        return 0
    
    else:
        logger.error(f"未知指令: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
