# 程式碼路徑到驗證測試對照表

日期：2026-07-24
範圍：`src/note_filler/**` 全部資料流異常/跳過/降級路徑
目標：證明每個可能造成資料未處理、未持久化、未轉送或未記錄之路徑均有非靜默處置及對應測試

## 方法論

1. 掃描全部 `audit_event()` 呼叫點（共 61 處），逐一對應是否有測試覆蓋
2. 識別 13 條未覆蓋路徑，新增 14 個測試（含 `twinkle_source_content_empty` 之 mock 路徑）補齊
3. 全量測試結果：266 passed, 11 deselected（均為 integration 測試，有獨立替代覆蓋）

## 風險分類定義

| 代號 | 意義 |
|------|------|
| U-L | 未記錄：事件未被 audit_event 追蹤 |
| U-P | 未持久化：資料未寫入磁碟或資料庫 |
| U-F | 未轉送：資料未傳遞到下游階段 |
| U-H | 未處理：異常未被捕獲或降級 |

## 全路徑對照表

### CLI 層 (`src/note_filler/__main__.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 1 | 64 | `delivery_receipt_replaced` | U-L | 輸出目錄已有 manifest | 覆蓋舊 receipt + audit | `test_delivery_receipt_replaced` | `test_fault_injection.py` |
| 2 | 109 | `input_directory_skipped` | U-L | 目錄無 .txt/.docx | audit + 跳過該目錄 | `test_input_directory_skipped` | `test_fault_injection.py` |
| 3 | 121 | `input_file_deduplicated` | U-L | 同路徑重複出現 | audit + 去重 | `test_input_file_deduplicated` | `test_fault_injection.py` |
| 4 | 201 | `file_processing_failed` | U-H | process_file 拋例外 | audit + stderr + failed receipt | `test_cli_output_write_failure_returns_failed_receipt` | `test_fault_injection.py` |
| 5 | 226 | `delivery_receipt_persist_failed` | U-P | receipt 寫入失敗 | audit + stderr + 不吞掉原始錯誤 | `test_cli_receipt_write_failure_still_reports_original_error` | `test_fault_injection.py` |

### 解析層 (`src/note_filler/parse.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 6 | 59 | `note_parsed_empty` | U-L | 檔案解析為空白 | audit + 回傳空 Document | `test_parse_domain_and_questions_degradations_are_identified` | `test_exception_skip_traceability.py` |

### 領域分類 (`src/note_filler/domain.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 7 | 44 | `domain_detection_defaulted` | U-L | LLM 回覆無法解析 | audit + fallback 到 other | `test_domain_detection_llm_returns_empty_string` | `test_fault_injection.py` |

### 問題生成 (`src/note_filler/questions.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 8 | 57 | `question_generation_skipped` | U-L | LLM 回傳 JSON 格式 | audit + 回傳空列表 | `test_parse_domain_and_questions_degradations_are_identified` | `test_exception_skip_traceability.py` |
| 9 | 69 | `question_generation_empty` | U-L | 解析後無問題 | audit + 回傳空列表 | `test_question_generation_empty_response` | `test_fault_injection.py` |

### 缺口偵測 (`src/note_filler/gap.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 10 | 63 | `gap_detection_skipped` | U-L | questions 為空 | audit + 回傳空列表 | `test_gap_detection_empty_questions_returns_empty` | `test_fault_injection.py` |
| 11 | 96 | `gap_item_skipped` (非 dict) | U-L | LLM 回傳非 dict 項目 | audit + continue | `test_gap_anomalies_recover_or_keep_question_and_reason` | `test_exception_skip_traceability.py` |
| 12 | 106 | `gap_item_filtered` | U-L | status=covered | audit + 過濾 | `test_gap_anomalies_recover_or_keep_question_and_reason` | `test_exception_skip_traceability.py` |
| 13 | 116 | `gap_item_skipped` (無效 status) | U-L | status 非 partial/missing | audit + continue | `test_gap_anomalies_recover_or_keep_question_and_reason` | `test_exception_skip_traceability.py` |
| 14 | 124 | `gap_item_skipped` (空 question) | U-L | question 為空 | audit + continue | `test_gap_anomalies_recover_or_keep_question_and_reason` | `test_exception_skip_traceability.py` |
| 15 | 135 | `gap_reason_defaulted` | U-L | LLM 未提供 reason | audit + 使用預設原因 | `test_gap_anomalies_recover_or_keep_question_and_reason` | `test_exception_skip_traceability.py` |
| 16 | 150 | `gap_question_recovered` | U-L | LLM 漏列問題 | audit + 補回 missing gap | `test_gap_anomalies_recover_or_keep_question_and_reason` | `test_exception_skip_traceability.py` |

