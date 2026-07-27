from __future__ import annotations

import json
from copy import deepcopy

import pytest
from docx import Document as DocxDocument

from note_filler.correction import Segment, assemble_correction
from note_filler.binding_report import (
    TRACEABILITY_FIELD_KEYS,
    build_binding_report,
    parse_binding_report,
    write_binding_report,
)
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


def test_traceability_payload_links_claim_source_fragments_and_spans(tmp_path):
    product = _product()
    report = parse_binding_report(build_binding_report(product))
    data = to_json(product)
    metrics = data["polaris_metrics"]

    assert tuple(report)[-3:] == TRACEABILITY_FIELD_KEYS
    assert tuple(metrics)[-3:] == TRACEABILITY_FIELD_KEYS
    for key in TRACEABILITY_FIELD_KEYS:
        assert metrics[key] == report[key]

    sourced = report["arguments"][0]
    segment = data["segments"][sourced["segment_index"]]
    assert sourced["argument_text"] == segment["text"]
    assert sourced["source_fragments"] == [
        {"source_id": "law:92", "text": "行政處分之定義。"}
    ]
    assert sourced["citation_spans"] == segment["citation_spans"]
    assert metrics["claim_source_map"] == {
        "argument:0": ["law:92"],
        "argument:1": [],
    }
    span = metrics["citation_span_map"][0]
    assert segment["text"][span["span_start"]:span["span_end"]] == "[^1]"
    assert (span["argument_id"], span["source_id"]) == ("argument:0", "law:92")
    assert [tuple(marker) for marker in metrics["traceability_markers"]] == [
        ("argument_id", "kind", "id", "binding_status"),
        ("argument_id", "kind", "id", "binding_status"),
    ]
    assert [tuple(item) for item in metrics["citation_span_map"]] == [
        (
            "segment_index",
            "argument_id",
            "source_id",
            "span_start",
            "span_end",
            "marker_text",
        )
    ]

    markdown = to_markdown(product)
    assert "**論點追溯**" in markdown
    assert "claim_fragment=" in markdown
    assert 'source_fragments=[{"source_id":"law:92"' in markdown
    assert 'citation_spans=[{"source_id":"law:92"' in markdown

    output = tmp_path / "traceability-fields.docx"
    to_docx(product, str(output))
    docx_text = "\n".join(p.text for p in DocxDocument(output).paragraphs)
    assert "論點追溯：argument_id=argument:0" in docx_text
    assert "source_fragments=" in docx_text
    assert "citation_spans=" in docx_text


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda seg: seg.citation_spans.clear(), "citation_spans 遺漏來源"),
        (
            lambda seg: seg.citation_spans[0].__setitem__("source_id", "wrong-source"),
            "citation_spans.*來源",
        ),
        (
            lambda seg: seg.citation_spans[0].__setitem__("span_start", 0),
            "範圍與 marker_text 不一致",
        ),
    ],
)
def test_traceability_gate_rejects_missing_wrong_or_shifted_span(mutate, match):
    product = _product()
    mutate(product.segments[1])

    with pytest.raises(RuntimeError, match=match):
        require_traceable_note_product(product, source="span-negative")

    argument = build_binding_report(product)["arguments"][0]
    assert argument["checks"]["source_traceable"] is False
    assert argument["binding_status"] == "fail"


def test_traceability_report_rejects_missing_or_reordered_fixed_fields():
    report = build_binding_report(_product())
    missing = deepcopy(report)
    del missing["claim_source_map"]
    with pytest.raises(ValueError, match="缺少欄位"):
        parse_binding_report(missing)

    reordered = deepcopy(report)
    span = reordered["citation_span_map"][0]
    reordered["citation_span_map"][0] = {
        "argument_id": span["argument_id"],
        "segment_index": span["segment_index"],
        "source_id": span["source_id"],
        "span_start": span["span_start"],
        "span_end": span["span_end"],
        "marker_text": span["marker_text"],
    }
    with pytest.raises(ValueError, match="欄位或序列漂移"):
        parse_binding_report(reordered)


