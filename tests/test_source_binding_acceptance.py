"""驗收測試：生成結果中每個論點對應到至少一個來源，且來源集合不重複遺漏。
涵蓋一對一與一對多綁定情境。

直接驗證 assemble_correction 與 write_supplement 形成的
Segment.sources / Segment.traceability / Segment.source_id 之間的不變式。

每個 supplement segment 的來源不變式：
  (a) 完整性：所有 used_source_ids 都有對應 Source 物件在 segment.sources
  (b) 無重複：segment.sources 內無重複 source.id
  (c) 無多餘：segment.sources 中的來源皆有在 used_source_ids 中
  (d) 追溯一致性：traceability 與 sources 一一對應
"""
from __future__ import annotations

import pytest

from note_filler.correction import assemble_correction
from note_filler.gap import Gap
from note_filler.parse import Document, Paragraph
from note_filler.retrieve.models import Source
from note_filler.verify import cross_validate
from note_filler.write import WrittenSupplement


# ---- 輔助函式 ---------------------------------------------------------------

def _doc():
    return Document(
        source_path="input/note.txt",
        paragraphs=(Paragraph(0, "原稿逐字保留。"),),
        full_text="原稿逐字保留。",
    )


def _source(id: str, title: str, level: str = "A") -> Source:
    return Source(
        id=id, title=title, url=None, level=level,
        content=f"{title} 內容", fetched_date="2026-07-24",
        doc_date=None, distance=0.5,
    )


def _assert_source_binding_invariants(segments) -> None:
    """對每個 supplement segment 驗證來源綁定不變式。"""
    for i, seg in enumerate(segments):
        if seg.type != "supplement":
            continue
        if not seg.sources:
            # 無來源段不需驗證綁定
            continue

        # (a) 無重複 id
        ids = [s.id for s in seg.sources]
        assert len(ids) == len(set(ids)), (
            f"segment[{i}] sources 含重複 id: {ids}"
        )

        # (b) traceability 與 sources 一一對應
        expected_trace = [{"kind": "source", "id": s.id} for s in seg.sources]
        assert seg.traceability == expected_trace, (
            f"segment[{i}] traceability 與 sources 不對應: "
            f"trace={[[t['kind'], t['id']] for t in seg.traceability]}, "
            f"expected={expected_trace}"
        )

        # (c) source_id 格式與內容正確
        expected_sid = f"sources:{','.join(ids)}"
        assert seg.source_id == expected_sid, (
            f"segment[{i}] source_id 應為 {expected_sid!r}, 實際 {seg.source_id!r}"
        )

        # (d) 所有 source 都有合法 level
        assert all(s.level in ("A", "B", "C", "D") for s in seg.sources), (
            f"segment[{i}] 含不合法的 level"
        )


def _assert_used_ids_covered(segment, used_ids: list[str]) -> None:
    """斷言 used_source_ids 中的每個 id 都在 segment.sources 且有對應 traceability。"""
    source_ids = {s.id for s in segment.sources}
    trace_ids = {t["id"] for t in segment.traceability if t.get("kind") == "source"}
    for uid in used_ids:
        assert uid in source_ids, (
            f"used_source_id {uid!r} 不在 segment.sources 中"
        )
        assert uid in trace_ids, (
            f"used_source_id {uid!r} 不在 segment.traceability 中"
        )


def _assert_no_extra_sources(segment, used_ids: list[str]) -> None:
    """斷言 segment.sources 中沒有未在 used_source_ids 出現的來源。"""
    for s in segment.sources:
        assert s.id in used_ids, (
            f"segment.sources 中有未使用的來源: {s.id!r}"
        )


# ---- 一對一綁定：每個 supplement 段對應剛好一個來源 -----------------------

