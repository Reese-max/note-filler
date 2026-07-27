"""負例最小案例：主張有寫但找不到來源映射、來源存在但未標出引用範圍。

鎖定：
1. 補充段引用了不存在的來源 ID → 門檻應明確失敗並指出缺失的追溯欄位。
2. 補充段有來源但 citation_spans 為空 → 門檻應明確失敗並指出缺失的引用範圍。
"""
from __future__ import annotations

import json
import logging

import pytest

from note_filler.correction import assemble_correction
from note_filler.gap import Gap
from note_filler.parse import Document, Paragraph
from note_filler.pipeline import require_traceable_note_product
from note_filler.retrieve.models import Source
from note_filler.verify import cross_validate
from note_filler.write import WrittenSupplement


def _doc():
    return Document(
        source_path="input/note.txt",
        paragraphs=(Paragraph(0, "原稿逐字保留。"),),
        full_text="原稿逐字保留。",
    )


# ---- 負例一：主張有寫但找不到來源映射 ----------------------------------------


def test_negative_claim_without_source_mapping(caplog):
    """最小負例：補充段引用了不存在的來源 ID，組裝後 source_id 宣稱存在但 sources 為空。

    驗證：
    1. require_traceable_note_product 明確 raise（不得默默過關）
    2. 錯誤訊息指出 source_id 對應缺口
    3. 缺失來源 ID 出現在稽核事件中
    """
    gap = Gap("行政處分之要件為何？", "missing", "原稿未展開")
    claim = "行政處分應符合法定要件，並保障當事人陳述意見之機會。"
    missing_id = "missing-src-TRACE-01"

    with caplog.at_level(logging.WARNING):
        product = assemble_correction(
            _doc(),
            [gap],
            {gap.question: []},  # retrieved 為空：missing_id 在此找不到
            {gap.question: WrittenSupplement(claim, [missing_id])},
            {},
        )
        with pytest.raises(RuntimeError, match="來源追溯驗證失敗") as ei:
            require_traceable_note_product(product, source="negative-claim-no-source")

    seg = product.segments[-1]
    assert claim in seg.text  # 論點存在
    assert seg.sources == []  # 來源缺失
    assert missing_id in seg.source_id  # source_id 宣稱了不存在的來源

    msg = str(ei.value)
    assert "source ID 對應失敗" in msg, f"應指出 source_id 對應缺口，實際：{msg!r}"
    assert "note_traceability_failed" in caplog.text

    # 組裝階段應留下缺失來源稽核
    audit_events = []
    for rec in caplog.records:
        try:
            payload = json.loads(rec.message)
        except (json.JSONDecodeError, TypeError):
            continue
        if payload.get("event") == "used_sources_not_forwarded":
            audit_events.append(payload)
    assert audit_events, "應有 used_sources_not_forwarded 稽核"
    assert any(
        missing_id in json.dumps(p.get("missing_source_ids", []), ensure_ascii=False)
        for p in audit_events
    ), f"稽核應列出缺失綁定 id {missing_id!r}"


# ---- 負例二：來源存在但未標出引用範圍 ----------------------------------------


def test_negative_source_exists_but_no_citation_spans():
    """最小負例：補充段有來源但 citation_spans 為空，引用範圍追溯缺失。

    驗證：
    1. require_traceable_note_product 明確 raise（不得默默過關）
    2. 錯誤訊息指出 citation_spans 遺漏的來源 ID
    """
    gap = Gap("行政處分如何定義？", "missing", "原稿未定義")
    src = Source(
        id="law:92",
        title="行政程序法第 92 條",
        url=None,
        level="A",
        content="行政處分之定義。",
        fetched_date="2026-07-27",
        doc_date=None,
        distance=0.1,
    )
    # used_source_ids 有值但 citation_spans 明確設為空 → 引用範圍缺失
    product = assemble_correction(
        _doc(),
        [gap],
        {gap.question: [src]},
        {gap.question: WrittenSupplement(
            "行政處分有法定定義。", [src.id], citation_spans=[]
        )},
        {gap.question: cross_validate(gap.question, [src])},
    )

    seg = product.segments[-1]
    assert seg.type == "supplement"
    assert [s.id for s in seg.sources] == ["law:92"]
    assert seg.citation_spans == []

    with pytest.raises(RuntimeError, match="來源追溯驗證失敗|citation_spans") as ei:
        require_traceable_note_product(product, source="negative-source-no-spans")

    msg = str(ei.value)
    assert "citation_spans 遺漏來源" in msg, (
        f"應指出 citation_spans 遺漏，實際：{msg!r}"
    )
    assert "law:92" in msg
