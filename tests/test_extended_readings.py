"""延伸閱讀欄位驗收測試：extended_readings、extended_readings_status、pending_evidence_reason。

驗證三欄在 binding_report、JSON、Markdown、DOCX 四種輸出格式中皆存在且結構正確，
並以負例確保缺欄／格式錯誤時明確失敗。
"""
import json
import tempfile
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from note_filler.correction import assemble_correction, CorrectionDoc, Segment
from note_filler.export import to_json, to_markdown, to_docx
from note_filler.binding_report import build_binding_report, parse_binding_report
from note_filler.llm import FakeLLM
from note_filler.parse import parse_note
from note_filler.pipeline import run_pipeline
from note_filler.retrieve.models import Source
from tests.test_pipeline import FakeTwinkle, FakeLaw


def _note_fixture(tmp_path: Path, content: str) -> str:
    p = tmp_path / "note.docx"
    d = DocxDocument()
    for para in content.split("\n\n"):
        if para.strip():
            d.add_paragraph(para.strip())
    d.save(str(p))
    return str(p)


def _src(sid, title, url, level, distance=0.6):
    return Source(
        id=sid, title=title, url=url, level=level,
        content=f"{title} 官方結構化記錄全文……",
        fetched_date="2026-07-15", doc_date="2026-01-01", distance=distance,
    )


def _pipeline_with_extended_readings(tmp_path):
    """Pipeline：gap1 有 3 個候選來源但只引用 2 個，第 3 個成為延伸閱讀。"""
    note_content = "行政程序法要求行政行為應遵守正當程序。\n\n本筆記僅記錄部分重點。"
    note_path = _note_fixture(tmp_path, note_content)
    llm = FakeLLM([
        "admin",
        "正當程序的要件為何?",
        json.dumps([
            {"question": "正當程序的要件為何?", "status": "missing", "reason": "筆記未展開"},
        ], ensure_ascii=False),
        '{"keyword": "正當程序", "law_name": null}',
        "正當程序需符合法律保留[^1]與比例原則[^2]。",
    ])
    twinkle = FakeTwinkle([
        [_src("s1", "行政程序法", "https://a", "A"),
         _src("s2", "大法官釋字", "https://b", "B"),
         _src("s3", "學者論文", "https://c", "C", distance=0.9)],
    ])
    law = FakeLaw()
    doc = run_pipeline(note_path, llm, twinkle, law)
    return doc


class TestExtendedReadingsInJson:
    """JSON 輸出必須包含三個延伸閱讀欄位。"""

    def test_supplement_has_extended_reading_fields(self, tmp_path):
        doc = _pipeline_with_extended_readings(tmp_path)
        data = to_json(doc)
        supplements = [s for s in data["segments"] if s["type"] == "supplement"]
        assert supplements, "應至少有一個補充段"
        seg = supplements[0]
        assert "extended_readings" in seg, "JSON segment 缺少 extended_readings"
        assert "extended_readings_status" in seg, "JSON segment 缺少 extended_readings_status"
        assert "pending_evidence_reason" in seg, "JSON segment 缺少 pending_evidence_reason"
        assert isinstance(seg["extended_readings"], list)
        assert seg["extended_readings_status"] in ("none", "available", "pending_evidence")
        assert isinstance(seg["pending_evidence_reason"], str)

    def test_extended_readings_contain_omitted_source(self, tmp_path):
        doc = _pipeline_with_extended_readings(tmp_path)
        data = to_json(doc)
        seg = [s for s in data["segments"] if s["type"] == "supplement"][0]
        # s3 被引用但未被 LLM 使用，應出現在延伸閱讀
        reading_ids = [r["source_id"] for r in seg["extended_readings"]]
        assert "s3" in reading_ids, f"s3 應在延伸閱讀中，實際: {reading_ids}"

    def test_extended_readings_have_required_keys(self, tmp_path):
        doc = _pipeline_with_extended_readings(tmp_path)
        data = to_json(doc)
        seg = [s for s in data["segments"] if s["type"] == "supplement"][0]
        for r in seg["extended_readings"]:
            assert "source_id" in r
            assert "title" in r
            assert "level" in r
            assert isinstance(r["source_id"], str) and r["source_id"].strip()
            assert isinstance(r["title"], str) and r["title"].strip()

    def test_original_segment_has_empty_extended_readings(self, tmp_path):
        doc = _pipeline_with_extended_readings(tmp_path)
        data = to_json(doc)
        originals = [s for s in data["segments"] if s["type"] == "original"]
        for seg in originals:
            assert seg["extended_readings"] == []
            assert seg["extended_readings_status"] == "none"
            assert seg["pending_evidence_reason"] == ""


