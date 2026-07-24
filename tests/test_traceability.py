from __future__ import annotations

import json

import pytest
from docx import Document as DocxDocument

from note_filler.correction import Segment, assemble_correction
from note_filler.export import to_docx, to_json, to_markdown
from note_filler.gap import Gap
from note_filler.llm import FakeLLM
from note_filler.parse import Document, Paragraph
from note_filler.pipeline import require_traceable_note_product
from note_filler.retrieve.models import Source
from note_filler.verify import cross_validate
from note_filler.write import WrittenSupplement


def _product():
    original = Document(
        source_path="input/note.txt",
        paragraphs=(Paragraph(0, "原稿逐字保留。"),),
        full_text="原稿逐字保留。",
    )
    source = Source(
        id="law:92",
        title="行政程序法第 92 條",
        url="https://law.moj.gov.tw/",
        level="A",
        content="行政處分之定義。",
        fetched_date="2026-07-24",
        doc_date=None,
        distance=0.1,
    )
    sourced = Gap("行政處分如何定義？", "missing", "原稿未說明")
    pending = Gap("例外情形為何？", "partial", "原稿未列舉")
    gaps = [sourced, pending]
    retrieved = {sourced.question: [source], pending.question: []}
    written = {
        sourced.question: WrittenSupplement("行政處分有法定定義[^1]。", [source.id]),
        pending.question: WrittenSupplement("【待補證】目前無相關來源。", []),
    }
    validations = {
        question: cross_validate(question, sources)
        for question, sources in retrieved.items()
    }
    return assemble_correction(original, gaps, retrieved, written, validations)


def test_product_content_has_verifiable_traceability_in_all_exports(tmp_path):
    product = _product()
    require_traceable_note_product(product)

    original, sourced, pending = product.segments
    assert original.text == product.original.paragraphs[0].text
    assert original.traceability == [
        {"kind": "original_input", "id": "input/note.txt", "paragraph_idx": 0}
    ]
    assert sourced.traceability == [{"kind": "source", "id": "law:92"}]
    assert [source.id for source in sourced.sources] == ["law:92"]
    assert pending.confidence == "pending_evidence" and not pending.sources
    assert pending.traceability == [
        {
            "kind": "processing_record",
            "id": "gap:1",
            "question": "例外情形為何？",
            "outcome": "pending_evidence",
        }
    ]

    data = to_json(product)
    assert [segment["traceability"] for segment in data["segments"]] == [
        segment.traceability for segment in product.segments
    ]
    markdown = to_markdown(product)
    assert "來源ID input:input/note.txt#p0" in markdown
    assert "原始輸入 input/note.txt#paragraph-0" in markdown
    assert "來源ID sources:law:92" in markdown
    assert "來源識別碼 law:92" in markdown
    assert "來源ID pending:gap:1" in markdown
    assert "處理紀錄 gap:1" in markdown

    output = tmp_path / "traceable.docx"
    to_docx(product, str(output))
    paragraphs = [p.text for p in DocxDocument(output).paragraphs]
    assert any("來源ID input:input/note.txt#p0" in p for p in paragraphs)
    assert any("原始輸入 input/note.txt#paragraph-0" in p for p in paragraphs)
    assert any("來源ID sources:law:92" in p for p in paragraphs)
    assert any("來源識別碼 law:92" in p for p in paragraphs)
    assert any("來源ID pending:gap:1" in p for p in paragraphs)
    assert any("處理紀錄 gap:1" in p for p in paragraphs)


def test_traceability_gate_rejects_source_id_drift(caplog):
    product = _product()
    product.segments[1].traceability[0]["id"] = "wrong-source"

    with pytest.raises(RuntimeError, match="source ID 對應失敗"):
        require_traceable_note_product(product, source="trace-test")

    assert "note_traceability_failed" in caplog.text
    assert "trace-test" in caplog.text


# ---- 來源識別碼 (source_id) 新測試 ------------------------------------------

def test_every_segment_has_source_id():
    """每個主要內容區塊都必須有非空的 source_id。"""
    product = _product()
    for i, seg in enumerate(product.segments):
        assert seg.source_id, f"segment[{i}] source_id 不得為空"
        assert isinstance(seg.source_id, str), f"segment[{i}] source_id 須為字串"


def test_source_id_format_original():
    """original 段的 source_id 格式：input:{path}#p{idx}"""
    product = _product()
    orig = product.segments[0]
    assert orig.type == "original"
    assert orig.source_id == "input:input/note.txt#p0"
    assert orig.source_id.startswith("input:")
    assert "#p" in orig.source_id


def test_source_id_format_supplement_sourced():
    """有來源的 supplement 段 source_id 格式：sources:{id1},{id2}..."""
    product = _product()
    supp = product.segments[1]
    assert supp.type == "supplement"
    assert supp.source_id == "sources:law:92"
    assert supp.source_id.startswith("sources:")
    # 多來源情境
    source_a = Source(id="law:100", title="民訴§100", url=None, level="A",
                      content="內容", fetched_date="2026-07-24", doc_date=None, distance=0.5)
    source_b = Source(id="law:200", title="刑訴§200", url=None, level="B",
                      content="內容", fetched_date="2026-07-24", doc_date=None, distance=0.5)
    multi = Gap("多重來源？", "missing", "缺")
    multi_supp = assemble_correction(
        _product().original, [multi],
        {multi.question: [source_a, source_b]},
        {multi.question: WrittenSupplement("多來源[^1][^2]。", [source_a.id, source_b.id])},
        {multi.question: cross_validate(multi.question, [source_a, source_b])},
    )
    assert multi_supp.segments[-1].source_id == "sources:law:100,law:200"


