"""交付回執(delivery receipt)測試。

驗證 digest 除了落盤外,還有明確的對外送達紀錄——
可查詢的 delivery_manifest.json 作為交付回執,
不可只靠本機檔案存在判定完成。

L035/L036:不可只靠 exit code 或檔案存在判定成功;
必須同時驗證有可讀輸出與明確完成訊號。
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from note_filler import __main__ as cli
from note_filler.metrics_pipeline import (
    MetricsCollectionConfig,
    collect_metrics_from_manifest,
    derive_note_id,
    rerun_note,
    scan_and_collect_metrics,
)
from note_filler.recovery import recover_delivery, verify_delivery_artifacts

def delivery_manifest_path(output):
    from note_filler.sidecars import delivery_manifest_path as _impl
    return _impl(output)


def binding_report_path(output):
    from note_filler.sidecars import binding_report_path as _impl
    return _impl(output)


def _load_output_metrics(markdown_path, content_hash):
    from note_filler.metrics_pipeline import _load_output_metrics as _impl
    return _impl(markdown_path, content_hash)


class _Metrics:
    def to_dict(self):
        return {"schema": "note_filler.polaris_metrics.v1"}



class _FakeDoc:
    """最小替身:含 2 個 segment,模擬 pipeline 產出.

    成功路徑必須具備角度有效性必要欄位（functional_gap／user_value／相異角度），
    否則 write_binding_report 角度有效性閘會明確拒絕。
    """
    class _Seg:
        def __init__(
            self,
            type_: str,
            confidence: str = "verified",
            angle_type: str = "",
            angle_key: str = "",
            text: str = "test text",
            functional_gap: str = "",
            user_value: str = "",
        ):
            self.type = type_
            self.confidence = confidence
            self.text = text
            self.sources = []
            self.traceability = []
            self.source_id = ""
            self.angle_type = angle_type
            self.angle_labels = (
                [angle_type, "functional_gap", "user_value"]
                if angle_type
                else []
            )
            self.angle_key = angle_key
            self.functional_gap = functional_gap
            self.user_value = user_value
            self.argument_id = ""
            self.angle_tags = list(self.angle_labels)
            self.valid_angle_count = 1 if angle_type else 0
            self.deduped_angle_count = 1 if angle_type else 0
            self.duplicate_angles: list[str] = []

    segments = [
        _Seg("original"),
        _Seg(
            "supplement",
            "verified",
            "definition",
            "definition:行政處分如何定義",
            text="行政處分如何定義之補充",
            functional_gap="原稿未定義行政處分",
            user_value="補齊讀者對「行政處分如何定義？」所需的說明",
        ),
        _Seg(
            "supplement",
            "pending_evidence",
            "limitation",
            "limitation:行政處分有何限制",
            text="行政處分有何限制之補充",
            functional_gap="原稿未說明限制",
            user_value="補齊讀者對「行政處分有何限制？」所需的說明",
        ),
    ]


# ---- 核心:process_file 成功後必須寫出 delivery receipt -------------------

def test_process_file_writes_delivery_receipt_on_success(tmp_path, monkeypatch):
    """成功交付後必須寫出 delivery_manifest.json,且內容可查詢。"""
    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n這是一份有內容的訂正稿。")

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    # manifest 必須存在於輸出檔同目錄
    manifest_path = Path(r["output"]).parent / cli.MANIFEST_NAME
    assert manifest_path.exists(), (
        f"成功交付後必須寫出 {cli.MANIFEST_NAME} 作為可查詢的交付回執；"
        f"預期路徑: {manifest_path}"
    )

    # manifest 內容必須合法且含所有必要欄位
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_keys = {
        "output_path", "input_path", "status", "timestamp", "content_hash",
        "delivery_status",
    }
    assert required_keys.issubset(manifest.keys()), (
        f"manifest 缺少必要欄位: {required_keys - manifest.keys()}"
    )
    assert manifest["status"] == "delivered", (
        f"成功交付的 manifest status 必須為 'delivered'，實際: {manifest['status']}"
    )
    assert manifest["output_path"] == r["output"]
    assert manifest["input_path"] == str(note)
    assert manifest["content_hash"], "content_hash 不可為空"
    expected_ds = {
        "primary_note_ready": True,
        "user_channel_sent": False,
        "local_fallback_written": True,
    }
    assert expected_ds.items() <= manifest["delivery_status"].items(), (
        f"manifest delivery_status 缺必要欄位: "
        f"{set(expected_ds) - set(manifest['delivery_status'])}"
    )


def test_process_file_receipt_status_is_delivered(tmp_path, monkeypatch):
    """manifest status 欄位必須明確標記為 delivered,不可含糊。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "有內容的訂正稿。")

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    manifest = json.loads(
        (Path(r["output"]).parent / cli.MANIFEST_NAME).read_text(encoding="utf-8")
    )
    # status 必須是明確的字串,不是空值或 None
    assert isinstance(manifest["status"], str) and manifest["status"], (
        f"manifest status 不可為空或 None: {manifest['status']!r}"
    )
    assert manifest["status"] == "delivered"


