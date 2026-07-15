import json

import pytest

from note_filler.parse import Document, Paragraph
from note_filler.correction import CorrectionDoc, Segment
from note_filler.retrieve.models import Source
from note_filler.export import to_json, to_markdown


def _sample_doc() -> CorrectionDoc:
    original = Document(
        source_path="/tmp/note.docx",
        paragraphs=(Paragraph(idx=0, text="原文第一段。"),),
        full_text="原文第一段。",
    )
    src_a = Source(
        id="s1",
        title="行政程序法第92條",
        url="https://law.moj.gov.tw/LawClass/LawSingle.aspx?a=92",
        level="A",
        content="行政程序法第92條：本法所稱行政處分，係指……全文。",
        fetched_date="2026-07-01",
        doc_date="2005-12-28",
        distance=0.10,
    )
    src_b = Source(
        id="s2",
        title="立法院第11屆第1會期議案關係文書",
        url="https://ppg.ly.gov.tw/ppg/bills/1101/text",
        level="B",
        content="議案關係文書全文……",
        fetched_date="2026-07-02",
        doc_date=None,
        distance=0.30,
    )
    segments = [
        Segment(
            type="original",
            text="原文第一段。",
            anchor_idx=0,
            sources=[],
            confidence="verified",
        ),
        Segment(
            type="supplement",
            text="依行政程序法第92條，行政處分係指行政機關就公法上具體事件所為之決定。",
            anchor_idx=0,
            sources=[src_a, src_b],
            confidence="verified",
        ),
        Segment(
            type="supplement",
            text="關於施行細節仍待查證。",
            anchor_idx=0,
            sources=[],
            confidence="pending_evidence",
        ),
    ]
    return CorrectionDoc(original=original, segments=segments)


def test_to_json_serializes_segments() -> None:
    data = to_json(_sample_doc())

    assert data["source_path"] == "/tmp/note.docx"
    segs = data["segments"]
    assert len(segs) == 3

    # 原文段
    assert segs[0]["type"] == "original"
    assert segs[0]["text"] == "原文第一段。"
    assert segs[0]["sources"] == []

    # verified supplement，帶兩個來源，Level 保留
    assert segs[1]["type"] == "supplement"
    assert segs[1]["confidence"] == "verified"
    assert [s["level"] for s in segs[1]["sources"]] == ["A", "B"]
    assert segs[1]["sources"][0]["fetched_date"] == "2026-07-01"

    # pending_evidence supplement，sources 空(C6 不變式)
    assert segs[2]["confidence"] == "pending_evidence"
    assert segs[2]["sources"] == []

    # 整份可被 json 序列化(不丟例外)
    json.dumps(data, ensure_ascii=False)


def test_to_markdown_format_locked() -> None:
    md = to_markdown(_sample_doc())

    # 原文段原樣輸出
    assert "原文第一段。" in md

    # C3：supplement 段 "> 【補充】{text}" 後接 [^n]
    assert "> 【補充】依行政程序法第92條" in md
    assert (
        "> 【補充】依行政程序法第92條，行政處分係指行政機關就公法上具體事件所為之決定。[^1][^2]"
        in md
    )

    # C3：pending_evidence 段【補充】後加 ⚠待補證
    assert "> 【補充】⚠待補證 關於施行細節仍待查證。" in md
    assert "⚠待補證" in md

    # 文末參考區塊(來自 T11 build_reference_lines)：帶 Level 與 Date
    assert "[^1]: [Level A]" in md          # 第一筆為 Level A
    assert "2005-12-28" in md               # C7：src_a doc_date 優先
    assert "2026-07-02" in md               # C7：src_b doc_date=None → fetched_date fallback


def test_to_markdown_pending_segment_has_no_footnote() -> None:
    md = to_markdown(_sample_doc())
    pending_lines = [ln for ln in md.splitlines() if "待補證" in ln]
    assert len(pending_lines) == 1
    # sources 空 → 該段不產生任何 [^n] 標記
    assert "[^" not in pending_lines[0]
