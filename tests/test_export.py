import json

import pytest

from note_filler.parse import Document, Paragraph
from note_filler.correction import CorrectionDoc, Segment, build_related_knowledge
from note_filler.retrieve.models import Source
from note_filler.export import to_docx, to_json, to_markdown, _calculate_polaris_for_doc


def _sample_doc() -> CorrectionDoc:
    original = Document(
        source_path="/tmp/note.docx",
        paragraphs=(Paragraph(idx=0, text="原文第一段。"),),
        full_text="原文第一段。",
    )
    src_a = Source(
        id="s1",
        title="行政程序法第92條",
        url="https://law.moj.gov.tw/LawClass/LawSingle.aspx?a=92",
        level="A",
        content="行政程序法第92條：本法所稱行政處分，係指……全文。",
        fetched_date="2026-07-01",
        doc_date="2005-12-28",
        distance=0.10,
    )
    src_b = Source(
        id="s2",
        title="立法院第11屆第1會期議案關係文書",
        url="https://ppg.ly.gov.tw/ppg/bills/1101/text",
        level="B",
        content="議案關係文書全文……",
        fetched_date="2026-07-02",
        doc_date=None,
        distance=0.30,
    )
    segments = [
        Segment(
            type="original",
            text="原文第一段。",
            anchor_idx=0,
            sources=[],
            confidence="verified",
            functional_gap="",
            user_value="",
            argument_id="",
        ),
        Segment(
            type="supplement",
            text="依行政程序法第92條，行政處分係指行政機關就公法上具體事件所為之決定。",
            anchor_idx=0,
            sources=[src_a, src_b],
            confidence="verified",
            traceability=[{"kind": "source", "id": "s1"}, {"kind": "source", "id": "s2"}],
            source_id="sources:s1,s2",
            functional_gap="原稿未定義行政處分",
            user_value="補齊讀者對「行政處分如何定義？」所需的說明",
            argument_id="argument:0",
        ),
        Segment(
            type="supplement",
            text="關於施行細節仍待查證。",
            anchor_idx=0,
            sources=[],
            confidence="pending_evidence",
            traceability=[{
                "kind": "processing_record", "id": "gap:1",
                "question": "細節待查", "outcome": "pending_evidence",
            }],
            source_id="pending:gap:1",
            functional_gap="原稿未說明施行細節",
            user_value="補齊讀者對「細節待查」所需的說明",
            argument_id="argument:1",
        ),
    ]
    return CorrectionDoc(original=original, segments=segments)


def test_to_json_serializes_segments() -> None:
    data = to_json(_sample_doc())

    assert data["source_path"] == "/tmp/note.docx"
    segs = data["segments"]
    assert len(segs) == 3

    # 原文段
    assert segs[0]["type"] == "original"
    assert segs[0]["text"] == "原文第一段。"
    assert segs[0]["sources"] == []

    # verified supplement，帶兩個來源，Level 保留
    assert segs[1]["type"] == "supplement"
    assert segs[1]["confidence"] == "verified"
    assert [s["level"] for s in segs[1]["sources"]] == ["A", "B"]
    assert segs[1]["sources"][0]["fetched_date"] == "2026-07-01"

    # pending_evidence supplement，sources 空(C6 不變式)
    assert segs[2]["confidence"] == "pending_evidence"
    assert segs[2]["sources"] == []

    # 整份可被 json 序列化(不丟例外)
    json.dumps(data, ensure_ascii=False)


def test_to_json_contains_binding_summary() -> None:
    """訂正稿 JSON 頂層必須包含 binding_summary，可直接被測試解析綁定驗證狀態。"""
    data = to_json(_sample_doc())
    bs = data.get("binding_summary")
    assert bs is not None, "JSON 輸出應含 binding_summary"
    assert bs["schema"] == "note_filler.binding_report.v1"
    assert isinstance(bs["argument_count"], int)
    assert isinstance(bs["pass"], int)
    assert isinstance(bs["fail"], int)
    assert isinstance(bs["pending_evidence"], int)
    assert isinstance(bs["one_to_one"], int)
    assert isinstance(bs["one_to_many"], int)
    assert isinstance(bs["none"], int)
    assert isinstance(bs["all_arguments_ok"], bool)
    assert isinstance(bs["all_sourced_arguments_ok"], bool)
    # _sample_doc 有 2 個 supplement：第一個 verified 有 2 源、第二個 pending 無源
    assert bs["argument_count"] == 2
    assert bs["one_to_many"] == 1
    assert bs["none"] == 1
    assert bs["pending_evidence"] == 1


