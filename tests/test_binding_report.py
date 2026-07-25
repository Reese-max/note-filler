"""可機器比對的綁定報告：格式可直接解析，逐項驗證至少一個來源／可追溯／無重複遺漏。

涵蓋一對一、一對多、pending、以及來源缺失／未對上的負例。
不得弱化既有品質閘（原稿 immutable、pending_evidence、只掛實際引用、法條離線查核）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from note_filler.binding_report import (
    BINDING_REPORT_NAME,
    SCHEMA_ID,
    build_binding_report,
    parse_binding_report,
    write_binding_report,
)
from note_filler.correction import Segment, assemble_correction
from note_filler.export import to_json
from note_filler.gap import Gap
from note_filler.parse import Document, Paragraph
from note_filler.retrieve.models import Source
from note_filler.verify import cross_validate
from note_filler.write import WrittenSupplement


def _doc(path: str = "input/note.txt") -> Document:
    return Document(
        source_path=path,
        paragraphs=(Paragraph(0, "原稿逐字保留。"),),
        full_text="原稿逐字保留。",
    )


def _source(id: str, title: str, level: str = "A") -> Source:
    return Source(
        id=id,
        title=title,
        url=None,
        level=level,
        content=f"{title} 內容",
        fetched_date="2026-07-25",
        doc_date=None,
        distance=0.5,
    )


def _assemble_one_to_one():
    src = _source("law:92", "行政程序法第 92 條")
    gap = Gap("行政處分之定義？", "missing", "未說明")
    return assemble_correction(
        _doc(),
        [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("定義參照[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )


def _assemble_one_to_many():
    srcs = [
        _source("law:92", "行政程序法第 92 條"),
        _source("law:93", "行政程序法第 93 條", level="B"),
        _source("web:abc", "官方函釋", level="C"),
    ]
    gap = Gap("附款相關規定？", "missing", "未說明")
    return assemble_correction(
        _doc(),
        [gap],
        {gap.question: srcs},
        {gap.question: WrittenSupplement("三源[^1][^2][^3]。", [s.id for s in srcs])},
        {gap.question: cross_validate(gap.question, srcs)},
    )


def _assemble_mixed():
    src_a = _source("law:92", "行政程序法第 92 條")
    src_b1 = _source("law:93", "行政程序法第 93 條")
    src_b2 = _source("law:94", "行政程序法第 94 條")
    gap_a = Gap("定義？", "missing", "未說明")
    gap_b = Gap("附款限制？", "missing", "未說明")
    return assemble_correction(
        _doc(),
        [gap_a, gap_b],
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


def _assemble_pending():
    gap = Gap("無來源問題？", "missing", "未說明")
    return assemble_correction(
        _doc(),
        [gap],
        {gap.question: []},
        {gap.question: WrittenSupplement("【待補證】尚無可用來源。", [])},
        {gap.question: cross_validate(gap.question, [])},
    )


# ---- 格式可直接由測試解析 ---------------------------------------------------

def test_schema_is_machine_parseable():
    report = build_binding_report(_assemble_one_to_one())
    parsed = parse_binding_report(report)
    assert parsed["schema"] == SCHEMA_ID
    assert parsed["argument_count"] == 1
    assert isinstance(parsed["arguments"], list)


def test_parse_rejects_missing_keys():
    with pytest.raises(ValueError, match="缺少頂層欄位"):
        parse_binding_report({"schema": SCHEMA_ID})


def test_parse_rejects_wrong_schema():
    report = build_binding_report(_assemble_one_to_one())
    report["schema"] = "other.v0"
    with pytest.raises(ValueError, match="schema 不符"):
        parse_binding_report(report)


def test_roundtrip_json_still_parseable(tmp_path):
    product = _assemble_mixed()
    path = write_binding_report(tmp_path / "out.md", product)
    assert path.name == BINDING_REPORT_NAME
    raw = json.loads(path.read_text(encoding="utf-8"))
    parsed = parse_binding_report(raw)
    assert parsed["argument_count"] == 2


# ---- 一對一 ------------------------------------------------------------------

def test_one_to_one_binding_checks():
    report = parse_binding_report(build_binding_report(_assemble_one_to_one()))
    assert report["summary"]["one_to_one"] == 1
    assert report["summary"]["one_to_many"] == 0
    arg = report["arguments"][0]
    assert arg["cardinality"] == "one_to_one"
    assert arg["source_count"] == 1
    assert arg["source_ids"] == ["law:92"]
    assert arg["trace_source_ids"] == ["law:92"]
    # 三項核心可機器比對
    assert arg["checks"]["at_least_one_source"] is True
    assert arg["checks"]["source_traceable"] is True
    assert arg["checks"]["no_duplicate_sources"] is True
    assert arg["checks"]["no_omitted_traces"] is True
    assert arg["checks"]["no_extra_traces"] is True
    assert arg["binding_status"] == "pass"
    assert arg["binding_ok"] is True


# ---- 一對多 ------------------------------------------------------------------

def test_one_to_many_binding_checks():
    report = parse_binding_report(build_binding_report(_assemble_one_to_many()))
    assert report["summary"]["one_to_many"] == 1
    arg = report["arguments"][0]
    assert arg["cardinality"] == "one_to_many"
    assert arg["source_count"] == 3
    assert arg["source_ids"] == ["law:92", "law:93", "web:abc"]
    assert arg["trace_source_ids"] == arg["source_ids"]
    assert arg["checks"]["at_least_one_source"] is True
    assert arg["checks"]["source_traceable"] is True
    assert arg["checks"]["no_duplicate_sources"] is True
    assert arg["checks"]["no_omitted_traces"] is True
    assert arg["binding_ok"] is True


def test_mixed_one_to_one_and_one_to_many():
    report = parse_binding_report(build_binding_report(_assemble_mixed()))
    assert report["argument_count"] == 2
    assert report["summary"]["one_to_one"] == 1
    assert report["summary"]["one_to_many"] == 1
    a0, a1 = report["arguments"]
    assert a0["cardinality"] == "one_to_one"
    assert a1["cardinality"] == "one_to_many"
    assert a0["source_ids"] == ["law:92"]
    assert a1["source_ids"] == ["law:93", "law:94"]
    assert report["summary"]["all_sourced_arguments_ok"] is True
    assert report["summary"]["all_arguments_ok"] is True


def test_product_output_each_argument_has_ids_and_traceable_fragments():
    """最小正例：同一成品逐筆核對 1:1、1:N 論點的來源與片段。"""
    from note_filler.pipeline import require_traceable_note_product

    product = _assemble_mixed()
    require_traceable_note_product(product, source="positive-binding")
    output = json.loads(json.dumps(to_json(product), ensure_ascii=False))
    report = parse_binding_report(build_binding_report(product))
    expected = [
        ("定義[^1]。", "one_to_one", {"law:92": "行政程序法第 92 條"}),
        (
            "限制[^1][^2]。",
            "one_to_many",
            {
                "law:93": "行政程序法第 93 條",
                "law:94": "行政程序法第 94 條",
            },
        ),
    ]

    assert report["argument_count"] == len(expected)
    for argument, (claim, cardinality, fragments) in zip(report["arguments"], expected):
        segment = output["segments"][argument["segment_index"]]
        sources = {source["id"]: source for source in segment["sources"]}

        assert argument["argument_text"] == segment["text"] == claim
        assert argument["cardinality"] == cardinality
        assert argument["source_ids"] == list(fragments)
        assert argument["trace_source_ids"] == list(fragments)
        assert segment["source_id"] == f"sources:{','.join(fragments)}"
        assert all(
            fragment in sources[source_id]["content"]
            for source_id, fragment in fragments.items()
        )
        assert all(argument["checks"].values())
        assert argument["binding_status"] == "pass"
        assert argument["binding_ok"] is True

    assert report["summary"]["all_arguments_ok"] is True


# ---- pending / 無來源 -------------------------------------------------------

def test_pending_evidence_has_none_cardinality_and_traceable_record():
    report = parse_binding_report(build_binding_report(_assemble_pending()))
    arg = report["arguments"][0]
    assert arg["cardinality"] == "none"
    assert arg["checks"]["at_least_one_source"] is False
    assert arg["checks"]["source_traceable"] is True  # processing_record
    assert arg["binding_status"] == "pending_evidence"
    assert arg["binding_ok"] is True
    assert report["summary"]["pending_evidence"] == 1


# ---- 逐項三條件：至少一源、可追溯、無重複遺漏 --------------------------------

def test_each_argument_exposes_three_core_checks():
    report = parse_binding_report(build_binding_report(_assemble_mixed()))
    for arg in report["arguments"]:
        c = arg["checks"]
        assert set(c) >= {
            "at_least_one_source",
            "source_traceable",
            "no_duplicate_sources",
            "no_omitted_traces",
            "no_extra_traces",
        }
        # 有來源的論點三項皆 True
        if arg["cardinality"] != "none":
            assert c["at_least_one_source"] is True
            assert c["source_traceable"] is True
            assert c["no_duplicate_sources"] is True
            assert c["no_omitted_traces"] is True
            assert c["no_extra_traces"] is True


# ---- 負例：缺來源／來源未對上 → binding_ok False ----------------------------

def test_missing_sources_on_verified_segment_fails():
    """論點存在但 sources 空且非 pending → fail（L071 最小負例）。"""
    product = _assemble_one_to_one()
    seg = product.segments[1]
    seg.sources = []
    seg.traceability = []
    seg.source_id = "sources:law:92"  # 欄位與實際脫節
    seg.confidence = "verified"
    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]
    assert arg["checks"]["at_least_one_source"] is False
    assert arg["binding_status"] == "fail"
    assert arg["binding_ok"] is False
    assert report["summary"]["fail"] == 1
    assert report["summary"]["all_arguments_ok"] is False


def test_trace_id_mismatch_fails_source_traceable():
    """有 Source 但 traceability 指到錯誤 id → source_traceable False。"""
    product = _assemble_one_to_one()
    product.segments[1].traceability = [{"kind": "source", "id": "wrong-id"}]
    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]
    assert arg["checks"]["at_least_one_source"] is True
    assert arg["checks"]["source_traceable"] is False
    assert arg["checks"]["no_omitted_traces"] is False  # law:92 缺 trace
    assert arg["checks"]["no_extra_traces"] is False  # wrong-id 多餘
    assert arg["binding_ok"] is False
    assert arg["binding_status"] == "fail"


def test_duplicate_source_ids_fail_no_duplicate_check():
    """人為注入重複 source → no_duplicate_sources False。"""
    product = _assemble_one_to_one()
    src = product.segments[1].sources[0]
    product.segments[1].sources = [src, src]
    product.segments[1].traceability = [
        {"kind": "source", "id": src.id},
        {"kind": "source", "id": src.id},
    ]
    product.segments[1].source_id = f"sources:{src.id},{src.id}"
    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]
    assert arg["checks"]["no_duplicate_sources"] is False
    assert arg["binding_ok"] is False


# ---- CLI 落盤 ---------------------------------------------------------------

def test_process_file_writes_binding_report(tmp_path, monkeypatch):
    """成功交付後必須寫出 binding_report.json，且可 parse。"""
    from note_filler import __main__ as cli
    from note_filler.correction import CorrectionDoc

    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")

    product = _assemble_mixed()

    class _FakePipelineDoc:
        """pipeline stub：完整 CorrectionDoc 欄位。"""

        def __init__(self, inner: CorrectionDoc):
            self.original = inner.original
            self.segments = inner.segments

    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakePipelineDoc(product))
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n有內容。")

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="md")
    report_path = Path(r["output"]).parent / BINDING_REPORT_NAME
    assert report_path.exists(), f"必須寫出 {BINDING_REPORT_NAME}"
    parsed = parse_binding_report(json.loads(report_path.read_text(encoding="utf-8")))
    assert parsed["argument_count"] == 2
    assert parsed["summary"]["one_to_one"] == 1
    assert parsed["summary"]["one_to_many"] == 1
    assert parsed["summary"]["all_arguments_ok"] is True


# ---- 與 require_traceable 閘一致：正常組裝不失敗 ----------------------------

def test_binding_report_agrees_with_traceable_gate_on_good_product():
    from note_filler.pipeline import require_traceable_note_product

    product = _assemble_mixed()
    require_traceable_note_product(product, source="binding-report-test")
    report = parse_binding_report(build_binding_report(product))
    assert report["summary"]["all_arguments_ok"] is True
    for arg in report["arguments"]:
        assert arg["binding_ok"] is True
        assert arg["checks"]["source_traceable"] is True
