# 綁定報告系統分析報告

## 任務要求
任務要求：若現有輸出仍無法被工具鏈逐項核對，補一份獨立的機器可讀綁定報告檔，內容需逐論點列出來源清單、追溯位置與驗證狀態，並讓測試直接解析該報告做一致性檢查。

## 現有系統分析

### 1. 獨立的機器可讀綁定報告檔
現有系統已經具備完整的獨立綁定報告檔：
- **檔案位置**：`src/note_filler/binding_report.py`
- **輸出檔名**：`binding_report.json`
- **Schema ID**：`note_filler.binding_report.v1`
- **寫入函式**：`write_binding_report(output_path, correction)`

### 2. 報告內容結構
報告已經包含任務要求的所有資訊：

#### 頂層結構
```json
{
  "schema": "note_filler.binding_report.v1",
  "source_path": "輸入檔路徑",
  "argument_count": 論點總數,
  "summary": {
    "one_to_one": 一對一論點數,
    "one_to_many": 一對多論點數,
    "none": 無來源論點數,
    "pass": 通過數,
    "fail": 失敗數,
    "pending_evidence": 待補證數,
    "all_sourced_arguments_ok": 有來源論點是否全部通過,
    "all_arguments_ok": 所有論點是否全部通過
  },
  "arguments": [論點陣列],
  "source_usage": 來源反向索引
}
```

#### 逐論點資訊（arguments 陣列）
每個論點包含：
- `argument_index`：論點索引
- `segment_index`：段落索引
- `argument_text`：論點文字
- `confidence`：信心等級
- `cardinality`：基數（one_to_one/one_to_many/none）
- `source_count`：來源數量
- `source_ids`：來源清單（任務要求）
- `trace_source_ids`：追溯位置（任務要求）
- `source_id_field`：source_id 欄位值
- `checks`：驗證狀態（任務要求；欄位契約鎖定，缺欄／未知欄拒絕）
  - `at_least_one_source`：至少一個來源
  - `source_traceable`：來源可追溯
  - `no_duplicate_sources`：無重複來源
  - `no_omitted_traces`：無遺漏追溯
  - `no_extra_traces`：無多餘追溯
  - `source_id_field_aligned`：source_id 欄位對齊
  - `no_empty_fragments`：片段非空
  - `has_functional_gap`：功能缺口非空（必要性視角）
  - `has_user_value`：使用者價值非空（必要性視角）
- `functional_gap`／`user_value`：必要性雙視角（來源可追溯仍不得為空通過）
- `binding_status`：綁定狀態（pass/fail/pending_evidence）
- `binding_ok`：整體綁定是否成功（含必要性）

#### 來源反向索引（source_usage）
```json
{
  "source_id": [使用該來源的論點索引陣列]
}
```

### 3. 測試直接解析報告做一致性檢查
測試系統已經實現完整的報告解析與驗證：

#### 解析函式
- `parse_binding_report(data)`：嚴格解析並校驗綁定報告結構
- 檢查所有必填欄位是否存在
- 驗證資料類型正確性
- 確保 source_usage 與 arguments 一致

#### 測試覆蓋
- `test_positive_acceptance_reads_binding_report_from_disk()`：直接從磁碟讀取報告並逐項驗證
- `test_schema_is_machine_parseable()`：驗證 schema 可機器解析
- `test_parse_rejects_missing_keys()`：驗證缺少欄位會被拒絕
- `test_product_output_each_argument_has_ids_and_traceable_fragments()`：驗證成品與報告一致性
- 多個負例測試驗證缺失來源、來源未對上等情況會正確標示為 fail

### 4. 工具鏈整合
綁定報告已經完全整合到工具鏈中：

#### CLI 整合
- `__main__.py` 的 `process_file()` 函式在輸出訂正稿後調用 `write_binding_report()`
- 支援所有輸出格式（md/json/docx）
- 報告寫在輸出檔同目錄

#### 輸出格式整合
- JSON 輸出：在 `to_json()` 中嵌入 `binding_summary` 摘要
- Markdown 輸出：在文末加入可解析的綁定驗證摘要行
- DOCX 輸出：對應 Markdown 結構

## 結論

**現有系統已經完全滿足任務要求，無需補充任何功能。**

具體來說：
1. ✅ 已有獨立的機器可讀綁定報告檔（`binding_report.json`）
2. ✅ 報告內容逐論點列出來源清單（`source_ids`）
3. ✅ 報告內容逐論點列出追溯位置（`trace_source_ids`）
4. ✅ 報告內容逐論點列出驗證狀態（`checks` 物件包含 7 項檢查）
5. ✅ 測試直接解析該報告做一致性檢查（`parse_binding_report()` + 多個測試）
6. ✅ 工具鏈已完整整合（CLI 自動產生報告）

現有系統的設計甚至超過任務基本要求，提供了：
- 固定的 schema 版本控制
- 嚴格的解析校驗
- 反向索引（source_usage）
- 多種輸出格式的整合
- 完整的正負例測試覆蓋

因此，本任務結論為：**無需新增任何功能，現有系統已完全符合要求。**