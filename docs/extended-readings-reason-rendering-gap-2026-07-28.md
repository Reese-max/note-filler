# 延伸閱讀待補證原因渲染缺口盤點與修復（2026-07-28）

## 範圍

盤點成品筆記論點區塊的 `extended_readings` 與 `pending_evidence_reason` 從內部資料模型到最終 markdown/DOCX 輸出的完整序列化/渲染路徑，找出最後一段缺口並修復。

## 資料流追蹤

### 完整路徑

```
retrieve_for_gap() → sources (全部候選)
    ↓
write_supplement() → WrittenSupplement (used_source_ids + omitted_source_ids)
    ↓
pipeline.py:run_pipeline() → omitted_source_ids 寫入 WrittenSupplement
    ↓
correction.py:assemble_correction() → Segment.extended_readings / extended_readings_status / pending_evidence_reason
    ↓
export.py:to_json()      → 三欄序列化為 JSON segment 欄位
export.py:to_markdown()   → _extended_readings_block() 渲染為 > 區塊
export.py:to_docx()       → 延伸閱讀段落 + 待補證原因段落
binding_report.py         → _evaluate_argument() 輸出三欄 + parse_binding_report() 驗證
```

### 各層實作狀態

| 層級 | 檔案:行號 | 狀態 |
|---|---|---|
| 資料模型 | `correction.py:179-182` | ✅ 三欄已在 Segment |
| 組裝邏輯 | `correction.py:348-379` | ✅ 計算 extended_readings/status/reason |
| JSON 序列化 | `export.py:481-483` | ✅ 三欄已輸出 |
| Markdown 渲染 | `export.py:243-261` | ⚠️ 已修復（見缺口） |
| DOCX 渲染 | `export.py:760-771` | ⚠️ 已修復（見缺口） |
| Binding report | `binding_report.py:497-502` | ✅ 三欄已輸出 |
| Binding 驗證 | `binding_report.py:957-981` | ✅ 嚴格校驗 |

## 缺口分析

### 原始狀態

`export.py:_extended_readings_block()` 原本的邏輯：

```python
if status == "pending_evidence" and reason:
    lines.append(f"> **待補證原因**：{reason}")
elif status == "available" and not readings:
    pass
```

**缺口：** 當 `extended_readings_status == "available"`（有候選來源但未被引用，例如 LLM 因來源與問題完全無關而回傳【待補證】）時，`pending_evidence_reason` 雖已在 Segment 上計算（值為「有候選來源但未被引用」），但 **不會出現在 markdown 或 DOCX 輸出中**。

### 影響場景

| 場景 | extended_readings_status | pending_evidence_reason | 原本是否輸出 reason |
|---|---|---|---|
| 無候選來源 | `pending_evidence` | 「檢索無可用來源」 | ✅ |
| 有候選但 LLM 未引用 | `available` | 「有候選來源但未被引用」 | ❌ **缺口** |
| 來源與問題完全無關 | `available` | 「來源與問題完全無關或無從作答」 | ❌ **缺口** |
| 引用來源不足 | `pending_evidence` | 「引用來源不足或未通過驗證」 | ✅ |

### 修復內容

將 `_extended_readings_block()` 的條件從 `status == "pending_evidence"` 改為 `if reason:`，讓所有 `pending_evidence_reason` 非空的論點（不論 status）都在输出中顯示原因。

同步修改 `to_docx()` 中的相同邏輯。

## 修改檔案

| 檔案 | 改動 |
|---|---|
| `src/note_filler/export.py` | `_extended_readings_block()`：移除 `status == "pending_evidence"` 條件，改為 `if reason:` |
| `src/note_filler/export.py` | `to_docx()`：同步移除 `status == "pending_evidence"` 條件 |
| `tests/test_extended_reading_negative.py` | 新增 2 個回歸測試：available 狀態下 markdown/DOCX 均顯示待補證原因 |

## 品質閘不變式（不受影響）

- **原稿逐字不變**：延伸閱讀只作為附加區塊，不改動原文
- **無來源/待補證**：`extended_readings_status="pending_evidence"` + `pending_evidence_reason` 非空（由 `parse_binding_report` 嚴格校驗）
- **來源綁定**：`extended_readings` 只含實際檢索到的候選來源
- **法條引用**：延伸閱讀不影響既有離線查核流程

## 測試結果

```
824 passed, 1 skipped, 12 deselected
```

新增 2 個回歸測試：
- `test_markdown_available_status_shows_reason_when_present`：available 狀態下 markdown 顯示待補證原因
- `test_docx_available_status_shows_reason_when_present`：available 狀態下 DOCX 顯示待補證原因
