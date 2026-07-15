# src/note_filler/citation_formatter.py
from __future__ import annotations

import hashlib

REFERENCE_SECTION_HEADING = "### 參考來源 (AI 引用追蹤)"


def build_reference_lines(sources: list) -> str:
    """把 Source 清單轉成引用行字串(純函式,無副作用)。

    每行格式:
        [^{i}]: [Level {level}] {title} | URL: {url} | Date: {doc_date or fetched_date} | Hash: {sha1(content)[:8]} | Evidence: {content[:100]}

    - i 依 sources 順序從 1 起算
    - url 為 None 時省略 " | URL: ..." 區段
    - Date 取 doc_date,否則 fetched_date(必存在,url 為 None 時仍保留)
    - Hash 為 content 的 sha1 前 8 碼(utf-8 編碼)
    - Evidence 取 content 前 100 字,換行壓成空白後 strip
    多行以 "\\n" 串接;空清單回傳空字串。
    """
    lines: list[str] = []
    for i, src in enumerate(sources, start=1):
        content = src.content or ""
        content_hash = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
        evidence = content[:100].replace("\n", " ").strip()
        url_part = f" | URL: {src.url}" if src.url else ""
        date = src.doc_date or src.fetched_date
        lines.append(
            f"[^{i}]: [Level {src.level}] {src.title}"
            f"{url_part} | Date: {date} | Hash: {content_hash} | Evidence: {evidence}"
        )
    return "\n".join(lines)


def build_reference_block(sources: list) -> str:
    """在引用行前加上參考來源標題;無來源時回傳空字串。"""
    lines = build_reference_lines(sources)
    if not lines:
        return ""
    return REFERENCE_SECTION_HEADING + "\n" + lines
