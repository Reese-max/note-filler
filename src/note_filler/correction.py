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
    from note_filler.write import WrittenSupplement


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


def _has_two_independent_ab(sources) -> bool:
    """used 的 A/B 來源中,存在一對 url 不同且 title 不同者 → 視為 ≥2 個獨立。"""
    ab = [s for s in sources if s.level in ("A", "B")]
    return any(
        a.url != b.url and a.title != b.title
        for i, a in enumerate(ab)
        for b in ab[i + 1:]
    )


def assemble_correction(doc, gaps, retrieved, written, validations) -> CorrectionDoc:
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

    # 2) 每個 gap 一個 supplement 段(overlay 疊加):text 取寫作結果,
    #    sources 只掛實際引用到(used_source_ids)的 Source。
    for gap in gaps:
        q = gap.question
        w = written.get(q)
        text = w.text if w else ""
        # 由 id 從 retrieved 找回 Source 物件,只保留 used 且找得到者(依 used 序)
        by_id = {s.id: s for s in retrieved.get(q, [])}
        used_ids = w.used_source_ids if w else []
        used_sources = [by_id[sid] for sid in used_ids if sid in by_id]

        # confidence:【待補證】→ pending;否則 used A/B 有 ≥2 獨立 → verified
        if text.startswith("【待補證】"):
            confidence: Literal["verified", "pending_evidence"] = "pending_evidence"
        elif _has_two_independent_ab(used_sources):
            confidence = "verified"
        else:
            confidence = "pending_evidence"

        segments.append(
            Segment(
                type="supplement",
                text=text,
                anchor_idx=_best_anchor(q, doc.paragraphs),
                sources=used_sources,
                confidence=confidence,
            )
        )

    return CorrectionDoc(original=doc, segments=segments)
