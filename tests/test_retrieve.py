# tests/test_retrieve.py
import os

import pytest

from note_filler.gap import Gap
from note_filler.llm import FakeLLM
from note_filler.retrieve.models import Source
from note_filler.retrieve import retrieve_for_gap, _LEVEL_RANK


class FakeTwinkle:
    """模擬 TwinkleClient.search;記錄呼叫參數,回傳 canned Source(Level B 為主)。"""
    def __init__(self, responses: list[Source]):
        self.responses = responses
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, n: int = 3) -> list[Source]:
        self.calls.append((query, n))
        return list(self.responses)  # 回副本,避免被排序就地改動


class FakeLaw:
    """模擬 LawLookup.search_articles;記錄呼叫參數,回固定條文列。"""
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.calls: list[tuple[str, int, str | None]] = []

    def search_articles(self, keyword: str, limit: int = 5, law_name: str | None = None):
        self.calls.append((keyword, limit, law_name))
        return list(self.rows)


def _src(sid: str, level: str, distance: float) -> Source:
    return Source(
        id=sid, title=f"title-{sid}", url=f"https://twinkle/{sid}",
        level=level, content=f"官方一手記錄全文 {sid}",
        fetched_date="2026-07-15", doc_date=None, distance=distance,
    )


def _row(pcode: str, article_no: str) -> dict:
    return {
        "pcode": pcode, "law_name": "行政程序法",
        "article_no": article_no, "article_text": f"第{article_no}條全文",
    }


def test_retrieve_for_gap_law_domain_puts_level_A_before_B():
    gap = Gap(question="行政處分附款的容許界限為何?", status="missing", reason="原稿未涵蓋")
    # twinkle 回 Level B(其中 b2 distance=0.1 比法條 A 還小,用來證明「級別壓過 distance」)
    twinkle = FakeTwinkle([_src("b1", "B", 0.3), _src("b2", "B", 0.1)])
    law = FakeLaw([_row("A0030055", "93"), _row("A0030055", "94")])
    llm = FakeLLM(['{"keyword": "附款", "law_name": "行政程序法"}'])

    out = retrieve_for_gap(gap, "law", twinkle, law, llm)

    # 法條(A,distance 0.1/0.2)整批在 twinkle(B)之前;級內 distance 升序
    assert [s.level for s in out] == ["A", "A", "B", "B"]
    assert [s.id for s in out] == ["law:A0030055:93", "law:A0030055:94", "b2", "b1"]
    # 法條與 twinkle 各呼叫一次,query/keyword 正確
    assert law.calls == [("附款", 25, "行政程序法")]
    assert twinkle.calls[0][0] == gap.question
    assert len(llm.calls) == 1


def test_retrieve_for_gap_other_domain_uses_web_not_twinkle(monkeypatch):
    gap = Gap(question="OWASP Top 10 是什麼?", status="missing", reason="")
    twinkle = FakeTwinkle([_src("b1", "B", 0.1)])
    law = FakeLaw([_row("X", "1")])
    llm = FakeLLM([])  # search_web_sources 被 fake 掉,不會真的 pop

    web_calls: list = []

    def fake_web(g, l):
        web_calls.append((g, l))
        return [_src("web1", "C", 0.2)]

    # other 領域:只加掛開放網路來源(web),不打 twinkle(立法院議案為噪音)
    monkeypatch.setattr("note_filler.retrieve.search_web_sources", fake_web)
    out = retrieve_for_gap(gap, "other", twinkle, law, llm)

    assert web_calls == [(gap, llm)]       # 有打 web
    assert twinkle.calls == []             # 不打 twinkle
    assert law.calls == []                 # 非法制領域不查法條
    assert [s.id for s in out] == ["web1"]


@pytest.mark.integration
def test_retrieve_for_gap_real_twinkle_smoke():
    token = os.environ.get("TWINKLE_HUB_TOKEN")
    if os.environ.get("GOV_AI_ENABLE_TWINKLE_MCP") != "1" or not token:
        pytest.skip("需 GOV_AI_ENABLE_TWINKLE_MCP=1 且設 TWINKLE_HUB_TOKEN")

    from pathlib import Path

    from note_filler.knowledge.law_lookup import LawLookup
    from note_filler.llm import GrokClient
    from note_filler.retrieve.twinkle import TwinkleClient

    law_db = Path(__file__).resolve().parents[1] / "data" / "law_index.db"
    gap = Gap(question="行政處分附款的容許界限為何?", status="missing", reason="")
    twinkle = TwinkleClient(token=token)
    law = LawLookup(str(law_db)) if law_db.exists() else None
    llm = GrokClient() if law is not None else None

    out = retrieve_for_gap(gap, "law", twinkle, law, llm)

    assert all(isinstance(s, Source) for s in out)
    assert all(s.level in ("A", "B") for s in out)  # MVP 只產 A/B
    # 排序不變式:整串 (rank, distance) 已升序
    keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
    assert keys == sorted(keys)