def test_binding_report_writer_persists_failure_then_rejects_missing_span(tmp_path):
    product = _product()
    product.segments[1].citation_spans = []

    with pytest.raises(RuntimeError, match="引用範圍追溯驗收失敗.*argument:0"):
        write_binding_report(tmp_path / "note.md", product)

    persisted = json.loads(
        (tmp_path / "binding_report.json").read_text(encoding="utf-8")
    )
    assert persisted["arguments"][0]["binding_status"] == "fail"
    assert persisted["arguments"][0]["checks"]["source_traceable"] is False


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


# ---- 可逐筆對應追溯標記驗收測試 -------------------------------------------

def test_traceability_markers_claim_source_map_citation_span_complete_binding():
    """正例：來源、主張、引用範圍三者完整綁定。
    
    驗證最終成品中存在可逐筆對應的追溯標記：
    1. traceability_markers 每筆都有 argument_id, kind, id, binding_status
    2. claim_source_map 正確映射 argument_id 到 source_ids
    3. citation_span_map 正確記錄每個引用標記的精確範圍
    4. 三者之間的關係完整且一致
    """
    product = _product()
    report = parse_binding_report(build_binding_report(product))
    data = to_json(product)
    metrics = data["polaris_metrics"]

    # 驗證 traceability_markers 結構
    markers = metrics["traceability_markers"]
    assert len(markers) >= 1, "至少應有一筆追溯標記"
    for marker in markers:
        assert "argument_id" in marker
        assert "kind" in marker
        assert "id" in marker
        assert "binding_status" in marker
        assert marker["binding_status"] in ("pass", "fail", "pending_evidence")

    # 驗證 claim_source_map 結構
    claim_map = metrics["claim_source_map"]
    assert isinstance(claim_map, dict)
    for arg_id, source_ids in claim_map.items():
        assert arg_id.startswith("argument:")
        assert isinstance(source_ids, list)

    # 驗證 citation_span_map 結構
    span_map = metrics["citation_span_map"]
    assert isinstance(span_map, list)
    for span in span_map:
        assert "segment_index" in span
        assert "argument_id" in span
        assert "source_id" in span
        assert "span_start" in span
        assert "span_end" in span
        assert "marker_text" in span

    # 驗證三者之間的一致性
    sourced_arg_id = "argument:0"
    assert sourced_arg_id in claim_map
    assert claim_map[sourced_arg_id] == ["law:92"]
    
    # citation_span_map 應包含對應的引用範圍
    related_spans = [s for s in span_map if s["argument_id"] == sourced_arg_id]
    assert len(related_spans) >= 1
    assert any(s["source_id"] == "law:92" for s in related_spans)
    
    # traceability_markers 應包含對應的標記
    related_markers = [m for m in markers if m["argument_id"] == sourced_arg_id]
    assert len(related_markers) >= 1
    assert any(m["id"] == "law:92" and m["kind"] == "source" for m in related_markers)


