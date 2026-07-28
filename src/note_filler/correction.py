# src/note_filler/correction.py
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlparse

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

# 論點區塊最低可開啟連結數
MIN_OPENABLE_LINKS = 2

# gap 在 written 字典中找不到時的可追蹤佔位文;以【待補證】開頭以觸發 pending_evidence
MISSING_WRITTEN_TEXT = "【待補證】寫作結果缺失：gap 問題不在 written 字典中"


def is_openable_url(url: str | None) -> bool:
    """判定 URL 是否為真實可開啟連結（http/https 協議、非空白、可解析）。"""
    if not isinstance(url, str):
        return False
    s = url.strip()
    if not s:
        return False
    try:
        parsed = urlparse(s)
    except Exception:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

# 關聯知識必須明示決策品質支撐與使用者理解補強（機器可驗收關鍵詞）
RELATED_KNOWLEDGE_DECISION_MARKER = "支撐決策品質"
RELATED_KNOWLEDGE_UNDERSTANDING_MARKER = "補強使用者理解"

# 排除固定模板語，否則「讀者／說明」也會讓無關內容誤判一致。
_RELATED_TOPIC_NOISE = re.compile(
    r"如何支撐決策品質|如何補強使用者理解|對應功能缺口|功能缺口|使用者價值|"
    r"提供可追溯依據|降低僅憑印象取捨的風險|原稿|未(?:定義|說明|提供)|"
    r"缺(?:少|失)|補齊|所需的說明|幫助|協助|讀者|使用者|定義|限制|"
    r"說明|理解|重要性?|影響|價值"
)
_RELATED_TOPIC_RUN = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")
_DIRECT_RELEVANCE_NOISE = re.compile(
    r"問題|為何|如何|何謂|哪些|是否|要件|規定|之|的|與|及|或"
)


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


def _related_topic_tokens(text: str) -> set[str]:
    normalized = _RELATED_TOPIC_NOISE.sub(" ", (text or "").casefold())

    tokens: set[str] = set()
    for run in _RELATED_TOPIC_RUN.findall(normalized):
        if run.isascii():
            if len(run) >= 2:
                tokens.add(run)
            continue
        for size in range(2, min(8, len(run)) + 1):
            tokens.update(run[i : i + size] for i in range(len(run) - size + 1))
    return tokens


def _source_directly_related(question: str, source) -> bool:
    """來源標題／正文至少須與論點問題共享一個具體主題詞。"""
    question_topics = _related_topic_tokens(
        _DIRECT_RELEVANCE_NOISE.sub(" ", question or "")
    )
    if not question_topics:
        return True
    source_text = f"{getattr(source, 'title', '')} {getattr(source, 'content', '')}"
    # ponytail: 先用可重現的詞彙重疊；有同義改寫誤拒量測時再換離線語義模型。
    return bool(question_topics & _related_topic_tokens(source_text))


def related_knowledge_matches_views(
    text: str,
    *,
    functional_gap: str,
    user_value: str,
) -> bool:
    """關聯知識、功能缺口與使用者價值須指向同一主題。"""
    related = (text or "").strip()
    gap = (functional_gap or "").strip()
    value = (user_value or "").strip()
    if not related_knowledge_explains_value(related) or not gap or not value:
        return False

    decision_at = related.find(RELATED_KNOWLEDGE_DECISION_MARKER)
    understanding_at = related.find(RELATED_KNOWLEDGE_UNDERSTANDING_MARKER)
    if understanding_at <= decision_at:
        return False
    decision_view = related[
        decision_at + len(RELATED_KNOWLEDGE_DECISION_MARKER) : understanding_at
    ]
    understanding_view = related[
        understanding_at + len(RELATED_KNOWLEDGE_UNDERSTANDING_MARKER) :
    ]

    gap_topics = _related_topic_tokens(gap)
    value_topics = _related_topic_tokens(value)
    decision_topics = _related_topic_tokens(decision_view)
    understanding_topics = _related_topic_tokens(understanding_view)

    # ponytail: 先用可重現的詞彙重疊；有量測到同義改寫誤拒時再換離線語義模型。
    explicit_links = gap in decision_view and value in understanding_view
    views_align = (
        explicit_links
        or not gap_topics
        or not value_topics
        or bool(gap_topics & value_topics)
    )
    gap_linked = gap in decision_view or bool(gap_topics & decision_topics)
    value_linked = value in understanding_view or bool(
        value_topics & understanding_topics
    )
    return views_align and gap_linked and value_linked


