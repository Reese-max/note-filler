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


def test_three_articles_same_law_same_url_verified():
    # 引 3 條同法(url 相同、id/title 不同,level A)→ verified
    # (先前被誤標 pending 的案例:一手法條原文即定論)
    url = "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0030055"
    sources = [
        mk("s1", "行政程序法第93條", url, "A", content="附款之許可。"),
        mk("s2", "行政程序法第94條", url, "A", content="附款不得違背目的。"),
        mk("s3", "行政程序法第96條", url, "A", content="書面行政處分應記載。"),
    ]
    v = cross_validate("附款相關規定", sources)
    assert v.verified is True


def test_single_a_source_verified():
    # 一手源(1 個 level A)即 grounded → verified
    sources = [mk("s1", "唯一來源", "https://only.example/z", "A", content="Z。")]
    v = cross_validate("Z", sources)
    assert v.verified is True


def test_two_distinct_b_verified():
    # 引 2 個不同 level B(id 不同、無 A)→ verified
    sources = [
        mk("s1", "學說甲", "https://b.example/1", "B", content="主張成立。"),
        mk("s2", "學說乙", "https://b.example/2", "B", content="主張成立。"),
    ]
    v = cross_validate("主張成立", sources)
    assert v.verified is True


def test_single_b_no_a_pending():
    # 1 個 level B、無 A → not verified(pending_evidence)
    sources = [mk("s1", "學說甲", "https://b.example/1", "B", content="主張成立。")]
    v = cross_validate("主張成立", sources)
    assert v.verified is False


def test_single_c_verified():
    # 1 個 level C(官方/標準組織一手,如 owasp.org/NIST/CVE)→ verified
    sources = [mk("s1", "OWASP Top 10", "https://owasp.org/x", "C", content="說明。")]
    v = cross_validate("說明", sources)
    assert v.verified is True


def test_single_d_pending():
    # 1 個 level D、無其他 → not verified(單一二手不算定論)
    sources = [mk("s1", "部落格摘要", "https://blog.example/d", "D", content="說明。")]
    v = cross_validate("說明", sources)
    assert v.verified is False


def test_two_distinct_d_verified():
    # 2 個相異 level D(id 不同)→ verified(多源佐證,規則三不限 level)
    sources = [
        mk("s1", "部落格甲", "https://blog.example/1", "D", content="說明。"),
        mk("s2", "論壇乙", "https://forum.example/2", "D", content="說明。"),
    ]
    v = cross_validate("說明", sources)
    assert v.verified is True


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


def test_distinct_by_id_not_url():
    # 相異以 id/title 判、不再用 url:同 url 不同 id/title → 各自計數(2 個相異)
    url = "https://law.example/pcode"
    sources = [
        mk("s1", "行政程序法第92條", url, "B", content="X。"),
        mk("s2", "行政程序法第93條", url, "B", content="X。"),
    ]
    assert len(_independent_ab(sources)) == 2
    v = cross_validate("X", sources)
    assert v.verified is True  # 2 個相異 B(規則二)
