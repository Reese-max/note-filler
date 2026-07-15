"""依缺口檢索:law/exam/admin 先查法條(A)再打 twinkle(B),其餘 domain 只打 twinkle;
最後依 C5 排序(A 先於 B、distance 小先)。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..gap import Gap
from .law_search import search_law_sources
from .models import Source

if TYPE_CHECKING:  # 僅型別檢查用,避免執行期循環匯入
    from ..domain import Domain
    from ..llm import LLMClient
    from .twinkle import TwinkleClient

# SourceLevel 枚舉 A/B/C/D 排序權重;MVP 只會出現 A/B,未知級別排最後
_LEVEL_RANK: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3}
# 會加掛 Level A 法條的領域;其餘領域仍會打 twinkle(Level B)
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
    - 其餘 domain:只打 twinkle。
    - 回傳前依 C5 排序:Level A 先於 B,同級 distance 小者先,落實 G2 優先一手源。
    """
    sources: list[Source] = []
    if domain in _LAW_DOMAINS and law is not None and llm is not None:
        sources.extend(search_law_sources(gap, llm, law))
    sources.extend(twinkle.search(gap.question))
    return sorted(sources, key=lambda s: (_LEVEL_RANK.get(s.level, 99), s.distance))
