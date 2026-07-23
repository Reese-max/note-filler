"""開放網路來源(資安/IT/一般領域):DDG 搜尋 → trafilatura 抓全文 → LLM 分級 C/D。

硬品質閘:
- content 一律存 trafilatura 抓的「全文」,絕不存 DDG 回的 snippet/摘要(禁引用搜尋摘要)。
- 任何網路例外(search 拋錯)一律降級整體回 [](比照 twinkle);單頁 fetch 失敗只跳過該頁。
真實 impl(_ddg_search / _fetch_fulltext)需網路,不進單元測試;測試一律注入 fake。
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import date
from typing import TYPE_CHECKING, Callable

from .models import Source

if TYPE_CHECKING:  # 僅型別檢查,避免執行期循環匯入
    from ..gap import Gap
    from ..llm import LLMClient

logger = logging.getLogger(__name__)

_MIN_FULLTEXT = 200      # 全文過短視為抓取失敗/導覽頁,跳過
_CONTENT_CAP = 2500      # content 截斷上限(夠寫作;要全文再另存)
_TRUNC_NOTE = "\n# ponytail: 截 2500 字夠寫作;要全文再存檔"

_QUERY_PROMPT = (
    "把下面這個問題濃縮成一句最精簡的網路搜尋關鍵字查詢,只回那句查詢字串,"
    "不要引號、不要說明、不要標點結尾。\n\n問題:{question}"
)

_GRADE_PROMPT = (
    "你是資料來源分級員。依下列網頁全文,判斷它相對於「問題」的可信度分級。\n"
    "只輸出 JSON,格式:{{\"level\":\"C|D|drop\",\"doc_date\":\"YYYY-MM-DD 或 null\",\"reason\":\"...\"}}\n"
    "分級規準:\n"
    "  C = 官方/標準組織/原廠一手文件(如 owasp.org、NIST、CVE/NVD、RFC、官方 docs、學術論文)。\n"
    "  D = 技術媒體/個人技術部落格/問答站等可信二手整理。\n"
    "  drop = 內容農場/SEO 垃圾/與問題無關 → 丟棄不計入。\n\n"
    "問題:{question}\n\n=== 網頁全文 ===\n{text}"
)


def _strip_fence(raw: str) -> str:
    """剝除 LLM 可能包上的 ```json ... ``` 圍欄。"""
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        if s.rstrip().endswith("```"):
            s = s.rstrip()[: s.rstrip().rindex("```")]
    return s.strip()


def _extract_query(gap: "Gap", llm: "LLMClient") -> str:
    """用 llm 抽一句精簡搜尋 query;任何失敗退回 gap.question 原文。"""
    try:
        raw = llm.complete([{"role": "user", "content": _QUERY_PROMPT.format(question=gap.question)}])
        query = _strip_fence(raw).strip().strip('"').strip()
        return query or gap.question
    except Exception as exc:  # 抽取失敗不致命,退回原問題
        logger.warning("query extraction failed, falling back to raw question: %s", exc)
        return gap.question


def _grade(llm: "LLMClient", gap: "Gap", text: str) -> tuple[str, str | None]:
    """回 (level, doc_date);level ∈ {C,D,drop};解析失敗保守當 drop。"""
    raw = llm.complete([{"role": "user", "content": _GRADE_PROMPT.format(question=gap.question, text=text)}])
    try:
        data = json.loads(_strip_fence(raw))
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("grade JSON parse failed: %s | raw=%.200s", exc, raw)
        return "drop", None
    level = str(data.get("level", "drop")).strip().upper()
    if level not in ("C", "D"):
        return "drop", None
    doc_date = data.get("doc_date")
    if doc_date in (None, "", "null"):
        doc_date = None
    return level, doc_date and str(doc_date)


def search_web_sources(
    gap: "Gap",
    llm: "LLMClient",
    *,
    search: Callable[[str, int], list[dict]] | None = None,
    fetch: Callable[[str], str | None] | None = None,
    max_results: int = 5,
    max_fetch: int = 3,
) -> list[Source]:
    """開放網路檢索:回 Level C/D 的 Source。網路例外整體降級回 []。"""
    search = search or _ddg_search
    fetch = fetch or _fetch_fulltext
    try:
        query = _extract_query(gap, llm)
        hits = search(query, max_results)  # search 拋錯 → 外層 except → []
    except Exception as exc:  # noqa: BLE001 - 外部服務不得中斷主流程,比照 twinkle 降級
        logger.warning("開放網路搜尋失敗,降級為空結果: %s", exc)
        return []

    today = date.today().isoformat()
    sources: list[Source] = []
    for i, hit in enumerate(list(hits)[:max_fetch]):
        href = hit.get("href")
        if not href:
            continue
        try:
            text = fetch(href)  # 單頁 fetch 失敗只跳過該頁
        except Exception as exc:  # noqa: BLE001
            logger.debug("fetch failed for %s, skipping: %s", href, exc)
            continue
        if not text or len(text) < _MIN_FULLTEXT:  # None/空/過短 → 跳過
            continue
        try:
            level, doc_date = _grade(llm, gap, text)
        except Exception as exc:  # 分級失敗(解析/呼叫)保守跳過該頁
            logger.warning("grading failed for %s, skipping page: %s", href, exc)
            continue
        if level not in ("C", "D"):  # drop → 不計入
            continue
        content = text[:_CONTENT_CAP] + (_TRUNC_NOTE if len(text) > _CONTENT_CAP else "")
        sources.append(
            Source(
                id=f"web:{hashlib.sha1(href.encode('utf-8')).hexdigest()[:10]}",
                title=str(hit.get("title") or href),
                url=href,
                level=level,  # type: ignore[arg-type]
                content=content,  # ★ trafilatura 全文,絕非 DDG snippet
                fetched_date=today,
                doc_date=doc_date,
                distance=0.1 * (i + 1),  # 列舉序:一手/前段結果 distance 較小
            )
        )
    return sources


# ---- 真實 impl(需網路,不進單元測試;測試一律注入 fake) ----
def _ddg_search(query: str, max_results: int) -> list[dict]:
    """DDGS().text → 正規化成 [{'title','href'}];例外回 []。"""
    try:
        from ddgs import DDGS

        hits = DDGS().text(query, max_results=max_results, region="tw-tzh")
        return [{"title": h.get("title", ""), "href": h.get("href", "")} for h in hits]
    except Exception as exc:  # noqa: BLE001
        logger.warning("ddgs 搜尋失敗: %s", exc)
        return []


def _fetch_fulltext(url: str) -> str | None:
    """trafilatura 抓全文;例外/None 回 None。"""
    try:
        import trafilatura

        html = trafilatura.fetch_url(url)
        if not html:
            return None
        return trafilatura.extract(html, include_comments=False, include_tables=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("trafilatura 抓取失敗 %s: %s", url, exc)
        return None
