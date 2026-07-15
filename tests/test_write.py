# tests/test_write.py
# -*- coding: utf-8 -*-
"""Q3:write.py 的 write_supplement / WrittenSupplement 驗收。"""
from note_filler.gap import Gap
from note_filler.llm import FakeLLM
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
