# Local law snapshot currentness — Issue #9

Decision: **BUILD**, confined to source provenance and currentness semantics.

On 2026-10-05, two public Ministry of Justice article pages were retrieved over HTTPS. Criminal Code Article 80 differs from the checked-in SQLite corpus: the official page contains an additional paragraph excluding time before the victim turns twenty for its enumerated offenses. The local row ends at the preceding paragraph. Article 81, the unchanged control, matches the official deleted-article text after whitespace normalization. This is a textual comparison, not an independent legal interpretation or advice about applicability.

An additional actual HTTPS read of [MOJ amendment notice198983](https://law.moj.gov.tw/News/NewsDetail.aspx?msgid=198983)
observed **公(發)布日期：115-07-22** and the statement **中華民國一百十五年七月二十二日總統華總一義字第11500067801號令修正公布第80條條文**.
Mechanical ROC/Gregorian conversion yields **2026-07-22**, after the recorded
2026-07-15 database custody commit. The notice reproduces the additional paragraph.
Its HTML SHA-256 is `7b74ac500044857e15b3b69c42218c7f9115623961d830fd46b4f17f32d2ef96`;
retrieval time, literal date label/value, announcement statement and URL are frozen
in the fixture. The same page separately states **法規整編資料截止日：民國115年09月24日**
(2026-09-24), a site compilation cutoff, not an Article80 effective date or a database
acquisition date. Article81 has no separately verified amendment date in this study.

**Effective date, effective status and legal applicability remain UNKNOWN** for
both cases. Promulgation/news dates and a textual current-page match cannot settle
when an amendment applies to a particular offense or pending case. Neither the
research nor LevelA currentness proof asserts that interpretation. The fixture and
replay keep these unknown fields separate from custody, retrieval, promulgation,
and compilation dates.

The DB blob was last committed on 2026-07-15. That is repository custody evidence, **not proof of the corpus's fetch/import date**. Neither the DB schema nor the retrieved Source carries a snapshot, revision, effective-date, or authority-currentness field.

The actual `LawLookup.search_articles`, `search_law_sources`, `is_stale`, `cross_validate`, and `assemble_correction` paths were replayed with this real DB. A fixed keyword extractor and article filter replaced provider-dependent query selection; they do not simulate current authoritative text. Both rows received query-day `fetched_date=2026-10-05`, `doc_date=null`, `is_stale(...,30)=false`, and supplement `confidence=verified`. The original synthetic note remained unchanged. Article 80 therefore demonstrates a product effect beyond a misleading label: demonstrably older text can receive fresh-looking Level-A grounding.

| Case | Local text equals official snapshot | Source stale at 30 days | Supplement confidence |
| --- | --- | --- | --- |
| Criminal Code Article 80 | No | False | verified |
| Criminal Code Article 81 | Yes | False | verified |

The source URLs, SHA-256 hashes of fetched HTML, extracted article text, baseline repository SHA, database blob/hash, and output Source fields are in the frozen fixture and receipt. The original receipt is immutable historical baseline evidence, not a promise that
current repaired source still emits the defect. Replay current integrated source:

```bash
python scripts/research_law_snapshot.py --expect repaired
```

To reproduce the original defect, explicitly pin the source checkout to the
fixture's baseline `2b231b22b336497e04d89a60d175cbe60242ec90` and select it:

```bash
git worktree add --detach /tmp/note-law-baseline 2b231b22b336497e04d89a60d175cbe60242ec90
NOTE_LAW_REPLAY_SOURCE_ROOT=/tmp/note-law-baseline python scripts/research_law_snapshot.py --expect baseline
```

Both modes read the same frozen comparison and database bytes; output includes
actual source repository SHA and a typed baseline/repaired contract. The wrapper
forwards actual lookup provenance on repaired source. No assertion demands old
unsafe behavior from new source; mismatched expectation or unexpected semantics
fails instead of silently claiming baseline replication.

The replay makes no network requests or provider calls. The original two HTTPS reads contacted only public MOJ pages; no credentials, paid services, production writes, notes, or law corpus were changed. Later replay dates may change query-day fields; they do not change the frozen official comparison.

The smallest next implementation should carry `source_kind=local_snapshot`, actual `snapshot/import/fetch` date when known, separate `queried_at`, and `currentness=unknown|verified|stale` through the existing Source/export/review path. Unknown corpus age must remain unknown rather than become today's fetch date; unknown/stale local authority must not automatically receive a current-law verified label. Add promulgation/effective-status fields only where verified source evidence supports them. A DB file mtime or commit date must not masquerade as official freshness.

No new database, background sync, legal citator, service, or unrestricted online gate is needed to correct the demonstrated semantics. A documentation-only warning cannot prevent the observed `verified` result. The separate repair PR #23 implements currentness gating. This research branch integrates that source to keep replay current while preserving the original baseline receipt; it does not itself update the legal corpus, infer a specific amendment's effective date, or claim every stored law is outdated. Product repair remains a separate explicit implementation and regression task.
