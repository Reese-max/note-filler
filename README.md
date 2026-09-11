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
# 1. Put your draft in data/draft.txt (or .docx)
# 2. Run the pipeline in dry-run mode — LLM/retrieval execute and the
#    corrected draft is printed, but NOTHING is written: no 訂正稿 file,
#    no binding report, no delivery receipt.
python -m note_filler data/draft.txt --dry-run --format md
# 3. The original at data/draft.txt is untouched. When you're satisfied,
#    run without --dry-run to write the real artifacts:
python -m note_filler data/draft.txt -o output/ --format md
#    → output/draft.訂正稿.md          補齊後的訂正稿
#    → output/binding_report.json     每個補充段的來源綁定（at_least_one_source 等檢查）
#    → output/delivery_manifest.json  交付回執（送達狀態 + polaris 品質指標）
```

## Segment model (what to look for in the output)

Every output document is a list of segments:

| Field | Values | Meaning |
|-------|--------|---------|
| `type` | `original` / `supplement` | `original` = text from your draft (untouched); `supplement` = AI-researched insertion |
| `confidence` | `verified` / `pending_evidence` | `verified` = has a bound source; `pending_evidence` = suggested but ungrounded — treat as draft, review before relying on it |
| `source_usage` (in `binding_report.json`) | per-segment | which `source_id`s back each supplement, plus `source_conflicts` when sources disagree |

The rule of thumb: `original` is yours; `supplement`+`verified` is
source-backed; `supplement`+`pending_evidence` is flagged degraded and must
not be treated as canonical without re-checking.

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
