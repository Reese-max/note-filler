# 50-Persona Audit — Round 4 (2026-09-19)

Run: `2026-09-19T20:08:20Z`

## Contract / inspected state

- Fixed-persona protocol blob: `6e3499d6ef5be7e123050e1526946f6a40f99263` (`Reese-max/autodev-ng/docs/portfolio-audit/2026-09-06-50-persona-audit.md`).
- Issue Quality v2 blob: `8167e10798071d2276addaff6b201c6b0e904a2a`.
- Inspected default branch: `main@9b579adb0391f9a96f620f2d58d4a7f0e420c4df`.
- The inspected HEAD is audit-only (`docs: record note-filler 50-persona round 3`); the last product-facing baseline remains `935b00113662942f9d700444de42d445ee6c8cea`.
- Fixed A01–J05 identities and baseline success conditions are unchanged. This is synthetic persona reasoning, not 50 human studies.
- Umbrella: #11. Existing actionable findings #1 and #4 remain open on default. #3 is opportunity/workflow work and #9 remains RESEARCH / NOT_ESTABLISHED.

## Change / issue / PR precheck

Current default still contains the process-global web export slot tracked by P1 #4. `app/server.py` resets and writes `app.state.last_doc` in `/run`; bare `/export` returns that process-global document without a request/result identity. Open PR #8 contains a candidate capability-based remediation and also covers #1, but it is not merged and therefore is not current-product evidence. PRs #5/#6/#7/#10 are likewise unmerged and were not counted as remediation.

No open/closed Issue, all-state PR, or branch matched the new batch-sidecar fingerprint before filing. New P2 #12 now tracks it. The finding is independent of #1/#4/#3/#9 and does not alter active PR scope.

## New actionable finding — #12

The CLI explicitly accepts multiple files/directories and an optional shared `--outdir`. Corrected note files are named per input stem, but the supporting audit artifacts are not:

- `write_delivery_receipt()` always writes `<output parent>/delivery_manifest.json` and explicitly replaces the previous receipt.
- `write_binding_report()` always writes `<output parent>/binding_report.json`.
- `main()` loops all expanded inputs through the same output directory and rewrites the manifest again after stdout delivery.
- `_load_output_metrics()` resolves both the manifest and binding report from `markdown_path.parent`, so multiple corrected Markdown files in one directory all consult the same last-written sidecars.
- `recovery.py` likewise defines the authoritative delivery manifest name as `delivery_manifest.json`.

Therefore note B overwrites note A's authoritative receipt/report in a supported batch path. Note A's corrected file can remain present while its own delivery/evidence sidecars are gone; later metrics/recovery cannot independently bind A to the original sidecars. This is `BUG / P2 / CONFIRMED / SOURCE_CONFIRMED / NEEDS_REVIEW / auto_implementation=false`, tracked in #12.

This is not raised to P1: no wrong corrected note content, live legal-user incident, privacy event, or production batch failure was observed. Runtime reproduction is still required with two fixture notes and stubbed providers.

Minimum change: keep the current artifact model, but make manifest/report paths output-specific (or use a small per-result directory), and make metrics/recovery resolve the sidecars belonging to that exact output. No database, queue, ledger service or general workflow framework is required.

## Other triage decisions

- The current TaskState store uses direct `Path.write_text()` and load-on-write semantics. Cross-process corruption/lost update is plausible, but this round did not establish that concurrent independent CLI processes are a supported/user-reachable workflow with P2 impact; no Issue was opened from that hypothesis.
- `async /run` invokes the synchronous pipeline directly, so long work can block the event loop. PR #8 already actively changes this path while fixing #4. This audit did not take over that active scope or create a duplicate finding; runtime concurrency impact remains unverified.
- #9's local-law currentness mismatch remains RESEARCH / NOT_ESTABLISHED. It is not promoted to a defect merely because an official corpus can change after the local snapshot.

## Runtime / CI boundary

Exact inspected HEAD `9b579adb0391f9a96f620f2d58d4a7f0e420c4df` has Actions run `34567359767`, completed `failure`. Jobs returned by GitHub are pinned 3.11 cancelled; latest 3.11/3.12/3.13 failed; pinned 3.12 failed; integration skipped. The connector exposes no recorded steps for those jobs, so this report does not infer a failed assertion, dependency error, billing state, or product-runtime defect from the run result.

No live Grok/Twinkle provider call, browser accessibility session, shared multi-user deployment, mobile/narrow-screen session, provider timeout/429/5xx injection, or two-note batch execution was performed in this audit. Those paths stay `NEEDS_RUNTIME_VERIFICATION` where applicable.

## Fixed 50-persona matrix

