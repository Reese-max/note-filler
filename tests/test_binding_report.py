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
    REQUIRED_ARGUMENT_ANGLE_KEYS,
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


def _assemble_repeated_angles(count: int = 2):
    questions = [
        "行政處分如何定義？",
        "行政處分如何定義!",
        "行政處分如何定義。",
    ][:count]
    gaps = [Gap(q, "missing", f"未說明 {i}") for i, q in enumerate(questions)]
    sources = [
        _source(f"law:{92 + i}", f"行政程序法第 {92 + i} 條")
        for i in range(count)
    ]
    return assemble_correction(
        _doc(),
        gaps,
        {gap.question: [src] for gap, src in zip(gaps, sources)},
        {
            gap.question: WrittenSupplement(f"定義 {i}[^1]。", [src.id])
            for i, (gap, src) in enumerate(zip(gaps, sources))
        },
        {
            gap.question: cross_validate(gap.question, [src])
            for gap, src in zip(gaps, sources)
        },
    )


def _assemble_same_topic_distinct_angles():
    """同一主題（行政處分）下兩個不同且不重複的有效角度：定義＋限制。"""
    src_a = _source("law:92", "行政程序法第 92 條")
    src_b = _source("law:93", "行政程序法第 93 條")
    gap_a = Gap("行政處分如何定義？", "missing", "未說明定義")
    gap_b = Gap("行政處分有何限制？", "missing", "未說明限制")
    return assemble_correction(
        _doc(),
        [gap_a, gap_b],
        {gap_a.question: [src_a], gap_b.question: [src_b]},
        {
            gap_a.question: WrittenSupplement("定義參照[^1]。", [src_a.id]),
            gap_b.question: WrittenSupplement("限制參照[^1]。", [src_b.id]),
        },
        {
            gap_a.question: cross_validate(gap_a.question, [src_a]),
            gap_b.question: cross_validate(gap_b.question, [src_b]),
        },
    )


def _assemble_synonym_angles():
    """同主題、同定義角度、高 token 重疊 → 同義，有效角度塌縮為 1。"""
    src_a = _source("law:92", "行政程序法第 92 條")
    src_b = _source("law:93", "行政程序法第 93 條")
    gap_a = Gap("行政處分之定義為何？", "missing", "未說明定義")
    gap_b = Gap("行政處分定義如何說明？", "missing", "未說明定義細節")
    return assemble_correction(
        _doc(),
        [gap_a, gap_b],
        {gap_a.question: [src_a], gap_b.question: [src_b]},
        {
            gap_a.question: WrittenSupplement("定義一[^1]。", [src_a.id]),
            gap_b.question: WrittenSupplement("定義二[^1]。", [src_b.id]),
        },
        {
            gap_a.question: cross_validate(gap_a.question, [src_a]),
            gap_b.question: cross_validate(gap_b.question, [src_b]),
        },
    )


# ---- 格式可直接由測試解析 ---------------------------------------------------

def test_schema_is_machine_parseable():
    report = build_binding_report(_assemble_one_to_one())
    parsed = parse_binding_report(report)
    assert parsed["schema"] == SCHEMA_ID
    assert parsed["argument_count"] == 1
    assert isinstance(parsed["arguments"], list)


def test_parse_rejects_missing_keys():
    with pytest.raises(ValueError, match="缺少欄位"):
        parse_binding_report({"schema": SCHEMA_ID})


def test_parse_rejects_wrong_schema():
    report = build_binding_report(_assemble_one_to_one())
    report["schema"] = "other.v0"
    with pytest.raises(ValueError, match="schema 不符"):
        parse_binding_report(report)


def test_parse_rejects_field_drift_extra_top_key():
    """欄位漂移：頂層多出未知鍵 → 拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    report["unexpected_top"] = True
    with pytest.raises(ValueError, match="欄位漂移"):
        parse_binding_report(report)


def test_parse_rejects_field_drift_extra_argument_key():
    """欄位漂移：arguments 多出未知鍵 → 拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    report["arguments"][0]["legacy_score"] = 0.9
    with pytest.raises(ValueError, match="欄位漂移"):
        parse_binding_report(report)


def test_parse_rejects_field_drift_extra_check_key():
    """欄位漂移：checks 多出未知鍵 → 拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    report["arguments"][0]["checks"]["legacy_ok"] = True
    with pytest.raises(ValueError, match="欄位漂移"):
        parse_binding_report(report)


def test_parse_rejects_missing_necessity_argument_keys():
    """缺欄：去掉 functional_gap／user_value → 拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    del report["arguments"][0]["functional_gap"]
    with pytest.raises(ValueError, match="缺少欄位"):
        parse_binding_report(report)
    report = build_binding_report(_assemble_one_to_one())
    del report["arguments"][0]["user_value"]
    with pytest.raises(ValueError, match="缺少欄位"):
        parse_binding_report(report)


def test_parse_rejects_empty_structural_string_fields():
    """結構性空欄：confidence 空白 → 拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    report["arguments"][0]["confidence"] = "   "
    with pytest.raises(ValueError, match="不可為空欄"):
        parse_binding_report(report)


def test_parse_rejects_empty_source_id_elements():
    """結構性空欄：source_ids 含空字串 → 拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    report["arguments"][0]["source_ids"] = ["law:92", ""]
    report["arguments"][0]["source_count"] = 2
    # source_usage 一併改壞以免先被其他規則擋
    report["source_usage"] = {"law:92": [0], "": [0]}
    with pytest.raises(ValueError, match="不可含空字串"):
        parse_binding_report(report)