### 檢索路由 (`src/note_filler/retrieve/__init__.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 17 | 44 | `law_source_retrieval_skipped` | U-F | law 域缺 law/llm | audit + 跳過 Level A | `test_law_domain_no_llm_no_law_skips_level_a` | `test_fault_injection.py` |
| 18 | 56 | `web_source_retrieval_skipped` | U-F | other 域缺 llm | audit + 跳過 web | `test_domain_other_no_llm_skips_web` | `test_fault_injection.py` |

### 法條搜尋 (`src/note_filler/retrieve/law_search.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 19 | 67 | `law_search_skipped` | U-F | LLM 無法抽取關鍵詞 | audit + 回傳空 | `test_law_search_skipped_on_empty_keywords` | `test_fault_injection.py` |
| 20 | 82 | `law_source_deduplicated` | U-L | pcode+article 重複 | audit + continue | `test_law_search_fallback_empty_dedup_and_truncation_are_bounded` | `test_exception_skip_traceability.py` |
| 21 | 94 | `law_sources_truncated` | U-L | 超過 20 筆 | audit + 截斷 | `test_law_sources_truncated` | `test_fault_injection.py` |

### Twinkle Hub (`src/note_filler/retrieve/twinkle.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 22 | 106 | `twinkle_response_empty` | U-F | MCP 回傳空 | audit + 回傳 {} | `test_twinkle_empty_rpc_response` | `test_fault_injection.py` |
| 23 | 126 | `twinkle_content_item_skipped` (非 text) | U-L | content item 非 text | audit + continue | `test_twinkle_empty_content_bad_hit_and_transport_are_traceable` | `test_exception_skip_traceability.py` |
| 24 | 137 | `twinkle_content_item_skipped` (空 text) | U-L | text 為空 | audit + continue | `test_twinkle_empty_content_bad_hit_and_transport_are_traceable` | `test_exception_skip_traceability.py` |
| 25 | 147 | `twinkle_content_item_skipped` (非 dict) | U-L | decoded 非 dict | audit + continue | `test_twinkle_empty_content_bad_hit_and_transport_are_traceable` | `test_exception_skip_traceability.py` |
| 26 | 154 | `twinkle_response_unusable` | U-F | 無可解析 JSON 物件 | audit + 回傳 {} | `test_twinkle_empty_content_bad_hit_and_transport_are_traceable` | `test_exception_skip_traceability.py` |
| 27 | 176 | `twinkle_similarity_defaulted` | U-L | similarity 非數字 | audit + 回傳 0.0 | `test_twinkle_similarity_non_numeric` | `test_fault_injection.py` |
| 28 | 208 | `twinkle_record_field_skipped` (嵌套) | U-L | 嵌套 dict 含非 scalar | audit + continue | `test_twinkle_empty_content_bad_hit_and_transport_are_traceable` | `test_exception_skip_traceability.py` |
| 29 | 217 | `twinkle_record_field_skipped` (頂層) | U-L | 頂層含非 scalar | audit + continue | `test_twinkle_empty_content_bad_hit_and_transport_are_traceable` | `test_exception_skip_traceability.py` |
| 30 | 249 | `twinkle_source_content_empty` | U-P | 全文為空 | audit + 仍回傳 Source | `test_twinkle_source_content_empty` | `test_fault_injection.py` |
| 31 | 281 | `twinkle_search_skipped` | U-F | 缺 token 或空 query | audit + 回傳 [] | `test_search_returns_empty_without_token` | `test_twinkle.py` |
| 32 | 291 | `twinkle_limit_defaulted` | U-L | n 非數字 | audit + limit=3 | `test_twinkle_limit_defaulted` | `test_fault_injection.py` |
| 33 | 306 | `twinkle_search_failed` | U-H | MCP 服務拋例外 | audit + 回傳 [] | `test_twinkle_search_timeout_returns_empty` | `test_fault_injection.py` |
| 34 | 317 | `twinkle_hits_empty` | U-L | MCP 回傳無 hits | audit + 回傳 [] | `test_twinkle_hits_empty` | `test_fault_injection.py` |
| 35 | 325 | `twinkle_hit_skipped` | U-L | hit 非 dict | audit + continue | `test_twinkle_non_dict_hit_skipped` | `test_fault_injection.py` |
| 36 | 337 | `twinkle_sources_truncated` | U-L | sources 超限 | audit + 截斷 | `test_twinkle_sources_truncated` | `test_fault_injection.py` |

