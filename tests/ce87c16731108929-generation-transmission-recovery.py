"""回歸測試：正式恢復入口的 artifact 內容雜湊與存在性驗證。

驗證場景：
1. 已持久化的生成成品、來源 artifact 與傳輸確認資訊保存內容雜湊。
2. 正式恢復入口在續跑前驗證定位檔案仍存在且雜湊一致。
3. 不一致時保留既有歷程、轉為帶 ``artifact_missing``／
   ``artifact_integrity_mismatch`` 錯誤的失敗或可重試狀態，
   且絕不宣告交付完成。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from note_filler import __main__ as cli
from note_filler.recovery import (
    ARTIFACT_INTEGRITY_MISMATCH,
    ARTIFACT_MISSING,
    RECOVERY_HISTORY_NAME,
    recover_delivery,
    verify_delivery_artifacts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _write_manifest(
    tmp_path: Path,
    *,
    body: str = "訂正稿內容[^1]",
    input_body: str = "原稿內容",
    status: str = "delivered",
    delivery_status: dict | None = None,
) -> dict:
    """用正式 write_delivery_receipt 寫出 manifest，並傳回輸出/來源路徑。"""
    source = tmp_path / "note.txt"
    source.write_text(input_body, encoding="utf-8")
    input_path = tmp_path / "out"
    input_path.mkdir(exist_ok=True)
    output = input_path / "note.訂正稿.md"
    output.write_text(body, encoding="utf-8", newline="\n")

    ds = delivery_status or {
        "primary_note_ready": status == "delivered",
        "user_channel_sent": False,
        "local_fallback_written": True,
    }
    cli.write_delivery_receipt(
        output, source,
        status=status,
        content=body,
        fmt="md",
        supplements=1,
        verified=1,
        delivery_status=ds,
    )
    return input_path / cli.MANIFEST_NAME


def _load(manifest_path: Path) -> dict:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# §1 已持久化 artifact 保存內容雜湊與存在性
# ---------------------------------------------------------------------------

class TestPersistArtifactHashes:
    def test_manifest_persists_generated_source_transmission_hashes(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        manifest = _load(manifest_path)

        out = tmp_path / "out" / "note.訂正稿.md"
        src = tmp_path / "note.txt"

        assert manifest["output_content_hash"] == _sha256(out.read_bytes())
        assert manifest["input_content_hash"] == _sha256(src.read_bytes())
        ds = manifest["delivery_status"]
        expected_tx = _sha256(
            json.dumps(ds, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        assert manifest["transmission_confirmation_hash"] == expected_tx

    def test_manifest_content_hash_is_sha256_prefix(self, tmp_path):
        manifest = _load(_write_manifest(tmp_path, body="abc123"))
        assert manifest["content_hash"] == _sha256("abc123")[:16]


# ---------------------------------------------------------------------------
# §2 重新恢復入口：存在且雜湊一致 → verified
# ---------------------------------------------------------------------------

class TestVerifyIntactArtifacts:
    def test_verify_delivery_artifacts_intact(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        manifest = _load(manifest_path)

        probes = verify_delivery_artifacts(manifest, manifest_path)
        codes = [p.code for p in probes if p.code]
        assert codes == [], f"完好 artifact 不應有錯誤: {codes}"
        kinds = {p.kind for p in probes}
        assert {"generated", "source", "transmission_confirmation"} <= kinds

    def test_recover_verified_when_all_intact(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        verdict = recover_delivery(manifest_path)

        assert verdict.verified is True
        assert verdict.status == "verified"
        assert verdict.errors == []
        # 完好時絕不擅自改寫為 delivered 之外狀態，也不新增恢復嘗試
        assert _load(manifest_path)["status"] == "delivered"

    def test_recover_verified_no_state_change(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        before = dict(_load(manifest_path))
        verdict = recover_delivery(manifest_path)
        after = _load(manifest_path)
        assert not verdict.errors
        assert before["status"] == after["status"]
        assert "recovered_at" not in after


# ---------------------------------------------------------------------------
# §3 定位檔案遺失 → artifact_missing，不宣告交付完成
# ---------------------------------------------------------------------------

class TestArtifactMissing:
    def test_missing_generated_artifact(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        (tmp_path / "out" / "note.訂正稿.md").unlink()

        verdict = recover_delivery(manifest_path)

        assert verdict.verified is False
        codes = {e["code"] for e in verdict.errors}
        assert ARTIFACT_MISSING in codes
        assert verdict.status in ("failed", "retryable")
        # 不得宣告交付完成
        assert _load(manifest_path)["status"] != "delivered"

    def test_missing_source_artifact(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        (tmp_path / "note.txt").unlink()

        verdict = recover_delivery(manifest_path)

        assert verdict.verified is False
        assert ARTIFACT_MISSING in {p.code for p in verdict.probes if p.code}
        assert _load(manifest_path)["status"] != "delivered"

    def test_missing_manifest_file(self, tmp_path):
        missing = tmp_path / "nope" / cli.MANIFEST_NAME
        verdict = recover_delivery(missing)

        assert verdict.verified is False
        assert verdict.status == "failed"
        assert verdict.errors[0]["code"] == ARTIFACT_MISSING


# ---------------------------------------------------------------------------
# §4 內容雜湊不一致 → artifact_integrity_mismatch，保留歷史
# ---------------------------------------------------------------------------

class TestArtifactIntegrityMismatch:
    def test_modified_generated_artifact(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        out = tmp_path / "out" / "note.訂正稿.md"
        out.write_text("被竄改的成品內容", encoding="utf-8", newline="\n")

        verdict = recover_delivery(manifest_path)

        assert verdict.verified is False
        assert ARTIFACT_INTEGRITY_MISMATCH in {p.code for p in verdict.probes if p.code}
        manifest = _load(manifest_path)
        assert manifest["status"] != "delivered"
        assert "artifact_integrity_mismatch" in manifest["error"]

    def test_modified_source_artifact(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        (tmp_path / "note.txt").write_text("被竄改來源", encoding="utf-8")

        verdict = recover_delivery(manifest_path)

        assert ARTIFACT_INTEGRITY_MISMATCH in {p.code for p in verdict.probes if p.code}

    def test_modified_transmission_confirmation(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        manifest = _load(manifest_path)
        manifest["delivery_status"]["user_channel_sent"] = True
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        verdict = recover_delivery(manifest_path)

        tx = [p for p in verdict.probes if p.kind == "transmission_confirmation"]
        assert tx and tx[0].code == ARTIFACT_INTEGRITY_MISMATCH

    def test_corrupted_manifest_file(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        manifest_path.write_text("{ not valid json", encoding="utf-8")

        verdict = recover_delivery(manifest_path)

        assert verdict.verified is False
        assert verdict.status == "failed"
        assert verdict.errors[0]["code"] == ARTIFACT_INTEGRITY_MISMATCH


# ---------------------------------------------------------------------------
# §5 歷史保留：恢復嘗試不覆寫既有歷程
# ---------------------------------------------------------------------------

class TestHistoryPreserved:
    def test_recovery_attempts_appended_not_overwritten(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        (tmp_path / "out" / "note.訂正稿.md").unlink()

        first = recover_delivery(manifest_path, force_status="failed")
        second = recover_delivery(manifest_path, force_status="retryable")

        manifest = _load(manifest_path)
        attempts = manifest["recovery_attempts"]
        assert isinstance(attempts, list)
        assert len(attempts) == 2, "兩次恢復嘗試都應保留，不得覆蓋"

        before_before = attempts[0]["status_before"]
        assert before_before == "delivered"

    def test_history_file_appends_distinct_attempts(self, tmp_path):
        manifest_path = _write_manifest(tmp_path)
        (tmp_path / "out" / "note.訂正稿.md").unlink()

        recover_delivery(manifest_path, force_status="failed")
        recover_delivery(manifest_path, force_status="retryable")

        history_path = tmp_path / "out" / RECOVERY_HISTORY_NAME
        lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 2
        for line in lines:
            record = json.loads(line)
            assert "timestamp" in record
            assert record["errors"][0]["code"] == ARTIFACT_MISSING

    def test_history_file_identical_attempt_deduped(self, tmp_path):
        """相同失敗特徵的重複恢復是 no-op，不重複落盤。"""
        manifest_path = _write_manifest(tmp_path)
        (tmp_path / "out" / "note.訂正稿.md").unlink()

        recover_delivery(manifest_path)
        recover_delivery(manifest_path)

        history_path = tmp_path / "out" / RECOVERY_HISTORY_NAME
        lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 1

    def test_failed_attempt_error_before_preserved(self, tmp_path):
        manifest_path = _write_manifest(tmp_path, status="failed", delivery_status={
            "primary_note_ready": False,
            "user_channel_sent": False,
            "local_fallback_written": False,
        })
        # 手動寫入失敗錯誤
        manifest = _load(manifest_path)
        manifest["error"] = "RuntimeError: first crash"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (tmp_path / "out" / "note.訂正稿.md").unlink()

        verdict = recover_delivery(manifest_path)

        rewritten = _load(manifest_path)
        assert "RuntimeError: first crash" in rewritten["recovery_attempts"][0].get("error_before", "")


# ---------------------------------------------------------------------------
# §6 雙重並行 resume：不重複恢復、偽成功
# ---------------------------------------------------------------------------

class TestDualParallelResume:
    def test_parallel_recover_no_duplicate_history(self, tmp_path):
        import threading

        manifest_path = _write_manifest(tmp_path)
        (tmp_path / "out" / "note.訂正稿.md").unlink()

        ready = threading.Event()
        results = []
        errors = []

        def worker():
            try:
                ready.wait(timeout=5)
                results.append(recover_delivery(manifest_path))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        ready.set()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"並行恢復不應有例外: {errors}"
        assert all(r.verified is False for r in results)

        history_path = tmp_path / "out" / RECOVERY_HISTORY_NAME
        lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) <= 1, f"並行恢復不應重複歷程，實際 {len(lines)} 筆"

    def test_parallel_recover_never_marks_delivered(self, tmp_path):
        import threading

        manifest_path = _write_manifest(tmp_path)
        (tmp_path / "out" / "note.訂正稿.md").unlink()

        ready = threading.Event()
        errors = []

        def worker():
            try:
                ready.wait(timeout=5)
                recover_delivery(manifest_path)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        ready.set()
        for t in threads:
            t.join(timeout=10)

        assert not errors
        assert _load(manifest_path)["status"] != "delivered"
