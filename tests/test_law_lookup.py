# tests/test_law_lookup.py
# -*- coding: utf-8 -*-
"""search_articles 排序驗收:同批 LIKE 命中依 article_no 數值序,核心條不被 rowid 擠掉。"""
import sqlite3

from note_filler.knowledge.law_lookup import LawLookup


def _make_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE law_articles "
            "(pcode TEXT, law_name TEXT, article_no TEXT, article_text TEXT)"
        )
        # 插入序刻意亂序,article_no 為純數字字串
        for no in ["117", "2", "120", "93"]:
            conn.execute(
                "INSERT INTO law_articles VALUES (?, ?, ?, ?)",
                ("P1", "測試法", no, f"第{no}條 命中關鍵詞"),
            )


def test_search_articles_orders_by_numeric_article_no(tmp_path):
    db = tmp_path / "t.db"
    _make_db(db)
    law = LawLookup(str(db))

    rows = law.search_articles("命中關鍵詞", limit=10)

    assert [r["article_no"] for r in rows] == ["2", "93", "117", "120"]


def test_search_articles_limit_after_numeric_sort(tmp_path):
    db = tmp_path / "t.db"
    _make_db(db)
    law = LawLookup(str(db))

    rows = law.search_articles("命中關鍵詞", limit=2)

    # limit 生效且取數值序前二(非插入序)
    assert [r["article_no"] for r in rows] == ["2", "93"]
