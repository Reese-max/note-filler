import socket

import pytest

from note_filler.gap import Gap, detect_gaps
from note_filler.llm import FakeLLM


def _grok_reachable(host: str = "127.0.0.1", port: int = 8318) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def test_detect_gaps_keeps_only_partial_and_missing():
    """LLM 回一個 JSON 陣列;covered 要被濾掉,只留 partial+missing。"""
    canned = """[
      {"question": "甲問題", "status": "covered", "reason": "已完整說明"},
      {"question": "乙問題", "status": "partial", "reason": "只提到一半"},
      {"question": "丙問題", "status": "missing", "reason": "完全沒提"}
    ]"""
    llm = FakeLLM([canned])
    gaps = detect_gaps(["甲問題", "乙問題", "丙問題"], "某段筆記文字", llm)
    assert [g.status for g in gaps] == ["partial", "missing"]
    assert [g.question for g in gaps] == ["乙問題", "丙問題"]
    assert all(isinstance(g, Gap) for g in gaps)
    assert all(g.reason for g in gaps)


def test_detect_gaps_calls_llm_exactly_once():
    """FakeLLM 只餵一個回應;若 detect_gaps 多次呼叫會把 responses pop 空 → IndexError。"""
    llm = FakeLLM(['[{"question":"q","status":"missing","reason":"r"}]'])
    gaps = detect_gaps(["q1", "q2", "q3"], "筆記", llm)
    assert [gap.question for gap in gaps] == ["q", "q1", "q2", "q3"]
    assert all(gap.status == "missing" for gap in gaps)


def test_detect_gaps_parse_failure_marks_all_missing():
    """JSON 解析失敗 → 全部 questions 保守標 missing,reason 記解析失敗。"""
    llm = FakeLLM(["抱歉這不是 JSON"])
    qs = ["q1", "q2"]
    gaps = detect_gaps(qs, "筆記", llm)
    assert [g.status for g in gaps] == ["missing", "missing"]
    assert [g.question for g in gaps] == qs
    assert all("解析失敗" in g.reason for g in gaps)


def test_detect_gaps_non_array_json_also_fallbacks():
    """合法 JSON 但不是陣列(dict) → 同樣走保守 fallback。"""
    llm = FakeLLM(['{"status": "missing"}'])
    gaps = detect_gaps(["q1"], "筆記", llm)
    assert [g.status for g in gaps] == ["missing"]
    assert "解析失敗" in gaps[0].reason


def test_detect_gaps_strips_code_fence():
    """LLM 常包 ```json 圍欄,需能剝除後仍解析。"""
    canned = '```json\n[{"question":"q","status":"partial","reason":"半"}]\n```'
    llm = FakeLLM([canned])
    gaps = detect_gaps(["q"], "筆記", llm)
    assert len(gaps) == 1 and gaps[0].status == "partial"


def test_detect_gaps_empty_questions_short_circuits():
    """空問題清單直接回空,不呼叫 LLM。"""
    llm = FakeLLM([])  # 不應被 pop
    assert detect_gaps([], "筆記", llm) == []


def test_detect_gaps_grok_error_propagates():
    from note_filler.llm import GrokClient

    def fake_complete(*args, **kw):
        raise RuntimeError("grok transport failure")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(GrokClient, "complete", fake_complete)
    with pytest.raises(RuntimeError, match="grok transport failure"):
        detect_gaps(["一個問題"], "筆記文字", GrokClient())
    monkeypatch.undo()


@pytest.mark.integration
@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")
def test_detect_gaps_real_grok():
    """真打 grok(http://127.0.0.1:8318/v1, grok-4.3):
    給一段只談行政處分定義的筆記 + 一題明顯未涵蓋的問題,
    驗回傳結構正確且所有 status 皆為缺口(partial/missing)。"""
    from note_filler.llm import GrokClient

    llm = GrokClient()  # base_url/model 用鎖定預設值
    note = "行政程序法第92條規定,行政處分係行政機關就公法上具體事件所為之對外直接發生法律效果之單方行政行為。"
    questions = [
        "行政處分的法定定義為何?",
        "行政罰鍰的裁量基準與上限為何?",  # 筆記完全沒提 → 應 missing
    ]
    gaps = detect_gaps(questions, note, llm)

    assert isinstance(gaps, list)
    assert all(isinstance(g, Gap) for g in gaps)
    assert all(g.status in ("partial", "missing") for g in gaps)  # 只回缺口
    # 第二題明顯未涵蓋,至少要出現在缺口清單
    assert any("裁量基準" in g.question or "罰鍰" in g.question for g in gaps)


@pytest.mark.integration
@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")
def test_detect_gaps_real_grok_semantic_matrix():
    """真模型須排除明顯 covered 題,並保留明顯 missing 題。"""
    from note_filler.llm import GrokClient

    covered = "行政處分的法定定義為何?"
    missing = "行政罰鍰的裁量基準與上限為何?"
    note = (
        "行政程序法第92條規定,行政處分係行政機關就公法上具體事件所為之"
        "對外直接發生法律效果之單方行政行為。"
    )

    gaps = detect_gaps([covered, missing], note, GrokClient())
    questions = {gap.question for gap in gaps}

    assert covered not in questions
    assert missing in questions