class TestExtendedReadingsInMarkdown:
    """Markdown 輸出必須包含延伸閱讀區塊。"""

    def test_extended_readings_block_present(self, tmp_path):
        doc = _pipeline_with_extended_readings(tmp_path)
        md = to_markdown(doc)
        assert "> **延伸閱讀**" in md, "Markdown 缺少延伸閱讀區塊"

    def test_extended_readings_list_item(self, tmp_path):
        doc = _pipeline_with_extended_readings(tmp_path)
        md = to_markdown(doc)
        assert "> - [s3]" in md, "Markdown 延伸閱讀應列出 s3"

    def test_pending_evidence_has_reason(self, tmp_path):
        """無來源的 pending_evidence 段應有待補證原因。"""
        note_content = "行政程序法要求行政行為應遵守正當程序。"
        note_path = _note_fixture(tmp_path, note_content)
        llm = FakeLLM([
            "admin",
            "正當程序的要件為何?",
            json.dumps([
                {"question": "正當程序的要件為何?", "status": "missing", "reason": "筆記未展開"},
            ], ensure_ascii=False),
            '{"keyword": "正當程序", "law_name": null}',
            "【待補證】此問題缺乏可用來源。",
        ])
        twinkle = FakeTwinkle([[]])
        law = FakeLaw()
        doc = run_pipeline(note_path, llm, twinkle, law)
        md = to_markdown(doc)
        assert "> **待補證原因**" in md, "pending_evidence 段應有待補證原因"


class TestExtendedReadingsInDocx:
    """DOCX 輸出必須包含延伸閱讀區塊。"""

    def test_extended_readings_paragraph_present(self, tmp_path):
        doc = _pipeline_with_extended_readings(tmp_path)
        out_path = tmp_path / "out.docx"
        to_docx(doc, str(out_path))
        out_doc = DocxDocument(str(out_path))
        texts = [p.text for p in out_doc.paragraphs]
        assert any("延伸閱讀" in t for t in texts), "DOCX 缺少延伸閱讀段落"
        assert any("[s3]" in t for t in texts), "DOCX 延伸閱讀應列出 s3"


class TestExtendedReadingsInBindingReport:
    """Binding report 必須包含延伸閱讀欄位。"""

    def test_binding_report_has_extended_reading_fields(self, tmp_path):
        doc = _pipeline_with_extended_readings(tmp_path)
        report = build_binding_report(doc)
        for arg in report["arguments"]:
            assert "extended_readings" in arg
            assert "extended_readings_status" in arg
            assert "pending_evidence_reason" in arg

    def test_parse_binding_report_validates_extended_readings(self, tmp_path):
        doc = _pipeline_with_extended_readings(tmp_path)
        report = build_binding_report(doc)
        # parse_binding_report 不應 raise
        parse_binding_report(report)

    def test_binding_report_extended_readings_matches_segment(self, tmp_path):
        doc = _pipeline_with_extended_readings(tmp_path)
        report = build_binding_report(doc)
        data = to_json(doc)
        seg_supplements = [s for s in data["segments"] if s["type"] == "supplement"]
        for arg, seg in zip(report["arguments"], seg_supplements):
            assert arg["extended_readings"] == seg["extended_readings"]
            assert arg["extended_readings_status"] == seg["extended_readings_status"]
            assert arg["pending_evidence_reason"] == seg["pending_evidence_reason"]


