# tests/test_verify.py
from note_filler.retrieve.models import Source
from note_filler.verify import Validation, cross_validate, _independent_ab


def mk(id: str, title: str, url: str | None, level: str,
       content: str = "", distance: float = 0.5) -> Source:
    """測試用 Source 工廠;固定 fetched_date、doc_date=None。"""
    return Source(
        id=id, title=title, url=url, level=level, content=content,
        fetched_date="2026-07-15", doc_date=None, distance=distance,
    )


def test_two_independent_ab_sources_verified():
    # 不同 url 且 不同 title/機關,level 皆 A/B → verified
    sources = [
        mk("s1", "行政程序法第92條", "https://law.moj.gov.tw/a", "A",
           content="行政處分應以書面為之。"),
        mk("s2", "立法院議案關係文書 第10屆", "https://ly.gov.tw/b", "B",
           content="行政處分應以書面為之。"),
    ]
    v = cross_validate("行政處分應以書面為之", sources)
    assert isinstance(v, Validation)
    assert v.verified is True
    assert v.claim == "行政處分應以書面為之"
    assert v.sources == sources  # 原始來源保留不刪


def test_same_url_not_verified():
    # 兩筆 url 相同 → 非獨立 → 只算 1 → not verified
    sources = [
        mk("s1", "來源甲", "https://same.example/x", "A", content="X 成立。"),
        mk("s2", "來源乙", "https://same.example/x", "A", content="X 成立。"),
    ]
    v = cross_validate("X 成立", sources)
    assert v.verified is False


def test_single_source_not_verified():
    sources = [mk("s1", "唯一來源", "https://only.example/z", "A", content="Z。")]
    v = cross_validate("Z", sources)
    assert v.verified is False


def test_cd_level_not_counted():
    # 1 個 A + 1 個 C + 1 個 D:C/D 不計入 → 獨立 A/B 僅 1 → not verified
    sources = [
        mk("s1", "官方一手", "https://gov.example/a", "A", content="主張成立。"),
        mk("s2", "部落格摘要", "https://blog.example/c", "C", content="主張成立。"),
        mk("s3", "論壇貼文", "https://forum.example/d", "D", content="主張成立。"),
    ]
    v = cross_validate("主張成立", sources)
    assert v.verified is False


def test_conflict_detected_and_no_side_taken():
    # 一源「得」、一源「不得」→ 標記衝突,但不刪來源、不選邊
    sources = [
        mk("s1", "來源甲", "https://a.example/1", "A", content="納稅義務人得申請延期。"),
        mk("s2", "來源乙", "https://b.example/2", "B", content="納稅義務人不得申請延期。"),
    ]
    v = cross_validate("納稅義務人得否申請延期", sources)
    assert v.conflict is True
    assert v.conflict_note is not None and "不選邊" in v.conflict_note
    assert v.sources == sources          # 未選邊、未刪除任何來源
    assert v.verified is True            # 2 獨立 A/B,verified 與 conflict 各自獨立


def test_no_conflict_when_consistent():
    sources = [
        mk("s1", "來源甲", "https://a.example/1", "A", content="行政處分應以書面為之。"),
        mk("s2", "來源乙", "https://b.example/2", "B", content="行政處分應以書面為之。"),
    ]
    v = cross_validate("行政處分應以書面為之", sources)
    assert v.conflict is False
    assert v.conflict_note is None


def test_negation_substring_not_false_positive():
    # 兩源皆為反面「不應」,不應被判為「應 vs 不應」衝突
    sources = [
        mk("s1", "來源甲", "https://a.example/1", "A", content="機關不應逕行處分。"),
        mk("s2", "來源乙", "https://b.example/2", "B", content="機關不應逕行處分。"),
    ]
    v = cross_validate("機關不應逕行處分", sources)
    assert v.conflict is False


def test_independent_ab_orders_A_before_B_and_by_distance():
    sources = [
        mk("b_far", "B 遠", "https://b.example/far", "B", distance=0.9),
        mk("a_near", "A 近", "https://a.example/near", "A", distance=0.2),
        mk("a_far", "A 遠", "https://a.example/far", "A", distance=0.7),
    ]
    kept = _independent_ab(sources)
    # 三者兩兩獨立(url、title 皆異)→ 全留;順序:A 近、A 遠、B 遠
    assert [s.id for s in kept] == ["a_near", "a_far", "b_far"]


def test_duplicate_title_collapses_to_one():
    # 同 title(同機關/文件)不同 url → 非獨立,計數仍為 1 → not verified
    sources = [
        mk("s1", "行政程序法第92條", "https://law.example/v1", "A", content="X。"),
        mk("s2", "行政程序法第92條", "https://law.example/v2", "A", content="X。"),
    ]
    v = cross_validate("X", sources)
    assert v.verified is False
    assert len(_independent_ab(sources)) == 1
