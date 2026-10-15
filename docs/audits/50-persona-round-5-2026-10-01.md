# 50-Persona Audit — Round 5 (2026-10-01)

Run: `2026-10-01T05:16:37Z`

## Contract / inspected state

- Fixed-persona protocol blob: `6e3499d6ef5be7e123050e1526946f6a40f99263` (`Reese-max/autodev-ng/docs/portfolio-audit/2026-09-06-50-persona-audit.md`, unchanged since Round 4).
- Issue Quality v2 blob: `8167e10798071d2276addaff6b201c6b0e904a2a` (unchanged since Round 4).
- Inspected default branch: `main@e8057ad815fc18dfd20aeea5e2e3c76d56925b3b`.
- The inspected HEAD is audit-only (`docs: record note-filler fixed50 round 4`); the last product-facing baseline remains `935b00113662942f9d700444de42d445ee6c8cea`. `git diff 935b001..e8057ad` touches only `docs/audits/50-persona-round-{1,2,3,4}-*.md`.
- Fixed A01–J05 identities and baseline success conditions are unchanged. This is synthetic persona reasoning, not 50 human studies.
- Umbrella: #11. Its body still names `9b579ad…` as the inspected HEAD; the actual current default tip is `e8057ad…`, so the umbrella text lags one round. This report does not edit the issue body.
- Existing actionable findings remain open on default: P2 #1, P1 #4, P2 #12. #3 is opportunity/workflow work and #9 remains RESEARCH / NOT_ESTABLISHED.

## Change / issue / PR precheck

Current default still contains all three previously confirmed fingerprints:

- P1 #4 — `app/server.py` keeps one process-global `app.state.last_doc`: `/run` clears it (line 50), assigns it (line 57), and bare `GET /export` (lines 95–106) returns that document with no result/session/owner identity.
- P2 #12 — batch sidecars still use fixed names: `MANIFEST_NAME = "delivery_manifest.json"` (`src/note_filler/__main__.py:35`), `BINDING_REPORT_NAME = "binding_report.json"` (`src/note_filler/binding_report.py:40`), the matching `DELIVERY_MANIFEST_NAME = "delivery_manifest.json"` in `src/note_filler/recovery.py:29`, and directory-level sidecar resolution in `src/note_filler/metrics_pipeline.py` (`markdown_path.parent / "delivery_manifest.json"` at line 228; `binding_report.json` sibling lookup at line 1169). Multiple notes delivered into one directory still collapse to the last-written manifest/report pair.
- P2 #1 — the repository root still has no `README*` entry point exposing the safety contract.

No open/closed Issue or all-state PR matched a new distinct fingerprint before filing, and no new P0/P1/P2 finding is promoted this round: the inspected product source is identical to the Round-4 inspection, and no previously-unseen reproducible candidate passed the deduplication and Issue Quality v2 gates.

Unmerged remediation PRs exist for every open actionable finding but are not current-product evidence: #2/#6/#8/#16/#17 target #1; #5/#8/#15 target #4; #13/#18 target #12; #7/#10/#14 target #3. PRs #13–#18 are new since Round 4; none are merged.

## Other triage decisions

- The TaskState store still uses direct `Path.write_text()` with load-on-write semantics. As in Round 4, concurrent independent CLI processes with supported P2 reachability are not established; no Issue opened from that hypothesis.
- `async /run` still invokes the synchronous pipeline directly (event-loop blocking candidate). Unmerged PRs #5/#8/#15 actively own the export path for #4; this audit does not take over that scope or file a duplicate.
- #9's local-law currentness question remains RESEARCH / NOT_ESTABLISHED; an official corpus changing after a local snapshot is not by itself a defect.

## Runtime / CI boundary

Default-branch push Actions run `35466539176` for inspected SHA `e8057ad815fc18dfd20aeea5e2e3c76d56925b3b` completed `failure`. Jobs: `test (pinned 3.11)`, `test (latest 3.11)`, `test (latest 3.12)` failed; `test (pinned 3.12)` and `test (latest 3.13)` were cancelled; `integration` was skipped. The GitHub jobs API returns no recorded steps for these jobs, so this report does not infer a failed assertion, dependency error, billing state, or product-runtime defect from the run result.

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
| G05 | Slow/high-latency network | long run remains responsive/recoverable | sync pipeline in async route is a candidate; unmerged PRs #5/#8/#15 own path; no runtime | STATIC candidate | no duplicate; NEEDS_RUNTIME_VERIFICATION |
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
| J03 | Long-running/resource pressure | service remains responsive/bounded | event-loop blocking candidate, no runtime; unmerged PRs #5/#8/#15 own path | STATIC candidate | no duplicate; NEEDS_RUNTIME_VERIFICATION |
| J04 | Privacy-sensitive user | one caller cannot fetch another note | no owner/result identity on current `/export` | SOURCE_CONFIRMED | P1 #4 |
| J05 | Expert automation/batch | artifacts machine-addressable per note | directory sidecars are not per-output | SOURCE_CONFIRMED | P2 #12 |

## Ten-dimension coverage

| Dimension | Round 5 result |
|---|---|
| First understanding | P2 #1 remains open; root README absent on default. |
| Core task | Static pipeline/output paths present; no current full runtime receipt. |
| Error recovery | Recovery/hash machinery exists, but batch receipt/report collision is P2 #12. |
| Data safety | P1 #4 remains on current source; no shared deployment incident claimed. |
| Observability | Per-run task/receipt structures exist; fixed directory sidecars undermine batch attribution (#12). |
| Accessibility/device | Browser keyboard/screen-reader/zoom/mobile paths remain unexecuted. |
| Performance/cost | No new qualified P2 cost/performance finding; long async-route blocking remains runtime-unverified and is touched by unmerged PRs #5/#8/#15. |
| Maintainability | CI workflow and extensive tests exist; exact current CI run `35466539176` failed with no usable per-job step evidence. |
| Failure injection | Source has error paths; timeout/429/5xx and two-note batch execution still need controlled runtime fixtures. |
| Trust | #4 export isolation, #12 per-note evidence binding, and #9 law-currentness research remain distinct. |

## Issue mapping / decisions

- #11 — umbrella tracker; this report is Round 5 under the same fixed protocol.
- #4 — existing P1 BUG, still source-reproducible on default; no duplicate because unmerged PRs #5/#8/#15 already own remediation.
- #1 — existing P2 onboarding/safety-contract issue; unmerged PRs #2/#6/#8/#16/#17.
- #12 — existing P2 BUG, still source-reproducible on default; unmerged PRs #13/#18.
- #3 — opportunity/review workflow; unmerged PRs #7/#10/#14; not treated as proven product defect.
- #9 — research on law snapshot freshness; remains `NOT_ESTABLISHED` pending bounded experiment.
- TaskState atomic/concurrency hypothesis — rejected again for Issue creation: supported reachability/P2 impact still not established.
- No new Issue filed this round.

## CLEAN / continuation

**NOT CLEAN; 0/2 qualifying clean rounds.** P1 #4, P2 #1 and P2 #12 remain open on default and required runtime evidence is incomplete; the streak has not started. Round 5 produced no new P0/P1/P2 finding, but CLEAN requires resolved findings plus two consecutive qualifying rounds — it does not begin while known P1/P2 defects remain open.

Next safe verification remains non-destructive: a two-fixture local/CI test proving per-note sidecars and first-note metrics/recovery after processing a second note (#12), plus a two-client `/run`→`/export` isolation fixture for #4. No external provider is required for either.
