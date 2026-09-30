from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any


_private_log_id = ContextVar("note_filler_private_log_id", default=None)


@contextmanager
def private_logs(data_id: str):
    """Redact nested Web logs; ContextVar also follows AnyIO worker threads."""
    previous_factory = logging.getLogRecordFactory()
    if not getattr(previous_factory, "_note_filler_private_logs", False):
        # Install once and chain the existing factory, never toggle global logging
        # per request: concurrent CLI work must retain its normal diagnostics.
        def record_factory(*args, **kwargs):
            record = previous_factory(*args, **kwargs)
            private_id = _private_log_id.get()
            if private_id is not None:
                record.msg = json.dumps(
                    {"event": "web_processing_log", "data_id": private_id,
                     "function": record.funcName, "details": "redacted"},
                    ensure_ascii=False,
                )
                record.args = ()
                record.message = record.msg
                record.exc_info = record.exc_text = record.stack_info = None
            return record

        record_factory._note_filler_private_logs = True
        logging.setLogRecordFactory(record_factory)
    token = _private_log_id.set(data_id)
    try:
        yield
    finally:
        _private_log_id.reset(token)


def audit_event(
    logger: logging.Logger,
    event: str,
    data_id: object,
    *,
    level: int = logging.WARNING,
    **details: Any,
) -> None:
    """寫一行可機器解析、必含資料識別碼的 JSON 稽核紀錄。"""
    logger.log(
        level,
        json.dumps(
            {"event": event, "data_id": str(data_id), **details},
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ),
    )
