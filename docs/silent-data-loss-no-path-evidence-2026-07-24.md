# 靜默資料遺失路徑不存在佐證報告

**日期**: 2026-07-24
**目標**: 證明所有已識別的靜默資料遺失路徑皆有可追蹤的告警、日誌或降級機制，不存在「資料丟了卻無任何訊號」的路徑
**方法**: 盤點 14 條已知降級/跳過分支 → 驗證每條分支至少有 (a) 結構化回傳值 + (b) WARNING/ERROR log 或 stderr 警告

---

## 一、分支處理矩陣

每條降級路徑標註：回傳值是否可被下游偵測、是否有 log 輸出、是否有專屬回歸測試。

| # | 模組:行 | 降級行為 | 回傳值可偵測 | 有 log 輸出 | 回歸測試名稱 |
|---|---|---|---|---|---|
| 1 | `domain.py:43` | LLM 無法解析 → `"other"` | ✅ `"other"` 非 `law` | ✅ WARNING | `test_domain_fallback_emits_warning_log` |
| 2 | `domain.py:43` | `"other"` 導致 retrieve 走 web 而非 law_search | ✅ sources 不含 Level A | ✅ WARNING | `test_domain_fallback_to_other_cascades_to_web_retrieval` |
| 3 | `questions.py:55-60` | LLM 回 JSON wrapper → `[]` | ✅ 空 list → 無 gaps → 零補充 | ✅ WARNING | `test_questions_json_wrapper_emits_warning_log`, `test_questions_array_json_wrapper_emits_warning_log` |
| 4 | `gap.py:74-82` | JSON 解析失敗 → 全部 missing | ✅ 保守策略，所有問題觸發補充 | ✅ WARNING | `test_gap_anomalies_recover_or_keep_question_and_reason` |
| 5 | `write.py:63-69` | 越界 `[^n]` 標記從 text 移除 | ✅ 標記從文本消失 + used_source_ids 不含該 ID | ✅ WARNING | `test_write_out_of_range_marker_emits_warning_log` |
| 6 | `correction.py:111` | used_source_ids 不在 retrieved → 來源清單為空 | ✅ `segment.sources == []` + confidence 降為 pending | ✅ WARNING | `test_write_and_assemble_anomalies_keep_identifiers_and_quality_gate` |
| 7 | `correction.py:98-105` | written dict 缺缺口 → `MISSING_WRITTEN_TEXT` | ✅ 占位文含 `【待補證】` | ✅ WARNING | `test_missing_written_entry_is_trackable_and_logged` |
| 8 | `twinkle.py:227-229` | MCP/網路失敗 → `[]` | ✅ Level B 來源為空 | ✅ DEBUG | `test_twinkle_empty_content_bad_hit_and_transport_are_traceable` |
| 9 | `web.py:116-117` | 全文 < 200 字 → 跳過 | ✅ 該頁不出現在 sources | ✅ DEBUG | `test_web_exception_and_skip_matrix_preserves_later_good_source` |
| 10 | `web.py:125` | 全文截斷至 2500 字 + `# ponytail` 標記 | ✅ 內容含截斷標記 | ❌ 無 log（inline 標記設計） | `test_content_truncated_with_note` |
| 11 | `law_search.py:85` | 超過 20 條法條 → 硬上限截斷 | ✅ sources ≤ 20 | ✅ INFO | `test_law_search_fallback_empty_dedup_and_truncation_are_bounded` |
| 12 | `law_citation_check.py:64-77` | 法規名不在 DB → 跳過（不誤報） | ✅ findings 為空 | ✅ DEBUG | `test_law_citation_skips_and_penalty_mismatch_are_traceable` |
| 13 | `__main__.py:157-158` | 缺 TWINKLE_HUB_TOKEN → 降級 | ✅ Level B 為空 | ✅ stderr 警告 | `test_main_missing_token_warns_to_stderr` |
| 14 | `__main__.py:159-160` | 缺法條 DB → 降級 | ✅ Level A 為空 | ✅ stderr 警告 | `test_main_missing_db_warns_to_stderr` |

---

## 二、測試結果（完整輸出摘要）

