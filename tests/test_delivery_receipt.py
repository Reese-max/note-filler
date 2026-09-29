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
from note_filler.sidecars import binding_report_path, delivery_manifest_path


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


def test_rerun_via_latest_manifest_updates_authoritative_receipt(tmp_path, monkeypatch):
    note = tmp_path / "note.txt"
    note.write_text("source", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakeDoc())
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n完整內容。")
    result = cli.process_file(note, None, None, None, out, "md", state_dir=tmp_path / "state")
    owned = delivery_manifest_path(Path(result["output"]))
    latest = out / cli.MANIFEST_NAME
    latest_data = json.loads(latest.read_text(encoding="utf-8"))
    assert latest_data["delivery_status"]["user_channel_sent"] is False
    latest_data["delivery_status"]["user_channel_sent"] = True
    latest_data["transmission_confirmation_hash"] = hashlib.sha256(
        json.dumps(
            latest_data["delivery_status"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    latest.write_text(json.dumps(latest_data, ensure_ascii=False, indent=2), encoding="utf-8")

    record, alerts = rerun_note(latest, MetricsCollectionConfig(scan_dirs=[out]))
    assert record is not None
    assert not any(alert.alert_type == "rerun_failure" for alert in alerts)
    assert Path(record.manifest_path) == owned
    owned_data = json.loads(owned.read_text(encoding="utf-8"))
    assert owned_data["metrics_rerun_at"]
    assert owned_data["delivery_status"]["user_channel_sent"] is True
    assert owned_data["polaris_metrics"]["delivery_success_rate"]["score"] == 1.0
    assert json.loads(latest.read_text(encoding="utf-8")) == owned_data


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
    assert json.loads(latest.read_text(encoding="utf-8")) == owned_data


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
