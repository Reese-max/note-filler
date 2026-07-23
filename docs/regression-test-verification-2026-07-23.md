# 回歸測試驗證報告

## 驗證日期
2026-07-23

## 任務目標
以目前 repo 的驗收指令重跑一次相關測試，並另加上新回歸測試的 node id 單獨執行，保存實際失敗/通過輸出，確認錯配時是由「輸出 vs 筆記內容」直接比對失敗。

## 新回歸測試資訊

### 測試類別
`TestConsistencyBypassRegression`

### 測試方法
`test_modified_correctiondoc_original_segment_detected_in_json_export`

### 完整 Node ID
`tests/test_output_consistency.py::TestConsistencyBypassRegression::test_modified_correctiondoc_original_segment_detected_in_json_export`

### 測試目的
模擬中間層靜默修改 CorrectionDoc 原文段內容的 bypass 情境，驗證直接比對機制仍會攔下此類修改。

## 驗收指令執行結果

### 執行指令
```bash
python -m pytest -m "not integration" -q
```

### 執行輸出
```
.....................................F.................................. [ 39%]
....................................................................F... [ 78%]
.......................................                                  [100%]
================================== FAILURES ===================================
____________________ test_integration_allowlist_is_stable _____________________

    def test_integration_allowlist_is_stable() -> None:
        """The current default deselection must exactly match the approved list."""
        all_tests, _, _ = _collect_tests("-o", "addopts=")
        selected_tests, _, _ = _collect_tests()
        actual = sorted(set(all_tests) - set(selected_tests))
        counts = (len(all_tests), len(selected_tests), len(actual))
        added = sorted(set(actual) - set(ALLOWED_INTEGRATION_TESTS))
        removed = sorted(set(ALLOWED_INTEGRATION_TESTS) - set(actual))
>       assert (
            counts == _EXPECTED_COUNTS
            and actual == ALLOWED_INTEGRATION_TESTS
        ), (
            f"Deselected test allowlist mismatch "
            f"(collected/selected/deselected: expected {_EXPECTED_COUNTS}, "
            f"got {counts}).\n"
            f"  Newly deselected (add to allowlist): {added}\n"
            f"  No longer deselected (remove from allowlist): {removed}"
        )
E       AssertionError: Deselected test allowlist mismatch (collected/selected/deselected: expected (190, 179, 11), got (194, 183, 11)).
E           Newly deselected (add to allowlist): []
E           No longer deselected (remove from allowlist): []
E       assert ((194, 183, 11) == (190, 179, 11)
E         
         At index 0 diff: 194 != 190
E         Use -v to get more diff)

tests\test_deselection_guard.py:409: AssertionError
______ test_default_gate_collects_every_equivalent_and_safety_regression ______

    def test_default_gate_collects_every_equivalent_and_safety_regression() -> None:
        matrix = _load(_MATRIX)
        path_audit = _load(_PATH_AUDIT)
        allowlist_ids = {row["test_id"] for row in _load(_ALLOWLIST)}
        default_ids = _default_collected_ids()
        all_ids = default_ids | allowlist_ids
    
        expected = matrix["default_gate"]["expected_collection"]
>       assert len(default_ids) == expected["default_selected"]
E       AssertionError: assert 183 == 179
E        +  where 183 = len({'tests/test_citation_formatter.py::test_build_reference_lines_two_sources', 'tests/test_cli.py::test_iter_inputs_expa...ll_eight_allowlist_nodes', 'tests/test_conclusion_classification.py::test_classification_index_schema_and_labels', ...})

tests/test_requirements_test_coverage.py:167: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_deselection_guard.py::test_integration_allowlist_is_stable
FAILED tests/test_requirements_test_coverage.py::test_default_gate_collects_every_equivalent_and_safety_regression
2 failed, 181 passed, 11 deselected in 102.05s (0:01:42)
```

### 失敗原因分析
1. **計數不匹配**：新增的回歸測試導致測試總數從 190 增加到 194，選中數從 179 增加到 183
2. **配置未同步更新**：`test_deselection_guard.py` 和 `test_requirements_test_coverage.py` 中的預期計數仍為舊值

## 新回歸測試單獨執行結果

### 執行指令
```bash
python -m pytest tests/test_output_consistency.py::TestConsistencyBypassRegression::test_modified_correctiondoc_original_segment_detected_in_json_export -v
```

### 執行輸出
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\3244c364
configfile: pyproject.toml
plugins: anyio-4.14.2, langsmith-0.8.9, cov-7.1.0, split-0.11.0, timeout-2.4.0, xdist-3.8.0
collecting ... collected 1 item

tests/test_output_consistency.py::TestConsistencyBypassRegression::test_modified_correctiondoc_original_segment_detected_in_json_export PASSED [100%]

============================== 1 passed in 0.21s ==============================
```

### 測試結果
**PASSED** - 測試通過，表示 bypass 檢測機制正常運作

## 錯配檢測機制分析

### 測試邏輯驗證
該測試確實驗證「輸出 vs 筆記內容」的直接比對失敗檢測：

1. **模擬 bypass 情境**：測試故意修改 CorrectionDoc 中 original segment 的文字（從"正當程序"改為"正當法律程序"）
2. **導出 JSON**：將修改後的 CorrectionDoc 導出為 JSON 格式
3. **直接比對**：從 JSON 中提取 original segments 的文字，與原始筆記內容進行逐字比對
4. **檢測不匹配**：如果發現不匹配，測試通過（表示 bypass 被檢測到）
5. **失敗條件**：如果沒有發現不匹配，測試失敗（表示 bypass 檢測機制失效）

### 比對路徑確認
```
原始筆記內容 → parse_note() → CorrectionDoc.original.full_text
                                       ↓
                                   (中間層修改)
                                       ↓
                               CorrectionDoc.segments[i].text (被修改)
                                       ↓
                                   to_json() 導出
                                       ↓
                               JSON["segments"][i]["text"]
                                       ↓
                               與原始筆記內容直接比對
```

### 結論
測試通過證明：
- 當中間層靜默修改 CorrectionDoc 的原文段內容時
- JSON 導出後的「輸出 vs 筆記內容」直接比對能夠檢測到不一致
- 即使其他 pipeline 檢查通過，輸出一致性驗證仍能攔下此類 bypass

## 需要修正的配置

### 計數不匹配原因
新增的回歸測試導致測試總數增加：
- 總測試數：190 → 194 (+4)
- 選中測試數：179 → 183 (+4)
- Deselected 測試數：11 → 11 (不變)

### 需要更新的檔案
1. `tests/test_deselection_guard.py`：更新 `_EXPECTED_COUNTS` 從 (190, 179, 11) 到 (194, 183, 11)
2. `docs/pytest-audit/requirements-test-coverage-2026-07-19.json`：更新 `default_gate.expected_collection.default_selected` 從 179 到 183

