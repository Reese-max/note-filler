"""最小負例測試：驗證送達通道失敗或 provider/執行器拋錯時的行為。"""

import json
from pathlib import Path

from note_filler import __main__ as cli
from note_filler.retrieve.models import Source


class _SequenceLLM:
    def __init__(self, responses):
        self.responses = iter(responses)

    def complete(self, messages, **kw):
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return value


def _source(sid: str = "source-1", *, level: str = "A") -> Source:
    return Source(
        id=sid,
        title=f"title-{sid}",
        url=f"https://example.test/{sid}",
        level=level,
        content="可引用全文內容",
        fetched_date="2026-07-24",
        doc_date=None,
        distance=0.1,
    )


def test_delivery_channel_failure_minimal(tmp_path, monkeypatch, capsys):
    """最小負例：provider 拋錯時驗證流程不中斷、不暴露堆疊、仍產出可讀筆記。"""
    note = tmp_path / "minimal-fail.txt"
    original_text = "原稿內容。"
    note.write_text(original_text, encoding="utf-8")
    out = tmp_path / "out"
    db = tmp_path / "law.db"
    db.touch()

    question = "測試問題？"
    llm = _SequenceLLM([
        "law",
        question,
        json.dumps([{"question": question, "status": "missing", "reason": "測試"}], ensure_ascii=False),
        '{"keywords":[]}',
        RuntimeError("provider-error"),
    ])

    class Twinkle:
        def search(self, q):
            return [_source("s1", level="B")]

    class Law:
        def search_articles(self, kw, lim, ln):
            return []

    monkeypatch.setattr(cli, "GrokClient", lambda: llm)
    monkeypatch.setattr(cli, "TwinkleClient", lambda token="": Twinkle())
    monkeypatch.setattr(cli, "LawLookup", lambda path: Law())

    exit_code = cli.main([str(note), "-o", str(out), "--db", str(db)])
    captured = capsys.readouterr()
    delivered = (out / "minimal-fail.訂正稿.md").read_text(encoding="utf-8")
    receipt = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
    visible = captured.out + captured.err + delivered

    assert exit_code == 0
    assert original_text in delivered
    assert "【待補證】" in delivered
    assert "Traceback" not in visible
    assert "provider-error" not in visible
    assert receipt["status"] == "delivered"
