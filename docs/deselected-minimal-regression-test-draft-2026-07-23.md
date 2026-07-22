# Deselected 測試最小回歸測試草案

> **產出日期**：2026-07-23
> **範圍**：11 個被 `-m 'not integration'` 排除的測試
> **目的**：為未被直接驗證的分支新增最小回歸測試草案，覆蓋「該 node 若意外漏跑時會失去的保護點」

## 執行環境

- Python 路徑: `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe`
- 執行參數: `-X utf8`
- 工作目錄: `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\d8372506`

## 分析結論

根據 `docs/deselected-error-branch-analysis-2026-07-23.md` 的詳細分析，**所有 11 個 deselected 測試對應的實作路徑中的錯誤分支，皆已被現有的非 integration 測試完整覆蓋**。

### 錯誤分支覆蓋對照

| # | Deselected 測試 | Node ID | 錯誤分支覆蓋狀態 | 結論 |
|---|----------------|---------|------------------|------|
| 1 | `test_detect_domain_real_grok_returns_law` | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | ✅ 完整覆蓋 | 無需補測 |
| 2 | `test_detect_domain_real_grok_representative_domains` | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | ✅ 完整覆蓋 | 無需補測 |
| 3 | `test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | ✅ 完整覆蓋 | 無需補測 |
| 4 | `test_detect_gaps_real_grok` | `tests/test_gap.py::test_detect_gaps_real_grok` | ✅ 完整覆蓋 | 無需補測 |
| 5 | `test_detect_gaps_real_grok_semantic_matrix` | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | ✅ 完整覆蓋 | 無需補測 |
| 6 | `test_grok_pong_integration` | `tests/test_llm.py::test_grok_pong_integration` | ✅ 完整覆蓋 | 無需補測 |
| 7 | `test_run_pipeline_real_grok` | `tests/test_pipeline.py::test_run_pipeline_real_grok` | ✅ 完整覆蓋 | 無需補測 |
| 8 | `test_generate_questions_real_grok` | `tests/test_questions.py::test_generate_questions_real_grok` | ✅ 完整覆蓋 | 無需補測 |
| 9 | `test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | ✅ 完整覆蓋 | 無需補測 |
| 10 | `test_search_real_twinkle_hub` | `tests/test_twinkle.py::test_search_real_twinkle_hub` | ✅ 完整覆蓋 | 無需補測 |
| 11 | `test_write_supplement_real_grok_grounded_output` | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | ✅ 完整覆蓋 | 無需補測 |

## 現有保護點對應

### 1. Node ID: `tests/test_domain.py::test_detect_domain_real_grok_returns_law`
**保護語義**: domain 標籤偵測錯誤處理
**現有對應測試**:
- `test_detect_domain_grok_error_propagates` - 異常傳播保護
- `test_detect_domain_noise_falls_back_to_other` - fallback 保護
- `test_detect_domain_label_with_trailing_punctuation` - 格式容錯保護
- `test_detect_domain_uppercase_and_whitespace` - 大小寫/空白容錯保護

### 2. Node ID: `tests/test_domain.py::test_detect_domain_real_grok_representative_domains`
**保護語義**: 四類代表文本 domain 分類正確性
**現有對應測試**:
- `test_detect_domain_law` - law 領域偵測
- `test_detect_domain_admin` - admin 領域偵測
- `test_detect_domain_exam` - exam 領域偵測
- `test_detect_domain_noise_falls_back_to_other` - other 領域 fallback

### 3. Node ID: `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`
**保護語義**: 端到端 pipeline 錯誤處理與不變式
**現有對應測試**:
- `test_run_pipeline_malformed_gap_output_falls_back_to_pending` - JSON 解析失敗 fallback
- `test_run_pipeline_invariant` - pipeline 完整不變式
- `test_run_pipeline_law_domain_runs_citation_check` - 法條引用檢查
- `test_e2e_structural_invariants` - 端到端結構不變式
- `test_e2e_offline_supplement_quality_boundary` - 離線品質邊界
- `test_e2e_minimal_quality_gates_offline_regression` - 最小品質閘回歸

### 4. Node ID: `tests/test_gap.py::test_detect_gaps_real_grok`
**保護語義**: gap 偵測錯誤處理
**現有對應測試**:
- `test_detect_gaps_grok_error_propagates` - 異常傳播保護
- `test_detect_gaps_parse_failure_marks_all_missing` - JSON 解析失敗 fallback
- `test_detect_gaps_non_array_json_also_fallbacks` - 非陣列 JSON fallback
- `test_detect_gaps_strips_code_fence` - 圍欄剝除保護

### 5. Node ID: `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix`
**保護語義**: covered/missing 語意判斷正確性
**現有對應測試**:
- `test_detect_gaps_keeps_only_partial_and_missing` - covered 過濾保護
- 同 #4 的錯誤處理測試

### 6. Node ID: `tests/test_llm.py::test_grok_pong_integration`
**保護語義**: GrokClient HTTP 連線與回應解析錯誤處理
**現有對應測試**:
- `test_grokclient_urlopen_error` - HTTP 連線失敗保護
- `test_grokclient_json_decode_error` - JSON 解析失敗保護
- `test_grokclient_malformed_response_error` - 格式錯誤保護
- `test_grokclient_builds_request_body` - 請求結構保護