class TestExtendedReadingsNegativeCases:
    """負例：缺欄或格式錯誤必須明確失敗。"""

    def test_binding_report_missing_extended_readings_rejected(self):
        """binding_report 缺少 extended_readings 欄位時 parse 應 raise。"""
        fake_report = {
            "schema": "note_filler.binding_report.v1",
            "source_path": "test.md",
            "argument_count": 1,
            "summary": {
                "one_to_one": 0, "one_to_many": 0, "none": 1,
                "pass": 0, "fail": 0, "pending_evidence": 1,
                "all_sourced_arguments_ok": True, "all_arguments_ok": False,
            },
            "arguments": [{
                "argument_index": 0,
                "argument_id": "argument:0",
                "segment_index": 1,
                "argument_text": "test",
                "summary": "test",
                "confidence": "pending_evidence",
                "cardinality": "none",
                "source_count": 0,
                "source_ids": [],
                "trace_source_ids": [],
                "source_fragments": [],
                "citation_spans": [],
                "source_id_field": "pending:gap:0",
                "checks": {
                    "at_least_one_source": False,
                    "source_traceable": True,
                    "no_duplicate_sources": True,
                    "no_omitted_traces": True,
                    "no_extra_traces": True,
                    "source_id_field_aligned": True,
                    "no_empty_fragments": True,
                    "has_functional_gap": True,
                    "has_user_value": True,
                    "has_related_knowledge": True,
                    "related_knowledge_consistent": True,
                    "summary_matches_product": True,
                    "has_angle_coverage": True,
                    "meets_angle_coverage_threshold": True,
                    "angle_facet_complete": True,
                    "angle_functional_gap_present": True,
                    "angle_user_value_present": True,
                    "angle_question_present": True,
                },
                "binding_status": "pending_evidence",
                "binding_ok": True,
                "functional_gap": "test gap",
                "user_value": "test value",
                "related_knowledge": "test（如何支撐決策品質：對應功能缺口「test gap」提供可追溯依據，降低僅憑印象取捨的風險；如何補強使用者理解：test value）",
                "angle_coverage": {
                    "angle_type": "test",
                    "angle_labels": ["test"],
                    "covered_facets": ["test"],
                    "angle_key": "test",
                    "relation": {
                        "kind": "unique",
                        "related_argument_indices": [],
                        "duplicate_of": [],
                        "synonym_of": [],
                    },
                    "effective_angle_count": 1,
                    "duplicate_exclusion": {
                        "excluded": False,
                        "reason": None,
                        "kept_argument_index": 0,
                    },
                },
                "angle_tags": ["test"],
                "valid_angle_count": 1,
                "deduped_angle_count": 1,
                "duplicate_angles": [],
                "angle_field_issues": [],
                # 故意缺 extended_readings, extended_readings_status, pending_evidence_reason
            }],
            "source_usage": {},
            "angle_coverage_summary": {
                "unique_angle_types": ["test"],
                "covered_facets_union": ["test"],
                "duplicate_pairs": [],
                "synonym_pairs": [],
                "argument_count_with_angles": 1,
                "effective_angle_count": 1,
                "excluded_angle_count": 0,
                "duplicate_ratio": 0.0,
                "required_effective_angle_count": 1,
                "max_duplicate_ratio": 0.5,
                "has_sufficient_angles": True,
                "has_acceptable_duplicate_ratio": True,
                "coverage_ok": True,
            },
            "traceability_markers": [{
                "argument_id": "argument:0",
                "kind": "processing_record",
                "id": "gap:0",
                "binding_status": "pending_evidence",
            }],
            "claim_source_map": {"argument:0": []},
            "citation_span_map": [],
        }
        with pytest.raises(ValueError, match="缺少欄位"):
            parse_binding_report(fake_report)

    def test_binding_report_invalid_extended_readings_status_rejected(self):
        """extended_readings_status 非法值時 parse 應 raise。"""
        doc = _pipeline_with_extended_readings(Path(tempfile.mkdtemp()))
        report = build_binding_report(doc)
        report["arguments"][0]["extended_readings_status"] = "invalid_status"
        with pytest.raises(ValueError, match="extended_readings_status 非法"):
            parse_binding_report(report)

    def test_binding_report_pending_without_reason_rejected(self):
        """pending_evidence 狀態但 reason 為空時 parse 應 raise。"""
        doc = _pipeline_with_extended_readings(Path(tempfile.mkdtemp()))
        report = build_binding_report(doc)
        # 找一個 pending_evidence 的 argument
        for arg in report["arguments"]:
            if arg["extended_readings_status"] == "pending_evidence":
                arg["pending_evidence_reason"] = ""
                with pytest.raises(ValueError, match="pending_evidence_reason 為空"):
                    parse_binding_report(report)
                return
        pytest.skip("無 pending_evidence argument 可測試")


class TestExtendedReadingsOriginalImmutability:
    """確保延伸閱讀欄位不影響原稿逐字不變。"""

    def test_original_text_unchanged_with_extended_readings(self, tmp_path):
        note_content = "行政程序法要求行政行為應遵守正當程序。\n\n本筆記僅記錄部分重點。"
        note_path = _note_fixture(tmp_path, note_content)
        doc = _pipeline_with_extended_readings(tmp_path)
        data = to_json(doc)
        original_segments = [s for s in data["segments"] if s["type"] == "original"]
        expected = [p.strip() for p in note_content.split("\n\n") if p.strip()]
        for seg, exp in zip(original_segments, expected):
            assert seg["text"] == exp, "原稿文字被延伸閱讀欄位影響"
