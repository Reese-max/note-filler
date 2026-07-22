# 輸出資料與筆記內容產生路徑盤點報告

## 盤點日期
2026-07-23

## 任務目標
盤點目前「輸出資料」與「筆記內容」的產生路徑，定位實際比對缺口：找出輸出檔生成函式、筆記來源讀取函式，以及兩者目前只各自被哪些測試覆蓋，整理成一份最小修補點清單。

## 一、輸出資料產生路徑

### 1.1 export.py - 輸出格式轉換

#### 函式清單
- `to_json(doc: CorrectionDoc) -> dict` - 序列化整份 CorrectionDoc 為 JSON
- `to_markdown(doc: CorrectionDoc) -> str` - 輸出 Markdown 格式（C3 鎖定格式）
- `to_docx(doc: CorrectionDoc, path: str) -> None` - 輸出 .docx 訂正稿

#### 測試覆蓋
| 測試檔案 | 測試函式 | 覆蓋函式 | 標記 |
|---------|---------|---------|------|
| test_export.py | test_to_json_serializes_segments | to_json | - |
| test_export.py | test_to_markdown_format_locked | to_markdown | - |
| test_export.py | test_to_markdown_pending_segment_has_no_footnote | to_markdown | - |
| test_export_docx.py | test_to_docx_roundtrip_preserves_original_and_marks_supplement | to_docx | - |

#### 覆蓋狀態
- ✅ `to_json()`: 有單元測試
- ✅ `to_markdown()`: 有單元測試
- ✅ `to_docx()`: 有單元測試

### 1.2 write.py - 補充內容撰寫

#### 函式清單
- `write_supplement(gap: Gap, sources: list[Source], llm: LLMClient) -> WrittenSupplement` - 根據來源撰寫補充

#### 測試覆蓋
| 測試檔案 | 測試函式 | 覆蓋函式 | 標記 |
|---------|---------|---------|------|
| test_write.py | test_used_source_ids_from_markers | write_supplement | - |
| test_write.py | test_pending_evidence_when_insufficient | write_supplement | - |
| test_write.py | test_out_of_range_marker_removed_and_not_used | write_supplement | - |
| test_write.py | test_write_supplement_real_grok_grounded_output | write_supplement | @integration |

#### 覆蓋狀態
- ✅ `write_supplement()`: 有單元測試 + 整合測試

### 1.3 pipeline.py - 完整流程串接

#### 函式清單
- `run_pipeline(path, llm, twinkle, law)` - 串接完整流程

#### 測試覆蓋
| 測試檔案 | 測試函式 | 覆蓋函式 | 標記 |
|---------|---------|---------|------|
| test_pipeline.py | test_run_pipeline_invariant | run_pipeline | - |
| test_pipeline.py | test_run_pipeline_law_domain_runs_citation_check | run_pipeline | - |
| test_pipeline.py | test_run_pipeline_malformed_gap_output_falls_back_to_pending | run_pipeline | - |
| test_pipeline.py | test_run_pipeline_real_grok | run_pipeline | @integration |

#### 覆蓋狀態
- ✅ `run_pipeline()`: 有單元測試 + 整合測試

## 二、筆記內容讀取路徑

### 2.1 parse.py - 筆記檔案解析

#### 函式清單
- `parse_note(path: str) -> Document` - 讀取筆記檔案（.txt/.docx）

#### 測試覆蓋
| 測試檔案 | 測試函式 | 覆蓋函式 | 標記 |
|---------|---------|---------|------|
| test_parse.py | test_parse_txt_splits_on_blank_lines | parse_note | - |
| test_parse.py | test_paragraph_and_document_are_frozen | parse_note | - |
| test_parse.py | test_parse_docx_roundtrip | parse_note | - |

#### 覆蓋狀態
- ✅ `parse_note()`: 有單元測試

### 2.2 retrieve/__init__.py - 來源檢索協調

#### 函式清單
- `retrieve_for_gap(gap, domain, twinkle, law, llm)` - 依缺口檢索一手來源

#### 測試覆蓋
| 測試檔案 | 測試函式 | 覆蓋函式 | 標記 |
|---------|---------|---------|------|
| test_retrieve.py | test_retrieve_for_gap_law_domain_puts_level_A_before_B | retrieve_for_gap | - |
| test_retrieve.py | test_retrieve_for_gap_other_domain_uses_web_not_twinkle | retrieve_for_gap | - |
| test_retrieve.py | test_retrieve_for_gap_real_twinkle_smoke | retrieve_for_gap | @integration |

#### 覆蓋狀態
- ✅ `retrieve_for_gap()`: 有單元測試 + 整合測試

