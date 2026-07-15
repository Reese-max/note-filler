"""端到端驗收測試(spec §12)。

§12 硬不變式:
  1. 原稿逐字不可變(diff 只增不改)
  2. 無來源閘 + C6:supplement sources 空 -> confidence == "pending_evidence"
  3. 交叉驗證 C4:supplement verified -> sources 非空且皆 A/B、>=2 獨立來源
  4. 補充法條經 check_law_citations(text=..., lookup) 無 article_not_found
  5. C3:輸出由 T14 to_markdown 產出,含【補充】/⚠待補證/參考區塊(帶日期 C7)
"""
from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import pytest

from note_filler.knowledge.law_citation_check import check_law_citations   # T8
from note_filler.knowledge.law_lookup import LawLookup                     # T8
from note_filler.llm import FakeLLM, GrokClient                  # T1
from note_filler.retrieve.models import Source                             # 鎖定型別(隨 T7)
from note_filler.pipeline import run_pipeline                    # T13
from note_filler.export import to_json, to_markdown             # T14
from note_filler.retrieve.twinkle import TwinkleClient                    # T7

FIXTURE = Path(__file__).parent / "fixtures" / "real_note.txt"
LAW_DB = Path(__file__).resolve().parents[1] / "data" / "law_index.db"


# ---- 環境探測(網路類斷言的 skip 閘) --------------------------------------
def _grok_up(host: str = "127.0.0.1", port: int = 8318) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def _twinkle_ready() -> bool:
    return bool(os.environ.get("TWINKLE_HUB_TOKEN")) and \
        os.environ.get("GOV_AI_ENABLE_TWINKLE_MCP") == "1"


# ---- 共用不變式(結構類,離線與真跑都套用) --------------------------------
def _assert_immutable_original(doc, note_text: str) -> None:
    """§12(1) 原稿逐字不可變:全文與各段皆不得被竄改,只增不改。

    parse_note 的契約(T2):full_text = 各段以單一換行 join(空行段界正規化,
    段內一字不改)。故逐字不可變的判準為「每段 verbatim 出現在原始檔」+
    「full_text 恰為各原文段之 join」,而非與原始位元組逐位元組相等。
    """
    assert doc.original.full_text == "\n".join(
        p.text for p in doc.original.paragraphs
    ), "原稿 full_text 應為各原文段以換行 join,不得竄改"
    for para in doc.original.paragraphs:
        assert para.text in note_text, f"原稿段落被竄改: {para.text!r}"
    for seg in doc.segments:
        if seg.type == "original":
            assert seg.text in note_text, f"original segment 非逐字原文: {seg.text!r}"


def _assert_no_source_gate(doc) -> None:
    """§12(2) 無來源閘 + C6 pending_evidence 不變式(斷言不變式,非「一定存在」)。"""
    for seg in doc.segments:
        if seg.type != "supplement":
            continue
        if not seg.sources:
            assert seg.confidence == "pending_evidence", \
                "sources 空的 supplement 必須 pending_evidence(不得刪除)"
        if seg.confidence == "verified":
            assert seg.sources, "verified supplement 不得無來源"
            assert all(s.level in ("A", "B") for s in seg.sources), \
                "verified 來源必須皆為 A/B 級"


def _assert_law_citations_ok(doc, law: LawLookup) -> None:
    """§12(4) 補充內法條必須真實存在(C2:text 第一參數)。"""
    for seg in doc.segments:
        if seg.type != "supplement":
            continue
        issues = check_law_citations(text=seg.text, lookup=law)
        bad = [i for i in issues if i.get("kind") == "article_not_found"]
        assert not bad, f"補充出現不存在法條: {bad}"


def _assert_markdown_contract(doc) -> None:
    """§12(5)/C3:呼叫 T14 to_markdown,驗鎖定格式標記,不自訂另一套格式。"""
    md = to_markdown(doc)               # C3:直接 import 呼叫 T14
    assert isinstance(md, str) and md
    for seg in doc.segments:
        if seg.type == "original":
            assert seg.text in md, "原文段未原樣輸出"
        else:  # supplement
            assert "> 【補充】" in md, "supplement 未依 C3 格式輸出"
            if seg.confidence == "pending_evidence":
                assert "⚠待補證" in md, "pending_evidence 未標 ⚠待補證"
    # C7:被引用來源的參考區塊須帶日期(doc_date 優先否則 fetched_date)
    cited = [s for seg in doc.segments for s in (seg.sources or [])]
    if cited:
        assert any((s.doc_date or s.fetched_date) in md for s in cited), \
            "參考區塊應含來源日期(doc_date 優先否則 fetched_date)"
    # to_json 亦須可序列化
    assert isinstance(to_json(doc), dict)


