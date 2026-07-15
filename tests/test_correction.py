# tests/test_correction.py
import pytest

from note_filler.correction import assemble_correction, Segment, CorrectionDoc
from note_filler.parse import Document, Paragraph      # T2
from note_filler.gap import Gap                         # T5
from note_filler.retrieve.models import Source                 # T6
from note_filler.verify import Validation              # T10


def _doc(texts):
    paras = tuple(Paragraph(idx=i, text=t) for i, t in enumerate(texts))
    return Document(source_path="x.docx", paragraphs=paras, full_text="\n".join(texts))


def _src(sid, title, url, level="A"):
    return Source(
        id=sid, title=title, url=url, level=level,
        content=f"{title} 記錄全文", fetched_date="2026-07-15",
        doc_date=None, distance=0.4,
    )


def test_original_segments_verbatim_and_immutable():
    """原文段逐字全等輸入,順序/段數不變,confidence=verified。"""
    texts = ["行政程序法第92條規定行政處分之定義。", "第二段原始筆記內容,一字不改。"]
    doc = _doc(texts)
    cd = assemble_correction(doc, gaps=[], retrieved={}, validations={})
    originals = [s for s in cd.segments if s.type == "original"]
    assert [s.text for s in originals] == texts          # 逐字全等(immutable)
    assert [s.anchor_idx for s in originals] == [0, 1]   # anchor = 原段 idx
    assert all(s.confidence == "verified" for s in originals)
    assert all(s.sources == [] for s in originals)
    assert cd.original is doc                             # 原 Document 原封帶回


def test_no_source_gap_is_pending_and_still_present():
    """無源 gap:confidence=pending_evidence,且該 supplement 段仍在 segments(不刪)。"""
    doc = _doc(["行政處分之定義。"])
    gap = Gap(question="訴願期間多久?", status="missing", reason="原文未提及")
    cd = assemble_correction(doc, gaps=[gap], retrieved={}, validations={})
    sups = [s for s in cd.segments if s.type == "supplement"]
    assert len(sups) == 1                                 # 保留該段
    assert sups[0].sources == []
    assert sups[0].confidence == "pending_evidence"       # C6:無源 → pending


def test_two_independent_ab_sources_verified():
    """有 2 個獨立 A/B 源且 Validation.verified=True → confidence=verified。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="missing", reason="原文未提及")
    s1 = _src("1", "訴願法第14條", "https://law.moj.gov.tw/a", level="A")
    s2 = _src("2", "立法院議案關係文書", "https://ly.gov.tw/b", level="B")
    retrieved = {q: [s1, s2]}
    validations = {q: Validation(claim=q, sources=[s1, s2], verified=True,
                                 conflict=False, conflict_note=None)}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved, validations=validations)
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "verified"
    assert len(sup.sources) == 2


def test_sources_but_unverified_stays_pending():
    """C6 第二 clause:有源但 verified=False,仍必須 pending_evidence。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="partial", reason="僅片段")
    s1 = _src("1", "訴願法第14條", "https://law.moj.gov.tw/a", level="A")
    retrieved = {q: [s1]}
    validations = {q: Validation(claim=q, sources=[s1], verified=False,
                                 conflict=False, conflict_note=None)}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved, validations=validations)
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "pending_evidence"


def test_anchor_picks_keyword_overlap():
    doc = _doc(["訴願程序相關規定。", "完全無關的天氣內容。"])
    gap = Gap(question="訴願期間多久?", status="missing", reason="")
    cd = assemble_correction(doc, gaps=[gap], retrieved={}, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.anchor_idx == 0        # 與「訴願」重疊之段


def test_anchor_none_when_no_overlap():
    doc = _doc(["天氣晴朗適合出遊。"])
    gap = Gap(question="ABC XYZ?", status="missing", reason="")
    cd = assemble_correction(doc, gaps=[gap], retrieved={}, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.anchor_idx is None
