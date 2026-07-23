# 輸出資料與筆記內容直接比對驗證 Bypass 盤點報告

## 盤點日期
2026-07-23

## 任務目標
盤點「輸出資料」與「筆記內容」的所有非 integration 呼叫路徑，確認新加入的直接比對驗證沒有被任何 helper、wrapper 或條件分支繞過；若發現 bypass，列出其檔案位置與觸發條件。

## 一、非 integration 呼叫路徑盤點

### 1.1 輸出資料產生路徑

#### 路徑 1: CLI 入口 (`src/note_filler/__main__.py`)
```
main() → process_file() → run_pipeline() → to_json/to_markdown/to_docx
```

**函式位置：**
- `process_file()` (第 45-59 行)
- 呼叫 `run_pipeline()` (第 47 行)
- 條件分支調用輸出函式 (第 54-58 行)：
  - `if fmt == "docx": to_docx(doc, str(dest))`
  - `else: to_json(doc) 或 to_markdown(doc)`

**特徵：**
- 無中間 wrapper，直接調用 export 函式
- 無條件跳過驗證的分支
- 異常處理只在 `main()` 層級 (第 87-92 行)，不影響輸出函式執行

#### 路徑 2: Server 入口 (`app/server.py`)
```
POST /run → run_pipeline() → app.state.last_doc
GET /export → to_markdown(doc)
```

**函式位置：**
- `/run` 端點 (第 40-52 行)
- 呼叫 `run_pipeline()` (第 48 行)
- `/export` 端點 (第 55-66 行)
- 呼叫 `to_markdown()` (第 62 行)

**特徵：**
- 無中間 wrapper，直接調用 export 函式
- 無條件跳過驗證的分支
- 異常處理只在 FastAPI 層級，不影響輸出函式執行

#### 路徑 3: 測試入口 (`tests/test_output_consistency.py`)
```
TestOutputConsistency → run_pipeline() → to_json/to_markdown/to_docx
```

**函式位置：**
- 多個測試方法直接調用 `run_pipeline()` 和 export 函式
- 例如 `test_markdown_export_original_text_verbatim` (第 80-120 行)

**特徵：**
- 無中間 wrapper，直接調用
- 測試專注於驗證輸出與原文的一致性

### 1.2 筆記內容讀取路徑

#### 路徑 1: Pipeline 內部 (`src/note_filler/pipeline.py`)
```
run_pipeline() → parse_note(path) → Document
```

**函式位置：**
- `run_pipeline()` (第 14-41 行)
- 呼叫 `parse_note()` (第 20 行)

**特徵：**
- 無中間 wrapper，直接調用
- 無條件跳過驗證的分支

#### 路徑 2: 測試直接調用 (`tests/test_output_consistency.py`)
```
parse_note() → Document
```

**函式位置：**
- `test_pipeline_output_original_segments_match_parsed_document` (第 204-244 行)
- 直接調用 `parse_note()` 獨立驗證 (第 215 行)

**特徵：**
- 無中間 wrapper，直接調用
- 用於建立 ground truth 對照

## 二、直接比對驗證覆蓋分析

### 2.1 測試覆蓋的直接比對驗證

#### 驗證 1: Markdown 輸出原文逐字保留
**測試函式：** `test_markdown_export_original_text_verbatim` (第 80-120 行)
**驗證邏輯：**
- 逐段檢查原文段落是否出現在 markdown 輸出中
- 驗證段落順序保持不變
- 失敗時明確報告缺失或被修改的段落

#### 驗證 2: JSON 輸出原文逐字保留
**測試函式：** `test_json_export_original_text_verbatim` (第 122-170 行)
**驗證邏輯：**
- 檢查 `full_text` 欄位與原文完全一致
- 逐段檢查 `original` 類型 segment 的文字、anchor_idx、sources、confidence
- 失敗時明確報告差異

#### 驗證 3: DOCX 輸出原文逐字保留
**測試函式：** `test_docx_export_original_text_verbatim` (第 172-202 行)
**驗證邏輯：**
- 讀回輸出的 docx 檔案
- 逐段比對與原文段落
- 失敗時明確報告差異

#### 驗證 4: Pipeline 輸出與解析文件一致
**測試函式：** `test_pipeline_output_original_segments_match_parsed_document` (第 204-244 行)
**驗證邏輯：**
- 獨立調用 `parse_note()` 建立 ground truth
- 比對 pipeline 輸出的 original segments 與 parsed document
- 驗證文字、anchor_idx、sources、confidence 一致

#### 驗證 5: Full text 一致性
**測試函式：** `test_pipeline_full_text_matches_source_note` (第 246-265 行)
**驗證邏輯：**
- 直接比對 `CorrectionDoc.original.full_text` 與 `parse_note()` 結果
- 驗證 source_path 一致

