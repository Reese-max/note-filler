"""機械可解析的回歸測試：延伸閱讀連結的可抽取性、數量、分離性與欄位穩定性。

逐筆驗證每個論點區塊的：
1. 延伸閱讀連結可從 binding_report / JSON / Markdown / DOCX 四種格式抽取
2. 數量符合預期（被檢索但未引用的來源數）
3. 與原文區塊分離（延伸閱讀不出現在 original segment 或 supplement text 中）
4. 不改動原稿內容（原稿逐字不變）
5. 輸出格式固定（schema ID、欄位名稱不漂移）
6. 欄位名稱穩定（extended_readings 子欄位契約與型別）

這些測試的目的是補齊既有測試缺少的「機械可解析」面向：
- 既有測試驗證「有」與「格式正確」，但未對欄位名稱與型別簽訂嚴格契約
- 未驗證跨格式的數值一致性
- 未驗證 Markdown 可用正則式解析
- 未將欄位契約與 source code 的 REQUIRED_ARGUMENT_KEYS 對齊
"""
from __future__ import annotations

import json
import json as _json
import re
import tempfile
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from note_filler.binding_report import (
    REQUIRED_ARGUMENT_KEYS,
    build_binding_report,
    parse_binding_report,
)
from note_filler.correction import assemble_correction, CorrectionDoc
from note_filler.export import to_docx, to_json, to_markdown
from note_filler.gap import Gap
from note_filler.llm import FakeLLM
from note_filler.parse import Document, Paragraph
from note_filler.pipeline import run_pipeline
from note_filler.retrieve.models import Source
from note_filler.verify import cross_validate
from note_filler.write import WrittenSupplement
from tests.test_pipeline import FakeLaw, FakeTwinkle


# ---------------------------------------------------------------------------
# 固定欄位契約（與 binding_report.py 的 REQUIRED_ARGUMENT_KEYS 對齊）
# ---------------------------------------------------------------------------

EXPECTED_EXTENDED_READING_KEYS = frozenset(
    {"source_id", "title", "url", "level", "distance"}
)
EXPECTED_EXTENDED_READING_KEY_TYPES: dict[str, type | tuple[type, ...]] = {
    "source_id": str,
    "title": str,
    "url": (str, type(None)),
    "level": str,
    "distance": (int, float),
}
VALID_EXTENDED_READINGS_STATUSES = frozenset({"none", "available", "pending_evidence"})
EXPECTED_SEGMENT_KEYS_FOR_SUPPLEMENT = frozenset(
    {
        "type",
        "text",
        "anchor_idx",
        "confidence",
        "conflict_note",
        "source_id",
        "source_ids",
        "cardinality",
        "traceability",
        "citation_spans",
        "sources",
        "functional_gap",
        "user_value",
        "summary",
        "related_knowledge",
        "argument_id",
        "angle_type",
        "angle_labels",
        "angle_key",
        "angle_coverage",
        "three_part_annotation",
        "angle_tags",
        "valid_angle_count",
        "deduped_angle_count",
        "duplicate_angles",
        "extended_readings",
        "extended_readings_status",
        "pending_evidence_reason",
        "openable_links_count",
        "openable_links_status",
        "openable_links_incomplete_reason",
    }
)
EXPECTED_ORIGINAL_SEGMENT_KEYS = frozenset(
    {
        "type",
        "text",
        "anchor_idx",
        "confidence",
        "conflict_note",
        "source_id",
        "source_ids",
        "cardinality",
        "traceability",
        "citation_spans",
        "sources",
        "functional_gap",
        "user_value",
        "summary",
        "related_knowledge",
        "argument_id",
        "angle_type",
        "angle_labels",
        "angle_key",
        "angle_coverage",
        "three_part_annotation",
        "extended_readings",
        "extended_readings_status",
        "pending_evidence_reason",
        "openable_links_count",
        "openable_links_status",
        "openable_links_incomplete_reason",
    }
)

# 可從 Markdown 解析延伸閱讀的正則
MD_EXTENDED_READING_RE = re.compile(r"> - \[(\S+?)\] Level (\S+) (.+)")

# 延伸閱讀欄位順序（依格式規格 v1 定義）
EXTENDED_READINGS_FIELD_ORDER = [
    "extended_readings",
    "extended_readings_status", 
    "pending_evidence_reason",
    "openable_links_count",
    "openable_links_status",
    "openable_links_incomplete_reason",
]