def test_empty_functional_gap_fails_even_when_sources_traceable():
    """來源可追溯但 functional_gap 空欄 → binding_ok False，checks 點名缺失。"""
    product = _assemble_one_to_one()
    product.segments[1].functional_gap = ""
    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]
    assert arg["checks"]["at_least_one_source"] is True
    assert arg["checks"]["source_traceable"] is True
    assert arg["checks"]["has_functional_gap"] is False
    assert arg["binding_ok"] is False
    assert arg["binding_status"] == "fail"
    assert report["summary"]["all_arguments_ok"] is False


def test_empty_user_value_fails_even_when_sources_traceable():
    """來源可追溯但 user_value 空欄 → binding_ok False，checks 點名缺失。"""
    product = _assemble_one_to_one()
    product.segments[1].user_value = "  "
    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]
    assert arg["checks"]["at_least_one_source"] is True
    assert arg["checks"]["source_traceable"] is True
    assert arg["checks"]["has_user_value"] is False
    assert arg["binding_ok"] is False
    assert arg["binding_status"] == "fail"


def test_parse_rejects_empty_necessity_marked_as_pass():
    """空欄卻標 pass／has_* True → 解析器拒絕（防止假完成報告）。"""
    report = build_binding_report(_assemble_one_to_one())
    report["arguments"][0]["functional_gap"] = ""
    report["arguments"][0]["checks"]["has_functional_gap"] = True
    report["arguments"][0]["binding_ok"] = True
    report["arguments"][0]["binding_status"] = "pass"
    with pytest.raises(ValueError, match="functional_gap 為空欄"):
        parse_binding_report(report)


def test_assembled_arguments_include_nonempty_necessity_views():
    """assemble 產出的論點必須自帶非空必要性雙視角，避免後續遺失。"""
    for product in (
        _assemble_one_to_one(),
        _assemble_one_to_many(),
        _assemble_mixed(),
        _assemble_pending(),
    ):
        report = parse_binding_report(build_binding_report(product))
        for arg in report["arguments"]:
            assert arg["functional_gap"].strip(), arg
            assert arg["user_value"].strip(), arg
            assert arg["checks"]["has_functional_gap"] is True
            assert arg["checks"]["has_user_value"] is True
            assert arg["binding_ok"] is True


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
        expected_angle_types = {
            "angle_tags": list,
            "valid_angle_count": int,
            "deduped_angle_count": int,
            "duplicate_angles": list,
        }
        for field, expected_type in expected_angle_types.items():
            assert type(arg[field]) is expected_type
            assert type(seg[field]) is expected_type
            assert seg[field] == arg[field]
        assert all(isinstance(tag, str) for tag in arg["angle_tags"])
        assert all(isinstance(angle, str) for angle in arg["duplicate_angles"])

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
    from note_filler.binding_report import REQUIRED_CHECK_KEYS

    report = parse_binding_report(build_binding_report(_assemble_mixed()))
    for arg in report["arguments"]:
        c = arg["checks"]
        assert set(c) == set(REQUIRED_CHECK_KEYS)
        # 有來源的論點：綁定三項 + 必要性雙視角皆 True
        if arg["cardinality"] != "none":
            assert c["at_least_one_source"] is True
            assert c["source_traceable"] is True
            assert c["no_duplicate_sources"] is True
            assert c["no_omitted_traces"] is True
            assert c["no_extra_traces"] is True
            assert c["has_functional_gap"] is True
            assert c["has_user_value"] is True
            assert c["has_angle_coverage"] is True
            assert c["meets_angle_coverage_threshold"] is True


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


# ---- 角度覆蓋（angle_coverage）-----------------------------------------------


def test_argument_exposes_angle_coverage_structure():
    """每個論點必須含可機器解析的 angle_coverage（type／labels／facets／key／relation）。"""
    from note_filler.binding_report import (
        REQUIRED_ANGLE_COVERAGE_KEYS,
        REQUIRED_ANGLE_RELATION_KEYS,
        REQUIRED_ANGLE_SUMMARY_KEYS,
        REQUIRED_DUPLICATE_EXCLUSION_KEYS,
    )

    report = parse_binding_report(build_binding_report(_assemble_mixed()))
    assert set(report["angle_coverage_summary"]) == set(REQUIRED_ANGLE_SUMMARY_KEYS)
    assert report["angle_coverage_summary"]["argument_count_with_angles"] == 2

    for arg in report["arguments"]:
        ac = arg["angle_coverage"]
        assert set(REQUIRED_ARGUMENT_ANGLE_KEYS) <= set(arg)
        assert arg["argument_id"] == f"argument:{arg['argument_index']}"
        assert arg["angle_tags"] == ac["angle_labels"]
        assert arg["valid_angle_count"] == 1
        assert arg["deduped_angle_count"] == 1
        assert arg["duplicate_angles"] == []
        assert set(ac) == set(REQUIRED_ANGLE_COVERAGE_KEYS)
        assert ac["angle_type"].strip()
        assert isinstance(ac["angle_labels"], list) and ac["angle_labels"]
        assert isinstance(ac["covered_facets"], list) and ac["covered_facets"]
        assert ac["angle_key"].strip()
        assert set(ac["relation"]) == set(REQUIRED_ANGLE_RELATION_KEYS)
        assert ac["relation"]["kind"] in ("unique", "duplicate", "synonym")
        assert ac["effective_angle_count"] == 1
        assert set(ac["duplicate_exclusion"]) == set(
            REQUIRED_DUPLICATE_EXCLUSION_KEYS
        )
        assert ac["duplicate_exclusion"]["excluded"] is False
        assert arg["checks"]["has_angle_coverage"] is True
        assert arg["checks"]["meets_angle_coverage_threshold"] is True


