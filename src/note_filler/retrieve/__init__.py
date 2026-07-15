"""依缺口檢索:對單一 Gap 打 twinkle 取回一手來源,並依 C5 排序(A 先於 B、distance 小先)。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..gap import Gap
from .models import Source

if TYPE_CHECKING:  # 僅型別檢查用,避免執行期循環匯入
    from ..domain import Domain
    from .twinkle import TwinkleClient

# SourceLevel 枚舉 A/B/C/D 排序權重;MVP 只會出現 A/B,未知級別排最後
_LEVEL_RANK: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3}
# MVP 領域閘:只在 law/admin/exam 檢索(開放網路/其他領域延後)
_RETRIEVABLE: frozenset[str] = frozenset({"law", "admin", "exam"})


def retrieve_for_gap(gap: Gap, domain: "Domain", twinkle: "TwinkleClient") -> list[Source]:
    """對缺口 gap 檢索一手來源。

    - domain 非 MVP(law/admin/exam)→ 不檢索,回 [](不浪費網路)。
    - 以 gap.question 為 query 打 twinkle.search。
    - 回傳前依 C5 排序:Level A 先於 B,同級 distance 小者先,落實 G2 優先一手源。
    """
    if domain not in _RETRIEVABLE:
        return []
    sources = twinkle.search(gap.question)
    return sorted(sources, key=lambda s: (_LEVEL_RANK.get(s.level, 99), s.distance))
