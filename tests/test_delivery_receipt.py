"""交付回執(delivery receipt)測試。

驗證 digest 除了落盤外,還有明確的對外送達紀錄——
可查詢的 delivery_manifest.json 作為交付回執,
不可只靠本機檔案存在判定完成。

L035/L036:不可只靠 exit code 或檔案存在判定成功;
必須同時驗證有可讀輸出與明確完成訊號。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from note_filler import __main__ as cli


class _FakeDoc:
    """最小替身:含 2 個 segment,模擬 pipeline 產出。"""
    class _Seg:
        def __init__(self, type_: str, confidence: str = "verified"):
            self.type = type_
            self.confidence = confidence
            self.text = "test text"
            self.sources = []

    segments = [_Seg("original"), _Seg("supplement", "verified"), _Seg("supplement", "pending_evidence")]


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
    required_keys = {"output_path", "input_path", "status", "timestamp", "content_hash"}
    assert required_keys.issubset(manifest.keys()), (
        f"manifest 缺少必要欄位: {required_keys - manifest.keys()}"
    )
    assert manifest["status"] == "delivered", (
        f"成功交付的 manifest status 必須為 'delivered'，實際: {manifest['status']}"
    )
    assert manifest["output_path"] == r["output"]
    assert manifest["input_path"] == str(note)
    assert manifest["content_hash"], "content_hash 不可為空"


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
