from __future__ import annotations

from docx import Document as DocxDocument
import pytest

from note_filler.correction import assemble_correction
from note_filler.export import to_docx, to_json, to_markdown
from note_filler.gap import Gap
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
    assert "追溯：原始輸入 input/note.txt#paragraph-0" in markdown
    assert "追溯：來源識別碼 law:92" in markdown
    assert "追溯：處理紀錄 gap:1" in markdown

    output = tmp_path / "traceable.docx"
    to_docx(product, str(output))
    paragraphs = [p.text for p in DocxDocument(output).paragraphs]
    assert "追溯：原始輸入 input/note.txt#paragraph-0" in paragraphs
    assert "追溯：來源識別碼 law:92" in paragraphs
    assert "追溯：處理紀錄 gap:1" in paragraphs


def test_traceability_gate_rejects_source_id_drift(caplog):
    product = _product()
    product.segments[1].traceability[0]["id"] = "wrong-source"

    with pytest.raises(RuntimeError, match="source ID 對應失敗"):
        require_traceable_note_product(product, source="trace-test")

    assert "note_traceability_failed" in caplog.text
    assert "trace-test" in caplog.text
