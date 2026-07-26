# argument_id 到最終輸出的資料流盤點：關聯知識缺口分析

## 任務背景
盤點 `argument_id` 到最終輸出的資料流，找出目前「關聯知識」仍停留在內部資料、未落到成品/序列化/報告的最後一個缺口。

## 資料流分析

### 1. argument_id 產生點
**檔案：** `src/note_filler/correction.py`  
**函式：** `assemble_correction()` (line 192)  
**產生方式：** `argument_id = f"argument:{arg_idx}"`

### 2. 關聯知識（related_knowledge）定義
「關聯知識」在 codebase 中實際上就是 `summary` 欄位，即論點的摘要內容。在輸出時以 `related_knowledge` 標籤顯示。

### 3. 資料流追蹤

#### 3.1 內部資料層（Segment）
**檔案：** `src/note_filler/correction.py`  
**函式：** `assemble_correction()` (line 230)  
**欄位：** `summary=text`  
**狀態：** ✅ 已寫入 Segment.dataclass

#### 3.2 機器可讀報告層（binding_report）
**檔案：** `src/note_filler/binding_report.py`  
**函式：** `_evaluate_argument()` (line 255-258, 371)  
**欄位：** `summary`  
**狀態：** ✅ 已寫入 argument dict，屬於 REQUIRED_ARGUMENT_KEYS

#### 3.3 序列化層（export.py to_json）
**檔案：** `src/note_filler/export.py`  
**函式：** `to_json()` → `_seg_argument_fields()` (line 139)  
**欄位：** `summary`  
**狀態：** ✅ 已寫入 JSON segments

#### 3.4 人類可讀輸出層（export.py to_markdown）
**檔案：** `src/note_filler/export.py`  
**函式：** `to_markdown()` → `_visible_summary_text()` (line 70-77)  
**顯示方式：** `related_knowledge={argument['summary']}`  
**狀態：** ✅ 已顯示為「關聯知識」

#### 3.5 Web 輸出層（result.html）
**檔案：** `app/templates/result.html` (line 76-77)  
**顯示方式：** `related_knowledge（關聯知識）`  
**狀態：** ✅ 已顯示

## 結論

**「關聯知識」已完整落地到所有輸出層級，無缺口。**

具體證據：
1. **內部資料層：** `Segment.summary` 欄位已存在並正確賦值
2. **機器可讀報告：** `binding_report.py` 的 `REQUIRED_ARGUMENT_KEYS` 包含 `summary`，且 `_evaluate_argument()` 正確寫入
3. **序列化層：** `export.py:to_json()` 的 `_seg_argument_fields()` 正確輸出 `summary`
4. **人類可讀輸出：** `to_markdown()` 透過 `_visible_summary_text()` 以 `related_knowledge` 標籤顯示
5. **Web 輸出：** `result.html` 明確顯示 `related_knowledge（關聯知識）`

## 測試覆蓋驗證

測試已驗證關聯知識的輸出：
- `tests/test_source_binding_acceptance.py` (line 1296, 1350)：解析 `related_knowledge` 欄位
- `tests/test_export.py` (line 285, 291)：驗證 JSON 輸出中的 `related_knowledge` 內容
- `tests/test_server.py` (line 131)：驗證 Web 輸出包含 `related_knowledge（關聯知識）`

## 最後缺口

**無缺口。** 關聯知識（summary）已完整從內部資料流轉到所有最終輸出格式（JSON、Markdown、HTML）。

## 需改動的檔案與函式

**無需改動。** 所有層級均已正確實現關聯知識的落地。

## 新增機器可讀欄位建議

**無需新增。** 現有 `summary` 欄位已滿足機器可讀需求，且：
- 在 `binding_report.py` 中已屬於 `REQUIRED_ARGUMENT_KEYS`
- 在 `export.py:to_json()` 中已正確序列化
- 在測試中已可被正確解析驗證

若需新增語意層次的欄位（如 `related_relation`、`decision_value`），需另行定義需求與資料來源，目前不在本次盤點範圍內。