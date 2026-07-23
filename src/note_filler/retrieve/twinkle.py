"""twinkle-hub 立法院議案即時查詢,回傳 note_filler 的 Source(Level B)。

移植自上游 公文ai agent/src/knowledge/mcp_law_source.py(純 stdlib urllib
JSON-RPC Streamable HTTP)。校準:回傳型別改 note_filler.retrieve.models.Source;
content 存「該筆記錄全文」以滿足無搜尋摘要閘(G4);移除 opt-in env 閘。
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import date
from typing import Any

from note_filler.retrieve.models import Source

logger = logging.getLogger(__name__)

DEFAULT_MCP_URL = "https://api.twinkleai.tw/mcp/"
_PROTOCOL_VERSION = "2025-03-26"
_MAX_RESULTS = 100


class MCPProtocolError(RuntimeError):
    """MCP 回應不符合預期協定。"""


# ---- 傳輸層:沿用上游(_decode_streamable_http / TwinkleMCPClient) ----
def _decode_streamable_http(raw: str) -> dict[str, Any] | None:
    """解析 MCP Streamable HTTP 的 JSON 或 SSE 最後一個 data payload。"""
    payloads = [
        line[5:].strip()
        for line in raw.splitlines()
        if line.startswith("data:") and line[5:].strip()
    ]
    text = payloads[-1] if payloads else raw.strip()
    if not text:
        return None
    decoded = json.loads(text)
    if not isinstance(decoded, dict):
        raise MCPProtocolError("MCP JSON-RPC 回應不是物件")
    if decoded.get("error"):
        raise MCPProtocolError(f"MCP JSON-RPC 錯誤: {decoded['error']}")
    return decoded


class TwinkleMCPClient:
    """只實作 initialize 與 tools/call 的最小 Streamable HTTP client(沿用上游)。"""

    def __init__(self, url: str, key: str, timeout: float) -> None:
        self.url = url
        self.key = key
        self.timeout = timeout
        self._session: str | None = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _rpc(self, method: str, params: dict[str, Any], *, notify: bool = False):
        if not self.key:
            raise MCPProtocolError("缺少 twinkle-hub 存取權杖")
        headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notify:
            payload["id"] = self._next_id()
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            session_id = response.headers.get("Mcp-Session-Id")
            if session_id:
                self._session = session_id
            raw = response.read().decode("utf-8")
        return _decode_streamable_http(raw)

    def _ensure_session(self) -> None:
        if self._session:
            return
        self._rpc(
            "initialize",
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "note-filler", "version": "0.1.0"},
            },
        )
        self._rpc("notifications/initialized", {}, notify=True)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._ensure_session()
        response = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if not response:
            return {}
        result = response.get("result")
        if not isinstance(result, dict):
            raise MCPProtocolError("MCP tools/call 缺少 result")
        if result.get("isError"):
            raise MCPProtocolError(f"MCP 工具回報失敗: {result.get('content', '')}")
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        content = result.get("content")
        if not isinstance(content, list):
            raise MCPProtocolError("MCP tools/call 缺少 content")
        for item in content:
            if not isinstance(item, dict) or item.get("type") not in (None, "text"):
                continue
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            decoded = json.loads(text)
            if isinstance(decoded, dict):
                return decoded
        return {}


# ---- 轉 Source(★必修項:全文 content / level / 日期 / distance 魔數) ----
def _first_text(hit: dict[str, Any], *names: str) -> str:
    for name in names:
        value = hit.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _clamp_similarity(value: Any) -> float:
    try:
        similarity = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return min(max(similarity, 0.0), 1.0)


def _extract_hits(data: dict[str, Any]) -> list[Any]:
    for key in ("hits", "results", "data"):
        hits = data.get(key)
        if isinstance(hits, list):
            return hits
    return []


def _record_fulltext(hit: dict[str, Any]) -> str:
    """★C5/G4:把整筆記錄(含 metadata)攤平成全文,絕不截斷成搜尋摘要。"""
    lines: list[str] = []
    for key, value in hit.items():
        if key in ("similarity", "distance"):
            continue
        if isinstance(value, (str, int, float)) and str(value).strip():
            lines.append(f"{key}: {str(value).strip()}")
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (str, int, float)) and str(sub_value).strip():
                    lines.append(f"{key}.{sub_key}: {str(sub_value).strip()}")
    return "\n".join(lines)


def _to_source(hit: dict[str, Any]) -> Source | None:
    title = _first_text(hit, "title", "議案名稱", "name")
    if not title:
        logger.warning(
            "twinkle-hub hit 缺 title 欄位,略過: id=%s url=%s",
            hit.get("id", "?"),
            hit.get("url", "?"),
        )
        return None
    meta = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
    url = (
        _first_text(hit, "url", "source_url", "網址")
        or _first_text(meta, "source_url", "url")
        or None
    )
    level = str(meta.get("source_level") or "B")  # ★ metadata.source_level 否則 "B"
    doc_date = _first_text(hit, "date", "提案日期", "最新進度日期", "doc_date") or None
    source_id = _first_text(hit, "id", "bill_id", "議案編號") or url or title
    similarity = _clamp_similarity(hit.get("similarity"))
    return Source(
        id=source_id,
        title=title,
        url=url,
        level=level,  # type: ignore[arg-type]  # MVP 只產 A/B,此源恆 B
        content=_record_fulltext(hit),          # ★ 全文,非截斷摘要
        fetched_date=date.today().isoformat(),  # ★ 今天 ISO
        doc_date=doc_date,                        # ★ 記錄有日期則帶,否則 None
        # TODO(校準): 0.6 魔數綁定上游 KB 快照分布(1-similarity 落 0.05-0.2,
        # 需壓入 [0.6,1.0] 頻帶避免系統性壓過本地 Level A 全文)。若日後接入
        # note_filler 自有向量檢索,須以 MCP OFF 對 3+ 典型 query 重量測 distance 分布
        # 後重設下界,勿沿用 0.6。
        distance=0.6 + 0.4 * (1.0 - similarity),
    )


class TwinkleClient:
    """twinkle-hub 立法院議案查詢;回傳 Level B 的 Source(無 token → 空結果)。"""

    def __init__(self, token: str, url: str = DEFAULT_MCP_URL, timeout: float = 60):
        self.token = token or os.environ.get("TWINKLE_HUB_TOKEN", "")  # env 後援
        self.url = url
        self.timeout = timeout

    def search(self, query: str, n: int = 3) -> list[Source]:
        if not self.token or not isinstance(query, str) or not query.strip():
            return []
        try:
            limit = min(max(int(n), 1), _MAX_RESULTS)
        except (TypeError, ValueError):
            limit = 3
        try:
            data = TwinkleMCPClient(self.url, self.token, self.timeout).call_tool(
                "search_ly_bills",
                {"query": query.strip(), "limit": limit},
            )
        except Exception as exc:  # noqa: BLE001 - 外部服務不得中斷主流程
            logger.warning("twinkle-hub 查詢失敗,降級為空結果: %s", exc)
            return []
        sources: list[Source] = []
        for raw_hit in _extract_hits(data):
            if not isinstance(raw_hit, dict):
                continue
            source = _to_source(raw_hit)
            if source:
                sources.append(source)
        return sources[:limit]
