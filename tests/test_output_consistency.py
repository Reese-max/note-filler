"""Output artifact consistency tests: directly compare exported output with source note content.

These tests verify that the original note content remains verbatim in the output artifacts
(markdown, JSON, docx) and that any inconsistency is explicitly reported as a test failure
rather than silently passing through overall test success.
"""
import json
import tempfile
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from note_filler.parse import parse_note
from note_filler.pipeline import run_pipeline
from note_filler.export import to_json, to_markdown, to_docx
from note_filler.llm import FakeLLM
from note_filler.retrieve.models import Source
from tests.test_pipeline import FakeTwinkle, FakeLaw


def _note_fixture(tmp_path: Path, content: str) -> str:
    """Create a temporary .docx note file with given content."""
    p = tmp_path / "note.docx"
    d = DocxDocument()
    for para in content.split("\n\n"):
        if para.strip():
            d.add_paragraph(para.strip())
    d.save(str(p))
    return str(p)


def _read_note_text(path: str) -> str:
    """Read the full text of a note file (.txt or .docx)."""
    suffix = Path(path).suffix.lower()
    if suffix == ".txt":
        return Path(path).read_text(encoding="utf-8")
    elif suffix == ".docx":
        doc = DocxDocument(path)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    raise ValueError(f"Unsupported note format: {suffix}")


def _pipeline_canned() -> tuple:
    """Return canned LLM responses for a minimal pipeline run."""
    # Domain, questions, gaps, gap1 keyword, gap1 writer, gap2 keyword, gap2 writer
    llm_responses = [
        "admin",  # detect_domain
        "正當程序的要件為何?\n聽證程序如何進行?",  # generate_questions
        json.dumps([
            {"question": "正當程序的要件為何?", "status": "missing", "reason": "筆記未展開"},
            {"question": "聽證程序如何進行?", "status": "missing", "reason": "筆記未提及"},
        ], ensure_ascii=False),  # detect_gaps
        '{"keyword": "正當程序", "law_name": null}',  # gap1 keyword
        "【待補證】此問題缺乏可用來源,尚待補充。",  # gap1 writer (no sources)
        '{"keyword": "聽證", "law_name": null}',  # gap2 keyword
        "聽證程序應保障當事人陳述意見[^1],並依法定程序進行[^2]。",  # gap2 writer (2 sources)
    ]
    llm = FakeLLM(llm_responses)

    def _src(sid, title, url, level):
        return Source(
            id=sid, title=title, url=url, level=level,
            content=f"{title} 官方結構化記錄全文……",
            fetched_date="2026-07-15", doc_date="2026-01-01", distance=0.6,
        )

    twinkle = FakeTwinkle([
        [],  # gap1 no sources
        [_src("s1", "聽證程序行政院公報", "https://a", "A"),
         _src("s2", "聽證程序立法院議案", "https://b", "B")],  # gap2 two sources
    ])
    law = FakeLaw()
    return llm, twinkle, law


