# 異常與跳過分支靜默處理審計報告

**日期**: 2026-07-24
**範圍**: note_filler 全部原始碼（src/ + app/）
**目標**: 為每個異常與跳過分支實作明確的重試、持久化、轉送、結構化告警或可查詢狀態回報

---

## 修正總覽

| # | 檔案 | 問題類型 | 修正方式 | 嚴重度 |
|---|------|---------|---------|--------|
| 1 | `__main__.py:165-175` | CLI batch 失敗無 manifest | 失敗時寫 `delivery_manifest.json` (status=failed) + traceback 到 logger | HIGH |
| 2 | `web.py:60-61` | `_extract_query` 靜默退回 | 補 `logger.warning` | MEDIUM |
| 3 | `web.py:107-108` | 單頁 fetch 失敗靜默 continue | 補 `logger.debug` | MEDIUM |
| 4 | `web.py:113-114` | `_grade` 失敗靜默 continue | 補 `logger.warning` | MEDIUM |
| 5 | `web.py:69-70` | `_grade` JSON 解析失敗無 log | 補 `logger.warning` 含 raw 回應 | MEDIUM |
| 6 | `twinkle.py:104-105` | MCP 空回應無 log | 補 `logger.warning` | MEDIUM |
| 7 | `twinkle.py:117-126` | 無可解析 payload 靜默 return {} | 補 `logger.warning` + 非 text 項目 `logger.debug` | MEDIUM |
| 8 | `write.py:53-60` | 越界 `[^n]` 標記靜默移除 | 補 `logger.warning` | MEDIUM |
| 9 | `correction.py:109-110` | source ID 找不到靜默丟棄 | 補 `logger.warning` 列出缺失 ID | HIGH |
| 10 | `correction.py:77` | `validations` 參數未使用(conflict_note 丟失) | 從 `validations[q]` 讀取 `conflict_note` 寫入 Segment | CRITICAL |
| 11 | `gap.py:71-73` | JSON parse fallback 無 log | 補 `logger.warning` 含 raw 回應 | MEDIUM |
| 12 | `gap.py:77-78` | 非 dict 項靜默 continue | 補 `logger.warning` | MEDIUM |
| 13 | `law_search.py:51-52` | 非 JSON 當 keyword 無 log | 補 `logger.warning` | LOW |
| 14 | `law_search.py:74` | 結果截斷至 20 條無 log | 補 `logger.info` | LOW |
| 15 | `law_citation_check.py:52-53` | 指代詞無前文靜默 continue | 補 `logger.debug` | LOW |
| 16 | `law_citation_check.py:70-71` | 法規名不在庫靜默 continue | 補 `logger.debug` | LOW |
| 17 | `law_lookup.py:119-120` | index build 跳過無 log | 補 `logger.warning` | MEDIUM |
| 18 | `domain.py:39-40` | fallback "other" 無 log | 補 `logger.warning` | HIGH |
| 19 | `questions.py:51-52` | JSON wrapper 回空清單無 log | 補 `logger.warning` | HIGH |
| 20 | `parse.py:49-53` | 空文件產生空 Document 無 log | 補 `logger.warning` | HIGH |
| 21 | `retrieve/__init__.py:37-41` | law 領域跳過 Level A 無 log | 補 `logger.warning` | HIGH |
| 22 | `pipeline.py:52-53` | `penalty_mismatch` findings 被忽略 | 新增 penalty_mismatch 降級 + `logger.warning` | HIGH |
| 23 | `app/server.py:40-52` | Web endpoint 無 try/except + temp 洩漏 | 包 try/except/finally, structured error + temp cleanup | HIGH |
| 24 | `export.py` | conflict_note 未匯出到 JSON/MD/DOCX | 新增 `conflict_note` 欄位到三種匯出格式 | HIGH |

---

## 關鍵修正詳解

### CRITICAL: validations 參數轉發 (#10)

**Before**: `assemble_correction()` 接收 `validations` 參數但從不讀取,`Validation.conflict` 與 `Validation.conflict_note` 永久丟失。
**After**: 從 `validations[q]` 讀取 `conflict_note` 寫入 `Segment.conflict_note`,確保衝突資訊到達輸出層。

### HIGH: CLI 失敗 manifest (#1)

**Before**: 例外只 print 到 stderr,無結構化記錄。
**After**: 寫 `delivery_manifest.json` (status=failed, error=錯誤訊息),下游可查詢交付狀態。

### HIGH: penalty_mismatch 處理 (#22)

**Before**: `check_law_citations` 回傳 `penalty_mismatch` findings 但 pipeline 只處理 `article_not_found`。
**After**: `penalty_mismatch` 同樣降級為 `pending_evidence`,避免含有不正確罰則金額的補充段被標為 verified。

### HIGH: Web endpoint 錯誤處理 (#23)

**Before**: 無 try/except,任何 pipeline 例外導致 raw 500; temp 檔永不清理。
**After**: try/except 回傳結構化錯誤頁面; finally 清理 temp 檔。

---

## 測試驗證

```
199 passed, 11 deselected in 47.31s
```

所有既有測試通過,包含:
- `test_correction.py::test_missing_written_entry_is_trackable_and_logged` — 確認靜默資料遺失已被攔截
- `test_pipeline.py` — 確認 pipeline 整體不變式
- `test_export.py` — 確認匯出格式正確（含新增 conflict_note 欄位）

---

## 無變更項目（評估後保留原設計）

| 項目 | 原因 |
|------|------|
| `web.py:136-143` DDG 搜尋失敗 | 已有 `logger.warning`,設計合理 |
| `web.py:148-157` trafilatura 抓取失敗 | 已有 `logger.warning`,外部服務韌性 |
| `twinkle.py:219-226` twinkle 查詢失敗 | 已有 `logger.warning`,外部服務降級 |
| `_extract_hits` 返回空清單 | 純提取函式,無副作用,呼叫端已有處理 |
