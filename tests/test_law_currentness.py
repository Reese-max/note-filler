"""Real saved MOJ current Article 80 and unchanged Article 81, without network."""
from dataclasses import replace
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from note_filler.citation_formatter import build_reference_lines
from note_filler.correction import _grounded, assemble_correction
from note_filler.gap import Gap
from note_filler.knowledge.law_lookup import LawLookup
from note_filler.llm import FakeLLM
from note_filler.parse import Document, Paragraph
from note_filler.retrieve.grading import is_stale
from note_filler.retrieve.law_currentness import SCHEMA, text_sha256
from note_filler.retrieve.law_search import search_law_sources
from note_filler.retrieve.models import LawSnapshotSource
from note_filler.review import evidence_bundle_hash
from note_filler.verify import cross_validate
from note_filler.write import WrittenSupplement

FIXTURE = json.loads((Path(__file__).parent / "fixtures/law-currentness/official-comparison.json").read_text())
TODAY = date.today().isoformat()


def corpus(tmp_path, outdated=False):
    db = tmp_path / "law_index.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE law_articles(pcode TEXT,law_name TEXT,article_no TEXT,article_text TEXT)")
        for item in FIXTURE["cases"]:
            text = item["official_text"]
            if outdated and item["article_no"] == "80":
                text = text.rsplit("\n", 1)[0]
            conn.execute("INSERT INTO law_articles VALUES(?,?,?,?)", (item["pcode"], item["law_name"], item["article_no"], text))
    return db


def write_proof(db, **overrides):
    data = {"schema": SCHEMA, "snapshot_sha256": hashlib.sha256(db.read_bytes()).hexdigest(),
            "articles": {f"{i['pcode']}:{i['article_no']}": {
                "official_url": i["official_url"], "verified_at": TODAY,
                "official_text_sha256": text_sha256(i["official_text"]),
            } for i in FIXTURE["cases"]}}
    data.update(overrides)
    db.with_suffix(".provenance.json").write_text(json.dumps(data))
    return data


def search(db):
    return search_law_sources(Gap("追訴時效", "missing", ""), FakeLLM([
        '{"keywords":["追訴權","刪除"],"law_name":"中華民國刑法"}'
    ]), LawLookup(db))


def correction(sources):
    doc = Document("note.txt", (Paragraph(0, "原始筆記不得變更。"),), "原始筆記不得變更。")
    q = "追訴時效"
    written = WrittenSupplement("追訴時效依刑法[^1]。", [s.id for s in sources])
    result = assemble_correction(doc, [Gap(q, "missing", "")], {q: sources}, {q: written}, {})
    assert result.original is doc and result.segments[0].text == doc.full_text
    return result.segments[1]


def test_legacy_corpus_query_is_not_a_fetch_or_verified_authority(tmp_path):
    sources = search(corpus(tmp_path))
    assert len(sources) == 2
    assert all(isinstance(s, LawSnapshotSource) for s in sources)
    assert all(s.fetched_date is None and s.queried_at == TODAY and s.currentness == "unknown" for s in sources)
    assert all(is_stale(s.fetched_date, 30) for s in sources)
    assert not cross_validate("claim", sources).verified  # even two Level A rows
    assert not _grounded(sources)
    assert correction(sources).confidence == "pending_evidence"
    reference = build_reference_lines(sources)
    assert "Date: UNKNOWN" in reference and "Currentness: unknown" in reference


def test_official_current_article_and_unchanged_control_are_verified(tmp_path):
    db = corpus(tmp_path)
    write_proof(db)
    sources = search(db)
    assert [s.currentness for s in sources] == ["verified", "verified"]
    assert all(s.verified_at == TODAY and s.fetched_date is None for s in sources)
    assert all(cross_validate("claim", [s]).verified for s in sources)
    assert all(_grounded([s]) for s in sources)
    assert correction(sources).confidence == "verified"


def test_old_article_is_stale_without_poisoning_unchanged_control(tmp_path):
    db = corpus(tmp_path, outdated=True)
    write_proof(db)
    changed, control = search(db)
    assert changed.currentness == "stale" and control.currentness == "verified"
    assert not cross_validate("claim", [changed]).verified
    assert correction([changed]).confidence == "pending_evidence"
    assert cross_validate("claim", [control]).verified
    assert "不計入第一項期間" not in changed.content


@pytest.mark.parametrize("drift", ["db", "expired", "future", "malformed", "oversize", "missing_article", "wrong_url", "wrong_article", "wrong_hash"])
def test_invalid_or_expired_proof_fails_closed(tmp_path, drift):
    db = corpus(tmp_path)
    proof = write_proof(db)
    path = db.with_suffix(".provenance.json")
    if drift == "db":
        with sqlite3.connect(db) as conn:
            conn.execute("UPDATE law_articles SET law_name='changed'")
    elif drift == "malformed":
        path.write_text("[]")
    elif drift == "oversize":
        path.write_text(" " * (256 * 1024 + 1))
    else:
        for item in proof["articles"].values():
            if drift == "expired": item["verified_at"] = (date.today() - timedelta(days=31)).isoformat()
            if drift == "future": item["verified_at"] = (date.today() + timedelta(days=1)).isoformat()
            if drift == "wrong_url": item["official_url"] = "https://example.com/fake"
            if drift == "wrong_article": item["official_url"] = item["official_url"].replace("flno=", "other=")
            if drift == "wrong_hash": item["official_text_sha256"] = "z" * 64
        if drift == "missing_article": proof["articles"] = {}
        path.write_text(json.dumps(proof))
    rows = LawLookup(db).search_articles("", 25)
    values = LawLookup(db).source_provenance(rows)
    assert all(v["currentness"] == "unknown" for v in values)


def test_proof_change_invalidates_human_evidence_fingerprint(tmp_path):
    db = corpus(tmp_path)
    write_proof(db)
    seg = correction(search(db))
    before = evidence_bundle_hash(seg)
    seg.sources[0] = replace(seg.sources[0], currentness="stale")
    assert evidence_bundle_hash(seg) != before


@pytest.mark.parametrize("value", [None, "", "not-a-date", (date.today()+timedelta(days=1)).isoformat()])
def test_unknown_invalid_future_fetch_date_is_stale(value):
    assert is_stale(value, 30)