def test_source_id_format_supplement_pending():
    """無來源的 supplement 段 source_id 格式：pending:gap:{idx}"""
    product = _product()
    supp = product.segments[2]
    assert supp.type == "supplement"
    assert supp.source_id == "pending:gap:1"
    assert supp.source_id.startswith("pending:gap:")


def test_source_id_in_json_export():
    """JSON 匯出必須包含 source_id 欄位"""
    product = _product()
    data = to_json(product)
    for i, seg in enumerate(data["segments"]):
        assert "source_id" in seg, f"JSON segment[{i}] 缺少 source_id"
        assert seg["source_id"], f"JSON segment[{i}] source_id 不得為空"


def test_source_id_in_markdown_export():
    """Markdown 匯出必須顯示來源 ID"""
    product = _product()
    md = to_markdown(product)
    assert "來源ID input:input/note.txt#p0" in md, "markdown 應含 original source_id"
    assert "來源ID sources:law:92" in md, "markdown 應含 supplement source_id"
    assert "來源ID pending:gap:1" in md, "markdown 應含 pending source_id"


def test_source_id_in_docx_export(tmp_path):
    """docx 匯出必須顯示來源 ID"""
    product = _product()
    output = tmp_path / "source_id.docx"
    to_docx(product, str(output))
    paragraphs = [p.text for p in DocxDocument(output).paragraphs]
    assert any("來源ID input:input/note.txt#p0" in p for p in paragraphs)
    assert any("來源ID sources:law:92" in p for p in paragraphs)
    assert any("來源ID pending:gap:1" in p for p in paragraphs)


def test_source_id_gate_rejects_wrong_original_source_id(caplog):
    """require_traceable_note_product 應拒絕錯誤的 original source_id"""
    product = _product()
    product.segments[0].source_id = "wrong:source"
    with pytest.raises(RuntimeError, match="source_id 應為"):
        require_traceable_note_product(product, source="trace-test")


def test_source_id_gate_rejects_wrong_supplement_source_id(caplog):
    """require_traceable_note_product 應拒絕錯誤的 supplement source_id"""
    product = _product()
    product.segments[1].source_id = "wrong:source"
    with pytest.raises(RuntimeError, match="source_id 應為"):
        require_traceable_note_product(product, source="trace-test")


def test_source_id_gate_rejects_missing_pending_prefix(caplog):
    """pending supplement 的 source_id 必須以 pending:gap: 開頭"""
    product = _product()
    product.segments[2].source_id = "sources:fake"
    with pytest.raises(RuntimeError, match="source_id 應以 pending:gap: 開頭"):
        require_traceable_note_product(product, source="trace-test")


def test_traceability_maintains_multi_paragraph_input():
    """多段落輸入仍可正確追溯每個原文段"""
    doc = Document(
        source_path="multi.txt",
        paragraphs=(
            Paragraph(0, "第一段原文。"),
            Paragraph(1, "第二段原文。"),
            Paragraph(2, "第三段原文。"),
        ),
        full_text="第一段原文。\n第二段原文。\n第三段原文。",
    )
    gap = Gap("測試問題？", "missing", "缺")
    src = Source(id="test:1", title="測試源", url=None, level="C",
                 content="測試內容", fetched_date="2026-07-24", doc_date=None, distance=0.5)
    prod = assemble_correction(
        doc, [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("測試補充[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    require_traceable_note_product(prod)

    assert len(prod.segments) == 4  # 3 original + 1 supplement
    for i in range(3):
        assert prod.segments[i].source_id == f"input:multi.txt#p{i}"
    assert prod.segments[3].source_id == "sources:test:1"


def test_traceability_full_pipeline(tmp_path):
    """透過完整 pipeline 驗證每個 segment 都有可追溯的 source_id"""
    from docx import Document as DocxMake
    fake = FakeLLM([
        "law",
        "問題一？\n問題二？",
        json.dumps([
            {"question": "問題一？", "status": "missing", "reason": "缺"},
            {"question": "問題二？", "status": "missing", "reason": "缺"},
        ], ensure_ascii=False),
        '{"keyword": "測試", "law_name": null}',
        "【待補證】問題一無來源。",
        '{"keyword": "測試二", "law_name": null}',
        "問題二有來源[^1][^2]。",
    ])

    class _FakeTwinkle:
        def __init__(self):
            self._batches = [
                [],
                [
                    Source(id="src:a", title="源A", url=None, level="A",
                           content="A內容", fetched_date="2026-07-24", doc_date=None, distance=0.5),
                    Source(id="src:b", title="源B", url=None, level="B",
                           content="B內容", fetched_date="2026-07-24", doc_date=None, distance=0.5),
                ],
            ]

        def search(self, query, n=3):
            return self._batches.pop(0) if self._batches else []

    class _FakeLaw:
        def lookup_article(self, law_name, article_no): return None
        def law_exists(self, name): return True
        def fuzzy_find_law(self, name): return None
        def search_articles(self, keyword, limit=5, law_name=None): return []

    from note_filler.pipeline import run_pipeline
    p = tmp_path / "note.docx"
    d = DocxMake()
    d.add_paragraph("測試用原文段落。")
    d.save(str(p))

    product = run_pipeline(str(p), fake, _FakeTwinkle(), _FakeLaw())
    require_traceable_note_product(product)

    for i, seg in enumerate(product.segments):
        assert seg.source_id, f"pipeline segment[{i}] source_id 不得為空"
        trace = getattr(seg, "traceability", [])
        assert trace, f"pipeline segment[{i}] traceability 不得為空"
