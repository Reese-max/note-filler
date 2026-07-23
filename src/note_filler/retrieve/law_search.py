"""Level A 法條原文來源:用 LLM 從缺口問題抽關鍵詞,查法條全文包成 Source。"""

from __future__ import annotations

import datetime
import json
import logging

from ..audit import audit_event
from ..gap import Gap
from ..llm import LLMClient
from .models import Source

logger = logging.getLogger(__name__)

_PROMPT = """你是法律檢索助手。閱讀下面的問題,抽出「2~4 個」最適合拿去對法條全文做\
關鍵詞檢索的中文關鍵詞(名詞優先,並涵蓋問題的不同面向/同義詞,例如聽證相關題可給\
["聽證","陳述意見"]),並判斷問題是否明顯屬於某一部法律(若是就給出完整法規名稱,\
例如「行政程序法」;若不確定給 null)。

只輸出 JSON 物件,不要任何額外文字或 markdown 圍欄,格式:
{{"keywords": ["<詞1>", "<詞2>", ...], "law_name": "<法規名稱或 null>"}}

=== 問題 ===
{question}
"""


def _parse_llm(raw: str) -> tuple[list[str], str | None]:
    """解析 LLM 回應,回 (keywords, law_name)。

    相容舊格式(單一 "keyword" 欄位包成單元素 list);非 JSON/非 dict 時整串當單一
    關鍵詞。過濾空字串、保序去重。
    """
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        if s.rstrip().endswith("```"):
            s = s.rstrip()[: s.rstrip().rindex("```")]
        s = s.strip()
    law_name = None
    try:
        data = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        data = None
    if isinstance(data, dict):
        raw_kws = data.get("keywords")
        if raw_kws is None:  # 相容舊單詞格式
            single = data.get("keyword")
            raw_kws = [single] if single else []
        elif not isinstance(raw_kws, list):
            raw_kws = [raw_kws]
        ln = data.get("law_name")
        law_name = str(ln).strip() if ln else None
    else:  # 非 JSON/非 dict:整串當單一關鍵詞
        logger.warning("law_search LLM parse: non-JSON response treated as keyword: %.100s", raw)
        raw_kws = [raw.strip()]
    keywords = list(dict.fromkeys(k for k in (str(x).strip() for x in raw_kws) if k))
    return keywords, law_name


def search_law_sources(gap: Gap, llm: LLMClient, law, limit: int = 25) -> list[Source]:
    """從 gap.question 抽多個關鍵詞,各查法條全文後 union 去重,回 Level A 的 Source 清單。"""
    raw = llm.complete([{"role": "user", "content": _PROMPT.format(question=gap.question)}])
    keywords, law_name = _parse_llm(raw)
    if not keywords:
        audit_event(
            logger,
            "law_search_skipped",
            gap.question,
            reason="no keywords; returning empty",
        )
        return []

    seen: set[tuple[str, str]] = set()
    rows: list[dict] = []
    for kw in keywords:
        # ponytail: law_name=null 會全庫 LIKE,理想條可能被他法洗掉;升級路徑=admin 法規白名單,觀察到再做
        for r in law.search_articles(kw, limit, law_name):
            key = (r["pcode"], r["article_no"])
            if key in seen:
                audit_event(
                    logger,
                    "law_source_deduplicated",
                    f"law:{key[0]}:{key[1]}",
                    level=logging.INFO,
                    question=gap.question,
                    keyword=kw,
                )
                continue
            seen.add(key)
            rows.append(r)
    if len(rows) > 20:
        audit_event(
            logger,
            "law_sources_truncated",
            gap.question,
            level=logging.INFO,
            found=len(rows),
            kept=20,
            omitted_ids=[f"law:{r['pcode']}:{r['article_no']}" for r in rows[20:]],
        )
    rows = rows[:20]  # ponytail: 上限 20 條夠 MVP;真爆量再分頁

    today = datetime.date.today().isoformat()
    return [
        Source(
            id=f"law:{r['pcode']}:{r['article_no']}",
            title=f"《{r['law_name']}》第{r['article_no']}條",
            url=f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={r['pcode']}",
            level="A",
            content=r["article_text"],
            fetched_date=today,
            doc_date=None,
            distance=0.1 * (i + 1),
        )
        for i, r in enumerate(rows)
    ]
