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


def test_positive_acceptance_reads_binding_report_from_disk(tmp_path):
    """正向驗收：直接讀取 binding_report.json 與成品 JSON，
    逐項斷言每個論點至少一個來源、來源 ID 與片段／位置可對上、無重複遺漏。
    """
    import json

    from note_filler.export import to_json

    product = _assemble_mixed()
    out_dir = tmp_path

    product_path = out_dir / "note_product.json"
    product_path.write_text(
        json.dumps(to_json(product), ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    report_path = write_binding_report(out_dir / "out.md", product)

    serialized = json.loads(product_path.read_text(encoding="utf-8"))
    report = parse_binding_report(
        json.loads(report_path.read_text(encoding="utf-8"))
    )

    assert report["summary"]["all_arguments_ok"] is True
    assert report["summary"]["fail"] == 0
    assert report["summary"]["pass"] == report["argument_count"]

    source_usage = report["source_usage"]
    seen_ids: list[str] = []

    for arg in report["arguments"]:
        seg = serialized["segments"][arg["segment_index"]]
        assert seg["type"] == "supplement"

        source_ids = list(arg["source_ids"])
        trace_ids = list(arg["trace_source_ids"])
        sources = list(seg["sources"])
        trace_refs = [
            t for t in seg["traceability"] if t.get("kind") == "source"
        ]

        # 至少一個來源
        assert len(source_ids) >= 1
        assert arg["checks"]["at_least_one_source"] is True

        # 無重複
        assert len(source_ids) == len(set(source_ids))
        assert len(trace_ids) == len(set(trace_ids))
        assert arg["checks"]["no_duplicate_sources"] is True

        # 無遺漏／無多餘：source_ids ↔ sources ↔ trace 三向一致
        obj_ids = [s["id"] for s in sources]
        assert obj_ids == source_ids, (
            f"位置不一致: {obj_ids} vs {source_ids}"
        )
        assert trace_ids == source_ids, (
            f"追溯不一致: {trace_ids} vs {source_ids}"
        )
        assert [t["id"] for t in trace_refs] == source_ids
        assert arg["checks"]["no_omitted_traces"] is True
        assert arg["checks"]["no_extra_traces"] is True
        assert arg["checks"]["source_traceable"] is True

        # source_id 欄位一致
        expected_field = f"sources:{','.join(source_ids)}"
        assert seg["source_id"] == expected_field
        assert arg["source_id_field"] == expected_field
        assert arg["checks"]["source_id_field_aligned"] is True

        # 每個位置：ID 一致、片段非空、反向索引正確
        for pos, sid in enumerate(source_ids):
            src_obj = sources[pos]
            assert src_obj["id"] == sid, f"位置{pos}: ID 不一致"
            assert trace_refs[pos]["id"] == sid, (
                f"位置{pos}: trace 不一致"
            )
            fragment = src_obj.get("content") or ""
            assert fragment.strip(), f"來源 {sid!r} content 為空"

            assert sid in source_usage, f"source_usage 遺漏 {sid!r}"
            assert arg["argument_index"] in source_usage[sid]
            seen_ids.append(sid)

        assert arg["binding_ok"] is True
        assert arg["binding_status"] == "pass"
        assert arg["source_count"] == len(source_ids)
        assert arg["cardinality"] in ("one_to_one", "one_to_many")

    # 全域：source_usage 覆蓋所有用過的來源（無重複遺漏）
    assert set(source_usage) == set(seen_ids)
    assert report["summary"]["one_to_one"] >= 1
    assert report["summary"]["one_to_many"] >= 1


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


def test_empty_source_fragment_fails():
    """最小負例：來源 ID 正確但 content 空白 → no_empty_fragments False。"""
    from note_filler.retrieve.models import Source

    src = Source(
        id="law:empty",
        title="行政程序法第 92 條",
        url=None, level="A",
        content="",  # 片段為空
        fetched_date="2026-07-25",
        doc_date=None, distance=0.5,
    )
    gap = Gap("定義？", "missing", "未說明")
    product = assemble_correction(
        _doc(),
        [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("定義[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]
    assert arg["checks"]["no_empty_fragments"] is False
    assert arg["binding_status"] == "fail"
    assert arg["binding_ok"] is False
    assert report["summary"]["fail"] == 1
    assert report["summary"]["all_arguments_ok"] is False


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


# ---- source_usage 反向索引：序列化中可直接看出每個來源對應哪個論點 ------------

def test_source_usage_exists_in_report():
    """binding report 必須包含 source_usage 反向索引。"""
    report = parse_binding_report(build_binding_report(_assemble_one_to_one()))
    assert "source_usage" in report
    assert isinstance(report["source_usage"], dict)


def test_source_usage_one_to_one_reverse():
    """一對一：law:92 被 argument[0] 使用 → source_usage 應為 {"law:92": [0]}。"""
    report = parse_binding_report(build_binding_report(_assemble_one_to_one()))
    assert report["source_usage"] == {"law:92": [0]}


def test_source_usage_one_to_many_reverse():
    """一對多：三個 source 分別對應到 argument[0]。"""
    report = parse_binding_report(build_binding_report(_assemble_one_to_many()))
    su = report["source_usage"]
    assert su == {
        "law:92": [0],
        "law:93": [0],
        "web:abc": [0],
    }


def test_source_usage_mixed_reverse():
    """混合：src_a 被 arg0 用，src_b1/src_b2 被 arg1 用。"""
    report = parse_binding_report(build_binding_report(_assemble_mixed()))
    su = report["source_usage"]
    assert su == {
        "law:92": [0],
        "law:93": [1],
        "law:94": [1],
    }


def test_source_usage_pending_excluded():
    """pending_evidence（無來源）不貢獻 source_usage。"""
    report = parse_binding_report(build_binding_report(_assemble_pending()))
    assert report["source_usage"] == {}


def test_source_usage_validated_by_parse():
    """parse_binding_report 驗證 source_usage 與 arguments 一致。"""
    report = build_binding_report(_assemble_one_to_one())
    report["source_usage"] = {"wrong:id": [0]}
    with pytest.raises(ValueError, match="source_usage 與 arguments 不一致"):
        parse_binding_report(report)


def test_source_usage_rejects_non_dict(tmp_path):
    """malformed source_usage 被 parse 拒絕。"""
    report = build_binding_report(_assemble_mixed())
    report["source_usage"] = "not-a-dict"
    with pytest.raises(ValueError, match="source_usage 必須為 dict"):
        parse_binding_report(report)


def test_source_usage_in_cli_output(tmp_path, monkeypatch):
    """CLI process_file 寫出的 binding_report.json 包含 source_usage。"""
    from note_filler import __main__ as cli
    from note_filler.correction import CorrectionDoc

    note = tmp_path / "note.txt"
    note.write_text("一、標題\n內容", encoding="utf-8")
    product = _assemble_one_to_many()

    class _FakePipelineDoc:
        def __init__(self, inner: CorrectionDoc):
            self.original = inner.original
            self.segments = inner.segments

    monkeypatch.setattr(cli, "run_pipeline", lambda *a, **k: _FakePipelineDoc(product))
    monkeypatch.setattr(cli, "to_markdown", lambda doc: "# 訂正稿\n有內容。")

    r = cli.process_file(note, None, None, None, out_dir=None, fmt="md")
    from pathlib import Path
    report_path = Path(r["output"]).parent / "binding_report.json"
    import json
    parsed = parse_binding_report(json.loads(report_path.read_text(encoding="utf-8")))
    assert "source_usage" in parsed
    assert parsed["source_usage"] == {"law:92": [0], "law:93": [0], "web:abc": [0]}


def test_source_usage_rejects_invalid_indices():
    """source_usage 的 argument_index 超出範圍時 parse 應拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    report["source_usage"] = {"law:92": [99]}
    with pytest.raises(ValueError, match="source_usage 與 arguments 不一致"):
        parse_binding_report(report)
