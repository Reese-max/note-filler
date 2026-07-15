from __future__ import annotations

from datetime import date

from note_filler.retrieve.models import SourceLevel


def grade_law() -> SourceLevel:
    """law_lookup 命中的本地法規原文 = 官方一手 → A。"""
    return "A"


def grade_twinkle() -> SourceLevel:
    """twinkle(立法院議案等)= 二手 → B。"""
    return "B"


def is_stale(fetched_date: str, max_age_days: int) -> bool:
    """fetched_date(ISO)距今天數 > max_age_days 即視為過期。

    MVP 不追文件本身 doc_date,以抓取當下 fetched_date 為準。
    邊界:剛好等於 max_age_days 不算 stale(用嚴格大於)。
    """
    fetched = date.fromisoformat(fetched_date)
    age_days = (date.today() - fetched).days
    return age_days > max_age_days
