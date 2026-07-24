# 主流程筆記降級分支盤點與對照表

**日期**: 2026-07-24  
**範圍**: `src/note_filler/**` 主流程中會把「實際筆記」降級成稽核/空結果的分支  
**任務**: 定位入口函式、條件判斷與回傳值，區分真正產出筆記路徑與停在測試稽核路徑，找出最短可修復點

---

## 1. 主流程拓樸與正常路徑

```
CLI(__main__.process_file) / Web(app/server.run)
  └─ run_pipeline (pipeline.py)
       T2 parse_note → Document
       T3 detect_domain → Domain (law/admin/exam/other)
       T4 generate_questions → list[str]
       T5 detect_gaps → list[Gap] (partial/missing)
       loop gaps:
         T9 retrieve_for_gap → list[Source] (Level A/B/C/D)
         Q3 write_supplement → WrittenSupplement (text + used_source_ids)
         T10 cross_validate → Validation (verified/conflict)
       T12 assemble_correction → CorrectionDoc (segments with confidence)
       C6 _verify_law_citations (domain==law)
  └─ export to_markdown | to_json | to_docx
  └─ write_delivery_receipt (CLI only)
```

**正常路徑產出筆記條件**：
- parse_note 成功解析原文
- detect_domain 正確辨識領域
- generate_questions 產出問題清單
- detect_gaps 偵測到缺口
- retrieve_for_gap 檢索到來源
- write_supplement 撰寫補充並引用來源
- cross_validate 驗證通過
- assemble_correction 組裝成 verified 段落

---

## 2. 降級分支清單與對照表

### 2.1 領域辨識降級

| ID | 檔案:行 | 入口函式 | 條件判斷 | 回傳值 | 影響階段 | 目前稽核路徑 | 真正筆記路徍 | 最短修復點 |
|----|---------|----------|----------|--------|----------|-------------|-------------|-----------|
| D-DOM-01 | `domain.py:43-51` | `detect_domain` | LLM 回應無法辨識（不包含任何合法標籤） | `"other"` | T3 → T9 走 web 路徑而非 law/twinkle | `audit_event("domain_detection_defaulted")` + 返回 "other" | LLM 應正確辨識領域 | 改善 LLM prompt 或增加重試機制 |

**影響分析**：
- 目前：降級為 "other" 領域，跳過法條檢索與 twinkle，只走 web 檢索
- 正常：應正確辨識為 law/admin/exam，啟用對應檢索路徑
- 修復點：`domain.py:43-51` 的 fallback 邏輯

---

### 2.2 問題生成降級

| ID | 檔案:行 | 入口函式 | 條件判斷 | 回傳值 | 影響階段 | 目前稽核路徑 | 真正筆記路徍 | 最短修復點 |
|----|---------|----------|----------|--------|----------|-------------|-------------|-----------|
| D-QUE-01 | `questions.py:56-64` | `generate_questions` | LLM 回應以 `[` 或 `{` 開頭（JSON 格式） | `[]` | T4 → T5 無缺口 → 無補充 | `audit_event("question_generation_skipped")` + 返回空清單 | LLM 應返回純文字問題清單 | 修改 prompt 禁止 JSON 或解析 JSON |
| D-QUE-02 | `questions.py:68-75` | `generate_questions` | LLM 回應無非空行 | `[]` | T4 → T5 無缺口 → 無補充 | `audit_event("question_generation_empty")` + 返回空清單 | LLM 應產出具體問題 | 改善 prompt 或增加重試 |

**影響分析**：
- 目前：返回空問題清單，導致 detect_gaps 無缺口，整個補充流程停止
- 正常：應產出具體可查證的問題清單
- 修復點：`questions.py:56-64` 和 `questions.py:68-75` 的 fallback 邏輯

---

### 2.3 缺口偵測降級

