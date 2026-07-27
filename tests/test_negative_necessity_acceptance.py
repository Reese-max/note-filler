"""負例驗收：功能缺口／使用者價值／關聯知識三者缺一即明確失敗。

鎖定：
1. 有功能缺口與使用者價值，但缺少關聯知識 → 必須指出 has_related_knowledge 為 False。
2. 有關聯知識但未說明影響對象（功能缺口）或價值（使用者價值） → 必須指出缺欄。

來源綁定正確的前提下，必要性雙視角或關聯知識缺一不可通過；
錯誤訊息必須點出缺失欄位名稱，避免默默產出不完整成品。
"""
from __future__ import annotations

import pytest

from note_filler.binding_report import build_binding_report, parse_binding_report
from note_filler.correction import assemble_correction
from note_filler.gap import Gap
from note_filler.parse import Document, Paragraph
from note_filler.retrieve.models import Source
from note_filler.verify import cross_validate
from note_filler.write import WrittenSupplement


def _doc():
    return Document(
        source_path="input/note.txt",
        paragraphs=(Paragraph(0, "原稿逐字保留。"),),
        full_text="原稿逐字保留。",
    )


def _source(id: str = "law:92", level: str = "A") -> Source:
    return Source(
        id=id,
        title="行政程序法第 92 條",
        url=None,
        level=level,
        content="【片段:law:92】行政處分，係指行政機關就公法上具體事件所為之決定。",
        fetched_date="2026-07-27",
        doc_date=None,
        distance=0.1,
    )


# ---- 負例一：有功能缺口與使用者價值，但缺少關聯知識 -------------------------


def test_negative_has_gap_and_value_but_no_related_knowledge():
    """來源正確、功能缺口與使用者價值皆非空，但關聯知識為空字串。

    驗證：
    1. has_related_knowledge 明確為 False（不得因來源正確而忽略缺失）
    2. binding_ok 為 False、binding_status 為 fail
    3. at_least_one_source／has_functional_gap／has_user_value 皆為 True（不連帶污染）
    """
    gap = Gap("行政處分之定義？", "missing", "原稿未定義行政處分")
    src = _source()
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("行政處分定義參照[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    seg = product.segments[-1]
    # 組裝後 functional_gap／user_value 非空
    assert seg.functional_gap.strip(), "前置：functional_gap 應非空"
    assert seg.user_value.strip(), "前置：user_value 應非空"
    # 人工設為空關聯知識：模擬「有論點但未產出關聯知識」
    seg.related_knowledge = ""

    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]

    # 來源綁定正確：不因關聯知識缺失而假性污染來源檢查
    assert arg["checks"]["at_least_one_source"] is True
    assert arg["checks"]["source_traceable"] is True
    assert arg["checks"]["no_duplicate_sources"] is True

    # 功能缺口與使用者價值仍正常
    assert arg["checks"]["has_functional_gap"] is True
    assert arg["checks"]["has_user_value"] is True
    assert arg["functional_gap"].strip()
    assert arg["user_value"].strip()

    # 關聯知識缺失必須明確標示
    assert arg["checks"]["has_related_knowledge"] is False
    assert arg["binding_ok"] is False
    assert arg["binding_status"] == "fail"
    assert report["summary"]["all_arguments_ok"] is False


def test_negative_has_gap_and_value_but_related_knowledge_without_markers():
    """來源正確、功能缺口與使用者價值非空，但關聯知識缺少決策品質／使用者理解標記。

    驗證：
    1. has_related_knowledge 明確為 False（僅有正文但無標記不算合格關聯知識）
    2. binding_ok 為 False
    """
    gap = Gap("行政處分之定義？", "missing", "原稿未定義行政處分")
    src = _source()
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("行政處分定義參照[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    seg = product.segments[-1]
    assert seg.functional_gap.strip()
    assert seg.user_value.strip()
    # 有文字但無「支撐決策品質」與「補強使用者理解」標記
    seg.related_knowledge = "僅有正文但缺少雙標記說明"

    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]

    assert arg["checks"]["at_least_one_source"] is True
    assert arg["checks"]["has_functional_gap"] is True
    assert arg["checks"]["has_user_value"] is True
    assert arg["checks"]["has_related_knowledge"] is False
    assert arg["binding_ok"] is False
    assert arg["binding_status"] == "fail"


