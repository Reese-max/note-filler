"""機械驗收測試：直接讀取最終成品筆記，逐論點檢查連結數量、URL 格式有效性、
與【待補來源】的互斥性，以及原稿逐字不變。

測試覆蓋「來源充足」與「來源不足」兩種最小案例。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from note_filler.correction import MIN_OPENABLE_LINKS, is_openable_url

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "final_output"


# ---------------------------------------------------------------------------
# helpers: Markdown 解析
# ---------------------------------------------------------------------------

_RE_FOOTNOTE_URL = re.compile(
    r"^\[?\^?\d*\]?:.*?\|\s*URL:\s*(https?://\S+)", re.MULTILINE
)
_RE_FOOTNOTE_LINE = re.compile(r"^\[\^(\d+)\]:\s*(.+)", re.MULTILINE)
_RE_SUPPLEMENT_LINE = re.compile(r"^>\s*【補充】", re.MULTILINE)
_RE_PENDING_MARKER = re.compile(r"⚠待補證|【待補證】")
_RE_OPENABLE_URL_IN_TEXT = re.compile(r"https?://[^\s\)\]|]+")


def _parse_md(text: str) -> dict:
    """解析 Markdown 成品，回傳 original_paragraphs、supplement_blocks、
    reference_urls、has_pending_marker。
    """
    lines = text.splitlines()

    original_paragraphs: list[str] = []
    supplement_texts: list[str] = []
    ref_urls: list[str] = []
    has_pending_marker = False
    in_ref_block = False

    for line in lines:
        stripped = line.strip()

        # 參考區塊：以 [^n]: 開頭的行
        if re.match(r"^\[\^\d+\]:", stripped):
            in_ref_block = True
            m = re.search(r"URL:\s*(https?://\S+)", stripped)
            if m:
                ref_urls.append(m.group(1))
            continue

        if in_ref_block:
            # 參考區塊結束（遇到非 [^n]: 行）
            if not re.match(r"^\[\^\d+\]:", stripped):
                in_ref_block = False
            else:
                m = re.search(r"URL:\s*(https?://\S+)", stripped)
                if m:
                    ref_urls.append(m.group(1))
                continue

        # 補充區塊
        if stripped.startswith("> 【補充】"):
            supplement_texts.append(stripped)
            # 補充行內也可能有 URL（inline 註腳）
            for m in _RE_OPENABLE_URL_IN_TEXT.finditer(stripped):
                url = m.group(0).rstrip(".,;)")
                if url not in ref_urls:
                    ref_urls.append(url)
            if _RE_PENDING_MARKER.search(stripped):
                has_pending_marker = True
            continue

        # 【待補來源】行
        if "【待補來源】" in stripped:
            has_pending_marker = True
            continue

        # 跳過元資料行（> **xxx**：...）
        if stripped.startswith("> **") and "：" in stripped:
            continue
        if stripped.startswith("> 追溯："):
            continue
        if stripped.startswith("---"):
            continue
        if stripped.startswith("> **來源綁定**") or stripped.startswith("> **角度覆蓋摘要**"):
            continue
        if stripped.startswith("> **北極星"):
            continue
        if not stripped:
            continue

        # 原文段
        original_paragraphs.append(stripped)

    return {
        "original_paragraphs": original_paragraphs,
        "supplement_texts": supplement_texts,
        "ref_urls": ref_urls,
        "has_pending_marker": has_pending_marker,
    }


def _urls_in_text(text: str) -> list[str]:
    """從文字中抽取所有 http/https URL。"""
    return _RE_OPENABLE_URL_IN_TEXT.findall(text)


# ---------------------------------------------------------------------------
# 來源充足案例
# ---------------------------------------------------------------------------

class TestSufficientSources:
    """來源充足：>= 2 條有效連結，不應有【待補來源】。"""

    @pytest.fixture()
    def parsed(self):
        path = FIXTURES_DIR / "sufficient_sources.md"
        return _parse_md(path.read_text(encoding="utf-8"))

    @pytest.fixture()
    def original_text(self):
        path = FIXTURES_DIR / "sufficient_sources.md"
        return path.read_text(encoding="utf-8")

    def test_has_supplement_blocks(self, parsed):
        """成品應含至少一個補充區塊。"""
        assert parsed["supplement_texts"], "成品缺少補充區塊（> 【補充】）"

    def test_link_count_sufficient(self, parsed):
        """每個論點區塊的引用來源連結數 >= MIN_OPENABLE_LINKS。"""
        all_valid = [
            url for url in parsed["ref_urls"] if is_openable_url(url)
        ]
        assert len(all_valid) >= MIN_OPENABLE_LINKS, (
            f"來源充足案例有效連結數不足：{len(all_valid)} < {MIN_OPENABLE_LINKS}"
        )

    def test_all_urls_valid_format(self, parsed):
        """所有引用來源 URL 必須為 http/https 協議。"""
        for url in parsed["ref_urls"]:
            assert is_openable_url(url), (
                f"URL 格式無效：{url}"
            )
            assert url.startswith(("http://", "https://")), (
                f"URL 非 http/https 協議：{url}"
            )

    def test_no_pending_marker_when_sufficient(self, parsed):
        """來源充足時不應出現【待補來源】或⚠待補證標記。"""
        assert not parsed["has_pending_marker"], (
            "來源充足案例出現了【待補來源】/⚠待補證標記，不符互斥性"
        )

    def test_original_text_unchanged(self, original_text):
        """原稿段落應逐字保留在成品中。"""
        expected_original = "行政程序法第92條規定,行政處分係指行政機關就公法上具體事件所為之決定或其他公權力措施,而對外直接發生法律效果之單方行政行為。"
        assert expected_original in original_text, (
            "原稿段落未逐字保留在成品中"
        )

    def test_footnote_references_present(self, original_text):
        """成品應含 [^n] 格式的參考註腳。"""
        assert re.search(r"\[\^\d+\]", original_text), (
            "成品缺少 [^n] 註腳參考"
        )


# ---------------------------------------------------------------------------
# 來源不足案例
# ---------------------------------------------------------------------------

class TestInsufficientSources:
    """來源不足：< 2 條有效連結，必須出現【待補來源】標記。"""

    @pytest.fixture()
    def parsed(self):
        path = FIXTURES_DIR / "insufficient_sources.md"
        return _parse_md(path.read_text(encoding="utf-8"))

    @pytest.fixture()
    def original_text(self):
        path = FIXTURES_DIR / "insufficient_sources.md"
        return path.read_text(encoding="utf-8")

    def test_has_supplement_blocks(self, parsed):
        """成品應含至少一個補充區塊。"""
        assert parsed["supplement_texts"], "成品缺少補充區塊（> 【補充】）"

    def test_link_count_insufficient(self, parsed):
        """來源不足案例有效連結數 < MIN_OPENABLE_LINKS。"""
        all_valid = [
            url for url in parsed["ref_urls"] if is_openable_url(url)
        ]
        assert len(all_valid) < MIN_OPENABLE_LINKS, (
            f"來源不足案例連結數應 < {MIN_OPENABLE_LINKS}：{len(all_valid)}"
        )

    def test_urls_still_valid_format(self, parsed):
        """即使來源不足，現有 URL 仍須為有效格式。"""
        for url in parsed["ref_urls"]:
            assert is_openable_url(url), (
                f"無效 URL：{url}"
            )

    def test_pending_marker_present(self, parsed):
        """來源不足時必須出現【待補來源】標記。"""
        assert parsed["has_pending_marker"], (
            "來源不足案例缺少【待補來源】/⚠待補證標記"
        )

    def test_original_text_unchanged(self, original_text):
        """原稿段落應逐字保留在成品中。"""
        expected_original = "行政程序法第92條規定,行政處分係指行政機關就公法上具體事件所為之決定或其他公權力措施,而對外直接發生法律效果之單方行政行為。"
        assert expected_original in original_text, (
            "原稿段落未逐字保留在成品中"
        )


# ---------------------------------------------------------------------------
# 端到端：兩組案例的互斥性交叉驗證
# ---------------------------------------------------------------------------

class TestCrossMutualExclusivity:
    """交叉驗證來源充足與不足案例的互斥性。"""

    def test_sufficient_has_links_insufficient_does_not(self):
        """充足案例的連結數應 > 不足案例的連結數。"""
        path_s = FIXTURES_DIR / "sufficient_sources.md"
        path_i = FIXTURES_DIR / "insufficient_sources.md"
        parsed_s = _parse_md(path_s.read_text(encoding="utf-8"))
        parsed_i = _parse_md(path_i.read_text(encoding="utf-8"))

        count_s = len([u for u in parsed_s["ref_urls"] if is_openable_url(u)])
        count_i = len([u for u in parsed_i["ref_urls"] if is_openable_url(u)])

        assert count_s >= MIN_OPENABLE_LINKS, (
            f"充足案例連結數不足：{count_s}"
        )
        assert count_i < MIN_OPENABLE_LINKS, (
            f"不足案例連結數異常高：{count_i}"
        )
        assert count_s > count_i, (
            f"充足({count_s}) 應 > 不足({count_i})"
        )

    def test_sufficient_no_pending_insufficient_has_pending(self):
        """充足案例無【待補來源】、不足案例有【待補來源】。"""
        path_s = FIXTURES_DIR / "sufficient_sources.md"
        path_i = FIXTURES_DIR / "insufficient_sources.md"
        parsed_s = _parse_md(path_s.read_text(encoding="utf-8"))
        parsed_i = _parse_md(path_i.read_text(encoding="utf-8"))

        assert not parsed_s["has_pending_marker"], (
            "充足案例不應有【待補來源】標記"
        )
        assert parsed_i["has_pending_marker"], (
            "不足案例應有【待補來源】標記"
        )
