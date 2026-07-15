# tests/test_retrieve.py
import os

import pytest

from note_filler.gap import Gap
from note_filler.retrieve.models import Source
from note_filler.retrieve import retrieve_for_gap


class FakeTwinkle:
    """模擬 TwinkleClient.search;記錄呼叫參數,回傳 canned Source。"""
    def __init__(self, responses: list[Source]):
        self.responses = responses
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, n: int = 3) -> list[Source]:
        self.calls.append((query, n))
        return list(self.responses)  # 回副本,避免被排序就地改動


def _src(sid: str, level: str, distance: float) -> Source:
    return Source(
        id=sid, title=f"title-{sid}", url=f"https://twinkle/{sid}",
        level=level, content=f"官方一手記錄全文 {sid}",
        fetched_date="2026-07-15", doc_date=None, distance=distance,
    )


def test_retrieve_for_gap_sorts_A_before_B_then_distance():
    gap = Gap(question="勞動基準法第84條之1責任制範圍為何?", status="missing", reason="原稿未涵蓋")
    # 刻意亂序;注意 b2 distance=0.1 比所有 A 都小,用來證明「級別壓過 distance」
    twinkle = FakeTwinkle([
        _src("b1", "B", 0.3),
        _src("a1", "A", 0.7),
        _src("a2", "A", 0.2),
        _src("b2", "B", 0.1),
    ])

    out = retrieve_for_gap(gap, "law", twinkle)

    # A 先(級內 distance 升序):a2(0.2)→a1(0.7);再 B:b2(0.1)→b1(0.3)
    assert [s.id for s in out] == ["a2", "a1", "b2", "b1"]
    # query 必須用 gap.question
    assert twinkle.calls[0][0] == gap.question


def test_retrieve_for_gap_skips_non_mvp_domain():
    gap = Gap(question="這題超綱", status="missing", reason="")
    twinkle = FakeTwinkle([_src("a1", "A", 0.1)])

    out = retrieve_for_gap(gap, "other", twinkle)

    assert out == []
    assert twinkle.calls == []  # 非 MVP 領域完全不打 twinkle


from note_filler.retrieve import _LEVEL_RANK  # 排序權重,重用以驗不變式


@pytest.mark.integration
def test_retrieve_for_gap_real_twinkle_smoke():
    token = os.environ.get("TWINKLE_HUB_TOKEN")
    if os.environ.get("GOV_AI_ENABLE_TWINKLE_MCP") != "1" or not token:
        pytest.skip("需 GOV_AI_ENABLE_TWINKLE_MCP=1 且設 TWINKLE_HUB_TOKEN")

    from note_filler.retrieve.twinkle import TwinkleClient

    gap = Gap(question="勞動基準法 責任制 工時", status="missing", reason="")
    twinkle = TwinkleClient(token=token)

    out = retrieve_for_gap(gap, "law", twinkle)

    assert all(isinstance(s, Source) for s in out)
    assert all(s.level in ("A", "B") for s in out)  # MVP 只產 A/B
    # 排序不變式:整串 (rank, distance) 已升序
    keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
    assert keys == sorted(keys)
