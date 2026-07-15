"""to_docx round-trip:寫出 .docx 再重開,驗原文保留與補充段標記。"""

from __future__ import annotations

from dataclasses import dataclass, field

from note_filler.export import to_docx


@dataclass
class _Seg:
    type: str
    text: str
    confidence: str = "verified"
    sources: list = field(default_factory=list)


@dataclass
class _Orig:
    source_path: str = "n.txt"


@dataclass
class _Doc:
    original: _Orig = field(default_factory=_Orig)
    segments: list = field(default_factory=list)


def test_to_docx_roundtrip_preserves_original_and_marks_supplement(tmp_path):
    from docx import Document as DocxDocument

    doc = _Doc(segments=[
        _Seg("original", "一、行政處分之定義"),
        _Seg("supplement", "行政處分須對外發生法律效果。", "verified"),
        _Seg("supplement", "無相關來源。", "pending_evidence"),
    ])
    dest = tmp_path / "out.docx"
    to_docx(doc, str(dest))

    assert dest.exists()
    texts = [p.text for p in DocxDocument(str(dest)).paragraphs]
    assert "一、行政處分之定義" in texts  # 原文逐字保留
    assert any(t.startswith("【補充】") and "對外發生法律效果" in t for t in texts)
    assert any("⚠待補證" in t for t in texts)  # pending 段標記
