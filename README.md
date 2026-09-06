# note-filler

> **Auto-fill research for legal / administrative / exam notes.**
> Original drafts are **immutable**, unsourced material **must not** enter
> canonical notes, and every accepted suggestion carries a citation.

This is a *read-and-suggest* tool, not an *overwrite* tool. It exists to help
someone filling out a long form / exam / administrative document draft by
proposing evidence-backed research snippets — which the user then has to accept
manually, with sources visible.

## What this is NOT

- Not a citation generator that fabricates. If the model doesn't have a real
  source, the suggestion is rejected at the gate; nothing crosses into the
  canonical file.
- Not an autocorrect of tone. Tone fixes only happen on user-accepted text.
- Not a replacement for the human's responsibility. The human **must** read and
  approve each insertion.

## Safety contract — the rule of three

| Role | Rule |
|------|------|
| **Reader / student** | Treat every suggestion as *draft*. The output file marks AI-researched text explicitly so a reviewer can spot it. |
| **Maintainer** | The pipeline writes only to `output/` and `metrics_output/`. The original document under `data/` is **read-only** in normal operation. A separate `recovery.py` module rebuilds state from logs if something interrupts in-flight work. |
| **Auditor** | Every accepted suggestion keeps a `source_url` and a `fetched_at` timestamp in the suggestion record. The `audit.py` module walks the suggestion log and emits a citation trail. |

If any of the three rules is violated, that's a release blocker. PRs that
weaken the contract must be flagged in the review.

## Repository layout

| Path | Purpose |
|------|---------|
| `app/` | FastAPI web UI (optional). The CLI in `__main__.py` works without it. |
| `data/` | **Authoritative inputs.** Original drafts go here. Read-only during normal runs. |
| `output/` | **Generated.** AI-researched suggestions, evidence, formatted drafts. Safe to delete and regenerate. |
| `metrics_output/` | **Generated.** Quality metrics snapshots. Safe to delete and regenerate. |
| `src/note_filler/` | Library code (pipeline, parse, llm, citation, audit, recovery, …). |
| `tests/` | Unit + integration tests. Integration tests need a running Grok provider on `localhost:8318`. |
| `docs/` | Auxiliary documentation. |
| `scripts/` | One-off driver scripts. |
| `pyproject.toml`, `requirements-lock.txt`, `constraints-pinned.txt` | Python packaging and pinned dependency universe. |

## Generated vs authoritative

| Kind | Path | Source of truth |
|------|------|-----------------|
| **Authoritative** | `data/*` | The user's original draft. Never overwritten by the pipeline. |
| **Authoritative** | `pyproject.toml` | Human-edited. |
| **Generated** | `output/*` | The pipeline. May be deleted and re-derived. |
| **Generated** | `metrics_output/*` | The metrics step. May be deleted and re-derived. |
| **Logs** | wherever the pipeline writes them | Append-only. |

`metrics_output/` and `output/` should be in `.gitignore` if they ever get
checked in by accident — the rule is "do not commit generated artifacts".

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate     # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -m "not integration"   # unit tests only; skip the Grok-requiring tests
```

To run the integration tests you need a local Grok provider listening on
`localhost:8318`. The CI runs unit tests only.

## End-to-end example (read-only / dry-run path)

```bash
# 1. Put your draft in data/draft.docx (or .md)
# 2. Run the pipeline in dry-run mode — it produces suggestions but writes
#    nothing into your draft.
python -m note_filler.pipeline run --input data/draft.docx --dry-run --out output/run-2026-09-06
# 3. Inspect the output:
#    output/run-2026-09-06/suggestions.json   ← every suggested insertion, with source_url
#    output/run-2026-09-06/citations.md      ← human-readable bibliography
#    output/run-2026-09-06/diff.md           ← what *would* change, marked as insertions
# 4. The original at data/draft.docx is untouched. To accept suggestions, run
#    without --dry-run and confirm each one interactively.
```

The four-state model embedded in every output:

| State | Description |
|-------|-------------|
| `original` | Was in your draft at start of run. Untouched. |
| `researched` | Suggested by the model, awaiting your review. Marked in the diff. |
| `source-backed` | Suggested **and** has a real `source_url`+`fetched_at`. Eligible for acceptance. |
| `pending` | Suggested without a source. **Cannot** be accepted silently — must be re-fetched or dropped. |
| `final` | Accepted by you. Marked with acceptance timestamp. |

Anything not in `original` is in one of the other four. The diff makes that
visible.

## Provider boundaries

The default LLM provider is a local Grok daemon. We do not ship API keys. CI
**must not** make outbound calls to commercial LLM providers. The
`requirements-lock.txt` pins only first-party-acceptable dependencies.

## License & contribution

The repository has no `LICENSE` file committed yet; until one is added, the
default is **all-rights-reserved by the maintainers**. PRs should:

- Touch only one thing per PR.
- Include the issue number in the commit footer (`Refs #N`).
- Pass `pytest -m "not integration"` locally.
- Not weaken the safety contract.

Open an issue for proposed contract changes before sending the PR.
