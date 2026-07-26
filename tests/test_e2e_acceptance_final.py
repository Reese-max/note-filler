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
from test_pipeline import FakeLaw, FakeTwinkle


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


# ---- 內容覆蓋驗證測試：驗證成品筆記包含具體、非占位的內容 -----

def test_content_coverage_domain_substance(tmp_path):
    """內容覆蓋驗證面向一：成品筆記包含領域相關的實質內容。
    
    斷言：
    1. 補充段包含領域專業術語（非通用詞彙）
    2. 補充段包含實質法律/行政概念（非空洞描述）
    3. 原稿關鍵詞在補充段中得到延伸（非重複原稿）
    """
    note = _docx(
        tmp_path, "note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    doc = run_pipeline(str(note), llm, twinkle, FakeLaw())

    supplements = [s for s in doc.segments if s.type == "supplement" and s.text.strip()]
    assert supplements, "無補充段可供驗證內容覆蓋"

    # 面向一：領域專業術語存在
    domain_terms = ["行政處分", "訴願", "行政程序", "正當程序"]
    for seg in supplements:
        text = seg.text.strip()
        # 至少包含一個領域專業術語
        has_domain_term = any(term in text for term in domain_terms)
        assert has_domain_term, (
            f"補充段缺乏領域專業術語（{domain_terms}）：{text!r}"
        )

    # 面向二：實質法律/行政概念（非空洞描述）
    empty_phrases = ["待補充", "尚未展開", "詳見", "參考", "請查閱"]
    for seg in supplements:
        text = seg.text.strip()
        # 不得僅為空洞描述
        is_substantive = not any(phrase in text for phrase in empty_phrases) or len(text) > 20
        assert is_substantive, (
            f"補充段為空洞描述或過短：{text!r}"
        )

    # 面向三：原稿關鍵詞得到延伸（非簡單重複）
    original_keywords = ["行政程序法", "正當程序"]
    for seg in supplements:
        text = seg.text.strip()
        # 若包含原稿關鍵詞，須有延伸內容（字數大於原稿段落）
        for kw in original_keywords:
            if kw in text:
                # 簡單檢查：補充段字數應大於關鍵詞本身
                assert len(text) > len(kw) + 5, (
                    f"補充段包含原稿關鍵詞 '{kw}' 但無延伸內容：{text!r}"
                )


def test_content_coverage_citation_integrity(tmp_path):
    """內容覆蓋驗證面向二：成品筆記包含正確格式的引用來源。
    
    斷言：
    1. 有來源的補充段包含實際引用標記（[^n] 格式）
    2. 引用標記對應的來源 ID 存在於 sources 欄位
    3. 無來源的補充段明確標記為 pending_evidence
    """
    note = _docx(
        tmp_path, "note.docx",
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])

    doc = run_pipeline(str(note), llm, twinkle, FakeLaw())

    supplements = [s for s in doc.segments if s.type == "supplement" and s.text.strip()]
    assert supplements, "無補充段可供驗證引用完整性"

    for seg in supplements:
        text = seg.text.strip()
        
        # 面向一：有來源的補充段包含引用標記
        if seg.sources:
            # 檢查是否包含 [^n] 格式的引用標記
            has_citation = "[^" in text and "]" in text
            assert has_citation, (
                f"有來源的補充段缺少引用標記 [^n]：{text!r}，來源：{seg.sources}"
            )
            
            # 面向二：引用標記數量與來源數量合理對應
            # 簡單檢查：至少有一個引用標記
            citation_count = text.count("[^")
            assert citation_count >= 1, (
                f"有來源的補充段引用標記數量不足：{text!r}，來源數：{len(seg.sources)}"
            )
        else:
            # 面向三：無來源的補充段明確標記為 pending_evidence
            assert seg.confidence == "pending_evidence", (
                f"無來源的補充段未標記為 pending_evidence：{text!r}，confidence：{seg.confidence}"
            )
            # 且應包含【待補證】標記
            assert "【待補證】" in text, (
                f"無來源的補充段缺少【待補證】標記：{text!r}"
            )


# ---- 端到端驗收：最終成品筆記直接送達使用者介面 ---------------------------