| Persona | Goal / input / steps | Expected → observed | Evidence | Grade / finding |
|---|---|---|---|---|
| A01 | First-time mobile user finds purpose/safety/start | 60-second entry contract → root README still absent on default | SOURCE_CONFIRMED | P2 #1 |
| A02 | Non-CLI student understands safe note completion | clear setup + provenance → contract remains buried in code/docs | SOURCE_CONFIRMED | P2 #1 |
| A03 | CLI-capable student processes multiple notes | each result remains independently auditable → fixed sidecars collide | SOURCE_CONFIRMED | P2 #12 |
| A04 | Time-pressured user completes one note | fast happy path → source path exists, current runtime receipt unavailable | STATIC + runtime gap | NEEDS_RUNTIME_VERIFICATION |
| A05 | User follows status/evidence | state belongs to current note → batch sidecars become last-writer-wins | SOURCE_CONFIRMED | P2 #12 |
| B01 | Office user starts without code reading | obvious README/path → missing root README | SOURCE_CONFIRMED | P2 #1 |
| B02 | Junior engineer installs/tests | CI should execute checks → current run failed with no step evidence | CI receipt boundary | VALIDATION_GAP; not product P1/P2 |
| B03 | User expects reversible outputs | note A evidence survives note B → report/receipt overwritten | SOURCE_CONFIRMED | P2 #12 |
| B04 | Research assistant verifies sources + export | own evidence/export only → web export global #4; batch evidence collision #12 | SOURCE_CONFIRMED | P1 #4 + P2 #12 |
| B05 | Fragmented/mobile web use | resumable accessible path → no mobile/runtime evidence | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| C01 | Public-sector user needs correctness/audit trail | each output traceable → global export #4 and batch sidecar loss #12 | SOURCE_CONFIRMED | P1 #4 + P2 #12 |
| C02 | Teacher/shared use | users never receive another result → current global export lacks identity | SOURCE_CONFIRMED | P1 #4 |
| C03 | High-risk source trust | authoritative currentness distinguishable → #9 experiment still pending | SOURCE_CONFIRMED gap | RESEARCH / NOT_ESTABLISHED #9 |
| C04 | Long workflow survives batch/retry | prior completed artifact keeps evidence → later batch item overwrites sidecars | SOURCE_CONFIRMED | P2 #12 |
| C05 | SRE expects fail-closed isolation | shared requests isolated + failures observable → #4 unresolved; CI cause unknown | SOURCE_CONFIRMED + runtime gap | P1 #4 |
| D01 | Manager reads delivery status | status corresponds to selected output → only latest directory receipt remains | SOURCE_CONFIRMED | P2 #12 |
| D02 | PM traces artifact responsibility | per-output receipt/report → batch sidecars not stable per output | SOURCE_CONFIRMED | P2 #12 |
| D03 | IT deploys service | shared deployment has ownership boundary → current export has none; actual shared deploy unproven | SOURCE_CONFIRMED | P1 #4; deployment runtime unknown |
| D04 | Cost-sensitive operator | bounded provider cost/fallback | no new cost failure established | STATIC | no new P0/P1/P2 |
| D05 | Compliance/audit user | retained evidence maps to exact note/user → #4/#12 break isolation/retention assumptions | SOURCE_CONFIRMED | P1 #4 + P2 #12 |
| E01 | Desktop novice completes web flow | understandable controls/error recovery | UI runtime not executed | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| E02 | Large-text desktop user | readable at larger scale | no browser zoom evidence | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| E03 | Low digital familiarity recovers mistakes | safe retry/clear state | static error paths exist; usability unexecuted | STATIC + runtime gap | no new P0/P1/P2 |
| E04 | Non-cloud user runs local CLI | local defaults understandable | onboarding blocker already #1 | SOURCE_CONFIRMED | P2 #1 |
| E05 | Long-reading user reviews result | sustained readability | no runtime/usability evidence | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| F01 | Older first-time user uses web | large obvious controls | no browser evidence | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| F02 | Low-vision user zooms to 200% | content remains usable | no zoom evidence | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| F03 | Low-precision user taps controls | targets remain usable | no touch evidence | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| F04 | Memory-sensitive user resumes | persistent state/evidence tied to one note | CLI state exists; batch evidence can be overwritten | SOURCE_CONFIRMED | P2 #12 |
| F05 | Assisted setup then daily use | documented repeatable operation | root README missing | SOURCE_CONFIRMED | P2 #1 |
| G01 | Keyboard-only web use | complete run/export by keyboard | not executed | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| G02 | Screen-reader user | meaningful labels/status | not executed | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| G03 | Color-limited user reads states | status not color-only | not executed | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| G04 | 200% zoom/narrow viewport | no clipped core action | not executed | UNKNOWN runtime | NEEDS_RUNTIME_VERIFICATION |
| G05 | Slow/high-latency network | long run remains responsive/recoverable | sync pipeline in async route is a candidate; active PR #8 owns path; no runtime | STATIC candidate | no duplicate; NEEDS_RUNTIME_VERIFICATION |
| H01 | Windows maintainer runs CLI | supported local file/state behavior | no current Windows execution receipt | STATIC | NEEDS_RUNTIME_VERIFICATION |
| H02 | macOS maintainer runs CLI | same workflow portable | no current macOS execution receipt | STATIC | NEEDS_RUNTIME_VERIFICATION |
| H03 | Linux/CI noninteractive | checks execute and identify failures | workflow defined, current jobs failed with steps unavailable | CI receipt boundary | VALIDATION_GAP |
| H04 | Self-host/shared deploy | result ownership isolated | current server global export breaks shared isolation | SOURCE_CONFIRMED | P1 #4 |
| H05 | New maintainer takes over | root contract + truth sources obvious | README absent; many deep docs exist | SOURCE_CONFIRMED | P2 #1 |
| I01 | Duplicate/repeated web actions | no cross-request mix-up | global last_doc remains last-writer-wins | SOURCE_CONFIRMED | P1 #4 |
| I02 | Process interrupted then recovery | exact artifact/evidence recovered | recovery hashes exist; per-dir manifest can be replaced in batch | SOURCE_CONFIRMED | P2 #12 |
| I03 | Invalid/wrong input | deterministic error without stale success | code has exceptions/failed receipts; no fresh executed fixture | STATIC | NEEDS_RUNTIME_VERIFICATION |
| I04 | Provider timeout/429/5xx | safe failure + recoverability | integration is dispatch-only and not run on inspected SHA | STATIC + runtime gap | NEEDS_RUNTIME_VERIFICATION |
| I05 | Partial success then retry | prior successful note remains independently auditable | later failure/success can overwrite directory receipt/report | SOURCE_CONFIRMED | P2 #12 |
| J01 | Large batch/directory input | every output keeps own evidence | fixed sidecar names collapse N outputs to latest pair | SOURCE_CONFIRMED | P2 #12 |
| J02 | Concurrent/multi-user web | per-user result authorization/isolation | global export state | SOURCE_CONFIRMED | P1 #4 |
| J03 | Long-running/resource pressure | service remains responsive/bounded | event-loop blocking candidate, no runtime; PR #8 active | STATIC candidate | no duplicate; NEEDS_RUNTIME_VERIFICATION |
| J04 | Privacy-sensitive user | one caller cannot fetch another note | no owner/result identity on current `/export` | SOURCE_CONFIRMED | P1 #4 |
| J05 | Expert automation/batch | artifacts machine-addressable per note | directory sidecars are not per-output | SOURCE_CONFIRMED | P2 #12 |