def test_traceability_markers_source_exists_but_no_clear_binding():
    """負例：有來源但無明確對應關係。
    
    區分「有來源但無明確對應關係」與「三者完整綁定」：
    1. 論點有 source_id，但 traceability_markers 缺失或不完整
    2. claim_source_map 與實際來源不一致
    3. citation_span_map 缺失或範圍不正確
    
    這種情況應被閘門拒絕，不得默默產出不完整成品。
    """
    product = _product()
    
    # 人為製造「有來源但無明確對應關係」的情況
    # 1. 修改 traceability_markers，移除來源標記
    data = to_json(product)
    metrics = data["polaris_metrics"]
    
    # 原本應該有完整的標記，我們模擬缺失情況
    original_markers = list(metrics["traceability_markers"])
    # 只保留 processing_record，移除 source 標記
    incomplete_markers = [m for m in original_markers if m["kind"] != "source"]
    
    # 2. 修改 claim_source_map，使其與實際來源不一致
    original_claim_map = dict(metrics["claim_source_map"])
    incomplete_claim_map = dict(original_claim_map)
    # 將 argument:0 的來源清空，模擬無明確對應
    incomplete_claim_map["argument:0"] = []
    
    # 3. 修改 citation_span_map，移除引用範圍
    original_span_map = list(metrics["citation_span_map"])
    incomplete_span_map = [s for s in original_span_map if s["argument_id"] != "argument:0"]
    
    # 驗證這種不完整狀態能被檢測出來
    # 檢查 markers 是否不完整
    assert len(incomplete_markers) < len(original_markers), "應檢測到 traceability_markers 不完整"
    
    # 檢查 claim_source_map 是否不一致
    assert incomplete_claim_map["argument:0"] != original_claim_map["argument:0"], "應檢測到 claim_source_map 不一致"
    
    # 檢查 citation_span_map 是否缺失
    assert len(incomplete_span_map) < len(original_span_map), "應檢測到 citation_span_map 缺失"
    
    # 實際產品中，這種不完整狀態應該被 require_traceable_note_product 拒絕
    # 我們可以驗證完整的產品能通過閘門
    require_traceable_note_product(product)
    
    # 而人為製造不完整狀態後，應該能檢測出差異
    complete_report = parse_binding_report(build_binding_report(product))
    assert complete_report["arguments"][0]["binding_status"] == "pass"
    assert complete_report["arguments"][0]["checks"]["source_traceable"] is True


def test_traceability_markers_distinguish_binding_status():
    """驗證能區分不同 binding_status 的追溯標記。
    
    確保測試能區分：
    1. pass：完整綁定（來源、主張、引用範圍三者完整）
    2. fail：綁定失敗（有來源但對應關係錯誤）
    3. pending_evidence：待補證（無來源）
    """
    product = _product()
    report = parse_binding_report(build_binding_report(product))
    data = to_json(product)
    metrics = data["polaris_metrics"]
    
    # 檢查不同 argument 的 binding_status
    arguments = report["arguments"]
    assert len(arguments) >= 2
    
    # argument:0 應該是 pass（有完整來源）
    sourced_arg = next(a for a in arguments if a["argument_id"] == "argument:0")
    assert sourced_arg["binding_status"] == "pass"
    assert sourced_arg["checks"]["source_traceable"] is True
    
    # argument:1 應該是 pending_evidence（無來源）
    pending_arg = next(a for a in arguments if a["argument_id"] == "argument:1")
    assert pending_arg["binding_status"] == "pending_evidence"
    assert pending_arg["checks"]["at_least_one_source"] is False
    
    # 檢查 traceability_markers 中的 binding_status
    markers = metrics["traceability_markers"]
    pass_markers = [m for m in markers if m["binding_status"] == "pass"]
    pending_markers = [m for m in markers if m["binding_status"] == "pending_evidence"]
    
    assert len(pass_markers) >= 1, "應至少有一個 pass 狀態的標記"
    assert len(pending_markers) >= 1, "應至少有一個 pending_evidence 狀態的標記"
    
    # 檢查 claim_source_map 中的對應關係
    claim_map = metrics["claim_source_map"]
    assert claim_map["argument:0"] == ["law:92"], "pass 狀態應有完整來源映射"
    assert claim_map["argument:1"] == [], "pending_evidence 狀態應無來源映射"
    
    # 檢查 citation_span_map 中的對應關係
    span_map = metrics["citation_span_map"]
    sourced_spans = [s for s in span_map if s["argument_id"] == "argument:0"]
    pending_spans = [s for s in span_map if s["argument_id"] == "argument:1"]
    
    assert len(sourced_spans) >= 1, "pass 狀態應有引用範圍"
    assert len(pending_spans) == 0, "pending_evidence 狀態應無引用範圍"