def test_assemble_classifies_definition_and_limitation_angles():
    """assemble 依問題關鍵詞寫入 angle_type／labels／key，可讀出不同面向。"""
    product = _assemble_mixed()  # 定義？ / 附款限制？
    supps = [s for s in product.segments if s.type == "supplement"]
    assert supps[0].angle_type == "definition"
    assert "definition" in supps[0].angle_labels
    assert "functional_gap" in supps[0].angle_labels
    assert "user_value" in supps[0].angle_labels
    assert supps[0].angle_key.startswith("definition:")

    assert supps[1].angle_type == "limitation"
    assert "limitation" in supps[1].angle_labels
    assert supps[1].angle_key.startswith("limitation:")

    report = parse_binding_report(build_binding_report(product))
    types = {a["angle_coverage"]["angle_type"] for a in report["arguments"]}
    assert types == {"definition", "limitation"}
    facets_union = report["angle_coverage_summary"]["covered_facets_union"]
    assert "angle:definition" in facets_union
    assert "angle:limitation" in facets_union
    assert "necessity:functional_gap" in facets_union
    assert "necessity:user_value" in facets_union


def test_same_topic_two_distinct_valid_angles_pass_acceptance(tmp_path):
    """正例：同一主題至少兩個不同且不重複的有效角度 → 驗收通過且可寫入。"""
    product = _assemble_same_topic_distinct_angles()
    supps = [s for s in product.segments if s.type == "supplement"]
    assert len(supps) == 2
    assert supps[0].angle_type == "definition"
    assert supps[1].angle_type == "limitation"
    assert supps[0].angle_key != supps[1].angle_key

    report = parse_binding_report(build_binding_report(product))
    summary = report["angle_coverage_summary"]
    types = {a["angle_coverage"]["angle_type"] for a in report["arguments"]}
    keys = {a["angle_coverage"]["angle_key"] for a in report["arguments"]}
    assert types == {"definition", "limitation"}
    assert len(keys) == 2
    assert [
        a["angle_coverage"]["relation"]["kind"] for a in report["arguments"]
    ] == ["unique", "unique"]
    assert [
        a["angle_coverage"]["effective_angle_count"] for a in report["arguments"]
    ] == [1, 1]
    assert summary["effective_angle_count"] == 2
    assert summary["required_effective_angle_count"] == 2
    assert summary["excluded_angle_count"] == 0
    assert summary["duplicate_pairs"] == []
    assert summary["synonym_pairs"] == []
    assert summary["has_sufficient_angles"] is True
    assert summary["has_acceptable_duplicate_ratio"] is True
    assert summary["coverage_ok"] is True
    assert report["summary"]["all_arguments_ok"] is True
    assert all(a["binding_status"] == "pass" for a in report["arguments"])
    assert all(a["checks"]["meets_angle_coverage_threshold"] is True for a in report["arguments"])
    assert all(a["checks"]["has_angle_coverage"] is True for a in report["arguments"])
    # 必要性雙視角與來源綁定不得因角度門檻而弱化
    for a in report["arguments"]:
        assert a["checks"]["at_least_one_source"] is True
        assert a["checks"]["source_traceable"] is True
        assert a["checks"]["has_functional_gap"] is True
        assert a["checks"]["has_user_value"] is True
        assert a["functional_gap"].strip()
        assert a["user_value"].strip()

    report_path = write_binding_report(tmp_path / "out.md", product)
    assert report_path.is_file()
    persisted = parse_binding_report(
        json.loads(report_path.read_text(encoding="utf-8"))
    )
    assert persisted["angle_coverage_summary"]["coverage_ok"] is True
    assert persisted["angle_coverage_summary"]["effective_angle_count"] == 2


def test_angle_duplicate_detection_same_key():
    """相同 angle_key 的兩個論點 → relation.kind=duplicate，summary 有 pair。"""
    product = _assemble_repeated_angles()
    supps = [s for s in product.segments if s.type == "supplement"]
    assert len(supps) == 2
    assert supps[0].angle_key == supps[1].angle_key
    assert supps[0].angle_key.startswith("definition:")
    assert [s.angle_tags for s in supps] == [s.angle_labels for s in supps]
    assert [s.valid_angle_count for s in supps] == [1, 1]
    assert [s.deduped_angle_count for s in supps] == [1, 0]
    assert [s.duplicate_angles for s in supps] == [
        [supps[1].angle_key],
        [supps[0].angle_key],
    ]

    report = parse_binding_report(build_binding_report(product))
    assert (
        report["arguments"][0]["angle_coverage"]["angle_key"]
        == report["arguments"][1]["angle_coverage"]["angle_key"]
    )
    assert report["arguments"][0]["angle_coverage"]["relation"]["kind"] == "duplicate"
    assert report["arguments"][1]["angle_coverage"]["relation"]["kind"] == "duplicate"
    assert 1 in report["arguments"][0]["angle_coverage"]["relation"]["duplicate_of"]
    assert 0 in report["arguments"][1]["angle_coverage"]["relation"]["duplicate_of"]
    assert [0, 1] in report["angle_coverage_summary"]["duplicate_pairs"]
    assert [
        arg["angle_coverage"]["effective_angle_count"]
        for arg in report["arguments"]
    ] == [1, 0]
    assert report["angle_coverage_summary"]["has_sufficient_angles"] is False
    assert report["angle_coverage_summary"]["coverage_ok"] is False
    assert report["summary"]["all_arguments_ok"] is False
    assert all(arg["binding_status"] == "fail" for arg in report["arguments"])


