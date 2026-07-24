"""端到端驗收測試：直接呼叫主流程並斷言實際筆記產出。

鎖定：
  1. run_pipeline 完成後 segments 含非空白 original/supplement 實際筆記
  2. to_markdown / to_json 產出非空、非稽核報告、非佔位內容
  3. process_file 寫出的磁碟檔案存在且含有效筆記內容
  4. 輸出不含內部稽核事件字串或 MISSING_WRITTEN_TEXT 佔位文

離線 FakeLLM + FakeTwinkle；非 integration。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from note_filler.export import to_json, to_markdown
from note_filler.llm import FakeLLM
from note_filler.pipeline import run_pipeline
from note_filler.retrieve.models import Source
from tests.test_pipeline import FakeLaw, FakeTwinkle


# ---- fixtures ----------------------------------------------------------------

def _docx(tmp_path: Path, name: str, *paragraphs: str) -> Path:
    p = tmp_path / name
    d = DocxDocument()
    for para in paragraphs:
        d.add_paragraph(para)
    d.save(str(p))
    return p


def _txt(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _src(sid: str = "s1", level: str = "A") -> Source:
    return Source(
        id=sid,
        title=f"來源{sid}",
        url=f"https://example.gov.tw/{sid}",
        level=level,
        content=f"官方結構化記錄全文 {sid}……",
        fetched_date="2026-07-15",
        doc_date="2026-01-01",
        distance=0.5,
    )


def _canned_llm_two_gaps():
    """兩個缺口的 canned LLM：domain=law, questions×1, gaps×1, gap1(keyword+writer), gap2(keyword+writer)。"""
    return FakeLLM([
        "law",
        "行政處分的定義為何?\n訴願前置程序為何?",
        json.dumps([
            {"question": "行政處分的定義為何?", "status": "missing", "reason": "筆記未展開定義"},
            {"question": "訴願前置程序為何?", "status": "missing", "reason": "筆記未提及"},
        ], ensure_ascii=False),
        '{"keyword": "行政處分", "law_name": "行政程序法"}',
        "行政處分係指行政機關就公法上具體事件所為之對外直接發生法律效果之單方行政行為[^1]。",
        '{"keyword": "訴願", "law_name": "訴願法"}',
        "人民對違法或不當行政處分應先經訴願程序始得提起行政訴訟[^2]。",
    ])


def _canned_llm_one_gap_no_source():
    """單缺口、無來源 → 補充為 pending_evidence。"""
    return FakeLLM([
        "admin",
        "正當程序的要件為何?",
        json.dumps([
            {"question": "正當程序的要件為何?", "status": "missing", "reason": "筆記未展開"},
        ], ensure_ascii=False),
        '{"keyword": "正當程序", "law_name": null}',
        "【待補證】此問題缺乏可用來源,尚待補充。",
    ])


# ---- 測試：直接呼叫主流程、斷言實際筆記存在且非空白非佔位 ---------------

def test_pipeline_produces_non_empty_note_segments(tmp_path):
    """直接呼叫 run_pipeline，斷言產出的 segments 含非空白實際筆記內容。"""
    note = _docx(
        tmp_path, "note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    doc = run_pipeline(str(note), llm, twinkle, FakeLaw())

    # 至少有 original 段（原稿保留）
    originals = [s for s in doc.segments if s.type == "original" and s.text.strip()]
    assert originals, "主流程未產出任何非空白 original 段——實際筆記不存在"

    # 至少有 supplement 段（補充成品）
    supplements = [s for s in doc.segments if s.type == "supplement" and s.text.strip()]
    assert supplements, "主流程未產出任何非空白 supplement 段——實際筆記不存在"


def test_pipeline_note_not_placeholder_or_audit(tmp_path):
    """直接呼叫 run_pipeline，斷言補充筆記不是佔位文或稽核事件字串。"""
    note = _docx(
        tmp_path, "note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    doc = run_pipeline(str(note), llm, twinkle, FakeLaw())

    for seg in doc.segments:
        if seg.type != "supplement":
            continue
        text = seg.text.strip()
        assert text, f"supplement 段空白：{seg!r}"

        # 不得是內部佔位文（MISSING_WRITTEN_TEXT 以【待補證】開頭 + 內部標記）
        assert "MISSING_WRITTEN_TEXT" not in text, (
            f"supplement 含內部佔位文 MISSING_WRITTEN_TEXT: {text!r}"
        )

        # 不得是稽核事件字串
        assert "note_product_empty" not in text, (
            f"supplement 含稽核事件字串: {text!r}"
        )

        # 不得是 JSON 傾印或 code block
        assert not text.lstrip().startswith("{"), (
            f"supplement 為 JSON 格式而非實際筆記: {text!r}"
        )
        assert not text.lstrip().startswith("```"), (
            f"supplement 為 code block 而非實際筆記: {text!r}"
        )


def test_markdown_output_is_real_notes_not_report(tmp_path):
    """呼叫 run_pipeline + to_markdown，斷言輸出為人類可讀筆記而非稽核報告。"""
    note = _docx(
        tmp_path, "note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    doc = run_pipeline(str(note), llm, twinkle, FakeLaw())
    md = to_markdown(doc)

    # 非空
    assert isinstance(md, str) and md.strip(), "to_markdown 產出空字串"

    # 不是稽核報告：不以 JSON / code block 開頭
    assert not md.lstrip().startswith("{"), "markdown 以 JSON 開頭，疑似稽核報告"
    assert not md.lstrip().startswith("```"), "markdown 以 code block 開頭，疑似稽核報告"

    # 不含內部稽核事件字串
    assert "note_product_empty" not in md, "markdown 含稽核事件字串"
    assert "MISSING_WRITTEN_TEXT" not in md, "markdown 含內部佔位文"

    # 含實質筆記領域內容（原稿關鍵字）
    assert any(kw in md for kw in ("行政程序法", "正當程序", "行政處分", "訴願")), (
        "markdown 缺乏實質筆記領域內容"
    )

    # 原稿段落完整輸出
    for p in doc.original.paragraphs:
        assert p.text in md, f"原稿段落未出現在 markdown: {p.text!r}"


def test_json_output_is_real_notes_not_report(tmp_path):
    """呼叫 run_pipeline + to_json，斷言 JSON 產出含實際筆記段。"""
    note = _docx(
        tmp_path, "note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    doc = run_pipeline(str(note), llm, twinkle, FakeLaw())
    data = to_json(doc)

    assert isinstance(data, dict), "to_json 未回傳 dict"
    assert "segments" in data, "JSON 缺 segments 欄位"

    note_segments = [
        s for s in data["segments"]
        if s["type"] in ("original", "supplement") and (s.get("text") or "").strip()
    ]
    assert note_segments, "JSON 產出無任何非空白 actual note segments"

    # segments 不得含內部佔位文
    for seg in data["segments"]:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        assert "MISSING_WRITTEN_TEXT" not in text, (
            f"JSON segment 含內部佔位文: {seg!r}"
        )
        assert "note_product_empty" not in text, (
            f"JSON segment 含稽核事件字串: {seg!r}"
        )


def test_pipeline_note_has_real_substance_not_just_titles(tmp_path):
    """斷言補充筆記有實質延伸論點（>= 10 字），非僅標題或空白架構。"""
    note = _docx(
        tmp_path, "note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    doc = run_pipeline(str(note), llm, twinkle, FakeLaw())

    supplements = [s for s in doc.segments if s.type == "supplement" and s.text.strip()]
    assert supplements, "無補充段"

    # 至少一個補充段有實質延伸論點（>= 10 字、非僅【待補證】）
    substantive = [
        s for s in supplements
        if len(s.text.strip()) >= 10 and not s.text.strip().startswith("【待補證】")
    ]
    assert substantive, "所有補充段皆為佔位文或過短，無實質延伸論點"

    # 實質補充段須掛實際來源
    for seg in substantive:
        assert seg.sources, f"實質補充段缺少實際引用來源: {seg.text!r}"


def test_cli_process_file_writes_note_to_disk(tmp_path):
    """透過 __main__.process_file 呼叫主流程，斷言磁碟產出存在且含有效內容。"""
    from note_filler import __main__ as cli

    note = _docx(
        tmp_path, "note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    out_dir = tmp_path / "output"
    r = cli.process_file(note, llm, twinkle, FakeLaw(), out_dir=out_dir, fmt="md")

    # process_file 回傳值確認
    assert r["input"] == str(note)
    dest = Path(r["output"])
    assert dest.exists(), f"訂正稿檔案未寫入磁碟: {dest}"
    assert dest.stat().st_size > 0, f"訂正稿檔案為空: {dest}"

    # 磁碟檔案內容驗證
    body = dest.read_text(encoding="utf-8")
    assert body.strip(), "訂正稿檔案內容空白"

    # 不是稽核報告 / 佔位文
    assert not body.lstrip().startswith("{"), "訂正稿為 JSON 格式，疑似稽核報告"
    assert "note_product_empty" not in body, "訂正稿含稽核事件字串"
    assert "MISSING_WRITTEN_TEXT" not in body, "訂正稿含內部佔位文"

    # 含實質筆記內容
    assert any(kw in body for kw in ("行政程序法", "正當程序", "行政處分", "訴願")), (
        "訂正稿缺乏實質筆記領域內容"
    )


def test_cli_process_file_json_format_writes_valid_note(tmp_path):
    """process_file 以 JSON 格式寫出，斷言檔案含有效筆記 JSON。"""
    from note_filler import __main__ as cli

    note = _docx(
        tmp_path, "note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    out_dir = tmp_path / "output"
    r = cli.process_file(note, llm, twinkle, FakeLaw(), out_dir=out_dir, fmt="json")

    dest = Path(r["output"])
    assert dest.exists(), f"JSON 訂正稿未寫入: {dest}"

    data = json.loads(dest.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "JSON 訂正稿非 dict"
    assert "segments" in data, "JSON 訂正稿缺 segments"

    note_segments = [
        s for s in data["segments"]
        if s["type"] in ("original", "supplement") and (s.get("text") or "").strip()
    ]
    assert note_segments, "JSON 訂正稿無任何非空白 actual note segments"


def test_pipeline_with_txt_input_produces_non_empty_notes(tmp_path):
    """以 .txt 筆記檔觸發主流程，斷言產出非空白實際筆記。"""
    note = _txt(
        tmp_path, "note.txt",
        "行政法重點筆記\n\n行政程序法第92條定義行政處分。\n\n救濟途徑包括訴願與行政訴訟。",
    )
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    doc = run_pipeline(str(note), llm, twinkle, FakeLaw())

    # 實際筆記存在
    originals = [s for s in doc.segments if s.type == "original" and s.text.strip()]
    supplements = [s for s in doc.segments if s.type == "supplement" and s.text.strip()]
    assert originals, ".txt 輸入未產出 original 段"
    assert supplements, ".txt 輸入未產出 supplement 段"

    # 非佔位
    for seg in supplements:
        assert "MISSING_WRITTEN_TEXT" not in seg.text, (
            f"supplement 含內部佔位文: {seg.text!r}"
        )


def test_pipeline_multiple_files_independently_produce_notes(tmp_path):
    """批次處理兩份筆記，各自獨立產出非空白實際筆記。"""
    from note_filler import __main__ as cli

    note_a = _docx(
        tmp_path, "note_a.docx",
        "行政程序法要求行政行為應遵守正當程序。",
    )
    note_b = _docx(
        tmp_path, "note_b.docx",
        "民事訴訟法規定當事人有陳述意見之權。",
    )

    # 每份筆記各自用獨立的 FakeLLM（避免共用時 responses 被耗盡）
    llm_a = _canned_llm_two_gaps()
    llm_b = _canned_llm_two_gaps()
    twinkle_a = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])
    twinkle_b = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    out_dir = tmp_path / "output"
    r_a = cli.process_file(note_a, llm_a, twinkle_a, FakeLaw(), out_dir=out_dir, fmt="md")
    r_b = cli.process_file(note_b, llm_b, twinkle_b, FakeLaw(), out_dir=out_dir, fmt="md")

    for label, r in [("note_a", r_a), ("note_b", r_b)]:
        dest = Path(r["output"])
        assert dest.exists(), f"{label}: 訂正稿未寫入"
        body = dest.read_text(encoding="utf-8")
        assert body.strip(), f"{label}: 訂正稿空白"
        assert "note_product_empty" not in body, f"{label}: 含稽核事件字串"