def test_one_to_one_single_source():
    """一個 gap、一個來源、一個 [^1] 標記 → 1:1 綁定。"""
    src = _source("law:92", "行政程序法第 92 條")
    gap = Gap("行政處分之定義？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("定義參照[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    seg = product.segments[1]
    assert seg.type == "supplement"
    assert len(seg.sources) == 1
    assert seg.sources[0].id == src.id
    assert len(seg.traceability) == 1
    assert seg.traceability[0] == {"kind": "source", "id": src.id}
    assert seg.source_id == "sources:law:92"
    _assert_source_binding_invariants(product.segments)


def test_one_to_one_two_separate_gaps():
    """兩個獨立 gap，各自綁定一個來源 → 每段都是 1:1。"""
    src_a = _source("law:92", "行政程序法第 92 條")
    src_b = _source("law:93", "行政程序法第 93 條")
    gap_a = Gap("定義？", "missing", "未說明")
    gap_b = Gap("附款？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap_a, gap_b],
        {gap_a.question: [src_a], gap_b.question: [src_b]},
        {
            gap_a.question: WrittenSupplement("定義[^1]。", [src_a.id]),
            gap_b.question: WrittenSupplement("附款[^1]。", [src_b.id]),
        },
        {
            gap_a.question: cross_validate(gap_a.question, [src_a]),
            gap_b.question: cross_validate(gap_b.question, [src_b]),
        },
    )
    assert len(product.segments) == 3  # 1 original + 2 supplement
    seg_a, seg_b = product.segments[1], product.segments[2]
    assert seg_a.type == seg_b.type == "supplement"
    assert len(seg_a.sources) == len(seg_b.sources) == 1
    assert seg_a.sources[0].id == src_a.id
    assert seg_b.sources[0].id == src_b.id
    assert seg_a.source_id == "sources:law:92"
    assert seg_b.source_id == "sources:law:93"
    _assert_source_binding_invariants(product.segments)


# ---- 一對多綁定：一個 supplement 段引用多個來源 ---------------------------

def test_one_to_many_three_sources():
    """一個 gap 引用三個來源 → 1:3 綁定。"""
    srcs = [
        _source("law:92", "行政程序法第 92 條"),
        _source("law:93", "行政程序法第 93 條", level="B"),
        _source("web:abc", "官方函釋", level="C"),
    ]
    gap = Gap("附款相關規定？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: srcs},
        {gap.question: WrittenSupplement("三源[^1][^2][^3]。", [s.id for s in srcs])},
        {gap.question: cross_validate(gap.question, srcs)},
    )
    seg = product.segments[1]
    assert seg.type == "supplement"
    assert len(seg.sources) == 3
    assert [s.id for s in seg.sources] == ["law:92", "law:93", "web:abc"]
    assert len(seg.traceability) == 3
    assert seg.traceability == [
        {"kind": "source", "id": "law:92"},
        {"kind": "source", "id": "law:93"},
        {"kind": "source", "id": "web:abc"},
    ]
    assert seg.source_id == "sources:law:92,law:93,web:abc"
    _assert_source_binding_invariants(product.segments)


def test_one_to_many_with_one_to_one_in_same_doc():
    """混合情境：gapA 一對一、gapB 一對多。"""
    src_a = _source("law:92", "行政程序法第 92 條")
    src_b1 = _source("law:93", "行政程序法第 93 條")
    src_b2 = _source("law:94", "行政程序法第 94 條")
    gap_a = Gap("定義？", "missing", "未說明")
    gap_b = Gap("附款限制？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap_a, gap_b],
        {gap_a.question: [src_a], gap_b.question: [src_b1, src_b2]},
        {
            gap_a.question: WrittenSupplement("定義[^1]。", [src_a.id]),
            gap_b.question: WrittenSupplement("限制[^1][^2]。", [src_b1.id, src_b2.id]),
        },
        {
            gap_a.question: cross_validate(gap_a.question, [src_a]),
            gap_b.question: cross_validate(gap_b.question, [src_b1, src_b2]),
        },
    )
    assert len(product.segments) == 3
    seg_a, seg_b = product.segments[1], product.segments[2]
    assert seg_a.source_id == "sources:law:92"
    assert seg_b.source_id == "sources:law:93,law:94"
    assert len(seg_a.sources) == 1
    assert len(seg_b.sources) == 2
    _assert_source_binding_invariants(product.segments)


# ---- 來源集合完整性：無遺漏 ------------------------------------------------

def test_no_omitted_source_all_used_ids_have_source_objects():
    """所有 used_source_ids 都在 segment.sources 中有對應 Source 物件。"""
    src = _source("law:92", "行政程序法第 92 條")
    gap = Gap("定義？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("定義[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    _assert_used_ids_covered(product.segments[1], [src.id])


def test_no_omitted_source_multiple_ids():
    """多個 used_source_ids 全數在 segment.sources 中有對應。"""
    srcs = [
        _source("law:92", "行政程序法第 92 條"),
        _source("law:93", "行政程序法第 93 條", level="B"),
        _source("law:94", "行政程序法第 94 條", level="B"),
    ]
    used = [s.id for s in srcs]
    gap = Gap("規定？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: srcs},
        {gap.question: WrittenSupplement("三源[^1][^2][^3]。", used)},
        {gap.question: cross_validate(gap.question, srcs)},
    )
    _assert_used_ids_covered(product.segments[1], used)


def test_partial_usage_no_omitted():
    """檢索了五個來源但只引用兩個 → 只 used 的兩筆有對應。"""
    srcs = [
        _source("law:92", "行政程序法第 92 條"),
        _source("law:93", "行政程序法第 93 條"),
        _source("law:94", "行政程序法第 94 條"),
        _source("web:abc", "官方函釋", level="C"),
        _source("web:xyz", "實務見解", level="D"),
    ]
    used_ids = ["law:92", "law:94"]
    used_sources = [s for s in srcs if s.id in used_ids]
    gap = Gap("定義？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: srcs},
        {gap.question: WrittenSupplement("兩源[^1][^2]。", used_ids)},
        {gap.question: cross_validate(gap.question, used_sources)},
    )
    seg = product.segments[1]
    assert len(seg.sources) == 2
    assert seg.sources[0].id == "law:92"
    assert seg.sources[1].id == "law:94"
    _assert_used_ids_covered(seg, used_ids)
    _assert_no_extra_sources(seg, used_ids)


# ---- 來源集合無多餘 ---------------------------------------------------------

def test_no_extra_sources_not_in_used():
    """segment.sources 不包含未被使用的來源 id。"""
    srcs = [
        _source("law:92", "行政程序法第 92 條"),
        _source("law:93", "行政程序法第 93 條"),
    ]
    used_ids = ["law:92"]  # 只引用了第一個
    used_sources = [s for s in srcs if s.id in used_ids]
    gap = Gap("定義？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: srcs},
        {gap.question: WrittenSupplement("定義[^1]。", used_ids)},
        {gap.question: cross_validate(gap.question, used_sources)},
    )
    seg = product.segments[1]
    assert len(seg.sources) == 1
    assert seg.sources[0].id == "law:92"
    _assert_no_extra_sources(seg, used_ids)


# ---- 來源集合無重複 ---------------------------------------------------------

def test_no_duplicate_sources():
    """segment.sources 無重複 source.id。"""
    src = _source("law:92", "行政程序法第 92 條")
    gap = Gap("定義？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: [src, src]},  # retrieved 有兩個相同 id 的 Source
        {gap.question: WrittenSupplement("定義[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    seg = product.segments[1]
    ids = [s.id for s in seg.sources]
    assert len(ids) == len(set(ids)), f"sources 含重複 id: {ids}"
    assert ids == [src.id]  # 應只保留一個


def test_no_duplicate_traceability():
    """segment.traceability 無重複條目。"""
    src = _source("law:92", "行政程序法第 92 條")
    gap = Gap("定義？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("定義[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    seg = product.segments[1]
    trace_ids = [t["id"] for t in seg.traceability]
    assert len(trace_ids) == len(set(trace_ids)), f"traceability 含重複 id: {trace_ids}"


# ---- 綁定不變式 x 多個 segment -----------------------------------------------

def test_all_supplement_segments_have_valid_binding():
    """所有 supplement segment 都滿足來源綁定不變式。"""
    srcs_a = [_source("law:92", "行政程序法第 92 條")]
    srcs_b = [
        _source("law:93", "行政程序法第 93 條"),
        _source("law:94", "行政程序法第 94 條", level="B"),
    ]
    gap_a = Gap("定義？", "missing", "未說明")
    gap_b = Gap("附款？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap_a, gap_b],
        {gap_a.question: srcs_a, gap_b.question: srcs_b},
        {
            gap_a.question: WrittenSupplement("定義[^1]。", [s.id for s in srcs_a]),
            gap_b.question: WrittenSupplement("附款限制[^1][^2]。", [s.id for s in srcs_b]),
        },
        {
            gap_a.question: cross_validate(gap_a.question, srcs_a),
            gap_b.question: cross_validate(gap_b.question, srcs_b),
        },
    )
    _assert_source_binding_invariants(product.segments)


def test_source_binding_survives_require_traceable_gate():
    """綁定不變式驗證後再通過 require_traceable_note_product 閘。"""
    from note_filler.pipeline import require_traceable_note_product
    src = _source("law:92", "行政程序法第 92 條")
    gap = Gap("定義？", "missing", "未說明")
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("定義[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    _assert_source_binding_invariants(product.segments)
    require_traceable_note_product(product, source="binding-acceptance")
