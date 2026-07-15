from __future__ import annotations

import json
import urllib.request
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, messages: list[dict], **kw) -> str: ...


class GrokClient:
    """研究層 LLM:xAI grok,OpenAI 相容端點(本機 proxy :8318)。純 stdlib。"""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8318/v1",
        model: str = "grok-4.3",
        api_key: str = "x",
        timeout: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, messages: list[dict], **kw) -> str:
        body = {"model": self.model, "messages": messages, **kw}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]


class FakeLLM:
    """測試用:建構時給定 canned responses,每次 complete 依序 pop(0) 回傳。"""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], **kw) -> str:
        self.calls.append(messages)
        return self.responses.pop(0)