# ---- 負例二：有關聯知識但未說明功能缺口或使用者價值 -------------------------


def test_negative_has_related_knowledge_but_no_functional_gap():
    """來源正確、有關聯知識（含雙標記），但功能缺口為空。

    驗證：
    1. has_functional_gap 明確為 False（不得因來源與關聯知識正確而忽略）
    2. has_related_knowledge 為 True、has_user_value 為 True（不連帶污染）
    3. binding_ok 為 False、binding_status 為 fail
    """
    gap = Gap("行政處分之定義？", "missing", "原稿未定義行政處分")
    src = _source()
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("行政處分定義參照[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    seg = product.segments[-1]
    # 組裝後關聯知識非空且含雙標記
    assert seg.related_knowledge and "支撐決策品質" in seg.related_knowledge
    assert "補強使用者理解" in seg.related_knowledge
    # 功能缺口設為空：模擬「有關聯知識但未指明對應哪個功能缺口」
    seg.functional_gap = ""

    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]

    # 來源與關聯知識檢查仍正常
    assert arg["checks"]["at_least_one_source"] is True
    assert arg["checks"]["source_traceable"] is True
    assert arg["checks"]["has_related_knowledge"] is True

    # 使用者價值仍正常
    assert arg["checks"]["has_user_value"] is True
    assert arg["user_value"].strip()

    # 功能缺口缺失必須明確標示
    assert arg["checks"]["has_functional_gap"] is False
    assert arg["binding_ok"] is False
    assert arg["binding_status"] == "fail"
    assert report["summary"]["all_arguments_ok"] is False


def test_negative_has_related_knowledge_but_no_user_value():
    """來源正確、有關聯知識（含雙標記），但使用者價值為空。

    驗證：
    1. has_user_value 明確為 False（不得因來源與關聯知識正確而忽略）
    2. has_related_knowledge 為 True、has_functional_gap 為 True（不連帶污染）
    3. binding_ok 為 False
    """
    gap = Gap("行政處分之定義？", "missing", "原稿未定義行政處分")
    src = _source()
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("行政處分定義參照[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    seg = product.segments[-1]
    assert seg.related_knowledge and "支撐決策品質" in seg.related_knowledge
    assert "補強使用者理解" in seg.related_knowledge
    # 使用者價值設為空白：模擬「有關聯知識但未說明對使用者的具體價值」
    seg.user_value = "   "

    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]

    assert arg["checks"]["at_least_one_source"] is True
    assert arg["checks"]["has_functional_gap"] is True
    assert arg["checks"]["has_related_knowledge"] is True

    # 使用者價值缺失必須明確標示
    assert arg["checks"]["has_user_value"] is False
    assert not arg["user_value"].strip()
    assert arg["binding_ok"] is False
    assert arg["binding_status"] == "fail"


def test_negative_has_related_knowledge_but_both_gap_and_value_empty():
    """來源正確、有關聯知識，但功能缺口與使用者價值皆為空。

    驗證兩欄同時缺失時皆被標示，不因僅標一欄而忽略另一欄。
    """
    gap = Gap("行政處分之定義？", "missing", "原稿未定義行政處分")
    src = _source()
    product = assemble_correction(
        _doc(), [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement("行政處分定義參照[^1]。", [src.id])},
        {gap.question: cross_validate(gap.question, [src])},
    )
    seg = product.segments[-1]
    assert seg.related_knowledge and "支撐決策品質" in seg.related_knowledge
    # 兩欄同時清空
    seg.functional_gap = ""
    seg.user_value = ""

    report = parse_binding_report(build_binding_report(product))
    arg = report["arguments"][0]

    assert arg["checks"]["at_least_one_source"] is True
    assert arg["checks"]["has_related_knowledge"] is True

    assert arg["checks"]["has_functional_gap"] is False
    assert arg["checks"]["has_user_value"] is False
    assert arg["binding_ok"] is False
    assert arg["binding_status"] == "fail"
