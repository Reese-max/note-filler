"""Offline article-level official comparison metadata for local law snapshots."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .grading import is_stale

SCHEMA = "note_filler.law_snapshot.v1"
MAX_PROOF_BYTES = 256 * 1024


def text_sha256(text: str) -> str:
    """Ignore layout whitespace only; retain every substantive article character."""
    return hashlib.sha256("".join(text.split()).encode("utf-8")).hexdigest()


def snapshot_provenance(db_path: Path, rows: list[dict]) -> list[dict]:
    with db_path.open("rb") as stream:
        snapshot = hashlib.file_digest(stream, "sha256").hexdigest()
    unknown = {"snapshot_sha256": snapshot, "currentness": "unknown"}
    fallback = [dict(unknown) for _ in rows]
    proof_path = db_path.with_suffix(".provenance.json")
    try:
        with proof_path.open("rb") as stream:
            raw = stream.read(MAX_PROOF_BYTES + 1)
        if len(raw) > MAX_PROOF_BYTES:
            return fallback
        proof = json.loads(raw)
        if (not isinstance(proof, dict) or proof.get("schema") != SCHEMA
                or proof.get("snapshot_sha256") != snapshot):
            return fallback
        articles = proof.get("articles")
        if not isinstance(articles, dict):
            return fallback
        fetched = proof.get("snapshot_fetched_date")
        if fetched is not None and is_stale(fetched, 100000):
            return fallback
        output = []
        for row in rows:
            item = articles.get(f"{row['pcode']}:{row['article_no']}")
            result = {**unknown, "fetched_date": fetched}
            if not isinstance(item, dict):
                output.append(result)
                continue
            url = urlparse(item.get("official_url", ""))
            query = parse_qs(url.query)
            digest = item.get("official_text_sha256")
            checked = item.get("verified_at")
            if (url.scheme != "https" or url.hostname != "law.moj.gov.tw"
                    or url.path != "/LawClass/LawSingle.aspx"
                    or query.get("pcode") != [row["pcode"]]
                    or query.get("flno") != [row["article_no"]]
                    or not isinstance(digest, str) or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)
                    or is_stale(checked, 30)):
                output.append(result)
                continue
            result.update(verified_at=checked, official_text_sha256=digest,
                          currentness=("verified" if text_sha256(row["article_text"]) == digest
                                       else "stale"))
            output.append(result)
        return output
    except (OSError, ValueError, TypeError, AttributeError):
        return fallback
