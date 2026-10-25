# Issue #11 — current source and temporary-vault recheck (2026-10-25)

This is a targeted source/runtime repair pass under the existing fixed A01–J05 protocol. It is **NOT CLEAN; 0/2 qualifying clean rounds**. The protocol/persona identities and success conditions are unchanged; this pass does not claim two independent full 50-persona rounds, human usability, live provider correctness, or deployment acceptance.

Inspected default baseline: `390184ae3168bce393c56363a5e8183c450e5550`. Product repair commit: `9c7d792` (the exact final head/tree and execution logs are retained separately in the round-2 issue-sweep evidence). PR #19 was already adapted to this main baseline; its historical Round 5 report and current-source correction are preserved through its existing head `08f3c9e2561cd172acd75b530c2c5872858de611`. No PR #20 content was used.

## Existing fingerprints on current main

The historical #1 README, #4 accidental shared-result export and #12 batch-sidecar collisions have current-source fixes. The README documents the local single-worker capability boundary; this is not authenticated shared deployment. Per-note output/manifest/report paths preserve separate delivery evidence. Those historical findings are not reimplemented or presented as still absent from main.

## New executed recovery boundaries and repairs

All reproductions use disposable synthetic `.txt` inputs and actual Markdown vault output, state JSON, sidecars and filesystem operations. The core parser/pipeline/export/recovery code is real; only LLM/search/law providers are replaced with offline responses. No personal vault, credential or live provider is read or changed.

| Current-main failure | Result after repair | Relevant fixed personas |
| --- | --- | --- |
| A corrupt state file is returned as absent, then overwritten by a fresh attempt. Unknown valid-JSON shapes can also lose attempt provenance. | Stop with a fixed content-safe error; preserve exact unknown bytes for manual recovery. | C05, D05, F04, I02, I03, I05 |
| `vault/a/b.txt` and `vault/a_b.txt` share the separator-replaced state filename; deep valid vault paths can exceed its filename limit. | Full source-key digest addresses; valid matching legacy history resumes without changing the old file, and a distinct legacy alias cannot inherit another note's attempts. | A03, C04, H01, H03, J01, J05 |
| Direct state writes can truncate existing history during interruption. | Write/flush/fsync a temporary sibling, then atomic replacement; failed replacement retains the old snapshot and leaves no temporary file. | B03, C05, I02, I05 |
| The CLI ignores the exhausted result and enters the real pipeline/provider again; a final RUNNING attempt can bypass the cap after interruption. | Enforce the existing 3-attempt cap before provider dispatch, keeping prior records and artifacts. | D04, I01, I02, I04, J03 |
| `recover_delivery({})` returns verified with zero artifact probes; invalid UTF-8 is not handled as a controlled refusal. | Incomplete identities/hash evidence or non-UTF8 receipts fail closed without replacing the original record. | A05, B04, C01, D01, D02, I02, I03 |
| Real LLM output producing duplicate angle questions is rejected by the actual quality gate after Markdown creation, but its task remains RUNNING without a failure reason. | Persist the exact current attempt's transmission failure; do not reclassify a previous attempt if a new reservation was never committed. | C05, D05, I03, I05 |

The positive control interrupts an actual pipeline through a mocked provider, resumes with seven offline responses, writes Markdown/binding/delivery evidence, retains the first failed attempt and immutable original input, then verifies the same output twice without changing bytes or dispatching a provider. With no real sources supplied, its supplement verified count stays zero.

## Executed checks and scope limits

- Untouched main baseline: `python -m pytest -q` — **1150 passed, 1 skipped, 12 integration cases deselected**.
- Current source focused state/CLI/delivery suite also covers incomplete receipts before any mutation, required original attempt timestamps, failure-phase retention across retries, and both directions of optional report identity/hash binding. The final full suite/compile/anti-leak command results are retained in the external exact-head receipt.
- Current regression tests are copied unchanged into an isolated main worktree for red-before proof; the successful offline pipeline control already passes on main while the faulty state/recovery boundaries fail.
- Formal commands: `python -m compileall -q src app tests scripts`, `python scripts/validate_deselection_ci.py`, `python -m pytest -q`.
- An explicitly invoked historical non-default file `ce87c16731108929-generation-transmission-recovery.py` has two stale failures already on untouched main: it edits the directory-level latest copy while recovery correctly follows authoritative note-owned receipts. Its positive helper also declares a binding-report path without writing that report or its expected hash, which the new incomplete-evidence gate correctly refuses. The normal current suite and current per-note regressions are the formal gate; this pass neither changes nor suppresses that historical file.

The specifically recognized pre-hash directory-level legacy format can still record missing-artifact failures and deduplicate their history. It cannot become verified without hash evidence. Partial note-owned receipts and declared reports missing either their identity or expected hash remain untouched for manual recovery; their absence is not an empty successful probe set.

No new live provider/official-law-currentness result is inferred. Shared deployment authentication, accessibility/browser/device scenarios, Windows/macOS execution and independent qualifying full audit rounds remain unperformed in this pass. Atomic file replacement does not establish multi-process writer ownership, cross-machine coordination or power-loss durability. These boundaries keep #11 open; a targeted software repair pass is not a clean audit verdict.
