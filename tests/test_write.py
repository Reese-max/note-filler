# tests/test_write.py
# -*- coding: utf-8 -*-
"""Q3:write.py 的 write_supplement / WrittenSupplement 驗收。"""
import socket

import pytest

from note_filler.gap import Gap
from note_filler.llm import FakeLLM, GrokClient
from note_filler.retrieve.models import Source
from note_filler.write import WrittenSupplement, write_supplement


def _gap() -> Gap:
    return Gap(question="行政處分附款的種類為何?", status="missing", reason="原稿未涵蓋")


def _sources() -> list[Source]:
    return [
        Source(id="law:A:93", title="《行政程序法》第93條", url="u1", level="A",
               content="行政機關作成行政處分有裁量權時,得為附款。", fetched_date="2026-07-15",
               doc_date=None, distance=0.1),
        Source(id="law:A:94", title="《行政程序法》第94條", url="u2", level="A",
               content="附款不得違背行政處分之目的。", fetched_date="2026-07-15",
               doc_date=None, distance=0.2),
    ]


def test_used_source_ids_from_markers():
    srcs = _sources()
    llm = FakeLLM(["附款須有裁量權[^1],且不得違背處分目的[^2]。"])
    out = write_supplement(_gap(), srcs, llm)
    assert isinstance(out, WrittenSupplement)
    assert out.used_source_ids == [srcs[0].id, srcs[1].id]
    assert out.text == "附款須有裁量權[^1],且不得違背處分目的[^2]。"
    assert len(llm.calls) == 1


def test_pending_evidence_when_insufficient():
    llm = FakeLLM(["【待補證】現有來源未提及附款撤回的效果。"])
    out = write_supplement(_gap(), _sources(), llm)
    assert out.text.startswith("【待補證】")
    assert out.used_source_ids == []


def test_out_of_range_marker_removed_and_not_used():
    srcs = _sources()
    llm = FakeLLM(["附款須有裁量權[^1],另有一說[^9]參見。"])
    out = write_supplement(_gap(), srcs, llm)
    assert out.used_source_ids == [srcs[0].id]
    assert "[^9]" not in out.text
    assert "[^1]" in out.text


def _grok_reachable(host: str = "127.0.0.1", port: int = 8318) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


@pytest.mark.integration
@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")
def test_write_supplement_real_grok_grounded_output():
    """固定來源、只真打 writer,補足昂貴 e2e 的第二個 grounded 觀察點。"""

    class _Grok0(GrokClient):
        def complete(self, messages, **kw):
            kw.setdefault("temperature", 0)
            return super().complete(messages, **kw)

    sources = _sources()
    gap = Gap(
        question="行政機關何時得為附款,附款受何限制?",
        status="missing",
        reason="原稿未涵蓋",
    )
    out = write_supplement(gap, sources, _Grok0())

    assert not out.text.startswith("【待補證】")
    assert "[^" in out.text
    assert out.used_source_ids
    assert set(out.used_source_ids) <= {source.id for source in sources}