@dataclass
class Segment:
    type: Literal["original", "supplement"]
    text: str
    anchor_idx: int | None
    sources: list
    confidence: Literal["verified", "pending_evidence"]
    conflict_note: str | None = None
    traceability: list[dict] = field(default_factory=list)
    citation_spans: list[dict] = field(default_factory=list)
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
    # 延伸閱讀：檢索到但未被引用的來源（附加區塊，不影響原稿）
    extended_readings: list[dict] = field(default_factory=list)
    extended_readings_status: str = "none"  # "none" | "available" | "pending_evidence"
    pending_evidence_reason: str = ""  # 為何此論點缺乏足夠來源
    # 可開啟連結：論點區塊至少需 2 條真實可開啟 URL
    openable_links_count: int = 0
    openable_links_status: str = "none"  # "none" | "insufficient" | "sufficient"
    openable_links_incomplete_reason: str = ""  # 為何可開啟連結不足


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
                citation_spans=[],
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

        # 延伸閱讀：依優先級規則收集（實際引用→權威延伸）
        all_retrieved = retrieved.get(q, [])
        omitted_ids = w.omitted_source_ids if w is not None else []
        by_id_full = {s.id: s for s in all_retrieved}
        
        # 優先級規則：先收集實際引用來源，再補權威延伸來源
        # 權威排序：Level A > B > C > D，同層級按 distance 遞增
        def source_priority_key(sid):
            if sid not in by_id_full:
                return (99, 1.0)  # 最低優先級
            src = by_id_full[sid]
            level_order = {"A": 0, "B": 1, "C": 2, "D": 3}
            level_priority = level_order.get(src.level, 99)
            return (level_priority, src.distance)
        
        # 收集所有候選來源（引用 + 延伸），按優先級排序
        all_candidate_ids = list(used_ids) + list(omitted_ids)
        # 去重但保持優先級（used_ids 優先）
        seen = set()
        prioritized_candidates = []
        for sid in all_candidate_ids:
            if sid in seen:
                continue
            seen.add(sid)
            if sid in by_id_full:
                prioritized_candidates.append(sid)
        
        # 按優先級排序
        prioritized_candidates.sort(key=source_priority_key)
        
        # 延伸閱讀只包含未被引用的來源，並依優先級排序
        # 欄位順序依格式規格 v1 定義：source_id, title, url, level, distance
        extended_readings_unsorted = [
            {
                "source_id": sid,
                "title": by_id_full[sid].title,
                "url": by_id_full[sid].url,
                "level": by_id_full[sid].level,
                "distance": by_id_full[sid].distance,
            }
            for sid in omitted_ids
            if sid in by_id_full
        ]
        # 依優先級排序延伸閱讀：Level A > B > C > D，同層級按 distance 遞增
        extended_readings = sorted(extended_readings_unsorted, key=lambda r: (
            {"A": 0, "B": 1, "C": 2, "D": 3}.get(r.get("level", "?"), 99),
            r.get("distance", 1.0)
        ))
        
        # 狀態判定：依延伸閱讀是否存在與 confidence 狀態
        if extended_readings:
            extended_readings_status = "available"
        elif confidence == "pending_evidence":
            extended_readings_status = "pending_evidence"
        else:
            extended_readings_status = "none"

        # 可開啟連結：依優先級規則收集（實際引用→權威延伸），保證至少2條URL
        # 使用優先級排序的候選來源
        prioritized_openable_urls = [
            by_id_full[sid].url
            for sid in prioritized_candidates
            if sid in by_id_full and is_openable_url(by_id_full[sid].url)
        ]
        directly_related_openable_ids = [
            sid
            for sid in prioritized_candidates
            if sid in by_id_full
            and is_openable_url(by_id_full[sid].url)
            and _source_directly_related(q, by_id_full[sid])
        ]
        
        # 區分引用與延伸來源（用於錯誤訊息）
        cited_urls = [
            by_id_full[sid].url
            for sid in used_ids
            if sid in by_id_full and is_openable_url(by_id_full[sid].url)
        ]
        extended_urls = [
            by_id_full[sid].url
            for sid in omitted_ids
            if sid in by_id_full and is_openable_url(by_id_full[sid].url)
        ]
        
        openable_links_count = len(prioritized_openable_urls)
        directly_related_openable_count = len(directly_related_openable_ids)
        has_any_candidates = bool(used_ids or omitted_ids)
        
        # 無任何候選來源時（pure pending），不強制要求可開啟連結
        if not has_any_candidates:
            openable_links_status = "sufficient"
            openable_links_incomplete_reason = ""
        elif directly_related_openable_count >= MIN_OPENABLE_LINKS:
            openable_links_status = "sufficient"
            openable_links_incomplete_reason = ""
        else:
            openable_links_status = "insufficient"
            related_cited_count = sum(sid in used_ids for sid in directly_related_openable_ids)
            missing_binding = (
                f"{argument_id}.extended_readings"
                if related_cited_count
                else f"{argument_id}.source_ids"
            )
            if openable_links_count == 0:
                openable_links_incomplete_reason = (
                    f"{missing_binding} 缺失：無可開啟連結"
                    "（引用來源與延伸閱讀均無有效 URL）"
                )
            elif openable_links_count < MIN_OPENABLE_LINKS:
                openable_links_incomplete_reason = (
                    f"{missing_binding} 缺失：僅有 {openable_links_count} 條可開啟連結"
                    f"（引用來源 {len(cited_urls)} 條、延伸閱讀 {len(extended_urls)} 條），"
                    f"不足 {MIN_OPENABLE_LINKS} 條"
                )
            else:
                openable_links_incomplete_reason = (
                    f"{missing_binding} 缺失：雖有 {openable_links_count} 條可開啟連結，"
                    f"但與論點直接相關僅 {directly_related_openable_count} 條，"
                    f"不足 {MIN_OPENABLE_LINKS} 條"
                )

        # pending_evidence_reason：說明為何此論點缺乏足夠來源（含優先級與URL數量）
        pending_evidence_reason = ""
        if confidence == "pending_evidence":
            if not used_ids and not extended_readings:
                pending_evidence_reason = "檢索無可用來源"
            elif not used_ids and extended_readings:
                pending_evidence_reason = "有候選來源但未被引用"
            elif openable_links_count < MIN_OPENABLE_LINKS and has_any_candidates:
                pending_evidence_reason = (
                    f"可開啟連結不足 {MIN_OPENABLE_LINKS} 條"
                    f"（實際 {openable_links_count} 條），無法滿足論點區塊最低要求"
                )
            elif text.startswith("【待補證】"):
                pending_evidence_reason = "來源與問題完全無關或無從作答"
            else:
                pending_evidence_reason = "引用來源不足或未通過驗證"

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
                citation_spans=[dict(span) for span in (w.citation_spans or [])]
                if w is not None
                else [],
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
                extended_readings=extended_readings,
                extended_readings_status=extended_readings_status,
                pending_evidence_reason=pending_evidence_reason,
                openable_links_count=openable_links_count,
                openable_links_status=openable_links_status,
                openable_links_incomplete_reason=openable_links_incomplete_reason,
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
