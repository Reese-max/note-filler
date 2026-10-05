# Offline law snapshot currentness

Local law search reads a database snapshot. Searching it today does not mean it
was fetched today or that its text is current. Legacy `data/law_index.db` therefore
returns `fetched_date: null`, `currentness: unknown`, the database SHA-256, and a
separate `queried_at` date. Level A describes the source's official origin; it
cannot establish current legal authority without article-level comparison.
Unknown and stale snapshot sources remain visible and citable, but neither they
nor multiple unproven articles can make a supplement `verified`.

A local operator can provide `<database-stem>.provenance.json` beside the SQLite
file. This is an offline evidence input, not an automatic updater or a signed
attestation. Do not invent dates or text hashes. Record the exact official article
text observed, retain the source capture, and calculate its hash with
`note_filler.retrieve.law_currentness.text_sha256`, which removes only whitespace.
The whole-database hash binds proof to this snapshot; each article still needs its
own dated official comparison. `snapshot_fetched_date` is optional and describes
actual corpus acquisition, not database modification, Git commit, or query time.

```json
{
  "schema": "note_filler.law_snapshot.v1",
  "snapshot_sha256": "<sha256 of the database bytes>",
  "snapshot_fetched_date": null,
  "articles": {
    "C0000001:80": {
      "official_url": "https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=C0000001&flno=80",
      "verified_at": "<actual official comparison ISO date>",
      "official_text_sha256": "<sha256 of official text without whitespace>"
    }
  }
}
```

A matching article is `verified` only when the official comparison is at most
30 days old, not future-dated, and names the exact MOJ article URL. A substantive
text mismatch is `stale`. Missing, oversized (>256 KiB), malformed, expired,
incorrectly bound, or invalid proofs remain `unknown`. No whole-corpus freshness
claim follows from verifying one unchanged article. Refreshing a proof changes the
human-review evidence fingerprint; prior acceptance must be reviewed again when
that evidence changes. JSON, citation exports, and the review UI disclose unknown
fetch dates and currentness separately.

The saved public MOJ fixtures compare current Criminal Code Article 80 (a local
snapshot is missing its final paragraph) and unchanged Article 81. Tests exercise
legacy unknown custody, stale Article 80 without poisoning its unchanged control,
a positive current-version database, expired/malformed/drifted proofs, unchanged
original notes, correction/cross-validation confidence, and review fingerprint
invalidation. Fixture capture time is historical evidence; runtime tests date
fresh comparisons explicitly and do not pretend to re-fetch MOJ.

This repair does not update the legal corpus, determine applicability/effective
dates, call a provider, or attest to all current law. Research issue #9's public
source comparison is recorded separately in research PR #22.