| ID | 檔案:行 | 入口函式 | 條件判斷 | 回傳值 | 影響階段 | 目前稽核路徑 | 真正筆記路徍 | 最短修復點 |
|----|---------|----------|----------|--------|----------|-------------|-------------|-----------|
| D-GAP-01 | `gap.py:62-73` | `detect_gaps` | JSON 解析失敗或非 list | `_all_missing(questions)` | T5 → 所有問題變 missing | 保守 fallback，但無 log | LLM 應返回正確 JSON | 增加 log 或改善 JSON 解析容錯 |
| D-GAP-02 | `gap.py:77-78` | `detect_gaps` | item 非 dict | `continue_skip` | T5 → 該 gap 靜默消失 | 無 log，靜默跳過 | 該 gap 應被處理 | 增加 log 或改為 missing |
| D-GAP-03 | `gap.py:115-122` | `detect_gaps` | status 非 partial/missing | `continue_skip` | T5 → covered 問題被過濾 | 設計正確，covered 應被過濾 | - | 無需修復 |

**影響分析**：
- D-GAP-01：JSON 解析失敗時保守把所有問題當 missing，雖然安全但可能過度保守
- D-GAP-02：item 非 dict 時靜默跳過，可能遺漏缺口
- 修復點：`gap.py:77-78` 增加 log

---

### 2.4 檢索路由降級

| ID | 檔案:行 | 入口函式 | 條件判斷 | 回傳值 | 影響階段 | 目前稽核路徑 | 真正筆記路徍 | 最短修復點 |
|----|---------|----------|----------|--------|----------|-------------|-------------|-----------|
| D-RET-01 | `retrieve/__init__.py:43-51` | `retrieve_for_gap` | law 域但 law is None 或 llm is None | 跳過 search_law_sources | T9 → Level A 法條缺失 | `audit_event("law_source_retrieval_skipped")` | 應確保 law 和 llm 齊備 | 啟動時檢查依賴或提供明確錯誤 |
| D-RET-02 | `retrieve/__init__.py:56-63` | `retrieve_for_gap` | other 域但 llm is None | 跳過 search_web_sources | T9 → Level C/D 網路來源缺失 | `audit_event("web_source_retrieval_skipped")` | 應確保 llm 齊備 | 啟動時檢查依賴或提供明確錯誤 |

**影響分析**：
- 目前：依賴缺失時跳過對應檢索，只留下其他來源
- 正常：應確保依賴齊備，或提供明確錯誤訊息
- 修復點：啟動時檢查依賴（CLI 已有警告但未阻擋）

---

### 2.5 法條檢索降級

| ID | 檔案:行 | 入口函式 | 條件判斷 | 回傳值 | 影響階段 | 目前稽核路徑 | 真正筆記路徍 | 最短修復點 |
|----|---------|----------|----------|--------|----------|-------------|-------------|-----------|
| D-LAW-01 | `retrieve/law_search.py:66-73` | `search_law_sources` | keywords 空清單 | `[]` | T9 → Level A 法條缺失 | `audit_event("law_search_skipped")` | LLM 應抽出有效關鍵詞 | 改善關鍵詞抽取 prompt |

**影響分析**：
- 目前：關鍵詞空時返回空清單，無法檢索法條
- 正常：LLM 應抽出有效關鍵詞進行檢索
- 修復點：`retrieve/law_search.py:66-73` 的 fallback 邏輯

---

### 2.6 Twinkle 檢索降級

| ID | 檔案:行 | 入口函式 | 條件判斷 | 回傳值 | 影響階段 | 目前稽核路徑 | 真正筆記路徍 | 最短修復點 |
|----|---------|----------|----------|--------|----------|-------------|-------------|-----------|
| D-TWI-01 | `retrieve/twinkle.py:280-287` | `TwinkleClient.search` | 無 token 或空 query | `[]` | T9 → Level B 立法院來源缺失 | `audit_event("twinkle_search_skipped")` | 應提供 token 或有效 query | CLI 已有警告，無需修復 |
| D-TWI-02 | `retrieve/twinkle.py:305-313` | `TwinkleClient.search` | 查詢失敗（例外） | `[]` | T9 → Level B 立法院來源缺失 | `audit_event("twinkle_search_failed")` + log_warning | 外部服務應正常運作 | 外部服務問題，程式已正確降級 |

