# Batch output sidecars

For an output such as `case.訂正稿.md`, the authoritative audit files are
`case.訂正稿.md.delivery_manifest.json` and
`case.訂正稿.md.binding_report.json` in the same directory. The receipt records
the input and output paths, their SHA-256 hashes, and the report path and hash.
Recovery verifies the report hash; metrics scanning and reruns use the matching
note-owned files. A receipt that states its own report identity never falls back
to the shared copy, so a note without a report reads as `metrics_unavailable`
instead of borrowing another note's report. If two input directories contain a note with the same stem,
the later output gets a stable source-path suffix so it cannot overwrite the
first note. Receipts also store canonical absolute input and output identities
so a change of working directory does not create a second output for the same
relative-path input. The report's canonical path is stored for recovery, and
metrics use the canonical input identity for a stable note ID.

## Authoritative versus compatibility copies

Note-owned receipts carry `"authoritative": true` and `"sidecar_scope": "output"`.
The directory-level `delivery_manifest.json` / `binding_report.json` files remain
as latest-output convenience copies, rewritten with `"authoritative": false`,
`"sidecar_scope": "directory_latest"`, and `sidecar_for_output` naming the output
they mirror. Readers prefer the note-owned pair and accept the directory-level
pair only for outputs that have no note-owned pair yet; a copy is never batch
evidence for an earlier output.

The marker scheme applies to delivery receipts only: the directory-level
`binding_report.json` is a raw copy of the latest report with no marker of its
own, so it can only be attributed through the receipt — a note-owned receipt
names its own report in `binding_report_path` / `binding_report_content_hash`,
and a legacy receipt without those fields may fall back to the copy. A receipt
that states no report of its own never does.

Receipts and their artifacts are bound by name, so moving or archiving an output
directory keeps a note resolvable: recovery then probes the sibling file beside
the receipt — the corrected note and its binding report, which live beside it —
and only when a recorded content hash exists and matches. A receipt copied onto
another note's name is still rejected while its recorded directory exists.

Copy policy:

- A delivered receipt always refreshes the copy.
- A failure receipt refreshes the copy only while the copy still belongs to the
  same note, so a failing note never replaces another note's latest delivery.
  Identity is compared by resolved path when both sides are absolute, and by
  file name only for a bare relative legacy identity; a relative identity that
  carries a directory component is never equal to an absolute one, so an
  ambiguous match preserves the existing copy.
- Recovery or a metrics rerun invoked with the directory-level path is routed to
  the matching note-owned receipt, which is what gets read and updated; the copy
  is recreated when it is absent and refreshed when it still names that output.
  A copy that was restored from a backup therefore cannot revert the note's
  recorded recovery state.
- Metrics scanning reads the note-owned receipts first, skips a directory-level
  copy whose declared output already has its note-owned receipt in the same
  scan, and deduplicates the rest by output identity. The improvement-report
  collector applies the same output-identity deduplication, preferring
  note-owned receipts because it globs them first. A relative identity counts
  together with the receipt's own directory, so two directories recording the
  same file name stay two notes.

## A later failed attempt

A receipt describes the note's latest attempt, so a failed re-run rewrites it —
but it never erases what the note has already recorded:

- `recovery_attempts` and `recovered_at` belong to the note, not to one attempt,
  and are carried into the failure receipt;
- the note's binding report identity is carried only while the note-owned report
  still hashes to the recorded value, so metrics stay bound to this note;
- the metrics of an earlier delivery are **not** carried: a failed note must not
  be counted as a successful delivery;
- the replaced receipt is archived once as `<output>.delivery_manifest.json.prev`
  (recorded in the receipt as `previous_receipt_archive`), so the delivered
  record survives. Archive files are not matched by any scan pattern.

## Ownership and compatibility rules

- Output naming reads ownership from the note's own receipt. A receipt filed
  under another note's output name is never treated as evidence for that note.
- A pre-upgrade output keeps its name while the directory-level copy still names
  it and its artifacts still exist; the next delivery into that directory first
  promotes the shared pair to the earlier note's own paths
  (`sidecars.migrate_legacy_sidecars`), so no note loses its evidence.
- Both candidate names — the plain and the source-suffixed one — are treated the
  same way: a name no receipt attributes to this input is never overwritten. The
  run is refused instead (exit code 1, a
  `delivery_receipt_not_written_name_collision` audit event, no receipt), because
  writing one would destroy the other note's evidence.
- Single-file runs behave as before, except that an unattributable
  `<stem>.訂正稿.md` already sitting beside the input is preserved and the note is
  written to a source-suffixed output; older directory-level sidecars stay
  readable.

## Note identity

Receipt-based metric records derive the note ID from the canonical input
identity, falling back to the recorded input path for legacy receipts written
before canonical paths existed, so IDs are stable across working-directory
changes for every note written by this version. The output-artifact scan that
fills `output_markdown_baseline.jsonl` keeps its own artifact-relative ID for
backwards compatibility with existing baseline files.

The shared `recovery_history.jsonl` records the receipt path, canonical input
identity, and input hash in each attempt so identical failures for different
notes remain separate even if an output filename is later reused.