### 2.3 retrieve/law_search.py - 法條來源檢索

#### 函式清單
- `search_law_sources(gap, llm, law, limit)` - 從缺口問題抽關鍵詞查法條全文

#### 測試覆蓋
| 測試檔案 | 測試函式 | 覆蓋函式 | 標記 |
|---------|---------|---------|------|
| test_law_search.py | test_search_law_sources_returns_level_A_law_articles | search_law_sources | @skipif(缺 DB) |
| test_law_search.py | test_search_law_sources_accepts_plain_keyword_response | search_law_sources | @skipif(缺 DB) |
| test_law_search.py | test_search_law_sources_uses_single_llm_call_and_empty_on_no_hit | search_law_sources | - |
| test_law_search.py | test_search_law_sources_unions_multiple_keywords_dedup_and_order | search_law_sources | - |
| test_law_search.py | test_search_law_sources_backward_compat_single_keyword | search_law_sources | - |
| test_law_search.py | test_search_law_sources_non_json_treated_as_single_keyword | search_law_sources | - |
| test_law_search.py | test_search_law_sources_empty_keywords_returns_empty | search_law_sources | - |

#### 覆蓋狀態
- ✅ `search_law_sources()`: 有單元測試（部分需 DB）

### 2.4 retrieve/twinkle.py - 立法院議案檢索

#### 函式清單
- `TwinkleClient.search(query, n)` - 檢索立法院議案（Level B）

#### 測試覆蓋
| 測試檔案 | 測試函式 | 覆蓋函式 | 標記 |
|---------|---------|---------|------|
| test_twinkle.py | test_search_parses_source_with_full_content | TwinkleClient.search | - |
| test_twinkle.py | test_search_clamps_similarity_input_to_distance_range | TwinkleClient.search | - |
| test_twinkle.py | test_search_returns_empty_without_token | TwinkleClient.search | - |
| test_twinkle.py | test_search_reuses_mcp_session | TwinkleClient.search | - |
| test_twinkle.py | test_search_transport_failure_returns_empty | TwinkleClient.search | - |
| test_twinkle.py | test_default_timeout_is_60 | TwinkleClient.search | - |
| test_twinkle.py | test_search_mcp_protocol_error_returns_empty | TwinkleClient.search | - |
| test_twinkle.py | test_search_real_twinkle_hub | TwinkleClient.search | @integration |

#### 覆蓋狀態
- ✅ `TwinkleClient.search()`: 有單元測試 + 整合測試

### 2.5 retrieve/web.py - 開放網路來源檢索

#### 函式清單
- `search_web_sources(gap, llm, search, fetch, max_results, max_fetch)` - 檢索開放網路來源（Level C/D）

#### 測試覆蓋
| 測試檔案 | 測試函式 | 覆蓋函式 | 標記 |
|---------|---------|---------|------|
| test_web.py | test_two_pages_graded_c_and_d | search_web_sources | - |
| test_web.py | test_drop_page_excluded | search_web_sources | - |
| test_web.py | test_fetch_none_skipped | search_web_sources | - |
| test_web.py | test_too_short_fulltext_skipped | search_web_sources | - |
| test_web.py | test_search_exception_degrades_to_empty | search_web_sources | - |
| test_web.py | test_content_truncated_with_note | search_web_sources | - |
| test_web.py | test_query_extraction_falls_back_to_question | search_web_sources | - |
| test_web.py | test_retrieve_other_domain_calls_web | search_web_sources (via retrieve_for_gap) | - |
| test_web.py | test_retrieve_law_domain_does_not_call_web | search_web_sources (via retrieve_for_gap) | - |

#### 覆蓋狀態
- ✅ `search_web_sources()`: 有單元測試

## 三、比對缺口分析

### 3.1 輸出資料與筆記內容之間的關聯

**資料流向：**
```
筆記檔案 (parse_note) 
  → Document (full_text)
  → detect_gaps (找出缺口)
  → retrieve_for_gap (檢索來源)
  → write_supplement (撰寫補充)
  → assemble_correction (組裝 CorrectionDoc)
  → to_json/to_markdown/to_docx (輸出)
```

### 3.2 測試覆蓋缺口

#### 缺口 1: 輸出格式與筆記來源的端到端驗證
- **問題**: 缺少從「原始筆記檔案」到「最終輸出檔案」的完整比對測試
- **影響**: 無法確保輸出檔案正確反映原始筆記內容與補充來源
- **現有測試**: 
  - `test_pipeline.py` 有完整流程測試，但未驗證輸出檔案內容與原始筆記的逐段對應
  - `test_export.py` 只測試格式轉換，未驗證資料來源正確性

