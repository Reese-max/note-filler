# src/note_filler/correction.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:                      # 僅型別提示,執行期零硬耦合(結構化 attr 讀取)
    from note_filler.parse import Document
    from note_filler.gap import Gap
    from note_filler.retrieve.models import Source
    from note_filler.verify import Validation


@dataclass
class Segment:
    type: Literal["original", "supplement"]
    text: str
    anchor_idx: int | None
    sources: list
    confidence: Literal["verified", "pending_evidence"]


@dataclass
class CorrectionDoc:
    original: "Document"
    segments: list


# CJK 逐字 + 英數字詞:粗略關鍵詞集合,供 anchor 重疊比對
_TOKEN = re.compile(r"[A-Za-z0-9]+|[一-鿿]")


def _tokens(s: str) -> set[str]:
    return set(_TOKEN.findall(s))


def _best_anchor(question: str, paragraphs) -> int | None:
    """挑與 question 關鍵詞重疊最多的原文段 idx;全為 0 → None;平手取最小 idx。"""
    q = _tokens(question)
    if not q:
        return None
    best_idx: int | None = None
    best_overlap = 0
    for p in paragraphs:               # paragraphs 已按 idx 遞增
        overlap = len(q & _tokens(p.text))
        if overlap > best_overlap:     # 嚴格大於 → 平手保留先出現(較小 idx)
            best_overlap = overlap
            best_idx = p.idx
    return best_idx


def _supplement_text(gap, sources) -> str:
    """組 supplement 段本文;無源時退回 gap.reason/question(段仍保留待補)。"""
    if sources:
        body = "；".join(s.content for s in sources)
    else:
        body = gap.reason or gap.question
    return f"針對「{gap.question}」補充:{body}"


def assemble_correction(doc, gaps, retrieved, validations) -> CorrectionDoc:
    segments: list[Segment] = []

    # 1) 原文段:逐字保留(immutable),絕不改一字;overlay 不刪原文
    for p in doc.paragraphs:
        segments.append(
            Segment(
                type="original",
                text=p.text,           # 逐字等於原 Paragraph.text
                anchor_idx=p.idx,
                sources=[],
                confidence="verified",
            )
        )

    # 2) 每個 gap 一個 supplement 段(overlay 疊加)
    for gap in gaps:
        sources = list(retrieved.get(gap.question, []))
        val = validations.get(gap.question)
        verified = bool(val and val.verified)
        # C6 不變式:無源 或 未 verified → pending_evidence(保留該段不刪)
        confidence = "verified" if (sources and verified) else "pending_evidence"
        segments.append(
            Segment(
                type="supplement",
                text=_supplement_text(gap, sources),
                anchor_idx=_best_anchor(gap.question, doc.paragraphs),
                sources=sources,
                confidence=confidence,
            )
        )

    return CorrectionDoc(original=doc, segments=segments)
