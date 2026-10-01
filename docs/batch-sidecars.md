# Batch output sidecars

For an output such as `case.訂正稿.md`, the authoritative audit files are
`case.訂正稿.md.delivery_manifest.json` and
`case.訂正稿.md.binding_report.json` in the same directory. The receipt records
the input and output paths, their SHA-256 hashes, and the report path and hash.
Recovery verifies the report hash; metrics scanning and reruns use the matching
note-owned files. If two input directories contain a note with the same stem,
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

The marker scheme applies to delivery receipts. A binding report is bound to its
output through its note-owned filename and through the receipt's
`binding_report_path` / `binding_report_content_hash` fields.

Copy policy:

- A delivered receipt always refreshes the copy.
- A failure receipt refreshes the copy only while the copy still belongs to the
  same note, so a failing note never replaces another note's latest delivery.
- Recovery or a metrics rerun invoked with the directory-level path is routed to
  the matching note-owned receipt, which is what gets read and updated; the copy
  is recreated when it is absent and refreshed when it still names that output.
  A copy that was restored from a backup therefore cannot revert the note's
  recorded recovery state.
- Metrics scanning and the improvement-report collector read the note-owned
  receipts first, skip a directory-level copy whose declared output already has
  its note-owned receipt in the same scan, and deduplicate the rest by output
  identity (a relative identity counts together with the receipt's directory).

## Ownership and compatibility rules

- Output naming reads ownership from the note's own receipt. A receipt filed
  under another note's output name is never treated as evidence for that note.
- A pre-upgrade output keeps its name while the directory-level copy still names
  it and its artifacts still exist. When nothing attributes a name to any note,
  an existing output is left untouched and the note gets a source-suffixed
  output: an unattributable corrected note is never overwritten.
- Single-file runs are unchanged apart from the added sidecar files next to the
  output; older directory-level sidecars stay readable.

## Note identity

Receipt-based metric records derive the note ID from the canonical input
identity, falling back to the recorded input path for legacy receipts written
before canonical paths existed, so IDs are stable across working-directory
changes for every note written by this version. The output-artifact scan that
fills `metrics_history.jsonl` keeps its own artifact-relative ID for backwards
compatibility with existing history files.

The shared `recovery_history.jsonl` records the receipt path, canonical input
identity, and input hash in each attempt so identical failures for different
notes remain separate even if an output filename is later reused.