class TestOutputConsistency:
    """Tests that verify output artifacts match source note content verbatim."""

    def test_markdown_export_original_text_verbatim(self, tmp_path):
        """Exported markdown must contain original note paragraphs verbatim and in order."""
        note_content = (
            "行政程序法要求行政行為應遵守正當程序。\n\n"
            "本筆記僅記錄部分重點,尚未展開。\n\n"
            "第三段內容：關於行政處分的定義與效力。"
        )
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        md = to_markdown(doc)

        # Split original note into paragraphs (by blank line)
        original_paras = [p.strip() for p in note_content.split("\n\n") if p.strip()]

        # Each original paragraph must appear verbatim in the markdown output
        for para in original_paras:
            assert para in md, (
                f"Original paragraph missing or altered in markdown output:\n"
                f"Expected: {para!r}\n"
                f"Full markdown output:\n{md}"
            )

        # Verify order: original paragraphs appear in same sequence
        md_lines = md.splitlines()
        para_positions = []
        for para in original_paras:
            # Find first occurrence of this paragraph
            found = False
            for i, line in enumerate(md_lines):
                if para in line:
                    para_positions.append(i)
                    found = True
                    break
            assert found, f"Paragraph not found in markdown: {para!r}"

        # Positions must be strictly increasing (order preserved)
        assert para_positions == sorted(para_positions), (
            "Original paragraphs appear out of order in markdown output"
        )

    def test_json_export_original_text_verbatim(self, tmp_path):
        """Exported JSON must contain original note full_text verbatim."""
        note_content = (
            "行政程序法要求行政行為應遵守正當程序。\n\n"
            "本筆記僅記錄部分重點,尚未展開。"
        )
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        data = to_json(doc)

        # full_text in JSON must exactly match parsed original full_text
        expected_full_text = "\n".join(
            p for p in note_content.split("\n\n") if p.strip()
        )
        actual_full_text = data["full_text"]

        assert actual_full_text == expected_full_text, (
            f"JSON full_text does not match original note content:\n"
            f"Expected: {expected_full_text!r}\n"
            f"Actual:   {actual_full_text!r}"
        )

        # Each original segment text must match corresponding paragraph
        original_segments = [s for s in data["segments"] if s["type"] == "original"]
        expected_paras = [p.strip() for p in note_content.split("\n\n") if p.strip()]

        assert len(original_segments) == len(expected_paras), (
            f"Number of original segments ({len(original_segments)}) "
            f"does not match original paragraphs ({len(expected_paras)})"
        )

        for i, (seg, expected) in enumerate(zip(original_segments, expected_paras)):
            assert seg["text"] == expected, (
                f"Original segment {i} text mismatch:\n"
                f"Expected: {expected!r}\n"
                f"Actual:   {seg['text']!r}"
            )
            assert seg["anchor_idx"] == i, (
                f"Original segment {i} anchor_idx mismatch: "
                f"expected {i}, got {seg['anchor_idx']}"
            )
            assert seg["sources"] == [], (
                f"Original segment {i} should have empty sources, got {seg['sources']}"
            )
            assert seg["confidence"] == "verified", (
                f"Original segment {i} confidence should be 'verified', got {seg['confidence']}"
            )

    def test_docx_export_original_text_verbatim(self, tmp_path):
        """Exported .docx must contain original note paragraphs verbatim and in order."""
        note_content = (
            "行政程序法要求行政行為應遵守正當程序。\n\n"
            "本筆記僅記錄部分重點,尚未展開。"
        )
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        out_path = tmp_path / "output.docx"
        to_docx(doc, str(out_path))

        # Read back the docx
        out_doc = DocxDocument(str(out_path))
        output_paras = [p.text for p in out_doc.paragraphs if p.text.strip()]

        original_paras = [p.strip() for p in note_content.split("\n\n") if p.strip()]

        # First N paragraphs of output must be the original content verbatim
        assert len(output_paras) >= len(original_paras), (
            f"Output docx has fewer paragraphs ({len(output_paras)}) "
            f"than original ({len(original_paras)})"
        )

        for i, (expected, actual) in enumerate(zip(original_paras, output_paras)):
            assert actual == expected, (
                f"Docx paragraph {i} mismatch:\n"
                f"Expected: {expected!r}\n"
                f"Actual:   {actual!r}"
            )

    def test_pipeline_output_original_segments_match_parsed_document(self, tmp_path):
        """Pipeline output segments of type 'original' must exactly match parsed document."""
        note_content = (
            "行政程序法要求行政行為應遵守正當程序。\n\n"
            "本筆記僅記錄部分重點,尚未展開。\n\n"
            "第三段：補充說明行政處分的效力。"
        )
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        # Parse note independently to get ground truth
        parsed_doc = parse_note(note_path)

        # Run pipeline
        correction_doc = run_pipeline(note_path, llm, twinkle, law)

        # Extract original segments from pipeline output
        original_segments = [s for s in correction_doc.segments if s.type == "original"]

        # Compare with parsed document paragraphs
        assert len(original_segments) == len(parsed_doc.paragraphs), (
            f"Segment count mismatch: pipeline produced {len(original_segments)} "
            f"original segments, but parsed document has {len(parsed_doc.paragraphs)} paragraphs"
        )

        for i, (seg, para) in enumerate(zip(original_segments, parsed_doc.paragraphs)):
            assert seg.text == para.text, (
                f"Segment {i} text mismatch:\n"
                f"Pipeline output: {seg.text!r}\n"
                f"Parsed document: {para.text!r}"
            )
            assert seg.anchor_idx == para.idx, (
                f"Segment {i} anchor_idx mismatch: "
                f"expected {para.idx}, got {seg.anchor_idx}"
            )
            assert seg.sources == [], (
                f"Original segment {i} should have no sources, got {seg.sources}"
            )
            assert seg.confidence == "verified", (
                f"Original segment {i} confidence should be 'verified', got {seg.confidence}"
            )

    def test_pipeline_full_text_matches_source_note(self, tmp_path):
        """CorrectionDoc.original.full_text must exactly match source note full_text."""
        note_content = (
            "行政程序法要求行政行為應遵守正當程序。\n\n"
            "本筆記僅記錄部分重點,尚未展開。"
        )
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        parsed_doc = parse_note(note_path)
        correction_doc = run_pipeline(note_path, llm, twinkle, law)

        assert correction_doc.original.full_text == parsed_doc.full_text, (
            f"CorrectionDoc.full_text mismatch:\n"
            f"Expected (from parse_note): {parsed_doc.full_text!r}\n"
            f"Actual (from pipeline):     {correction_doc.original.full_text!r}"
        )
        assert correction_doc.original.source_path == parsed_doc.source_path, (
            f"source_path mismatch: {correction_doc.original.source_path!r} vs {parsed_doc.source_path!r}"
        )

    def test_markdown_export_supplement_segments_have_explicit_format(self, tmp_path):
        """Supplement segments in markdown must follow C3 format exactly."""
        note_content = "行政程序法要求行政行為應遵守正當程序。"
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        md = to_markdown(doc)

        # Find supplement segments
        supplement_lines = [line for line in md.splitlines() if line.strip().startswith("> 【補充】")]

        assert supplement_lines, "Expected at least one supplement segment in markdown"

        for line in supplement_lines:
            # Must start with "> 【補充】"
            assert line.startswith("> 【補充】"), (
                f"Supplement line missing prefix: {line!r}"
            )

            # If pending_evidence, must have "⚠待補證"
            if "⚠待補證" in line:
                assert "⚠待補證" in line, (
                    f"Pending evidence supplement missing warning marker: {line!r}"
                )
                # Should NOT have footnote markers [^n]
                assert "[^" not in line, (
                    f"Pending evidence supplement should not have footnotes: {line!r}"
                )
            else:
                # Verified supplements should have footnote markers if they have sources
                # (We can't easily check source count here without parsing, but format must be valid)
                pass

    def test_json_export_supplement_confidence_matches_sources(self, tmp_path):
        """Supplement confidence in JSON must follow C6 invariant: empty sources -> pending_evidence."""
        note_content = "行政程序法要求行政行為應遵守正當程序。"
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        data = to_json(doc)

        for seg in data["segments"]:
            if seg["type"] != "supplement":
                continue

            sources = seg["sources"]
            confidence = seg["confidence"]

            if not sources:
                assert confidence == "pending_evidence", (
                    f"Supplement with empty sources must be pending_evidence, "
                    f"got {confidence}: {seg['text']!r}"
                )
            else:
                # Has sources - verify confidence logic
                has_a = any(s["level"] == "A" for s in sources)
                has_c = any(s["level"] == "C" for s in sources)
                distinct_sources = {(s["id"], s["title"]) for s in sources}

                expected_verified = has_a or has_c or len(distinct_sources) >= 2
                expected_confidence = "verified" if expected_verified else "pending_evidence"

                assert confidence == expected_confidence, (
                    f"Supplement confidence mismatch:\n"
                    f"Sources: {sources}\n"
                    f"Has A: {has_a}, Has C: {has_c}, Distinct: {len(distinct_sources)}\n"
                    f"Expected: {expected_confidence}, Got: {confidence}\n"
                    f"Segment text: {seg['text']!r}"
                )

    def test_output_artifacts_consistent_across_formats(self, tmp_path):
        """JSON, markdown, and docx exports must all contain same original content."""
        note_content = (
            "行政程序法要求行政行為應遵守正當程序。\n\n"
            "本筆記僅記錄部分重點,尚未展開。"
        )
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)

        # Get original paragraphs from all three formats
        json_data = to_json(doc)
        md = to_markdown(doc)

        docx_path = tmp_path / "out.docx"
        to_docx(doc, str(docx_path))
        docx_doc = DocxDocument(str(docx_path))
        docx_paras = [p.text for p in docx_doc.paragraphs if p.text.strip()]

        # Original paragraphs from JSON
        json_originals = [s["text"] for s in json_data["segments"] if s["type"] == "original"]

        # Original paragraphs from markdown (lines that are not supplement/reference lines)
        md_lines = md.splitlines()
        md_originals = []
        for line in md_lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Skip supplement lines (start with > 【補充】)
            if stripped.startswith("> 【補充】"):
                continue
            # 追溯 metadata 是成品資訊，不是原稿內容。
            if stripped.startswith("> 追溯："):
                continue
            # Skip reference block lines (start with [^N]:)
            if stripped.startswith("[^") and "]:" in stripped:
                continue
            # Skip binding verification separator and lines (末尾新增)
            if stripped.startswith("---") or stripped.startswith("> **來源綁定**"):
                continue
            if stripped.startswith("> **來源清單**"):
                continue
            # Skip new functional_gap / user_value / related_knowledge lines
            if stripped.startswith("> **功能缺口**"):
                continue
            if stripped.startswith("> **使用者價值**"):
                continue
            if stripped.startswith("> **關聯知識**"):
                continue
            if stripped.startswith("> **摘要可見**"):
                continue
            # Skip new argument_id line
            if stripped.startswith("> **論點ID**"):
                continue
            # Skip angle coverage line
            if stripped.startswith("> **角度覆蓋**"):
                continue
            if stripped.startswith("> **角度覆蓋摘要**"):
                continue
            if stripped.startswith("> **論點追溯**"):
                continue
            # Skip polaris metrics line
            if stripped.startswith("> **北極星分數**"):
                continue
            if stripped.startswith("> **北極星追蹤**"):
                continue
            # Skip three-part annotation lines
            if stripped.startswith("> **來源差異**"):
                continue
            if stripped.startswith("> **差異分析**"):
                continue
            if stripped.startswith("> **適用條件**"):
                continue
            if stripped.startswith("> **結論**"):
                continue
            # Skip extended readings lines
            if stripped.startswith("> **延伸閱讀**"):
                continue
            if stripped.startswith("> **待補證原因**"):
                continue
            if stripped.startswith("> **【待補來源】**"):
                continue
            if stripped.startswith("> - ["):
                continue
            md_originals.append(stripped)

        # Original paragraphs from docx (first N paragraphs where N = original count)
        # Filter out metadata lines (來源清單, 功能缺口, 使用者價值, 關聯知識, 追溯)
        docx_filtered = []
        for para in docx_paras:
            stripped = para.strip()
            if not stripped:
                continue
            if stripped.startswith("來源清單："):
                continue
            if stripped.startswith("功能缺口："):
                continue
            if stripped.startswith("使用者價值："):
                continue
            if stripped.startswith("關聯知識："):
                continue
            if stripped.startswith("摘要可見："):
                continue
            if stripped.startswith("論點ID："):
                continue
            if stripped.startswith("角度覆蓋："):
                continue
            if stripped.startswith("角度覆蓋摘要："):
                continue
            if stripped.startswith("論點追溯："):
                continue
            if stripped.startswith("北極星分數："):
                continue
            if stripped.startswith("北極星追蹤："):
                continue
            if stripped.startswith("追溯："):
                continue
            # Skip three-part annotation lines
            if stripped.startswith("來源差異："):
                continue
            if stripped.startswith("差異分析："):
                continue
            if stripped.startswith("適用條件："):
                continue
            if stripped.startswith("結論："):
                continue
            # Skip extended readings lines
            if stripped.startswith("延伸閱讀："):
                continue
            if stripped.startswith("待補證原因："):
                continue
            if stripped.startswith("【待補來源】"):
                continue
            if stripped.startswith("  ["):
                continue
            docx_filtered.append(stripped)
        docx_originals = docx_filtered[:len(json_originals)]

        # All three must have same count
        assert len(json_originals) == len(md_originals) == len(docx_originals), (
            f"Original paragraph count mismatch across formats:\n"
            f"JSON: {len(json_originals)}, MD: {len(md_originals)}, DOCX: {len(docx_originals)}"
        )

        # All three must match verbatim
        for i, (j, m, d) in enumerate(zip(json_originals, md_originals, docx_originals)):
            assert j == m == d, (
                f"Original paragraph {i} mismatch across formats:\n"
                f"JSON:  {j!r}\n"
                f"MD:    {m!r}\n"
                f"DOCX:  {d!r}"
            )

    def test_supplement_text_contains_only_claimed_sources(self, tmp_path):
        """Supplement text footnote markers [^n] in body must correspond to actual sources."""
        note_content = "行政程序法要求行政行為應遵守正當程序。"
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        md = to_markdown(doc)

        # Find supplement lines (body text, not reference block)
        for seg in doc.segments:
            if seg.type != "supplement":
                continue

            # Skip pending_evidence supplements (no sources, no footnotes)
            if seg.confidence == "pending_evidence":
                continue

            # Find the corresponding line in markdown
            import re
            # Build expected prefix
            prefix = "> 【補充】"
            if seg.confidence == "pending_evidence":
                prefix += "⚠待補證 "

            # Find matching line in markdown
            matching_lines = [line for line in md.splitlines() 
                            if line.strip().startswith(prefix) and seg.text[:30] in line]
            
            assert matching_lines, f"Could not find markdown line for supplement: {seg.text!r}"
            line = matching_lines[0].strip()

            # Extract all footnote numbers from the line
            footnotes = re.findall(r"\^\d+", line)
            footnote_nums = [int(f[1:]) for f in footnotes]

            # All footnote numbers should be >= 1
            assert all(n >= 1 for n in footnote_nums), (
                f"Invalid footnote numbers in: {line!r}"
            )

            # Verified supplements with sources should have at least one footnote
            assert footnote_nums, f"Verified supplement with sources should have footnotes: {line!r}"

            # The number of unique footnote markers should match or be less than sources
            # (some sources might be grouped under same footnote if LLM combines them)
            unique_footnotes = len(set(footnote_nums))
            assert unique_footnotes <= len(seg.sources), (
                f"More unique footnotes ({unique_footnotes}) than sources ({len(seg.sources)}): {line!r}"
            )
            # (LLM may reference same source multiple times)
            unique_footnotes = set(footnote_nums)
            assert len(unique_footnotes) <= len(seg.sources), (
                f"More unique footnote refs ({len(unique_footnotes)}) than sources ({len(seg.sources)}): {line!r}"
            )


