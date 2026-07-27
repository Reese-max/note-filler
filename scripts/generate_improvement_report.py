"""改善追蹤報告產生 CLI。

從 metrics_output 或 delivery_manifest 掃描並產生改善追蹤報告。
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _load_records_from_metrics_output(
    metrics_output_dir: Path,
) -> list[dict]:
    """從 metrics_output 載入 MetricsRecord。"""
    records_path = metrics_output_dir.glob("metrics_records_*.json")
    latest = sorted(records_path, key=lambda p: p.stat().st_mtime, reverse=True)
    if not latest:
        return []
    data = json.loads(latest[0].read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _load_records_from_manifests(
    scan_dirs: list[Path],
    recursive: bool = True,
) -> list[dict]:
    """從 delivery_manifest.json 蒐集 MetricsRecord。"""
    records = []
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        pattern = "**/delivery_manifest.json" if recursive else "delivery_manifest.json"
        for manifest_path in scan_dir.glob(pattern):
            try:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                polaris_metrics = manifest_data.get("polaris_metrics")
                if not polaris_metrics:
                    continue
                source_path = manifest_data.get("input_path", str(manifest_path))
                records.append({
                    "source_path": source_path,
                    "manifest_path": str(manifest_path),
                    "polaris_metrics": polaris_metrics,
                })
            except Exception as exc:
                logger.warning(f"跳過 manifest {manifest_path}: {exc}")
    return records


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="generate_improvement_report",
        description="產生依指標分數與功能缺口排序的改善追蹤報告",
    )
    ap.add_argument(
        "command",
        choices=["generate", "from-metrics"],
        help="generate=從 manifest 掃描; from-metrics=從 metrics_output 載入",
    )
    ap.add_argument(
        "--scan-dirs",
        nargs="+",
        default=["."],
        help="掃描目錄（generate 模式）",
    )
    ap.add_argument(
        "--metrics-output",
        default="metrics_output",
        help="metrics_output 目錄（from-metrics 模式）",
    )
    ap.add_argument(
        "--output",
        default="output/improvement_tracker.json",
        help="輸出 JSON 路徑",
    )
    ap.add_argument(
        "--recursive/--no-recursive",
        default=True,
        help="是否遞迴掃描子目錄",
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="詳細輸出",
    )

    args = ap.parse_args(argv)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        from note_filler.improvement_tracker import generate_improvement_report
    except ImportError as exc:
        logger.error(f"無法導入 improvement_tracker: {exc}")
        return 1

    if args.command == "generate":
        records = _load_records_from_manifests(
            [Path(d) for d in args.scan_dirs],
            recursive=args.recursive,
        )
    else:
        records = _load_records_from_metrics_output(Path(args.metrics_output))

    if not records:
        print("找不到可分析的指標記錄")
        return 0

    report = generate_improvement_report(records)
    report_dict = report.to_dict()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )

    # 摘要輸出
    print(f"\n改善追蹤報告已產生: {output_path}")
    print(f"  總項目數: {report.total_items}")
    print(f"  優先級分佈:")
    for level, count in sorted(report.by_priority.items()):
        print(f"    {level}: {count}")
    print(f"  指標分佈:")
    for metric, count in sorted(report.by_metric.items()):
        print(f"    {metric}: {count}")

    if report.items:
        print(f"\n改善項目（按 ROI 排序）:")
        for item in report.items:
            print(
                f"  [{item.priority_level}] {item.id} {item.title}: "
                f"{item.metric_name} = {item.baseline_value:.3f} → "
                f"{item.target_value:.3f} (差距 {item.gap_to_threshold:.3f}, "
                f"ROI {item.roi_score:.2f})"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
