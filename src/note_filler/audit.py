from __future__ import annotations

import json
import logging
from typing import Any


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
