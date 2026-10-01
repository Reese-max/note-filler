# Note-Filler Legal/Admin Safety Contract

## Overview

This repository provides automated note-filling for legal, administrative, and examination purposes. The system extracts, validates, and supplements notes from various sources while preserving the integrity of the original content.

## Safety Contract

### Core Principles

1. **Source Integrity**: Only verified sources may contribute to the final note. Unverified or ambiguous inputs are flagged as pending evidence and excluded from the main text.

2. **Traceability**: Every supplemented claim must retain a machine-readable provenance link to its source. The system must not silently discard or overwrite source evidence.

3. **Per-Note Isolation**: Output artifacts (manifests, receipts, reports) must be scoped to individual notes. Batch operations must not collide — each note's evidence must remain independently auditable.

4. **Fail-Closed**: Missing or unknown sources result in pending evidence, not arbitrary defaults. The system must never promote unverified content to the main note body.

5. **Legal/Admin Compliance**: Notes involving law, regulation, or official examination content must flag jurisdiction-specific currency requirements. Local snapshots must be clearly marked as potentially stale.

### Contract Boundaries

- **P1 Issues** (critical): Source isolation (export global state), per-note evidence binding
- **P2 Issues** (onboarding/safety): Root README absent, batch sidecar collision, missing provenance
- **P3 Issues** (maintainability): CI job failures, test coverage gaps

### Onboarding

New maintainers must review this contract before modifying the pipeline. The root README serves as the entry point for the safety contract — all code changes must preserve or improve upon these guarantees.

### Related

- P1 #4: Global export isolation
- P2 #12: Batch sidecar overwrite failure
- P2 #1: Root README absence (this issue)
- P2 #3: Opportunity/workflow review
- P2 #9: Law currentness research

---

*This contract is reviewed as part of the 50-Persona Audit cycle. Open issues tracked in the repository represent outstanding findings from the audit.*