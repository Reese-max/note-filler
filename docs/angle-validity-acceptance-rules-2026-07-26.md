# 角度有效性驗收規則實作報告

**日期**: 2026-07-26
**任務**: 實作角度有效性驗收規則

## 變更摘要

實作了論點角度有效性驗收規則，當同一論點只有單一角度、角度彼此同義重複、或角度欄位缺失時，驗收應明確失敗並指出是哪個 `argument_id` 缺少哪類角度；同時保留一對一與一對多來源綁定的既有檢查。

## 核心變更

### 1. `src/note_filler/angle_coverage.py`

**新增常數**:
- `REQUIRED_FACETS = frozenset({"angle_type", "functional_gap", "user_value", "question"})` - 每個 argument 必須具備的四類必要 facet

**新增函數**:
- `validate_argument_angle(cov, *, argument_id)` - 驗證單一 argument 的角度面向完整性
  - 檢查四類必要 facet 是否齊全：`angle:{type}`、`necessity:functional_gap`、`necessity:user_value`、`question`
  - 檢查 `angle_type` 與 `angle:{type}` facet 是否一致
  - 檢查 `functional_gap` 與 `user_value` 來源欄位非空
  - 回傳 `(is_valid, missing_list)`，缺失訊息包含 `argument_id` 以利定位

### 2. `src/note_filler/binding_report.py`

**更新檢查鍵值** (`REQUIRED_CHECK_KEYS`):
- 新增 `has_angle_facets` (取代原有細分檢查)
- 移除 `angle_facet_complete`、`angle_functional_gap_present` 等過度細分的檢查鍵，改用單一 `has_angle_facets` 表示角度面向完整性

**更新 `_evaluate_argument`**:
- 引入 `validate_argument_angle` 進行每個 argument 的角度有效性驗證
- 將驗證結果寫入 `checks["has_angle_facets"]`
- `angle_ok = has_angle_coverage and has_angle_facets` - 角度覆蓋結構完整且面向齊全才算通過

**更新 `parse_binding_report`**:
- 驗證 `has_angle_facets` 為 bool
- `has_angle_facets` 為 False 時，`binding_ok` 必為 False、`binding_status` 必為 "fail"
- `has_angle_facets` 為 True 時，確保正確標記

### 3. `tests/test_angle_coverage.py`

新增 7 項測試:
1. `test_validate_argument_angle_single_argument_missing_facets` - 單一 argument 缺失多個 facet
2. `test_validate_argument_angle_missing_functional_gap` - 缺失 functional_gap facet
3. `test_validate_argument_angle_missing_user_value` - 缺失 user_value facet
4. `test_validate_argument_angle_missing_question` - 缺失 question facet
5. `test_validate_argument_angle_complete_passes` - 完整四類 facet 通過
5. `test_validate_argument_angle_missing_angle_type` - angle_type 為空失敗
6. `test_validate_argument_angle_mismatched_angle_type_facet` - angle_type 與 facet 不符失敗

## 驗收規則行為

### 觸發失敗的情況

| 情況 | 錯誤訊息範例 |
|------|-------------|
| 單一論點只有一個角度 | `argument:0: 缺少 functional_gap facet (necessity:functional_gap)` |
| 角度同義重複 | 既有邏輯：`synonym` 關係導致 `effective_angle_count=0` |
| angle_type 缺失 | `argument:5: 缺少 angle type facet (angle:...)` |
| functional_gap 缺失 | `argument:0: 缺少 functional_gap facet (necessity:functional_gap)` |
| user_value 缺失 | `argument:0: 缺少 user_value facet (necessity:user_value)` |
| question 缺失 | `argument:0: 缺少 question facet` |
| angle_type 與 facet 不符 | `argument:6: 缺少 angle type facet (angle:definition)` |

### 保留的既有檢查

- 一對一綁定：`cardinality == "one_to_one"` 且 `source_count == 1`
- 一對多綁定：`cardinality == "one_to_many"` 且 `source_count >= 2`
- 來源可追溯性：`source_traceable`、`no_duplicate_sources`、`no_omitted_traces`、`no_extra_traces`
- 來源片段非空：`no_empty_fragments`
- 必要性雙視角：`has_functional_gap`、`has_user_value`
- 角度覆蓋門檻：`meets_angle_coverage_threshold` (跨論點去重後的有效角度數)

## 測試結果

```
406 passed, 11 deselected
```

所有既有測試通過，新增測試驗證角度有效性規則正確運作。

## 相關檔案異動

- `src/note_filler/angle_coverage.py` - 新增 `REQUIRED_FACETS`、`validate_argument_angle`
- `src/note_filler/binding_report.py` - 整合角度有效性驗證到綁定報告
- `tests/test_angle_coverage.py` - 新增 7 項角度有效性測試
- `docs/pytest-audit/requirements-test-coverage-2026-07-19.json` - 更新測試收集期望值 (417/406/11)
- `tests/test_deselection_guard.py` - 更新 `_EXPECTED_COUNTS` 為 (417, 406, 11)