**影響分析**：
- D-TWI-01：CLI 已有警告，屬預期行為
- D-TWI-02：外部服務失敗時正確降級，已有稽核
- 修復點：無需修復，屬正確的 resilience 設計

---

### 2.7 Web 檢索降級

| ID | 檔案:行 | 入口函式 | 條件判斷 | 回傳值 | 影響階段 | 目前稽核路徑 | 真正筆記路徍 | 最短修復點 |
|----|---------|----------|----------|--------|----------|-------------|-------------|-----------|
| D-WEB-01 | `retrieve/web.py:117-126` | `search_web_sources` | 搜尋階段例外 | `[]` | T9 → Level C/D 網路來源缺失 | `audit_event("web_search_failed")` + log_warning | 外部服務應正常運作 | 外部服務問題，程式已正確降級 |

**影響分析**：
- 外部服務失敗時正確降級，已有稽核
- 修復點：無需修復，屬正確的 resilience 設計

---

### 2.8 撰寫降級

| ID | 檔案:行 | 入口函式 | 條件判斷 | 回傳值 | 影響階段 | 目前稽核路徑 | 真正筆記路徍 | 最短修復點 |
|----|---------|----------|----------|--------|----------|-------------|-------------|-----------|
| D-WRI-01 | `write.py:51-59` | `write_supplement` | LLM 回應以【待補證】開頭 | `used_source_ids=[]` | Q3 → 補充標記為待補證 | `audit_event("supplement_writing_deferred")` | LLM 應根據來源撰寫補充 | 改善撰寫 prompt 或確保來源充足 |
| D-WRI-02 | `write.py:89-96` | `write_supplement` | 無有效 [^n] 標記 | `used_source_ids=[]` | Q3 → 補充無引用來源 | `audit_event("supplement_has_no_forwardable_sources")` | LLM 應正確引用來源 | 改善撰寫 prompt 引用格式 |

**影響分析**：
- D-WRI-01：來源不足時 LLM 正確標記【待補證】，屬設計行為
- D-WRI-02：LLM 未引用來源時正確記錄，屬設計行為
- 修復點：無需修復，屬正確的品質閘設計

---

### 2.9 組裝降級

| ID | 檔案:行 | 入口函式 | 條件判斷 | 回傳值 | 影響階段 | 目前稽核路徑 | 真正筆記路徍 | 最短修復點 |
|----|---------|----------|----------|--------|----------|-------------|-------------|-----------|
| D-COR-01 | `correction.py:128-133` | `assemble_correction` | text 以【待補證】開頭或未 grounded | `confidence="pending_evidence"` | T12 → 段落降為待補證 | 設計行為，無 audit_event | 應有足夠來源通過 grounded 檢查 | 確保上游檢索提供足夠來源 |

**影響分析**：
- 無來源或來源不足時正確降級為 pending_evidence，屬設計行為
- 修復點：無需修復，屬正確的品質閘設計

---

### 2.10 法規引用核對降級

| ID | 檔案:行 | 入口函式 | 條件判斷 | 回傳值 | 影響階段 | 目前稽核路徑 | 真正筆記路徍 | 最短修復點 |
|----|---------|----------|----------|--------|----------|-------------|-------------|-----------|
| D-CITE-01 | `pipeline.py:69-77` | `_verify_law_citations` | findings 含 article_not_found | `seg.confidence="pending_evidence"` | C6 → 法條引用缺失時降級 | `audit_event("law_citation_not_forwarded_as_verified")` | 法條應存在於離線庫 | 更新法條庫或改善法條抽取 |

**影響分析**：
- 法條不存在於離線庫時正確降級，屬設計行為
- 修復點：無需修復，屬正確的品質閘設計