## Ten-dimension coverage

| Dimension | Round 4 result |
|---|---|
| First understanding | P2 #1 remains open; root README absent on default. |
| Core task | Static pipeline/output paths present; no current full runtime receipt. |
| Error recovery | Recovery/hash machinery exists, but batch receipt/report collision is P2 #12. |
| Data safety | P1 #4 remains on current source; no shared deployment incident claimed. |
| Observability | Per-run task/receipt structures exist; fixed directory sidecars undermine batch attribution (#12). |
| Accessibility/device | Browser keyboard/screen-reader/zoom/mobile paths remain unexecuted. |
| Performance/cost | No new qualified P2 cost/performance finding; long async-route blocking remains runtime-unverified and is touched by active PR #8. |
| Maintainability | CI workflow and extensive tests exist; exact current CI has failed jobs with no usable step evidence. |
| Failure injection | Source has error paths; timeout/429/5xx and two-note batch execution still need controlled runtime fixtures. |
| Trust | #4 export isolation, #12 per-note evidence binding, and #9 law-currentness research remain distinct. |

## Issue mapping / decisions

- #11 — umbrella tracker created after deduplication because this repo had no existing continuous 50-persona umbrella.
- #12 — NEW P2 BUG, batch sidecar overwrite/binding failure. `NEEDS_REVIEW`, `auto_implementation=false`.
- #4 — existing P1 BUG, still source-reproducible on default; no duplicate/update because active PR #8 owns remediation.
- #1 — existing P2 onboarding/safety-contract issue; active PRs #2/#6/#8 are unmerged.
- #3 — opportunity/review workflow; active PRs #7/#10; not treated as proven product defect.
- #9 — research on law snapshot freshness; remains `NOT_ESTABLISHED` pending bounded experiment.
- TaskState atomic/concurrency hypothesis — rejected for Issue creation this round: current supported reachability/P2 impact not established.

## CLEAN / continuation

**NOT CLEAN; 0/2 qualifying clean rounds.** New P2 #12 resets any streak, while P1 #4 and P2 #1 remain open and required runtime evidence is incomplete. The current source inspection cannot advance CLEAN.

Next safe verification for #12 is a non-destructive two-fixture local/CI test proving separate sidecars and first-note metrics/recovery after processing a second note. No external provider is required.