### 開放網路 (`src/note_filler/retrieve/web.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 37 | 62 | `web_query_defaulted` | U-L | LLM 回傳空 query | audit + 退回原文 | `test_web_query_defaulted` | `test_fault_injection.py` |
| 38 | 88 | `web_grade_dropped` | U-L | 分級無效或 drop | audit + drop | `test_web_grade_drop_skipped` | `test_fault_injection.py` |
| 39 | 118 | `web_search_failed` | U-H | search 拋例外 | audit + 回傳 [] | `test_web_search_exception_all_pages_faulty` | `test_fault_injection.py` |
| 40 | 132 | `web_hits_truncated` | U-L | hits 超過 max_fetch | audit + 截斷 | `test_web_hits_truncated` | `test_fault_injection.py` |
| 41 | 142 | `web_hit_skipped` (非 dict) | U-L | hit 非 dict | audit + continue | `test_web_hit_not_dict_skipped` | `test_fault_injection.py` |
| 42 | 152 | `web_hit_skipped` (缺 href) | U-L | hit 缺 href | audit + continue | `test_web_exception_and_skip_matrix_preserves_later_good_source` | `test_exception_skip_traceability.py` |
| 43 | 163 | `web_fetch_failed` | U-H | 單頁 fetch 失敗 | audit + continue | `test_web_fetch_timeout_skips_page` | `test_fault_injection.py` |
| 44 | 172 | `web_content_skipped` | U-L | 內容過短 | audit + continue | `test_web_content_too_short_skipped` | `test_fault_injection.py` |
| 45 | 184 | `web_grading_failed` | U-H | 分級拋例外 | audit + continue | `test_web_exception_and_skip_matrix_preserves_later_good_source` | `test_exception_skip_traceability.py` |
| 46 | 193 | `web_source_not_forwarded` | U-F | 分級 drop | audit + continue | `test_web_grade_drop_skipped` | `test_fault_injection.py` |
| 47 | 203 | `web_content_truncated` | U-L | 內容超 2500 字 | audit + 截斷 | `test_web_exception_and_skip_matrix_preserves_later_good_source` | `test_exception_skip_traceability.py` |
| 48 | 248 | `web_fetch_empty` | U-P | trafilatura 無 HTML | audit + 回傳 None | `test_web_fetch_empty` | `test_fault_injection.py` |

### 撰寫 (`src/note_filler/write.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 49 | 52 | `supplement_writing_deferred` | U-L | LLM 回傳【待補證】 | audit + used=[] | `test_pending_evidence_when_insufficient` | `test_write.py` |
| 50 | 71 | `citation_source_deduplicated` | U-L | 同一 [^n] 重複 | audit + 保留首次 | `test_citation_source_deduplicated` | `test_fault_injection.py` |
| 51 | 79 | `out-of-range citation marker removed` | U-L | [^n] 超出 sources | audit + 移除標記 | `test_write_out_of_range_marker_emits_warning_log` | `test_exception_skip_traceability.py` |
| 52 | 90 | `supplement_has_no_forwardable_sources` | U-F | 全部引用越界 | audit + pending_evidence | `test_supplement_has_no_forwardable_sources` | `test_fault_injection.py` |

### 交叉驗證 (`src/note_filler/verify.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| — | — | （無 audit_event） | — | 純函數，無副作用 | — | `test_cross_validate_*` | `test_verify.py` |

### 訂正組裝 (`src/note_filler/correction.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 53 | 102 | `written_supplement_missing` | U-F | gap 不在 written dict | audit + 【待補證】placeholder | `test_written_supplement_missing_in_assembly` | `test_fault_injection.py` |
| 54 | 119 | `used_sources_not_forwarded` | U-F | 引用的 source ID 不存在 | audit + pending_evidence | `test_used_sources_not_forwarded` | `test_fault_injection.py` |
| 55 | 141 | `validation_not_forwarded` | U-F | gap 不在 validations dict | audit + 繼續組裝 | `test_validation_not_forwarded_audit` | `test_fault_injection.py` |