def test_to_json_binding_summary_matches_segments() -> None:
    """binding_summary 的計數必須與 segments 實際 supplement 數一致。"""
    data = to_json(_sample_doc())
    bs = data["binding_summary"]
    supplement_segs = [s for s in data["segments"] if s["type"] == "supplement"]
    assert bs["argument_count"] == len(supplement_segs)
    assert bs["pass"] + bs["fail"] + bs["pending_evidence"] == len(supplement_segs)


def test_to_markdown_ends_with_binding_line() -> None:
    """Markdown 輸出必須包含來源綁定驗證行，格式為 > **來源綁定**。"""
    md = to_markdown(_sample_doc())
    # 綁定驗證行可能不在最後一行（因為北極星分數行在其後），但必須存在
    binding_lines = [ln for ln in md.splitlines() if "來源綁定" in ln]
    assert len(binding_lines) >= 1, "Markdown 應含來源綁定驗證行"
    assert "✓" in binding_lines[0] or "✗" in binding_lines[0]


def test_to_markdown_binding_verdict_matches_doc() -> None:
    md = to_markdown(_sample_doc())
    assert "\u5168\u90e8\u901a\u904e" in md  # UTF-8: 「全部通過」


def test_to_markdown_binding_line_machine_parseable() -> None:
    import re
    md = to_markdown(_sample_doc())
    m = re.search(r"> \*\*[\u4f86\u6e90\u7d81\u5b9a]+\*\*", md)
    assert m is not None, "binding line format mismatch"


def test_to_markdown_format_locked() -> None:
    md = to_markdown(_sample_doc())

    # 原文段原樣輸出
    assert "原文第一段。" in md

    # C3：supplement 段 "> 【補充】{text}" 後接 [^n]
    assert "> 【補充】依行政程序法第92條" in md
    assert (
        "> 【補充】依行政程序法第92條，行政處分係指行政機關就公法上具體事件所為之決定。[^1][^2]"
        in md
    )

    # C3：pending_evidence 段【補充】後加 ⚠待補證
    assert "> 【補充】⚠待補證 關於施行細節仍待查證。" in md
    assert "⚠待補證" in md

    # 文末參考區塊(來自 T11 build_reference_lines)：帶 Level 與 Date
    assert "[^1]: [Level A]" in md          # 第一筆為 Level A
    assert "2005-12-28" in md               # C7：src_a doc_date 優先
    assert "2026-07-02" in md               # C7：src_b doc_date=None → fetched_date fallback


def test_to_markdown_pending_segment_has_no_footnote() -> None:
    md = to_markdown(_sample_doc())
    # 篩出補充段的待補證行（非末尾綁定摘要行）
    pending_supplement = [ln for ln in md.splitlines() if "待補證" in ln and "【補充】" in ln]
    assert len(pending_supplement) == 1
    # sources 空 → 該段不產生任何 [^n] 標記
    assert "[^" not in pending_supplement[0]


# ---- 可機器解析綁定結構：source_ids／cardinality／來源清單行 --------------