#### 缺口 2: 不同輸出格式間的一致性驗證
- **問題**: 缺少驗證 `to_json`、`to_markdown`、`to_docx` 三種輸出格式是否產生等價內容的測試
- **影響**: 不同格式可能產生不一致的內容
- **現有測試**: 各格式有獨立測試，但無交叉比對

#### 缺口 3: 筆記來源讀取與輸出檔案的來源引用對應
- **問題**: 缺少驗證輸出檔案中的來源引用是否正確對應到檢索到的來源
- **影響**: 來源引用可能錯亂或遺失
- **現有測試**: 
  - `test_write.py` 驗證 `used_source_ids` 解析
  - `test_export.py` 驗證輸出格式中的來源呈現
  - 但缺少端到端的來源鏈驗證

#### 缺口 4: 筆記檔案格式支援與輸出格式的對應
- **問題**: 缺少驗證不同輸入格式（.txt/.docx）經過完整流程後，輸出檔案是否正確保留原文
- **影響**: 不同輸入格式可能導致原文遺失或格式錯誤
- **現有測試**: 
  - `test_parse.py` 有 roundtrip 測試
  - 但未結合完整 pipeline 與輸出格式驗證

## 四、最小修補點清單

### 4.1 高優先級（影響資料正確性）

#### 修補點 1: 端到端筆記來源驗證測試
- **位置**: `tests/test_pipeline.py` 或新增 `tests/test_e2e_source_trace.py`
- **內容**: 
  - 建立測試驗證從原始筆記檔案到最終輸出檔案的完整資料鏈
  - 驗證輸出檔案中的原文段與原始筆記逐段對應
  - 驗證補充段的來源引用正確對應到檢索來源
- **覆蓋函式**: `parse_note` → `run_pipeline` → `to_json/to_markdown/to_docx`

#### 修補點 2: 輸出格式一致性測試
- **位置**: `tests/test_export.py`
- **內容**:
  - 新增測試驗證同一 CorrectionDoc 經過三種輸出格式後，核心內容等價
  - 比對原文段、補充段文字、來源數量、來源 ID
- **覆蓋函式**: `to_json` ↔ `to_markdown` ↔ `to_docx`

### 4.2 中優先級（影響格式一致性）

#### 修補點 3: 來源引用鏈驗證測試
- **位置**: `tests/test_correction.py` 或新增 `tests/test_source_trace.py`
- **內容**:
  - 驗證 CorrectionDoc 中的每個補充段的 sources 正確對應到檢索來源
  - 驗證輸出檔案中的註腳編號與來源順序一致
- **覆蓋函式**: `retrieve_for_gap` → `write_supplement` → `assemble_correction` → `to_*`

#### 修補點 4: 多輸入格式端到端測試
- **位置**: `tests/test_pipeline.py`
- **內容**:
  - 對 .txt 和 .docx 兩種輸入格式執行完整 pipeline
  - 驗證最終輸出檔案正確保留原文內容
- **覆蓋函式**: `parse_note` (txt/docx) → `run_pipeline` → `to_*`

### 4.3 低優先級（加強防護）

#### 修補點 5: 邊界條件測試
- **位置**: 各對應測試檔案
- **內容**:
  - 空筆記檔案的處理
  - 極大筆記檔案的處理
  - 特殊字元的處理
- **覆蓋函式**: `parse_note`, `to_*`, `retrieve_for_gap`

## 五、驗收標準

### 5.1 測試覆蓋完整性
- [ ] 每個輸出函式至少有一個端到端測試驗證資料來源正確性
- [ ] 每個筆記讀取函式至少有一個測試驗證其輸出正確傳遞到下游
- [ ] 三種輸出格式有一致性測試

### 5.2 資料鏈可追溯性
- [ ] 從原始筆記到最終輸出的每個環節都有測試覆蓋
- [ ] 來源引用從檢索到輸出都有測試驗證

### 5.3 文件完整性
- [ ] 本報告已落盤至 docs/
- [ ] 所有修補點都有明確的測試位置與內容定義

## 六、結論

目前輸出資料與筆記內容的產生路徑在單元測試層面覆蓋良好，但缺少端到端的資料鏈驗證。主要缺口在於：

1. **輸出格式與筆記來源的端到端驗證缺失** - 無法確保輸出檔案正確反映原始筆記內容
2. **不同輸出格式間的一致性驗證缺失** - 無法確保三種格式產生等價內容
3. **來源引用鏈的完整驗證缺失** - 無法確保來源從檢索到輸出的正確傳遞

建議優先實作高優先級的修補點 1 和 2，以確保資料正確性與格式一致性。
