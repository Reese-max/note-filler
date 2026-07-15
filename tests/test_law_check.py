# tests/test_law_check.py
# -*- coding: utf-8 -*-
from pathlib import Path

import pytest

from note_filler.knowledge.law_lookup import LawLookup
from note_filler.knowledge.law_citation_check import check_law_citations

DB = str(Path(__file__).resolve().parents[1] / "data" / "law_index.db")


@pytest.fixture(scope="module")
def lookup() -> LawLookup:
    db = Path(DB)
    assert db.exists(), f"法規索引 DB 未就緒:{db}"
    return LawLookup(DB)


def test_real_law_article_exists(lookup):
    # 真法規、真條號 → 存在且有內容
    assert lookup.law_exists("行政程序法") is True
    art = lookup.lookup_article("行政程序法", "1")
    assert art is not None and len(art) > 0


def test_fake_article_no_flagged_not_found(lookup):
    # 真法規、假條號 → article_not_found,且 dict 欄位齊全
    issues = check_law_citations("依行政程序法第9999條規定辦理。", lookup)
    hits = [i for i in issues if i["kind"] == "article_not_found"]
    assert hits, f"預期 article_not_found,實得 {issues}"
    hit = hits[0]
    assert set(hit) >= {"law_name", "article_no", "kind", "detail"}
    assert hit["law_name"] == "行政程序法"
    assert hit["article_no"] == "9999"


def test_unknown_law_not_false_reported(lookup):
    # 法規名不在庫(未收錄)→ 不誤報
    issues = check_law_citations("依外星生物保護法第1條規定辦理。", lookup)
    assert issues == []


def test_check_law_citations_first_param_is_text():
    # C2:第一參數名一律 text(防回歸成 draft)
    import inspect
    params = list(inspect.signature(check_law_citations).parameters)
    assert params[0] == "text", f"第一參數應為 text,實得 {params[0]}"
