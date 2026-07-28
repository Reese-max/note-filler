"""回歸：「吞錯仍全綠」路徑——write_supplement 例外被 pipeline 靜默吞掉後仍綠燈。

鎖定 code path：pipeline.py:184-198
    try:
        w = write_supplement(gap, sources, llm)
    except Exception as exc:
        ...
        w = WrittenSupplement(text="【待補證】...", used_source_ids=[])

既有非整合測試覆蓋了 malformed gap JSON fallback（gap.py:82-90），
但「write_supplement 本身拋例外 → pipeline 靜默降級」這條路徑沒有直接驗證。
若此路徑被移除或改為 re-raise，本測試會紅燈。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from note_filler.llm import FakeLLM
from note_filler.pipeline import run_pipeline
from note_filler.retrieve.models import Source


class _FakeTwinkle:
    def __init__(self, batches):
        self.batches = list(batches)
        self.queries = []

    def search(self, query, n=3):
        self.queries.append(query)
        return self.batches.pop(0) if self.batches else []


class _FakeLaw:
    def lookup_article(self, law_name, article_no):
        return None

    def law_exists(self, name):
        return True

    def fuzzy_find_law(self, name):
        return None

    def search_articles(self, keyword, limit=5, law_name=None):
        return []


def _make_note(tmp_path: Path) -> str:
    p = tmp_path / "note.docx"
    d = DocxDocument()
    d.add_paragraph("行政程序法要求行政行為應遵守正當程序。")
    d.add_paragraph("本筆記僅記錄部分重點,尚未展開。")
    d.save(str(p))
    return str(p)


def test_write_supplement_exception_yields_pending_evidence(tmp_path):
    """write_supplement 拋例外 → pipeline 靜默降級為 pending_evidence 且不中斷。

    驗證 pipeline.py:184-198 的 except 分支：例外被吞、補充段以
    「【待補證】」開頭、used_source_ids=[]、confidence=pending_evidence。
    若此路徑不存在，本測試會因 write_supplement 的 RuntimeError 而紅燈。
    """
    note_path = _make_note(tmp_path)

    # domain / questions / gaps / keyword抽取 / writer（writer 會拋例外）
    llm = FakeLLM([
        "admin",
        "正當程序的要件為何?",
        json.dumps([
            {"question": "正當程序的要件為何?", "status": "missing", "reason": "筆記未展開"},
        ], ensure_ascii=False),
        '{"keyword": "正當程序", "law_name": null}',
        # FakeLLM 只有 4 個 response；第 5 次 complete 會 IndexError
        # 但 pipeline 先呼叫 write_supplement → llm.complete → IndexError
        # → 被 except Exception 捕獲 → 降級為 pending_evidence
    ])

    # Twinkle 回一筆來源，讓 retrieve_for_gap 有東西可傳給 write_supplement
    twinkle = _FakeTwinkle([
        [Source(
            id="s1", title="行政院公報", url="https://a", level="A",
            content="行政程序法相關內容", fetched_date="2026-07-15",
            doc_date=None, distance=0.1,
        )],
    ])

    doc = run_pipeline(note_path, llm, twinkle, _FakeLaw())

    supplements = [s for s in doc.segments if s.type == "supplement"]
    assert supplements, "應至少有一個補充段"
    sup = supplements[0]
    # 例外被吞：補充段以【待補證】開頭、無引用來源
    assert sup.text.startswith("【待補證】"), (
        f"write_supplement 拋例外後應降級為【待補證】，實際: {sup.text[:80]}"
    )
    assert sup.source_ids == [], "例外降級不應引用任何來源"
    assert sup.confidence == "pending_evidence", "例外降級段 confidence 應為 pending_evidence"
    assert sup.sources == [], "例外降級段 sources 應為空"


def test_empty_gaps_still_produces_nonempty_note(tmp_path):
    """detect_gaps 回空 → 無補充段 → require_non_empty_note_product 仍靠 original 通過。

    驗證 pipeline 在無缺口時不產生補充，但原稿段仍完整保留。
    若 require_non_empty_note_product 誤判為失敗，本測試會紅燈。
    """
    note_path = _make_note(tmp_path)

    llm = FakeLLM([
        "admin",
        "什麼是行政程序?",
        # detect_gaps: 所有問題皆 covered → 過濾後 gaps 為空 → 不產生 supplement
        json.dumps([
            {"question": "什麼是行政程序?", "status": "covered", "reason": "已涵蓋"},
        ], ensure_ascii=False),
    ])
    twinkle = _FakeTwinkle([])

    doc = run_pipeline(note_path, llm, twinkle, _FakeLaw())

    supplements = [s for s in doc.segments if s.type == "supplement"]
    assert supplements == [], "空缺口不應產生補充段"
    originals = [s for s in doc.segments if s.type == "original"]
    assert len(originals) == 2, "原稿段應完整保留"
    assert originals[0].text == "行政程序法要求行政行為應遵守正當程序。"
    assert originals[1].text == "本筆記僅記錄部分重點,尚未展開。"