def test_single_or_duplicate_angles_fail_acceptance(tmp_path):
    """負例：只有單一有效角度（精確重複或同義去重）→ 判定不合格並拒絕寫入驗收。"""
    # 精確重複角度
    dup_report = parse_binding_report(build_binding_report(_assemble_repeated_angles()))
    dup_summary = dup_report["angle_coverage_summary"]
    assert dup_summary["effective_angle_count"] == 1
    assert dup_summary["required_effective_angle_count"] == 2
    assert dup_summary["has_sufficient_angles"] is False
    assert dup_summary["coverage_ok"] is False
    assert dup_report["summary"]["all_arguments_ok"] is False
    assert all(a["binding_status"] == "fail" for a in dup_report["arguments"])
    assert all(
        a["checks"]["meets_angle_coverage_threshold"] is False
        for a in dup_report["arguments"]
    )
    with pytest.raises(RuntimeError, match="角度有效性驗收失敗"):
        write_binding_report(tmp_path / "dup.md", _assemble_repeated_angles())
    dup_path = tmp_path / BINDING_REPORT_NAME
    assert dup_path.is_file()
    persisted_dup = json.loads(dup_path.read_text(encoding="utf-8"))
    assert persisted_dup["angle_coverage_summary"]["coverage_ok"] is False
    assert persisted_dup["angle_coverage_summary"]["effective_angle_count"] == 1

    # 同義／單一角度（兩論點塌縮為 1 個有效角度）
    syn_product = _assemble_synonym_angles()
    syn_report = parse_binding_report(build_binding_report(syn_product))
    syn_summary = syn_report["angle_coverage_summary"]
    assert [
        a["angle_coverage"]["relation"]["kind"] for a in syn_report["arguments"]
    ] == ["synonym", "synonym"]
    assert [
        a["angle_coverage"]["effective_angle_count"] for a in syn_report["arguments"]
    ] == [1, 0]
    assert syn_summary["effective_angle_count"] == 1
    assert syn_summary["required_effective_angle_count"] == 2
    assert syn_summary["has_sufficient_angles"] is False
    assert syn_summary["coverage_ok"] is False
    assert syn_report["summary"]["all_arguments_ok"] is False
    assert all(a["binding_status"] == "fail" for a in syn_report["arguments"])
    with pytest.raises(RuntimeError, match="角度有效性驗收失敗"):
        write_binding_report(tmp_path / "syn.md", syn_product)


def test_sources_ok_but_angles_insufficient_or_duplicate_fails_explicitly(tmp_path):
    """最小負例：來源綁定正確，但角度不足／角度重複 → 流程明確失敗。

    鎖定雙閘隔離：來源 checks 全過仍不得因「只驗來源」而放行不完整輸出；
    角度門檻未過時 binding_ok／all_arguments_ok 必須為 False，且 write 拒絕驗收。
    """
    # --- 精確重複角度（有效角度塌縮為 1）---
    product_dup = _assemble_repeated_angles()
    report_dup = parse_binding_report(build_binding_report(product_dup))
    summary_dup = report_dup["angle_coverage_summary"]

    assert report_dup["argument_count"] == 2
    assert [
        a["angle_coverage"]["relation"]["kind"] for a in report_dup["arguments"]
    ] == ["duplicate", "duplicate"]
    assert summary_dup["effective_angle_count"] == 1
    assert summary_dup["required_effective_angle_count"] == 2
    assert summary_dup["has_sufficient_angles"] is False
    assert summary_dup["coverage_ok"] is False

    for arg in report_dup["arguments"]:
        c = arg["checks"]
        # 來源綁定正確：不得因角度失敗而假性把來源也標壞
        assert arg["cardinality"] == "one_to_one"
        assert arg["source_count"] == 1
        assert arg["source_ids"]  # 有實際引用來源
        assert c["at_least_one_source"] is True
        assert c["source_traceable"] is True
        assert c["no_duplicate_sources"] is True
        assert c["no_omitted_traces"] is True
        assert c["no_extra_traces"] is True
        assert c["source_id_field_aligned"] is True
        assert c["no_empty_fragments"] is True
        assert c["has_functional_gap"] is True
        assert c["has_user_value"] is True
        # 單點 facet 結構完整，但跨論點有效角度不足
        assert c["has_angle_coverage"] is True
        assert c["angle_facet_complete"] is True
        assert c["meets_angle_coverage_threshold"] is False
        assert arg["binding_ok"] is False
        assert arg["binding_status"] == "fail"

    assert report_dup["summary"]["fail"] == 2
    assert report_dup["summary"]["all_arguments_ok"] is False
    with pytest.raises(RuntimeError, match="角度有效性驗收失敗") as ei_dup:
        write_binding_report(tmp_path / "src-ok-angle-dup.md", product_dup)
    dup_msg = str(ei_dup.value)
    assert "被排除的角度欄位" in dup_msg or "僅單一有效角度" in dup_msg
    persisted_dup = json.loads(
        (tmp_path / BINDING_REPORT_NAME).read_text(encoding="utf-8")
    )
    assert persisted_dup["angle_coverage_summary"]["coverage_ok"] is False
    assert persisted_dup["summary"]["all_arguments_ok"] is False

    # --- 同義角度（同樣有效角度不足）---
    product_syn = _assemble_synonym_angles()
    report_syn = parse_binding_report(build_binding_report(product_syn))
    summary_syn = report_syn["angle_coverage_summary"]
    assert [
        a["angle_coverage"]["relation"]["kind"] for a in report_syn["arguments"]
    ] == ["synonym", "synonym"]
    assert summary_syn["effective_angle_count"] == 1
    assert summary_syn["coverage_ok"] is False
    for arg in report_syn["arguments"]:
        c = arg["checks"]
        assert c["at_least_one_source"] is True
        assert c["source_traceable"] is True
        assert c["meets_angle_coverage_threshold"] is False
        assert arg["binding_ok"] is False
        assert arg["binding_status"] == "fail"
        assert arg["angle_field_issues"], "同義／單一角度應列出缺少或被排除欄位"
    assert report_syn["summary"]["all_arguments_ok"] is False
    with pytest.raises(RuntimeError, match="角度有效性驗收失敗"):
        write_binding_report(tmp_path / "src-ok-angle-syn.md", product_syn)


