"""Web 端結果暫存:把每份訂正稿綁到不可猜的 result id 與所屬 session。

取代舊制 process-global ``app.state.last_doc``:同一 application process 下,
不同 client 不能再靠呼叫全域匯出端點拿到別人的訂正稿。每筆結果同時要求
opaque result id(能力令牌)與 owner session id(瀏覽器 cookie)相符才放行;
兩者缺一律視為不存在,不回退到「最新一份文件」。
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Callable

from note_filler.correction import CorrectionDoc

MISSING = "missing"
EXPIRED = "expired"
OK = "ok"

DEFAULT_TTL_SECONDS = 3600.0
MAX_RESULTS = 64


@dataclass
class _Entry:
    doc: CorrectionDoc
    owner: str
    expires_at: float


class ResultStore:
    """In-memory result store keyed by opaque result id.

    - ``put`` 為每次成功 run 產生新的 unguessable result id;
    - ``get`` 只在未過期且 owner(session cookie)相符時回傳文件;
      不存在或他人所有一律回 ``MISSING``,不洩漏差別(含已過期項目,
      owner 檢查先於過期檢查);
    - ``discard_owner`` 在該 session 開始新 run 時清掉其舊結果,
      讓失敗的 run 無法再把上一份成功稿當成本次產物匯出;
    - TTL 過期即刪除並回 ``EXPIRED``;process 重啟後全部清空。
    """

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._entries: dict[str, _Entry] = {}

    def put(self, doc: CorrectionDoc, owner: str) -> str:
        now = self._clock()
        self._drop_expired(now)
        while len(self._entries) >= MAX_RESULTS:
            oldest = min(
                self._entries,
                key=lambda rid: self._entries[rid].expires_at,
            )
            del self._entries[oldest]
        rid = secrets.token_urlsafe(24)
        self._entries[rid] = _Entry(doc=doc, owner=owner, expires_at=now + self._ttl)
        return rid

    def get(self, rid: str, owner: str | None) -> tuple[str, CorrectionDoc | None]:
        entry = self._entries.get(rid)
        if entry is None:
            return MISSING, None
        if owner is None or entry.owner != owner:
            return MISSING, None  # 不洩漏存在性,含已過期項目
        if entry.expires_at <= self._clock():
            del self._entries[rid]
            return EXPIRED, None
        return OK, entry.doc

    def discard_owner(self, owner: str) -> None:
        doomed = [
            rid for rid, entry in self._entries.items() if entry.owner == owner
        ]
        for rid in doomed:
            del self._entries[rid]

    def _drop_expired(self, now: float) -> None:
        expired = [
            rid for rid, entry in self._entries.items() if entry.expires_at <= now
        ]
        for rid in expired:
            del self._entries[rid]
