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

The older `delivery_manifest.json` and `binding_report.json` files remain as
latest-output compatibility copies. They are **not** batch-wide evidence and
must not be used to inspect an earlier output. Readers prefer the note-owned
pair when present and accept the directory-level pair only for older outputs.
The metrics collector skips a directory-level copy when its note-owned receipt
is in the same scan, so one delivery is counted once.
When recovery or a metrics rerun is invoked with the latest-output copy, it
reads that requested copy, updates the matching note-owned receipt, and refreshes
the latest-output copy.
The shared `recovery_history.jsonl` records the note-owned receipt path in
each attempt so identical failures for different notes remain separate.
