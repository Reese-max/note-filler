# 「吞錯仍全綠」回歸測試補強報告

> 產出日期：2026-07-28  
> 範圍：`tests/deselected_allowlist.json` 對照表中未被現有 `not integration` 測試直接驗證的失敗語義  
> 方法：針對「吞錯仍全綠」路徑新增最小化回歸測試

---

## 背景

`docs/deselected-failure-semantic-coverage-2026-07-22.md` 分析指出，8 個 deselected integration 測試皆存在至少一種 vacuous pass 或例外傳遞的靜默失敗模式。其中「吞錯仍全綠」路徑特指：

**例外被 pipeline 靜默捕獲後，產出降級但仍被判定為成功**——測試 green、流程 exit=0，但實質產出不完整。

---

## 未被覆蓋的失敗語義

| # | Code Path | 風險 | 現有覆蓋 | 缺口 |
|---|-----------|------|----------|------|
| 1 | `pipeline.py:184-198` `write_supplement` 例外 → pending_evidence 降級 | pipeline 吞掉例外、補充段以【待補證】佔位，測試不驗證降級行為 | ❌ 無直接覆蓋 | `test_run_pipeline_malformed_gap_output_falls_back_to_pending` 只測 malformed gap JSON fallback（gap.py:82-90），不觸及 write_supplement 例外 |
| 2 | `detect_gaps` 回空 → 無 supplement → pipeline 仍以 original 段通過 | 無缺口時 vacuous pass（C6 迴圈不執行），但 require_non_empty_note_product 仍靠 original 通過 | ⚠️ 間接覆蓋 | 無直接驗證「全 covered → 無 supplement → pipeline 穩定」路徑 |

---

## 新增測試

**檔案**：`tests/test_swallow_error_still_green.py`（2 個 test case）

### 1. `test_write_supplement_exception_yields_pending_evidence`

- **目標**：驗證 `pipeline.py:184-198` 的 except 分支
- **手法**：FakeLLM 只餵 4 個 response，第 5 次 `llm.complete`（`write_supplement` 內部）觸發 `IndexError`
- **預期**：
  - pipeline 不中斷（exit 正常）
  - 補充段以「【待補證】」開頭
  - `source_ids == []`、`confidence == "pending_evidence"`、`sources == []`
- **若路徑被移除**：`write_supplement` 的 `IndexError` 向上傳播 → 測試紅燈

### 2. `test_empty_gaps_still_produces_nonempty_note`

- **目標**：驗證 `detect_gaps` 回空時 pipeline 的 vacuous pass 行為
- **手法**：LLM 回所有問題為 `covered` → gaps 過濾後為空 → 無 supplement
- **預期**：
  - `supplements == []`
  - `originals` 保留完整原稿（2 段）
  - `require_non_empty_note_product` 靠 original 段通過

---

## 與既有測試的差異

| 測試 | 路徑 | 差異 |
|------|------|------|
| `test_run_pipeline_malformed_gap_output_falls_back_to_pending` | gap.py:82-90（JSON 解析失敗 fallback） | 測 gap parser fallback，不觸及 write_supplement 例外 |
| `test_pipeline::test_write_supplement_exception_yields_pending_evidence` | pipeline.py:184-198（write_supplement 例外降級） | **新增**：直接驗證 write_supplement 例外被吞的行為 |
| `test_pipeline::test_empty_gaps_still_produces_nonempty_note` | pipeline.py:181（空 gaps vacuous pass） | **新增**：直接驗證全 covered → 無 supplement → pipeline 穩定 |

---

## 驗證結果

```
tests/test_swallow_error_still_green.py::test_write_supplement_exception_yields_pending_evidence PASSED
tests/test_swallow_error_still_green.py::test_empty_gaps_still_produces_nonempty_note PASSED

完整非整合測試：703 passed, 11 deselected
```
