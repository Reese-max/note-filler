import json
from datetime import date

import pytest

from note_filler.retrieve.models import Source
from note_filler.retrieve import twinkle
from note_filler.retrieve.twinkle import TwinkleClient

_BILL = {
    "id": "1120001",
    "title": "道路交通管理處罰條例部分條文修正草案",
    "議案類別": "法律案",
    "議案狀態": "交付審查",
    "提案人": "王小明委員等 17 人",
    "提案日期": "2024-03-15",
    "案由": "為提高酒後駕車罰則、遏止累犯,爰擬具本修正草案。",
    "說明": "一、現行條文對累犯之處罰不足。二、修正理由:參酌日本立法例,提高吊銷年限。",
    "url": "https://ly.gov.tw/bill/1120001",
    "similarity": 0.82,
}


class _FakeResponse:
    def __init__(self, body: str, session: str | None = "sess-1"):
        self._body = body.encode("utf-8")
        self.headers = {"Mcp-Session-Id": session}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _make_fake_urlopen(hits: list[dict]):
    """依 JSON-RPC method 回不同 payload:tools/call 回 SSE 包住的議案清單。"""
    def fake_urlopen(request, timeout=None):
        body = json.loads(request.data.decode("utf-8"))
        if body.get("method") == "tools/call":
            inner = json.dumps({"hits": hits}, ensure_ascii=False)
            envelope = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {"content": [{"type": "text", "text": inner}]},
                },
                ensure_ascii=False,
            )
            return _FakeResponse(f"data: {envelope}\n\n")  # 驗 SSE 解析路徑
        # initialize / notifications/initialized
        plain = json.dumps({"jsonrpc": "2.0", "id": body.get("id"), "result": {}})
        return _FakeResponse(plain)

    return fake_urlopen


def test_search_parses_source_with_full_content(monkeypatch):
    monkeypatch.setattr(
        twinkle.urllib.request, "urlopen", _make_fake_urlopen([_BILL])
    )
    client = TwinkleClient(token="fake-token")
    results = client.search("酒駕 罰則", n=3)

    assert len(results) == 1
    src = results[0]
    assert isinstance(src, Source)
    assert src.title == _BILL["title"]
    assert src.url == "https://ly.gov.tw/bill/1120001"
    assert src.level == "B"                     # metadata 無 source_level → 預設 B
    assert src.doc_date == "2024-03-15"
    assert src.fetched_date == date.today().isoformat()
    # ★ 全文 content:案由 + 說明全文都在,非截斷摘要(G4)
    assert "現行條文對累犯之處罰不足" in src.content
    assert "參酌日本立法例" in src.content
    assert "王小明委員等 17 人" in src.content
    assert abs(src.distance - (0.6 + 0.4 * (1 - 0.82))) < 1e-9


def test_search_returns_empty_without_token(monkeypatch):
    monkeypatch.delenv("TWINKLE_HUB_TOKEN", raising=False)
    assert TwinkleClient(token="").search("酒駕") == []


def test_search_reuses_mcp_session(monkeypatch):
    requests = []
    fake_urlopen = _make_fake_urlopen([_BILL])

    def recording_urlopen(request, timeout=None):
        body = json.loads(request.data.decode("utf-8"))
        headers = {key.lower(): value for key, value in request.header_items()}
        requests.append((body["method"], headers.get("mcp-session-id")))
        return fake_urlopen(request, timeout)

    monkeypatch.setattr(twinkle.urllib.request, "urlopen", recording_urlopen)

    assert TwinkleClient(token="fake-token").search("酒駕")
    assert requests == [
        ("initialize", None),
        ("notifications/initialized", "sess-1"),
        ("tools/call", "sess-1"),
    ]


def test_search_transport_failure_returns_empty(monkeypatch):
    def fail_urlopen(request, timeout=None):
        raise TimeoutError("twinkle timeout")

    monkeypatch.setattr(twinkle.urllib.request, "urlopen", fail_urlopen)

    assert TwinkleClient(token="fake-token").search("酒駕") == []


def test_default_timeout_is_60():
    # 讀取逾時屬網路問題,預設放寬到 60 秒
    assert TwinkleClient(token="x").timeout == 60


@pytest.mark.integration
def test_search_real_twinkle_hub():
    import os

    token = os.environ.get("TWINKLE_HUB_TOKEN", "")
    if not token:
        pytest.skip("未設定 TWINKLE_HUB_TOKEN,跳過 twinkle-hub 真打整合測試")
    results = TwinkleClient(token=token).search("道路交通管理處罰條例", n=3)
    assert isinstance(results, list)
    for src in results:
        assert isinstance(src, Source)
        assert src.level in ("A", "B")
        assert src.content.strip()               # 全文非空
        assert src.fetched_date == date.today().isoformat()
