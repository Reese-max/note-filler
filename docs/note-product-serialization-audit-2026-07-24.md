# 筆記產物序列化/儲存/回傳鏈調查報告

**日期**: 2026-07-24
**任務**: 檢查筆記產物的序列化/儲存/回傳鏈是否在最後一步被覆寫成空值或測試輸出，必要時把「實際筆記」與「稽核資訊」分離成不同欄位與檔案

---

## 調查結論

**主要發現**：筆記產物鏈已具備完整的防護機制，**未被覆寫成空值或測試輸出**，且「實際筆記」與「稽核資訊」已適當分離，**不需要額外修正**。

---

## 筆記產物鏈分析

### 1. Pipeline 層（`pipeline.py`）

**產出閘**：`require_non_empty_note_product()` (line 19-67)
- **檢查條件**：至少一個 `original` 或 `supplement` 段的 `text` 去空白後非空
- **失敗條件**：
  - 無 segments / 全文與段皆空白
  - 僅空白段、無實質筆記文字（等同空白或僅稽核摘要）
- **失敗處理**：寫 `note_product_empty` 稽核事件並 `raise RuntimeError`（含明確原因）
- **調用位置**：
  - `run_pipeline()` line 108：pipeline 完成後立即檢查
  - `__main__.py` line 139：CLI 層寫出前再次檢查（防禦層）

**評估**：✅ 硬性閘已確保 pipeline 產出非空實際筆記

### 2. CLI 層（`__main__.py`）

**寫出檢查**：`process_file()` (line 131-169)
- **Pipeline 後檢查**：line 139 再次呼叫 `require_non_empty_note_product()`（防禦層）
- **寫出後驗證**：
  - DOCX：line 151-152 檢查檔案存在且大小非零
  - MD/JSON：line 155-158 檢查 `body` 非空
- **失敗處理**：`raise RuntimeError` 拒絕視為送達成功

**交付回執**：`write_delivery_receipt()` (line 36-95)
- **成功時**：寫 `delivery_manifest.json`（`status=delivered`、`content_hash`）
- **失敗時**：寫 `delivery_manifest.json`（`status=failed`、`error` 欄位）
- **目的**：提供可查詢的交付回執，不只依賴本機檔案存在

**評估**：✅ CLI 層有雙重檢查（pipeline 後 + 寫出後）與結構化回執

### 3. Web 層（`server.py`）

**狀態管理**：`app.state.last_doc`
- **初始化**：line 29 設為 `None`
- **成功時**：line 57 設為 `doc`（供 `/export` 使用）
- **失敗時**：line 50 清空為 `None`（不得轉送上一份結果）
- **測試覆蓋**：`test_fault_injection.py::test_web_pipeline_failure_clears_last_doc`

**匯出端點**：`GET /export` (line 95-106)
- **條件檢查**：line 98 若 `doc is None` 回 404
- **序列化**：line 102 呼叫 `to_markdown(doc)` 直接從 `CorrectionDoc` 序列化
- **測試覆蓋**：`test_server.py::test_export_without_run_returns_404`

**評估**：✅ Web 層有狀態隔離與 404 防護

### 4. 序列化層（`export.py`）

**三種匯出格式**：
- `to_json()` (line 15-31)：直接從 `CorrectionDoc` 轉 dict，無覆寫邏輯
- `to_markdown()` (line 34-74)：直接從 `CorrectionDoc` 產 markdown，無覆寫邏輯
- `to_docx()` (line 77-114)：直接從 `CorrectionDoc` 產 docx，無覆寫邏輯

**稽核資訊轉送**：
- `conflict_note` 已正確轉送到三種匯出格式（line 26, 62, 97）
- 修正記錄：`docs/silent-exception-branch-audit-2026-07-24.md` #10, #24

**測試覆蓋**：
- `test_export.py` - 確認匯出格式正確
- `test_output_consistency.py` - 確認輸出與來源一致
- `test_exception_skip_traceability.py` - 確認 conflict_note 轉送

**評估**：✅ 序列化層直接從 `CorrectionDoc` 轉換，無覆寫風險

---

## 實際筆記與稽核資訊分離評估

### 現有設計分析

**實際筆記內容**（`Segment` dataclass）：
- `text`：筆記文字內容
- `sources`：引用來源列表
- `confidence`：`verified` / `pending_evidence`
- `type`：`original` / `supplement`