def test_angles_complete_but_sources_missing_fails_explicitly():
    """最小負例：角度齊全（兩相異有效角度）但來源缺失 → 流程明確失敗。

    鎖定雙閘隔離：角度 coverage_ok 仍不得因「只驗角度」而放行無來源輸出；
    來源 checks 必須標 False，binding_status=fail，且 require_traceable 硬失敗。
    """
    from note_filler.pipeline import require_traceable_note_product

    product = _assemble_same_topic_distinct_angles()
    # 先確認正例本體角度齊全且來源正確
    good = parse_binding_report(build_binding_report(product))
    assert good["angle_coverage_summary"]["coverage_ok"] is True
    assert good["angle_coverage_summary"]["effective_angle_count"] == 2
    assert good["summary"]["all_arguments_ok"] is True

    # 剝除來源：模擬「角度欄位齊全、來源未綁定」的不完整輸出
    stripped_ids: list[str] = []
    for seg in product.segments:
        if seg.type != "supplement":
            continue
        assert seg.sources, "前置組裝必須有來源才可構造來源缺失負例"
        stripped_ids.extend(s.id for s in seg.sources)
        seg.sources = []
        seg.traceability = []
        seg.source_id = "sources:stripped-missing"
        seg.confidence = "verified"  # 非 pending → 不可當待補證放行

    assert len(stripped_ids) >= 2
    report = parse_binding_report(build_binding_report(product))
    angle_summary = report["angle_coverage_summary"]

    # 角度齊全：定義＋限制，facet 完整，門檻通過
    assert report["argument_count"] == 2
    assert {
        a["angle_coverage"]["angle_type"] for a in report["arguments"]
    } == {"definition", "limitation"}
    assert [
        a["angle_coverage"]["relation"]["kind"] for a in report["arguments"]
    ] == ["unique", "unique"]
    assert angle_summary["effective_angle_count"] == 2
    assert angle_summary["required_effective_angle_count"] == 2
    assert angle_summary["has_sufficient_angles"] is True
    assert angle_summary["coverage_ok"] is True

    for arg in report["arguments"]:
        c = arg["checks"]
        # 來源缺失：至少一源／可追溯必須失敗
        assert arg["cardinality"] == "none"
        assert arg["source_count"] == 0
        assert arg["source_ids"] == []
        assert c["at_least_one_source"] is False
        assert c["source_traceable"] is False
        assert c["source_id_field_aligned"] is False
        # 角度仍齊全——證明失敗不是角度閘造成
        assert c["has_angle_coverage"] is True
        assert c["angle_facet_complete"] is True
        assert c["meets_angle_coverage_threshold"] is True
        assert c["has_functional_gap"] is True
        assert c["has_user_value"] is True
        assert arg["binding_ok"] is False
        assert arg["binding_status"] == "fail"

    assert report["summary"]["fail"] == 2
    assert report["summary"]["pass"] == 0
    assert report["summary"]["all_arguments_ok"] is False
    assert report["source_usage"] == {}

    # 末端追溯閘必須明確 raise，避免默默產出不完整成品
    with pytest.raises(RuntimeError, match="來源追溯驗證失敗") as ei:
        require_traceable_note_product(product, source="neg-angles-ok-sources-missing")
    msg = str(ei.value)
    assert "source_id" in msg or "對應失敗" in msg or "pending:gap:" in msg, (
        f"失敗訊息應指出來源綁定缺口，實際：{msg!r}"
    )


def test_excessive_angle_repetition_fails_acceptance():
    report = parse_binding_report(build_binding_report(_assemble_repeated_angles(3)))
    summary = report["angle_coverage_summary"]
    assert summary["effective_angle_count"] == 1
    assert summary["excluded_angle_count"] == 2
    assert summary["duplicate_ratio"] == 2 / 3
    assert summary["has_acceptable_duplicate_ratio"] is False
    assert summary["coverage_ok"] is False
    assert report["summary"]["fail"] == 3
    assert report["summary"]["all_arguments_ok"] is False


def test_parse_rejects_tampered_angle_measurement_and_summary():
    report = build_binding_report(_assemble_mixed())
    report["arguments"][0]["angle_coverage"]["effective_angle_count"] = 0
    with pytest.raises(ValueError, match="角度量測不一致"):
        parse_binding_report(report)

    report = build_binding_report(_assemble_mixed())
    report["angle_coverage_summary"]["effective_angle_count"] = 0
    with pytest.raises(ValueError, match="角度覆蓋摘要不一致"):
        parse_binding_report(report)

    report = build_binding_report(_assemble_repeated_angles())
    report["summary"]["all_arguments_ok"] = True
    with pytest.raises(ValueError, match="驗收摘要不一致"):
        parse_binding_report(report)


