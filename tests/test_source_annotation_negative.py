"""來源附註負例：證據不足或適用條件未明時不得生成確定結論。"""

from docx import Document as DocxDocument

from note_filler.correction import assemble_correction
from note_filler.export import to_docx, to_json, to_markdown
from note_filler.gap import Gap
from note_filler.parse import Document, Paragraph
from note_filler.retrieve.models import Source
from note_filler.verify import cross_validate
from note_filler.write import WrittenSupplement


_ORIGINAL = "原稿逐字保留。"


def _source(source_id: str, title: str, content: str, level: str) -> Source:
    return Source(
        id=source_id,
        title=title,
        url=None,
        level=level,
        content=content,
        fetched_date="2026-07-28",
        doc_date=None,
        distance=0.1,
    )


def _product(sources: list[Source], text: str):
    question = "此申請是否符合要件？"
    gap = Gap(question, "missing", "原稿未說明申請要件")
    validation = cross_validate(question, sources)
    product = assemble_correction(
        Document("input/note.txt", (Paragraph(0, _ORIGINAL),), _ORIGINAL),
        [gap],
        {question: sources},
        {question: WrittenSupplement(text, [source.id for source in sources])},
        {question: validation},
    )
    return product, validation


def _exports(product, tmp_path, name: str):
    data = to_json(product)
    markdown = to_markdown(product)
    path = tmp_path / f"{name}.docx"
    to_docx(product, str(path))
    paragraphs = [paragraph.text for paragraph in DocxDocument(path).paragraphs]
    supplement = next(
        segment for segment in data["segments"] if segment["type"] == "supplement"
    )
    assert next(
        segment["text"] for segment in data["segments"] if segment["type"] == "original"
    ) == _ORIGINAL
    assert _ORIGINAL in markdown and paragraphs[0] == _ORIGINAL
    return supplement, markdown, paragraphs


def test_claim_without_qualified_source_outputs_pending_without_fabricated_url(tmp_path):
    candidate = _source(
        "commentary:1",
        "未經查核的單一評論",
        "這是一般性評論，沒有可獨立驗證的依據。",
        "D",
    )
    product, validation = _product([candidate], "此申請應予准許。[^1]")

    assert validation.verified is False
    assert product.segments[-1].confidence == "pending_evidence"
    supplement, markdown, paragraphs = _exports(product, tmp_path, "unqualified")
    annotation = supplement["three_part_annotation"]

    assert [row["url"] for row in annotation["source_comparison"]] == [None]
    assert all("【待補來源】" in item for item in annotation["usage_conditions"])
    assert annotation["conclusion"].startswith("【待補來源】")
    assert "建議以" not in annotation["conclusion"]
    assert "http://" not in markdown and "https://" not in markdown
    assert not any("http://" in line or "https://" in line for line in paragraphs)


def test_conflicting_sources_without_applicability_stay_separate_and_pending(tmp_path):
    allow = _source("official:allow", "來源甲", "申請人得提出申請。", "A")
    deny = _source("official:deny", "來源乙", "申請人不得提出申請。", "A")
    product, validation = _product(
        [allow, deny], "現有資料對申請資格的結論互有衝突。[^1][^2]"
    )

    assert validation.conflict is True
    supplement, markdown, paragraphs = _exports(product, tmp_path, "unresolved")
    annotation = supplement["three_part_annotation"]

    assert [row["id"] for row in annotation["source_comparison"]] == [
        "official:allow",
        "official:deny",
    ]
    assert [row["url"] for row in annotation["source_comparison"]] == [None, None]
    assert len(annotation["usage_conditions"]) == 2
    assert all("【待補來源】" in item for item in annotation["usage_conditions"])
    assert annotation["conclusion"].startswith("【待補來源】")
    assert "不合併為單一結論" in annotation["conclusion"]
    assert "建議以" not in annotation["conclusion"]
    assert "交叉驗證" not in annotation["conclusion"]
    assert "得提出申請" not in annotation["conclusion"]
    assert "不得提出申請" not in annotation["conclusion"]
    assert markdown.count("【待補來源】") >= 3
    assert any("結論：【待補來源】" in line for line in paragraphs)
    assert "http://" not in markdown and "https://" not in markdown