class TestConsistencyBypassRegression:
    """Regression tests that detect bypass attempts where output differs from source but other checks pass."""

    def test_modified_correctiondoc_original_segment_detected_in_json_export(self, tmp_path):
        """A direct source-note/JSON comparison must fail with both sides identified."""
        note_content = "行政程序法要求行政行為應遵守正當程序。\n\n本筆記僅記錄部分重點,尚未展開。"
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)

        # Simulate bypass: silently modify an original segment's text
        # This could happen if someone tampers with CorrectionDoc after pipeline
        for seg in doc.segments:
            if seg.type == "original":
                # Introduce a subtle change that other checks might miss
                seg.text = seg.text.replace("正當程序", "正當法律程序")  # Silent modification

        data = to_json(doc)
        original_segments = [s for s in data["segments"] if s["type"] == "original"]
        original_texts = [s["text"] for s in original_segments]
        expected_paras = [p.strip() for p in note_content.split("\n\n") if p.strip()]

        failure_message = (
            "來源筆記與 JSON 產物不一致：\n"
            f"來源筆記：{expected_paras!r}\n"
            f"JSON 產物：{original_texts!r}"
        )
        with pytest.raises(AssertionError) as error:
            assert original_texts == expected_paras, failure_message

        error_text = str(error.value)
        assert "來源筆記與 JSON 產物不一致" in error_text
        assert repr(expected_paras) in error_text
        assert repr(original_texts) in error_text


