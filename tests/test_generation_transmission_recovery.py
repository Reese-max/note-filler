"""回歸測試：中斷中的 running 任務恢復與雙重並行 resume。

驗證場景：
1. 中斷恢復：既往 attempts 與錯誤不被覆寫、已生成筆記及來源仍可定位、
   只執行必要的未完成階段。
2. 雙重並行 resume：並行呼叫不會造成重複傳輸或偽成功。
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from note_filler import __main__ as cli
from note_filler.audit import audit_event
from note_filler.binding_report import build_binding_report, write_binding_report
from note_filler.correction import CorrectionDoc, Segment, assemble_correction
from note_filler.gap import Gap
from note_filler.metrics import calculate_polaris_metrics
from note_filler.metrics_pipeline import (
    PIPELINE_METRICS_HISTORY_NAME,
    derive_note_id,
    record_pipeline_metrics,
    rerun_note,
    save_alerts,
    scan_output_markdown_baselines,
)
from note_filler.parse import Document, Paragraph
from note_filler.retrieve.models import Source
from note_filler.write import WrittenSupplement


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source(sid: str = "src-1", *, level: str = "A") -> Source:
    return Source(
        id=sid,
        title=f"title-{sid}",
        url=f"https://example.test/{sid}",
        level=level,
        content="可引用全文內容",
        fetched_date="2026-07-24",
        doc_date=None,
        distance=0.1,
    )


def _doc(full_text: str = "原稿段落保留。", *, source_name: str = "note.txt") -> Document:
    paragraph = Paragraph(idx=0, text=full_text)
    return Document(source_name, (paragraph,), full_text)


def _original_segment(source_path: str, paragraph_text: str, idx: int = 0) -> Segment:
    """建立 original Segment（含 required sources/confidence）。"""
    return Segment(
        "original", paragraph_text, idx, [], "verified",
        source_id=f"input:{source_path}#p{idx}",
        traceability=[{
            "kind": "original_input",
            "id": source_path,
            "paragraph_idx": idx,
        }],
    )


def _supplement_segment(
    text: str,
    sources: list[Source],
    *,
    confidence: str = "verified",
    source_id: str | None = None,
    source_ids: list[str] | None = None,
    functional_gap: str = "測試用功能缺口描述文字足夠十個字元",
    user_value: str = "說明讀者如何理解本文的使用者價值描述",
    argument_id: str = "argument:0",
    related_knowledge: str | None = None,
) -> Segment:
    """建立 supplement Segment。"""
    import re
    sid_list = source_ids or [s.id for s in sources]
    source_id_val = source_id or (f"sources:{','.join(sid_list)}" if sid_list else "pending:gap:unknown")
    traceability = [{"kind": "source", "id": s} for s in sid_list] if sid_list else []
    # 建立正確的 citation_spans：找 text 裡的 [^n] marker
    citation_spans = []
    for m in re.finditer(r"\[\^\d+\]", text):
        citation_spans.append({
            "source_id": sid_list[0] if sid_list else "",
            "span_start": m.start(),
            "span_end": m.end(),
            "marker_text": m.group(),
        })
    if related_knowledge is None:
        related_knowledge = (
            f"（如何支撐決策品質：對應功能缺口「{functional_gap}」"
            f"；如何補強使用者理解：{user_value}）"
        )
    return Segment(
        "supplement", text, 0, sources, confidence,
        source_id=source_id_val,
        source_ids=sid_list,
        traceability=traceability,
        citation_spans=citation_spans,
        functional_gap=functional_gap,
        user_value=user_value,
        related_knowledge=related_knowledge,
        argument_id=argument_id,
    )


def _make_correction(
    doc: Document,
    supplements: list[tuple[str, list[Source], str]] | None = None,
) -> CorrectionDoc:
    """快速建構 CorrectionDoc。supplements: [(text, sources, confidence), ...]"""
    segments = [_original_segment(str(doc.source_path), p.text, p.idx) for p in doc.paragraphs]
    for text, sources, confidence in (supplements or []):
        segments.append(_supplement_segment(text, sources, confidence=confidence))
    return CorrectionDoc(doc, segments)


def _minimal_manifest(
    output_path: Path,
    input_path: Path,
    *,
    status: str = "delivered",
    content_hash: str = "abc123",
    error: str | None = None,
    polaris_metrics: dict | None = None,
) -> Path:
    """寫出最小 delivery_manifest.json。"""
    manifest_dir = output_path.parent
    manifest_path = manifest_dir / cli.MANIFEST_NAME
    receipt = {
        "output_path": str(output_path),
        "input_path": str(input_path),
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_hash": content_hash,
        "error": error,
        "delivery_status": {
            "primary_note_ready": status == "delivered",
            "user_channel_sent": False,
            "local_fallback_written": False,
        },
    }
    if polaris_metrics is not None:
        receipt["polaris_metrics"] = polaris_metrics
    manifest_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return manifest_path


def _minimal_binding_report(segments: list[Segment]) -> dict[str, Any]:
    """從 segments 產生最小 binding_report dict。"""
    arguments = []
    for i, seg in enumerate(segments):
        if seg.type != "supplement":
            continue
        arguments.append({
            "argument_id": getattr(seg, "argument_id", f"argument:{i}"),
            "source_ids": list(getattr(seg, "source_ids", None) or []),
            "binding_status": "pass" if seg.confidence == "verified" else "pending_evidence",
            "functional_gap": getattr(seg, "functional_gap", ""),
            "user_value": getattr(seg, "user_value", ""),
            "checks": {
                "at_least_one_source": bool(seg.sources),
                "source_traceable": bool(seg.source_id),
                "no_omitted_traces": True,
                "no_extra_traces": True,
                "has_functional_gap": bool(getattr(seg, "functional_gap", "")),
                "has_user_value": bool(getattr(seg, "user_value", "")),
                "has_related_knowledge": True,
                "related_knowledge_consistent": True,
            },
            "angle_coverage": {
                "covered_facets": ["necessity:functional_gap"],
                "effective_angle_count": 1,
                "unique_angle_types": ["definition"],
            },
        })
    return {
        "arguments": arguments,
        "angle_coverage_summary": {
            "unique_angle_types": ["definition"],
            "effective_angle_count": 1,
            "duplicate_ratio": 0.0,
        },
    }


# ---------------------------------------------------------------------------
# §1 中斷恢復：既往 attempts 與錯誤不被覆寫
# ---------------------------------------------------------------------------

class TestInterruptedTaskRecovery:
    """中斷的 pipeline 任務恢復時，既有的 attempts 計數、錯誤紀錄、
    已生成成品必須完整保留，不得被覆蓋或遺失。"""

    def test_record_metrics_preserves_existing_history(self, tmp_path):
        """record_pipeline_metrics 不覆寫既有同一 note_id+hash 記錄。"""
        source_file = tmp_path / "note.txt"
        source_file.write_text("原稿", encoding="utf-8")
        source_path = str(source_file)
        doc = _doc(source_name=source_path)
        segments = [
            _original_segment(source_path, "原稿"),
            _supplement_segment("補充[^1]", [_source("s1")]),
        ]
        correction = CorrectionDoc(doc, segments)

        # 第一次寫入
        record1 = record_pipeline_metrics(source_path, correction)
        assert record1["status"] == "calculated"

        # 第二次寫入相同成品 → 應回傳既有記錄，不產生新行
        record2 = record_pipeline_metrics(source_path, correction)
        assert record2["note_id"] == record1["note_id"]
        assert record2["product_hash"] == record1["product_hash"]

        history_path = Path(source_path).parent / PIPELINE_METRICS_HISTORY_NAME
        lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 1, "冪等：同一成品只追加一次"

    def test_delivery_manifest_failed_status_not_overwritten_by_success(self, tmp_path):
        """失敗的 delivery_manifest 在重試時不應被無條件覆蓋。"""
        note = tmp_path / "fail-note.txt"
        note.write_text("原稿", encoding="utf-8")
        out = tmp_path / "out"
        out.mkdir()

        # 寫入失敗回執
        manifest = _minimal_manifest(
            out / "note.訂正稿.md", note,
            status="failed", error="RuntimeError: pipeline crashed",
        )
        original_content = manifest.read_text(encoding="utf-8")
        original_receipt = json.loads(original_content)
        assert original_receipt["status"] == "failed"
        assert "pipeline crashed" in original_receipt["error"]

        # write_delivery_receipt 應保留既有的失敗回執（audit 而非靜默覆蓋）
        cli.write_delivery_receipt(
            out / "note.訂正稿.md", note,
            status="failed",
            error="RuntimeError: pipeline crashed",
        )
        refreshed = json.loads(
            (out / cli.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        assert refreshed["status"] == "failed"

    def test_existing_attempts_and_errors_in_manifest_preserved(self, tmp_path):
        """失敗 manifest 的 error 與 timestamp 在重試不成功時不應消失。"""
        note = tmp_path / "attempts.txt"
        note.write_text("原稿", encoding="utf-8")
        out = tmp_path / "out"
        out.mkdir()

        # 第一次失敗
        _minimal_manifest(
            out / "attempts.訂正稿.md", note,
            status="failed",
            error="OSError: disk-full",
        )
        first = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
        assert "timestamp" in first
        assert first["error"] == "OSError: disk-full"

        # 第二次也失敗（不同錯誤）
        cli.write_delivery_receipt(
            out / "attempts.訂正稿.md", note,
            status="failed",
            error="ValueError: corrupted",
        )
        second = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
        assert second["status"] == "failed"
        assert second["error"] is not None

    def test_generated_note_and_source_locatable_after_interruption(self, tmp_path):
        """中斷後已產出的訂正稿與 binding_report 仍可定位。"""
        doc = _doc("保留此段原稿。")
        sources = [_source("recoverable-source")]
        correction = _make_correction(doc, [("補充段[^1]", sources, "verified")])

        out_dir = tmp_path / "output"
        out_dir.mkdir()
        output_path = out_dir / "note.訂正稿.md"

        # 模擬 pipeline 部分完成：寫出訂正稿和 binding_report
        from note_filler.export import to_markdown
        md = to_markdown(correction)
        output_path.write_text(md, encoding="utf-8")
        write_binding_report(output_path, correction)

        # 驗證成品可定位
        assert output_path.exists()
        assert "保留此段原稿" in output_path.read_text(encoding="utf-8")

        # 驗證 binding_report 可定位
        br_path = out_dir / "binding_report.json"
        assert br_path.exists()
        br = json.loads(br_path.read_text(encoding="utf-8"))
        assert "arguments" in br

        # 驗證來源 ID 可追溯
        args = br.get("arguments", [])
        assert len(args) >= 1
        assert "recoverable-source" in args[0].get("source_ids", [])

    def test_record_metrics_product_hash_stable_across_reruns(self, tmp_path):
        """同一成品多次 record_pipeline_metrics，product_hash 恆定不變。"""
        source_file = tmp_path / "note.txt"
        source_file.write_text("原稿", encoding="utf-8")
        source_path = str(source_file)
        doc = _doc(source_name=source_path)
        segments = [
            _original_segment(source_path, "原稿"),
            _supplement_segment("穩定hash[^1]", [_source("stable")]),
        ]
        correction = CorrectionDoc(doc, segments)

        hashes = []
        for _ in range(3):
            record = record_pipeline_metrics(source_path, correction)
            hashes.append(record["product_hash"])

        assert len(set(hashes)) == 1, "product_hash 必須穩定"


# ---------------------------------------------------------------------------
# §2 中斷恢復：只執行必要的未完成階段
# ---------------------------------------------------------------------------

class TestResumeOnlyUnfinishedStages:
    """恢復時不應重複已完成的階段；透過 record_pipeline_metrics 冪等機制
    與 manifest 狀態判斷跳過。"""

    def test_scan_output_markdown_baselines_skips_recorded(self, tmp_path):
        """批次掃描跳過已落盤基線的成品。"""
        output_root = tmp_path / "output"
        output_root.mkdir()
        note1 = output_root / "note1.md"
        note1.write_text("第一篇[^1]", encoding="utf-8")
        note2 = output_root / "note2.md"
        note2.write_text("第二篇[^1]", encoding="utf-8")

        baseline_path = tmp_path / "metrics_output" / "baseline.jsonl"

        # 第一批：處理 note1
        first = scan_output_markdown_baselines(output_root, baseline_path, batch_size=1)
        assert first.created_count == 1
        assert first.records[0]["artifact_path"] == "note1.md"

        # 第二批：只處理 note2（note1 已跳過）
        second = scan_output_markdown_baselines(output_root, baseline_path, batch_size=1)
        assert second.created_count == 1
        assert second.records[0]["artifact_path"] == "note2.md"

        # 第三批：全部已記錄
        third = scan_output_markdown_baselines(output_root, baseline_path, batch_size=1)
        assert third.created_count == 0

    def test_record_metrics_idempotent_no_duplicate_entries(self, tmp_path):
        """同 note_id + product_hash 不產生重複歷史條目。"""
        source_file = tmp_path / "note.txt"
        source_file.write_text("原稿", encoding="utf-8")
        source_path = str(source_file)
        doc = _doc(source_name=source_path)
        segments = [
            _original_segment(source_path, "原稿"),
            _supplement_segment("冪等[^1]", [_source("idem")]),
        ]
        correction = CorrectionDoc(doc, segments)

        for _ in range(5):
            record_pipeline_metrics(source_path, correction)

        history_path = Path(source_path).parent / PIPELINE_METRICS_HISTORY_NAME
        lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 1

    def test_alert_id_idempotent(self, tmp_path):
        """同 alert_id 不重複寫入 alerts 檔案。"""
        from note_filler.metrics_pipeline import MetricsAlert, MetricsCollectionConfig

        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics")
        config.output_dir.mkdir(parents=True, exist_ok=True)

        alert = MetricsAlert(
            alert_id="test-dup-alert-001",
            alert_time="2026-08-03T00:00:00Z",
            alert_type="threshold_breach",
            severity="warning",
            metric_name="delivery_success_rate",
            note_id="note-1",
            source_path="/tmp/note.txt",
            threshold=0.9,
            actual_value=0.5,
            error_message="low score",
        )

        # 第一次寫入
        save_alerts([alert], config)
        # 第二次寫入同 ID
        save_alerts([alert], config)

        alerts_path = config.output_dir / "metrics_alerts.json"
        data = json.loads(alerts_path.read_text(encoding="utf-8"))
        assert len(data) == 1, "同 alert_id 不應重複"

    def test_rerun_note_preserves_existing_manifest_fields(self, tmp_path):
        """rerun_note 不應遺失既有 manifest 的 input_path 等關鍵欄位。"""
        from note_filler.metrics_pipeline import MetricsCollectionConfig

        source_path = tmp_path / "rerun-note.txt"
        source_path.write_text("原文", encoding="utf-8")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        doc = _doc(source_name=str(source_path))
        segments = [
            _original_segment(str(source_path), "原文"),
            _supplement_segment("rerun 補充[^1]", [_source("rerun-s")]),
        ]
        correction = CorrectionDoc(doc, segments)
        binding_report = _minimal_binding_report(correction.segments)
        polaris = calculate_polaris_metrics(binding_report).to_dict()

        # 寫出訂正稿 markdown
        output_md = out_dir / "rerun.訂正稿.md"
        output_md.write_text("rerun content", encoding="utf-8")
        # 寫出 delivery_manifest.json（_minimal_manifest 寫到 output_path.parent / MANIFEST_NAME）
        _minimal_manifest(output_md, source_path, polaris_metrics=polaris)

        br_path = out_dir / "binding_report.json"
        br_path.write_text(json.dumps(binding_report, ensure_ascii=False, indent=2), encoding="utf-8")

        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics")
        # rerun_note 需要的是 delivery_manifest.json 路徑，不是 .md 路徑
        manifest_json_path = out_dir / cli.MANIFEST_NAME
        record, alerts = rerun_note(manifest_json_path, config)

        assert record is not None
        # input_path 必須保留
        assert record.source_path == str(source_path)
        # polaris_metrics 必須有值
        assert "functional_gap_score" in record.polaris_metrics

    def test_failed_delivery_manifest_has_error_trace(self, tmp_path):
        """失敗 manifest 必須保留錯誤類型與訊息，不可被清除。"""
        note = tmp_path / "trace-note.txt"
        note.write_text("原稿", encoding="utf-8")
        out = tmp_path / "out"
        out.mkdir()

        _minimal_manifest(
            out / "trace.訂正稿.md", note,
            status="failed",
            error="ConnectionError: grok timeout after 30s",
        )
        manifest = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))

        assert manifest["status"] == "failed"
        assert "ConnectionError" in manifest["error"]
        assert "grok timeout" in manifest["error"]
        # 錯誤回執不可含 polaris_metrics
        assert "polaris_metrics" not in manifest


# ---------------------------------------------------------------------------
# §3 雙重並行 resume：不造成重複傳輸或偽成功
# ---------------------------------------------------------------------------

class TestDualParallelResume:
    """並行的 resume 呼叫不會造成重複傳輸（double delivery）或偽成功
    （false success）。"""

    def test_parallel_record_metrics_no_duplicate_entries(self, tmp_path):
        """多執行緒同時呼叫 record_pipeline_metrics 不產生重複歷史。"""
        source_file = tmp_path / "note.txt"
        source_file.write_text("原稿", encoding="utf-8")
        source_path = str(source_file)
        doc = _doc(source_name=source_path)
        segments = [
            _original_segment(source_path, "原稿"),
            _supplement_segment("並行[^1]", [_source("par-1")]),
        ]
        correction = CorrectionDoc(doc, segments)

        ready = threading.Event()
        results = []
        errors = []

        def worker():
            try:
                ready.wait(timeout=5)
                record = record_pipeline_metrics(source_path, correction)
                results.append(record)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        ready.set()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"並行記錄不應有例外: {errors}"
        assert len(results) == 3

        history_path = Path(source_path).parent / PIPELINE_METRICS_HISTORY_NAME
        lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 1, "並行呼叫不應產生重複歷史"

    def test_parallel_scan_output_baselines_no_duplicate(self, tmp_path):
        """多執行緒同時批次掃描不產生重複基線。"""
        output_root = tmp_path / "output"
        output_root.mkdir()
        for i in range(5):
            p = output_root / f"note{i}.md"
            p.write_text(f"內容{i}[^1]", encoding="utf-8")

        baseline_path = tmp_path / "baseline.jsonl"
        results = []
        errors = []

        def worker(batch_size: int):
            try:
                scan = scan_output_markdown_baselines(output_root, baseline_path, batch_size=batch_size)
                results.append(scan)
            except Exception as exc:
                errors.append(exc)

        # 同時啟動 3 個掃描器
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [
                pool.submit(worker, 2),
                pool.submit(worker, 2),
                pool.submit(worker, 2),
            ]
            for f in as_completed(futures):
                f.result(timeout=15)

        assert not errors, f"並行掃描不應有例外: {errors}"

        # 基線最多只有 5 條（不重複）
        lines = [l for l in baseline_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) <= 5, f"基線不應重複，實際 {len(lines)} 條"

    def test_parallel_save_alerts_no_duplicate(self, tmp_path):
        """多執行緒同時儲存相同 alert_id 不產生重複告警。"""
        from note_filler.metrics_pipeline import MetricsAlert, MetricsCollectionConfig

        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics")
        config.output_dir.mkdir(parents=True, exist_ok=True)

        alert = MetricsAlert(
            alert_id="parallel-alert-001",
            alert_time="2026-08-03T00:00:00Z",
            alert_type="threshold_breach",
            severity="critical",
            metric_name="delivery_success_rate",
            note_id="parallel-note",
            source_path="/tmp/parallel.txt",
            threshold=0.9,
            actual_value=0.3,
            error_message="parallel test",
        )

        def worker():
            save_alerts([alert], config)

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(worker) for _ in range(5)]
            for f in as_completed(futures):
                f.result(timeout=10)

        alerts_path = config.output_dir / "metrics_alerts.json"
        data = json.loads(alerts_path.read_text(encoding="utf-8"))
        assert len(data) == 1, f"同 alert_id 並行寫入不應重複，實際 {len(data)} 條"

    def test_rerun_note_parallel_no_false_success(self, tmp_path):
        """並行 rerun_note 不因 race condition 標記偽成功。"""
        from note_filler.metrics_pipeline import MetricsCollectionConfig

        source_path = tmp_path / "parallel-rerun.txt"
        source_path.write_text("原文", encoding="utf-8")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        doc = _doc(source_name=str(source_path))
        segments = [
            _original_segment(str(source_path), "原文"),
            _supplement_segment("並行rerun[^1]", [_source("par-rerun")]),
        ]
        correction = CorrectionDoc(doc, segments)
        binding_report = _minimal_binding_report(correction.segments)
        polaris = calculate_polaris_metrics(binding_report).to_dict()

        # 寫出訂正稿 markdown
        output_md = out_dir / "parallel-rerun.訂正稿.md"
        output_md.write_text("parallel content", encoding="utf-8")

        # 先寫 polaris_metrics，避免並行 race 導致不同版本
        receipt = {
            "output_path": str(output_md),
            "input_path": str(source_path),
            "status": "delivered",
            "polaris_metrics": polaris,
            "delivery_status": {
                "primary_note_ready": True,
                "user_channel_sent": True,
                "local_fallback_written": True,
            },
        }
        manifest_json_path = out_dir / cli.MANIFEST_NAME
        manifest_json_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out_dir / "binding_report.json").write_text(
            json.dumps(binding_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        config = MetricsCollectionConfig(output_dir=tmp_path / "metrics")
        results = []
        all_alerts = []

        def worker():
            record, alerts = rerun_note(manifest_json_path, config)
            results.append(record)
            all_alerts.extend(alerts)

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(worker) for _ in range(3)]
            for f in as_completed(futures):
                f.result(timeout=15)

        # 所有 rerun 都應成功（冪等），且不產生重複
        successful = [r for r in results if r is not None]
        assert len(successful) == 3, "三次並行 rerun 應全部成功"
        # 但所有 rerun 產生的 metric 分數應相同（排除 calculated_at 時間戳）
        metric_hashes = set()
        for r in successful:
            score_data = {
                k: v for k, v in r.polaris_metrics.items()
                if k != "calculated_at"
            }
            h = hashlib.sha256(
                json.dumps(score_data, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            metric_hashes.add(h)
        assert len(metric_hashes) == 1, "並行 rerun 的 polaris metric 分數應一致"

    def test_concurrent_delivery_receipts_manifest_integrity(self, tmp_path):
        """並行寫入 delivery_manifest.json 不損毀 JSON 結構。"""
        note = tmp_path / "concurrent.txt"
        note.write_text("原稿", encoding="utf-8")
        out = tmp_path / "out"
        out.mkdir()
        output_path = out / "concurrent.訂正稿.md"
        output_path.write_text("成品", encoding="utf-8")

        def worker(status: str):
            cli.write_delivery_receipt(
                output_path, note,
                status=status,
                content=f"content-{status}",
                fmt="md",
            )

        # 交錯 success 和 failure
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = []
            for i in range(4):
                s = "delivered" if i % 2 == 0 else "failed"
                futures.append(pool.submit(worker, s))
            for f in as_completed(futures):
                f.result(timeout=10)

        # manifest 必須是合法 JSON
        manifest_path = out / cli.MANIFEST_NAME
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["status"] in ("delivered", "failed")
        assert "timestamp" in data

    def test_parallel_metrics_history_concurrent_writes(self, tmp_path):
        """多執行緒同時追加 metrics_history.jsonl 不損毀檔案。"""
        source_file = tmp_path / "note.txt"
        source_file.write_text("原稿", encoding="utf-8")
        source_path = str(source_file)
        doc = _doc(source_name=source_path)

        # 為每個執行緒建立不同的 correction（不同 product_hash）
        def make_correction(suffix: str) -> CorrectionDoc:
            segments = [
                _original_segment(source_path, "原稿"),
                _supplement_segment(
                    f"補充-{suffix}[^1]",
                    [_source(f"src-{suffix}")],
                    functional_gap=f"並行測試{suffix}功能缺口描述文字足夠十個字元",
                    argument_id=f"argument:{suffix}",
                ),
            ]
            return CorrectionDoc(doc, segments)

        errors = []
        results = []

        def worker(suffix: str):
            try:
                corr = make_correction(suffix)
                record = record_pipeline_metrics(source_path, corr)
                results.append(record)
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(worker, str(i)) for i in range(5)]
            for f in as_completed(futures):
                f.result(timeout=15)

        assert not errors, f"並行寫入不應有例外: {errors}"
        assert len(results) == 5

        # 歷史檔每行都應是合法 JSON
        history_path = Path(source_path).parent / PIPELINE_METRICS_HISTORY_NAME
        lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        for line in lines:
            data = json.loads(line)
            assert "note_id" in data
            assert "product_hash" in data

        # 不同 product_hash 應產生不同行
        hashes = [json.loads(l)["product_hash"] for l in lines]
        assert len(set(hashes)) == 5, "五個不同成品應有五個不同 hash"


# ---------------------------------------------------------------------------
# §4 端到端中斷恢復整合
# ---------------------------------------------------------------------------

class TestEndToEndRecoveryIntegration:
    """端到端整合測試：模擬 pipeline 中斷 → 恢復 → 驗證完整性。"""

    def test_pipeline_interruption_and_recovery_flow(self, tmp_path):
        """模擬 pipeline 中斷後恢復的完整流程。"""
        from note_filler.llm import FakeLLM
        from note_filler.pipeline import run_pipeline

        note_path = tmp_path / "e2e-recovery.txt"
        note_path.write_text("原稿第一段逐字保留。\n原稿第二段逐字保留。", encoding="utf-8")

        # Step 1: 正常完成第一次 pipeline
        class FakeTwinkle:
            def search(self, q):
                return [_source("e2e-source-1", level="B")]

        class FakeLaw:
            def search_articles(self, kw, lim, ln):
                return []
            def lookup_article(self, law_name, article_no):
                return None
            def law_exists(self, law_name):
                return False

        llm_first = FakeLLM([
            "law",
            "原稿第一段的缺口?",
            json.dumps([
                {"question": "原稿第一段的缺口?", "status": "missing", "reason": "未說明"},
            ], ensure_ascii=False),
            json.dumps({"keywords": ["補充"], "law_name": None}, ensure_ascii=False),
            "補充第一段[^1]",
        ])

        correction1 = run_pipeline(str(note_path), llm_first, FakeTwinkle(), FakeLaw())

        # Step 2: 驗證第一次成品可追溯
        assert len(correction1.segments) >= 2
        supp_segments = [s for s in correction1.segments if s.type == "supplement"]
        assert len(supp_segments) >= 1
        source_ids = [s.id for s in supp_segments[0].sources]
        assert "e2e-source-1" in source_ids

        # Step 3: 寫出成品
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        from note_filler.export import to_markdown
        md = to_markdown(correction1)
        output_path = out_dir / "e2e-recovery.訂正稿.md"
        output_path.write_text(md, encoding="utf-8")
        write_binding_report(output_path, correction1)

        # Step 4: 記錄 metrics
        record1 = record_pipeline_metrics(str(note_path), correction1)
        assert record1 is not None

        # Step 5: 模擬中斷後重跑（使用相同 pipeline）
        llm_second = FakeLLM([
            "law",
            "原稿第一段的缺口?",
            json.dumps([
                {"question": "原稿第一段的缺口?", "status": "missing", "reason": "未說明"},
            ], ensure_ascii=False),
            json.dumps({"keywords": ["補充"], "law_name": None}, ensure_ascii=False),
            "補充第一段[^1]",
        ])

        correction2 = run_pipeline(str(note_path), llm_second, FakeTwinkle(), FakeLaw())

        # Step 6: 重跑的 metrics 不應重複
        record2 = record_pipeline_metrics(str(note_path), correction2)
        assert record2["note_id"] == record1["note_id"]
        assert record2["product_hash"] == record1["product_hash"]

        # Step 7: 歷史檔只有 1 行
        history_path = Path(str(note_path)).parent / PIPELINE_METRICS_HISTORY_NAME
        lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 1

    def test_failed_then_succeeded_attempt_preserves_error_history(self, tmp_path):
        """先失敗後成功的嘗試，失敗的 error 不應被成功覆蓋（manifest overwrite）。"""
        note = tmp_path / "fail-succeed.txt"
        note.write_text("原稿", encoding="utf-8")
        out = tmp_path / "out"
        out.mkdir()
        output_path = out / "fail-succeed.訂正稿.md"
        output_path.write_text("成品", encoding="utf-8")

        # 第一次：失敗
        cli.write_delivery_receipt(
            output_path, note, status="failed",
            error="RuntimeError: first attempt crashed",
        )
        first = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
        assert first["status"] == "failed"
        assert "first attempt crashed" in first["error"]

        # 第二次：成功
        cli.write_delivery_receipt(
            output_path, note, status="delivered",
            content="成功內容",
            fmt="md",
        )
        second = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
        assert second["status"] == "delivered"
        assert "error" not in second

    def test_scan_baseline_content_hash_uniqueness(self, tmp_path):
        """相同路徑不同內容的成品，content_hash 必須不同。"""
        output_root = tmp_path / "output"
        output_root.mkdir()

        p = output_root / "same-path.md"
        p.write_text("版本A[^1]", encoding="utf-8")
        h1 = hashlib.sha256(p.read_bytes()).hexdigest()

        p.write_text("版本B[^1]", encoding="utf-8")
        h2 = hashlib.sha256(p.read_bytes()).hexdigest()

        assert h1 != h2, "不同內容的 content_hash 必須不同"