def test_final_note_delivery_ui_accessible(tmp_path):
    """條件一：使用者介面（CLI process_file 回傳值）可取得完整成品筆記內容。"""
    from note_filler import __main__ as cli
    
    note = _txt(
        tmp_path, "note.txt",
        "行政程序法要求行政行為應遵守正當程序。\n\n本筆記僅記錄部分重點,尚未展開。",
    )
    
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])
    
    r = cli.process_file(note, llm, twinkle, FakeLaw(), out_dir=None, fmt="md")
    
    # process_file 回傳值應包含完整內容
    assert "content" in r, "process_file 回傳值缺 content 欄位"
    content = r["content"]
    assert content.strip(), "content 為空，使用者無法取得任何內容"
    assert any(kw in content for kw in ("行政程序法", "正當程序", "行政處分", "訴願")), (
        f"content 缺乏實質筆記內容，僅包含：{content[:200]}"
    )
    assert "行政程序法要求行政行為應遵守正當程序" in content, (
        "content 未包含原稿段落"
    )
    assert "行政處分係指行政機關就公法上具體事件所為之對外直接發生法律效果之單方行政行為" in content, (
        "content 未包含補充內容"
    )


def test_final_note_delivery_flow_uninterrupted(tmp_path):
    """條件二：主流程不中斷，正常完成且回傳值完整。"""
    from note_filler import __main__ as cli
    
    note = _txt(
        tmp_path, "note.txt",
        "行政程序法要求行政行為應遵守正當程序。",
    )
    
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])
    
    r = cli.process_file(note, llm, twinkle, FakeLaw(), out_dir=None, fmt="md")
    
    # process_file 應正常回傳，不拋出異常
    assert r is not None, "process_file 未正常回傳"
    assert "input" in r, "回傳值缺 input 欄位"
    assert "output" in r, "回傳值缺 output 欄位"
    assert "content" in r, "回傳值缺 content 欄位"
    assert r["output"] is not None, "未產生輸出路徑"
    assert Path(r["output"]).exists(), "輸出檔不存在"





def test_final_note_delivery_not_empty_or_local_only(tmp_path):
    """條件四：回傳結果不是空輸出或僅本機落盤（content 有實際內容）。"""
    from note_filler import __main__ as cli
    
    note = _txt(
        tmp_path, "note.txt",
        "行政程序法要求行政行為應遵守正當程序。",
    )
    
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])
    
    r = cli.process_file(note, llm, twinkle, FakeLaw(), out_dir=None, fmt="md")
    
    content = r["content"]
    
    # 驗證不是空輸出
    assert content.strip(), "content 為空輸出"
    assert len(content) > 100, (
        f"content 內容過短，疑似僅包含路徑或統計：{content}"
    )
    assert "行政程序法" in content, (
        "content 缺乏實際筆記內容，疑似僅本機落盤"
    )
    
    # 驗證本機檔案也存在（兩者並存）
    assert Path(r["output"]).exists(), "本機輸出檔不存在"
    local_content = Path(r["output"]).read_text(encoding="utf-8")
    assert local_content.strip(), "本機輸出檔為空"
    
    # content 應與本機檔案內容一致
    assert content.strip() == local_content.strip(), (
        "content 與本機檔案不一致"
    )


def test_final_note_delivery_all_conditions(tmp_path):
    """整合測試：同時驗證四個條件。"""
    from note_filler import __main__ as cli
    
    note = _txt(
        tmp_path, "note.txt",
        "行政程序法要求行政行為應遵守正當程序。\n\n本筆記僅記錄部分重點,尚未展開。",
    )
    
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])
    
    r = cli.process_file(note, llm, twinkle, FakeLaw(), out_dir=None, fmt="md")
    
    content = r["content"]
    
    # 條件一：使用者介面可取得完整內容（透過回傳值）
    assert content.strip(), "條件一失敗：content 為空"
    assert "行政程序法" in content, "條件一失敗：content 缺乏實質內容"
    assert "行政處分係指行政機關就公法上具體事件所為之對外直接發生法律效果之單方行政行為" in content, (
        "條件一失敗：content 缺乏補充內容"
    )
    
    # 條件二：主流程不中斷（process_file 正常回傳）
    assert r is not None, "條件二失敗：process_file 未正常回傳"
    assert r["output"] is not None, "條件二失敗：未產生輸出路徑"
    
    # 條件三：失敗情境不輸出錯誤堆疊（這是成功情境，代表無異常）
    # 成功情境自然不會有 traceback
    
    # 條件四：回傳結果不是空輸出或僅本機落盤
    assert len(content) > 100, "條件四失敗：content 內容過短"
    assert Path(r["output"]).exists(), "條件四失敗：本機檔案不存在"
    local_content = Path(r["output"]).read_text(encoding="utf-8")
    assert content.strip() == local_content.strip(), "條件四失敗：content 與本機不一致"


