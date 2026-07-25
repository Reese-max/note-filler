# src/note_filler/correction.py
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from note_filler.audit import audit_event

if TYPE_CHECKING:                      # 僅型別提示,執行期零硬耦合(結構化 attr 讀取)
    from note_filler.parse import Document
    from note_filler.gap import Gap
    from note_filler.retrieve.models import Source
    from note_filler.verify import Validation
    from note_filler.write import WrittenSupplement

logger = logging.getLogger(__name__)

# gap 在 written 字典中找不到時的可追蹤佔位文;以【待補證】開頭以觸發 pending_evidence
MISSING_WRITTEN_TEXT = "【待補證】寫作結果缺失：gap 問題不在 written 字典中"


@dataclass
class Segment:
    type: Literal["original", "supplement"]
    text: str
    anchor_idx: int | None
    sources: list
    confidence: Literal["verified", "pending_evidence"]
    conflict_note: str | None = None
    traceability: list[dict] = field(default_factory=list)
    source_id: str = ""
    source_ids: list[str] = field(default_factory=list)
    functional_gap: str = ""
    user_value: str = ""


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


def _grounded(sources) -> bool:
    """grounded/verified 若滿足其一(一手源即定論):
    (1) 引用來源含 >=1 個 level A(法規一手);或
    (2) 引用來源含 >=1 個 level C(官方/標準組織一手,如 owasp.org/NIST/CVE);或
    (3) 含 >=2 個相異來源(相異以 id 或 title 判,level 不限 A/B/C/D)。
    """
    if any(s.level == "A" for s in sources):
        return True
    if any(s.level == "C" for s in sources):
        return True
    kept: list = []
    for s in sources:
        if all(s.id != k.id or s.title != k.title for k in kept):
            kept.append(s)
    return len(kept) >= 2


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
                traceability=[
                    {
                        "kind": "original_input",
                        "id": doc.source_path,
                        "paragraph_idx": p.idx,
                    }
                ],
                source_id=f"input:{doc.source_path}#p{p.idx}",
                source_ids=[],
                functional_gap="",
                user_value="",
            )
        )

    # 2) 每個 gap 一個 supplement 段(overlay 疊加):text 取寫作結果,
    #    sources 只掛實際引用到(used_source_ids)的 Source。
    for gap_idx, gap in enumerate(gaps):
        q = gap.question
        w = written.get(q)
        if w is None:
            # 不可靜默產生空補充:明確告警 + 可機器比對的【待補證】佔位
            audit_event(
                logger,
                "written_supplement_missing",
                q,
                reason="gap question absent from written mapping",
                outcome="pending_evidence",
            )
            text = MISSING_WRITTEN_TEXT
            used_ids: list = []
        else:
            text = w.text
            used_ids = w.used_source_ids
        # 由 id 從 retrieved 找回 Source 物件,只保留 used 且找得到者(依 used 序)
        by_id = {s.id: s for s in retrieved.get(q, [])}
        used_sources = [by_id[sid] for sid in used_ids if sid in by_id]
        missing_ids = [sid for sid in used_ids if sid not in by_id]
        if missing_ids:
            audit_event(
                logger,
                "used_sources_not_forwarded",
                q,
                missing_source_ids=missing_ids,
                reason="used source IDs not found in retrieved",
            )

        # confidence:【待補證】→ pending;否則一手源即 grounded(見 _grounded)
        if text.startswith("【待補證】"):
            confidence: Literal["verified", "pending_evidence"] = "pending_evidence"
        elif _grounded(used_sources):
            confidence = "verified"
        else:
            confidence = "pending_evidence"

        # 從 validations 取 conflict_note,確保衝突資訊不被丟棄
        conflict_note: str | None = None
        v = validations.get(q)
        if v is not None and getattr(v, "conflict", False):
            conflict_note = getattr(v, "conflict_note", None)
        elif v is None:
            audit_event(
                logger,
                "validation_not_forwarded",
                q,
                reason="question absent from validations mapping",
                outcome="pending_evidence" if confidence == "pending_evidence" else confidence,
            )

        source_id: str
        if used_ids:
            source_id = f"sources:{','.join(used_ids)}"
        else:
            source_id = f"pending:gap:{gap_idx}"

        segments.append(
            Segment(
                type="supplement",
                text=text,
                anchor_idx=_best_anchor(q, doc.paragraphs),
                sources=used_sources,
                confidence=confidence,
                conflict_note=conflict_note,
                traceability=(
                    [{"kind": "source", "id": source.id} for source in used_sources]
                    or [
                        {
                            "kind": "processing_record",
                            "id": f"gap:{gap_idx}",
                            "question": q,
                            "outcome": confidence,
                        }
                    ]
                ),
                source_id=source_id,
                source_ids=list(used_ids) if used_ids else [],
                functional_gap=gap.reason,
                user_value="",
            )
        )

    return CorrectionDoc(original=doc, segments=segments)
