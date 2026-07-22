import socket

import pytest

from note_filler.llm import FakeLLM
from note_filler.questions import generate_questions


def _grok_reachable(host: str = "127.0.0.1", port: int = 8318) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def test_generate_questions_splits_multiline_string():
    canned = "本法的立法目的為何?\n適用範圍包含哪些對象?\n違反時的罰則規定為何?"
    llm = FakeLLM([canned])

    result = generate_questions("某段筆記內容", "law", llm)

    assert isinstance(result, list)
    assert all(isinstance(q, str) for q in result)
    assert result == [
        "本法的立法目的為何?",
        "適用範圍包含哪些對象?",
        "違反時的罰則規定為何?",
    ]


def test_generate_questions_strips_and_drops_blank_lines():
    canned = "  第一題應涵蓋什麼?  \n\n   \n第二題的依據為何?\n"
    llm = FakeLLM([canned])

    result = generate_questions("內容", "admin", llm)

    assert result == ["第一題應涵蓋什麼?", "第二題的依據為何?"]


def test_generate_questions_empty_response_returns_empty_list():
    llm = FakeLLM(["   \n\n  \n"])

    result = generate_questions("內容", "exam", llm)

    assert result == []


def test_generate_questions_calls_llm_exactly_once():
    # FakeLLM 依序 pop:只放一顆 canned。若函式呼叫超過一次,
    # 第二次 pop 會 IndexError;故「不炸」即證明恰一次呼叫。
    llm = FakeLLM(["唯一一題?"])

    result = generate_questions("內容", "law", llm)

    assert result == ["唯一一題?"]
    # 佇列已被唯一一次呼叫清空,再呼叫即 IndexError → 反證只呼叫過一次
    with pytest.raises(IndexError):
        llm.complete([{"role": "user", "content": "probe"}])


def test_generate_questions_grok_error_propagates():
    from note_filler.llm import GrokClient

    def fake_complete(*args, **kw):
        raise RuntimeError("grok transport failure")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(GrokClient, "complete", fake_complete)
    with pytest.raises(RuntimeError, match="grok transport failure"):
        generate_questions("個資法筆記", "law", GrokClient())
    monkeypatch.undo()


@pytest.mark.integration
@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")
def test_generate_questions_real_grok():
    from note_filler.llm import GrokClient

    llm = GrokClient()  # base_url=http://127.0.0.1:8318/v1, model="grok-4.3"
    note = (
        "個人資料保護法規範公務機關與非公務機關對個人資料之蒐集、處理及利用,"
        "並要求特定情形須告知當事人並取得同意。"
    )

    result = generate_questions(note, "law", llm)

    assert isinstance(result, list)
    assert len(result) >= 1
    assert all(isinstance(q, str) and q.strip() for q in result)
    # 合約:回傳為換行切割後的乾淨清單,不應殘留 JSON 括號等結構符號
    assert not any(q.strip().startswith(("[", "{")) for q in result)
