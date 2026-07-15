# tests/test_law_search.py
# -*- coding: utf-8 -*-
"""Q2:retrieve/law_search.py 的 search_law_sources 驗收。"""
import datetime
from pathlib import Path

import pytest

from note_filler.gap import Gap
from note_filler.llm import FakeLLM
from note_filler.knowledge.law_lookup import LawLookup
from note_filler.retrieve.models import Source
from note_filler.retrieve.law_search import search_law_sources

LAW_DB = Path(__file__).resolve().parents[1] / "data" / "law_index.db"


def _gap() -> Gap:
    return Gap(
        question="行政處分附加附款的容許界限與種類為何?",
        status="missing",
        reason="原稿未涵蓋",
    )


@pytest.mark.skipif(not LAW_DB.exists(), reason="缺 data/law_index.db")
def test_search_law_sources_returns_level_A_law_articles():
    law = LawLookup(str(LAW_DB))
    llm = FakeLLM(['{"keyword": "附款", "law_name": "行政程序法"}'])

    out = search_law_sources(_gap(), llm, law, limit=4)

    assert out, "應至少查到一條法條"
    assert all(isinstance(s, Source) for s in out)
    assert all(s.level == "A" for s in out)
    # title 形如 《行政程序法》第93條
    assert all(s.title.startswith("《行政程序法》第") and s.title.endswith("條") for s in out)
    # url 含 pcode
    assert all("pcode=" in s.url and s.url.split("pcode=")[1] for s in out)
    # content = 法條原文,非空
    assert all(s.content.strip() for s in out)
    # id 形如 law:<pcode>:<article_no>
    assert all(s.id.startswith("law:") and s.id.count(":") == 2 for s in out)
    # distance 依序 0.1/0.2/...
    assert [round(s.distance, 1) for s in out] == [round(0.1 * (i + 1), 1) for i in range(len(out))]
    # fetched_date = 今天 ISO;doc_date=None
    today = datetime.date.today().isoformat()
    assert all(s.fetched_date == today and s.doc_date is None for s in out)
    # 至少命中第93條(附款主條)
    assert any(s.title == "《行政程序法》第93條" for s in out)


@pytest.mark.skipif(not LAW_DB.exists(), reason="缺 data/law_index.db")
def test_search_law_sources_accepts_plain_keyword_response():
    """LLM 只回純關鍵詞(非 JSON)也要能運作,law_name 視為 None。"""
    law = LawLookup(str(LAW_DB))
    llm = FakeLLM(["附款"])

    out = search_law_sources(_gap(), llm, law, limit=3)

    assert out
    assert all(s.level == "A" for s in out)
    assert len(out) <= 3


def test_search_law_sources_uses_single_llm_call_and_empty_on_no_hit():
    """無命中回空 list;只呼叫一次 llm.complete。"""
    class _EmptyLaw:
        def __init__(self):
            self.calls = []

        def search_articles(self, keyword, limit=5, law_name=None):
            self.calls.append((keyword, limit, law_name))
            return []

    law = _EmptyLaw()
    llm = FakeLLM(['{"keyword": "不存在關鍵詞", "law_name": null}'])

    out = search_law_sources(_gap(), llm, law, limit=4)

    assert out == []
    assert len(llm.calls) == 1
    assert law.calls == [("不存在關鍵詞", 4, None)]


# --- 多關鍵詞 union（B）------------------------------------------------------

class _RecordingLaw:
    """依 keyword 回不同 rows,並記錄每次呼叫參數。"""

    def __init__(self, table: dict[str, list[dict]]):
        self.table = table
        self.calls: list[tuple[str, int, str | None]] = []

    def search_articles(self, keyword, limit=5, law_name=None):
        self.calls.append((keyword, limit, law_name))
        return list(self.table.get(keyword, []))


def _r(pcode: str, no: str) -> dict:
    return {"pcode": pcode, "law_name": "行政程序法", "article_no": no,
            "article_text": f"第{no}條全文"}


def test_search_law_sources_unions_multiple_keywords_dedup_and_order():
    law = _RecordingLaw({
        "聽證": [_r("A", "102"), _r("A", "107")],
        "陳述意見": [_r("A", "107"), _r("A", "109")],  # 107 與聽證重複
    })
    llm = FakeLLM(['{"keywords": ["聽證", "陳述意見"], "law_name": "行政程序法"}'])

    out = search_law_sources(_gap(), llm, law)

    # union、去重(107 只一次)、保序(聽證命中在前)
    assert [s.title for s in out] == [
        "《行政程序法》第102條", "《行政程序法》第107條", "《行政程序法》第109條",
    ]
    assert all(s.level == "A" for s in out)
    # 每個 keyword 都以預設 limit=25 呼叫
    assert law.calls == [("聽證", 25, "行政程序法"), ("陳述意見", 25, "行政程序法")]


def test_search_law_sources_backward_compat_single_keyword():
    law = _RecordingLaw({"附款": [_r("A", "93")]})
    llm = FakeLLM(['{"keyword": "附款", "law_name": "行政程序法"}'])

    out = search_law_sources(_gap(), llm, law)

    assert [s.title for s in out] == ["《行政程序法》第93條"]
    assert law.calls == [("附款", 25, "行政程序法")]


def test_search_law_sources_non_json_treated_as_single_keyword():
    law = _RecordingLaw({"附款": [_r("A", "93")]})
    llm = FakeLLM(["附款"])

    out = search_law_sources(_gap(), llm, law)

    assert [s.title for s in out] == ["《行政程序法》第93條"]
    assert law.calls == [("附款", 25, None)]


def test_search_law_sources_empty_keywords_returns_empty():
    law = _RecordingLaw({})
    llm = FakeLLM(['{"keywords": [], "law_name": null}'])

    out = search_law_sources(_gap(), llm, law)

    assert out == []
    assert law.calls == []  # 無關鍵詞不查
