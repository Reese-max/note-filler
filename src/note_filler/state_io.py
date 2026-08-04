"""任務狀態檔案的原子寫入與損毀偵測。"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

MANIFEST_REQUIRED_FIELDS = frozenset(
    {
        "output_path",
        "input_path",
        "status",
        "timestamp",
        "content_hash",
        "format",
        "supplements",
        "verified",
        "delivery_status",
    }
)


class ManifestCorruptionError(Exception):
    """manifest 檔案損毀或格式錯誤。"""

    def __init__(self, path: Path, reason: str, error_code: str) -> None:
        self.path = path
        self.reason = reason
        self.error_code = error_code
        super().__init__(f"[{error_code}] {path}: {reason}")


def write_manifest_atomic(path: Path, data: dict[str, Any]) -> Path:
    """以原子寫入儲存 manifest：tmp + fsync + os.replace。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f"{path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_path)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    return path


def read_manifest_safe(path: Path) -> dict[str, Any]:
    """安全讀取 manifest，偵測截斷/解析失敗/schema 不合法。

    失敗時保留原始檔案，raise ManifestCorruptionError。
    """
    path = Path(path)
    if not path.exists():
        raise ManifestCorruptionError(
            path, "manifest 檔案不存在", "manifest_missing"
        )

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestCorruptionError(
            path, f"讀取失敗: {exc}", "manifest_read_os_error"
        ) from exc

    if not raw.strip():
        raise ManifestCorruptionError(
            path, "manifest 檔案為空", "manifest_empty"
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ManifestCorruptionError(
            path, f"JSON 解析失敗(可能截斷): {exc}", "manifest_json_corrupt"
        ) from exc

    if not isinstance(data, dict):
        raise ManifestCorruptionError(
            path, "manifest 根不是 JSON object", "manifest_schema_invalid"
        )

    missing = MANIFEST_REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise ManifestCorruptionError(
            path,
            f"manifest 缺少必要欄位: {sorted(missing)}",
            "manifest_schema_invalid",
        )

    status = data.get("status")
    if not isinstance(status, str) or not status.strip():
        raise ManifestCorruptionError(
            path, "manifest status 為空白或非字串", "manifest_status_invalid"
        )

    return data