---

## 3. 關鍵降級路徑分析

### 3.1 高優先度修復點（影響實際筆記產出）

| 優先 | ID | 問題 | 影響 | 修復建議 |
|------|-----|------|------|----------|
| 高 | D-DOM-01 | 領域誤判為 other | 跳過法條/twinkle 檢索 | 改善 LLM prompt 或增加重試 |
| 高 | D-QUE-01 | JSON 格式被拒 | 無問題清單 → 無補充 | 解析 JSON 或改善 prompt |
| 高 | D-QUE-02 | 空問題清單 | 無缺口 → 無補充 | 改善 prompt 或增加重試 |
| 中 | D-GAP-02 | gap item 非 dict 靜默跳過 | 可能遺漏缺口 | 增加 log |
| 中 | D-LAW-01 | 關鍵詞空 | 無法檢索法條 | 改善關鍵詞抽取 prompt |

### 3.2 設計行為（無需修復）

| ID | 分類 | 原因 |
|----|------|------|
| D-TWI-01, D-TWI-02 | Resilience | 外部服務失敗正確降級 |
| D-WEB-01 | Resilience | 外部服務失敗正確降級 |
| D-WRI-01, D-WRI-02 | 品質閘 | 無來源時正確標記 |
| D-COR-01 | 品質閘 | 來源不足時正確降級 |
| D-CITE-01 | 品質閘 | 法條缺失時正確降級 |
| D-RET-01, D-RET-02 | 依賴檢查 | 依賴缺失時正確跳過 |

---

## 4. 最短可修復點總結

### 4.1 立即可修復（程式邏輯）

1. **D-GAP-02** (`gap.py:77-78`)：增加 log，避免靜默跳過
2. **D-QUE-01** (`questions.py:56-64`)：解析 JSON 而非直接拒絕
3. **D-QUE-02** (`questions.py:68-75`)：增加重試機制而非直接返回空

### 4.2 需改善 prompt（LLM 行為）

1. **D-DOM-01** (`domain.py:43-51`)：改善領域辨識 prompt
2. **D-LAW-01** (`retrieve/law_search.py:66-73`)：改善關鍵詞抽取 prompt
3. **D-WRI-01, D-WRI-02** (`write.py`)：改善撰寫 prompt 引用格式

### 4.3 依賴管理（啟動檢查）

1. **D-RET-01, D-RET-02** (`retrieve/__init__.py`)：啟動時檢查依賴並明確錯誤

---

## 5. 與既有報告對應

| 既有文件 | 對應關係 |
|----------|----------|
| `docs/data-flow-exception-skip-branch-inventory-2026-07-24.md` | 本報告聚焦「實際筆記降級」分支，該報告為全面異常分支盤點 |
| `docs/data-skip-persist-forward-audit-2026-07-24.md` | 本報告補充對照表與修復點分析 |

---

## 6. 結論

1. **高優先修復點**：D-DOM-01、D-QUE-01、D-QUE-02 會直接導致無補充產出
2. **中優先修復點**：D-GAP-02、D-LAW-01 會部分影響補充品質
3. **設計行為**：多數降級屬正確的 resilience 與品質閘設計，無需修復
4. **最短修復路徑**：優先修復 D-GAP-02 增加 log，其次改善 prompt 與依賴檢查

---

## 7. 機器證據

本報告基於以下原始碼分析：
- `src/note_filler/__main__.py`
- `src/note_filler/pipeline.py`
- `src/note_filler/domain.py`
- `src/note_filler/questions.py`
- `src/note_filler/gap.py`
- `src/note_filler/retrieve/__init__.py`
- `src/note_filler/retrieve/law_search.py`
- `src/note_filler/retrieve/twinkle.py`
- `src/note_filler/retrieve/web.py`
- `src/note_filler/write.py`
- `src/note_filler/correction.py`
- `src/note_filler/verify.py`
