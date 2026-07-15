# -*- coding: utf-8 -*-
"""法規名＋條號精確查詢索引，供核對公文引用法條之正確性。"""

import re
import sqlite3
from pathlib import Path


def _cn_to_arabic(s: str) -> str:
    """將中文條號數字轉為阿拉伯數字字串。"""
    value = s.strip()
    if re.fullmatch(r"\d+(?:-\d+)?", value):
        return value

    if "-" in value or "－" in value:
        parts = re.split(r"[-－]", value)
        return "-".join(_cn_to_arabic(part) for part in parts)

    nums = {
        "一": 1,
        "二": 2,
        "兩": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }

    result = 0
    temp = 0
    seen = False

    for char in value:
        if char in nums:
            temp = nums[char]
            seen = True
        elif char == "十":
            result += (temp if temp > 0 else 1) * 10
            temp = 0
            seen = True
        elif char == "百":
            result += (temp if temp > 0 else 1) * 100
            temp = 0
            seen = True
        elif char in ("零", "〇"):
            seen = True

    if not value or not seen:
        return value

    result += temp
    return str(result)


def _normalize_article_no(raw) -> str:
    """正規化法條條號為索引用字串。"""
    value = str(raw).strip()
    value = re.sub(r"[第條之\s]+", "", value)
    return _cn_to_arabic(value)


def parse_law_md(text: str) -> tuple:
    """解析 mojlaw markdown 文字，回傳法規代碼、法規名稱與條文對照。"""
    pcode_match = re.search(r"^source_id:\s*(\S+)", text, re.MULTILINE)
    title_match = re.search(r"^title:\s*(.+)$", text, re.MULTILINE)

    pcode = pcode_match.group(1) if pcode_match else ""
    law_name = title_match.group(1).strip() if title_match else ""

    articles = {}
    matches = list(re.finditer(r"^###\s*第\s*(\S+)\s*條", text, re.MULTILINE))

    for index, match in enumerate(matches):
        article_no = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        article_text = text[start:end]
        article_text = re.split(
            r"^第\s*[一二三四五六七八九十百零〇]+\s*章",
            article_text,
            maxsplit=1,
            flags=re.MULTILINE,
        )[0]
        articles[article_no] = article_text.strip()

    return (pcode, law_name, articles)


def build_law_index(corpus_dir, db_path) -> tuple:
    """從 mojlaw markdown 語料建立 SQLite 法條精確查詢索引。"""
    corpus_path = Path(corpus_dir)
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    law_count = 0
    article_count = 0

    with sqlite3.connect(db_file) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS law_articles (
                pcode TEXT,
                law_name TEXT,
                article_no TEXT,
                article_text TEXT,
                PRIMARY KEY(pcode, article_no)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_law_name ON law_articles(law_name)"
        )

        for md_path in corpus_path.glob("*.md"):
            pcode, law_name, articles = parse_law_md(md_path.read_text(encoding="utf-8"))
            if not pcode or not articles:
                continue

            law_count += 1
            for article_no, article_text in articles.items():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO law_articles
                    (pcode, law_name, article_no, article_text)
                    VALUES (?, ?, ?, ?)
                    """,
                    (pcode, law_name, article_no, article_text),
                )
                article_count += 1

    return (law_count, article_count)


class LawLookup:
    """以 SQLite 索引執行法規名與條號的精確查詢。"""

    def __init__(self, db_path):
        """設定 SQLite 索引檔路徑。"""
        self.db_path = Path(db_path)

    def lookup_article(self, law_name: str, article_no):
        """依法規名稱與條號精確查詢條文內容，查無則回傳 None。"""
        normalized_no = _normalize_article_no(article_no)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT article_text
                FROM law_articles
                WHERE law_name = ? AND article_no = ?
                """,
                (law_name, normalized_no),
            ).fetchone()
        return row[0] if row else None

    def find_law(self, law_name: str):
        """依法規名稱精確查詢法規代碼，查無則回傳 None。"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT DISTINCT pcode
                FROM law_articles
                WHERE law_name = ?
                LIMIT 1
                """,
                (law_name,),
            ).fetchone()
        return row[0] if row else None

    def law_exists(self, law_name: str) -> bool:
        """判斷指定法規名稱是否存在於索引。"""
        return self.find_law(law_name) is not None

    def fuzzy_find_law(self, law_name: str) -> str | None:
        """DB-wide substring fuzzy match：找 DB 中與 law_name 互為子字串的法規名。

        回傳匹配到的 DB 法規名，無匹配回傳 None。
        用例：law_name="人事總處組織法" → DB 有 "行政院人事行政總處組織法"。
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT law_name FROM law_articles"
            ).fetchall()
        for (db_name,) in rows:
            if law_name in db_name or db_name in law_name:
                return db_name
        return None

    def article_count(self) -> int:
        """回傳索引中的條文總數。"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM law_articles").fetchone()
        return int(row[0])

    def law_count(self) -> int:
        """回傳索引中的法規總數。"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(DISTINCT pcode) FROM law_articles"
            ).fetchone()
        return int(row[0])