def test_write_binding_report_persists_metrics_then_fails_angle_gate(tmp_path):
    path = tmp_path / "binding_report.json"
    with pytest.raises(RuntimeError, match="角度有效性驗收失敗") as ei:
        write_binding_report(path, _assemble_repeated_angles(3))
    assert "被排除的角度欄位" in str(ei.value) or "僅單一有效角度" in str(ei.value)

    report_path = tmp_path / BINDING_REPORT_NAME
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["angle_coverage_summary"]["coverage_ok"] is False
    assert report["angle_coverage_summary"]["effective_angle_count"] == 1


def test_missing_angle_fields_fail_with_explicit_field_names(tmp_path):
    """來源綁定正確但角度欄位缺失 → 明確失敗並指出缺少的角度欄位。"""
    product = _assemble_same_topic_distinct_angles()
    # 剝除第一論點的 functional_gap／user_value → 角度 facet 缺失
    for seg in product.segments:
        if seg.type != "supplement":
            continue
        seg.functional_gap = ""
        seg.user_value = ""
        break

    report = parse_binding_report(build_binding_report(product))
    arg0 = report["arguments"][0]
    # 來源不得因角度失敗而被假性標壞
    assert arg0["checks"]["at_least_one_source"] is True
    assert arg0["checks"]["source_traceable"] is True
    assert arg0["checks"]["angle_facet_complete"] is False
    assert arg0["binding_ok"] is False
    assert arg0["binding_status"] == "fail"
    issues = arg0["angle_field_issues"]
    assert any("functional_gap" in i for i in issues)
    assert any("user_value" in i for i in issues)
    assert any("缺少角度欄位" in i for i in issues)

    with pytest.raises(RuntimeError, match="角度有效性驗收失敗") as ei:
        write_binding_report(tmp_path / "missing-angle-fields.md", product)
    msg = str(ei.value)
    assert "functional_gap" in msg
    assert "user_value" in msg or "缺少角度欄位" in msg
    persisted = json.loads((tmp_path / BINDING_REPORT_NAME).read_text(encoding="utf-8"))
    assert persisted["arguments"][0]["angle_field_issues"]
    assert persisted["summary"]["all_arguments_ok"] is False


def test_excluded_synonym_angles_list_excluded_fields_and_keep_source_checks():
    """同義角度被排除時必須指出 excluded angle_key，且來源 checks 不退化。"""
    report = parse_binding_report(build_binding_report(_assemble_synonym_angles()))
    assert report["angle_coverage_summary"]["coverage_ok"] is False

    kept = report["arguments"][0]
    excluded = report["arguments"][1]
    assert kept["angle_coverage"]["duplicate_exclusion"]["excluded"] is False
    assert excluded["angle_coverage"]["duplicate_exclusion"]["excluded"] is True
    assert excluded["angle_coverage"]["duplicate_exclusion"]["reason"] == "synonym"

    assert any("僅單一有效角度" in i for i in kept["angle_field_issues"])
    assert any("被排除的角度欄位" in i for i in excluded["angle_field_issues"])
    assert any("reason=synonym" in i for i in excluded["angle_field_issues"])
    assert any(
        excluded["angle_coverage"]["angle_key"] in i
        for i in excluded["angle_field_issues"]
    )

    for arg in report["arguments"]:
        c = arg["checks"]
        assert c["at_least_one_source"] is True
        assert c["source_traceable"] is True
        assert c["no_duplicate_sources"] is True
        assert c["no_omitted_traces"] is True
        assert c["no_extra_traces"] is True
        assert c["source_id_field_aligned"] is True
        assert c["no_empty_fragments"] is True
        assert arg["binding_status"] == "fail"
        assert arg["binding_ok"] is False


def test_angle_synonym_detection_same_type_overlapping_tokens():
    """同 angle_type、不同 key、高 token 重疊 → synonym，且有效角度不足而不合格。"""
    product = _assemble_synonym_angles()
    report = parse_binding_report(build_binding_report(product))
    a0 = report["arguments"][0]["angle_coverage"]
    a1 = report["arguments"][1]["angle_coverage"]
    assert a0["angle_type"] == a1["angle_type"] == "definition"
    assert a0["angle_key"] != a1["angle_key"]
    assert a0["relation"]["kind"] == "synonym"
    assert a1["relation"]["kind"] == "synonym"
    assert [0, 1] in report["angle_coverage_summary"]["synonym_pairs"]
    assert report["angle_coverage_summary"]["effective_angle_count"] == 1
    assert report["angle_coverage_summary"]["has_sufficient_angles"] is False
    assert report["angle_coverage_summary"]["coverage_ok"] is False
    assert report["summary"]["all_arguments_ok"] is False


def test_parse_rejects_missing_angle_coverage_key():
    """缺 angle_coverage 欄位 → 拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    del report["arguments"][0]["angle_coverage"]
    with pytest.raises(ValueError, match="缺少欄位"):
        parse_binding_report(report)


def test_parse_rejects_missing_angle_coverage_summary():
    """缺 angle_coverage_summary → 拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    del report["angle_coverage_summary"]
    with pytest.raises(ValueError, match="缺少欄位"):
        parse_binding_report(report)


