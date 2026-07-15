# tests/test_citation_formatter.py
import hashlib

from note_filler.retrieve.models import Source
from note_filler.citation_formatter import build_reference_lines


def _make_source(id: str, title: str, url: str | None, level: str, content: str) -> Source:
    return Source(
        id=id,
        title=title,
        url=url,
        level=level,
        content=content,
        fetched_date="2026-07-15",
        doc_date=None,
        distance=0.0,
    )


def test_build_reference_lines_two_sources():
    long_content = "本法所稱行政處分,係指行政機關就公法上具體事件所為之決定而對外直接發生法律效果之單方行政行為。" * 5
    sources = [
        _make_source(
            "s1",
            "行政程序法",
            "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0030055",
            "A",
            "行政程序法第九十二條:本法所稱行政處分,係指行政機關就公法上具體事件所為之決定。",
        ),
        _make_source(
            "s2",
            "立法院議案關係文書",
            "https://ppg.ly.gov.tw/ppg/bills/12345",
            "B",
            long_content,
        ),
    ]

    result = build_reference_lines(sources)
    lines = result.split("\n")

    # 兩個 Source -> 兩行
    assert len(lines) == 2

    # 序號:依序 [^1] [^2]
    assert lines[0].startswith("[^1]: ")
    assert lines[1].startswith("[^2]: ")

    # Level 正確
    assert "[Level A]" in lines[0]
    assert "[Level B]" in lines[1]

    # 標題
    assert "行政程序法" in lines[0]
    assert "立法院議案關係文書" in lines[1]

    # URL 正確
    assert "URL: https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0030055" in lines[0]
    assert "URL: https://ppg.ly.gov.tw/ppg/bills/12345" in lines[1]

    # Date:doc_date 優先,否則 fetched_date(此處兩筆 doc_date 皆 None → 用 fetched_date)
    assert "Date: 2026-07-15" in lines[0]
    assert "Date: 2026-07-15" in lines[1]

    # Hash = sha1(content)[:8]
    expected_hash = hashlib.sha1(sources[0].content.encode("utf-8")).hexdigest()[:8]
    assert f"Hash: {expected_hash}" in lines[0]

    # Evidence 取 content 前 100 字(長內容需被截斷)
    assert f"Evidence: {sources[1].content[:100]}" in lines[1]
    assert len(sources[1].content) > 100  # 確認確實有截斷發生
