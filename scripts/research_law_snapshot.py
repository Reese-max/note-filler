"""Replay #9's local law freshness experiment without provider or network calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get("NOTE_LAW_REPLAY_SOURCE_ROOT", ROOT)).resolve()
sys.path.insert(0, str(SOURCE_ROOT / "src"))

from note_filler.correction import assemble_correction  # noqa: E402
from note_filler.gap import Gap  # noqa: E402
from note_filler.knowledge.law_lookup import LawLookup  # noqa: E402
from note_filler.parse import Document, Paragraph  # noqa: E402
from note_filler.retrieve.grading import is_stale  # noqa: E402
from note_filler.retrieve.law_search import search_law_sources  # noqa: E402
from note_filler.verify import cross_validate  # noqa: E402
from note_filler.write import WrittenSupplement  # noqa: E402


class FixedKeywordExtractor:
    """Supply a pinned query, rather than calling an LLM for keyword selection."""

    def __init__(self, keyword: str) -> None:
        self.keyword = keyword

    def complete(self, messages: list[dict]) -> str:
        return json.dumps({"keywords": [self.keyword], "law_name": "中華民國刑法"})


class OneArticleCorpus:
    """Filter actual database search rows to the experiment's single law article."""

    def __init__(self, db: Path, article_no: str) -> None:
        self.lookup = LawLookup(db)
        self.article_no = article_no

    def search_articles(self, keyword: str, limit: int, law_name: str | None) -> list[dict]:
        rows = self.lookup.search_articles(keyword, 5000, law_name)
        return [r for r in rows if r["pcode"] == "C0000001" and r["article_no"] == self.article_no]


    def source_provenance(self, rows: list[dict]) -> list[dict]:
        if hasattr(self.lookup, "source_provenance"):
            return self.lookup.source_provenance(rows)
        return [{} for _ in rows]


def replay(expected: str = "auto") -> dict:
    fixture = json.loads((ROOT / "tests/fixtures/law-currentness/official-comparison.json").read_text())
    db = ROOT / "data/law_index.db"
    assert hashlib.sha256(db.read_bytes()).hexdigest() == fixture["db_sha256"], "Database drift"
    results = []
    for case in fixture["cases"]:
        article = case["article_no"]
        gap = Gap(f"中華民國刑法第{article}條的規定為何？", "missing", "原稿未涵蓋條文")
        keyword = "追訴權" if article == "80" else "（刪除）"
        sources = search_law_sources(gap, FixedKeywordExtractor(keyword), OneArticleCorpus(db, article))
        assert len(sources) == 1, "Pinned database row missing"
        source = sources[0]
        original = Document("synthetic-note", (Paragraph(0, "原始筆記。"),), "原始筆記。")
        written = WrittenSupplement(source.content + "[^1]", [source.id])
        result = assemble_correction(
            original, [gap], {gap.question: sources}, {gap.question: written},
            {gap.question: cross_validate(gap.question, sources)},
        )
        normalize = lambda text: re.sub(r"\s+", "", text)
        results.append({
            "article_no": article, "official_url": case["official_url"],
            "official_html_sha256": case["official_html_sha256"],
            "law_temporal_evidence": case.get("law_temporal_evidence", {}),
            "text_matches_official": normalize(source.content) == normalize(case["official_text"]),
            "local_source": asdict(source), "is_stale_30_days": is_stale(source.fetched_date, 30),
            "supplement_confidence": result.segments[1].confidence,
            "original_preserved": result.segments[0].text == original.full_text,
        })
    assert results[0]["text_matches_official"] is False
    assert results[1]["text_matches_official"] is True
    baseline = all(r["is_stale_30_days"] is False and r["supplement_confidence"] == "verified"
                   and "currentness" not in r["local_source"] for r in results)
    repaired = all(r["is_stale_30_days"] is True and r["supplement_confidence"] == "pending_evidence"
                   and r["local_source"].get("fetched_date") is None
                   and r["local_source"].get("currentness") == "unknown" for r in results)
    assert baseline or repaired, "Unexpected source/grounding contract; investigate drift"
    contract = "baseline" if baseline else "repaired"
    assert expected == "auto" or expected == contract, f"Expected {expected}, got {contract}"
    source_sha = subprocess.check_output(
        ["git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"], text=True,
    ).strip()
    return {
        "schema_version": 2, "decision": "BUILD", "baseline_repo_sha": fixture["repo_sha"],
        "source_repo_sha": source_sha, "source_contract": contract,
        "db_blob": fixture["db_blob"], "db_sha256": fixture["db_sha256"],
        "last_db_commit_date": fixture["last_db_commit_date"],
        "official_amendment_notice": fixture.get("official_amendment_notice"),
        "method": "Actual local SQLite/source/staleness/correction paths; fixed keyword extractor; frozen official public snapshots",
        "provider_calls": 0, "replay_network_requests": 0, "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect", choices=("auto", "baseline", "repaired"), default="auto")
    print(json.dumps(replay(parser.parse_args().expect), ensure_ascii=False, indent=2))
