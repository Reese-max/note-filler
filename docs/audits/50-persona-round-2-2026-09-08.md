# 50-Persona Audit — Round 2

Date: 2026-09-08
Protocol: `Reese-max/autodev-ng/docs/portfolio-audit/2026-09-06-50-persona-audit.md`
Default branch: `main`
Audited SHA: `04b310947e0dde32904df2b32e69a304d43c0494`
Relevant product-code base: `935b00113662942f9d700444de42d445ee6c8cea` (the audited head adds only the Round-1 audit document)

> Fixed 50-persona model simulation plus current default-branch repository/CI evidence. This is not a 50-human study. Static control-flow evidence is not represented as live provider, browser, shared-deployment, or production validation.

## Result

Status: **NOT CLEAN**

Round 2 confirms the existing P2 #1 remains unresolved and adds one reproducible P1:

- **#4 — P1: process-global web export state can return the wrong client's legal/administrative note.**

The Round-2 finding resets the two-consecutive-no-new-P0/P1/P2 counter.

## Current open audit findings

### P2 #1 — root safety/operating contract still missing

The repository still has no root `README.md`. The product identity and safety constraints exist in `pyproject.toml` and deeper specs, but A02/C01/D05/H05/J04 cannot derive the canonical setup, provider boundary, immutable-original rule, provenance/recovery path, and end-to-end safe workflow from the repository landing page alone.

Tracking: #1 — `[P2][50-persona audit] Add a root README for the legal/admin note-filling safety contract`.

### P1 #4 — global `app.state.last_doc` mixes client export authority

`app/server.py` implements the web flow with one application-global slot:

```python
app = FastAPI(title="筆記補齊")
app.state.last_doc = None

@app.post("/run")
async def run(...):
    app.state.last_doc = None
    ...
    doc = run_pipeline(...)
    app.state.last_doc = doc

@app.get("/export")
def export():
    doc = app.state.last_doc
```

There is no session/result identifier or ownership check around `/export`. The interface contract explicitly defines `last_doc` as the cross-request cache, and the server tests validate only one client's `/run` followed by `/export`.

Deterministic scenario:

1. Client A completes `/run` for note A.
2. The process-global `last_doc` now points to A's `CorrectionDoc`.
3. Client B calls `/export` without uploading a document or presenting a result/session capability.
4. B receives whichever document is currently in `last_doc`.
5. If A and B run concurrently, the last assignment wins globally; an export can therefore return the other request's note.

This is classified **P1** under the portfolio rubric because it can make the core export task return a materially wrong legal/administrative document and, if more than one person can reach the same FastAPI process, disclose one caller's note to another. It is not escalated to P0 in this round because repository evidence does not establish that a shared/public deployment currently exists.

Tracking: #4 — `[P1][50-persona audit] Isolate web export state so one client cannot receive another client's note`.

## Fixed 50-persona rerun

The same persona IDs were retained. This repository's primary task is interpreted as: understand the product boundary → submit an original note → inspect source-backed supplements and pending evidence → export the intended corrected note without losing provenance or mixing another request's state.

### A — students 16–22

- **A01**: onboarding still partial because no root README provides the shortest safe path.
- **A02**: fail/partial on entry contract (#1); deeper specs are not a substitute for a landing-page workflow.
- **A03**: can inspect code/specs, but current red CI prevents treating default-branch verification as healthy.
- **A04**: export path is statically simple, but correctness cannot be trusted under overlapping runs (#4).
- **A05**: result presentation has source/provenance structure in tests/specs; actual visual usability remains runtime-pending.

### B — early-career 23–30

- **B01/B02/B03**: setup/recovery remains partial due #1 and absent executed web-flow evidence.
- **B04**: **fail** for research-note isolation: a second request can receive another result through global `last_doc` (#4).
- **B05**: interrupted/repeated browser use remains runtime-pending; global state raises wrong-export risk if another run occurs.

### C — professional 31–40

- **C01**: **fail** trust/correctness boundary because a legal/public-service note export can be replaced by another request's result (#4).
- **C02**: multi-learner/shared-host usage cannot be treated as isolated (#4).
- **C03**: provenance mechanisms exist, but actual provider/output safety is not revalidated by live execution here.
- **C04**: long-flow persistence/recovery remains unverified; `last_doc` disappears on restart.
- **C05**: red CI and global in-process result state keep reliability verification incomplete.

### D — management/decision 41–50

- **D01/D02**: evidence/reporting is present but no current successful CI receipt supports a release-ready claim.
- **D03**: **fail/partial** because deployment trust boundary is undocumented and web result isolation is absent (#1/#4).
- **D04**: provider cost behavior remains runtime/config pending; no new cost defect promoted this round.
- **D05**: **fail** because result ownership/privacy is not represented in the `/export` contract (#4).

### E/F — older and assisted users

- **E01–E05/F01–F05**: static templates/specs do not establish font, zoom, keyboard, assistive or interruption usability. No new static P0/P1/P2 is promoted from this group this round; runtime evidence is still required.

### G — accessibility/constraint scenarios

- **G01–G05**: no actual browser/accessibility/slow-network run was performed in this continuation. These scenarios remain unverified rather than passed.

### H — technical/operations

- **H01–H05**: source structure and CI workflow exist, but root onboarding #1 remains open. Current Actions for audited SHA is red, so setup/test claims cannot be marked passed from repository presence alone.

### I — stress/failure modes

- **I01**: **fail** under overlapping/repeated runs because one global result slot is shared (#4).
- **I02**: restart/recovery remains unverified; `last_doc` is process memory and intentionally disappears on restart.
- **I03/I04**: malformed/provider-failure behavior was not re-executed; no new issue promoted without stronger evidence.
- **I05**: **fail/partial** because partial/concurrent workflows can leave `/export` pointing at a different request's latest success (#4).

### J — advanced/boundary scenarios

- **J01**: large-input behavior not executed.
- **J02**: **fail** multi-client/concurrency isolation (#4).
- **J03**: long-running process/restart behavior remains runtime-pending.
- **J04**: **fail** privacy-sensitive use because `/export` has no result ownership boundary (#4).
- **J05**: **fail/partial** automated/custom callers cannot deterministically bind an export to the run that produced it (#4).

## CI / runtime evidence boundary

GitHub Actions run `33989418673` for audited SHA `04b310947e0dde32904df2b32e69a304d43c0494` completed with conclusion **failure**.

The jobs API shows the matrix reached `Run tests (skip integration; includes substitute coverage)`. At least the pinned Python 3.12 and latest Python 3.12 jobs failed there; other matrix jobs were cancelled after the matrix failure. The anti-leak gate steps shown in the jobs response completed successfully before the test step.

This report does **not** infer the exact failing assertion because the failure logs were not established here. It also does not claim that Grok, Twinkle, the FastAPI web server, a browser, a multi-client deployment, or integration tests passed.

## Required next gates

1. Resolve #1 or explicitly disposition it under the protocol.
2. Resolve #4 by binding export results to the originating request/session/capability and add cross-client/concurrency tests.
3. Restore a green current-default CI run and preserve evidence for the full non-integration test matrix.
4. Execute the relevant web happy path, failed-run recovery, two-client isolation, concurrent-run isolation, and restart/expiry scenarios.
5. Re-run the same fixed 50 personas on the merged remediation SHA.
6. Only after all P0/P1/P2 are resolved/dispositioned, required runtime paths have evidence, and two consecutive rounds produce no new P0/P1/P2 may this repository be marked `CLEAN`.
