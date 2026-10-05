"""正式恢復入口：續跑前驗證已持久化 artifact 的存在性與內容雜湊。

已持久化的生成成品（輸出訂正稿）、來源 artifact（輸入筆記）與傳輸確認資訊
（delivery_status）在交付時都保存內容雜湊；正式恢復入口在續跑前必須驗證
定位的檔案仍存在且雜湊一致：

- 全部一致 → verified，可安全續跑。
- 任一不一致 → 保留既有歷程（recovery_history.jsonl 與 manifest 的
  recovery_attempts），將狀態轉為帶 ``artifact_missing`` 或
  ``artifact_integrity_mismatch`` 錯誤的失敗或可重試狀態，
  絕不在此宣告交付完成。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .sidecars import (
    DELIVERY_MANIFEST_NAME,
    is_receipt_file_name,
    receipt_conflicts_with_note,
    receipt_input_identity,
    receipt_output_identity,
    resolve_delivery_manifest_path,
    resolve_manifest_for_update,
    write_manifest_and_latest,
)

logger = logging.getLogger(__name__)

ARTIFACT_MISSING = "artifact_missing"
ARTIFACT_INTEGRITY_MISMATCH = "artifact_integrity_mismatch"

RECOVERY_HISTORY_NAME = "recovery_history.jsonl"


def sha256_bytes(data: bytes) -> str:
    """全長 sha256 hex。"""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    """檔案的全長 sha256；不存在或不可讀時回傳 None。"""
    try:
        return sha256_bytes(Path(path).read_bytes())
    except OSError:
        return None


def _hashes_match(expected: str | None, actual: str | None) -> bool:
    """比較預期與實際雜湊；預期為截斷值（如舊 content_hash 前 16 碼）時比前綴。"""
    if not expected:
        return True
    if not actual:
        return False
    if len(expected) >= 64:
        return actual == expected
    return actual[: len(expected)] == expected


@dataclass
class ArtifactProbe:
    """單一 artifact 的存在性與內容雜湊探測結果。"""

    kind: str
    path: str
    exists: bool
    expected_hash: str | None
    actual_hash: str | None
    code: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "exists": self.exists,
            "expected_hash": self.expected_hash,
            "actual_hash": self.actual_hash,
            "code": self.code,
        }


@dataclass
class RecoveryVerdict:
    """正式恢復入口的判定結果。"""

    verified: bool
    status: str
    errors: list[dict[str, Any]]
    probes: list[ArtifactProbe]
    history_preserved: bool
    history_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "status": self.status,
            "errors": self.errors,
            "probes": [p.as_dict() for p in self.probes],
            "history_preserved": self.history_preserved,
            "history_path": self.history_path,
        }


def probe_artifact(kind: str, path: str, expected_hash: str | None) -> ArtifactProbe:
    """探測單一檔案：是否存在，且（有基準雜湊時）內容是否一致。"""
    target = Path(path)
    exists = target.is_file()
    actual = sha256_file(target) if exists else None
    if not exists:
        code = ARTIFACT_MISSING
    elif not _hashes_match(expected_hash, actual):
        code = ARTIFACT_INTEGRITY_MISMATCH
    else:
        code = None
    return ArtifactProbe(kind, str(target), exists, expected_hash, actual, code)


def _probe_error(probe: ArtifactProbe) -> dict[str, Any]:
    message = (
        "已定位的檔案不存在"
        if probe.code == ARTIFACT_MISSING
        else "已定位的檔案內容雜湊不一致"
    )
    return {
        "kind": probe.kind,
        "path": probe.path,
        "code": probe.code,
        "message": message,
    }


def _transmission_probe(
    manifest: dict[str, Any],
    manifest_path: Path | None,
) -> ArtifactProbe:
    """傳輸確認資訊以 manifest 內 delivery_status 為內容、manifest 自身為錨檔。"""
    delivery_status = manifest.get("delivery_status")
    expected_hash = manifest.get("transmission_confirmation_hash")
    anchor = manifest_path
    if anchor is None:
        output_path = manifest.get("output_path")
        anchor = (
            resolve_delivery_manifest_path(Path(output_path))
            if isinstance(output_path, str) and output_path
            else Path.cwd() / DELIVERY_MANIFEST_NAME
        )
    exists = anchor.is_file()
    if not exists:
        return ArtifactProbe(
            "transmission_confirmation",
            str(anchor),
            exists=False,
            expected_hash=expected_hash,
            actual_hash=None,
            code=ARTIFACT_MISSING,
        )
    payload = json.dumps(
        delivery_status,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    actual = sha256_bytes(payload.encode("utf-8"))
    code = None
    if not _hashes_match(expected_hash, actual):
        code = ARTIFACT_INTEGRITY_MISMATCH
    return ArtifactProbe(
        "transmission_confirmation",
        str(anchor),
        exists=True,
        expected_hash=expected_hash,
        actual_hash=actual,
        code=code,
    )


def _probe_bound_artifact(
    kind: str,
    recorded_path: str,
    manifest_path: Path | None,
    expected_hash: str | None,
) -> ArtifactProbe:
    """探測回執記錄的 artifact，允許整批輸出被搬移或封存。

    回執與其成品一起移動時，記錄的絕對路徑會失效；此時改探測回執同目錄下
    同名的檔案（成品與綁定報告就在回執旁邊，來源筆記不在），且記錄的內容雜湊
    必須存在並一致，因此搬移不會被誤判為竄改，無雜湊則一律照實回報遺失。
    """
    probe = probe_artifact(kind, recorded_path, expected_hash)
    if probe.exists or manifest_path is None or kind == "source" or not expected_hash:
        return probe
    sibling = Path(manifest_path).parent / Path(recorded_path).name
    if sibling == Path(recorded_path):
        return probe
    return probe_artifact(kind, sibling, expected_hash)


def verify_delivery_artifacts(
    manifest: dict[str, Any],
    manifest_path: Path | None = None,
) -> list[ArtifactProbe]:
    """依已持久化 manifest 定位並探測全部 artifact。"""
    probes: list[ArtifactProbe] = []

    output_path = receipt_output_identity(manifest)
    if manifest_path is not None and receipt_conflicts_with_note(manifest, manifest_path):
        # The receipt is filed under one note but records another note's output,
        # so it is not evidence for the note it was opened as.
        probes.append(
            ArtifactProbe(
                "delivery_manifest",
                str(manifest_path),
                exists=True,
                expected_hash=None,
                actual_hash=None,
                code=ARTIFACT_INTEGRITY_MISMATCH,
            )
        )
        return probes
    if isinstance(output_path, str) and output_path:
        expected = manifest.get("output_content_hash") or manifest.get("content_hash")
        probes.append(
            _probe_bound_artifact("generated", output_path, manifest_path, expected)
        )

    input_path = receipt_input_identity(manifest)
    if isinstance(input_path, str) and input_path:
        probes.append(
            _probe_bound_artifact(
                "source", input_path, manifest_path, manifest.get("input_content_hash")
            )
        )

    report_path = manifest.get("binding_report_canonical_path") or manifest.get("binding_report_path")
    report_hash = manifest.get("binding_report_content_hash")
    if isinstance(report_path, str) and report_path and report_hash:
        probes.append(
            _probe_bound_artifact("binding_report", report_path, manifest_path, report_hash)
        )

    if manifest.get("delivery_status") is not None:
        probes.append(_transmission_probe(manifest, manifest_path))

    return probes


def _append_history(history_path: Path, attempt: dict[str, Any]) -> None:
    """以檔案鎖追加單筆恢復嘗試，既有歷程絕不覆寫。

    同一筆記內重複的失敗特徵（errors 的 kind+code 集合、目標狀態與筆記身分）
    不重複追加，避免並行 resume 重複落盤；跨筆記的相同失敗各自留痕。
    """
    history_path.parent.mkdir(parents=True, exist_ok=True)
    signature = _attempt_signature(attempt)
    with history_path.open("a+", encoding="utf-8", newline="") as history:
        history.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(history.fileno(), msvcrt.LK_LOCK, 1)
            try:
                return _write_lock_unless_duplicate(history, signature, attempt)
            finally:
                history.seek(0)
                msvcrt.locking(history.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(history.fileno(), fcntl.LOCK_EX)
            try:
                return _write_lock_unless_duplicate(history, signature, attempt)
            finally:
                fcntl.flock(history.fileno(), fcntl.LOCK_UN)


def _attempt_signature(attempt: dict[str, Any]) -> frozenset[tuple[str, str | None]]:
    """Deduplicate a failure only within its own note receipt.

    不含 status_before，避免並行 resume 讀到前次寫入的狀態造成重複記錄；
    含 status_after，讓 failed→retryable 等不同目標狀態視為不同嘗試。
    """
    errors = attempt.get("errors") or []
    codes = frozenset(
        {(e.get("kind"), e.get("code")) for e in errors if isinstance(e, dict)}
    )
    return frozenset({
        ("note_manifest_path", attempt.get("note_manifest_path")),
        ("note_source_path", attempt.get("note_source_path")),
        ("note_source_hash", attempt.get("note_source_hash")),
        ("status_after", attempt.get("status_after")),
        ("errors", ",".join(sorted(f"{a}|{b}" for a, b in codes))),
    })


def _write_lock_unless_duplicate(
    history, signature: frozenset[tuple[str, str | None]], attempt: dict[str, Any]
) -> bool:
    history.seek(0)
    existing = history.read()
    for line in existing.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(record, dict) and _attempt_signature(record) == signature:
            return False
    history.seek(0, 2)
    history.write(json.dumps(attempt, ensure_ascii=False, sort_keys=True) + "\n")
    return True


def recover_delivery(
    manifest_path: Path | str,
    *,
    force_status: str | None = None,
) -> RecoveryVerdict:
    """正式恢復入口：續跑前驗證已持久化 artifact。

    - manifest 不存在或損壞 → 以 ``artifact_missing``／``artifact_integrity_mismatch``
      轉為失敗狀態，保留既有歷程。
    - 定位的生成成品／來源／傳輸確認都存在且雜湊一致 → ``verified``，不改寫狀態。
    - 任一不一致 → 追加恢復嘗試至 recovery_history.jsonl 與 manifest
      recovery_attempts（既有歷程保留），狀態轉為 ``failed``／``retryable``，
      錯誤帶 ``artifact_missing``／``artifact_integrity_mismatch``。

    此入口絕不將狀態宣告為 ``delivered``。
    """
    requested_path = Path(manifest_path)
    manifest_path = resolve_manifest_for_update(requested_path)
    # A latest-only path is routed to its authoritative note receipt, and that
    # receipt is what gets read and updated: a stale or hand-edited copy must
    # never revert the recorded recovery state of its note.
    if not manifest_path.is_file():
        return RecoveryVerdict(
            verified=False,
            status="failed",
            errors=[{
                "kind": "delivery_manifest",
                "path": str(manifest_path),
                "code": ARTIFACT_MISSING,
                "message": "交付狀態檔不存在，無法驗證已持久化 artifact",
            }],
            probes=[],
            history_preserved=True,
        )

    if not is_receipt_file_name(manifest_path.name):
        # Archives (…delivery_manifest.json.prev) record a past state; rewriting
        # them would destroy the record the archive exists to preserve.
        return RecoveryVerdict(
            verified=False,
            status="failed",
            errors=[{
                "kind": "delivery_manifest",
                "path": str(manifest_path),
                "code": ARTIFACT_INTEGRITY_MISMATCH,
                "message": "不是交付回執檔，拒絕改寫其狀態",
            }],
            probes=[],
            history_preserved=True,
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return RecoveryVerdict(
            verified=False,
            status="failed",
            errors=[{
                "kind": "delivery_manifest",
                "path": str(manifest_path),
                "code": ARTIFACT_INTEGRITY_MISMATCH,
                "message": f"交付狀態檔損壞，無法驗證已持久化 artifact: {exc}",
            }],
            probes=[],
            history_preserved=True,
        )

    if not isinstance(manifest, dict):
        return RecoveryVerdict(
            verified=False,
            status="failed",
            errors=[{
                "kind": "delivery_manifest",
                "path": str(manifest_path),
                "code": ARTIFACT_INTEGRITY_MISMATCH,
                "message": "交付狀態檔非 JSON 物件，無法驗證已持久化 artifact",
            }],
            probes=[],
            history_preserved=True,
        )

    probes = verify_delivery_artifacts(manifest, manifest_path)
    errors = [_probe_error(probe) for probe in probes if probe.code]
    history_path = manifest_path.parent / RECOVERY_HISTORY_NAME

    if not errors:
        return RecoveryVerdict(
            verified=True,
            status="verified",
            errors=[],
            probes=probes,
            history_preserved=True,
            history_path=str(history_path),
        )

    new_status = force_status if force_status in ("failed", "retryable") else "retryable"
    attempt = {
        "note_manifest_path": str(manifest_path.resolve()),
        "note_source_path": receipt_input_identity(manifest),
        "note_source_hash": manifest.get("input_content_hash"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status_before": manifest.get("status"),
        "status_after": new_status,
        "error_before": manifest.get("error"),
        "errors": [dict(e) for e in errors],
    }
    _append_history(history_path, attempt)

    attempts = manifest.get("recovery_attempts")
    if not isinstance(attempts, list):
        attempts = []
    signature = _attempt_signature(attempt)
    if not any(
        isinstance(item, dict) and _attempt_signature(item) == signature
        for item in attempts
    ):
        attempts.append(attempt)
    manifest["recovery_attempts"] = attempts
    manifest["status"] = new_status
    manifest["recovered_at"] = attempt["timestamp"]
    manifest["error"] = "; ".join(
        f"{e['code']}:{e['kind']}:{e['path']}" for e in errors
    )
    write_manifest_and_latest(manifest_path, manifest)

    return RecoveryVerdict(
        verified=False,
        status=new_status,
        errors=[dict(e) for e in errors],
        probes=probes,
        history_preserved=True,
        history_path=str(history_path),
    )