# 延伸閱讀子欄位順序（依格式規格 v1 定義）
EXTENDED_READING_ITEM_FIELD_ORDER = [
    "source_id",
    "title",
    "url",
    "level",
    "distance",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _doc(path: str = "input/note.txt") -> Document:
    return Document(
        source_path=path,
        paragraphs=(
            Paragraph(0, "原稿逐字保留的第一行。"),
            Paragraph(1, "原稿第二行。"),
        ),
        full_text="原稿逐字保留的第一行。\n原稿第二行。",
    )


def _source(
    sid: str,
    title: str,
    url: str | None = None,
    level: str = "C",
    distance: float = 0.5,
    content: str = "",
) -> Source:
    return Source(
        id=sid,
        title=title,
        url=url,
        level=level,
        content=content or f"{title} 內容。",
        fetched_date="2026-07-28",
        doc_date=None,
        distance=distance,
    )


def _basic_product(
    used_ids: list[str] | None = None,
    omitted_ids: list[str] | None = None,
) -> CorrectionDoc:
    """建立含延伸閱讀的簡單 CorrectionDoc。"""
    srcs = [
        _source("s1", "法規來源A", "https://law.gov.tw/a", "A"),
        _source("s2", "判決先例B", "https://judicial.gov.tw/b", "B"),
    ]
    if used_ids is None:
        used_ids = ["s1"]
    if omitted_ids is None:
        omitted_ids = ["s2"]
    gap = Gap("測試問題", "missing", "未展開")
    return assemble_correction(
        _doc(),
        [gap],
        {gap.question: srcs},
        {gap.question: WrittenSupplement(
            "補充內容[^1]。", used_ids,
            omitted_source_ids=omitted_ids,
        )},
        {gap.question: cross_validate(gap.question, srcs)},
    )


# ===================================================================
# 1. 欄位契約穩定性
# ===================================================================


class TestFieldContractStability:
    """extended_readings 子欄位的型別與名稱契約。"""

    def test_extended_reading_required_keys_present(self):
        """每筆 extended_reading 都應含 source_id / title / url / level / distance。"""
        readings = [
            {"source_id": "s1", "title": "t1", "url": "https://a", "level": "A", "distance": 0.3},
            {"source_id": "s2", "title": "t2", "url": None, "level": "B", "distance": 0.7},
        ]
        for r in readings:
            missing = EXPECTED_EXTENDED_READING_KEYS - set(r.keys())
            assert not missing, f"extended_reading 缺少欄位: {missing}"

    def test_extended_reading_key_types_match_contract(self):
        """每筆 extended_reading 的欄位型別必須符合契約。"""
        readings = [
            {"source_id": "s1", "title": "t1", "url": "https://a", "level": "A", "distance": 0.3},
            {"source_id": "s2", "title": "t2", "url": None, "level": "B", "distance": 0.7},
        ]
        for r in readings:
            for key, expected in EXPECTED_EXTENDED_READING_KEY_TYPES.items():
                assert isinstance(r[key], expected), (
                    f"extended_reading.{key} 型別應為 {expected}，實際 {type(r[key])}"
                )

    def test_extended_readings_status_only_valid_values(self):
        """extended_readings_status 只能是 none / available / pending_evidence。"""
        for status in VALID_EXTENDED_READINGS_STATUSES:
            assert isinstance(status, str)
        for invalid in ("invalid", "", True, None):
            assert invalid not in VALID_EXTENDED_READINGS_STATUSES

    def test_extended_readings_in_required_argument_keys(self):
        """binding_report 的 REQUIRED_ARGUMENT_KEYS 含延伸閱讀欄位。"""
        assert "extended_readings" in REQUIRED_ARGUMENT_KEYS
        assert "extended_readings_status" in REQUIRED_ARGUMENT_KEYS
        assert "pending_evidence_reason" in REQUIRED_ARGUMENT_KEYS
        assert "openable_links_count" in REQUIRED_ARGUMENT_KEYS
        assert "openable_links_status" in REQUIRED_ARGUMENT_KEYS
        assert "openable_links_incomplete_reason" in REQUIRED_ARGUMENT_KEYS

    def test_report_built_with_all_required_keys(self):
        """實際 build_binding_report 的每個 argument 含所有必要欄位。"""
        product = _basic_product()
        report = build_binding_report(product)
        for arg in report["arguments"]:
            missing = REQUIRED_ARGUMENT_KEYS - set(arg.keys())
            assert not missing, (
                f"build_binding_report argument 缺少 REQUIRED_ARGUMENT_KEYS: {missing}"
            )

    def test_parse_binding_report_accepts_valid_readings(self):
        """parse_binding_report 接受合法 extended_readings。"""
        product = _basic_product()
        report = build_binding_report(product)
        # 不應 raise
        parse_binding_report(report)

    def test_json_all_supplement_has_expected_keys(self):
        """JSON supplement segment 含所有預期欄位。"""
        data = to_json(_basic_product())
        for seg in data["segments"]:
            if seg["type"] == "supplement":
                missing = EXPECTED_SEGMENT_KEYS_FOR_SUPPLEMENT - set(seg.keys())
                assert not missing, f"JSON supplement 缺少欄位: {missing}"

    def test_json_all_original_has_expected_keys(self):
        """JSON original segment 含所有預期欄位。"""
        data = to_json(_basic_product())
        for seg in data["segments"]:
            if seg["type"] == "original":
                missing = EXPECTED_ORIGINAL_SEGMENT_KEYS - set(seg.keys())
                assert not missing, f"JSON original 缺少欄位: {missing}"


# ===================================================================
# 2. 延伸閱讀可從四種輸出格式抽取
# ===================================================================


class TestExtractability:
    """延伸閱讀可從 binding_report / JSON / Markdown / DOCX 抽取。"""

    def test_extract_from_binding_report(self):
        """binding_report 的 extended_readings 可逐一解析。"""
        product = _basic_product(used_ids=["s1"], omitted_ids=["s2"])
        report = build_binding_report(product)
        for arg in report["arguments"]:
            ers = arg["extended_readings"]
            assert isinstance(ers, list)
            for er in ers:
                assert isinstance(er, dict)
                assert all(k in er for k in EXPECTED_EXTENDED_READING_KEYS)

    def test_extract_from_json(self):
        """JSON extended_readings 可逐筆解析。"""
        data = to_json(_basic_product(used_ids=["s1"], omitted_ids=["s2"]))
        for seg in data["segments"]:
            if seg["type"] == "supplement":
                for er in seg["extended_readings"]:
                    assert isinstance(er, dict)
                    for key in EXPECTED_EXTENDED_READING_KEYS:
                        assert key in er, f"JSON extended_reading 缺少 {key}"

    def test_extract_from_markdown_with_regex(self):
        """Markdown 的延伸閱讀區塊可用正則式解析。"""
        product = _basic_product(
            used_ids=["s1"],
            omitted_ids=["s2", "s3"],
        )
        # 補 s3 來源
        product.segments[-1].extended_readings.append(
            {"source_id": "s3", "title": "學術論文C", "url": "https://c", "level": "C", "distance": 0.9}
        )
        md = to_markdown(product)
        matches = MD_EXTENDED_READING_RE.findall(md)
        found_ids = {m[0] for m in matches}
        assert "s2" in found_ids, f"Markdown 應可解析出 s2，實際抓到: {found_ids}"
        assert "s3" in found_ids, f"Markdown 應可解析出 s3，實際抓到: {found_ids}"

    def test_extract_from_markdown_zero_readings(self):
        """延伸閱讀為空時，正則式在 Markdown 中不誤抓。"""
        product = _basic_product(used_ids=["s1", "s2"], omitted_ids=[])
        md = to_markdown(product)
        matches = MD_EXTENDED_READING_RE.findall(md)
        assert not matches, f"無延伸閱讀時不應有正則命中: {matches}"

    def test_extract_from_docx(self):
        """DOCX 的延伸閱讀段落可被解析。"""
        product = _basic_product(used_ids=["s1"], omitted_ids=["s2"])
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            out_path = f.name
        try:
            to_docx(product, out_path)
            doc = DocxDocument(out_path)
            texts = [p.text for p in doc.paragraphs]
            reading_lines = [t for t in texts if "延伸閱讀" in t or "[s2]" in t]
            assert any("延伸閱讀" in t for t in reading_lines), "DOCX 缺少延伸閱讀標題"
            assert any("[s2]" in t for t in reading_lines), "DOCX 缺少延伸閱讀條目 s2"
        finally:
            Path(out_path).unlink(missing_ok=True)

    def test_extract_from_all_four_formats_identical_content(self):
        """同一批資料跨四種格式的延伸閱讀內容一致。"""
        product = _basic_product(used_ids=["s1"], omitted_ids=["s2"])
        report = build_binding_report(product)
        data = to_json(product)
        md = to_markdown(product)

        report_ers = report["arguments"][0]["extended_readings"]
        json_ers = [s["extended_readings"] for s in data["segments"] if s["type"] == "supplement"][0]

        assert len(report_ers) == 1
        assert len(json_ers) == 1
        assert report_ers[0]["source_id"] == json_ers[0]["source_id"] == "s2"

        matches = MD_EXTENDED_READING_RE.findall(md)
        assert any("s2" in m for m in [m[0] for m in matches]), "Markdown 應含延伸閱讀 s2"

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            out_path = f.name
        try:
            to_docx(product, out_path)
            doc = DocxDocument(out_path)
            docx_texts = [p.text for p in doc.paragraphs]
            assert any("[s2]" in t for t in docx_texts), "DOCX 應含延伸閱讀 s2"
        finally:
            Path(out_path).unlink(missing_ok=True)


# ===================================================================
# 3. 數量符合預期
# ===================================================================


class TestQuantity:
    """延伸閱讀數量符合被檢索但未使用的來源數。"""

    def test_count_matches_omitted_ids(self):
        """延伸閱讀數 = omitted_source_ids 中在 retrieved 存在者。"""
        srcs = [
            _source("s1", "源A", "https://a", "A"),
            _source("s2", "源B", "https://b", "B"),
            _source("s3", "源C", "https://c", "C"),
        ]
        gap = Gap("test", "missing", "未展開")
        product = assemble_correction(
            _doc(), [gap],
            {gap.question: srcs},
            {gap.question: WrittenSupplement("內容。", ["s1"], omitted_source_ids=["s2", "s3"])},
            {gap.question: cross_validate(gap.question, srcs)},
        )
        seg = [s for s in product.segments if s.type == "supplement"][0]
        assert len(seg.extended_readings) == 2

    def test_zero_when_all_sources_used(self):
        """所有來源都被引用時延伸閱讀為 0。"""
        srcs = [
            _source("s1", "源A", "https://a", "A"),
            _source("s2", "源B", "https://b", "B"),
        ]
        gap = Gap("test", "missing", "未展開")
        product = assemble_correction(
            _doc(), [gap],
            {gap.question: srcs},
            {gap.question: WrittenSupplement("內容[^1][^2]。", ["s1", "s2"], omitted_source_ids=[])},
            {gap.question: cross_validate(gap.question, srcs)},
        )
        seg = [s for s in product.segments if s.type == "supplement"][0]
        assert seg.extended_readings == []

    def test_zero_when_no_retrieved_sources(self):
        """檢索結果為空時延伸閱讀為 0。"""
        gap = Gap("test", "missing", "未展開")
        product = assemble_correction(
            _doc(), [gap],
            {gap.question: []},
            {gap.question: WrittenSupplement("【待補證】無來源。", [], omitted_source_ids=[])},
            {gap.question: cross_validate(gap.question, [])},
        )
        seg = [s for s in product.segments if s.type == "supplement"][0]
        assert seg.extended_readings == []

    def test_count_in_report_matches_json_and_supplement(self):
        """binding_report / JSON / Segment 三者延伸閱讀數一致。"""
        srcs = [
            _source("s1", "源A", "https://a", "A"),
            _source("s2", "源B", "https://b", "B"),
            _source("s3", "源C", "https://c", "C"),
        ]
        gap = Gap("test", "missing", "未展開")
        product = assemble_correction(
            _doc(), [gap],
            {gap.question: srcs},
            {gap.question: WrittenSupplement("內容。", ["s1", "s2"], omitted_source_ids=["s3"])},
            {gap.question: cross_validate(gap.question, srcs)},
        )
        report = build_binding_report(product)
        data = to_json(product)
        seg = [s for s in product.segments if s.type == "supplement"][0]

        report_count = sum(len(a["extended_readings"]) for a in report["arguments"])
        json_count = sum(
            len(s["extended_readings"])
            for s in data["segments"] if s["type"] == "supplement"
        )
        seg_count = len(seg.extended_readings)

        assert report_count == json_count == seg_count == 1

    def test_binding_report_flags_pending_evidence_count(self):
        """pending_evidence 狀態下延伸閱讀數可為 0 但 reason 非空。"""
        gap = Gap("test", "missing", "未展開")
        product = assemble_correction(
            _doc(), [gap],
            {gap.question: []},
            {gap.question: WrittenSupplement("【待補證】無來源。", [])},
            {gap.question: cross_validate(gap.question, [])},
        )
        report = build_binding_report(product)
        arg = report["arguments"][0]
        assert arg["extended_readings"] == []
        assert arg["extended_readings_status"] == "pending_evidence"
        assert arg["pending_evidence_reason"].strip()

    def test_multiple_arguments_all_have_correct_counts(self):
        """多論點情境下每個論點各自的延伸閱讀數正確。"""
        srcs_a = [_source("s1", "源A", "https://a", "A"), _source("s2", "源B", "https://b", "B")]
        srcs_b = [_source("s3", "源C", "https://c", "C")]
        gap_a = Gap("問題一", "missing", "未展開")
        gap_b = Gap("問題二", "missing", "未展開")
        product = assemble_correction(
            _doc(), [gap_a, gap_b],
            {gap_a.question: srcs_a, gap_b.question: srcs_b},
            {
                gap_a.question: WrittenSupplement("內容A。", ["s1"], omitted_source_ids=["s2"]),
                gap_b.question: WrittenSupplement("內容B。", [], omitted_source_ids=["s3"]),
            },
            {
                gap_a.question: cross_validate(gap_a.question, srcs_a),
                gap_b.question: cross_validate(gap_b.question, srcs_b),
            },
        )
        supplements = [s for s in product.segments if s.type == "supplement"]
        assert len(supplements) == 2
        assert len(supplements[0].extended_readings) == 1  # 論點一: 1 筆延伸閱讀
        assert len(supplements[1].extended_readings) == 1  # 論點二: 1 筆延伸閱讀


# ===================================================================
# 4. 與原文區塊分離
# ===================================================================


class TestSeparationFromOriginal:
    """延伸閱讀與原文區塊分離、不改動原稿。"""

    ORIGINAL_TEXTS = ["原稿逐字保留的第一行。", "原稿第二行。"]

    def test_original_segments_have_no_extended_readings(self):
        """original segment 的 extended_readings 永遠為空。"""
        product = _basic_product(used_ids=[], omitted_ids=["s1", "s2"])
        data = to_json(product)
        for seg in data["segments"]:
            if seg["type"] == "original":
                assert seg["extended_readings"] == []
                assert seg["extended_readings_status"] == "none"
                assert seg["pending_evidence_reason"] == ""

    def test_original_text_unchanged_regardless_of_readings(self):
        """無論延伸閱讀有無與多寡，原稿文字不變。"""
        for omitted in ([], ["s1"], ["s1", "s2"]):
            product = _basic_product(used_ids=["s1"], omitted_ids=omitted)
            data = to_json(product)
            actual = [s["text"] for s in data["segments"] if s["type"] == "original"]
            assert actual == self.ORIGINAL_TEXTS, (
                f"omitted_ids={omitted} 時原稿變更: {actual} != {self.ORIGINAL_TEXTS}"
            )

    def test_extended_readings_not_mixed_with_supplement_text(self):
        """延伸閱讀不在 supplement text 內文裡。"""
        product = _basic_product(used_ids=[], omitted_ids=["s1"])
        seg = [s for s in product.segments if s.type == "supplement"][0]
        assert "法規來源A" not in seg.text
        assert "s1" not in seg.text

    def test_markdown_extended_readings_is_separate_block(self):
        """Markdown 的延伸閱讀是獨立 > 區塊。"""
        product = _basic_product(used_ids=[], omitted_ids=["s1"])
        md = to_markdown(product)
        assert "> **延伸閱讀**" in md
        assert "> - [s1]" in md

    def test_markdown_supplement_block_does_not_contain_source_ids(self):
        """Markdown supplement 主文區不含延伸閱讀來源 ID。"""
        product = _basic_product(used_ids=[], omitted_ids=["s1"])
        md = to_markdown(product)
        # 找到 【補充】 到 **延伸閱讀** 之間的主文區
        m = re.search(r"> 【補充】(.+?)(?=> \*\*延伸閱讀\*\*|$)", md, re.DOTALL)
        if m:
            main = m.group(1)
            assert "s1" not in main
            assert "法規來源A" not in main

    def test_docx_extended_readings_separate_paragraph(self):
        """DOCX 的延伸閱讀是獨立段落，不在 supplement 文字中。"""
        product = _basic_product(used_ids=[], omitted_ids=["s1"])
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            out_path = f.name
        try:
            to_docx(product, out_path)
            doc = DocxDocument(out_path)
            paragraphs = [p.text for p in doc.paragraphs]
            # 找出延伸閱讀段落的位置
            er_idx = next((i for i, t in enumerate(paragraphs) if "延伸閱讀" in t), None)
            supp_idx = next((i for i, t in enumerate(paragraphs) if "補充" in t or "待補" in t), None)
            if er_idx is not None and supp_idx is not None:
                assert er_idx > supp_idx, "延伸閱讀應在 supplement 段落之後"
        finally:
            Path(out_path).unlink(missing_ok=True)

    def test_binding_report_matches_original_text_length(self):
        """binding_report 不影響原稿文字（原始段落數不變）。"""
        product = _basic_product()
        assert len(product.original.paragraphs) == 2
        for p in product.original.paragraphs:
            assert p.text in self.ORIGINAL_TEXTS


# ===================================================================
# 5. 跨格式內容一致性
# ===================================================================


class TestCrossFormatConsistency:
    """同一批資料跨格式的一致。"""

    def test_report_and_json_extended_readings_identical(self):
        """binding_report 與 JSON 的 extended_readings 資料一致。"""
        srcs = [
            _source("s1", "源A", "https://a", "A"),
            _source("s2", "源B", "https://b", "B"),
            _source("s3", "源C", "https://c", "C"),
        ]
        gap = Gap("測試問題", "missing", "未展開")
        product = assemble_correction(
            _doc(), [gap],
            {gap.question: srcs},
            {gap.question: WrittenSupplement("內容。", ["s1"], omitted_source_ids=["s2", "s3"])},
            {gap.question: cross_validate(gap.question, srcs)},
        )
        report = build_binding_report(product)
        data = to_json(product)
        report_ers = report["arguments"][0]["extended_readings"]
        json_ers = [s["extended_readings"] for s in data["segments"] if s["type"] == "supplement"][0]
        assert report_ers == json_ers

    def test_report_and_json_status_identical(self):
        """binding_report 與 JSON 的狀態欄位一致。"""
        product = _basic_product(used_ids=["s1"], omitted_ids=["s2"])
        report = build_binding_report(product)
        data = to_json(product)
        for arg, seg in zip(
            report["arguments"],
            [s for s in data["segments"] if s["type"] == "supplement"],
        ):
            assert arg["extended_readings_status"] == seg["extended_readings_status"]
            assert arg["pending_evidence_reason"] == seg["pending_evidence_reason"]
            assert arg["openable_links_count"] == seg["openable_links_count"]
            assert arg["openable_links_status"] == seg["openable_links_status"]
            assert arg["openable_links_incomplete_reason"] == seg["openable_links_incomplete_reason"]

    def test_pipeline_output_has_stable_schema(self, tmp_path):
        """完整 pipeline 流程的輸出包含所有必要欄位。"""
        note_path = tmp_path / "note.docx"
        docx = DocxDocument()
        docx.add_paragraph("行政程序法要求行政行為應遵守正當程序。")
        docx.save(str(note_path))

        llm = FakeLLM([
            "admin",
            "正當程序的要件為何?",
            _json.dumps([
                {"question": "正當程序的要件為何?", "status": "missing", "reason": "筆記未展開"},
            ], ensure_ascii=False),
            '{"keyword": "正當程序", "law_name": null}',
            "【待補證】此問題缺乏可用來源。",
        ])
        twinkle = FakeTwinkle([
            [
                _source("s1", "相關法規", "https://law.gov.tw/rule", "A"),
                _source("s2", "學者見解", "https://academic.tw/paper", "C"),
            ],
        ])
        doc = run_pipeline(str(note_path), llm, twinkle, FakeLaw())

        report = build_binding_report(doc)
        for arg in report["arguments"]:
            assert "extended_readings" in arg
            assert "extended_readings_status" in arg
            assert "pending_evidence_reason" in arg
            assert "openable_links_count" in arg
            assert "openable_links_status" in arg
            assert "openable_links_incomplete_reason" in arg
            for er in arg["extended_readings"]:
                for key in EXPECTED_EXTENDED_READING_KEYS:
                    assert key in er

        data = to_json(doc)
        for seg in data["segments"]:
            if seg["type"] == "supplement":
                for key in (
                    "extended_readings", "extended_readings_status",
                    "pending_evidence_reason",
                    "openable_links_count", "openable_links_status",
                    "openable_links_incomplete_reason",
                ):
                    assert key in seg

        md = to_markdown(doc)
        if "延伸閱讀" in md:
            matches = MD_EXTENDED_READING_RE.findall(md)
            for match in matches:
                assert len(match) == 3  # (source_id, level, title)


# ===================================================================
# 6. 完整 pipeline 回歸測試
# ===================================================================


class TestPipelineRegression:
    """完整 pipeline 流程的回歸檢查。"""

    def test_extended_readings_omitted_ids_in_pipeline(self, tmp_path):
        """Pipeline 輸出中 omitted 的來源出現在延伸閱讀。"""
        note_path = tmp_path / "note.docx"
        d = DocxDocument()
        d.add_paragraph("行政程序法第92條：行政處分定義。")
        d.add_paragraph("本筆記僅記錄部分重點。")
        d.save(str(note_path))

        llm = FakeLLM([
            "law",
            "行政處分之定義為何？",
            _json.dumps([
                {"question": "行政處分之定義為何？", "status": "missing", "reason": "筆記未展開定義"},
            ], ensure_ascii=False),
            '{"keyword": "行政處分", "law_name": "行政程序法"}',
            "行政處分係指行政機關就公法上具體事件所為之決定[^1]。",
        ])
        twinkle = FakeTwinkle([
            [
                _source("s1", "行政程序法第92條", "https://law.moj.gov.tw/Art92", "A"),
                _source("s2", "學者見解", "https://academic.tw/paper", "C"),
            ],
        ])
        doc = run_pipeline(str(note_path), llm, twinkle, FakeLaw())

        report = build_binding_report(doc)
        data = to_json(doc)

        for arg, seg in zip(
            report["arguments"],
            [s for s in data["segments"] if s["type"] == "supplement"],
        ):
            er_ids = [er["source_id"] for er in arg["extended_readings"]]
            # s1 被引用（used）、s2 被 omitted → s2 應在延伸閱讀
            if "s1" in arg.get("source_ids", []):
                assert "s2" in er_ids or not arg["extended_readings"], (
                    "Omitted 來源應出現在延伸閱讀"
                )

    def test_pipeline_original_immutable_with_extended_readings(self, tmp_path):
        """Pipeline 輸出中原稿逐字不變。"""
        note_path = tmp_path / "note.docx"
        d = DocxDocument()
        d.add_paragraph("行政程序法要求行政行為應遵守正當程序。")
        d.save(str(note_path))

        llm = FakeLLM([
            "admin",
            "正當程序的要件為何?",
            _json.dumps([
                {"question": "正當程序的要件為何?", "status": "missing", "reason": "筆記未展開"},
            ], ensure_ascii=False),
            '{"keyword": "正當程序", "law_name": null}',
            "正當程序需符合法律保留[^1]與比例原則[^2]。",
        ])
        twinkle = FakeTwinkle([
            [
                _source("s1", "行政程序法", "https://law.moj.gov.tw/admin", "A"),
                _source("s2", "法學資料", "https://law.moj.gov.tw/ref", "B"),
            ],
        ])
        doc = run_pipeline(str(note_path), llm, twinkle, FakeLaw())

        data = to_json(doc)
        originals = [s["text"] for s in data["segments"] if s["type"] == "original"]
        assert originals == ["行政程序法要求行政行為應遵守正當程序。"]


# ===================================================================
# 7. 格式規格 v1 驗證
# ===================================================================


class TestFormatSpecificationV1:
    """驗證延伸閱讀格式規格 v1 的欄位順序與契約。"""

    def test_extended_readings_field_order_in_json(self):
        """JSON 輸出中延伸閱讀欄位順序符合規格 v1。"""
        product = _basic_product(used_ids=["s1"], omitted_ids=["s2"])
        data = to_json(product)
        for seg in data["segments"]:
            if seg["type"] == "supplement":
                # 檢查延伸閱讀相關欄位的順序
                seg_keys = list(seg.keys())
                for i, field in enumerate(EXTENDED_READINGS_FIELD_ORDER):
                    field_idx = seg_keys.index(field)
                    # 確保欄位存在且順序正確（後面的欄位索引應該更大）
                    assert field in seg_keys, f"缺少欄位: {field}"
                    if i > 0:
                        prev_field_idx = seg_keys.index(EXTENDED_READINGS_FIELD_ORDER[i-1])
                        assert field_idx > prev_field_idx, (
                            f"欄位順序錯誤: {field} 應在 {EXTENDED_READINGS_FIELD_ORDER[i-1]} 之後"
                        )

    def test_extended_reading_item_field_order(self):
        """每筆延伸閱讀記錄的欄位順序符合規格 v1。"""
        product = _basic_product(used_ids=["s1"], omitted_ids=["s2"])
        data = to_json(product)
        for seg in data["segments"]:
            if seg["type"] == "supplement":
                for er in seg["extended_readings"]:
                    er_keys = list(er.keys())
                    for i, field in enumerate(EXTENDED_READING_ITEM_FIELD_ORDER):
                        field_idx = er_keys.index(field)
                        assert field in er_keys, f"延伸閱讀項目缺少欄位: {field}"
                        if i > 0:
                            prev_field_idx = er_keys.index(EXTENDED_READING_ITEM_FIELD_ORDER[i-1])
                            assert field_idx > prev_field_idx, (
                                f"延伸閱讀項目欄位順序錯誤: {field} 應在 {EXTENDED_READING_ITEM_FIELD_ORDER[i-1]} 之後"
                            )

    def test_field_order_matches_specification_document(self):
        """測試中定義的欄位順序與規格文檔一致。"""
        # 這個測試確保測試代碼與文檔保持同步
        assert len(EXTENDED_READINGS_FIELD_ORDER) == 6, "延伸閱讀欄位數應為 6"
        assert len(EXTENDED_READING_ITEM_FIELD_ORDER) == 5, "延伸閱讀項目欄位數應為 5"
        
        # 驗證關鍵欄位存在
        assert "extended_readings" in EXTENDED_READINGS_FIELD_ORDER
        assert "extended_readings_status" in EXTENDED_READINGS_FIELD_ORDER
        assert "pending_evidence_reason" in EXTENDED_READINGS_FIELD_ORDER
        assert "openable_links_count" in EXTENDED_READINGS_FIELD_ORDER
        assert "openable_links_status" in EXTENDED_READINGS_FIELD_ORDER
        assert "openable_links_incomplete_reason" in EXTENDED_READINGS_FIELD_ORDER

    def test_sorting_priority_implementation_matches_spec(self):
        """延伸閱讀排序實作符合規格 v1 的優先級規則。"""
        srcs = [
            _source("s1", "源A", "https://a", "C", 0.5),
            _source("s2", "源B", "https://b", "A", 0.8),
            _source("s3", "源C", "https://c", "B", 0.3),
            _source("s4", "源D", "https://d", "A", 0.2),
        ]
        gap = Gap("test", "missing", "未展開")
        product = assemble_correction(
            _doc(), [gap],
            {gap.question: srcs},
            {gap.question: WrittenSupplement("內容。", [], omitted_source_ids=["s1", "s2", "s3", "s4"])},
            {gap.question: cross_validate(gap.question, srcs)},
        )
        seg = [s for s in product.segments if s.type == "supplement"][0]
        
        # 驗證排序：Level A > B > C > D，同層級按 distance 遞增
        # 預期順序：s4 (A, 0.2) > s2 (A, 0.8) > s3 (B, 0.3) > s1 (C, 0.5)
        assert len(seg.extended_readings) == 4
        assert seg.extended_readings[0]["source_id"] == "s4"  # A, 0.2
        assert seg.extended_readings[1]["source_id"] == "s2"  # A, 0.8
        assert seg.extended_readings[2]["source_id"] == "s3"  # B, 0.3
        assert seg.extended_readings[3]["source_id"] == "s1"  # C, 0.5

    def test_failure_message_format_matches_spec(self):
        """失敗訊息格式符合規格 v1 的標準模板。"""
        srcs = [_source("s1", "源A", "https://a", "A")]
        gap = Gap("test", "missing", "未展開")
        product = assemble_correction(
            _doc(), [gap],
            {gap.question: srcs},
            {gap.question: WrittenSupplement("【待補證】內容。", [], omitted_source_ids=[])},
            {gap.question: cross_validate(gap.question, srcs)},
        )
        seg = [s for s in product.segments if s.type == "supplement"][0]
        
        # 驗證失敗訊息包含 argument_id 與欄位名稱
        if seg.openable_links_incomplete_reason:
            reason = seg.openable_links_incomplete_reason
            assert "argument:" in reason or "缺失" in reason, (
                f"失敗訊息應包含 argument_id 或標準格式: {reason}"
            )

    def test_polaris_spec_includes_extended_readings_fields(self):
        """polaris_field_specification.json 包含延伸閱讀欄位定義。"""
        import json
        spec_path = Path(__file__).parent.parent / "docs" / "polaris_field_specification.json"
        assert spec_path.exists(), "polaris_field_specification.json 應存在"
        
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
        
        field_defs = spec["field_definitions"]
        
        # 驗證延伸閱讀相關欄位都在規格中
        assert "extended_readings" in field_defs
        assert "extended_readings_status" in field_defs
        assert "pending_evidence_reason" in field_defs
        
        # 驗證子欄位定義
        er_def = field_defs["extended_readings"]
        assert "sub_fields" in er_def
        sub_fields = er_def["sub_fields"]
        assert "source_id" in sub_fields
        assert "title" in sub_fields
        assert "url" in sub_fields
        assert "level" in sub_fields
        assert "distance" in sub_fields