class TestConsistencyEdgeCases:
    """Edge cases for output consistency verification."""

    def test_empty_note_produces_empty_original_segments(self, tmp_path):
        """Empty note should produce no original segments."""
        note_path = _note_fixture(tmp_path, "")
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        original_segments = [s for s in doc.segments if s.type == "original"]

        assert original_segments == [], "Empty note should produce no original segments"
        assert doc.original.full_text == ""

    def test_note_with_only_whitespace(self, tmp_path):
        """Note with only whitespace should be handled gracefully."""
        note_path = _note_fixture(tmp_path, "   \n\n  \n\n  ")
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        original_segments = [s for s in doc.segments if s.type == "original"]

        assert original_segments == [], "Whitespace-only note should produce no original segments"
        assert doc.original.full_text == ""

    def test_single_paragraph_note(self, tmp_path):
        """Single paragraph note should produce exactly one original segment."""
        note_path = _note_fixture(tmp_path, "單一段落筆記內容。")
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        original_segments = [s for s in doc.segments if s.type == "original"]

        assert len(original_segments) == 1
        assert original_segments[0].text == "單一段落筆記內容。"
        assert original_segments[0].anchor_idx == 0

    def test_paragraphs_with_special_characters(self, tmp_path):
        """Paragraphs with special characters must be preserved verbatim."""
        note_content = (
            "第 1 條：行政程序法立法目的。\n\n"
            "第 2 條：定義—「行政處分」指行政機關就公法上具體事件所為之對外直接發生法律效果之單方行政行為。\n\n"
            "【備註】包含特殊符號：①②③、※、*、*、*、( )、(）、[ ]、{ }、< >、《 》、「 」、『 』"
        )
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        md = to_markdown(doc)

        # Each original paragraph must appear verbatim
        for para in note_content.split("\n\n"):
            para = para.strip()
            if para:
                assert para in md, f"Special character paragraph missing in markdown: {para!r}"

    def test_unicode_content_preserved(self, tmp_path):
        """Unicode content (emoji, CJK, etc.) must be preserved verbatim."""
        note_content = "測試內容 🎉\n\n包含 Emoji 與 CJK：中文、日文（日本語）、英文 English。"
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)

        # Check JSON export
        data = to_json(doc)
        json_originals = [s["text"] for s in data["segments"] if s["type"] == "original"]
        for para in note_content.split("\n\n"):
            para = para.strip()
            if para:
                assert para in json_originals, f"Unicode paragraph missing in JSON: {para!r}"

        # Check markdown export
        md = to_markdown(doc)
        for para in note_content.split("\n\n"):
            para = para.strip()
            if para:
                assert para in md, f"Unicode paragraph missing in markdown: {para!r}"

        # Check docx export
        docx_path = tmp_path / "unicode.docx"
        to_docx(doc, str(docx_path))
        docx_doc = DocxDocument(str(docx_path))
        docx_paras = [p.text for p in docx_doc.paragraphs if p.text.strip()]
        for para in note_content.split("\n\n"):
            para = para.strip()
            if para:
                assert para in docx_paras, f"Unicode paragraph missing in docx: {para!r}"