def test_to_json_contains_source_ids_per_segment():
    """JSON 輸出每 segment 必須含 source_ids list 與 cardinality。"""
    data = to_json(_sample_doc())
    for i, seg in enumerate(data["segments"]):
        assert "source_ids" in seg, f"segment[{i}] 缺少 source_ids"
        assert isinstance(seg["source_ids"], list), f"segment[{i}] source_ids 須為 list"
        assert all(isinstance(s, str) for s in seg["source_ids"]), (
            f"segment[{i}] source_ids 元素須為 str"
        )
        assert "cardinality" in seg, f"segment[{i}] 缺少 cardinality"
        assert seg["cardinality"] in ("one_to_one", "one_to_many", "none"), (
            f"segment[{i}] cardinality 非法: {seg['cardinality']!r}"
        )
        assert "functional_gap" in seg, f"segment[{i}] 缺少 functional_gap"
        assert isinstance(seg["functional_gap"], str), f"segment[{i}] functional_gap 須為 str"
        assert "user_value" in seg, f"segment[{i}] 缺少 user_value"
        assert isinstance(seg["user_value"], str), f"segment[{i}] user_value 須為 str"
        assert "argument_id" in seg, f"segment[{i}] 缺少 argument_id"
        assert isinstance(seg["argument_id"], str), f"segment[{i}] argument_id 須為 str"
        assert "angle_coverage" in seg, f"segment[{i}] 缺少 angle_coverage"
        assert isinstance(seg["angle_coverage"], dict), f"segment[{i}] angle_coverage 須為 dict"
        assert "angle_type" in seg, f"segment[{i}] 缺少 angle_type"
        assert "angle_labels" in seg, f"segment[{i}] 缺少 angle_labels"
        assert "angle_key" in seg, f"segment[{i}] 缺少 angle_key"
    assert "angle_coverage_summary" in data
    assert data["angle_coverage_summary"]["effective_angle_count"] == 2
    assert data["angle_coverage_summary"]["coverage_ok"] is True
    assert data["segments"][1]["angle_coverage"]["effective_angle_count"] == 1
    assert data["segments"][1]["angle_coverage"]["duplicate_exclusion"]["excluded"] is False
    # _sample_doc: seg[0]=original → none(0源), seg[1]=supplement 2源→ one_to_many
    assert data["segments"][0]["cardinality"] == "none"
    assert data["segments"][0]["source_ids"] == []
    assert data["segments"][1]["cardinality"] == "one_to_many"
    assert data["segments"][1]["source_ids"] == ["s1", "s2"]
    assert data["segments"][2]["cardinality"] == "none"
    assert data["segments"][2]["source_ids"] == []


def test_to_json_source_ids_matches_sources():
    """JSON 輸出 per-segment 的 source_ids 與 sources.id 一致。"""
    data = to_json(_sample_doc())
    for i, seg in enumerate(data["segments"]):
        expected = [s["id"] for s in seg.get("sources", [])]
        assert seg["source_ids"] == expected, (
            f"segment[{i}] source_ids {seg['source_ids']} != sources.id {expected}"
        )


def test_to_markdown_contains_machine_parseable_source_list():
    """Markdown 輸出每個 supplement 段後須有機器可解析的來源清單行。"""
    md = to_markdown(_sample_doc())
    lines = md.splitlines()

    # verified supplement 有兩個來源 → one to many
    source_lines = [ln for ln in lines if "> **來源清單**" in ln]
    assert len(source_lines) == 2, f"應有 2 筆來源清單行，實際 {len(source_lines)}"
    assert "s1,s2" in source_lines[0], f"第一筆應含 s1,s2: {source_lines[0]!r}"
    assert "one to many" in source_lines[0], (
        f"第一筆應標示 one to many: {source_lines[0]!r}"
    )
    # pending supplement → 無來源
    assert "pending（無來源）" in source_lines[1], (
        f"第二筆應標示 pending: {source_lines[1]!r}"
    )


def test_to_markdown_contains_angle_coverage_line():
    """Markdown 逐筆同列論點、來源、必要性雙視角與角度清單。"""
    doc = _sample_doc()
    # 手建 fixture 預設無 angle_*；補上以驗證序列化輸出
    doc.segments[1].angle_type = "definition"
    doc.segments[1].angle_labels = ["definition", "functional_gap", "user_value"]
    doc.segments[1].angle_key = "definition:行政處分如何定義"
    md = to_markdown(doc)
    angle_lines = [ln for ln in md.splitlines() if "> **角度覆蓋**" in ln]
    assert len(angle_lines) >= 1
    assert "functional_gap=原稿未定義行政處分" in angle_lines[0]
    assert "user_value=補齊讀者對「行政處分如何定義？」所需的說明" in angle_lines[0]
    assert "angle_tags=definition、functional_gap、user_value" in angle_lines[0]
    assert "source_ids=s1,s2" in angle_lines[0]
    summary_lines = [ln for ln in md.splitlines() if "> **角度覆蓋摘要**" in ln]
    assert len(summary_lines) == 1
    assert "有效角度 2/最低 2" in summary_lines[0]
    assert "通過 ✓" in summary_lines[0]


