# src/note_filler/correction.py
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from note_filler.angle_coverage import (
    attach_relations,
    build_angle_coverage,
    build_argument_angle_fields,
    coverage_from_segment,
)
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

# 關聯知識必須明示決策品質支撐與使用者理解補強（機器可驗收關鍵詞）
RELATED_KNOWLEDGE_DECISION_MARKER = "支撐決策品質"
RELATED_KNOWLEDGE_UNDERSTANDING_MARKER = "補強使用者理解"


def build_related_knowledge(
    *,
    knowledge_body: str,
    functional_gap: str = "",
    user_value: str = "",
) -> str:
    """組裝與 argument_id 同論點綁定的關聯知識文字。

    必須同時說明：
      1. 如何支撐決策品質（對應功能缺口、提供可追溯依據）
      2. 如何補強使用者理解（對應使用者價值）
    """
    body = (knowledge_body or "").strip()
    fg = (functional_gap or "").strip() or "（未標示功能缺口）"
    uv = (user_value or "").strip() or "（未標示使用者價值）"
    prefix = body if body else "（尚無可落地的關聯知識正文）"
    return (
        f"{prefix}"
        f"（如何{RELATED_KNOWLEDGE_DECISION_MARKER}：對應功能缺口「{fg}」"
        f"提供可追溯依據，降低僅憑印象取捨的風險；"
        f"如何{RELATED_KNOWLEDGE_UNDERSTANDING_MARKER}：{uv}）"
    )


def related_knowledge_explains_value(text: str) -> bool:
    """關聯知識非空且明確含決策品質／使用者理解雙重說明。"""
    t = (text or "").strip()
    return (
        bool(t)
        and RELATED_KNOWLEDGE_DECISION_MARKER in t
        and RELATED_KNOWLEDGE_UNDERSTANDING_MARKER in t
    )


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
    summary: str | None = None
    # None＝相容既有手建 Segment，binding_report 依 summary 合成；空字串＝明確缺欄
    related_knowledge: str | None = None
    argument_id: str = ""
    # 角度覆蓋：主類型／標籤／精確鍵（序列化時組成 angle_coverage）
    angle_type: str = ""
    angle_labels: list[str] = field(default_factory=list)
    angle_key: str = ""
    angle_tags: list[str] = field(default_factory=list)
    valid_angle_count: int = 0
    deduped_angle_count: int = 0
    duplicate_angles: list[str] = field(default_factory=list)


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
                summary="",
                related_knowledge="",
                argument_id="",
                angle_type="",
                angle_labels=[],
                angle_key="",
            )
        )

    # 2) 每個 gap 一個 supplement 段(overlay 疊加):text 取寫作結果,
    #    sources 只掛實際引用到(used_source_ids)的 Source。
    for gap_idx, gap in enumerate(gaps):
        arg_idx = gap_idx  # argument_index 對應 gap_idx
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
            used_ids = []
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
            confidence = "pending_evidence"
        elif _grounded(used_sources):
            confidence = "verified"
        else:
            confidence = "pending_evidence"

        # 從 validations 取 conflict_note,確保衝突資訊不被丟棄
        conflict_note = None
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

        if used_ids:
            source_id = f"sources:{','.join(used_ids)}"
        else:
            source_id = f"pending:gap:{gap_idx}"

        argument_id = f"argument:{arg_idx}"

        # 必要性雙視角：功能缺口取 gap.reason；使用者價值由問題推導
        functional_gap = gap.reason
        user_value = f"補齊讀者對「{q}」所需的說明"
        # 關聯知識：同 argument_id 綁定，明示決策品質支撐與使用者理解補強
        related_knowledge = build_related_knowledge(
            knowledge_body=text,
            functional_gap=functional_gap,
            user_value=user_value,
        )
        # 角度覆蓋：依問題文字分類類型／標籤／鍵，供重複／同義機器判定
        angle_cov = build_angle_coverage(
            question=q,
            argument_text=text,
            functional_gap=functional_gap,
            user_value=user_value,
        )

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
                # 必要性雙視角：功能缺口取 gap.reason；使用者價值由問題推導，
                # 避免後續只掛來源卻遺失「為何需要此論點」的視角。
                functional_gap=functional_gap,
                user_value=user_value,
                summary=text,
                related_knowledge=related_knowledge,
                argument_id=argument_id,
                angle_type=angle_cov["angle_type"],
                angle_labels=list(angle_cov["angle_labels"]),
                angle_key=angle_cov["angle_key"],
            )
        )

    arguments = [seg for seg in segments if seg.type == "supplement"]
    coverages = attach_relations([coverage_from_segment(seg) for seg in arguments])
    for seg, cov in zip(arguments, coverages, strict=True):
        fields = build_argument_angle_fields(
            cov,
            argument_id=seg.argument_id,
            coverages=coverages,
        )
        for name, value in fields.items():
            setattr(seg, name, value)

    return CorrectionDoc(original=doc, segments=segments)
