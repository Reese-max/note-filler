# Local law snapshot currentness — Issue #9

Decision: **BUILD**, confined to source provenance and currentness semantics.

On 2026-10-05, two public Ministry of Justice article pages were retrieved over HTTPS. Criminal Code Article 80 differs from the checked-in SQLite corpus: the official page contains an additional paragraph excluding time before the victim turns twenty for its enumerated offenses. The local row ends at the preceding paragraph. Article 81, the unchanged control, matches the official deleted-article text after whitespace normalization. This is a textual comparison, not an independent legal interpretation or advice about applicability.

The DB blob was last committed on 2026-07-15. That is repository custody evidence, **not proof of the corpus's fetch/import date**. Neither the DB schema nor the retrieved Source carries a snapshot, revision, effective-date, or authority-currentness field.

The actual `LawLookup.search_articles`, `search_law_sources`, `is_stale`, `cross_validate`, and `assemble_correction` paths were replayed with this real DB. A fixed keyword extractor and article filter replaced provider-dependent query selection; they do not simulate current authoritative text. Both rows received query-day `fetched_date=2026-10-05`, `doc_date=null`, `is_stale(...,30)=false`, and supplement `confidence=verified`. The original synthetic note remained unchanged. Article 80 therefore demonstrates a product effect beyond a misleading label: demonstrably older text can receive fresh-looking Level-A grounding.

| Case | Local text equals official snapshot | Source stale at 30 days | Supplement confidence |
| --- | --- | --- | --- |
| Criminal Code Article 80 | No | False | verified |
| Criminal Code Article 81 | Yes | False | verified |

The source URLs, SHA-256 hashes of fetched HTML, extracted article text, baseline repository SHA, database blob/hash, and output Source fields are in the frozen fixture and receipt. Replay with:

```bash
python scripts/research_law_snapshot.py
```

The replay makes no network requests or provider calls. The original two HTTPS reads contacted only public MOJ pages; no credentials, paid services, production writes, notes, or law corpus were changed. Later replay dates may change query-day fields; they do not change the frozen official comparison.

The smallest next implementation should carry `source_kind=local_snapshot`, actual `snapshot/import/fetch` date when known, separate `queried_at`, and `currentness=unknown|verified|stale` through the existing Source/export/review path. Unknown corpus age must remain unknown rather than become today's fetch date; unknown/stale local authority must not automatically receive a current-law verified label. Add promulgation/effective-status fields only where verified source evidence supports them. A DB file mtime or commit date must not masquerade as official freshness.

No new database, background sync, legal citator, service, or unrestricted online gate is needed to correct the demonstrated semantics. A documentation-only warning cannot prevent the observed `verified` result. This research branch records the decision; it does not implement the currentness correction, infer a specific amendment's effective date, or claim every stored law is outdated. Product repair remains a separate explicit implementation and regression task.
