"""交叉驗證(verify.py)。

純函式模組,不呼叫 LLM。C4:對「獨立 A/B 來源」顯式計數,count>=2 才 verified。
衝突偵測用關鍵詞啟發式,只標記不自動選邊。來源排序遵守 C5(Level A 先、distance 小先)。
"""
from __future__ import annotations

from dataclasses import dataclass

from note_filler.retrieve.models import Source


@dataclass
class Validation:
    claim: str
    sources: list
    verified: bool
    conflict: bool
    conflict_note: str | None


def _is_independent(a: Source, b: Source) -> bool:
    """獨立 = url 不同 且 title(機關/文件) 不同。
    任一 url 為 None 時無法證明「不同 url」,保守視為不獨立。
    """
    diff_url = a.url is not None and b.url is not None and a.url != b.url
    diff_title = a.title != b.title
    return diff_url and diff_title


def _independent_ab(sources: list[Source]) -> list[Source]:
    """回傳彼此獨立的 A/B 來源子集(僅計 level A/B)。
    C5 排序:Level A 先於 B、distance 小者先;再貪婪挑選互相獨立者。
    """
    ab = [s for s in sources if s.level in ("A", "B")]
    ab.sort(key=lambda s: (0 if s.level == "A" else 1, s.distance))
    kept: list[Source] = []
    for s in ab:
        if all(_is_independent(s, k) for k in kept):
            kept.append(s)
    return kept


# 衝突偵測用的正/反關鍵詞對;命中僅標記,絕不自動選邊
_CONFLICT_PAIRS: list[tuple[str, str]] = [
    ("應", "不應"),
    ("得", "不得"),
    ("有效", "失效"),
    ("有效", "廢止"),
    ("合法", "違法"),
    ("成立", "不成立"),
]


def _detect_conflict(sources: list[Source]) -> tuple[bool, str | None]:
    """關鍵詞啟發式:若某來源含正面詞、另一來源含其反面詞 → 標記衝突。
    不判斷孰是孰非(不選邊)。
    """
    texts = [s.content or "" for s in sources]
    for pos, neg in _CONFLICT_PAIRS:
        # 反面詞常含正面詞為子字串(如「不應」含「應」),故正面命中須排除含反面詞者
        has_pos = any(pos in t and neg not in t for t in texts)
        has_neg = any(neg in t for t in texts)
        if has_pos and has_neg:
            note = f"來源對「{pos}/{neg}」表述不一致,需人工判讀(不選邊)"
            return True, note
    return False, None


def cross_validate(claim: str, sources: list) -> Validation:
    """C4:顯式計數獨立 A/B 來源,count>=2 才 verified。
    衝突僅標記不選邊(見 _detect_conflict)。
    """
    independent = _independent_ab(sources)
    verified = len(independent) >= 2  # 顯式計數 >=2
    conflict, note = _detect_conflict(sources)
    return Validation(
        claim=claim,
        sources=sources,      # 原始來源保留,不因衝突刪除
        verified=verified,
        conflict=conflict,
        conflict_note=note,
    )
