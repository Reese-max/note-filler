"""持久化任務狀態管理。

提供 note-filler 流程中每個任務的狀態追蹤：
  - 狀態：pending / running / failed / retryable / succeeded / exhausted
  - 階段：generation / transmission
  - 歷次嘗試紀錄（attempts 陣列）：每次 attempt 保留時間、錯誤類型、錯誤訊息、
    階段、是否可恢復——重試時累加而非覆寫。
  - MAX_TASK_ATTEMPTS 強制上限：exhausted 任務不得再建新 attempt。

設計約束（來自歷輪拒收靶心）：
  ① 重試必須「累加」而非覆寫，保留每次 attempt 的失敗時間與錯誤原因。
  ② transmission 階段的例外路徑要逐一盤點並全部落盤。
  ③ 同名來源不得互相覆寫任務狀態，鍵須含來源唯一識別。
  ④ exhausted 任務不得再建第 4 次 attempt。
  ⑤ 生成例外不得吞沒後標成功。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import errno
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MAX_TASK_ATTEMPTS = 3


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FAILED = "failed"
    RETRYABLE = "retryable"
    SUCCEEDED = "succeeded"
    EXHAUSTED = "exhausted"


class TaskStage(str, Enum):
    GENERATION = "generation"
    TRANSMISSION = "transmission"


class AttemptRecord:
    """單次嘗試紀錄：時間、錯誤、階段、可恢復性。"""

    __slots__ = (
        "attempt_index",
        "timestamp",
        "stage",
        "error_type",
        "error_message",
        "recoverable",
        "artifact_path",
    )

    def __init__(
        self,
        attempt_index: int,
        *,
        stage: TaskStage,
        error_type: str = "",
        error_message: str = "",
        recoverable: bool = False,
        artifact_path: str = "",
    ) -> None:
        self.attempt_index = attempt_index
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.stage = stage
        self.error_type = error_type
        self.error_message = error_message
        self.recoverable = recoverable
        self.artifact_path = artifact_path

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_index": self.attempt_index,
            "timestamp": self.timestamp,
            "stage": self.stage.value,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "recoverable": self.recoverable,
            "artifact_path": self.artifact_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttemptRecord:
        rec = cls(
            attempt_index=data["attempt_index"],
            stage=TaskStage(data["stage"]),
            error_type=data.get("error_type", ""),
            error_message=data.get("error_message", ""),
            recoverable=data.get("recoverable", False),
            artifact_path=data.get("artifact_path", ""),
        )
        rec.timestamp = data.get("timestamp", rec.timestamp)
        return rec


class TaskRecord:
    """單一任務的完整狀態紀錄。

    task_key 格式：{source_unique_id}，確保同名來源不互相覆寫。
    attempts 陣列累加所有嘗試紀錄，重試時只 append，不覆寫既有紀錄。
    """

    __slots__ = (
        "task_key",
        "state",
        "stage",
        "attempts",
        "created_at",
        "updated_at",
        "artifact_path",
        "source_locator",
        "content_hash",
    )

    def __init__(
        self,
        task_key: str,
        *,
        state: TaskState = TaskState.PENDING,
        stage: TaskStage = TaskStage.GENERATION,
    ) -> None:
        self.task_key = task_key
        self.state = state
        self.stage = stage
        self.attempts: list[AttemptRecord] = []
        now = datetime.now(timezone.utc).isoformat()
        self.created_at = now
        self.updated_at = now
        self.artifact_path = ""
        self.source_locator = ""
        self.content_hash = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_key": self.task_key,
            "state": self.state.value,
            "stage": self.stage.value,
            "attempts": [a.to_dict() for a in self.attempts],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "artifact_path": self.artifact_path,
            "source_locator": self.source_locator,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskRecord:
        rec = cls(
            task_key=data["task_key"],
            state=TaskState(data["state"]),
            stage=TaskStage(data["stage"]),
        )
        rec.attempts = [AttemptRecord.from_dict(a) for a in data.get("attempts", [])]
        rec.created_at = data.get("created_at", rec.created_at)
        rec.updated_at = data.get("updated_at", rec.updated_at)
        rec.artifact_path = data.get("artifact_path", "")
        rec.source_locator = data.get("source_locator", "")
        rec.content_hash = data.get("content_hash", "")
        return rec


def build_task_key(source_id: str, *, run_id: str = "") -> str:
    """建立含來源唯一識別的任務鍵，防止同名來源互相覆寫。

    格式：{source_id} 或 {source_id}:{run_id}。
    """
    if run_id:
        return f"{source_id}:{run_id}"
    return source_id


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


class TaskStateCorruptionError(RuntimeError):
    """Existing unknown history is never authority to start a fresh task."""


def _read_record(path: Path) -> TaskRecord:
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not a regular state file")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("task_key"), str) or not data["task_key"]:
            raise ValueError("missing task identity")
        if set(data) != set(TaskRecord.__slots__):
            raise ValueError("unknown state schema")
        attempts = data.get("attempts")
        if not isinstance(attempts, list):
            raise ValueError("invalid attempts")
        for index, attempt in enumerate(attempts):
            if not isinstance(attempt, dict) or type(attempt.get("attempt_index")) is not int or attempt["attempt_index"] != index:
                raise ValueError("invalid attempt sequence")
            if set(attempt) != set(AttemptRecord.__slots__):
                raise ValueError("unknown attempt schema")
            if not isinstance(attempt.get("timestamp"), str) or not attempt["timestamp"]:
                raise ValueError("missing attempt provenance")
            TaskStage(attempt["stage"])
            for field in ("timestamp", "error_type", "error_message", "artifact_path"):
                if field in attempt and not isinstance(attempt[field], str):
                    raise ValueError("invalid attempt field")
            if "recoverable" in attempt and type(attempt["recoverable"]) is not bool:
                raise ValueError("invalid retry flag")
        for field in ("created_at", "updated_at", "artifact_path", "source_locator", "content_hash"):
            if field in data and not isinstance(data[field], str):
                raise ValueError("invalid state field")
        return TaskRecord.from_dict(data)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        # Never echo state/note fragments, JSON decoder messages or provider text.
        logger.warning("task_state_corrupted")
        raise TaskStateCorruptionError("Task state is unreadable or invalid; preserve it for manual recovery") from None


class TaskStateManager:
    """管理所有任務狀態的持久化 Store。

    狀態檔寫在 state_dir 下，檔名為 task_key 的 safe filename。
    """

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _state_path(self, task_key: str) -> Path:
        # Separator replacement aliases a/b.txt with a_b.txt and can exceed the
        # filesystem filename limit for an otherwise valid deep vault path.
        identity = hashlib.sha256(task_key.encode("utf-8")).hexdigest()
        return self.state_dir / f"{identity}.task_state.json"

    def _legacy_path(self, task_key: str) -> Path | None:
        safe = task_key.replace("/", "_").replace("\\", "_").replace(":", "_")
        path = self.state_dir / f"{safe}.task_state.json"
        try:
            return path if path.exists() or path.is_symlink() else None
        except OSError as error:
            if error.errno == errno.ENAMETOOLONG:
                return None # Such a legacy filename could never have been written.
            raise

    def load(self, task_key: str) -> TaskRecord | None:
        path = self._state_path(task_key)
        if path.exists() or path.is_symlink():
            record = _read_record(path)
            if record.task_key != task_key:
                raise TaskStateCorruptionError("Task state identity mismatch; preserve it for manual recovery")
            return record
        legacy = self._legacy_path(task_key)
        if legacy is None:
            return None
        record = _read_record(legacy)
        # A valid legacy file can belong to another colliding key. Preserve it;
        # this distinct task starts under its own digest, never under that key.
        return record if record.task_key == task_key else None

    def save(self, record: TaskRecord) -> None:
        record.updated_at = datetime.now(timezone.utc).isoformat()
        path = self._state_path(record.task_key)
        if path.exists() or path.is_symlink():
            current = _read_record(path)
            if current.task_key != record.task_key:
                raise TaskStateCorruptionError("Task state identity mismatch; preserve it for manual recovery")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=self.state_dir,
                                             prefix=path.name + "-", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(record.to_dict(), handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def start_task(
        self,
        task_key: str,
        *,
        stage: TaskStage = TaskStage.GENERATION,
        source_locator: str = "",
    ) -> TaskRecord:
        """開始或重試一個任務。

        - 若已 exhausted，拒絕建立新 attempt。
        - 若已有紀錄，累加新 attempt（不覆寫既有 attempts）。
        """
        existing = self.load(task_key)
        if existing is not None:
            if existing.state == TaskState.EXHAUSTED or len(existing.attempts) >= MAX_TASK_ATTEMPTS:
                if existing.state != TaskState.EXHAUSTED:
                    existing.state = TaskState.EXHAUSTED
                    self.save(existing)
                audit_event(
                    logger,
                    "task_state_rejected",
                    task_key,
                    reason="exhausted task cannot start new attempt",
                    current_attempts=len(existing.attempts),
                )
                return existing
            record = existing
        else:
            record = TaskRecord(task_key, state=TaskState.RUNNING, stage=stage)
            record.source_locator = source_locator

        record.state = TaskState.RUNNING
        record.stage = stage
        attempt = AttemptRecord(
            attempt_index=len(record.attempts),
            stage=stage,
        )
        record.attempts.append(attempt)
        self.save(record)
        return record

    def succeed(
        self,
        task_key: str,
        *,
        artifact_path: str = "",
        content: str = "",
    ) -> TaskRecord:
        """標記任務成功。更新最後一個 attempt（由 start_task 建立）。"""
        record = self.load(task_key)
        if record is None:
            record = TaskRecord(task_key, state=TaskState.SUCCEEDED)
        record.state = TaskState.SUCCEEDED
        if artifact_path:
            record.artifact_path = artifact_path
        if content:
            record.content_hash = _hash_content(content)
        self.save(record)
        return record

    def fail(
        self,
        task_key: str,
        *,
        stage: TaskStage,
        error_type: str,
        error_message: str,
        recoverable: bool = False,
        artifact_path: str = "",
    ) -> TaskRecord:
        """記錄失敗，更新最後一個 attempt（由 start_task 建立）的錯誤資訊。

        - 不可覆寫既有 attempts 的錯誤欄位。
        - 若嘗試次數已達上限，轉為 exhausted。
        """
        record = self.load(task_key)
        if record is None:
            record = TaskRecord(task_key, state=TaskState.FAILED, stage=stage)

        # 更新最後一個 attempt（由 start_task 建立）的錯誤資訊
        if record.attempts:
            last_attempt = record.attempts[-1]
            last_attempt.stage = stage
            last_attempt.error_type = error_type
            last_attempt.error_message = error_message
            last_attempt.recoverable = recoverable
            last_attempt.artifact_path = artifact_path
        else:
            # fallback：若無 attempt（不應發生），建立一個
            attempt = AttemptRecord(
                attempt_index=0,
                stage=stage,
                error_type=error_type,
                error_message=error_message,
                recoverable=recoverable,
                artifact_path=artifact_path,
            )
            record.attempts.append(attempt)

        if len(record.attempts) >= MAX_TASK_ATTEMPTS:
            record.state = TaskState.EXHAUSTED
            audit_event(
                logger,
                "task_state_exhausted",
                task_key,
                total_attempts=len(record.attempts),
                last_error_type=error_type,
                last_error_message=error_message,
            )
        elif recoverable:
            record.state = TaskState.RETRYABLE
        else:
            record.state = TaskState.FAILED

        record.stage = stage
        self.save(record)
        return record

    def query(self, task_key: str) -> dict[str, Any] | None:
        """查詢任務狀態，回傳可序列化的 dict。"""
        record = self.load(task_key)
        if record is None:
            return None
        result = record.to_dict()
        result["attempt_count"] = len(record.attempts)
        if record.attempts:
            last = record.attempts[-1]
            result["last_attempt"] = last.to_dict()
        return result


def audit_event(
    logger: logging.Logger,
    event: str,
    data_id: object,
    *,
    level: int = logging.WARNING,
    **details: Any,
) -> None:
    """寫一行可機器解析、必含資料識別碼的 JSON 稽核紀錄。"""
    import json as _json

    logger.log(
        level,
        _json.dumps(
            {"event": event, "data_id": str(data_id), **details},
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ),
    )
