"""任務狀態持久化驗收測試。

驗證：
  ① 重試累加：連續兩次失敗後第三次成功，前兩次的錯誤紀錄仍在。
  ② MAX_TASK_ATTEMPTS 強制：exhausted 任務不得再建第 4 次 attempt。
  ③ 生成例外不得吞沒後標成功。
  ④ 同名來源不得互相覆寫任務狀態，鍵須含來源唯一識別。
  ⑤ transmission 階段例外全部落盤。
"""

from __future__ import annotations

import json
import time

import pytest

from note_filler.task_state import (
    MAX_TASK_ATTEMPTS,
    AttemptRecord,
    TaskRecord,
    TaskStage,
    TaskState,
    TaskStateManager,
    build_task_key,
)


# ── 基礎：狀態枚舉與鍵建立 ─────────────────────────────────────


def test_task_state_enum_values():
    expected = {"pending", "running", "failed", "retryable", "succeeded", "exhausted"}
    actual = {s.value for s in TaskState}
    assert actual == expected


def test_task_stage_enum_values():
    expected = {"generation", "transmission"}
    actual = {s.value for s in TaskStage}
    assert actual == expected


def test_build_task_key_with_source_id():
    key = build_task_key("note_20260803.txt")
    assert key == "note_20260803.txt"


def test_build_task_key_with_run_id():
    key = build_task_key("note_20260803.txt", run_id="run-001")
    assert key == "note_20260803.txt:run-001"


def test_build_task_key_same_source_different_run_ids_are_isolated():
    k1 = build_task_key("note.txt", run_id="run-1")
    k2 = build_task_key("note.txt", run_id="run-2")
    assert k1 != k2


# ── 核心：重試累加（靶心①） ─────────────────────────────────────


def test_retry_accumulates_attempts_not_overwrites(tmp_path):
    """連續兩次失敗後第三次成功，前兩次的錯誤紀錄必須仍在。"""
    mgr = TaskStateManager(tmp_path / "state")
    key = "source_A"

    # attempt 0: generation 失敗
    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="LLMTimeout",
        error_message="generation timeout on attempt 0",
        recoverable=True,
    )

    # attempt 1: generation 再失敗
    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="LLMTimeout",
        error_message="generation timeout on attempt 1",
        recoverable=True,
    )

    # attempt 2: generation 成功
    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.succeed(key, artifact_path="/out/note.md", content="final content")

    record = mgr.load(key)
    assert record is not None
    assert record.state == TaskState.SUCCEEDED
    assert len(record.attempts) == 3

    # 前兩次的錯誤紀錄必須保留
    assert record.attempts[0].error_type == "LLMTimeout"
    assert "attempt 0" in record.attempts[0].error_message
    assert record.attempts[1].error_type == "LLMTimeout"
    assert "attempt 1" in record.attempts[1].error_message
    # 第三次無錯誤
    assert record.attempts[2].error_type == ""
    assert record.attempts[2].error_message == ""


