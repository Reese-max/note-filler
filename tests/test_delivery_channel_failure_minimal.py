"""最小負例測試：驗證送達通道失敗或 provider/執行器拋錯時的行為。"""

import builtins
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


def test_local_success_user_channel_failure_regression(tmp_path, monkeypatch, capsys):
    """回歸測試：本機檔案成功但使用者通道未送達時，驗證：
      1. 流程不能被判定為完成（exit code != 0）
      2. 必須保留可讀筆記內容（local_fallback_written = True）
      3. 必須保留可解析的送達失敗狀態（user_channel_sent = False, status = failed）
    """
    note = tmp_path / "regression-note.txt"
    original_text = "原稿內容，需要保留。"
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
        "補充內容已生成",
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

    # 模擬使用者通道（stdout）送達失敗
    real_print = builtins.print

    def fail_stdout(*args, **kwargs):
        if kwargs.get("file") is None:
            raise OSError("user channel unavailable")
        return real_print(*args, **kwargs)

    monkeypatch.setattr(builtins, "print", fail_stdout)

    exit_code = cli.main([str(note), "-o", str(out), "--db", str(db)])
    captured = capsys.readouterr()

    # 驗證 1：流程不能被判定為完成（exit code != 0）
    assert exit_code != 0, "本機成功但使用者通道失敗時，exit code 應為非 0"

    # 驗證 2：本機檔案成功，可讀筆記內容已保留
    delivered = (out / "regression-note.訂正稿.md").read_text(encoding="utf-8")
    assert original_text in delivered, "原稿內容應保留在本機檔案中"
    assert "補充內容已生成" in delivered, "生成內容應保留在本機檔案中"

    # 驗證 3：delivery manifest 存在且包含送達失敗狀態
    receipt = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert receipt["status"] == "failed", "manifest status 應為 failed"
    assert receipt["delivery_status"]["primary_note_ready"] == True, "primary_note_ready 應為 True"
    assert receipt["delivery_status"]["user_channel_sent"] == False, "user_channel_sent 應為 False"
    assert receipt["delivery_status"]["local_fallback_written"] == True, "local_fallback_written 應為 True"

    # 驗證 4：錯誤訊息不暴露底層堆疊
    visible = captured.out + captured.err + delivered
    assert "Traceback" not in visible, "不應暴露堆疊"
    assert "user channel unavailable" in captured.err, "stderr 應包含送達失敗原因"