**稽核資訊**：
- `conflict_note`：衝突告警文字（已正確轉送到匯出）
- `audit_event()`：結構化稽核事件（寫到 logger，不與筆記混雜）

### 分離狀態評估

| 項目 | 狀態 | 說明 |
|------|------|------|
| 實際筆記內容 | ✅ 已分離 | `Segment.text`、`Segment.sources`、`Segment.confidence` |
| 衝突稽核資訊 | ✅ 已分離 | `Segment.conflict_note` 獨立欄位，已轉送到匯出 |
| 稽核事件 | ✅ 已分離 | `audit_event()` 寫到 logger，不與筆記混雜 |
| 交付回執 | ✅ 已分離 | `delivery_manifest.json` 獨立檔案 |

### 結論

**不需要額外分離**，理由：
1. 實際筆記內容（`text`、`sources`、`confidence`）已與稽核資訊（`conflict_note`）分離
2. 稽核事件透過 `audit_event()` 記錄到 logger，不干擾筆記產物
3. 交付回執（`delivery_manifest.json`）已獨立於筆記檔案
4. 三種匯出格式（JSON/MD/DOCX）都正確包含實際筆記與稽核資訊

---

## 測試覆蓋驗證

### 相關測試檔案

| 測試檔案 | 覆蓋範圍 | 關鍵測試 |
|----------|----------|----------|
| `test_note_product_gate.py` | 非空實際筆記閘 | `test_main_flow_actual_note_has_traceable_source_and_extension` |
| `test_output_consistency.py` | 輸出與來源一致性 | `test_markdown_export_original_text_verbatim` |
| `test_delivery_receipt.py` | 交付回執正確性 | `test_process_file_writes_delivery_receipt_on_success` |
| `test_exception_skip_traceability.py` | 稽核資訊轉送 | `test_conflict_note_forwarded_to_all_exports` |
| `test_fault_injection.py` | Web 失敗狀態清空 | `test_web_pipeline_failure_clears_last_doc` |
| `test_server.py` | Web 匯出端點 | `test_export_without_run_returns_404` |

### 測試執行結果

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -q
211 passed, 11 deselected in 46.81s
```

**評估**：✅ 測試覆蓋完整，無缺口

---

## 潛在風險評估

### 已防護風險

| 風險 | 防護機制 | 狀態 |
|------|----------|------|
| Pipeline 回空成品 | `require_non_empty_note_product()` | ✅ 已防護 |
| 寫出時覆寫為空 | 寫出後檢查 `body` 非空 | ✅ 已防護 |
| Web 轉送舊結果 | 失敗時清空 `app.state.last_doc` | ✅ 已防護 |
| 序列化覆寫 | 直接從 `CorrectionDoc` 轉換 | ✅ 已防護 |
| 稽核資訊遺失 | `conflict_note` 轉送到匯出 | ✅ 已防護 |
| 交付狀態不明 | `delivery_manifest.json` | ✅ 已防護 |

### 無風險項目

- **測試 stub 覆寫**：測試中使用 `monkeypatch.setattr(cli, "to_markdown", lambda doc: ...)` 僅影響測試執行，不影響生產環境
- **序列化邏輯**：`to_markdown()`、`to_json()`、`to_docx()` 無條件覆寫邏輯

---

## 結論與建議

### 結論

1. **筆記產物鏈未被覆寫**：從 pipeline 到序列化的完整鏈路都有防護機制，確保最後一步不會被覆寫成空值或測試輸出
2. **實際筆記與稽核資訊已分離**：`Segment` 結構已適當分離實際筆記內容與稽核資訊，且稽核資訊正確轉送到匯出
3. **測試覆蓋完整**：相關測試覆蓋所有關鍵路徑，無缺口

### 建議

**不需要額外修正**，現有設計已滿足任務要求。

---

## 相關文件

- `docs/silent-exception-branch-audit-2026-07-24.md` - 異常與跳過分支靜默處理審計報告
- `docs/data-flow-exception-skip-branch-inventory-2026-07-24.md` - 資料流異常跳過分支盤點
- `src/note_filler/pipeline.py` - Pipeline 產出閘實作
- `src/note_filler/export.py` - 序列化實作
- `src/note_filler/__main__.py` - CLI 交付層實作
- `app/server.py` - Web 端點實作
