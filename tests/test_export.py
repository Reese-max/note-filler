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
            traceability=[{"kind": "source", "id": "s1"}, {"kind": "source", "id": "s2"}],
            source_id="sources:s1,s2",
        ),
        Segment(
            type="supplement",
            text="關於施行細節仍待查證。",
            anchor_idx=0,
            sources=[],
            confidence="pending_evidence",
            traceability=[{
                "kind": "processing_record", "id": "gap:1",
                "question": "細節待查", "outcome": "pending_evidence",
            }],
            source_id="pending:gap:1",
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


def test_to_json_contains_binding_summary() -> None:
    """訂正稿 JSON 頂層必須包含 binding_summary，可直接被測試解析綁定驗證狀態。"""
    data = to_json(_sample_doc())
    bs = data.get("binding_summary")
    assert bs is not None, "JSON 輸出應含 binding_summary"
    assert bs["schema"] == "note_filler.binding_report.v1"
    assert isinstance(bs["argument_count"], int)
    assert isinstance(bs["pass"], int)
    assert isinstance(bs["fail"], int)
    assert isinstance(bs["pending_evidence"], int)
    assert isinstance(bs["one_to_one"], int)
    assert isinstance(bs["one_to_many"], int)
    assert isinstance(bs["none"], int)
    assert isinstance(bs["all_arguments_ok"], bool)
    assert isinstance(bs["all_sourced_arguments_ok"], bool)
    # _sample_doc 有 2 個 supplement：第一個 verified 有 2 源、第二個 pending 無源
    assert bs["argument_count"] == 2
    assert bs["one_to_many"] == 1
    assert bs["none"] == 1
    assert bs["pending_evidence"] == 1


def test_to_json_binding_summary_matches_segments() -> None:
    """binding_summary 的計數必須與 segments 實際 supplement 數一致。"""
    data = to_json(_sample_doc())
    bs = data["binding_summary"]
    supplement_segs = [s for s in data["segments"] if s["type"] == "supplement"]
    assert bs["argument_count"] == len(supplement_segs)
    assert bs["pass"] + bs["fail"] + bs["pending_evidence"] == len(supplement_segs)


def test_to_markdown_ends_with_binding_line() -> None:
    """Markdown 輸出末尾必須包含來源綁定驗證行，格式為 > **來源綁定**。"""
    md = to_markdown(_sample_doc())
    last_lines = md.strip().splitlines()[-2:]
    binding_lines = [ln for ln in last_lines if "來源綁定" in ln]
    assert len(binding_lines) >= 1, "Markdown 末段應含來源綁定驗證行"
    assert "✓" in binding_lines[0] or "✗" in binding_lines[0]


def test_to_markdown_binding_verdict_matches_doc() -> None:
    md = to_markdown(_sample_doc())
    assert "\u5168\u90e8\u901a\u904e" in md  # UTF-8: 「全部通過」


def test_to_markdown_binding_line_machine_parseable() -> None:
    import re
    md = to_markdown(_sample_doc())
    m = re.search(r"> \*\*[\u4f86\u6e90\u7d81\u5b9a]+\*\*", md)
    assert m is not None, "binding line format mismatch"


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
    # 篩出補充段的待補證行（非末尾綁定摘要行）
    pending_supplement = [ln for ln in md.splitlines() if "待補證" in ln and "【補充】" in ln]
    assert len(pending_supplement) == 1
    # sources 空 → 該段不產生任何 [^n] 標記
    assert "[^" not in pending_supplement[0]