#### 驗證 6: 跨格式一致性
**測試函式：** `test_output_artifacts_consistent_across_formats` (第 339-393 行)
**驗證邏輯：**
- 從 JSON、Markdown、DOCX 三種格式提取原文段落
- 驗證三種格式的原文段落數量一致
- 驗證三種格式的原文段落內容逐字一致

### 2.2 異常處理與降級分析

#### 外部服務降級 (不影響輸出比對驗證)

**位置：** `src/note_filler/retrieve/web.py`
- 第 92-94 行：網路搜尋失敗降級為空結果
- 第 104-105 行：單頁 fetch 失敗跳過該頁
- 第 110-111 行：分級失敗跳過該頁

**位置：** `src/note_filler/retrieve/twinkle.py`
- 第 219-221 行：twinkle-hub 查詢失敗降級為空結果

**影響分析：**
- 這些降級只影響「來源檢索」階段，不影響「輸出格式轉換」階段
- `to_json/to_markdown/to_docx` 函式本身無異常處理跳過驗證
- 即使來源檢索失敗，輸出函式仍會正確處理已有的 CorrectionDoc
- 原文段落的處理不受來源檢索結果影響

#### CLI 層級異常處理
**位置：** `src/note_filler/__main__.py`
- 第 87-92 行：單檔失敗不拖垮整批

**影響分析：**
- 只處理檔案級別的異常，不影響成功執行的檔案的輸出驗證
- 不會跳過輸出函式的執行

## 三、Bypass 檢查結果

### 3.1 Helper/Wrapper 檢查
**檢查方法：** 搜尋 `def.*wrapper|def.*helper|@.*wrapper|@.*helper`
**結果：** 無匹配項目
**結論：** 專案中沒有專門的 helper 或 wrapper 函式可能繞過直接比對驗證

### 3.2 條件分支檢查
**檢查方法：** 檢查所有調用 `to_json/to_markdown/to_docx` 的位置
**結果：**
- `__main__.py` 第 54-58 行：僅根據格式參數選擇調用哪個函式，無跳過驗證的分支
- `server.py` 第 62 行：直接調用，無條件分支
- 測試檔案：直接調用，無條件分支

**結論：** 沒有條件分支可能跳過直接比對驗證

### 3.3 Integration 標記檢查
**檢查方法：** 搜尋 `@integration` 標記
**結果：**
- `test_output_consistency.py` 中無 `@integration` 標記
- 所有直接比對驗證測試都是非 integration 測試
- 預設執行 `-m 'not integration'` 時仍會執行這些驗證

**結論：** 直接比對驗證不會因 integration 標記而被跳過

### 3.4 中間層檢查
**檢查方法：** 追蹤從入口到輸出函式的完整調用鏈
**結果：**
- CLI: `process_file()` → 直接調用 export 函式
- Server: `/export` → 直接調用 `to_markdown()`
- 測試: 測試方法 → 直接調用 export 函式

**結論：** 沒有中間層可能繞過直接比對驗證

## 四、結論

### 4.1 Bypass 發現狀況
**無發現任何 bypass。**

所有「輸出資料」與「筆記內容」的非 integration 呼叫路徑都：
1. 直接調用輸出函式 (`to_json/to_markdown/to_docx`)
2. 無 helper 或 wrapper 可能繞過驗證
3. 無條件分支可能跳過驗證
4. 無中間層可能干擾驗證

### 4.2 異常處理影響評估
外部服務的異常處理降級（web 檢索、twinkle 檢索）只影響來源檢索階段，不影響：
- 原文段落的處理
- 輸出格式轉換的正確性
- 直接比對驗證的有效性

### 4.3 測試覆蓋完整性
`test_output_consistency.py` 提供了完整的直接比對驗證：
- 覆蓋三種輸出格式 (JSON, Markdown, DOCX)
- 驗證原文逐字保留
- 驗證段落順序保持
- 驗證跨格式一致性
- 驗證 pipeline 輸出與解析文件一致
- 包含明確失敗報告測試

### 4.4 風險評估
**風險等級：低**

理由：
1. 所有呼叫路徑都是直接調用，無繞過可能
2. 異常處理只在外部服務層，不影響輸出驗證
3. 測試覆蓋完整，包含多種驗證角度
4. 無 integration 標記影響，預設執行即包含驗證

## 五、驗收標準檢查

- [x] 已盤點所有非 integration 呼叫路徑
- [x] 已確認直接比對驗證沒有被 helper、wrapper 或條件分支繞過
- [x] 已檢查異常處理是否影響驗證有效性
- [x] 已將結論寫成 docs/ 下的 .md 報告
- [x] 報告包含具體檔案位置與行號引用
- [x] 報告包含觸發條件分析
