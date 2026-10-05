from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SourceLevel = Literal["A", "B", "C", "D"]


@dataclass
class Source:
    id: str
    title: str
    url: str | None
    level: SourceLevel
    content: str
    fetched_date: str | None  # Actual fetch date; unknown corpus dates stay None
    doc_date: str | None     # 文件本身日期,未知則 None
    distance: float


@dataclass
class LawSnapshotSource(Source):
    """Local corpus custody and article-level official comparison, never query time."""

    queried_at: str = ""
    snapshot_sha256: str | None = None
    currentness: Literal["unknown", "verified", "stale"] = "unknown"
    verified_at: str | None = None
    official_text_sha256: str | None = None


def usable_authority(source: Source) -> bool:
    """Unproven local snapshots cannot establish current legal authority."""
    if not isinstance(source, LawSnapshotSource):
        return True
    from .grading import is_stale

    return source.currentness == "verified" and not is_stale(source.verified_at, 30)
