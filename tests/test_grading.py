from dataclasses import fields
from datetime import date, timedelta

from note_filler.retrieve.grading import grade_law, grade_twinkle, is_stale
from note_filler.retrieve.models import Source


def test_source_dataclass_has_locked_fields():
    s = Source(
        id="law-民法-184",
        title="民法第184條",
        url=None,
        level="A",
        content="因故意或過失,不法侵害他人之權利者,負損害賠償責任。",
        fetched_date="2026-07-15",
        doc_date=None,
        distance=0.0,
    )
    assert s.id == "law-民法-184"
    assert s.level == "A"
    assert s.url is None
    assert s.doc_date is None
    assert s.fetched_date == "2026-07-15"
    assert s.distance == 0.0
    # 鎖定型別:欄位名稱與順序不得改
    names = [f.name for f in fields(Source)]
    assert names == [
        "id", "title", "url", "level", "content",
        "fetched_date", "doc_date", "distance",
    ]


def test_grade_law_returns_A():
    # law_lookup 命中的法規原文 = 官方一手 = A
    assert grade_law() == "A"


def test_grade_twinkle_returns_B():
    # twinkle 立法院議案等 = 二手 = B
    assert grade_twinkle() == "B"


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def test_is_stale_exactly_max_age_is_not_stale():
    # 剛好 max_age_days 天前抓的:未超過 → 不算 stale
    assert is_stale(_days_ago(30), max_age_days=30) is False


def test_is_stale_over_max_age_is_stale():
    # 超過一天:算 stale
    assert is_stale(_days_ago(31), max_age_days=30) is True


def test_is_stale_under_max_age_is_not_stale():
    # 未達門檻:不算 stale
    assert is_stale(_days_ago(29), max_age_days=30) is False


def test_is_stale_today_is_not_stale():
    # 今天剛抓:一定不 stale
    assert is_stale(date.today().isoformat(), max_age_days=0) is False