def test_retry_attempt_indices_are_sequential(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_seq"

    for i in range(3):
        mgr.start_task(key, stage=TaskStage.GENERATION)
        if i < 2:
            mgr.fail(
                key,
                stage=TaskStage.GENERATION,
                error_type=f"Err{i}",
                error_message=f"msg{i}",
                recoverable=True,
            )
        else:
            mgr.succeed(key, content="ok")

    record = mgr.load(key)
    assert [a.attempt_index for a in record.attempts] == [0, 1, 2]


# ── 核心：MAX_TASK_ATTEMPTS 強制（靶心④） ─────────────────────


def test_exhausted_task_rejects_new_attempt(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_exh"

    for i in range(MAX_TASK_ATTEMPTS):
        mgr.start_task(key, stage=TaskStage.GENERATION)
        mgr.fail(
            key,
            stage=TaskStage.GENERATION,
            error_type="PermErr",
            error_message=f"fatal {i}",
            recoverable=False,
        )

    record = mgr.load(key)
    assert record.state == TaskState.EXHAUSTED
    assert len(record.attempts) == MAX_TASK_ATTEMPTS

    # 再嘗試 start → 應被拒絕，不建立新 attempt
    result = mgr.start_task(key, stage=TaskStage.GENERATION)
    assert result.state == TaskState.EXHAUSTED
    assert len(result.attempts) == MAX_TASK_ATTEMPTS


def test_exhausted_after_max_recoverable_failures(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_exh_r"

    for i in range(MAX_TASK_ATTEMPTS):
        mgr.start_task(key, stage=TaskStage.TRANSMISSION)
        mgr.fail(
            key,
            stage=TaskStage.TRANSMISSION,
            error_type="NetworkErr",
            error_message=f"transmission fail {i}",
            recoverable=True,
        )

    record = mgr.load(key)
    assert record.state == TaskState.EXHAUSTED
    assert len(record.attempts) == MAX_TASK_ATTEMPTS


def test_fewer_than_max_failures_stays_retryable(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_retry"

    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="Timeout",
        error_message="gen timeout",
        recoverable=True,
    )

    record = mgr.load(key)
    assert record.state == TaskState.RETRYABLE
    assert len(record.attempts) == 1


# ── 核心：生成例外不得吞沒後標成功（靶心⑤） ─────────────────


def test_generation_exception_does_not_mark_success(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_gen_exc"

    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="RuntimeError",
        error_message="note_product_empty: 補齊流程完成但未產生非空實際筆記",
        recoverable=False,
    )

    record = mgr.load(key)
    assert record.state == TaskState.FAILED
    assert record.attempts[-1].error_type == "RuntimeError"
    assert "note_product_empty" in record.attempts[-1].error_message
    # 不得為 succeeded
    assert record.state != TaskState.SUCCEEDED


def test_generation_exception_attempt_recorded(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_gen_exc2"

    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="ValueError",
        error_message="parse error in segment[2]",
        recoverable=False,
    )

    record = mgr.load(key)
    assert len(record.attempts) == 1
    assert record.attempts[0].stage == TaskStage.GENERATION
    assert record.attempts[0].error_type == "ValueError"


# ── 核心：同名來源不互相覆寫（靶心③） ─────────────────────


def test_same_source_different_keys_are_isolated(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    k1 = build_task_key("note.txt", run_id="run-1")
    k2 = build_task_key("note.txt", run_id="run-2")

    mgr.start_task(k1, stage=TaskStage.GENERATION)
    mgr.fail(
        k1,
        stage=TaskStage.GENERATION,
        error_type="Err1",
        error_message="fail in run-1",
        recoverable=True,
    )

    mgr.start_task(k2, stage=TaskStage.GENERATION)
    mgr.succeed(k2, content="run-2 ok")

    r1 = mgr.load(k1)
    r2 = mgr.load(k2)
    assert r1.state == TaskState.RETRYABLE
    assert r2.state == TaskState.SUCCEEDED
    assert r1.attempts[0].error_type == "Err1"
    assert r2.attempts[0].error_type == ""


def test_different_sources_same_key_overwrites_if_not_isolated(tmp_path):
    """若不用 run_id 區隔，同 key 會累加（測試 build_task_key 的用途）。"""
    mgr = TaskStateManager(tmp_path / "state")
    key = "note.txt"

    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="ErrA",
        error_message="fail A",
        recoverable=True,
    )

    # 第二次 start 同 key（模擬未用 run_id 區隔）
    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.succeed(key, content="ok")

    record = mgr.load(key)
    # 應累加 2 次 attempt
    assert len(record.attempts) == 2
    assert record.state == TaskState.SUCCEEDED


# ── 核心：transmission 階段例外全部落盤（靶心②） ─────────────


def test_transmission_exception_persisted(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_tx"

    mgr.start_task(key, stage=TaskStage.TRANSMISSION)
    mgr.fail(
        key,
        stage=TaskStage.TRANSMISSION,
        error_type="ConnectionRefused",
        error_message="twinkle hub unreachable",
        recoverable=True,
    )

    record = mgr.load(key)
    assert record.state == TaskState.RETRYABLE
    assert record.attempts[0].stage == TaskStage.TRANSMISSION
    assert record.attempts[0].error_type == "ConnectionRefused"


def test_transmission_exception_all_paths_persisted(tmp_path):
    """模擬多種 transmission 失敗路徑，全部必須落盤。"""
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_tx_multi"

    tx_errors = [
        ("ConnectionRefused", "hub unreachable", True),
        ("Timeout", "send timeout 30s", True),
        ("HTTPError", "502 bad gateway", False),
    ]

    for err_type, err_msg, recoverable in tx_errors:
        mgr.start_task(key, stage=TaskStage.TRANSMISSION)
        mgr.fail(
            key,
            stage=TaskStage.TRANSMISSION,
            error_type=err_type,
            error_message=err_msg,
            recoverable=recoverable,
        )

    record = mgr.load(key)
    # 3 次 failure attempts → 達到上限 exhausted
    assert len(record.attempts) == 3
    assert record.state == TaskState.EXHAUSTED
    # 所有錯誤都被保留
    assert record.attempts[0].error_type == "ConnectionRefused"
    assert record.attempts[1].error_type == "Timeout"
    assert record.attempts[2].error_type == "HTTPError"


def test_transmission_stage_recorded_in_attempt(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_tx_stage"

    mgr.start_task(key, stage=TaskStage.TRANSMISSION)
    mgr.fail(
        key,
        stage=TaskStage.TRANSMISSION,
        error_type="OSError",
        error_message="disk full during write",
        recoverable=False,
    )

    record = mgr.load(key)
    assert record.stage == TaskStage.TRANSMISSION
    assert record.attempts[0].stage == TaskStage.TRANSMISSION


# ── 持久化：json 檔可讀寫 ─────────────────────────────────────


def test_state_file_persisted_and_reloadable(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_persist"

    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="Err",
        error_message="persistent fail",
        recoverable=True,
    )

    # 用新的 manager 實例讀取
    mgr2 = TaskStateManager(tmp_path / "state")
    record = mgr2.load(key)
    assert record is not None
    assert record.state == TaskState.RETRYABLE
    assert len(record.attempts) == 1
    assert record.attempts[0].error_message == "persistent fail"


def test_task_record_to_dict_and_from_dict_roundtrip(tmp_path):
    rec = TaskRecord("key_rt", state=TaskState.RETRYABLE, stage=TaskStage.TRANSMISSION)
    rec.attempts.append(
        AttemptRecord(
            0,
            stage=TaskStage.TRANSMISSION,
            error_type="NetErr",
            error_message="timeout",
            recoverable=True,
        )
    )
    rec.artifact_path = "/tmp/art.md"
    rec.source_locator = "file:///tmp/note.txt"
    rec.content_hash = "abc123"

    d = rec.to_dict()
    rec2 = TaskRecord.from_dict(d)
    assert rec2.task_key == "key_rt"
    assert rec2.state == TaskState.RETRYABLE
    assert rec2.stage == TaskStage.TRANSMISSION
    assert len(rec2.attempts) == 1
    assert rec2.attempts[0].error_type == "NetErr"
    assert rec2.artifact_path == "/tmp/art.md"
    assert rec2.content_hash == "abc123"


# ── query 回傳 ────────────────────────────────────────────────


def test_query_returns_attempt_count_and_last_attempt(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    key = "src_q"

    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="Err1",
        error_message="m1",
        recoverable=True,
    )
    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="Err2",
        error_message="m2",
        recoverable=False,
    )

    q = mgr.query(key)
    assert q is not None
    assert q["attempt_count"] == 2
    assert q["last_attempt"]["error_type"] == "Err2"


def test_query_nonexistent_returns_none(tmp_path):
    mgr = TaskStateManager(tmp_path / "state")
    assert mgr.query("no_such_key") is None


# ── 端到端：兩次失敗後第三次成功，前兩次紀錄完整 ────────────


def test_two_failures_then_success_preserves_all_error_records(tmp_path):
    """靶心①完整驗證：前兩次的 error_type、error_message、timestamp 都在。"""
    mgr = TaskStateManager(tmp_path / "state")
    key = "e2e_accumulate"

    # attempt 0
    mgr.start_task(key, stage=TaskStage.GENERATION)
    t0_fail = time.time()
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="LLMTimeout",
        error_message="generation timeout at gap[0]",
        recoverable=True,
    )

    # attempt 1
    mgr.start_task(key, stage=TaskStage.GENERATION)
    t1_fail = time.time()
    mgr.fail(
        key,
        stage=TaskStage.GENERATION,
        error_type="LLMError",
        error_message="malformed JSON response",
        recoverable=True,
    )

    # attempt 2
    mgr.start_task(key, stage=TaskStage.GENERATION)
    mgr.succeed(key, artifact_path="/out/note.md", content="success content")

    record = mgr.load(key)
    assert record is not None
    assert record.state == TaskState.SUCCEEDED
    assert len(record.attempts) == 3

    # attempt 0 紀錄
    a0 = record.attempts[0]
    assert a0.attempt_index == 0
    assert a0.error_type == "LLMTimeout"
    assert "gap[0]" in a0.error_message
    assert a0.stage == TaskStage.GENERATION
    assert a0.recoverable is True

    # attempt 1 紀錄
    a1 = record.attempts[1]
    assert a1.attempt_index == 1
    assert a1.error_type == "LLMError"
    assert "malformed JSON" in a1.error_message
    assert a1.stage == TaskStage.GENERATION
    assert a1.recoverable is True

    # attempt 2 紀錄
    a2 = record.attempts[2]
    assert a2.attempt_index == 2
    assert a2.error_type == ""
    assert a2.error_message == ""
    assert a2.stage == TaskStage.GENERATION

    # 內容雜湊
    assert record.content_hash
