# Failing Test 驗證報告

**日期**: 2026-07-18
**執行環境**: Python 3.11.9, pytest 9.1.1, win32
**執行指令**: `pytest -m "not integration" -v --tb=short -rs`

## 結論

**不存在 failing test，修正條件未觸發。**

## 詳細結果

- 收集測試: 113 items
- 排除 (integration): 8 deselected
- 執行: 105 selected
- **105 passed, 0 failed, 0 errors, 0 xfail, 0 xpass**
- 耗時: ~4-5 秒
- 工作樹狀態: clean (on branch adng/856adfaf)

## 測試覆蓋模組

| 測試檔案 | 測試數 | 狀態 |
|---|---|---|
| test_citation_formatter.py | 1 | PASSED |
| test_cli.py | 3 | PASSED |
| test_correction.py | 11 | PASSED |
| test_deselection_guard.py | 2 | PASSED |
| test_domain.py | 6 | PASSED |
| test_e2e_acceptance.py | 2 | PASSED |
| test_export.py | 3 | PASSED |
| test_export_docx.py | 1 | PASSED |
| test_gap.py | 6 | PASSED |
| test_grading.py | 7 | PASSED |
| test_law_check.py | 7 | PASSED |
| test_law_lookup.py | 2 | PASSED |
| test_law_search.py | 7 | PASSED |
| test_llm.py | 2 | PASSED |
| test_parse.py | 3 | PASSED |
| test_pipeline.py | 2 | PASSED |
| test_questions.py | 4 | PASSED |
| test_retrieve.py | 2 | PASSED |
| test_server.py | 4 | PASSED |
| test_twinkle.py | 3 | PASSED |
| test_verify.py | 12 | PASSED |
| test_web.py | 9 | PASSED |
| test_write.py | 3 | PASSED |

## 判定

由於所有 105 個非 integration 測試全數通過且無任何異常輸出，無需進行邏輯修正。此報告作為驗證憑證。