def test_process_file_receipt_timestamp_is_iso8601(tmp_path, monkeypatch):
    """manifest timestamp 必須是合法 ISO 8601,代表交付時間點。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "有內容。")

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    manifest = json.loads(
        (Path(r["output"]).parent / cli.MANIFEST_NAME).read_text(encoding="utf-8")
    )
    # ISO 8601 基本格式檢查
    ts = manifest["timestamp"]
    assert "T" in ts, f"timestamp 非 ISO 8601 格式: {ts}"
    # 可被 datetime 解析
    from datetime import datetime, timezone
    datetime.fromisoformat(ts.replace("Z", "+00:00"))


# ---- manifest 必須可在交付後被外部查詢 -----------------------------------

def test_delivery_receipt_queryable_after_delivery(tmp_path, monkeypatch):
    """交付後,manifest 必須可被外部程式讀取並回傳交付狀態。"""
    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "訂正稿內容。")

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    # 模擬外部查詢:讀取 manifest 並取得交付狀態
    manifest_path = Path(r["output"]).parent / cli.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # 外部查詢結果必須包含可判定的交付資訊
    assert manifest["status"] == "delivered"
    assert Path(manifest["output_path"]).exists(), (
        f"manifest 指向的 output_path 必須可讀取: {manifest['output_path']}"
    )


# ---- 失敗時 manifest 不得偽造成功 ----------------------------------------

def test_process_file_empty_content_no_success_manifest(tmp_path, monkeypatch):
    """空內容時不得寫出 status=delivered 的 manifest。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "   \n\t  ")

    with pytest.raises(RuntimeError, match="為空|送達"):
        cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    # 失敗後 manifest 要麼不存在,要麼 status≠delivered
    manifest_path = tmp_path / cli.MANIFEST_NAME
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest.get("status") != "delivered", (
            "空內容失敗時 manifest 不得標記為 delivered"
        )


def test_process_file_os_error_no_success_manifest(tmp_path, monkeypatch):
    """寫出失敗(OSError)時不得留下 delivered 狀態的 manifest。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "有內容。")

    def _boom_write(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", _boom_write)

    with pytest.raises(OSError, match="disk full"):
        cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    # OSError 發生在 write_text 階段 → manifest 不應存在
    # (因為 manifest 也在 write_text 後才寫,但 main output 寫出就失敗了)
    manifest_path = tmp_path / cli.MANIFEST_NAME
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest.get("status") != "delivered", (
            "寫出失敗時 manifest 不得標記為 delivered"
        )


# ---- content_hash 必須與實際輸出一致 -------------------------------------

def test_process_file_receipt_content_hash_matches_output(tmp_path, monkeypatch):
    """manifest content_hash 必須與實際輸出檔的 sha256 一致。"""
    import hashlib

    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    expected_body = "這份訂正稿的完整內容用於驗證 hash。"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: expected_body)

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    manifest = json.loads(
        (Path(r["output"]).parent / cli.MANIFEST_NAME).read_text(encoding="utf-8")
    )
    actual_hash = hashlib.sha256(expected_body.encode("utf-8")).hexdigest()[:16]
    assert manifest["content_hash"] == actual_hash, (
        f"manifest content_hash ({manifest['content_hash']}) "
        f"≠ 實際 sha256[:16] ({actual_hash})"
    )


# ---- JSON 格式也必須產生 receipt ----------------------------------------

def test_process_file_json_format_writes_receipt(tmp_path, monkeypatch):
    """JSON 格式交付同樣必須寫出 delivery receipt。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_json", lambda doc: {"ok": True})

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="json")

    manifest_path = Path(r["output"]).parent / cli.MANIFEST_NAME
    assert manifest_path.exists(), "JSON 格式交付也必須寫出 manifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "delivered"
    assert manifest["format"] == "json"


# ---- manifest 與輸出檔並存 ------------------------------------------------

def test_process_file_manifest_copexists_with_output(tmp_path, monkeypatch):
    """manifest 必須與輸出檔並存,且兩者路徑同目錄。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "內容。")

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="md")

    output = Path(r["output"])
    manifest = output.parent / cli.MANIFEST_NAME
    assert output.exists(), "輸出檔必須存在"
    assert manifest.exists(), "manifest 必須存在"
    # 兩者在同一目錄
    assert output.parent == manifest.parent


# ---- 禁止外洩底層錯誤檢查 ----------------------------------------------

def test_process_file_rejects_traceback_in_content(tmp_path, monkeypatch):
    """內容含 traceback 字樣時應拒絕送達成功。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "正常內容\nTraceback (most recent call last):")

    with pytest.raises(RuntimeError, match="traceback"):
        cli.process_file(note, None, None, None, out_dir=None, fmt="md")


def test_process_file_rejects_provider_error_in_content(tmp_path, monkeypatch):
    """內容含 provider error 字樣時應拒絕送達成功。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "正常內容\nProvider error: API key invalid")

    with pytest.raises(RuntimeError, match="provider error"):
        cli.process_file(note, None, None, None, out_dir=None, fmt="md")


def test_process_file_rejects_connection_error_in_content(tmp_path, monkeypatch):
    """內容含 connection error 字樣時應拒絕送達成功。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "正常內容\nConnection error: timeout")

    with pytest.raises(RuntimeError, match="connection error"):
        cli.process_file(note, None, None, None, out_dir=None, fmt="md")


def test_process_file_allows_clean_content(tmp_path, monkeypatch):
    """不含錯誤訊息的乾淨內容應正常送達。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "這是乾淨的訂正稿內容，沒有錯誤訊息。")

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="md")
    assert r["output"]
    manifest_path = Path(r["output"]).parent / cli.MANIFEST_NAME
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "delivered"


def test_process_file_json_format_rejects_traceback(tmp_path, monkeypatch):
    """JSON 格式含 traceback 字樣時也應拒絕送達成功。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    
    def _to_json_with_traceback(doc):
        return {"text": "Traceback (most recent call last):", "ok": True}
    
    monkeypatch.setattr(cli, "to_json", _to_json_with_traceback)

    with pytest.raises(RuntimeError, match="traceback"):
        cli.process_file(note, None, None, None, out_dir=None, fmt="json")


def test_check_no_leaked_errors_case_insensitive(tmp_path, monkeypatch):
    """錯誤檢查應不區分大小寫。"""
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "正常內容\nTRACEBACK: some error")

    with pytest.raises(RuntimeError, match="traceback"):
        cli.process_file(note, None, None, None, out_dir=None, fmt="md")


