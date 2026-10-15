"""Tests for claim-level review decision: Verify / Accept / Reject."""

from __future__ import annotations

import pytest

from note_filler.decision import ReviewDecision, decide_review, DecisionRecord, _generate_decision_id
from note_filler.verify import Validation, cross_validate
from note_filler.retrieve.models import Source


def _ms(id: str, title: str, url: str | None, level: str, content: str = "") -> Source:
    """Test Source factory, matching the style of tests/test_verify.py."""
    return Source(
        id=id,
        title=title,
        url=url,
        level=level,
        content=content,
        fetched_date="2026-07-15",
        doc_date=None,
        distance=0.5,
    )


def _make_validation(claim: str, sources: list, *, verified: bool, conflict: bool, conflict_note: str | None = None) -> Validation:
    """Helper to build a Validation without calling cross_validate."""
    return Validation(
        claim=claim,
        sources=sources,
        verified=verified,
        conflict=conflict,
        conflict_note=conflict_note,
    )


def test_decide_review_verified_with_conflict()-> None:
    sources = [_ms("s1", "來源甲", "https://a.example/1", "A", content="得"),
               _ms("s2", "來源乙", "https://b.example/2", "B", content="不得")]
    v = _make_validation("納稅義務人得否申請延期", sources, verified=True, conflict=True, conflict_note="衝突標記")
    decision = decide_review(v)
    assert decision == ReviewDecision.VERIFY


def test_decide_review_verified_no_conflict()-> None:
    sources = [_ms("s1", "來源甲", "https://a.example/1", "A", content="應以書面為之"),
               _ms("s2", "來源乙", "https://b.example/2", "B", content="以書面為之")]
    v = _make_validation("行政處分應以書面為之", sources, verified=True, conflict=False)
    decision = decide_review(v)
    assert decision == ReviewDecision.ACCEPT


def test_decide_review_not_verified()-> None:
    sources = [_ms("s1", "單一來源", "https://b.example/1", "B", content="主張成立。")]
    v = _make_validation("主張成立", sources, verified=False, conflict=False)
    decision = decide_review(v)
    assert decision == ReviewDecision.REJECT


def test_decision_record_to_from_dict()-> None:
    sources = [_ms("s1", "來源甲", "https://a.example/1", "A", content="得")]
    v = _make_validation("test claim", sources, verified=True, conflict=True)
    rec = DecisionRecord(claim="test claim", decision=ReviewDecision.ACCEPT, validation=v, reason="clean", decided_at="2026-07-15", decision_id="hack123")
    d = rec.to_dict()
    rec2 = DecisionRecord.from_dict(d)
    assert rec2.claim == rec.claim
    assert rec2.decision == rec.decision
    assert rec2.reason == rec.reason
    assert rec2.decided_at == rec.decided_at
    assert rec2.decision_id == rec.decision_id


def test_generate_decision_id()-> None:
    """Decision ID should be deterministic and short."""
    id1 = _generate_decision_id("same claim")
    id2 = _generate_decision_id("same claim")
    id3 = _generate_decision_id("different claim")
    assert id1 == id2  # deterministic
    assert id1 != id3  # different content yields different ID
    assert len(id1) == 12  # truncated to 12 chars