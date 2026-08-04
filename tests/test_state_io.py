"""任務狀態檔案的原子寫入與損毀偵測測試。"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from note_filler.state_io import (
    MANIFEST_REQUIRED_FIELDS,
    ManifestCorruptionError,
    read_manifest_safe,
    write_manifest_atomic,
)


def _minimal_manifest(path: Path) -> dict:
    return {
        "output_path": str(path),
        "input_path": str(path),
        "status": "delivered",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "content_hash": "abcd1234",
        "format": "md",
        "supplements": 1,
        "verified": 1,
        "delivery_status": {
            "primary_note_ready": True,
            "user_channel_sent": False,
            "local_fallback_written": True,
        },
    }


# ---- 原子寫入 ----


def test_write_manifest_atomic_creates_valid_file(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    data = _minimal_manifest(target)
    result = write_manifest_atomic(target, data)
    assert result == target
    assert target.exists()
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == data


def test_write_manifest_atomic_replaces_existing(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    target.write_text("old content", encoding="utf-8")
    data = _minimal_manifest(target)
    write_manifest_atomic(target, data)
    assert target.exists()
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == data


def test_write_manifest_atomic_creates_parent_dirs(tmp_path):
    target = tmp_path / "a" / "b" / "delivery_manifest.json"
    data = _minimal_manifest(target)
    write_manifest_atomic(target, data)
    assert target.exists()
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == data


def test_write_manifest_atomic_no_tmp_left_on_success(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    data = _minimal_manifest(target)
    write_manifest_atomic(target, data)
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert not tmp_files


def test_write_manifest_atomic_cleans_tmp_on_failure(tmp_path, monkeypatch):
    target = tmp_path / "delivery_manifest.json"

    def _boom_replace(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", _boom_replace)
    with pytest.raises(OSError, match="disk full"):
        write_manifest_atomic(target, _minimal_manifest(target))
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert not tmp_files


# ---- 安全讀取 ----


def test_read_manifest_safe_valid(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    data = _minimal_manifest(target)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    loaded = read_manifest_safe(target)
    assert loaded == data


def test_read_manifest_safe_truncated_json(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    target.write_text('{"output_path": "x", "input_path": "x", "status": ', encoding="utf-8")
    with pytest.raises(ManifestCorruptionError) as exc_info:
        read_manifest_safe(target)
    assert exc_info.value.error_code == "manifest_json_corrupt"
    assert exc_info.value.path == target
    assert target.exists()
    assert target.read_text(encoding="utf-8") == '{"output_path": "x", "input_path": "x", "status": '


def test_read_manifest_safe_invalid_json(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    target.write_text("NOT JSON{{", encoding="utf-8")
    with pytest.raises(ManifestCorruptionError) as exc_info:
        read_manifest_safe(target)
    assert exc_info.value.error_code == "manifest_json_corrupt"
    assert target.exists()


def test_read_manifest_safe_missing_fields(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    target.write_text('{"output_path": "x"}', encoding="utf-8")
    with pytest.raises(ManifestCorruptionError) as exc_info:
        read_manifest_safe(target)
    assert exc_info.value.error_code == "manifest_schema_invalid"
    assert "缺少必要欄位" in exc_info.value.reason
    assert target.exists()


def test_read_manifest_safe_not_dict(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    target.write_text('["a", "b"]', encoding="utf-8")
    with pytest.raises(ManifestCorruptionError) as exc_info:
        read_manifest_safe(target)
    assert exc_info.value.error_code == "manifest_schema_invalid"
    assert "根不是 JSON object" in exc_info.value.reason


def test_read_manifest_safe_blank_status(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    data = _minimal_manifest(target)
    data["status"] = ""
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ManifestCorruptionError) as exc_info:
        read_manifest_safe(target)
    assert exc_info.value.error_code == "manifest_status_invalid"
    assert "空白" in exc_info.value.reason or "非字串" in exc_info.value.reason
    assert target.exists()


def test_read_manifest_safe_none_status(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    data = _minimal_manifest(target)
    data["status"] = None
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ManifestCorruptionError) as exc_info:
        read_manifest_safe(target)
    assert exc_info.value.error_code == "manifest_status_invalid"
    assert target.exists()


def test_read_manifest_safe_empty_file(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    target.write_text("", encoding="utf-8")
    with pytest.raises(ManifestCorruptionError) as exc_info:
        read_manifest_safe(target)
    assert exc_info.value.error_code == "manifest_empty"
    assert target.exists()


def test_read_manifest_safe_whitespace_only_file(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    target.write_text("   \n\t  \n", encoding="utf-8")
    with pytest.raises(ManifestCorruptionError) as exc_info:
        read_manifest_safe(target)
    assert exc_info.value.error_code == "manifest_empty"
    assert target.exists()


def test_read_manifest_safe_missing_file(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    with pytest.raises(ManifestCorruptionError) as exc_info:
        read_manifest_safe(target)
    assert exc_info.value.error_code == "manifest_missing"


def test_read_manifest_safe_preserves_original_on_corruption(tmp_path):
    target = tmp_path / "delivery_manifest.json"
    original_content = '{"output_path": "x", "input_path": "x", "status": "delivered", "timestamp": "2026-01-01T00:00:00+00:00", "content_hash": "x", "format": "md", "supplements": 0, "verified": 0, "delivery_status": {}}'
    target.write_text(original_content[:-5], encoding="utf-8")
    with pytest.raises(ManifestCorruptionError):
        read_manifest_safe(target)
    assert target.read_text(encoding="utf-8") == original_content[:-5]
