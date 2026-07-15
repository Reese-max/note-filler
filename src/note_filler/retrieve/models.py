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
    fetched_date: str        # ISO date,例如 "2026-07-15"
    doc_date: str | None     # 文件本身日期,未知則 None
    distance: float