def test_batch_outputs_keep_independent_receipts_and_reports(tmp_path, monkeypatch):
    """A second note cannot replace the first note's authoritative evidence."""
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "first").mkdir()
    (inputs / "second").mkdir()
    first = inputs / "first" / "note.txt"
    second = inputs / "second" / "note.txt"
    first.write_text("first source", encoding="utf-8")
    second.write_text("second source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"

    first_result = cli.process_file(first, None, None, None, out, "md", state_dir=state_dir)
    first_output = Path(first_result["output"])
    first_manifest = delivery_manifest_path(first_output)
    first_report = binding_report_path(first_output)
    manifest_before = first_manifest.read_bytes()
    report_before = first_report.read_bytes()

    second_result = cli.process_file(second, None, None, None, out, "md", state_dir=state_dir)
    second_output = Path(second_result["output"])
    second_manifest = delivery_manifest_path(second_output)
    second_report = binding_report_path(second_output)
    assert first_output != second_output
    assert first_manifest != second_manifest and first_report != second_report
    assert first_manifest.read_bytes() == manifest_before
    assert first_report.read_bytes() == report_before

    for source, output, receipt, report in (
        (first, first_output, first_manifest, first_report),
        (second, second_output, second_manifest, second_report),
    ):
        data = json.loads(receipt.read_text(encoding="utf-8"))
        assert data["status"] == "delivered"
        assert data["input_path"] == str(source)
        assert data["output_path"] == str(output)
        assert data["output_content_hash"] == hashlib.sha256(output.read_bytes()).hexdigest()
        assert data["binding_report_path"] == str(report)
        assert data["binding_report_content_hash"] == hashlib.sha256(report.read_bytes()).hexdigest()
        assert all(probe.code is None for probe in verify_delivery_artifacts(data, receipt))

    records = scan_and_collect_metrics(MetricsCollectionConfig(scan_dirs=[out]))
    assert {Path(r.manifest_path) for r in records} == {first_manifest, second_manifest}
    rerun_record, alerts = rerun_note(first_manifest, MetricsCollectionConfig(scan_dirs=[out]))
    assert rerun_record is not None
    assert all(alert.alert_type != "rerun_failure" for alert in alerts)
    assert rerun_record.source_path == str(first)

    first_report.write_text("{}", encoding="utf-8")
    stale = json.loads(first_manifest.read_text(encoding="utf-8"))
    assert any(
        probe.kind == "binding_report" and probe.code == "artifact_integrity_mismatch"
        for probe in verify_delivery_artifacts(stale, first_manifest)
    )
    rerun_record, alerts = rerun_note(first_manifest, MetricsCollectionConfig(scan_dirs=[out]))
    assert rerun_record is None
    assert any(alert.alert_type == "rerun_failure" for alert in alerts)


def test_missing_output_keeps_its_sidecars_and_reserves_its_name(tmp_path, monkeypatch):
    """A missing output still owns its receipt and report filename."""
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "note.txt"
    second = second_dir / "note.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"

    first_result = cli.process_file(first, None, None, None, out, "md", state_dir=state_dir)
    first_output = Path(first_result["output"])
    first_manifest = delivery_manifest_path(first_output)
    first_report = binding_report_path(first_output)
    manifest_before = first_manifest.read_bytes()
    report_before = first_report.read_bytes()
    first_output.unlink()

    second_result = cli.process_file(second, None, None, None, out, "md", state_dir=state_dir)
    second_output = Path(second_result["output"])
    assert second_output != first_output
    assert first_manifest.read_bytes() == manifest_before
    assert first_report.read_bytes() == report_before
    assert json.loads(delivery_manifest_path(second_output).read_text(encoding="utf-8"))["input_path"] == str(second)



def test_rerun_keeps_owned_alternate_when_base_artifacts_are_removed(tmp_path, monkeypatch):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "note.txt"
    second = second_dir / "note.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"

    first_result = cli.process_file(first, None, None, None, out, "md", state_dir=state_dir)
    first_output = Path(first_result["output"])
    second_result = cli.process_file(second, None, None, None, out, "md", state_dir=state_dir)
    second_output = Path(second_result["output"])
    assert second_output != first_output

    # Simulate cleanup of the first note's output and its owned audit artifacts.
    first_output.unlink()
    delivery_manifest_path(first_output).unlink()
    binding_report_path(first_output).unlink()

    assert cli._output_for_input(second, out, "md") == second_output


def test_rerun_via_latest_manifest_updates_authoritative_receipt(tmp_path, monkeypatch):
    note = tmp_path / "note.txt"
    note.write_text("source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    result = cli.process_file(note, None, None, None, out, "md", state_dir=tmp_path / "state")
    owned = delivery_manifest_path(Path(result["output"]))
    latest = out / cli.MANIFEST_NAME

    # The note-owned receipt is the evidence that is read and updated; the
    # directory-level copy only mirrors it afterwards.
    owned_data = json.loads(owned.read_text(encoding="utf-8"))
    owned_data["delivery_status"]["user_channel_sent"] = True
    owned_data["transmission_confirmation_hash"] = hashlib.sha256(
        json.dumps(
            owned_data["delivery_status"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    owned.write_text(json.dumps(owned_data, ensure_ascii=False, indent=2), encoding="utf-8")

    record, alerts = rerun_note(latest, MetricsCollectionConfig(scan_dirs=[out]))
    assert record is not None
    assert not any(alert.alert_type == "rerun_failure" for alert in alerts)
    assert Path(record.manifest_path) == owned
    updated = json.loads(owned.read_text(encoding="utf-8"))
    assert updated["metrics_rerun_at"]
    assert updated["delivery_status"]["user_channel_sent"] is True
    assert updated["polaris_metrics"]["delivery_success_rate"]["score"] == 1.0
    assert updated["authoritative"] is True
    latest_now = json.loads(latest.read_text(encoding="utf-8"))
    assert latest_now["authoritative"] is False
    assert latest_now["sidecar_for_output"] == updated["output_path"]
    for key in ("authoritative", "sidecar_scope", "sidecar_for_output"):
        latest_now.pop(key, None)
        updated.pop(key, None)
    assert latest_now == updated


def test_stale_latest_copy_cannot_revert_authoritative_recovery_state(tmp_path, monkeypatch):
    """A copy restored from backup must not undo a note's recorded recovery."""
    note = tmp_path / "note.txt"
    note.write_text("source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    result = cli.process_file(note, None, None, None, out, "md", state_dir=tmp_path / "state")
    output = Path(result["output"])
    owned = delivery_manifest_path(output)
    latest = out / cli.MANIFEST_NAME
    pre_recovery_copy = latest.read_text(encoding="utf-8")

    output.unlink()
    assert recover_delivery(owned).status == "retryable"
    recovered = json.loads(owned.read_text(encoding="utf-8"))
    assert recovered["status"] == "retryable"
    assert len(recovered["recovery_attempts"]) == 1

    # Simulate a restored backup / half-written copy, then a rerun through it.
    latest.write_text(pre_recovery_copy, encoding="utf-8")
    record, alerts = rerun_note(latest, MetricsCollectionConfig(scan_dirs=[out]))
    assert record is not None, alerts
    assert not any(alert.alert_type == "rerun_failure" for alert in alerts)

    after_rerun = json.loads(owned.read_text(encoding="utf-8"))
    assert after_rerun["status"] == "retryable"
    assert len(after_rerun["recovery_attempts"]) == 1
    assert after_rerun["recovery_attempts"][0] == recovered["recovery_attempts"][0]

    output.write_text("# 訂正稿\n完整內容。", encoding="utf-8")
    verdict = recover_delivery(latest)
    assert verdict.verified is True
    # Verified artifacts never become a delivered receipt: the recorded
    # recovery state of the note survives the stale copy.
    after_verify = json.loads(owned.read_text(encoding="utf-8"))
    assert after_verify["status"] == "retryable"
    assert len(after_verify["recovery_attempts"]) == 1


def test_recovery_recreates_a_deleted_latest_copy(tmp_path, monkeypatch):
    """The compatibility copy is recreated, marked non-authoritative."""
    note = tmp_path / "note.txt"
    note.write_text("source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    result = cli.process_file(note, None, None, None, out, "md", state_dir=tmp_path / "state")
    output = Path(result["output"])
    owned = delivery_manifest_path(output)
    latest = out / cli.MANIFEST_NAME
    latest.unlink()
    output.unlink()

    assert recover_delivery(owned).status == "retryable"

    recreated = json.loads(latest.read_text(encoding="utf-8"))
    assert recreated["authoritative"] is False
    assert recreated["sidecar_scope"] == "directory_latest"
    assert recreated["sidecar_for_output"] == str(output)
    assert recreated["status"] == "retryable"


def test_recovery_rejects_receipt_filed_under_another_note(tmp_path, monkeypatch):
    """A receipt whose recorded output names another note is not its evidence."""
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "note.txt"
    second = second_dir / "note.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"
    first_output = Path(cli.process_file(first, None, None, None, out, "md", state_dir=state_dir)["output"])
    second_output = Path(cli.process_file(second, None, None, None, out, "md", state_dir=state_dir)["output"])
    second_receipt = delivery_manifest_path(second_output)

    # Repoint note A's receipt at note B's intact artifacts.
    borrowed = json.loads(delivery_manifest_path(first_output).read_text(encoding="utf-8"))
    second_data = json.loads(second_receipt.read_text(encoding="utf-8"))
    borrowed["output_canonical_path"] = second_data["output_canonical_path"]
    borrowed["output_content_hash"] = second_data["output_content_hash"]
    delivery_manifest_path(first_output).write_text(
        json.dumps(borrowed, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    verdict = recover_delivery(delivery_manifest_path(first_output))
    assert verdict.verified is False
    assert any(probe.kind == "delivery_manifest" for probe in verdict.probes)
    metrics_status, *_ = _load_output_metrics(
        first_output, hashlib.sha256(first_output.read_bytes()).hexdigest()
    )
    assert metrics_status == "metrics_unavailable"


def test_legacy_relative_copy_is_refreshed_by_the_same_notes_failure(tmp_path, monkeypatch):
    """A copy written with relative paths still tracks its own note."""
    note = tmp_path / "note.txt"
    note.write_text("source", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "note.訂正稿.md").write_text("# 訂正稿\n舊成品。", encoding="utf-8")
    (out / "binding_report.json").write_text(json.dumps({"schema": "x"}), encoding="utf-8")
    (out / cli.MANIFEST_NAME).write_text(
        json.dumps(
            {
                "input_path": "note.txt",
                "output_path": "note.訂正稿.md",
                "status": "delivered",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "TASK_STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(
        cli, "run_pipeline", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    assert cli.main(["note.txt", "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 1

    failed = json.loads(delivery_manifest_path(out / "note.訂正稿.md").read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    copy = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert copy["status"] == "failed"
    assert copy["authoritative"] is False


def test_failed_note_keeps_pre_upgrade_latest_copy_of_delivered_note(tmp_path, monkeypatch):
    """A failure receipt must not erase another note's only legacy receipt."""
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("first source", encoding="utf-8")
    second.write_text("second source", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    monkeypatch.setattr(cli, "TASK_STATE_DIR", tmp_path / "state")

    # Pre-upgrade state: note A's only receipt is the directory-level file.
    legacy_output = out / "first.訂正稿.md"
    legacy_output.write_text("# 訂正稿\n舊成品。", encoding="utf-8")
    legacy_receipt = out / cli.MANIFEST_NAME
    legacy_receipt.write_text(
        json.dumps(
            {
                "input_path": str(first),
                "output_path": str(legacy_output),
                "status": "delivered",
                "delivery_status": {"primary_note_ready": True, "local_fallback_written": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    legacy_bytes = legacy_receipt.read_bytes()

    def pipeline(path, *args):
        if Path(path) == second:
            raise RuntimeError("synthetic B failure")
        return _FakeDoc()

    monkeypatch.setattr(cli, "run_pipeline", pipeline)
    assert cli.main([str(second), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 1

    assert legacy_receipt.read_bytes() == legacy_bytes
    assert json.loads(legacy_receipt.read_text(encoding="utf-8"))["input_path"] == str(first)
    failed = json.loads(
        delivery_manifest_path(out / "second.訂正稿.md").read_text(encoding="utf-8")
    )
    assert failed["status"] == "failed"
    assert cli._output_for_input(first, out, "md") == legacy_output


def test_unattributable_output_is_never_overwritten_by_another_note(tmp_path, monkeypatch):
    """An output no receipt attributes stays untouched; the rerun gets its own name."""
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "note.txt"
    second = second_dir / "note.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    monkeypatch.setattr(cli, "TASK_STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(cli, "calculate_polaris_metrics", lambda **kwargs: _Metrics())

    # A corrected note whose receipt and report are both gone: nothing
    # attributes the name to any note.
    unattributed = out / "note.訂正稿.md"
    unattributed.write_text("# 訂正稿\n舊成品。", encoding="utf-8")

    args = ["--outdir", str(out), "--db", str(tmp_path / "missing.db")]
    assert cli.main([str(second), *args]) == 0
    second_output = cli._output_for_input(second, out, "md")
    assert second_output != unattributed
    assert unattributed.read_text(encoding="utf-8") == "# 訂正稿\n舊成品。"

    rerun_target = cli._output_for_input(first, out, "md")
    assert rerun_target != unattributed
    assert not rerun_target.exists()
    assert cli._output_for_input(first, out, "md") == rerun_target


def test_source_suffixed_name_is_never_overwritten(tmp_path, monkeypatch):
    """An existing file at the source-suffixed name blocks the write."""
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "note.txt"
    second = second_dir / "note.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    monkeypatch.setattr(cli, "TASK_STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(cli, "calculate_polaris_metrics", lambda **kwargs: _Metrics())

    base = out / "note.訂正稿.md"
    base.write_text("# 訂正稿\n既有成品。", encoding="utf-8")
    alternate = out / f"note.{hashlib.sha256(str(second.resolve()).encode()).hexdigest()[:12]}.訂正稿.md"
    alternate.write_text("# 訂正稿\n別人的成品。", encoding="utf-8")

    assert cli.main([str(second), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 1
    assert base.read_text(encoding="utf-8") == "# 訂正稿\n既有成品。"
    assert alternate.read_text(encoding="utf-8") == "# 訂正稿\n別人的成品。"
    assert not delivery_manifest_path(alternate).exists()


def test_legacy_directory_pair_is_migrated_to_the_note_owned_paths(tmp_path, monkeypatch):
    """A pre-upgrade note keeps its evidence when a later note delivers."""
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("first source", encoding="utf-8")
    second.write_text("second source", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    monkeypatch.setattr(cli, "TASK_STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(cli, "calculate_polaris_metrics", lambda **kwargs: _Metrics())

    legacy_output = out / "first.訂正稿.md"
    legacy_output.write_text("# 訂正稿\n舊成品。", encoding="utf-8")
    legacy_report = out / "binding_report.json"
    legacy_report.write_text(json.dumps({"schema": "note_filler.binding_report.v2"}), encoding="utf-8")
    legacy_report_text = legacy_report.read_text(encoding="utf-8")
    (out / cli.MANIFEST_NAME).write_text(
        json.dumps(
            {
                "input_path": str(first),
                "output_path": str(legacy_output),
                "status": "delivered",
                "delivery_status": {"primary_note_ready": True, "local_fallback_written": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    assert cli.main([str(second), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 0

    migrated_receipt = delivery_manifest_path(legacy_output)
    migrated_report = binding_report_path(legacy_output)
    assert migrated_receipt.is_file()
    assert json.loads(migrated_receipt.read_text(encoding="utf-8"))["input_path"] == str(first)
    assert json.loads(migrated_receipt.read_text(encoding="utf-8"))["authoritative"] is True
    assert migrated_report.read_text(encoding="utf-8") == legacy_report_text
    # The shared copies now describe the newer note only.
    assert json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))["input_path"] == str(second)
    assert legacy_report.read_text(encoding="utf-8") != legacy_report_text


def test_failed_note_never_borrows_another_notes_report(tmp_path, monkeypatch):
    """A receipt with no report of its own must not read the shared copy."""
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("first source", encoding="utf-8")
    second.write_text("second source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"

    first_output = Path(cli.process_file(first, None, None, None, out, "md", state_dir=state_dir)["output"])
    first_report = binding_report_path(first_output)

    def fail_report(*args, **kwargs):
        raise RuntimeError("synthetic report failure")

    # The output lands, its report never does: the failure receipt then states
    # that this note has no report of its own.
    monkeypatch.setattr(cli, "write_binding_report", fail_report)
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "TASK_STATE_DIR", state_dir)
    assert cli.main([str(second), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 1

    second_output = out / "second.訂正稿.md"
    second_receipt = delivery_manifest_path(second_output)
    failed = json.loads(second_receipt.read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert failed["binding_report_content_hash"] == ""
    assert second_output.is_file()
    assert not binding_report_path(second_output).exists()

    # The shared report copy still holds the first note's report; the failed
    # note must resolve metrics as unavailable instead of borrowing it.
    assert (out / "binding_report.json").read_text(encoding="utf-8") == first_report.read_text(
        encoding="utf-8"
    )
    status, *_ = _load_output_metrics(
        second_output, hashlib.sha256(second_output.read_bytes()).hexdigest()
    )
    assert status == "metrics_unavailable"
    record, alerts = rerun_note(second_receipt, MetricsCollectionConfig(scan_dirs=[out]))
    assert record is None
    assert any(alert.alert_type == "rerun_failure" for alert in alerts)


def test_relative_input_uses_persisted_absolute_identity_after_cwd_change(tmp_path, monkeypatch):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    (first_dir / "notes").mkdir(parents=True)
    second_dir.mkdir()
    note = first_dir / "notes" / "note.txt"
    note.write_text("source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"

    monkeypatch.chdir(first_dir)
    first_result = cli.process_file(Path("notes/note.txt"), None, None, None, out, "md", state_dir=state_dir)
    first_output = Path(first_result["output"])
    first_receipt = json.loads(delivery_manifest_path(first_output).read_text(encoding="utf-8"))
    assert first_receipt["input_canonical_path"] == str(note.resolve())
    assert first_receipt["output_canonical_path"] == str(first_output.resolve())

    monkeypatch.chdir(second_dir)
    second_result = cli.process_file(Path("../first/notes/note.txt"), None, None, None, out, "md", state_dir=state_dir)
    assert Path(second_result["output"]) == first_output
    assert len(list(out.glob("*.訂正稿.md"))) == 1
    owned = delivery_manifest_path(first_output)
    expected_id = derive_note_id(str(note.resolve()))
    collected = collect_metrics_from_manifest(owned, MetricsCollectionConfig(scan_dirs=[out]))
    assert collected is not None and collected.note_id == expected_id
    rerun_record, alerts = rerun_note(owned, MetricsCollectionConfig(scan_dirs=[out]))
    assert rerun_record is not None and rerun_record.note_id == expected_id
    assert not any(alert.alert_type == "rerun_failure" for alert in alerts)


def test_recovery_uses_canonical_artifact_paths_after_cwd_change(tmp_path, monkeypatch):
    origin = tmp_path / "origin"
    origin.mkdir()
    note = origin / "note.txt"
    note.write_text("source", encoding="utf-8")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    monkeypatch.chdir(origin)
    result = cli.process_file(
        Path("note.txt"), None, None, None, Path("out"), "md", state_dir=tmp_path / "state"
    )
    owned = delivery_manifest_path(origin / result["output"])
    before = owned.read_bytes()
    data = json.loads(before)
    assert data["input_path"] == "note.txt"
    assert not Path(data["output_path"]).is_absolute()
    assert not Path(data["binding_report_path"]).is_absolute()

    monkeypatch.chdir(tmp_path)
    verdict = recover_delivery(owned)
    assert verdict.verified is True
    assert verdict.status == "verified"
    assert all(probe.code is None for probe in verdict.probes)
    assert owned.read_bytes() == before


def test_recovery_via_latest_manifest_updates_authoritative_receipt(tmp_path, monkeypatch):
    note = tmp_path / "note.txt"
    note.write_text("source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    result = cli.process_file(note, None, None, None, out, "md", state_dir=tmp_path / "state")
    output = Path(result["output"])
    owned = delivery_manifest_path(output)
    latest = out / cli.MANIFEST_NAME
    output.unlink()

    verdict = recover_delivery(latest)
    assert verdict.status == "retryable"
    assert any(error["code"] == "artifact_missing" for error in verdict.errors)
    owned_data = json.loads(owned.read_text(encoding="utf-8"))
    assert owned_data["status"] == "retryable"
    assert owned_data["recovery_attempts"]
    latest_now = json.loads(latest.read_text(encoding="utf-8"))
    assert latest_now["authoritative"] is False
    for key in ("authoritative", "sidecar_scope", "sidecar_for_output"):
        latest_now.pop(key, None)
        owned_data.pop(key, None)
    assert latest_now == owned_data


def test_legacy_only_receipt_updated_in_place_is_marked_non_authoritative(tmp_path):
    """A directory-level receipt with no owned pair stays marked non-authoritative."""
    legacy = tmp_path / "delivery_manifest.json"
    legacy.write_text(
        json.dumps(
            {
                "input_path": "in.txt",
                "output_path": str(tmp_path / "out.md"),
                "status": "delivered",
                "delivery_status": {
                    "primary_note_ready": True,
                    "user_channel_sent": False,
                    "local_fallback_written": True,
                },
            }
        ),
        encoding="utf-8",
    )

    recover_delivery(legacy)

    data = json.loads(legacy.read_text(encoding="utf-8"))
    assert data["authoritative"] is False
    assert data["sidecar_scope"] == "directory_latest"
    assert data["sidecar_for_output"] == str(tmp_path / "out.md")


def test_recovery_history_keeps_same_failure_for_each_note(tmp_path, monkeypatch):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "note.txt"
    second = second_dir / "note.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"
    first_output = Path(cli.process_file(first, None, None, None, out, "md", state_dir=state_dir)["output"])
    second_output = Path(cli.process_file(second, None, None, None, out, "md", state_dir=state_dir)["output"])
    first_receipt = delivery_manifest_path(first_output)
    second_receipt = delivery_manifest_path(second_output)
    first_output.unlink()
    second_output.unlink()

    assert recover_delivery(first_receipt).status == "retryable"
    assert recover_delivery(second_receipt).status == "retryable"
    assert recover_delivery(first_receipt).status == "retryable"
    attempts = [json.loads(line) for line in (out / "recovery_history.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {entry["note_manifest_path"] for entry in attempts} == {
        str(first_receipt.resolve()), str(second_receipt.resolve())
    }
    assert len(attempts) == 2
    for receipt in (first_receipt, second_receipt):
        data = json.loads(receipt.read_text(encoding="utf-8"))
        assert data["status"] == "retryable"
        assert len(data["recovery_attempts"]) == 1
        assert data["recovery_attempts"][0]["note_manifest_path"] == str(receipt.resolve())


def test_recovery_history_distinguishes_reused_receipt_path(tmp_path, monkeypatch):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "note.txt"
    second = second_dir / "note.txt"
    first.write_text("first source", encoding="utf-8")
    second.write_text("second source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"

    first_output = Path(cli.process_file(first, None, None, None, out, "md", state_dir=state_dir)["output"])
    first_receipt = delivery_manifest_path(first_output)
    first_report = binding_report_path(first_output)
    first_output.unlink()
    assert recover_delivery(first_receipt).status == "retryable"
    first_receipt.unlink()
    first_report.unlink()

    second_output = Path(cli.process_file(second, None, None, None, out, "md", state_dir=state_dir)["output"])
    assert second_output == first_output
    second_output.unlink()
    assert recover_delivery(delivery_manifest_path(second_output)).status == "retryable"

    history = [json.loads(line) for line in (out / "recovery_history.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(history) == 2
    assert {entry["note_manifest_path"] for entry in history} == {str(first_receipt.resolve())}
    assert {entry["note_source_path"] for entry in history} == {str(first.resolve()), str(second.resolve())}
    assert len({entry["note_source_hash"] for entry in history}) == 2


def test_failed_second_note_does_not_replace_first_note_receipt(tmp_path, monkeypatch):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("first source", encoding="utf-8")
    second.write_text("second source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    monkeypatch.setattr(cli, "TASK_STATE_DIR", tmp_path / "state")

    def pipeline(path, *args):
        if Path(path) == second:
            raise RuntimeError("synthetic B failure")
        return _FakeDoc()

    monkeypatch.setattr(cli, "run_pipeline", pipeline)
    assert cli.main([str(first), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 0
    first_receipt = delivery_manifest_path(out / "first.訂正稿.md")
    first_bytes = first_receipt.read_bytes()
    assert cli.main([str(second), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 1
    assert first_receipt.read_bytes() == first_bytes
    failed = json.loads(delivery_manifest_path(out / "second.訂正稿.md").read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert failed["input_path"] == str(second)


def test_post_write_failure_uses_second_notes_actual_output(tmp_path, monkeypatch):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "note.txt"
    second = second_dir / "note.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "TASK_STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")

    args = ["--outdir", str(out), "--db", str(tmp_path / "missing.db")]
    assert cli.main([str(first), *args]) == 0
    first_output = out / "note.訂正稿.md"
    first_receipt = delivery_manifest_path(first_output)
    first_bytes = first_receipt.read_bytes()

    def fail_after_output(*args, **kwargs):
        raise RuntimeError("synthetic report failure")

    monkeypatch.setattr(cli, "write_binding_report", fail_after_output)
    assert cli.main([str(second), *args]) == 1
    second_output = cli._output_for_input(second, out, "md")
    assert second_output != first_output and second_output.is_file()
    failed = json.loads(delivery_manifest_path(second_output).read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert failed["output_path"] == str(second_output)
    assert first_receipt.read_bytes() == first_bytes


def test_failed_rerun_keeps_the_notes_delivery_record(tmp_path, monkeypatch):
    """A failed re-run must not erase the note's own delivery evidence."""
    note = tmp_path / "note.txt"
    note.write_text("source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"
    result = cli.process_file(note, None, None, None, out, "md", state_dir=state_dir)
    output = Path(result["output"])
    owned = delivery_manifest_path(output)
    delivered = json.loads(owned.read_text(encoding="utf-8"))
    assert delivered["status"] == "delivered"
    assert delivered["polaris_metrics"]
    assert delivered["binding_report_content_hash"]

    monkeypatch.setattr(
        cli,
        "run_pipeline",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("transient outage")),
    )
    assert cli.main([str(note), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 1

    failed = json.loads(owned.read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    # A failure must not advertise the earlier delivery's metrics.
    assert "polaris_metrics" not in failed
    assert failed["binding_report_content_hash"] == delivered["binding_report_content_hash"]
    assert failed["previous_receipt_archive"] == f"{owned.name}.prev"
    archive = out / f"{owned.name}.prev"
    assert json.loads(archive.read_text(encoding="utf-8"))["status"] == "delivered"
    # The note's own report is still bound, so its metrics stay resolvable.
    status, *_ = _load_output_metrics(
        output, hashlib.sha256(output.read_bytes()).hexdigest()
    )
    assert status == "calculated"


def test_failed_rerun_keeps_recorded_recovery_history(tmp_path, monkeypatch):
    """Recovery history in the receipt survives a later failed attempt."""
    note = tmp_path / "note.txt"
    note.write_text("source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"
    result = cli.process_file(note, None, None, None, out, "md", state_dir=state_dir)
    output = Path(result["output"])
    owned = delivery_manifest_path(output)

    note.unlink()
    assert recover_delivery(owned).status == "retryable"
    recovering = json.loads(owned.read_text(encoding="utf-8"))
    assert recovering["status"] == "retryable"
    assert len(recovering["recovery_attempts"]) == 1

    note.write_text("source", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "run_pipeline",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("transient outage")),
    )
    assert cli.main([str(note), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 1

    failed = json.loads(owned.read_text(encoding="utf-8"))
    assert failed["status"] == "failed"
    assert failed["recovery_attempts"] == recovering["recovery_attempts"]
    assert failed["recovered_at"] == recovering["recovered_at"]


def test_bare_relative_legacy_input_cannot_claim_another_notes_output(tmp_path, monkeypatch):
    """A copy recorded from another cwd never hands its name to this note."""
    first = tmp_path / "case.txt"
    second_dir = tmp_path / "notes"
    second_dir.mkdir()
    second = second_dir / "case.txt"
    first.write_text("note A", encoding="utf-8")
    second.write_text("note B", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "case.訂正稿.md").write_text("# 訂正稿\nA 的成品。", encoding="utf-8")
    (out / cli.MANIFEST_NAME).write_text(
        json.dumps(
            {
                "input_path": "case.txt",
                "output_path": "out/case.訂正稿.md",
                "status": "delivered",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\nB 的成品。")
    monkeypatch.setattr(cli, "TASK_STATE_DIR", tmp_path / "state")

    assert cli.main([str(second), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 0
    assert (out / "case.訂正稿.md").read_text(encoding="utf-8") == "# 訂正稿\nA 的成品。"
    second_output = cli._output_for_input(second, out, "md")
    assert second_output.name != "case.訂正稿.md"
    # Note A keeps its own receipt, promoted from the shared copy untouched.
    a_receipt = json.loads(
        delivery_manifest_path(out / "case.訂正稿.md").read_text(encoding="utf-8")
    )
    assert a_receipt["input_path"] == "case.txt"
    assert a_receipt["status"] == "delivered"


def test_receipt_copied_onto_another_note_is_rejected(tmp_path, monkeypatch):
    """A cloned receipt must not pass as another note's evidence."""
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "note.txt"
    second = second_dir / "note.txt"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    state_dir = tmp_path / "state"
    first_output = Path(cli.process_file(first, None, None, None, out, "md", state_dir=state_dir)["output"])
    second_output = Path(cli.process_file(second, None, None, None, out, "md", state_dir=state_dir)["output"])

    clone = delivery_manifest_path(second_output)
    clone.write_bytes(delivery_manifest_path(first_output).read_bytes())

    verdict = recover_delivery(clone)
    assert verdict.verified is False
    status, *_ = _load_output_metrics(
        second_output, hashlib.sha256(second_output.read_bytes()).hexdigest()
    )
    assert status == "metrics_unavailable"


def test_moved_output_directory_keeps_resolving_its_note(tmp_path, monkeypatch):
    """Archiving the output directory must not break the note's metrics."""
    note = tmp_path / "note.txt"
    note.write_text("source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    result = cli.process_file(note, None, None, None, out, "md", state_dir=tmp_path / "state")
    output = Path(result["output"])

    archive = tmp_path / "archive" / "2026"
    archive.parent.mkdir()
    out.rename(archive)
    moved_output = archive / output.name

    content_hash = hashlib.sha256(moved_output.read_bytes()).hexdigest()
    status, *_ = _load_output_metrics(moved_output, content_hash)
    assert status == "calculated"
    verdict = recover_delivery(delivery_manifest_path(moved_output))
    assert verdict.verified is True
    assert all(probe.code is None for probe in verdict.probes)


def test_stale_copy_of_a_deleted_output_is_not_promoted(tmp_path, monkeypatch):
    """A copy whose output is gone must not become authoritative evidence."""
    first = tmp_path / "first.txt"
    first.write_text("first source", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / cli.MANIFEST_NAME).write_text(
        json.dumps(
            {"input_path": str(first), "output_path": str(out / "ghost.訂正稿.md"), "status": "delivered"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    monkeypatch.setattr(cli, "TASK_STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(cli, "calculate_polaris_metrics", lambda **kwargs: _Metrics())

    assert cli.main([str(first), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 0
    assert not (out / "ghost.訂正稿.md.delivery_manifest.json").exists()
    assert (out / "first.訂正稿.md.delivery_manifest.json").is_file()


def test_latest_copy_of_another_note_is_left_untouched(tmp_path):
    """Recovering note A must not repoint the copy that names note B."""
    from note_filler.sidecars import (
        delivery_manifest_path as owned_receipt_path,
        write_manifest_and_latest,
    )

    out = tmp_path / "out"
    out.mkdir()
    a_output = out / "a.訂正稿.md"
    b_output = out / "b.訂正稿.md"
    b_receipt = {
        "output_path": str(b_output),
        "input_path": str(tmp_path / "b.txt"),
        "status": "delivered",
        "polaris_metrics": {"schema": "note_filler.polaris_metrics.v1"},
    }
    (out / cli.MANIFEST_NAME).write_text(json.dumps(b_receipt), encoding="utf-8")

    a_receipt = dict(b_receipt, output_path=str(a_output), input_path=str(tmp_path / "a.txt"))
    write_manifest_and_latest(owned_receipt_path(a_output), a_receipt)

    copy = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert copy["input_path"] == str(tmp_path / "b.txt")
    assert copy["output_path"] == str(b_output)
    assert copy["status"] == "delivered"


def test_unreadable_latest_copy_is_preserved(tmp_path):
    """A corrupt copy is reported and kept, never overwritten blindly."""
    from note_filler.sidecars import (
        delivery_manifest_path as owned_receipt_path,
        may_write_latest_copy,
    )

    out = tmp_path / "out"
    out.mkdir()
    (out / cli.MANIFEST_NAME).write_text("{not json", encoding="utf-8")
    receipt = {
        "output_path": str(out / "note.訂正稿.md"),
        "input_path": str(tmp_path / "note.txt"),
        "status": "failed",
    }
    assert may_write_latest_copy(out / cli.MANIFEST_NAME, receipt) is False
    assert (out / cli.MANIFEST_NAME).read_text(encoding="utf-8") == "{not json"
    assert owned_receipt_path(out / "note.訂正稿.md").name.endswith(
        ".delivery_manifest.json"
    )


def test_legacy_relative_input_path_keeps_its_output_name(tmp_path, monkeypatch):
    """A legacy receipt recorded from the output directory still owns its name."""
    notes = tmp_path / "notes"
    notes.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    note = notes / "note.txt"
    note.write_text("source", encoding="utf-8")
    (out / "note.訂正稿.md").write_text("# 訂正稿\n舊成品。", encoding="utf-8")
    (out / cli.MANIFEST_NAME).write_text(
        json.dumps(
            {
                "input_path": "../notes/note.txt",
                "output_path": "note.訂正稿.md",
                "status": "delivered",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda **kwargs: None)
    monkeypatch.setattr(cli, "LawLookup", lambda path: None)
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    monkeypatch.setattr(cli, "TASK_STATE_DIR", tmp_path / "state")

    assert cli.main([str(note), "--outdir", str(out), "--db", str(tmp_path / "missing.db")]) == 0
    assert sorted(p.name for p in out.glob("*.訂正稿.md")) == ["note.訂正稿.md"]
    assert (out / "note.訂正稿.md.delivery_manifest.json").is_file()