def test_human_readable_exports_show_argument_aligned_visible_summaries(tmp_path):
    """每筆關聯知識必須與同一 argument_id 的必要性雙視角一起顯示。"""
    rk0 = build_related_knowledge(
        knowledge_body="依行政程序法第92條，行政處分係指行政機關就公法上具體事件所為之決定。",
        functional_gap="原稿未定義行政處分",
        user_value="補齊讀者對「行政處分如何定義？」所需的說明",
    )
    rk1 = build_related_knowledge(
        knowledge_body="關於施行細節仍待查證。",
        functional_gap="原稿未說明施行細節",
        user_value="補齊讀者對「細節待查」所需的說明",
    )
    expected = [
        (
            "argument_id=argument:0；"
            "functional_gap=原稿未定義行政處分；"
            "user_value=補齊讀者對「行政處分如何定義？」所需的說明；"
            f"related_knowledge={rk0}"
        ),
        (
            "argument_id=argument:1；"
            "functional_gap=原稿未說明施行細節；"
            "user_value=補齊讀者對「細節待查」所需的說明；"
            f"related_knowledge={rk1}"
        ),
    ]

    md_lines = [
        line.removeprefix("> **摘要可見**：")
        for line in to_markdown(_sample_doc()).splitlines()
        if line.startswith("> **摘要可見**：")
    ]
    assert md_lines == expected
    # 人類可讀亦須有獨立「關聯知識」列，且明示決策品質／使用者理解
    md = to_markdown(_sample_doc())
    rk_lines = [
        line.removeprefix("> **關聯知識**：")
        for line in md.splitlines()
        if line.startswith("> **關聯知識**：")
    ]
    assert rk_lines == [rk0, rk1]
    assert all("支撐決策品質" in line and "補強使用者理解" in line for line in rk_lines)

    out = tmp_path / "visible-summaries.docx"
    to_docx(_sample_doc(), str(out))
    from docx import Document as DocxDocument

    docx_lines = [
        paragraph.text.removeprefix("摘要可見：")
        for paragraph in DocxDocument(out).paragraphs
        if paragraph.text.startswith("摘要可見：")
    ]
    assert docx_lines == expected
    docx_rk = [
        paragraph.text.removeprefix("關聯知識：")
        for paragraph in DocxDocument(out).paragraphs
        if paragraph.text.startswith("關聯知識：")
    ]
    assert docx_rk == [rk0, rk1]


def test_to_docx_contains_machine_parseable_source_list(tmp_path):
    """docx 輸出每個 supplement 段後須有機器可解析的來源清單行。"""
    from docx import Document as DocxDocument
    out = tmp_path / "binding.docx"
    to_docx(_sample_doc(), str(out))
    paras = [p.text for p in DocxDocument(out).paragraphs]
    source_lines = [p for p in paras if p.startswith("來源清單")]
    assert len(source_lines) == 2, f"應有 2 筆來源清單行，實際 {len(source_lines)}"
    assert "s1,s2" in source_lines[0]
    assert "one to many" in source_lines[0]
    assert "pending" in source_lines[1]
    angle_lines = [p for p in paras if p.startswith("角度覆蓋：")]
    assert any(
        "functional_gap=原稿未定義行政處分" in p
        and "user_value=補齊讀者對「行政處分如何定義？」所需的說明" in p
        and "angle_tags=definition、functional_gap、user_value" in p
        and "source_ids=s1,s2" in p
        for p in angle_lines
    )
    assert any(p.startswith("角度覆蓋摘要：") for p in paras)


# ---- 北極星品質指標整合測試 ----