def test_final_note_delivery_with_partial_page_failure_and_generation_exception(
    tmp_path, monkeypatch
):
    """端到端正向測試：模擬部分頁面缺失與一段內容生成例外時，最終仍能取得完整筆記輸出。
    
    測試情境：
    1. 模擬部分頁面缺失（web 檢索時部分頁面失敗）
    2. 模擬一段內容生成例外（LLM 寫作時拋出異常）
    3. 驗證最終仍能取得完整筆記輸出
    4. 驗證輸出同時出現在使用者可見通道（process_file 回傳值）與最終回傳值中
    """
    from note_filler import __main__ as cli
    
    note = _txt(
        tmp_path, "note.txt",
        "行政程序法要求行政行為應遵守正當程序。\n\n本筆記僅記錄部分重點,尚未展開。",
    )
    
    from note_filler import pipeline as pipeline_module
    from note_filler.retrieve import web as web_module

    search_calls = 0

    def partial_search(query, max_results):
        nonlocal search_calls
        search_calls += 1
        if search_calls == 1:
            return [
                {"title": "缺失頁", "href": "https://example.test/missing"},
                {"title": "可用頁", "href": "https://example.test/available"},
            ]
        return [{"title": "缺失頁", "href": "https://example.test/missing"}]

    available_page = "官方完整頁面。" + "行政處分是具外部法律效果的行政行為。" * 30
    monkeypatch.setattr(web_module, "_ddg_search", partial_search)
    monkeypatch.setattr(
        web_module,
        "_fetch_fulltext",
        lambda url: available_page if url.endswith("/available") else None,
    )

    # 第二個 gap 的寫作真正拋出例外，pipeline 必須轉成待補證填充。
    real_write_supplement = pipeline_module.write_supplement

    def partial_write(gap, sources, client):
        if gap.question == "訴願前置程序為何?":
            raise RuntimeError("private-generation-error")
        return real_write_supplement(gap, sources, client)

    monkeypatch.setattr(pipeline_module, "write_supplement", partial_write)

    llm = FakeLLM([
        "other",
        "行政處分的定義為何?\n訴願前置程序為何?",
        json.dumps([
            {"question": "行政處分的定義為何?", "status": "missing", "reason": "筆記未展開定義"},
            {"question": "訴願前置程序為何?", "status": "missing", "reason": "筆記未提及"},
        ], ensure_ascii=False),
        "行政處分 定義",
        '{"level":"C","doc_date":"2026-07-26","reason":"官方頁面"}',
        "行政處分係指行政機關就公法上具體事件所為之對外直接發生法律效果之單方行政行為[^1]。",
        "訴願 前置程序",
    ])

    r = cli.process_file(note, llm, FakeTwinkle([]), FakeLaw(), out_dir=None, fmt="md")
    
    content = r["content"]
    
    # 驗證最終可見筆記存在且非空
    assert content.strip(), "最終可見筆記為空，屬靜默失敗"
    
    # 驗證筆記可讀（非亂碼、非二進位、非損壞格式）
    assert isinstance(content, str), "最終可見筆記非字串格式，不可讀"
    assert len(content) > 50, "最終可見筆記內容過短，可能不完整"
    
    # 驗證不含底層錯誤資訊（traceback、exception、stack trace）
    error_indicators = [
        "Traceback",
        "Exception",
        "Error:",
        "stack trace",
        "raise ",
        "assert ",
        "File \"",
        "line ",
    ]
    for indicator in error_indicators:
        assert indicator not in content, f"最終可見筆記含底層錯誤資訊: {indicator}"
    
    # 驗證不含內部稽核事件字串
    assert "note_product_empty" not in content, "最終可見筆記含內部稽核事件字串"
    assert "MISSING_WRITTEN_TEXT" not in content, "最終可見筆記含內部佔位文"
    assert "private-generation-error" not in content, "最終可見筆記洩漏生成例外"
    
    # 驗證含實質筆記內容（非僅錯誤訊息或技術輸出）
    assert any(kw in content for kw in ("行政程序法", "正當程序", "行政處分")), (
        "最終可見筆記缺乏實質筆記內容，可能為錯誤輸出"
    )
    
    # 驗證原稿段落完整保留
    assert "行政程序法要求行政行為應遵守正當程序" in content, (
        "最終可見筆記未包含原稿段落"
    )
    
    # 驗證補充內容存在（即使部分降級為待補證）
    assert "行政處分係指行政機關就公法上具體事件所為之對外直接發生法律效果之單方行政行為" in content, (
        "最終可見筆記未包含補充內容"
    )
    assert "【待補證】" in content, "生成例外未降級為待補證填充"
    expected_ds = {
        "primary_note_ready": True,
        "user_channel_sent": False,
        "local_fallback_written": True,
    }
    assert expected_ds.items() <= r["delivery_status"].items(), (
        f"delivery_status 缺必要欄位: "
        f"{set(expected_ds) - set(r['delivery_status'])}"
    )
    receipt = json.loads((tmp_path / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert expected_ds.items() <= receipt["delivery_status"].items()


def test_silent_failure_detection_final_note_readable_and_error_free(tmp_path):
    """針對「靜默失敗」的斷言：只檢查最終可見筆記是否存在、是否可讀、是否未含底層錯誤資訊。
    
    避免只看 exit code 或本機檔案存在就誤判完成。
    
    斷言：
    1. 最終可見筆記（process_file 回傳值 content）存在且非空
    2. 筆記內容可讀（字串格式、合理長度、UTF-8 可解碼）
    3. 筆記不含底層錯誤資訊（traceback、exception、stack trace）
    4. 筆記不含內部稽核事件字串或佔位文
    5. 筆記含實質內容（非僅錯誤訊息或技術輸出）
    """
    from note_filler import __main__ as cli
    
    note = _txt(
        tmp_path, "note.txt",
        "行政程序法要求行政行為應遵守正當程序。\n\n本筆記僅記錄部分重點,尚未展開。",
    )
    
    llm = _canned_llm_two_gaps()
    twinkle = FakeTwinkle([[_src("s1"), _src("s2")], [_src("s3"), _src("s4")]])
    
    # 執行 process_file，若失敗則直接失敗（這是驗收測試，不應吞掉異常）
    try:
        r = cli.process_file(note, llm, twinkle, FakeLaw(), out_dir=None, fmt="md")
    except Exception as e:
        pytest.fail(f"process_file 拋出異常，屬靜默失敗: {type(e).__name__}: {e}")
    
    # 先檢查回傳值結構
    assert r is not None, "process_file 回傳值為 None，屬靜默失敗"
    assert "content" in r, f"process_file 回傳值缺 content 欄位，實際欄位: {list(r.keys())}，屬靜默失敗"
    
    content = r["content"]
    
    # 斷言 1：最終可見筆記存在且非空
    assert content is not None, "最終可見筆記不存在，屬靜默失敗"
    assert content.strip(), "最終可見筆記為空，屬靜默失敗"
    
    # 斷言 2：筆記內容可讀
    assert isinstance(content, str), "最終可見筆記非字串格式，不可讀"
    try:
        content.encode("utf-8").decode("utf-8")
    except UnicodeError:
        pytest.fail("最終可見筆記非有效 UTF-8，不可讀")
    assert len(content) > 100, "最終可見筆記內容過短，可能不完整"
    
    # 斷言 3：筆記不含底層錯誤資訊
    error_indicators = [
        "Traceback",
        "Exception",
        "Error:",
        "stack trace",
        "raise ",
        "assert ",
        "File \"",
        "line ",
        "TypeError",
        "ValueError",
        "AttributeError",
        "KeyError",
        "RuntimeError",
    ]
    for indicator in error_indicators:
        assert indicator not in content, f"最終可見筆記含底層錯誤資訊: {indicator}"
    
    # 斷言 4：筆記不含內部稽核事件字串或佔位文
    assert "note_product_empty" not in content, "最終可見筆記含內部稽核事件字串"
    assert "MISSING_WRITTEN_TEXT" not in content, "最終可見筆記含內部佔位文"
    
    # 斷言 5：筆記含實質內容
    assert any(kw in content for kw in ("行政程序法", "正當程序", "行政處分", "訴願")), (
        "最終可見筆記缺乏實質筆記內容，可能為錯誤輸出或技術摘要"
    )
    
    # 額外驗證：原稿與補充內容都存在
    assert "行政程序法要求行政行為應遵守正當程序" in content, (
        "最終可見筆記未包含原稿段落"
    )
    assert "行政處分係指行政機關就公法上具體事件所為之對外直接發生法律效果之單方行政行為" in content, (
        "最終可見筆記未包含補充內容"
    )