# ---- 離線替身:回兩個「獨立 A/B」來源,使 supplement 可被判 verified ----------
class _StubTwinkle:
    """符合 TwinkleClient.search(query, n=3) -> list[Source]。"""

    def __init__(self) -> None:
        today = "2026-07-15"
        self._sources = [
            Source(id="s1", title="行政程序法(全國法規資料庫)",
                   url="https://law.moj.gov.tw/LawClass/A0030055",
                   level="A", content="行政程序法第92條:本法所稱行政處分,係指行政機關就公法上具體事件所為之決定或其他公權力措施。",
                   fetched_date=today, doc_date="2021-01-20", distance=0.62),
            Source(id="s2", title="立法院議案關係文書",
                   url="https://ppg.ly.gov.tw/ppg/bills/2",
                   level="B", content="行政程序法第92條修正說明:釐清行政處分之對外效力。",
                   fetched_date=today, doc_date=None, distance=0.71),
        ]

    def search(self, query: str, n: int = 3):
        return list(self._sources[:n])


# ---- 結構類:永遠跑(不打真網路) -------------------------------------------
@pytest.mark.skipif(not LAW_DB.exists(), reason="缺 data/law_index.db,無法驗離線結構不變式")
def test_e2e_structural_invariants():
    note_text = FIXTURE.read_text(encoding="utf-8")
    law = LawLookup(str(LAW_DB))
    # law 領域每 gap 呼叫序=(keyword 抽取 + writer)。canned 依序:domain / questions /
    # gaps / gap(keyword 抽取 JSON, writer 撰寫)。writer text 不含「法第N條」樣式,
    # 避免誤觸法條引用檢查。
    fake = FakeLLM([
        "law",
        "什麼是行政處分?\n行政程序法第92條的定義為何?\n訴願前置程序為何?",
        json.dumps(
            [{"question": "行政程序法第92條的定義為何?",
              "status": "missing", "reason": "筆記未展開條文定義"}],
            ensure_ascii=False,
        ),
        '{"keyword": "行政處分", "law_name": "行政程序法"}',
        "行政處分係指行政機關就公法上具體事件所為之對外發生法律效果之單方行政行為[^1][^2]。",
    ])
    doc = run_pipeline(str(FIXTURE), fake, _StubTwinkle(), law)

    _assert_immutable_original(doc, note_text)
    _assert_no_source_gate(doc)
    _assert_law_citations_ok(doc, law)
    _assert_markdown_contract(doc)


# ---- 網路類:真 grok+真 twinkle+真 law;無 token/未上線則 skip --------------
@pytest.mark.integration
def test_e2e_acceptance_real():
    note_text = FIXTURE.read_text(encoding="utf-8")
    if not LAW_DB.exists():
        pytest.skip("缺 data/law_index.db")
    law = LawLookup(str(LAW_DB))

    if not (_grok_up() and _twinkle_ready()):
        pytest.skip(
            "grok proxy 未上線或無 TWINKLE_HUB_TOKEN/GOV_AI_ENABLE_TWINKLE_MCP;"
            "網路類斷言略過(結構不變式見 test_e2e_structural_invariants)"
        )

    llm = GrokClient()                                    # 127.0.0.1:8318 grok-4.3
    twinkle = TwinkleClient(token=os.environ["TWINKLE_HUB_TOKEN"])
    doc = run_pipeline(str(FIXTURE), llm, twinkle, law)

    # 結構不變式:真跑亦須成立
    _assert_immutable_original(doc, note_text)
    _assert_no_source_gate(doc)
    _assert_law_citations_ok(doc, law)
    _assert_markdown_contract(doc)

    # 網路類斷言:真跑應偵測 gap 產生補充;verified 者須 >=2 獨立 A/B(C4)
    supplements = [s for s in doc.segments if s.type == "supplement"]
    assert supplements, "真跑應偵測到 gap 並產生補充段"
    for seg in supplements:
        if seg.confidence == "verified":
            urls = {s.url for s in seg.sources}
            titles = {s.title for s in seg.sources}  # 機關/文件標題
            assert len(urls) >= 2 and len(titles) >= 2, \
                "verified 需 >=2 個 url 不同且 title(機關)不同的獨立 A/B 來源"
            assert all(s.level in ("A", "B") for s in seg.sources)
