# 8 個整合測試逐項執行報告

> 日期: 2026-07-18
> 執行環境: `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe` (Python 3.11.9)
> 覆寫 addopts: `-o "addopts=" -m integration -v -s`
> grok proxy: `http://127.0.0.1:8318/v1` (model `grok-4.3`)，curl 確認 models endpoint 可達

## 總覽

| # | 測試 node ID | 結果 | 耗時 | 備註 |
|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | **PASSED** | 4.18s | grok 回傳含 law 之 domain 判定 |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | **PASSED** | 138.94s | 完整端到端流程，含 grok+twinkle |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | **PASSED** | 5.08s | grok 判斷缺失段落 |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | **PASSED** | 1.14s | grok proxy 連線 + PONG 驗證 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | **PASSED** | 65.89s | 完整 pipeline grok 實跑 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | **PASSED** | 9.47s | grok 生成考題 |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | **SKIPPED** | 0.03s | 缺 `GOV_AI_ENABLE_TWINKLE_MCP=1` 且未設 `TWINKLE_HUB_TOKEN` |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | **PASSED** | 5.17s | twinkle-hub API 查詢 |

**結論: 7/8 PASSED, 1/8 SKIPPED**

## 逐項詳情

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`
- **結果**: PASSED (4.18s)
- **前置條件**: grok proxy(:8318) 可達
- **實測輸出**: `1 passed in 4.18s`

### 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`
- **結果**: PASSED (138.94s)
- **前置條件**: grok proxy(:8318) + `TWINKLE_HUB_TOKEN` + `data/law_index.db`
- **實測輸出**: `1 passed in 138.94s (0:02:18)`
- **備註**: 耗時最長，為完整端到端驗收

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`
- **結果**: PASSED (5.08s)
- **前置條件**: grok proxy(:8318)
- **實測輸出**: `1 passed in 5.08s`

### 4. `tests/test_llm.py::test_grok_pong_integration`
- **結果**: PASSED (1.14s)
- **前置條件**: grok proxy(:8318)
- **實測輸出**: `1 passed in 1.14s`

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`
- **結果**: PASSED (65.89s)
- **前置條件**: grok proxy(:8318)
- **實測輸出**: `1 passed in 65.89s (0:01:05)`

### 6. `tests/test_questions.py::test_generate_questions_real_grok`
- **結果**: PASSED (9.47s)
- **前置條件**: grok proxy(:8318)
- **實測輸出**: `1 passed in 9.47s`

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`
- **結果**: SKIPPED (0.03s)
- **Skip 原因**: `需 GOV_AI_ENABLE_TWINKLE_MCP=1 且設 TWINKLE_HUB_TOKEN`
- **環境限制**: 此測試需要 twinkle-hub MCP 整合環境，當前 session 未設定相關環境變數
- **可重現條件**: 設定 `GOV_AI_ENABLE_TWINKLE_MCP=1` 並提供有效 `TWINKLE_HUB_TOKEN` 後重跑

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`
- **結果**: PASSED (5.17s)
- **前置條件**: `TWINKLE_HUB_TOKEN` 環境變數（已設定）
- **實測輸出**: `1 passed in 5.17s`
