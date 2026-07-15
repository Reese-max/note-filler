# tests/test_web.py -- 全部免網路,注入 fake search/fetch
import pytest

from note_filler.gap import Gap
from note_filler.llm import FakeLLM
from note_filler.retrieve import retrieve_for_gap
from note_filler.retrieve.models import Source
from note_filler.retrieve.web import search_web_sources

GAP = Gap(question="OWASP Top 10 的 SSRF 是什麼?", status="missing", reason="原稿未涵蓋")

# 夠長(>200 字)的假全文,兩頁內容不同以驗證非 snippet
FULL_C = "官方一手全文 C。" + "SSRF 是伺服器端請求偽造。" * 30
FULL_D = "技術部落格整理 D。" + "SSRF 防禦與案例說明。" * 30


def _fake_search(*hrefs_titles):
    def search(query, max_results):
        return [{"title": t, "href": h} for t, h in hrefs_titles]
    return search


def _fake_fetch(mapping):
    def fetch(url):
        return mapping.get(url)
    return fetch


def test_two_pages_graded_c_and_d():
    search = _fake_search(("OWASP 官方", "https://owasp.org/ssrf"), ("某部落格", "https://blog.dev/ssrf"))
    fetch = _fake_fetch({"https://owasp.org/ssrf": FULL_C, "https://blog.dev/ssrf": FULL_D})
    llm = FakeLLM([
        "OWASP SSRF 定義",  # query 抽取
        '{"level":"C","doc_date":"2024-01-01","reason":"官方"}',
        '{"level":"D","doc_date":null,"reason":"部落格"}',
    ])

    out = search_web_sources(GAP, llm, search=search, fetch=fetch)

    assert [s.level for s in out] == ["C", "D"]
    assert all(isinstance(s, Source) for s in out)
    # content 是 fetch 全文,絕非 DDG snippet
    assert out[0].content == FULL_C
    assert out[1].content == FULL_D
    assert out[0].url == "https://owasp.org/ssrf"
    assert out[0].id.startswith("web:")
    assert out[0].fetched_date  # 有值
    assert out[0].doc_date == "2024-01-01"
    assert out[1].doc_date is None
    assert out[0].distance < out[1].distance  # 列舉序遞增


def test_drop_page_excluded():
    search = _fake_search(
        ("A", "https://a"), ("B", "https://b"), ("C", "https://c"),
    )
    fetch = _fake_fetch({"https://a": FULL_C, "https://b": FULL_D, "https://c": FULL_C})
    llm = FakeLLM([
        "query",
        '{"level":"C","doc_date":null,"reason":"官方"}',
        '{"level":"drop","doc_date":null,"reason":"內容農場"}',
        '{"level":"D","doc_date":null,"reason":"二手"}',
    ])

    out = search_web_sources(GAP, llm, search=search, fetch=fetch)

    assert [s.level for s in out] == ["C", "D"]  # 中間 drop 被排除
    assert [s.url for s in out] == ["https://a", "https://c"]


def test_fetch_none_skipped():
    search = _fake_search(("A", "https://a"), ("B", "https://b"))
    fetch = _fake_fetch({"https://a": None, "https://b": FULL_D})
    llm = FakeLLM(["query", '{"level":"D","doc_date":null,"reason":"二手"}'])

    out = search_web_sources(GAP, llm, search=search, fetch=fetch)

    assert [s.url for s in out] == ["https://b"]  # None 頁跳過,只剩 b


def test_too_short_fulltext_skipped():
    search = _fake_search(("A", "https://a"))
    fetch = _fake_fetch({"https://a": "太短"})  # <200 字
    llm = FakeLLM(["query"])  # 不應進到分級

    out = search_web_sources(GAP, llm, search=search, fetch=fetch)

    assert out == []


def test_search_exception_degrades_to_empty():
    def boom(query, max_results):
        raise RuntimeError("network down")

    llm = FakeLLM(["query"])
    out = search_web_sources(GAP, llm, search=boom, fetch=_fake_fetch({}))

    assert out == []  # 降級,不拋錯


def test_content_truncated_with_note():
    long_text = "字" * 3000  # >2500
    search = _fake_search(("A", "https://a"))
    fetch = _fake_fetch({"https://a": long_text})
    llm = FakeLLM(["query", '{"level":"C","doc_date":null,"reason":"官方"}'])

    out = search_web_sources(GAP, llm, search=search, fetch=fetch)

    assert len(out) == 1
    assert out[0].content.startswith("字" * 2500)
    assert "# ponytail" in out[0].content  # 截斷註記


def test_query_extraction_falls_back_to_question():
    # llm 抽取拋錯(無回應)→ 退回 gap.question 當 query
    captured = {}

    def search(query, max_results):
        captured["query"] = query
        return []

    out = search_web_sources(GAP, FakeLLM([]), search=search, fetch=_fake_fetch({}))
    assert out == []
    assert captured["query"] == GAP.question


# ---- 接線:retrieve_for_gap ----
class _FakeTwinkle:
    def search(self, query, n=3):
        return []


def test_retrieve_other_domain_calls_web(monkeypatch):
    called = {}

    def fake_web(gap, llm):
        called["hit"] = True
        return [Source("web:x", "t", "https://x", "C", "全文", "2026-07-16", None, 0.1)]

    monkeypatch.setattr("note_filler.retrieve.search_web_sources", fake_web)
    out = retrieve_for_gap(GAP, "other", _FakeTwinkle(), law=None, llm=FakeLLM([]))

    assert called.get("hit") is True
    assert [s.id for s in out] == ["web:x"]


def test_retrieve_law_domain_does_not_call_web(monkeypatch):
    def boom_web(gap, llm):
        raise AssertionError("law 領域不該呼叫 web")

    monkeypatch.setattr("note_filler.retrieve.search_web_sources", boom_web)

    class _FakeLaw:
        def search_articles(self, keyword, limit=5, law_name=None):
            return []

    # law 領域:llm 只被 law_search 用;web 不得被呼叫(呼叫即 AssertionError)
    retrieve_for_gap(
        GAP, "law", _FakeTwinkle(), law=_FakeLaw(),
        llm=FakeLLM(['{"keyword":"SSRF","law_name":null}']),
    )