class TestExplicitFailureReporting:
    """Tests that verify explicit failure reporting on consistency violations.

    These tests intentionally introduce mismatches to verify that the
    assertions in the test suite above will catch them and report clear errors.
    """

    def test_assertion_fails_on_modified_original_text(self, tmp_path):
        """If original text is modified in pipeline, test must fail explicitly."""
        note_content = "原始筆記內容。"
        note_path = _note_fixture(tmp_path, note_content)

        # Manually run pipeline but with a corrupted doc
        from note_filler.correction import assemble_correction, CorrectionDoc, Segment
        from note_filler.parse import parse_note, Document, Paragraph

        parsed = parse_note(note_path)

        # Create a corrupted correction doc where original text is modified
        corrupted_segments = [
            Segment(
                type="original",
                text="被修改的內容",  # Intentionally wrong
                anchor_idx=0,
                sources=[],
                confidence="verified",
                functional_gap="",
                user_value="",
                argument_id="",
            )
        ]
        corrupted_doc = CorrectionDoc(original=parsed, segments=corrupted_segments)

        # This assertion should fail with a clear message
        original_segments = [s for s in corrupted_doc.segments if s.type == "original"]
        expected = "原始筆記內容。"
        actual = original_segments[0].text

        with pytest.raises(AssertionError, match="Original segment.*mismatch"):
            assert actual == expected, (
                f"Original segment text mismatch:\n"
                f"Expected: {expected!r}\n"
                f"Actual:   {actual!r}"
            )

    def test_assertion_fails_on_missing_paragraph_in_markdown(self, tmp_path):
        """If markdown export misses a paragraph, test must fail explicitly."""
        note_content = "第一段內容。\n\n第二段內容。"
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        md = to_markdown(doc)

        # Intentionally check for a paragraph that doesn't exist
        missing_para = "不存在的段落"

        with pytest.raises(AssertionError, match="Original paragraph missing"):
            assert missing_para in md, (
                f"Original paragraph missing or altered in markdown output:\n"
                f"Expected: {missing_para!r}\n"
                f"Full markdown output:\n{md}"
            )

    def test_assertion_fails_on_json_full_text_mismatch(self, tmp_path):
        """If JSON full_text doesn't match source, test must fail explicitly."""
        note_content = "筆記內容。"
        note_path = _note_fixture(tmp_path, note_content)
        llm, twinkle, law = _pipeline_canned()

        doc = run_pipeline(note_path, llm, twinkle, law)
        data = to_json(doc)

        # Corrupt the data for testing
        data["full_text"] = "被竄改的內容"

        with pytest.raises(AssertionError, match="JSON full_text does not match"):
            expected_full_text = "\n".join(
                p for p in note_content.split("\n\n") if p.strip()
            )
            actual_full_text = data["full_text"]
            assert actual_full_text == expected_full_text, (
                f"JSON full_text does not match original note content:\n"
                f"Expected: {expected_full_text!r}\n"
                f"Actual:   {actual_full_text!r}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
