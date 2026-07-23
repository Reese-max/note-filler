"""依缺口檢索:law/exam/admin 先查法條(A)再打 twinkle(B),other 只加掛開放網路來源(C/D);
最後依 C5 排序(A 先於 B、distance 小先)。"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..audit import audit_event
from ..gap import Gap
from .law_search import search_law_sources
from .models import Source
from .web import search_web_sources

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # 僅型別檢查用,避免執行期循環匯入
    from ..domain import Domain
    from ..llm import LLMClient
    from .twinkle import TwinkleClient

# SourceLevel 枚舉 A/B/C/D 排序權重;MVP 只會出現 A/B,未知級別排最後
_LEVEL_RANK: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3}
# 會加掛 Level A 法條、且會打 twinkle(Level B)的領域;other 不打 twinkle
_LAW_DOMAINS: frozenset[str] = frozenset({"law", "admin", "exam"})


def retrieve_for_gap(
    gap: Gap,
    domain: "Domain",
    twinkle: "TwinkleClient",
    law=None,
    llm: "LLMClient | None" = None,
) -> list[Source]:
    """對缺口 gap 檢索一手來源。

    - law/exam/admin 且 law+llm 齊備:先 search_law_sources(Level A)再 twinkle(Level B)。
    - other(且 llm 齊備):只加掛開放網路來源(Level C/D),不打 twinkle。
    - 回傳前依 C5 排序:Level A 先於 B,同級 distance 小者先,落實 G2 優先一手源。
    """
    sources: list[Source] = []
    if domain in _LAW_DOMAINS and law is not None and llm is not None:
        sources.extend(search_law_sources(gap, llm, law))
    elif domain in _LAW_DOMAINS and (law is None or llm is None):
        audit_event(
            logger,
            "law_source_retrieval_skipped",
            gap.question,
            domain=domain,
            dependency_state=f"law={law is not None}/llm={llm is not None}",
            reason="missing retrieval dependency",
        )
    elif domain == "other" and llm is not None:
        # 資安/IT/一般領域:加掛開放網路來源(Level C/D),不打 twinkle(立法院議案為噪音)
        sources.extend(search_web_sources(gap, llm))
    elif domain == "other":
        audit_event(
            logger,
            "web_source_retrieval_skipped",
            gap.question,
            domain="other",
            dependency_state="llm=False",
            reason="missing retrieval dependency",
        )
    if domain in _LAW_DOMAINS:  # twinkle(Level B)只對法制領域有意義,other 不打
        sources.extend(twinkle.search(gap.question))
    return sorted(sources, key=lambda s: (_LEVEL_RANK.get(s.level, 99), s.distance))
