"""主張級人工審查:Verify/Accept/Reject 審查佇列與決策履歷(issue #3)。

設計契約:
  - 每個 supplement/argument 有獨立 human review state,與系統 confidence 分欄保存;
    confidence=verified 只代表系統 evidence gate,不等於人類 ACCEPTED。
  - 決策以 stable argument_id + claim_hash + evidence_bundle_hash 綁定;
    claim text / citation span / source content / 驗證契約(confidence,conflict_note)
    任一改變 → 舊決策失效,狀態轉 STALE_REVIEW(fail closed,不靜默沿用)。
  - ReviewDecision ledger 可序列化/載入,以 doc_fingerprint 重播同一文件的審查狀態;
    檔案不存在、毀損或文件指紋不符 → 回傳全新 ledger(全部 UNREVIEWED,匯出安全)。
    無法辨識的既有履歷仍保留原檔,保存決策前須先修復或另存。
  - 來源立場(supports/conflicts/context_only/unresolved)只用 deterministic
    lexical overlap 與既有 cross_validate 衝突極性判定,不採用 LLM 自評。
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from note_filler.audit import audit_event
from note_filler.verify import _CONFLICT_PAIRS

if TYPE_CHECKING:                      # 僅型別提示,執行期零硬耦合
    from note_filler.correction import CorrectionDoc, Segment

logger = logging.getLogger(__name__)

REVIEW_LEDGER_SCHEMA = "note_filler.review_ledger.v2"
LEGACY_REVIEW_LEDGER_SCHEMA = "note_filler.review_ledger.v1"


class ReviewLedgerWriteConflict(ValueError):
    """An existing ledger cannot be safely recognized and replaced."""


class ReviewState(str, Enum):
    """每個主張的人類審查狀態(獨立於系統 confidence)。"""

    UNREVIEWED = "unreviewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    EDITED_ACCEPTED = "edited_accepted"
    STALE_REVIEW = "stale_review"


# 可由 record() 記錄的人類決策;UNREVIEWED/STALE_REVIEW 為衍生態,不可手動記錄
REVIEWABLE_DECISIONS = frozenset(
    {
        ReviewState.ACCEPTED,
        ReviewState.REJECTED,
        ReviewState.NEEDS_MORE_EVIDENCE,
        ReviewState.EDITED_ACCEPTED,
    }
)

# accepted-only 匯出允許的審查狀態
EXPORTABLE_STATES = frozenset({ReviewState.ACCEPTED, ReviewState.EDITED_ACCEPTED})

# 仍需人工處理的狀態(審查佇列「待審」計數)
PENDING_STATES = frozenset(
    {
        ReviewState.UNREVIEWED,
        ReviewState.STALE_REVIEW,
        ReviewState.NEEDS_MORE_EVIDENCE,
    }
)

# 決策理由快捷碼
REASON_CODES = frozenset(
    {
        "source_not_supporting",
        "out_of_scope",
        "duplicate",
        "needs_primary_source",
        "manual_edit",
    }
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def doc_fingerprint(doc: "CorrectionDoc") -> str:
    """文件指紋:綁定 ledger 與同一原始內容(原文改動 → 不重播舊決策)。

    只依內容(full_text + paragraphs),不依檔名:同內容不同路徑的筆記
    可重播決策;不同內容絕不共用履歷(fail closed)。
    """
    original = getattr(doc, "original", None)
    full_text = getattr(original, "full_text", "") or ""
    paragraphs = getattr(original, "paragraphs", ()) or ()
    payload = {
        "full_text": full_text,
        "paragraphs": [getattr(p, "text", "") for p in paragraphs],
    }
    return _sha(_canonical(payload))


def _declared_source_ids(segment: "Segment") -> list[str]:
    ids = list(getattr(segment, "source_ids", None) or [])
    ids.extend(
        span.get("source_id")
        for span in getattr(segment, "citation_spans", None) or []
        if isinstance(span, dict)
    )
    if not ids:
        ids = [getattr(s, "id", "") for s in getattr(segment, "sources", []) or []]
    return list(dict.fromkeys(sid for sid in ids if sid))


def claim_revision_hash(segment: "Segment") -> str:
    """主張修訂指紋:claim text、citation span、argument_id 任一變動即改變。"""
    spans = []
    for span in getattr(segment, "citation_spans", None) or []:
        if not isinstance(span, dict):
            continue
        spans.append(
            {
                "source_id": span.get("source_id"),
                "span_start": span.get("span_start"),
                "span_end": span.get("span_end"),
                "marker_text": span.get("marker_text"),
            }
        )
    spans.sort(key=_canonical)
    return _sha(
        _canonical(
            {
                "argument_id": getattr(segment, "argument_id", "") or "",
                "text": getattr(segment, "text", "") or "",
                "citation_spans": spans,
            }
        )
    )


def _snapshot_evidence(source) -> dict:
    """Changing currentness proof invalidates prior human evidence approval."""
    if not hasattr(source, "currentness"):
        return {}
    return {key: getattr(source, key, None) for key in (
        "snapshot_sha256", "currentness", "verified_at", "official_text_sha256",
    )}


def evidence_bundle_hash(segment: "Segment") -> str:
    """證據束指紋:引用來源 id/內容/層級/日期/URL、來源缺失、驗證契約皆納入。"""
    sources = list(getattr(segment, "sources", []) or [])
    by_id = {getattr(s, "id", ""): s for s in sources}
    # 涵蓋宣告的 source_ids 與實際掛上的 sources 聯集:任一成員的內容漂移皆失效
    all_ids = set(_declared_source_ids(segment)) | set(by_id) - {""}
    entries = []
    for sid in sorted(all_ids):
        src = by_id.get(sid)
        if src is None:
            entries.append({"source_id": sid, "missing": True})
            continue
        entries.append(
            {
                "source_id": sid,
                "missing": False,
                "content_sha": _sha(getattr(src, "content", "") or ""),
                "title": getattr(src, "title", "") or "",
                "url": getattr(src, "url", None),
                "level": getattr(src, "level", ""),
                "doc_date": getattr(src, "doc_date", None),
                "fetched_date": getattr(src, "fetched_date", "") or "",
                **_snapshot_evidence(src),
            }
        )
    return _sha(
        _canonical(
            {
                "sources": entries,
                "confidence": getattr(segment, "confidence", ""),
                "conflict_note": getattr(segment, "conflict_note", None),
            }
        )
    )


def _missing_source_ids(segment: "Segment") -> list[str]:
    present = {
        getattr(s, "id", "") for s in getattr(segment, "sources", []) or []
        if (getattr(s, "content", "") or "").strip()
    }
    return [sid for sid in _declared_source_ids(segment) if sid not in present]


_TOKEN_RUN = re.compile(r"[A-Za-z0-9]+|[一-鿿]+")


def _bigrams(text: str) -> set[str]:
    """ASCII 詞(>=2 字元)與 CJK 二字組;供 deterministic 支持度判定。"""
    out: set[str] = set()
    for run in _TOKEN_RUN.findall(text or ""):
        if run.isascii():
            if len(run) >= 2:
                out.add(run)
            continue
        out.update(run[i : i + 2] for i in range(len(run) - 1))
    return out


def _conflict_poles(text: str) -> dict[tuple[str, str], str]:
    """命中既有衝突關鍵詞對的正/反極性(沿用 verify 的 _CONFLICT_PAIRS)。"""
    poles: dict[tuple[str, str], str] = {}
    for pos, neg in _CONFLICT_PAIRS:
        if neg in text:
            poles[pos, neg] = "neg"
        elif pos in text:
            poles[pos, neg] = "pos"
    return poles


def source_stances(segment: "Segment") -> list[dict]:
    """逐來源 deterministic 立場判定:supports/conflicts/context_only/unresolved。

    - 與主張共享 >=2 個詞彙單位時,比較同一組正/反關鍵詞:相反 → conflicts。
    - 有來源衝突時須與主張的極性一致才標 supports;無衝突時採詞彙重疊。
      無法比較或詞彙不足 → unresolved。
    - 檢索到但未引用(extended_readings) → context_only。
    - 宣告但遺失的來源 → unresolved 且 missing=True。
    """
    sources = list(getattr(segment, "sources", []) or [])
    claim = getattr(segment, "text", "") or ""
    has_conflict = bool(getattr(segment, "conflict_note", None))
    claim_tokens = _bigrams(claim)
    claim_poles = _conflict_poles(claim)

    items: list[dict] = []
    cited_ids: set[str] = set()
    for src in sources:
        sid = getattr(src, "id", "")
        cited_ids.add(sid)
        content = (getattr(src, "content", "") or "").strip()
        poles = _conflict_poles(content)
        source_tokens = _bigrams(
            f"{getattr(src, 'title', '')} {getattr(src, 'content', '')}"
        )
        shared_poles = claim_poles.keys() & poles.keys()
        overlaps = len(claim_tokens & source_tokens) >= 2
        if not content:
            stance = "unresolved"
        elif overlaps and any(claim_poles[p] != poles[p] for p in shared_poles):
            stance = "conflicts"
        elif overlaps and (not has_conflict or shared_poles):
            stance = "supports"
        else:
            stance = "unresolved"
        items.append(
            {
                "source_id": sid,
                "title": getattr(src, "title", "") or "",
                "url": getattr(src, "url", None),
                "level": getattr(src, "level", ""),
                "doc_date": getattr(src, "doc_date", None),
                "fetched_date": getattr(src, "fetched_date", "") or "",
                **_snapshot_evidence(src),
                "stance": stance,
                "missing": not bool(content),
            }
        )
    for sid in _declared_source_ids(segment):
        if sid not in cited_ids:
            cited_ids.add(sid)
            items.append(
                {
                    "source_id": sid,
                    "title": "",
                    "url": None,
                    "level": "",
                    "doc_date": None,
                    "fetched_date": "",
                    "stance": "unresolved",
                    "missing": True,
                }
            )
    for r in getattr(segment, "extended_readings", None) or []:
        sid = r.get("source_id")
        if not sid or sid in cited_ids:
            continue
        cited_ids.add(sid)
        items.append(
            {
                "source_id": sid,
                "title": r.get("title", ""),
                "url": r.get("url"),
                "level": r.get("level", ""),
                "doc_date": None,
                "fetched_date": "",
                "stance": "context_only",
                "missing": False,
            }
        )
    return items


@dataclass
class DecisionRecord:
    """單筆審查決策:時間、理由、審查者與當時的 claim/evidence 指紋。"""

    decision_id: str
    argument_id: str
    decision: ReviewState
    reason_code: str = ""
    note: str = ""
    reviewer: str = "local"
    reviewed_at: str = ""
    claim_hash: str = ""
    evidence_hash: str = ""
    previous_decision_id: str | None = None
    revision_overlay: dict | None = None

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "argument_id": self.argument_id,
            "decision": self.decision.value,
            "reason_code": self.reason_code,
            "note": self.note,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "claim_hash": self.claim_hash,
            "evidence_hash": self.evidence_hash,
            "previous_decision_id": self.previous_decision_id,
            "revision_overlay": self.revision_overlay,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DecisionRecord":
        overlay = data.get("revision_overlay")
        if overlay is not None:
            if not isinstance(overlay, dict) or not isinstance(overlay.get("edited_text"), str):
                raise ValueError("Invalid revision overlay")
            for key in ("base_claim_hash", "evidence_hash", "edited_claim_hash"):
                if not isinstance(overlay.get(key), str) or not re.fullmatch(r"[a-f0-9]{64}", overlay[key]):
                    raise ValueError("Invalid revision overlay hash")
        return cls(
            decision_id=str(data["decision_id"]),
            argument_id=str(data["argument_id"]),
            decision=ReviewState(data["decision"]),
            reason_code=str(data.get("reason_code") or ""),
            note=str(data.get("note") or ""),
            reviewer=str(data.get("reviewer") or "local"),
            reviewed_at=str(data.get("reviewed_at") or ""),
            claim_hash=str(data.get("claim_hash") or ""),
            evidence_hash=str(data.get("evidence_hash") or ""),
            previous_decision_id=data.get("previous_decision_id"),
            revision_overlay=dict(overlay) if overlay is not None else None,
        )


class ReviewLedger:
    """追加式決策履歷:以 argument_id 為鍵,重審保留歷史並指回前一筆。"""

    def __init__(
        self,
        doc_fingerprint: str = "",
        records: list[DecisionRecord] | None = None,
    ) -> None:
        self.doc_fingerprint = doc_fingerprint
        self.records: list[DecisionRecord] = list(records or [])

    @classmethod
    def for_document(cls, doc: "CorrectionDoc") -> "ReviewLedger":
        return cls(doc_fingerprint=doc_fingerprint(doc))

    def records_for(self, argument_id: str) -> list[DecisionRecord]:
        return [r for r in self.records if r.argument_id == argument_id]

    def latest(self, argument_id: str) -> DecisionRecord | None:
        records = self.records_for(argument_id)
        return records[-1] if records else None

    def record(
        self,
        segment: "Segment",
        decision: ReviewState | str,
        *,
        reason_code: str = "",
        note: str = "",
        reviewer: str = "local",
        now: str | None = None,
        base_segment: "Segment | None" = None,
    ) -> DecisionRecord:
        """記錄一筆人工決策並綁定當前 claim/evidence 指紋。

        僅允許 REVIEWABLE_DECISIONS;STALE_REVIEW/UNREVIEWED 為衍生態。
        EDITED_ACCEPTED 缺省理由碼為 manual_edit。
        """
        if getattr(segment, "type", None) != "supplement":
            raise ValueError("只有 supplement/argument 可記錄審查決策")
        argument_id = getattr(segment, "argument_id", "") or ""
        if not argument_id.strip():
            raise ValueError("supplement 缺少 argument_id,無法建立決策綁定")
        decision = ReviewState(decision)
        if decision not in REVIEWABLE_DECISIONS:
            raise ValueError(
                f"decision {decision.value!r} 不是可記錄的人類決策"
                f"(允許: {sorted(d.value for d in REVIEWABLE_DECISIONS)})"
            )
        reason_code = reason_code or ""
        if not reason_code and decision == ReviewState.EDITED_ACCEPTED:
            reason_code = "manual_edit"
        if reason_code and reason_code not in REASON_CODES:
            raise ValueError(
                f"reason_code {reason_code!r} 非法(允許: {sorted(REASON_CODES)})"
            )
        reviewer = (reviewer or "").strip() or "local"
        reviewed_at = now or datetime.now(timezone.utc).isoformat()
        previous = self.latest(argument_id)
        overlay = None
        previous_overlay = previous.revision_overlay if previous is not None else None
        if base_segment is not None:
            if (
                getattr(base_segment, "argument_id", "") != argument_id
                or evidence_bundle_hash(base_segment) != evidence_bundle_hash(segment)
            ):
                raise ValueError("Manual edit must preserve the reviewed evidence and argument")
            if base_segment.text != segment.text:
                base_hash = claim_revision_hash(base_segment)
                if previous_overlay and base_hash == previous.claim_hash:
                    base_hash = previous_overlay["base_claim_hash"]
                overlay = {
                    "base_claim_hash": base_hash,
                    "evidence_hash": evidence_bundle_hash(segment),
                    "edited_text": segment.text,
                    "edited_claim_hash": claim_revision_hash(segment),
                }
        if overlay is None and previous_overlay and claim_revision_hash(segment) == previous.claim_hash:
            overlay = dict(previous_overlay)
            overlay["evidence_hash"] = evidence_bundle_hash(segment)
        decision_id = _sha(
            f"{self.doc_fingerprint}|{argument_id}|{decision.value}|"
            f"{reviewed_at}|{len(self.records)}"
        )[:16]
        rec = DecisionRecord(
            decision_id=decision_id,
            argument_id=argument_id,
            decision=decision,
            reason_code=reason_code,
            note=note or "",
            reviewer=reviewer,
            reviewed_at=reviewed_at,
            claim_hash=claim_revision_hash(segment),
            evidence_hash=evidence_bundle_hash(segment),
            previous_decision_id=(
                previous.decision_id if previous is not None else None
            ),
            revision_overlay=overlay,
        )
        self.records.append(rec)
        audit_event(
            logger,
            "claim_review_decision",
            argument_id,
            level=logging.INFO,
            decision=decision.value,
            reason_code=reason_code,
            reviewer=reviewer,
            decision_id=decision_id,
            previous_decision_id=rec.previous_decision_id,
        )
        return rec

    def apply_overlays(self, doc: "CorrectionDoc") -> "CorrectionDoc":
        """Replay edits only over the exact generated claim and evidence reviewed."""
        if self.doc_fingerprint != doc_fingerprint(doc):
            return doc
        segments = []
        changed = False
        for segment in doc.segments:
            record = self.latest(getattr(segment, "argument_id", ""))
            overlay = record.revision_overlay if record is not None else None
            if (
                segment.type == "supplement"
                and overlay
                and claim_revision_hash(segment) == overlay["base_claim_hash"]
                and evidence_bundle_hash(segment) == overlay["evidence_hash"]
            ):
                candidate = replace(segment, text=overlay["edited_text"])
                candidate_hash = claim_revision_hash(candidate)
                if candidate_hash == record.claim_hash == overlay["edited_claim_hash"]:
                    segment = candidate
                    changed = True
            segments.append(segment)
        return replace(doc, segments=segments) if changed else doc

    def revision_tokens(self, doc: "CorrectionDoc", segment: "Segment") -> dict[str, str]:
        """Bind a browser decision to document, claim, evidence and decision revisions."""
        document_revision = _sha(_canonical({
            "original": doc_fingerprint(doc),
            "segments": [
                {
                    "type": current.type,
                    "claim": claim_revision_hash(current),
                    "evidence": evidence_bundle_hash(current),
                }
                for current in doc.segments
            ],
        }))
        latest = self.latest(getattr(segment, "argument_id", ""))
        return {
            "document_revision": document_revision,
            "claim_revision": claim_revision_hash(segment),
            "evidence_revision": evidence_bundle_hash(segment),
            "decision_revision": latest.decision_id if latest is not None else "unreviewed",
        }

    def state_detail(self, segment: "Segment") -> dict:
        """有效審查狀態:舊決策的指紋與當前不符 → STALE_REVIEW(fail closed)。"""
        argument_id = getattr(segment, "argument_id", "") or ""
        rec = self.latest(argument_id)
        if rec is None:
            return {
                "argument_id": argument_id,
                "state": ReviewState.UNREVIEWED,
                "stale_reason": None,
                "record": None,
            }
        if rec.decision in EXPORTABLE_STATES and (
            not getattr(segment, "sources", None) or _missing_source_ids(segment)
        ):
            return {
                "argument_id": argument_id,
                "state": ReviewState.STALE_REVIEW,
                "stale_reason": "evidence_unavailable",
                "record": rec,
            }
        if rec.claim_hash != claim_revision_hash(segment):
            return {
                "argument_id": argument_id,
                "state": ReviewState.STALE_REVIEW,
                "stale_reason": "claim_changed",
                "record": rec,
            }
        if rec.evidence_hash != evidence_bundle_hash(segment):
            reason = (
                "evidence_unavailable"
                if _missing_source_ids(segment)
                else "evidence_changed"
            )
            return {
                "argument_id": argument_id,
                "state": ReviewState.STALE_REVIEW,
                "stale_reason": reason,
                "record": rec,
            }
        return {
            "argument_id": argument_id,
            "state": rec.decision,
            "stale_reason": None,
            "record": rec,
        }

    def state_of(self, segment: "Segment") -> ReviewState:
        return self.state_detail(segment)["state"]

    def queue_items(self, doc: "CorrectionDoc") -> list[dict]:
        """審查佇列卡片:claim、來源立場、驗證狀態與決策履歷。"""
        items: list[dict] = []
        for seg in getattr(doc, "segments", []) or []:
            if getattr(seg, "type", None) != "supplement":
                continue
            detail = self.state_detail(seg)
            items.append(
                {
                    "argument_id": getattr(seg, "argument_id", "") or "",
                    "revision_tokens": self.revision_tokens(doc, seg),
                    "state": detail["state"].value,
                    "stale_reason": detail["stale_reason"],
                    "claim": getattr(seg, "text", "") or "",
                    "confidence": getattr(seg, "confidence", "") or "",
                    "conflict_note": getattr(seg, "conflict_note", None),
                    "pending_evidence_reason": getattr(
                        seg, "pending_evidence_reason", ""
                    )
                    or "",
                    "citation_spans": [
                        dict(span)
                        for span in (getattr(seg, "citation_spans", None) or [])
                        if isinstance(span, dict)
                    ],
                    "sources": [
                        {
                            "source_id": getattr(s, "id", ""),
                            "title": getattr(s, "title", "") or "",
                            "url": getattr(s, "url", None),
                            "level": getattr(s, "level", ""),
                            "doc_date": getattr(s, "doc_date", None),
                            "fetched_date": getattr(s, "fetched_date", "") or "",
                            **_snapshot_evidence(s),
                        }
                        for s in getattr(seg, "sources", []) or []
                    ],
                    "source_stances": source_stances(seg),
                    "history": [
                        r.to_dict()
                        for r in self.records_for(
                            getattr(seg, "argument_id", "") or ""
                        )
                    ],
                }
            )
        return items

    def summary(self, doc: "CorrectionDoc") -> dict:
        """各狀態計數、待審數與下一個待審 argument_id。"""
        counts = {state.value: 0 for state in ReviewState}
        pending_values = {s.value for s in PENDING_STATES}
        next_pending: str | None = None
        for item in self.queue_items(doc):
            counts[item["state"]] += 1
            if next_pending is None and item["state"] in pending_values:
                next_pending = item["argument_id"]
        pending = sum(counts[s.value] for s in PENDING_STATES)
        return {
            **counts,
            "pending": pending,
            "total": sum(counts.values()),
            "next_pending_argument_id": next_pending,
        }

    def to_dict(self) -> dict:
        return {
            "schema": REVIEW_LEDGER_SCHEMA,
            "doc_fingerprint": self.doc_fingerprint,
            "records": [r.to_dict() for r in self.records],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewLedger":
        if not isinstance(data, dict):
            raise ValueError("Invalid review ledger object")
        raw_records = data.get("records", [])
        if not isinstance(raw_records, list) or any(
            not isinstance(record, dict) for record in raw_records
        ):
            raise ValueError("Invalid review ledger records")
        records = [
            DecisionRecord.from_dict(r) for r in raw_records
        ]
        return cls(
            doc_fingerprint=str(data.get("doc_fingerprint") or ""),
            records=records,
        )

    def save(self, path: Path | str) -> Path:
        """原子寫入(tmp + replace),避免半寫入的履歷檔。"""
        path = Path(path)
        # Reading an unknown ledger may safely reset review/export state, but
        # that fallback must not authorize destroying its existing history.
        if (path.exists() or path.is_symlink()) and self.load(path) is None:
            raise ReviewLedgerWriteConflict("無法辨識既有審查履歷,已保留原檔")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)
        return path

    @classmethod
    def load(cls, path: Path | str) -> "ReviewLedger | None":
        """載入履歷檔;不存在/毀損/schema 不符 → None。"""
        path = Path(path)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        schema = data.get("schema") if isinstance(data, dict) else None
        if not isinstance(schema, str) or schema not in {
            REVIEW_LEDGER_SCHEMA, LEGACY_REVIEW_LEDGER_SCHEMA,
        }:
            return None
        try:
            return cls.from_dict(data)
        except (KeyError, TypeError, ValueError):
            return None

    @classmethod
    def load_for_document(
        cls, path: Path | str, doc: "CorrectionDoc"
    ) -> "ReviewLedger":
        """重播同一文件的審查狀態;文件指紋不符 → 全新 ledger(fail closed)。"""
        fingerprint = doc_fingerprint(doc)
        ledger = cls.load(path)
        if ledger is None or ledger.doc_fingerprint != fingerprint:
            if ledger is not None:
                audit_event(
                    logger,
                    "review_ledger_fingerprint_mismatch",
                    fingerprint,
                    level=logging.INFO,
                    reason="ledger bound to a different document; starting fresh",
                )
            return cls.for_document(doc)
        return ledger


def is_exportable(segment: "Segment", ledger: "ReviewLedger | None") -> bool:
    """accepted-only 閘:有效 ACCEPTED/EDITED_ACCEPTED 決策且系統仍 verified。

    人類核准凌駕不了產品安全契約:pending_evidence(無合格來源)一律不進正式稿。
    """
    if ledger is None or getattr(segment, "type", None) != "supplement":
        return False
    if getattr(segment, "confidence", None) != "verified":
        return False
    return ledger.state_of(segment) in EXPORTABLE_STATES
