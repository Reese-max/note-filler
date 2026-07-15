"""Level A 法條原文來源:用 LLM 從缺口問題抽關鍵詞,查法條全文包成 Source。"""

from __future__ import annotations

import datetime
import json

from ..gap import Gap
from ..llm import LLMClient
from .models import Source

_PROMPT = """你是法律檢索助手。閱讀下面的問題,抽出「一個」最適合拿去對法條全文做關鍵詞\
檢索的中文關鍵詞(名詞優先,例如「附款」「行政處分」「信賴保護」),並判斷問題是否\
明顯屬於某一部法律(若是就給出完整法規名稱,例如「行政程序法」;若不確定給 null)。

只輸出 JSON 物件,不要任何額外文字或 markdown 圍欄,格式:
{{"keyword": "<關鍵詞>", "law_name": "<法規名稱或 null>"}}

=== 問題 ===
{question}
"""


def _parse_llm(raw: str) -> tuple[str, str | None]:
    """解析 LLM 回應,回 (keyword, law_name)。非 JSON 時整串當關鍵詞、law_name=None。"""
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        if s.rstrip().endswith("```"):
            s = s.rstrip()[: s.rstrip().rindex("```")]
        s = s.strip()
    try:
        data = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return raw.strip(), None
    if not isinstance(data, dict):
        return raw.strip(), None
    keyword = str(data.get("keyword") or "").strip()
    law_name = data.get("law_name")
    law_name = str(law_name).strip() if law_name else None
    return keyword, law_name


def search_law_sources(gap: Gap, llm: LLMClient, law, limit: int = 4) -> list[Source]:
    """從 gap.question 抽關鍵詞,查法條全文,回 Level A 的 Source 清單。"""
    raw = llm.complete([{"role": "user", "content": _PROMPT.format(question=gap.question)}])
    keyword, law_name = _parse_llm(raw)
    if not keyword:
        return []

    rows = law.search_articles(keyword, limit, law_name)
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