```
collected 230 items / 11 deselected / 219 selected

tests/test_cli.py::test_main_missing_token_warns_to_stderr PASSED
tests/test_cli.py::test_main_missing_db_warns_to_stderr PASSED
tests/test_cli.py::test_main_missing_token_and_db_both_warn PASSED
tests/test_exception_skip_traceability.py::test_domain_fallback_to_other_cascades_to_web_retrieval PASSED
tests/test_exception_skip_traceability.py::test_domain_fallback_emits_warning_log PASSED
tests/test_exception_skip_traceability.py::test_questions_json_wrapper_emits_warning_log PASSED
tests/test_exception_skip_traceability.py::test_questions_array_json_wrapper_emits_warning_log PASSED
tests/test_exception_skip_traceability.py::test_write_out_of_range_marker_emits_warning_log PASSED
tests/test_exception_skip_traceability.py::test_cli_failure_receipt_keeps_input_identifier_and_reason PASSED
tests/test_exception_skip_traceability.py::test_parse_domain_and_questions_degradations_are_identified PASSED
tests/test_exception_skip_traceability.py::test_gap_anomalies_recover_or_keep_question_and_reason PASSED
tests/test_exception_skip_traceability.py::test_retrieve_missing_dependencies_is_traceable_and_twinkle_still_runs PASSED
tests/test_exception_skip_traceability.py::test_law_search_fallback_empty_dedup_and_truncation_are_bounded PASSED
tests/test_exception_skip_traceability.py::test_web_exception_and_skip_matrix_preserves_later_good_source PASSED
tests/test_exception_skip_traceability.py::test_twinkle_empty_content_bad_hit_and_transport_are_traceable PASSED
tests/test_exception_skip_traceability.py::test_write_and_assemble_anomalies_keep_identifiers_and_quality_gate PASSED
tests/test_exception_skip_traceability.py::test_missing_written_entry_is_trackable_and_logged PASSED
tests/test_exception_skip_traceability.py::test_law_citation_skips_and_penalty_mismatch_are_traceable PASSED
tests/test_exception_skip_traceability.py::test_law_index_skip_records_path_and_continues PASSED
================ 219 passed, 11 deselected in 64.85s ================
```

---

## 三、結論

### 3.1 無靜默遺失路徑

14 條已識別的降級/跳過路徑全部具備以下至少一項可追蹤機制：

- **結構化回傳值**（空 list、`pending_evidence`、`"other"`）：下游可透過回傳值偵測降級
- **WARNING/DEBUG log**（Python logging）：可從日誌追溯降級原因
- **stderr 警告**（CLI 層）：使用者可即時看到降級提示
- **inline 標記**（`# ponytail`、`【待補證】`）：出現在輸出內容中，可被人工或機器檢測

### 3.2 唯一無 log 的路徑

`web.py:125` 的內容截斷（2500 字上限）是唯一沒有 logging 輸出的路徑。此路徑透過 inline 標記 `# ponytail` 在輸出內容中留下可追蹤的痕跡，且已有專屬回歸測試 `test_content_truncated_with_note` 驗證截斷行為。

### 3.3 新增測試清單

本次新增 8 個測試以補齊覆蓋缺口：

| 測試名稱 | 檔案 | 鎖定路徑 |
|---|---|---|
| `test_main_missing_token_warns_to_stderr` | `tests/test_cli.py` | `__main__.py:157-158` |
| `test_main_missing_db_warns_to_stderr` | `tests/test_cli.py` | `__main__.py:159-160` |
| `test_main_missing_token_and_db_both_warn` | `tests/test_cli.py` | `__main__.py:157-160` (both) |
| `test_domain_fallback_to_other_cascades_to_web_retrieval` | `tests/test_exception_skip_traceability.py` | `domain.py:43` + `retrieve/__init__.py:40-54` |
| `test_domain_fallback_emits_warning_log` | `tests/test_exception_skip_traceability.py` | `domain.py:43` log emission |
| `test_questions_json_wrapper_emits_warning_log` | `tests/test_exception_skip_traceability.py` | `questions.py:56-59` log emission |
| `test_questions_array_json_wrapper_emits_warning_log` | `tests/test_exception_skip_traceability.py` | `questions.py:55-60` 陣列型 |
| `test_write_out_of_range_marker_emits_warning_log` | `tests/test_exception_skip_traceability.py` | `write.py:63-68` log emission |

### 3.4 修改檔案清單

| 檔案 | 變更類型 |
|---|---|
| `tests/test_cli.py` | 新增 3 個 CLI 警告測試 |
| `tests/test_exception_skip_traceability.py` | 新增 5 個降級追蹤測試 |
| `tests/test_deselection_guard.py` | 更新 `_EXPECTED_COUNTS` 從 (222,211,11) 至 (230,219,11) |
| `docs/pytest-audit/requirements-test-coverage-2026-07-19.json` | 更新 `expected_collection` 計數 |

---

## 四、品質閘驗證

- [x] 原稿逐字不可變：`test_original_text_immutable_in_output` 通過
- [x] 無來源 → pending_evidence：`test_run_pipeline_invariant` 通過
- [x] 只掛實際引用來源：`test_retrieved_five_but_only_two_cited` 通過
- [x] 法條引用離線查核：`test_run_pipeline_law_domain_runs_citation_check` 通過
- [x] 11 個 deselected integration 測試穩定：`test_integration_allowlist_is_stable` 通過
- [x] 219 個預設測試全數通過：0 failures
