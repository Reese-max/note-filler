"""排除範圍（deselected integration）correctness 盲區回歸。

鎖定對象：`tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`
（預設 `-m 'not integration'` 排除；見 `tests/deselected_allowlist.json` #7）。

具體盲區：該 integration smoke 的三道斷言對 **空清單** 皆為 vacuous True：

    assert all(isinstance(s, Source) for s in out)
    assert all(s.level in ("A", "B") for s in out)
    keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
    assert keys == sorted(keys)

因此「檢索全滅」不會被該 smoke 攔截。若日常僅跑非 integration 集合，
連 smoke 本身都不執行，更無法證明 law 領域 Level A 路徑仍可用。

本檔兩個回歸：
1. 純邏輯：重現 vacuous pass（證明未強化斷言 = 驗證缺口）。
2. 生產不變量（failing-first 候選）：law + 真實 LawLookup 不得回空、
   必須含 Level A。若此測失敗，即為可歸因於「排除/弱 smoke」的 correctness 盲區。

判定：若 (2) 穩定 PASS → 產品缺陷路徑 **NOT-REPRODUCIBLE**；
vacuous 設計缺口仍列為「真實驗證缺口」（見 docs/）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from note_filler.gap import Gap
from note_filler.knowledge.law_lookup import LawLookup
from note_filler.llm import FakeLLM
from note_filler.retrieve import _LEVEL_RANK, retrieve_for_gap
from note_filler.retrieve.models import Source

LAW_DB = Path(__file__).resolve().parents[1] / "data" / "law_index.db"

# 與 deselected #7 相同 gap 文案，降低「換 query 誤判」變因
_GAP = Gap(
    question="行政處分附款的容許界限為何?",
    status="missing",
    reason="",
)


class _EmptyTwinkle:
    """Twinkle 全滅：隔離「只靠 law Level A」的正確性路徑。"""

    def search(self, query: str, n: int = 3) -> list[Source]:
        return []


def _integration_smoke_asserts(out: list[Source]) -> None:
    """逐字重現 deselected integration smoke 的三道斷言（test_retrieve.py）。"""
    assert all(isinstance(s, Source) for s in out)
    assert all(s.level in ("A", "B") for s in out)  # MVP 只產 A/B
    keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
    assert keys == sorted(keys)


def test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot() -> None:
    """證明：排除範圍 #7 的 smoke 斷言對 empty out 仍全部通過。

    這不是產品行為缺陷，而是「未執行/弱斷言」造成的 correctness 驗證盲區：
    檢索全滅時 smoke 仍綠燈。
    """
    empty: list[Source] = []
    _integration_smoke_asserts(empty)  # 若此行失敗，代表 smoke 已強化、盲區關閉
    # 明示：empty 滿足 smoke ⇒ 單靠該 deselected 測無法證明有任何來源
    assert empty == []


@pytest.mark.skipif(not LAW_DB.exists(), reason="缺 data/law_index.db,無法驗 law Level A 路徑")
def test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty() -> None:
    """Failing-first 候選：law 領域 + 真實 LawLookup 不得被 vacuous empty 掩蓋。

    前置：FakeLLM 固定 keyword、Twinkle 回空、LawLookup(data/law_index.db)。
    預期（現況健康時 PASS）：至少一筆 Level A。
    若失敗：在預設排除 #7 且 smoke 允許 empty 的前提下，日常 CI 看不到此 correctness 缺口。
    """
    law = LawLookup(str(LAW_DB))
    llm = FakeLLM(['{"keyword": "行政處分", "law_name": "行政程序法"}'])
    out = retrieve_for_gap(_GAP, "law", _EmptyTwinkle(), law, llm)

    # 對照：同一 out 若套 smoke 三斷言，在 empty 時仍會過；此處強制非空 + Level A
    _integration_smoke_asserts(out)
    assert out, (
        "CORRECTNESS 盲區重現：law+LawLookup 回空，但 deselected smoke 的 "
        "all()/sort 對 empty 仍 vacuous PASS；預設 -m 'not integration' 不會跑到此路徑"
    )
    assert any(s.level == "A" for s in out), (
        "law 領域應至少產出 Level A 法條來源；否則僅靠排除的 smoke 無法攔截"
    )
    assert all(s.level == "A" for s in out), (
        "Twinkle 已隔離為空時，結果應全為 Level A（不得混入未定義 level）"
    )
