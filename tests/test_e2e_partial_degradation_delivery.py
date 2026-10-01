"""端到端驗收：部分頁面缺失 + 一段內容生成失敗時的降級交付。

模擬情境：
  1. 多個 gap 中，部分 gap 檢索不到頁面（partial page missing）
  2. 其中一個 gap 的 write_supplement 拋出例外（content generation failure）
  3. 驗證：
     a. 使用者可見通道（process_file 回傳值 content）仍收到完整可讀筆記
     b. 回傳值非空
     c. delivery_status.segment_delivery_details 明確標示哪些片段是降級補齊
        （degraded=True）而非中斷流程
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from note_filler import __main__ as cli
from note_filler.llm import FakeLLM
from note_filler.pipeline import run_pipeline
from note_filler.retrieve.models import Source
from tests.test_pipeline import FakeLaw, FakeTwinkle


# ---- helpers ----------------------------------------------------------------

def _make_note(tmp_path: Path, *paragraphs: str) -> Path:
    p = tmp_path / "note.docx"
    d = DocxDocument()
    for para in paragraphs:
        d.add_paragraph(para)
    d.save(str(p))
    return p


def _src(sid: str, level: str = "A") -> Source:
    return Source(
        id=sid,
        title=f"來源{sid}",
        url=f"https://example.gov.tw/{sid}",
        level=level,
        content=f"官方結構化記錄全文 {sid}",
        fetched_date="2026-07-25",
        doc_date="2026-01-01",
        distance=0.5,
    )


def _canned_llm_three_gaps_one_fails():
    """三個缺口的 canned LLM：gap1/gap2 正常，gap3 寫作拋例外。

    FakeLLM 呼叫序：
      0: detect_domain
      1: generate_questions（三個問題）
      2: detect_gaps（三個 missing）
      3: gap1 keyword extraction
      4: gap1 writer（正常）
      5: gap2 keyword extraction
      6: gap2 writer（正常）
      7: gap3 keyword extraction
      8: gap3 writer → Exception
    """
    return FakeLLM([
        "law",
        "行政處分的定義為何?\n訴願前置程序為何?\n法規命令的效力為何?",
        json.dumps([
            {"question": "行政處分的定義為何?", "status": "missing", "reason": "未展開定義"},
            {"question": "訴願前置程序為何?", "status": "missing", "reason": "未提及"},
            {"question": "法規命令的效力為何?", "status": "missing", "reason": "未展開"},
        ], ensure_ascii=False),
        '{"keyword": "行政處分", "law_name": "行政程序法"}',
        "行政處分係指行政機關就公法上具體事件所為之對外直接發生法律效果之單方行政行為[^1]。",
        '{"keyword": "訴願", "law_name": "訴願法"}',
        "人民對違法或不當行政處分應先經訴願程序始得提起行政訴訟[^2]。",
        '{"keyword": "法規命令", "law_name": null}',
        RuntimeError("private-generation-error"),
    ])


def _partial_twinkle():
    """gap1/gap2 有來源，gap3 檢索失敗（回空）。"""
    return FakeTwinkle([
        [_src("s1", "A"), _src("s2", "B")],   # gap1
        [_src("s3", "A"), _src("s4", "B")],   # gap2
        [],                                     # gap3: partial page missing
    ])


# ---- core test --------------------------------------------------------------

def test_partial_degradation_e2e_delivery_status(tmp_path, monkeypatch):
    """模擬部分頁面缺失 + 一段內容生成失敗，斷言：
      1. 使用者可見通道（content）仍收到完整可讀筆記
      2. 回傳值非空
      3. delivery_status.segment_delivery_details 明確標示降級片段
    """
    from note_filler import pipeline as pipeline_module

    note = _make_note(
        tmp_path,
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )

    # monkeypatch write_supplement：gap3 的問題會拋例外 → pipeline 內部 catch 轉待補證
    real_write = pipeline_module.write_supplement

    def _partial_write(gap, sources, client):
        if "法規命令" in gap.question:
            raise RuntimeError("private-generation-error")
        return real_write(gap, sources, client)

    monkeypatch.setattr(pipeline_module, "write_supplement", _partial_write)

    llm = _canned_llm_three_gaps_one_fails()
    twinkle = _partial_twinkle()

    r = cli.process_file(note, llm, twinkle, FakeLaw(), out_dir=None, fmt="md")

    # ---- 斷言 1：回傳值非空、content 可讀 ----
    assert r is not None, "process_file 回傳值為 None"
    content = r.get("content", "")
    assert isinstance(content, str), f"content 非字串: {type(content)}"
    assert content.strip(), "content 為空"
    assert len(content) > 100, f"content 過短: {len(content)}"

    # ---- 斷言 2：使用者可見通道含完整可讀筆記 ----
    # 原稿逐字保留
    assert "行政程序法要求行政行為應遵守正當程序" in content, "原稿段落未保留"
    # 正常 gap 的補充存在
    assert "行政處分" in content, "gap1 補充缺失"
    assert "訴願" in content, "gap2 補充缺失"
    # 降級 gap 以【待補證】呈現（流程未中斷）
    assert "【待補證】" in content, "降級 gap 未以待補證呈現"

    # 不含底層錯誤
    for bad in ("Traceback", "private-generation-error", "provider error"):
        assert bad not in content, f"content 洩漏底層錯誤: {bad}"

    # ---- 斷言 3：delivery_status 含 segment_delivery_details ----
    ds = r.get("delivery_status")
    assert isinstance(ds, dict), f"delivery_status 非 dict: {type(ds)}"
    assert ds.get("primary_note_ready"), "primary_note_ready 應為 True"
    assert ds.get("local_fallback_written"), "local_fallback_written 應為 True"

    details = ds.get("segment_delivery_details")
    assert isinstance(details, list), (
        f"segment_delivery_details 非 list: {type(details)}"
    )
    assert len(details) >= 2, (
        f"segment_delivery_details 至少含 original+supplement, 實際 {len(details)}"
    )

    # ---- 斷言 4：segment_delivery_details 標示降級片段 ----
    supplement_details = [d for d in details if d.get("question", "").startswith("argument:")]
    assert len(supplement_details) == 3, (
        f"應有 3 個 supplement segment detail, 實際 {len(supplement_details)}"
    )

    degraded = [d for d in supplement_details if d.get("degraded")]
    non_degraded = [d for d in supplement_details if not d.get("degraded")]

    # 至少一個降級（gap3: 生成失敗 + 無來源）
    assert len(degraded) >= 1, (
        f"應至少一個 degraded segment, 實際全部 non-degraded: {supplement_details}"
    )
    # 至少一個非降級（gap1/gap2: 正常生成且有來源）
    assert len(non_degraded) >= 1, (
        f"應至少一個 non-degraded segment, 實際全部 degraded: {supplement_details}"
    )

    # 降級 segment 的 confidence 為 pending_evidence
    for d in degraded:
        assert d.get("confidence") == "pending_evidence", (
            f"degraded segment confidence 非 pending_evidence: {d}"
        )

    # 非降級 segment 的 confidence 為 verified 或非 pending_evidence
    for d in non_degraded:
        assert d.get("confidence") != "pending_evidence" or d.get("has_sources"), (
            f"non-degraded segment 應有 sources 或非 pending: {d}"
        )

    # ---- 斷言 5：manifest 的 delivery_status 也含 segment_delivery_details ----
    manifest_path = Path(r["output"]).parent / cli.MANIFEST_NAME
    assert manifest_path.exists(), "delivery_manifest.json 不存在"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_ds = manifest.get("delivery_status", {})
    assert "segment_delivery_details" in manifest_ds, (
        "manifest delivery_status 缺 segment_delivery_details"
    )
    manifest_details = manifest_ds["segment_delivery_details"]
    assert len(manifest_details) >= 2, (
        f"manifest segment_delivery_details 過少: {len(manifest_details)}"
    )
    # manifest 也應有降級標記
    manifest_degraded = [d for d in manifest_details if d.get("degraded")]
    assert len(manifest_degraded) >= 1, (
        "manifest segment_delivery_details 缺 degraded segment"
    )


def test_degradation_delivery_status_fields_integrity(tmp_path, monkeypatch):
    """驗證 segment_delivery_details 每筆含必要欄位，且降級/非降級邏輯一致。"""
    from note_filler import pipeline as pipeline_module

    note = _make_note(
        tmp_path,
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )

    real_write = pipeline_module.write_supplement

    def _partial_write(gap, sources, client):
        if "法規命令" in gap.question:
            raise RuntimeError("gen-error")
        return real_write(gap, sources, client)

    monkeypatch.setattr(pipeline_module, "write_supplement", _partial_write)

    llm = _canned_llm_three_gaps_one_fails()
    twinkle = _partial_twinkle()

    r = cli.process_file(note, llm, twinkle, FakeLaw(), out_dir=None, fmt="md")

    details = r["delivery_status"]["segment_delivery_details"]
    required_keys = {"question", "confidence", "has_sources", "degraded"}

    for d in details:
        assert required_keys.issubset(d.keys()), (
            f"segment_delivery_detail 缺欄位: {required_keys - d.keys()} in {d}"
        )
        # degraded=True → confidence 必為 pending_evidence
        if d["degraded"]:
            assert d["confidence"] == "pending_evidence", (
                f"degraded segment confidence 非 pending: {d}"
            )
        # has_sources=True 且 confidence=verified → non-degraded
        if d["has_sources"] and d["confidence"] == "verified":
            assert not d["degraded"], (
                f"verified+has_sources 不應 degraded: {d}"
            )


def test_pipeline_direct_partial_degradation_segments(tmp_path, monkeypatch):
    """直接呼叫 run_pipeline（不經過 CLI），驗證 segments 本身的降級狀態。"""
    from note_filler import pipeline as pipeline_module

    note = _make_note(
        tmp_path,
        "行政程序法要求行政行為應遵守正當程序。",
        "本筆記僅記錄部分重點,尚未展開。",
    )

    real_write = pipeline_module.write_supplement

    def _partial_write(gap, sources, client):
        if "法規命令" in gap.question:
            raise RuntimeError("gen-error")
        return real_write(gap, sources, client)

    monkeypatch.setattr(pipeline_module, "write_supplement", _partial_write)

    llm = _canned_llm_three_gaps_one_fails()
    twinkle = _partial_twinkle()

    doc = run_pipeline(str(note), llm, twinkle, FakeLaw())

    supplements = [s for s in doc.segments if s.type == "supplement"]
    assert len(supplements) == 3, f"應有 3 個 supplement, 實際 {len(supplements)}"

    # 至少一個 pending_evidence（降級）
    pending = [s for s in supplements if s.confidence == "pending_evidence"]
    assert len(pending) >= 1, "應至少一個 pending_evidence segment"

    # 至少一個有 sources 的 segment（非降級）
    sourced = [s for s in supplements if s.sources]
    assert len(sourced) >= 1, "應至少一個有 sources 的 segment"

    # 原稿逐字保留
    originals = [s for s in doc.segments if s.type == "original"]
    assert len(originals) == 2, f"應有 2 個 original, 實際 {len(originals)}"
    assert originals[0].text == "行政程序法要求行政行為應遵守正當程序。"
    assert originals[1].text == "本筆記僅記錄部分重點,尚未展開。"
