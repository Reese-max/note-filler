import json
import socket
import urllib.error
import urllib.request

import pytest

from note_filler.llm import FakeLLM, GrokClient


def _grok_reachable(host: str = "127.0.0.1", port: int = 8318) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def test_fakellm_returns_canned_in_order():
    llm = FakeLLM(["first", "second"])
    assert llm.complete([{"role": "user", "content": "a"}]) == "first"
    assert llm.complete([{"role": "user", "content": "b"}]) == "second"


def test_grokclient_builds_request_body(monkeypatch):
    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "OK"}}]}
            ).encode("utf-8")

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["auth"] = req.get_header("Authorization")
        captured["content_type"] = req.get_header("Content-type")
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    client = GrokClient(api_key="secret", model="grok-4.3", timeout=42)
    out = client.complete([{"role": "user", "content": "hi"}], temperature=0.0)

    assert out == "OK"
    assert captured["url"] == "http://127.0.0.1:8318/v1/chat/completions"
    assert captured["method"] == "POST"
    assert captured["auth"] == "Bearer secret"
    assert captured["content_type"] == "application/json"
    assert captured["body"] == {
        "model": "grok-4.3",
        "messages": [{"role": "user", "content": "hi"}],
        "temperature": 0.0,
    }
    assert captured["timeout"] == 42


def test_grokclient_urlopen_error(monkeypatch):
    def fake_error(*args, **kw):
        raise urllib.error.URLError("connection refused")
    monkeypatch.setattr(urllib.request, "urlopen", fake_error)
    with pytest.raises(urllib.error.URLError, match="connection refused"):
        GrokClient().complete([{"role": "user", "content": "hi"}])


def test_grokclient_json_decode_error(monkeypatch):
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *exc): return False
        def read(self): return b"not-json-at-all"
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: FakeResp())
    with pytest.raises(json.JSONDecodeError):
        GrokClient().complete([{"role": "user", "content": "hi"}])


def test_grokclient_malformed_response_error(monkeypatch):
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *exc): return False
        def read(self): return json.dumps({"unexpected": "shape"}).encode("utf-8")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: FakeResp())
    with pytest.raises((KeyError, IndexError)):
        GrokClient().complete([{"role": "user", "content": "hi"}])


@pytest.mark.integration
@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")
def test_grok_pong_integration():
    client = GrokClient()
    out = client.complete(
        [{"role": "user", "content": "Reply with exactly one word: PONG"}]
    )
    assert "PONG" in out.upper()
