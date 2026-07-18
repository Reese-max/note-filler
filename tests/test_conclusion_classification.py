"""結論分類守衛：非缺陷 vs 真實驗證缺口（含缺口四要件）。

任務：逐項將既有結論分類；真實驗證缺口必須附
可重現失敗測試、預期行為、實際行為、修復後驗收命令。

機器來源：docs/pytest-audit/conclusion-classification-2026-07-19.json
人類報告：docs/conclusion-classification-2026-07-19.md
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from note_filler.retrieve import _LEVEL_RANK
from note_filler.retrieve.models import Source

_REPO = Path(__file__).resolve().parents[1]
_JSON = _REPO / "docs" / "pytest-audit" / "conclusion-classification-2026-07-19.json"
_MD = _REPO / "docs" / "conclusion-classification-2026-07-19.md"
_ALLOWLIST = _REPO / "tests" / "deselected_allowlist.json"

_ALLOWED = frozenset({"非缺陷", "真實驗證缺口"})


def _load_index() -> dict:
    assert _JSON.is_file(), f"missing classification index: {_JSON}"
    return json.loads(_JSON.read_text(encoding="utf-8"))


def _current_smoke_asserts(out: list[Source]) -> None:
    """逐字重現 deselected #7 integration smoke（test_retrieve.py）。"""
    assert all(isinstance(s, Source) for s in out)
    assert all(s.level in ("A", "B") for s in out)
    keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
    assert keys == sorted(keys)


def _strengthened_smoke_asserts(out: list[Source]) -> None:
    """修復後應納入的契約：禁止 vacuous empty，再跑既有三斷言。"""
    assert out, "retrieve smoke 不得 vacuous empty"
    _current_smoke_asserts(out)


def test_classification_index_schema_and_labels() -> None:
    data = _load_index()
    assert data["schema"] == "note-filler.conclusion-classification/v1"
    items = data["items"]
    assert len(items) == 9  # C1–C6, C7-product, C7-verification, C8

    labels = [row["classification"] for row in items]
    assert set(labels) <= _ALLOWED
    assert labels.count("真實驗證缺口") == 1
    assert labels.count("非缺陷") == 8

    summary = data["summary"]
    assert summary["非缺陷"] == 8
    assert summary["真實驗證缺口"] == 1


def test_classification_covers_all_eight_allowlist_nodes() -> None:
    data = _load_index()
    allowlist = json.loads(_ALLOWLIST.read_text(encoding="utf-8"))
    allow_ids = {row["test_id"] for row in allowlist}
    classified_ids = {row["node_id"] for row in data["items"]}
    assert classified_ids == allow_ids


def test_non_defect_items_have_no_gap_package() -> None:
    data = _load_index()
    for row in data["items"]:
        if row["classification"] == "非缺陷":
            assert row.get("gap_package") is None, row["id"]
            assert row.get("product_defect_reproducible") is False


def test_true_gap_items_have_full_package() -> None:
    data = _load_index()
    gaps = [row for row in data["items"] if row["classification"] == "真實驗證缺口"]
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap["id"] == "C7-verification"
    pkg = gap["gap_package"]
    assert pkg is not None
    assert pkg["expected_behavior"].strip()
    assert pkg["actual_behavior"].strip()
    assert len(pkg["repro_failing_tests"]) >= 2
    assert len(pkg["post_fix_acceptance_commands"]) >= 3
    # 四要件測試必須指向本模組可收集 node
    for tid in pkg["repro_failing_tests"]:
        assert tid.startswith("tests/test_conclusion_classification.py::")


def test_human_report_exists_and_mentions_both_labels() -> None:
    assert _MD.is_file()
    text = _MD.read_text(encoding="utf-8")
    assert "非缺陷" in text
    assert "真實驗證缺口" in text
    assert "C7-verification" in text
    assert "test_gap_c7_strengthened_contract_fails_on_empty" in text


# ---------------------------------------------------------------------------
# C7-verification 四要件：可重現「實際 vs 預期」行為
# ---------------------------------------------------------------------------
def test_gap_c7_current_smoke_vacuous_pass_on_empty() -> None:
    """實際行為：現行 smoke 對 empty 全綠（vacuous）→ 缺口仍開時本測 PASSED。

    修復後（smoke 改為要求非空）本測應改寫或改為期望 raise；
    在缺口關閉前，此測通過即證明「實際行為」可重現。
    """
    empty: list[Source] = []
    _current_smoke_asserts(empty)
    assert empty == []


def test_gap_c7_strengthened_contract_fails_on_empty() -> None:
    """可重現失敗：修復後契約對 empty 必須 AssertionError（預期行為鎖定）。

    這是「真實驗證缺口」要求的可重現失敗測試：
    - 預期：非空契約拒絕 []
    - 實際（對照）：現行 smoke 不拒絕 []（見上一測）
    """
    empty: list[Source] = []
    with pytest.raises(AssertionError, match="vacuous empty"):
        _strengthened_smoke_asserts(empty)


def test_gap_c7_package_acceptance_commands_are_non_empty_shell() -> None:
    data = _load_index()
    gap = next(r for r in data["items"] if r["id"] == "C7-verification")
    cmds = gap["gap_package"]["post_fix_acceptance_commands"]
    joined = "\n".join(cmds)
    assert "not integration" in joined
    assert "test_gap_c7" in joined or "test_conclusion_classification" in joined
    assert "筆記補齊" in joined or "python.exe" in joined.lower() or "$py" in joined