### 管線編排 (`src/note_filler/pipeline.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 56 | 39 | `sources_not_forwarded_to_validation` | U-F | 來源未被 writer 引用 | audit + 只驗引用來源 | `test_sources_not_forwarded_to_validation` | `test_fault_injection.py` |
| 57 | 70 | `law_citation_not_forwarded_as_verified` | U-F | 法規引用查核失敗 | audit + confidence 降級 | `test_law_citation_not_forwarded_as_verified` | `test_fault_injection.py` |

### 法規引用核對 (`src/note_filler/knowledge/law_citation_check.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 58 | 57 | `law_citation_skipped` (指代詞) | U-L | 同法/本法但無前文 | audit + continue | `test_law_citation_skips_and_penalty_mismatch_are_traceable` | `test_exception_skip_traceability.py` |
| 59 | 83 | `law_citation_skipped` (法規不在庫) | U-L | 法規名查無 | audit + continue | `test_law_citation_skips_and_penalty_mismatch_are_traceable` | `test_exception_skip_traceability.py` |
| 60 | 117 | `law_issue_deduplicated` | U-L | 同一 issue 重複 | audit + 去重 | `test_law_issue_deduplicated` | `test_fault_injection.py` |

### 法條索引 (`src/note_filler/knowledge/law_lookup.py`)

| # | 行號 | 事件名稱 | 風險類型 | 觸發條件 | 處置行為 | 驗證測試 | 測試檔案 |
|---|------|----------|----------|----------|----------|----------|----------|
| 61 | 125 | `law_index_file_skipped` | U-L | md 檔無 pcode 或條文 | audit + continue | `test_law_index_skip_records_path_and_continues` | `test_exception_skip_traceability.py` |

## 覆蓋率統計

| 指標 | 數值 |
|------|------|
| 總 audit_event 呼叫點 | 61 |
| 有對應測試覆蓋 | 61 |
| 未覆蓋 | 0 |
| 覆蓋率 | 100% |
| 非靜默處置（raise/audit/degrade） | 61/61 (100%) |
| 全量測試結果 | 266 passed, 11 deselected |

## 新增測試清單（本次變更）

| # | 測試函數 | 覆蓋事件 | 測試檔案 |
|---|----------|----------|----------|
| 1 | `test_delivery_receipt_replaced` | `delivery_receipt_replaced` | `test_fault_injection.py` |
| 2 | `test_input_directory_skipped` | `input_directory_skipped` | `test_fault_injection.py` |
| 3 | `test_input_file_deduplicated` | `input_file_deduplicated` | `test_fault_injection.py` |
| 4 | `test_citation_source_deduplicated` | `citation_source_deduplicated` | `test_fault_injection.py` |
| 5 | `test_supplement_has_no_forwardable_sources` | `supplement_has_no_forwardable_sources` | `test_fault_injection.py` |
| 6 | `test_web_query_defaulted` | `web_query_defaulted` | `test_fault_injection.py` |
| 7 | `test_web_hits_truncated` | `web_hits_truncated` | `test_fault_injection.py` |
| 8 | `test_web_fetch_empty` | `web_fetch_empty` | `test_fault_injection.py` |
| 9 | `test_twinkle_source_content_empty` | `twinkle_source_content_empty` | `test_fault_injection.py` |
| 10 | `test_twinkle_limit_defaulted` | `twinkle_limit_defaulted` | `test_fault_injection.py` |
| 11 | `test_twinkle_hits_empty` | `twinkle_hits_empty` | `test_fault_injection.py` |
| 12 | `test_twinkle_sources_truncated` | `twinkle_sources_truncated` | `test_fault_injection.py` |
| 13 | `test_law_issue_deduplicated` | `law_issue_deduplicated` | `test_fault_injection.py` |
| 14 | `test_law_sources_truncated` | `law_sources_truncated` | `test_fault_injection.py` |

## 結論

所有 61 條 audit_event 路徑現在均有對應的非靜態處置（audit + degrade/continue/return）及可重現的回歸測試。無任何路徑在異常或跳過時靜默遺失資料。
