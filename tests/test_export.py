import json

import pytest

from note_filler.parse import Document, Paragraph
from note_filler.correction import CorrectionDoc, Segment
from note_filler.retrieve.models import Source
from note_filler.export import to_docx, to_json, to_markdown


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
            functional_gap="",
            user_value="",
            argument_id="",
        ),
        Segment(
            type="supplement",
            text="依行政程序法第92條，行政處分係指行政機關就公法上具體事件所為之決定。",
            anchor_idx=0,
            sources=[src_a, src_b],
            confidence="verified",
            traceability=[{"kind": "source", "id": "s1"}, {"kind": "source", "id": "s2"}],
            source_id="sources:s1,s2",
            functional_gap="原稿未定義行政處分",
            user_value="補齊讀者對「行政處分如何定義？」所需的說明",
            argument_id="argument:0",
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
            functional_gap="原稿未說明施行細節",
            user_value="補齊讀者對「細節待查」所需的說明",
            argument_id="argument:1",
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


# ---- 可機器解析綁定結構：source_ids／cardinality／來源清單行 --------------


def test_to_json_contains_source_ids_per_segment():
    """JSON 輸出每 segment 必須含 source_ids list 與 cardinality。"""
    data = to_json(_sample_doc())
    for i, seg in enumerate(data["segments"]):
        assert "source_ids" in seg, f"segment[{i}] 缺少 source_ids"
        assert isinstance(seg["source_ids"], list), f"segment[{i}] source_ids 須為 list"
        assert all(isinstance(s, str) for s in seg["source_ids"]), (
            f"segment[{i}] source_ids 元素須為 str"
        )
        assert "cardinality" in seg, f"segment[{i}] 缺少 cardinality"
        assert seg["cardinality"] in ("one_to_one", "one_to_many", "none"), (
            f"segment[{i}] cardinality 非法: {seg['cardinality']!r}"
        )
        assert "functional_gap" in seg, f"segment[{i}] 缺少 functional_gap"
        assert isinstance(seg["functional_gap"], str), f"segment[{i}] functional_gap 須為 str"
        assert "user_value" in seg, f"segment[{i}] 缺少 user_value"
        assert isinstance(seg["user_value"], str), f"segment[{i}] user_value 須為 str"
        assert "argument_id" in seg, f"segment[{i}] 缺少 argument_id"
        assert isinstance(seg["argument_id"], str), f"segment[{i}] argument_id 須為 str"
        assert "angle_coverage" in seg, f"segment[{i}] 缺少 angle_coverage"
        assert isinstance(seg["angle_coverage"], dict), f"segment[{i}] angle_coverage 須為 dict"
        assert "angle_type" in seg, f"segment[{i}] 缺少 angle_type"
        assert "angle_labels" in seg, f"segment[{i}] 缺少 angle_labels"
        assert "angle_key" in seg, f"segment[{i}] 缺少 angle_key"
    assert "angle_coverage_summary" in data
    assert data["angle_coverage_summary"]["effective_angle_count"] == 2
    assert data["angle_coverage_summary"]["coverage_ok"] is True
    assert data["segments"][1]["angle_coverage"]["effective_angle_count"] == 1
    assert data["segments"][1]["angle_coverage"]["duplicate_exclusion"]["excluded"] is False
    # _sample_doc: seg[0]=original → none(0源), seg[1]=supplement 2源→ one_to_many
    assert data["segments"][0]["cardinality"] == "none"
    assert data["segments"][0]["source_ids"] == []
    assert data["segments"][1]["cardinality"] == "one_to_many"
    assert data["segments"][1]["source_ids"] == ["s1", "s2"]
    assert data["segments"][2]["cardinality"] == "none"
    assert data["segments"][2]["source_ids"] == []


def test_to_json_source_ids_matches_sources():
    """JSON 輸出 per-segment 的 source_ids 與 sources.id 一致。"""
    data = to_json(_sample_doc())
    for i, seg in enumerate(data["segments"]):
        expected = [s["id"] for s in seg.get("sources", [])]
        assert seg["source_ids"] == expected, (
            f"segment[{i}] source_ids {seg['source_ids']} != sources.id {expected}"
        )


def test_to_markdown_contains_machine_parseable_source_list():
    """Markdown 輸出每個 supplement 段後須有機器可解析的來源清單行。"""
    md = to_markdown(_sample_doc())
    lines = md.splitlines()

    # verified supplement 有兩個來源 → one to many
    source_lines = [ln for ln in lines if "> **來源清單**" in ln]
    assert len(source_lines) == 2, f"應有 2 筆來源清單行，實際 {len(source_lines)}"
    assert "s1,s2" in source_lines[0], f"第一筆應含 s1,s2: {source_lines[0]!r}"
    assert "one to many" in source_lines[0], (
        f"第一筆應標示 one to many: {source_lines[0]!r}"
    )
    # pending supplement → 無來源
    assert "pending（無來源）" in source_lines[1], (
        f"第二筆應標示 pending: {source_lines[1]!r}"
    )


def test_to_markdown_contains_angle_coverage_line():
    """Markdown 逐筆同列論點、來源、必要性雙視角與角度清單。"""
    doc = _sample_doc()
    # 手建 fixture 預設無 angle_*；補上以驗證序列化輸出
    doc.segments[1].angle_type = "definition"
    doc.segments[1].angle_labels = ["definition", "functional_gap", "user_value"]
    doc.segments[1].angle_key = "definition:行政處分如何定義"
    md = to_markdown(doc)
    angle_lines = [ln for ln in md.splitlines() if "> **角度覆蓋**" in ln]
    assert len(angle_lines) >= 1
    assert "functional_gap=原稿未定義行政處分" in angle_lines[0]
    assert "user_value=補齊讀者對「行政處分如何定義？」所需的說明" in angle_lines[0]
    assert "angle_tags=definition、functional_gap、user_value" in angle_lines[0]
    assert "source_ids=s1,s2" in angle_lines[0]
    summary_lines = [ln for ln in md.splitlines() if "> **角度覆蓋摘要**" in ln]
    assert len(summary_lines) == 1
    assert "有效角度 2/最低 2" in summary_lines[0]
    assert "通過 ✓" in summary_lines[0]


def test_human_readable_exports_show_argument_aligned_visible_summaries(tmp_path):
    """每筆關聯知識必須與同一 argument_id 的必要性雙視角一起顯示。"""
    expected = [
        (
            "argument_id=argument:0；"
            "functional_gap=原稿未定義行政處分；"
            "user_value=補齊讀者對「行政處分如何定義？」所需的說明；"
            "related_knowledge=依行政程序法第92條，行政處分係指行政機關就公法上具體事件所為之決定。"
        ),
        (
            "argument_id=argument:1；"
            "functional_gap=原稿未說明施行細節；"
            "user_value=補齊讀者對「細節待查」所需的說明；"
            "related_knowledge=關於施行細節仍待查證。"
        ),
    ]

    md_lines = [
        line.removeprefix("> **摘要可見**：")
        for line in to_markdown(_sample_doc()).splitlines()
        if line.startswith("> **摘要可見**：")
    ]
    assert md_lines == expected

    out = tmp_path / "visible-summaries.docx"
    to_docx(_sample_doc(), str(out))
    from docx import Document as DocxDocument

    docx_lines = [
        paragraph.text.removeprefix("摘要可見：")
        for paragraph in DocxDocument(out).paragraphs
        if paragraph.text.startswith("摘要可見：")
    ]
    assert docx_lines == expected


def test_to_docx_contains_machine_parseable_source_list(tmp_path):
    """docx 輸出每個 supplement 段後須有機器可解析的來源清單行。"""
    from docx import Document as DocxDocument
    out = tmp_path / "binding.docx"
    to_docx(_sample_doc(), str(out))
    paras = [p.text for p in DocxDocument(out).paragraphs]
    source_lines = [p for p in paras if p.startswith("來源清單")]
    assert len(source_lines) == 2, f"應有 2 筆來源清單行，實際 {len(source_lines)}"
    assert "s1,s2" in source_lines[0]
    assert "one to many" in source_lines[0]
    assert "pending" in source_lines[1]
    angle_lines = [p for p in paras if p.startswith("角度覆蓋：")]
    assert any(
        "functional_gap=原稿未定義行政處分" in p
        and "user_value=補齊讀者對「行政處分如何定義？」所需的說明" in p
        and "angle_tags=definition、functional_gap、user_value" in p
        and "source_ids=s1,s2" in p
        for p in angle_lines
    )
    assert any(p.startswith("角度覆蓋摘要：") for p in paras)
