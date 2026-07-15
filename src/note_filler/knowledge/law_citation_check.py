# -*- coding: utf-8 -*-
"""法規引用正確性核對：抽取公文法條引用，與法規庫核對條號存在性與罰則一致性，杜絕法規幻覺。

直擊 AI 公文最致命的失敗模式——引用錯誤法條（如把「一千二百~六千」罰則掛到不相干的條號）。
"""

import re

from note_filler.knowledge.law_lookup import LawLookup, _normalize_article_no

_LAW_CITE_RE = re.compile(
    r"([一-鿿]{2,16}(?:法|條例|細則|辦法|規則|準則|自治條例))第(\S{1,8})條"
)
_LEAD_VERB_RE = re.compile(r"^(?:依據|違反|觸犯|有違|牴觸|依|按|據|稱)")
_MONEY_RE = re.compile(
    r"[\d一二三四五六七八九十百千萬兩零]+元以上[\d一二三四五六七八九十百千萬兩零]+元以下"
)
_ANAPHORA = ("同法", "本法", "該法", "前法")

_LAW_WARNING_PREFIX = (
    "> ⚠️ **法規引用核對未通過**（與全國法規資料庫不符，發文前請承辦人務必核對）：\n"
)


def extract_law_citations(draft: str) -> list[dict]:
    """抽取公文中的法條引用（去前導動詞，保留指代詞），回傳含位置的清單。"""
    citations = []
    for match in _LAW_CITE_RE.finditer(draft or ""):
        name = _LEAD_VERB_RE.sub("", match.group(1)).strip()
        citations.append(
            {
                "law_name": name,
                "article_no": match.group(2),
                "start": match.start(),
                "end": match.end(),
            }
        )
    return citations


def check_law_citations(text: str, lookup: LawLookup) -> list[dict]:
    """核對每個法條引用：條號是否存在、引用附近的罰則金額是否與真實條文一致。

    回傳問題清單，每筆含 law_name / article_no / kind（article_not_found | penalty_mismatch）/ detail。
    指代詞（同法/本法）以前文最近的完整法規名解析。法規名不在庫者不誤報。
    """
    issues = []
    last_full = None
    for cite in extract_law_citations(text):
        law = cite["law_name"]
        if law in _ANAPHORA:
            if not last_full:
                continue
            law = last_full
        else:
            last_full = law

        article = _normalize_article_no(cite["article_no"])  # 正規化為標準條號（五十九→59）
        real = lookup.lookup_article(law, article)
        if real is None:
            if lookup.law_exists(law):
                issues.append(
                    {
                        "law_name": law,
                        "article_no": article,
                        "kind": "article_not_found",
                        "detail": f"《{law}》查無第 {article} 條（疑似條號幻覺）",
                    }
                )
            # 法規名不在庫（簡稱/未收錄）→ 不確定，不誤報
            continue

        real_money = set(_MONEY_RE.findall(real))
        window = text[cite["end"] : cite["end"] + 70]
        for claimed in _MONEY_RE.findall(window):
            if claimed not in real_money:
                issues.append(
                    {
                        "law_name": law,
                        "article_no": article,
                        "kind": "penalty_mismatch",
                        "detail": f"《{law}》第 {article} 條實際無「{claimed}」之罰則（與法規庫不符）",
                    }
                )
    return issues


def annotate_law_mismatches(draft: str, lookup) -> str:
    """若法條引用與法規庫不符，於草稿最前加註明顯警告（不刪原文，交承辦人核定）。"""
    issues = check_law_citations(draft, lookup)
    if not issues:
        return draft
    seen = set()
    lines = []
    for issue in issues:
        key = (issue["law_name"], issue["article_no"], issue["kind"], issue["detail"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"> - {issue['detail']}\n")
    return _LAW_WARNING_PREFIX + "".join(lines) + "\n" + draft
