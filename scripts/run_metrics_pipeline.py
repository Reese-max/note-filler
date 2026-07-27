"""北極星指標計算管線 CLI。

執行週期性指標計算、查詢歷史結果與告警檢查。
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="run_metrics_pipeline",
        description="北極星指標週期性計算管線"
    )
    ap.add_argument(
        "command",
        choices=["collect", "query", "latest"],
        help="指令: collect=蒐集指標, query=查詢歷史, latest=查詢最新"
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
            print(f"  平均分數:")
            for metric_name, score in history['average_scores'].items():
                print(f"    {metric_name}: {score:.3f}")
            print(f"  品質分佈:")
            for status, count in history['quality_distribution'].items():
                print(f"    {status}: {count}")
            if history['alerts']:
                print(f"  告警數: {len(history['alerts'])}")
        
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
        
        return 0
    
    else:
        logger.error(f"未知指令: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
