# 論點區塊延伸閱讀欄位缺口盤點與實作（2026-07-28）

## 範圍

盤點成品筆記的論點區塊渲染/序列化路徑，找出每個論點只輸出單一來源或缺少延伸閱讀欄位的最後缺口，並實作三個新增機器可讀欄位。

## 缺口分析

### 原始狀態

每個論點（supplement segment）只輸出實際被 LLM 引用的來源（`used_source_ids`）。檢索到但未被引用的候選來源在 `pipeline.py:run_pipeline()` 中被計算為 `omitted_ids`，但僅記錄稽核事件後即丟棄，不會出現在任何最終成品中。

### 缺口位置

**最後缺口：** `export.py` 的 `to_json()`、`to_markdown()`、`to_docx()` 三個輸出函式。

理由：即使資料模型（`Segment`）或綁定報告（`binding_report.py`）已有欄位，若最終成品輸出層未序列化這些欄位，下游消費者仍無法取得延伸閱讀資訊。

### 缺失欄位

| 欄位 | 型別 | 說明 |
|---|---|---|
| `extended_readings` | `list[dict]` | 檢索到但未被引用的候選來源，每筆含 `source_id`、`title`、`level`、`url`、`distance` |
| `extended_readings_status` | `str` | `"none"`（無延伸閱讀）、`"available"`（有候選來源）、`"pending_evidence"`（待補證） |
| `pending_evidence_reason` | `str` | 為何此論點缺乏足夠來源的文字說明 |

## 實作內容

### 資料流

```
retrieve_for_gap() → sources (全部候選)
    ↓
write_supplement() → WrittenSupplement (used_source_ids + omitted_source_ids)
    ↓
pipeline.py → omitted_source_ids 寫入 WrittenSupplement
    ↓
assemble_correction() → Segment.extended_readings / extended_readings_status / pending_evidence_reason
    ↓
export.py → to_json() / to_markdown() / to_docx() 輸出附加區塊
binding_report.py → _evaluate_argument() 輸出可機器驗證欄位
```

### 修改檔案

| 檔案 | 改動 |
|---|---|
| `src/note_filler/write.py` | `WrittenSupplement` 新增 `omitted_source_ids` 欄位 |
| `src/note_filler/pipeline.py` | 計算 `omitted_ids` 後寫入 `w.omitted_source_ids` |
| `src/note_filler/correction.py` | `Segment` 新增三欄；`assemble_correction()` 計算並填入 |
| `src/note_filler/export.py` | `to_json()` 輸出三欄；`to_markdown()`/`to_docx()` 輸出延伸閱讀附加區塊 |
| `src/note_filler/binding_report.py` | `REQUIRED_ARGUMENT_KEYS` 新增三欄；`_evaluate_argument()` 輸出；`parse_binding_report()` 驗證 |
| `tests/test_extended_readings.py` | 新增 15 個測試（正例+負例+边界） |
| `tests/test_output_consistency.py` | 過濾邏輯新增延伸閱讀行 |
| `tests/test_fault_injection.py` | 更新断言：允許來源出現在延伸閱讀區塊 |

### 品質閘不變式

- **原稿逐字不變**：`Segment.text` 與原文完全一致，延伸閱讀只作為附加區塊。
- **無來源/待補證**：`extended_readings_status="pending_evidence"` + `pending_evidence_reason` 非空。
- **來源綁定**：`extended_readings` 只含實際檢索到的候選來源，不可虛構。
- **法條引用**：延伸閱讀不影響既有離線查核流程。

## 測試結果

```
726 passed, 1 skipped, 12 deselected
```

新增 15 個延伸閱讀專屬測試全部通過：
- 4 個 JSON 輸出正例
- 3 個 Markdown 輸出正例
- 1 個 DOCX 輸出正例
- 3 個 binding_report 正例
- 3 個負例（缺欄/非法值/空 reason）
- 1 個原稿不可變性測試