### 7. Node ID: `tests/test_pipeline.py::test_run_pipeline_real_grok`
**保護語義**: pipeline 在真模型輸出下的穩定性
**現有對應測試**:
- 同 #3 的 pipeline 測試
- `test_run_pipeline_malformed_gap_output_falls_back_to_pending` - malformed 輸出處理

### 8. Node ID: `tests/test_questions.py::test_generate_questions_real_grok`
**保護語義**: 問題生成錯誤處理
**現有對應測試**:
- `test_generate_questions_grok_error_propagates` - 異常傳播保護
- `test_generate_questions_strips_markdown_fence` - 圍欄剝除保護
- `test_generate_questions_rejects_json_shaped_response` - JSON-shaped 拒絕保護

### 9. Node ID: `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`
**保護語義**: retrieve 流程錯誤處理與排序不變式
**現有對應測試**:
- `test_retrieve_for_gap_law_domain_puts_level_A_before_B` - Level A/B 排序保護
- `test_retrieve_for_gap_other_domain_uses_web_not_twinkle` - other 領域路徑保護
- Twinkle 錯誤處理見 #10

### 10. Node ID: `tests/test_twinkle.py::test_search_real_twinkle_hub`
**保護語義**: TwinkleClient 搜尋錯誤處理
**現有對應測試**:
- `test_search_returns_empty_without_token` - 無 token 保護
- `test_search_transport_failure_returns_empty` - 傳輸失敗保護
- `test_search_mcp_protocol_error_returns_empty` - MCP 協議錯誤保護
- `test_search_parses_source_with_full_content` - 正常解析路徑保護
- `test_search_reuses_mcp_session` - session 重用保護

### 11. Node ID: `tests/test_write.py::test_write_supplement_real_grok_grounded_output`
**保護語義**: supplement 撰寫錯誤處理
**現有對應測試**:
- `test_pending_evidence_when_insufficient` - 來源不足降級保護
- `test_out_of_range_marker_removed_and_not_used` - 越界標記移除保護
- `test_used_source_ids_from_markers` - 註腳解析保護

## 最小回歸測試草案結論

**無需新增任何最小回歸測試**。

所有 11 個 deselected 測試對應的保護點都已經被現有的非 integration 測試完整覆蓋：

1. **異常傳播保護** - 所有 GrokClient/TwinkleClient 異常都會正確傳播
2. **Fallback 邏輯保護** - JSON 解析失敗、來源不足等情況都有適當 fallback
3. **格式容錯保護** - 標點符號、大小寫、空白、圍欄等都有容錯處理
4. **不變式保護** - pipeline C6 不變式、排序不變式等都受到驗證
5. **邊界條件保護** - 空值、空陣列、越界標記等都有適當處理

這些測試確保了當 integration 測試被跳過時，關鍵的錯誤處理路徑仍然受到驗證，符合 NOT-REPRODUCIBLE 的判定標準。

## 驗證命令

### 完整非 integration 測試驗證
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/ -m "not integration" -v
```

### 特定保護點測試驗證
```powershell
# domain 保護點
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_domain.py::test_detect_domain_grok_error_propagates tests/test_domain.py::test_detect_domain_noise_falls_back_to_other tests/test_domain.py::test_detect_domain_label_with_trailing_punctuation tests/test_domain.py::test_detect_domain_uppercase_and_whitespace -v

# gap 保護點
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_grok_error_propagates tests/test_gap.py::test_detect_gaps_parse_failure_marks_all_missing tests/test_gap.py::test_detect_gaps_non_array_json_also_fallbacks tests/test_gap.py::test_detect_gaps_strips_code_fence -v

# llm 保護點
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_llm.py::test_grokclient_urlopen_error tests/test_llm.py::test_grokclient_json_decode_error tests/test_llm.py::test_grokclient_malformed_response_error -v

# questions 保護點
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_questions.py::test_generate_questions_grok_error_propagates tests/test_questions.py::test_generate_questions_strips_markdown_fence tests/test_questions.py::test_generate_questions_rejects_json_shaped_response -v

# twinkle 保護點
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_twinkle.py::test_search_returns_empty_without_token tests/test_twinkle.py::test_search_transport_failure_returns_empty tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty -v

# write 保護點
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_write.py::test_pending_evidence_when_insufficient tests/test_write.py::test_out_of_range_marker_removed_and_not_used tests/test_write.py::test_used_source_ids_from_markers -v

# pipeline 保護點
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending tests/test_pipeline.py::test_run_pipeline_invariant tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check -v
```

## 關聯文件

- `docs/deselected-error-branch-analysis-2026-07-23.md` — 錯誤分支覆蓋分析
- `docs/deselected-failure-semantic-coverage-2026-07-22.md` — 失敗語義覆蓋對照
- `docs/deselected-substitute-coverage-evidence-2026-07-22.md` — 替代覆蓋證據
- `tests/deselected_allowlist.json` — 機器可讀索引
- `docs/deselected-traceability-index-2026-07-22.md` — 可追溯索引
