"""根 README 安全合約驗收（issue #1）。

對應 50-persona audit 驗收條件：根目錄必須有一份 README，
讓使用者／新維護者不看原始碼就能回答：用途與非用途、
無來源不進正文規則、輸入輸出目錄與產物權威性、
來源與證據檢視方式、原稿保護與回復、安裝與測試、
Grok/provider 邊界，以及最小端到端範例。
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"


def _readme() -> str:
    return README_PATH.read_text(encoding="utf-8")


def test_root_readme_exists_and_is_utf8_text():
    """驗收 1：根目錄存在 README.md，且為可讀的非空文字。"""
    assert README_PATH.is_file(), "repo 根目錄缺少 README.md"
    text = _readme()
    assert text.strip(), "README.md 不得為空"
    assert text.startswith("#"), "README.md 應以 Markdown 標題開頭"


def test_readme_states_purpose_and_non_purpose():
    """驗收 1：README 陳述用途與明確的非用途邊界。"""
    text = _readme()
    # 用途：法律／行政／考試筆記自動補齊
    assert re.search(r"法律|行政|考試", text), "README 未說明法律/行政/考試用途"
    assert re.search(r"補齊|補充", text), "README 未說明筆記補齊功能"
    # 非用途：需有明確的「不是什麼」段落或否定式聲明
    assert re.search(r"非用途|不是|並非|不提供.*(法律意見|法律建議)", text), (
        "README 未標示非用途邊界"
    )


def test_readme_states_unsourced_claims_never_enter_canonical_notes():
    """驗收 1：明載「無來源不進正文」的安全規則與待補證標記。"""
    text = _readme()
    assert re.search(r"無來源.*(不進|不得|不寫入)|沒有來源.*(不進|不得)", text), (
        "README 未陳述無來源不進正文規則"
    )
    # 待補證降級機制必須被寫出
    assert "待補證" in text and "pending_evidence" in text, (
        "README 未說明待補證/pending_evidence 降級標記"
    )


def test_readme_explains_io_dirs_and_generated_vs_authoritative():
    """驗收 2：說明輸入/輸出目錄，並區分產物與權威來源。"""
    text = _readme()
    for token in ("data/", "output/", "metrics_output/", "docs/"):
        assert token in text, f"README 未提及目錄 {token}"
    # 輸入為權威原稿、輸出為可再生產物
    assert re.search(r"原稿|原始|authoritative|權威", text), (
        "README 未指出原稿為權威來源"
    )
    assert re.search(r"產物|generated|可再生|重建", text), (
        "README 未區分生成產物與權威來源"
    )


def test_readme_documents_provenance_fields_and_evidence_inspection():
    """驗收 3：記載來源/provenance 欄位與證據檢視方式。"""
    text = _readme()
    for token in ("[^", "level", "Level A", "url", "fetched_date"):
        assert token in text, f"README 未提及 provenance 欄位 {token}"
    # 成品內的可檢視證據機制
    assert "delivery_manifest.json" in text, "README 未提及交付回執 manifest"
    assert "binding_report" in text, "README 未提及來源綁定報告"
    assert re.search(r"追溯|traceability|source_id", text), (
        "README 未說明追溯欄位"
    )


def test_readme_explains_original_protection_and_recovery():
    """驗收 4：說明原稿不被覆寫的機制與回復/續跑方式。"""
    text = _readme()
    assert "訂正稿" in text, "README 未說明輸出為獨立訂正稿檔案"
    assert re.search(r"不會.*(覆寫|修改|更動)|不.*(覆寫|修改).*原", text), (
        "README 未說明原稿不被覆寫"
    )
    assert ".task_state" in text, "README 未提及任務狀態/續跑目錄"
    assert re.search(r"sha256|雜湊|hash", text, re.IGNORECASE), (
        "README 未說明完整性雜湊驗證"
    )
    assert re.search(r"回復|恢復|續跑|recovery", text, re.IGNORECASE), (
        "README 未說明回復/續跑"
    )


def test_readme_documents_setup_tests_and_provider_boundary():
    """驗收 5：本地安裝、測試指令、整合測試需求、provider 邊界（無機密）。"""
    text = _readme()
    assert 'pip install -e ".[dev]"' in text or "pip install -e .[dev]" in text, (
        "README 未記載 editable + dev extras 安裝指令"
    )
    assert "constraints-pinned.txt" in text, "README 未提及釘定 constraints"
    assert "pytest" in text, "README 未記載測試指令"
    assert "integration" in text, "README 未說明整合測試標記"
    assert "run_tests.sh" in text, "README 未提及 scripts/run_tests.sh"
    # provider 邊界：grok 走本機 proxy、twinkle 需環境變數 token
    assert "127.0.0.1:8318" in text, "README 未說明 grok 本機 proxy 位址"
    assert "TWINKLE_HUB_TOKEN" in text, "README 未說明 twinkle token 環境變數"
    # 不得洩漏真實 token：只允許環境變數名，不得出現賦值形式
    assert not re.search(r"TWINKLE_HUB_TOKEN\s*=\s*\S", text), (
        "README 不得在範例外寫死 token 值"
    )


def test_readme_has_minimal_end_to_end_example():
    """驗收 6：最小端到端範例（原稿 → 研究建議 → 證據檢視 → 接受的輸出）。"""
    text = _readme()
    assert "python -m note_filler" in text, "README 未給出 CLI 端到端範例指令"
    # 範例需覆蓋流程各階段的名稱
    for stage in ("研究", "證據", "訂正稿"):
        assert stage in text, f"README 範例未涵蓋階段 {stage}"


def test_readme_describes_read_only_path_and_content_classes():
    """回歸驗收：說明唯讀路徑，並可區分原文/AI 補充/有來源/待審/最終。"""
    text = _readme()
    # 唯讀性：原稿只讀不寫
    assert re.search(r"唯讀|只讀|readonly|read-only", text, re.IGNORECASE), (
        "README 未說明對原稿的唯讀路徑"
    )
    # 成品中可辨識的內容分類標記
    for marker in ("【補充】", "verified", "pending_evidence"):
        assert marker in text, f"README 未提及內容分類標記 {marker}"