def test_parse_rejects_empty_angle_type():
    """angle_type 空欄 → 拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    report["arguments"][0]["angle_coverage"]["angle_type"] = "  "
    with pytest.raises(ValueError, match="angle_type 不可為空欄"):
        parse_binding_report(report)


def test_parse_rejects_angle_coverage_field_drift():
    """角度覆蓋欄位名稱或型別漂移 → 拒絕。"""
    report = build_binding_report(_assemble_one_to_one())
    report["arguments"][0]["angle_coverage"]["legacy_score"] = 1
    with pytest.raises(ValueError, match="欄位漂移"):
        parse_binding_report(report)

    invalid_values = {
        "angle_tags": "definition",
        "valid_angle_count": True,
        "deduped_angle_count": 1.0,
        "duplicate_angles": [0],
    }
    for field, invalid in invalid_values.items():
        report = build_binding_report(_assemble_one_to_one())
        report["arguments"][0][field] = invalid
        with pytest.raises(ValueError, match=field):
            parse_binding_report(report)


def test_json_export_includes_angle_coverage():
    """to_json 序列化每段含 angle_coverage，頂層含 angle_coverage_summary。"""
    data = to_json(_assemble_mixed())
    assert "angle_coverage_summary" in data
    assert isinstance(data["angle_coverage_summary"].get("unique_angle_types"), list)
    for seg in data["segments"]:
        assert "angle_coverage" in seg
        if seg["type"] == "supplement":
            ac = seg["angle_coverage"]
            assert seg["angle_tags"] == ac["angle_labels"]
            assert ac["angle_type"].strip()
            assert ac["angle_labels"]
            assert ac["covered_facets"]
            assert ac["angle_key"].strip()
            assert "relation" in ac
            assert ac["effective_angle_count"] in (0, 1)
            assert "duplicate_exclusion" in ac


def _assemble_multi_angle_with_one_to_many():
    """同主題 ≥2 個不同且不重複有效角度，且其中一則為一對多來源。"""
    src_def = _source("law:92", "行政程序法第 92 條")
    src_lim_a = _source("law:93", "行政程序法第 93 條")
    src_lim_b = _source("law:94", "行政程序法第 94 條", level="B")
    gap_def = Gap("行政處分如何定義？", "missing", "原稿未定義行政處分")
    gap_lim = Gap("行政處分有何限制？", "missing", "原稿未說明附款限制")
    return assemble_correction(
        _doc(),
        [gap_def, gap_lim],
        {
            gap_def.question: [src_def],
            gap_lim.question: [src_lim_a, src_lim_b],
        },
        {
            gap_def.question: WrittenSupplement(
                "行政處分定義參照[^1]。", [src_def.id]
            ),
            gap_lim.question: WrittenSupplement(
                "附款限制須兼顧目的[^1][^2]。",
                [src_lim_a.id, src_lim_b.id],
            ),
        },
        {
            gap_def.question: cross_validate(gap_def.question, [src_def]),
            gap_lim.question: cross_validate(
                gap_lim.question, [src_lim_a, src_lim_b]
            ),
        },
    )


def test_positive_acceptance_multi_angle_and_one_to_many_count_consistency(
    tmp_path,
):
    """正向驗收：直接讀最終成品／綁定報告。

    斷言至少一則論點同時處於：
      - 筆記層 ≥2 個不同且不重複的有效角度（definition + limitation）
      - 該論點 cardinality=one_to_many 且 source_count≥2
    並逐筆核對角度數與來源清單在成品 JSON、binding_report 兩端完全一致。
    """
    product = _assemble_multi_angle_with_one_to_many()
    product_path = tmp_path / "note_product.json"
    product_path.write_text(
        json.dumps(to_json(product), ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    report_path = write_binding_report(tmp_path / "out.md", product)
    assert product_path.is_file()
    assert report_path.is_file()

    # 只靠落盤輸出驗收，不依賴記憶體 product
    serialized = json.loads(product_path.read_text(encoding="utf-8"))
    report = parse_binding_report(
        json.loads(report_path.read_text(encoding="utf-8"))
    )

    assert report["summary"]["all_arguments_ok"] is True
    assert report["summary"]["fail"] == 0
    assert report["argument_count"] == 2

    # 兩個以上不同且不重複的有效角度（筆記層）
    angle_summary = report["angle_coverage_summary"]
    product_angle_summary = serialized["angle_coverage_summary"]
    assert set(angle_summary["unique_angle_types"]) == {
        "definition",
        "limitation",
    }
    assert angle_summary["effective_angle_count"] >= 2
    assert (
        angle_summary["effective_angle_count"]
        == product_angle_summary["effective_angle_count"]
    )
    assert angle_summary["required_effective_angle_count"] == 2
    assert angle_summary["excluded_angle_count"] == 0
    assert angle_summary["duplicate_pairs"] == []
    assert angle_summary["synonym_pairs"] == []
    assert angle_summary["has_sufficient_angles"] is True
    assert angle_summary["coverage_ok"] is True
    assert product_angle_summary["coverage_ok"] is True

    # 至少一則一對多來源綁定
    one_to_many_args = [
        a for a in report["arguments"] if a["cardinality"] == "one_to_many"
    ]
    assert len(one_to_many_args) >= 1
    assert report["summary"]["one_to_many"] == len(one_to_many_args)
    assert report["summary"]["one_to_one"] + report["summary"]["one_to_many"] == (
        report["argument_count"]
    )

    # 至少一個論點同時滿足：位於多有效角度集合內 + 一對多來源
    multi_angle_keys = {
        a["angle_coverage"]["angle_key"]
        for a in report["arguments"]
        if a["angle_coverage"]["effective_angle_count"] == 1
        and a["angle_coverage"]["relation"]["kind"] == "unique"
        and a["angle_coverage"]["duplicate_exclusion"]["excluded"] is False
    }
    assert len(multi_angle_keys) >= 2, (
        f"有效且不重複角度不足: {sorted(multi_angle_keys)}"
    )
    simultaneous = [
        a
        for a in one_to_many_args
        if a["angle_coverage"]["angle_key"] in multi_angle_keys
        and a["source_count"] >= 2
        and a["binding_ok"] is True
        and a["binding_status"] == "pass"
    ]
    assert simultaneous, (
        "須至少一則論點同時滿足「多有效角度集合中」與「一對多來源綁定」"
    )
    otm = simultaneous[0]
    assert otm["source_ids"] == ["law:93", "law:94"]
    assert otm["angle_coverage"]["angle_type"] == "limitation"

    # 逐筆核對：角度數與來源清單一致（成品 segments ↔ binding_report.arguments）
    summed_effective = 0
    summed_valid = 0
    summed_deduped = 0
    seen_angle_types: set[str] = set()
    seen_angle_keys: set[str] = set()
    for arg in report["arguments"]:
        seg = serialized["segments"][arg["segment_index"]]
        assert seg["type"] == "supplement"
        assert seg["argument_id"] == arg["argument_id"] == (
            f"argument:{arg['argument_index']}"
        )

        # --- 角度數：報告 ↔ 成品 ↔ 內部欄位 ---
        ac_report = arg["angle_coverage"]
        ac_product = seg["angle_coverage"]
        assert arg["valid_angle_count"] == seg["valid_angle_count"]
        assert arg["deduped_angle_count"] == seg["deduped_angle_count"]
        assert arg["angle_tags"] == seg["angle_tags"] == ac_report["angle_labels"]
        assert list(ac_report["angle_labels"]) == list(ac_product["angle_labels"])
        assert ac_report["angle_type"] == ac_product["angle_type"] == seg["angle_type"]
        assert ac_report["angle_key"] == ac_product["angle_key"] == seg["angle_key"]
        assert ac_report["effective_angle_count"] == ac_product["effective_angle_count"]
        assert ac_report["effective_angle_count"] in (0, 1)
        assert arg["valid_angle_count"] in (0, 1)
        assert arg["deduped_angle_count"] in (0, 1)
        # 去重後保留者：valid 與 deduped 皆為 1，且 effective_angle_count=1
        if ac_report["duplicate_exclusion"]["excluded"] is False:
            assert arg["valid_angle_count"] == 1
            assert arg["deduped_angle_count"] == 1
            assert ac_report["effective_angle_count"] == 1
            assert ac_report["relation"]["kind"] == "unique"
            seen_angle_types.add(ac_report["angle_type"])
            seen_angle_keys.add(ac_report["angle_key"])
        else:
            assert arg["deduped_angle_count"] == 0
            assert ac_report["effective_angle_count"] == 0
        summed_effective += int(ac_report["effective_angle_count"])
        summed_valid += int(arg["valid_angle_count"])
        summed_deduped += int(arg["deduped_angle_count"])
        assert arg["checks"]["has_angle_coverage"] is True
        assert arg["checks"]["meets_angle_coverage_threshold"] is True
        assert arg["checks"]["angle_facet_complete"] is True

        # --- 來源清單：報告 ↔ 成品 ↔ 計數欄位 ---
        source_ids = list(arg["source_ids"])
        assert source_ids == list(seg["source_ids"])
        assert source_ids == list(arg["trace_source_ids"])
        # 成品無獨立 source_count 欄位：以清單長度與報告計數對齊
        assert arg["source_count"] == len(source_ids) == len(seg["source_ids"])
        assert arg["cardinality"] == seg["cardinality"]
        assert len(source_ids) == len(set(source_ids)), (
            f"論點[{arg['argument_index']}] source_ids 重複: {source_ids}"
        )
        sources = list(seg["sources"])
        assert [s["id"] for s in sources] == source_ids
        assert len(sources) == arg["source_count"]
        expected_field = f"sources:{','.join(source_ids)}"
        assert arg["source_id_field"] == seg["source_id"] == expected_field
        if arg["cardinality"] == "one_to_many":
            assert arg["source_count"] >= 2
        elif arg["cardinality"] == "one_to_one":
            assert arg["source_count"] == 1
        for pos, sid in enumerate(source_ids):
            assert sources[pos]["id"] == sid
            fragment = sources[pos].get("content") or ""
            assert fragment.strip(), f"來源 {sid!r} 片段空白"
        assert arg["checks"]["at_least_one_source"] is True
        assert arg["checks"]["source_traceable"] is True
        assert arg["checks"]["no_duplicate_sources"] is True
        assert arg["checks"]["no_omitted_traces"] is True
        assert arg["checks"]["no_extra_traces"] is True
        assert arg["checks"]["source_id_field_aligned"] is True
        assert arg["binding_ok"] is True
        assert arg["binding_status"] == "pass"
        assert all(arg["checks"].values())

    # 彙總角度數 = 逐筆加總；跨論點角度真的不同且不重複
    assert summed_effective == angle_summary["effective_angle_count"]
    assert summed_deduped == angle_summary["effective_angle_count"]
    assert summed_valid == report["argument_count"]
    assert seen_angle_types == {"definition", "limitation"}
    assert len(seen_angle_keys) == 2
    assert report["source_usage"] == {
        "law:92": [0],
        "law:93": [1],
        "law:94": [1],
    }