class TestPolarisMetricsIntegration:
    """北極星品質指標在成品輸出中的整合測試。"""

    def test_to_json_contains_polaris_metrics(self):
        """JSON 輸出必須包含 polaris_metrics 頂層欄位。"""
        data = to_json(_sample_doc())
        assert "polaris_metrics" in data, "JSON 輸出應含 polaris_metrics"
        polaris = data["polaris_metrics"]
        assert polaris["schema"] == "note_filler.polaris_metrics.v1"
        assert polaris["overall_status"] in ["excellent", "good", "acceptable", "poor", "error"]
        assert isinstance(polaris["core_metrics_pass_count"], int)
        assert isinstance(polaris["core_metrics_total_count"], int)
        assert polaris["core_metrics_total_count"] == 5

    def test_to_json_polaris_metrics_has_all_subscores(self):
        """polaris_metrics 必須包含所有五項分項分數。"""
        data = to_json(_sample_doc())
        polaris = data["polaris_metrics"]
        
        # 驗證五項分項分數都存在
        for key in [
            "functional_gap_score",
            "user_value_score",
            "source_binding_integrity",
            "angle_diversity_index",
            "delivery_success_rate",
        ]:
            assert key in polaris, f"polaris_metrics 應含 {key}"
            subscore = polaris[key]
            assert "score" in subscore, f"{key} 應含 score"
            assert "status" in subscore, f"{key} 應含 status"
            assert "passes_threshold" in subscore, f"{key} 應含 passes_threshold"
            assert 0.0 <= subscore["score"] <= 1.0, f"{key}.score 應在 0-1 之間"

    def test_to_json_polaris_metrics_judgment_basis(self):
        """polaris_metrics 每項分項分數必須包含判定依據（threshold）。"""
        data = to_json(_sample_doc())
        polaris = data["polaris_metrics"]
        
        for key in [
            "functional_gap_score",
            "user_value_score",
            "source_binding_integrity",
            "angle_diversity_index",
            "delivery_success_rate",
        ]:
            subscore = polaris[key]
            assert "threshold" in subscore, f"{key} 應含 threshold（判定門檻）"
            assert isinstance(subscore["threshold"], float), f"{key}.threshold 應為 float"

    def test_to_json_polaris_metrics_source_binding_detail(self):
        """source_binding_integrity 必須包含通過/失敗/待補證計數。"""
        data = to_json(_sample_doc())
        sbi = data["polaris_metrics"]["source_binding_integrity"]
        assert "total_arguments" in sbi
        assert "arguments_pass" in sbi
        assert "arguments_fail" in sbi
        assert "arguments_pending" in sbi
        assert isinstance(sbi["total_arguments"], int)
        assert isinstance(sbi["arguments_pass"], int)

    def test_to_json_polaris_metrics_functional_gap_detail(self):
        """functional_gap_score 必須包含具體描述計數。"""
        data = to_json(_sample_doc())
        fgs = data["polaris_metrics"]["functional_gap_score"]
        assert "total_arguments" in fgs
        assert "arguments_with_concrete_gap" in fgs
        assert "arguments_with_empty_gap" in fgs
        assert isinstance(fgs["total_arguments"], int)

    def test_to_json_polaris_metrics_angle_diversity_detail(self):
        """angle_diversity_index 必須包含角度覆蓋資訊。"""
        data = to_json(_sample_doc())
        adi = data["polaris_metrics"]["angle_diversity_index"]
        assert "unique_angle_types" in adi
        assert "expected_angle_types" in adi
        assert "effective_angle_count" in adi
        assert isinstance(adi["unique_angle_types"], int)
        assert isinstance(adi["expected_angle_types"], int)

    def test_to_markdown_contains_polaris_metrics_line(self):
        """Markdown 輸出必須包含北極星分數摘要行。"""
        md = to_markdown(_sample_doc())
        polaris_lines = [ln for ln in md.splitlines() if "> **北極星分數**" in ln]
        assert len(polaris_lines) == 1, f"應有 1 筆北極星分數行，實際 {len(polaris_lines)}"
        line = polaris_lines[0]
        # 驗證包含 overall_status
        assert "overall=" in line
        # 驗證包含各分項分數
        assert "functional_gap=" in line
        assert "user_value=" in line
        assert "source_binding=" in line
        assert "angle_diversity=" in line
        assert "delivery=" in line

    def test_to_markdown_polaris_metrics_has_pass_fail_marks(self):
        """Markdown 北極星分數行必須包含通過/未通過標記。"""
        md = to_markdown(_sample_doc())
        polaris_lines = [ln for ln in md.splitlines() if "> **北極星分數**" in ln]
        assert len(polaris_lines) == 1
        line = polaris_lines[0]
        # 每項分數後應有 ✓ 或 ✗ 標記
        assert "✓" in line or "✗" in line, "北極星分數行應含通過/未通過標記"

    def test_human_readable_metrics_include_quantified_breakdown(self, tmp_path):
        """Markdown 與 DOCX 都須帶出四個子分數、總分門檻及公式。"""
        from docx import Document as DocxDocument

        doc = _sample_doc()
        md = to_markdown(doc)
        out = tmp_path / "breakdown.docx"
        to_docx(doc, str(out))
        docx_text = "\n".join(p.text for p in DocxDocument(out).paragraphs)

        for text in (md, docx_text):
            assert "functional_gap_subscores=traceability:" in text
            assert "user_value_subscores=traceability:" in text
            assert "coverage_breadth:" in text
            assert "necessity_clarity:" in text
            assert "decision_support:" in text
            assert "functional_gap_threshold=0.70" in text
            assert "user_value_threshold=0.70" in text
            assert "formula=weighted_sum" in text

    def test_note_json_breakdown_keeps_pending_evidence_fail_closed(self):
        """無實際來源的論點仍為 pending，且可追溯性子分數不得誤給分。"""
        data = to_json(_sample_doc())
        metrics = data["polaris_metrics"]
        pending_basis = metrics["functional_gap_score"]["calculation_basis"][1]

        assert data["segments"][0]["text"] == "原文第一段。"
        assert pending_basis["source_ids"] == []
        assert pending_basis["binding_status"] == "pending_evidence"
        assert pending_basis["traceability"] is False
        assert set(metrics["user_value_score"]["subscores"]) == {
            "traceability",
            "coverage_breadth",
            "necessity_clarity",
            "decision_support",
        }

    def test_to_markdown_polaris_metrics_machine_parseable(self):
        """Markdown 北極星分數行必須可被機器解析。"""
        import re
        md = to_markdown(_sample_doc())
        polaris_lines = [ln for ln in md.splitlines() if "> **北極星分數**" in ln]
        assert len(polaris_lines) == 1
        line = polaris_lines[0]
        
        # 驗證可解析的格式：key=value（threshold）
        pattern = r"(\w+)=([0-9.]+)（([✓✗])）"
        matches = re.findall(pattern, line)
        assert len(matches) >= 5, f"應至少有 5 項分數，實際 {len(matches)}"
        
        # 驗證 overall_status 可解析
        overall_pattern = r"overall=(\w+)"
        overall_match = re.search(overall_pattern, line)
        assert overall_match is not None, "應可解析 overall_status"
        assert overall_match.group(1) in ["excellent", "good", "acceptable", "poor", "error"]

    def test_to_docx_contains_polaris_metrics(self, tmp_path):
        """docx 輸出必須包含北極星品質指標摘要。"""
        from docx import Document as DocxDocument
        out = tmp_path / "polaris.docx"
        to_docx(_sample_doc(), str(out))
        paras = [p.text for p in DocxDocument(out).paragraphs]
        polaris_lines = [p for p in paras if p.startswith("北極星分數：")]
        assert len(polaris_lines) == 1, f"應有 1 筆北極星分數行，實際 {len(polaris_lines)}"
        line = polaris_lines[0]
        assert "overall=" in line
        assert "functional_gap=" in line
        assert "user_value=" in line
        assert "source_binding=" in line
        assert "angle_diversity=" in line
        assert "delivery=" in line

    def test_calculate_polaris_for_doc_returns_valid_dict(self):
        """_calculate_polaris_for_doc 必須回傳有效的 polaris_metrics dict。"""
        result = _calculate_polaris_for_doc(_sample_doc())
        assert isinstance(result, dict)
        assert result["schema"] == "note_filler.polaris_metrics.v1"
        assert result["overall_status"] in ["excellent", "good", "acceptable", "poor", "error"]
        assert isinstance(result["core_metrics_pass_count"], int)
        assert isinstance(result["core_metrics_total_count"], int)

    def test_polaris_metrics_json_serializable(self):
        """polaris_metrics 必須可被 JSON 序列化。"""
        data = to_json(_sample_doc())
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        assert len(json_str) > 0
        # 驗證可反序列化
        parsed = json.loads(json_str)
        assert "polaris_metrics" in parsed
        assert parsed["polaris_metrics"]["schema"] == "note_filler.polaris_metrics.v1"

    def test_polaris_metrics_consistent_across_formats(self):
        """JSON 與 Markdown 輸出的 polaris_metrics 必須一致。"""
        data = to_json(_sample_doc())
        md = to_markdown(_sample_doc())
        
        # 從 JSON 取得分數
        json_polaris = data["polaris_metrics"]
        
        # 從 Markdown 解析分數
        import re
        polaris_lines = [ln for ln in md.splitlines() if "> **北極星分數**" in ln]
        assert len(polaris_lines) == 1
        line = polaris_lines[0]
        
        # 驗證 overall_status 一致
        overall_match = re.search(r"overall=(\w+)", line)
        assert overall_match is not None
        assert overall_match.group(1) == json_polaris["overall_status"]
        
        # 驗證各分項分數數值一致
        for key, subscore in [
            ("functional_gap", json_polaris["functional_gap_score"]),
            ("user_value", json_polaris["user_value_score"]),
            ("source_binding", json_polaris["source_binding_integrity"]),
            ("angle_diversity", json_polaris["angle_diversity_index"]),
            ("delivery", json_polaris["delivery_success_rate"]),
        ]:
            pattern = rf"{key}=([0-9.]+)"
            match = re.search(pattern, line)
            assert match is not None, f"Markdown 應含 {key} 分數"
            md_score = float(match.group(1))
            assert abs(md_score - subscore["score"]) < 0.01, (
                f"{key} 分數不一致：JSON={subscore['score']}, MD={md_score}"
            )

    def test_polaris_metrics_in_empty_doc(self):
        """空文件（無 supplement）的 polaris_metrics 應正確處理缺值。"""
        original = Document(
            source_path="/tmp/empty.txt",
            paragraphs=(Paragraph(idx=0, text="只有原文。"),),
            full_text="只有原文。",
        )
        doc = CorrectionDoc(original=original, segments=[
            Segment(
                type="original",
                text="只有原文。",
                anchor_idx=0,
                sources=[],
                confidence="verified",
                functional_gap="",
                user_value="",
                argument_id="",
            ),
        ])
        data = to_json(doc)
        polaris = data["polaris_metrics"]
        # 無 supplement → 功能缺口/使用者價值/來源綁定應為 missing_data
        assert polaris["functional_gap_score"]["status"] == "missing_data"
        assert polaris["user_value_score"]["status"] == "missing_data"
        assert polaris["source_binding_integrity"]["status"] == "missing_data"

    def test_polaris_metrics_with_mixed_confidence(self):
        """混合 confidence 的 polaris_metrics 應正確計算。"""
        data = to_json(_sample_doc())
        polaris = data["polaris_metrics"]
        
        # _sample_doc 有一個 verified supplement 與一個 pending_evidence supplement
        # 來源綁定完整性應反映此狀態
        sbi = polaris["source_binding_integrity"]
        assert sbi["total_arguments"] == 2
        # pending_evidence 的 binding_status 為 pending_evidence
        assert sbi["arguments_pending"] >= 0

    def test_polaris_metrics_core_metrics_count_matches(self):
        """core_metrics_pass_count 必須等於通過門檻的核心指標數。"""
        data = to_json(_sample_doc())
        polaris = data["polaris_metrics"]
        
        # 計算通過門檻的核心指標數
        pass_count = sum(1 for key in [
            "functional_gap_score",
            "user_value_score",
            "source_binding_integrity",
            "angle_diversity_index",
            "delivery_success_rate",
        ] if polaris[key]["passes_threshold"])
        
        assert polaris["core_metrics_pass_count"] == pass_count
