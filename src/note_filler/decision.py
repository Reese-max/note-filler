"""Claim-level review decision: Verify / Accept / Reject, with decision history.

Provides:
- ReviewDecision: Three-level decision enum for claim verification status.
- decide_review(): Map a verify.Validation to a ReviewDecision.
- DecisionRecord: Persist a single decision with timestamp, reason, and audit trail.
- audit_decision(): Write a machine-readable audit event for each decision.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from note_filler.retrieve.models import Source
from note_filler.verify import Validation


class ReviewDecision(str, Enum):
    """Three-level review decision for a claim."""

    VERIFY = "verify"
    ACCEPT = "accept"
    REJECT = "reject"


@dataclass
class DecisionRecord:
    """A single decision record with full audit trail."""

    claim: str
    decision: ReviewDecision
    validation: Validation
    reason: str
    decided_at: str
    decision_id: str

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "decision": self.decision.value,
            "validation": asdict(self.validation),
            "reason": self.reason,
            "decided_at": self.decided_at,
            "decision_id": self.decision_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DecisionRecord:
        """Restore evidence snapshots; reject non-boolean validation flags."""
        validation = data["validation"]
        if any(type(validation[key]) is not bool for key in ("verified", "conflict")):
            raise ValueError("validation verified and conflict must be booleans")
        return cls(
            claim=data["claim"],
            decision=ReviewDecision(data["decision"]),
            validation=Validation(
                claim=validation["claim"],
                sources=[Source(**source) for source in validation.get("sources", [])],
                verified=validation["verified"],
                conflict=validation["conflict"],
                conflict_note=validation.get("conflict_note"),
            ),
            reason=data["reason"],
            decided_at=data["decided_at"],
            decision_id=data["decision_id"],
        )


def decide_review(validation: Validation) -> ReviewDecision:
    """Map a cross_validate Validation to a ReviewDecision.

    Logic:
      - verified=False  → REJECT (claim cannot be grounded)
      - verified=True,  conflict=True  → VERIFY (verified but conflict marked, needs human review)
      - verified=True,  conflict=False → ACCEPT (verified and clean, acceptable)
    """
    if not validation.verified:
        return ReviewDecision.REJECT
    if validation.conflict:
        return ReviewDecision.VERIFY
    return ReviewDecision.ACCEPT


def _generate_decision_id(claim: str) -> str:
    return hashlib.sha256(claim.encode("utf-8")).hexdigest()[:12]


def audit_decision(logger, record: DecisionRecord) -> None:
    """Write a machine-readable JSON audit event for the decision."""
    logger.log(
        logging.INFO,
        json.dumps(
            {
                "event": "claim_review_decision",
                "decision_id": record.decision_id,
                "claim": record.claim,
                "decision": record.decision.value,
                "reason": record.reason,
                "decided_at": record.decided_at,
                "verified": record.validation.verified,
                "conflict": record.validation.conflict,
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ),
    )
