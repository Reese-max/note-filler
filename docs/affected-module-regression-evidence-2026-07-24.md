# 受影響模組精準回歸測試證據 — 2026-07-24

## 測試範圍：最近 5 個 commit 受影響模組

| Commit | 受影響原始碼 | 受影響測試 |
|--------|-------------|-----------|
| af216ca fix(correction) | `src/note_filler/correction.py` | `tests/test_correction.py` (+1 new test) |
| 64a480f test(twinkle) | `src/note_filler/retrieve/twinkle.py` | `tests/test_twinkle.py` |
| 3e65004 fix(retrieve) | `src/note_filler/retrieve/web.py` | `tests/test_web.py`, `tests/test_correction.py` |
| efb1b6c test(consistency) | — | `tests/test_output_consistency.py` |
| 4a0c513 fix(ci) | — | `tests/test_deselection_guard.py`, `tests/test_deselected_ci_gate_acceptance.py` |

## 執行結果

### 批次 1：correction 模組（14 測試）

```
tests/test_correction.py ..............                                   [100%]
14 passed

- test_missing_written_entry_is_trackable_and_logged  ← 新増邊界案例
```

### 批次 2：deselection guard（5 測試）

```
tests/test_deselection_guard.py .....                                     [100%]
5 passed

- 驗證 (197, 186, 11) 計數一致性
- 驗證代償 mapping 完整性
- 驗證 C7 正確性路徑未被排除
```

### 批次 3：deselected CI gate（12 測試）

```
tests/test_deselected_ci_gate_acceptance.py ............                  [100%]
12 passed

- 允許清單穩定、排除漂移偵測、代償覆蓋完整性
```

### 批次 4：output consistency（18 測試）

```
tests/test_output_consistency.py ..................                       [100%]
18 passed

- 正常：markdown/json/docx 原文逐字保留
- 邊界：空白筆記、純空白、單段、特殊字元、Unicode
- 異常顯式暴露 (TestExplicitFailureReporting)：修改原文、缺段、全文不符 → 斷言失敗
- 回歸 bypass 防護
```

### 批次 5：全量非整合測試（186 測試）

```
collected 197 items / 11 deselected / 186 selected
186 passed in 40.18s
```

## 正常路徑確認

- 原文逐字不可變：test_original_segments_verbatim_and_immutable ✓
- 整合校正流程：test_run_pipeline_invariant, test_run_pipeline_law_domain ✓
- 各種 confidence 分級（A/B/C/D）校正：全部通過 ✓
- 跨格式匯出 roundtrip：test_to_docx_roundtrip, test_to_json, test_to_markdown ✓
- 一致性 3 格式交叉比對：test_output_artifacts_consistent_across_formats ✓

## 異常與邊界路徑顯式暴露

| 測試 | 情境 | 驗證方式 |
|------|------|---------|
| `test_missing_written_entry_is_trackable_and_logged` | written 字典缺 key | 斷言 `【待補證】` 佔位 + `pending_evidence` + logger.warning |
| `TestExplicitFailureReporting::test_assertion_fails_on_modified_original_text` | 原文被改 | 斷言 pytest 顯式 FAIL |
| `TestExplicitFailureReporting::test_assertion_fails_on_missing_paragraph_in_markdown` | 輸出缺段 | 斷言 pytest 顯式 FAIL |
| `TestExplicitFailureReporting::test_assertion_fails_on_json_full_text_mismatch` | 全文不符 | 斷言 pytest 顯式 FAIL |
| `TestConsistencyEdgeCases::test_empty_note_produces_empty_original_segments` | 空輸入 | empty segments |
| `TestConsistencyEdgeCases::test_note_with_only_whitespace` | 純空白 | whitespace-handling |
| `test_gap.py::test_detect_gaps_parse_failure_marks_all_missing` | JSON parse 失敗 | fallback all missing |
| `test_llm.py::test_grokclient_urlopen_error` | 連線錯誤 | error propagation |
| `test_llm.py::test_grokclient_json_decode_error` | 回應非 JSON | error propagation |
| `test_write.py::test_pending_evidence_when_insufficient` | 來源不足 | pending_evidence |
| `test_web.py::test_search_exception_degrades_to_empty` | 網路例外 | degrades to empty |
| `test_server.py::test_export_without_run_returns_404` | 未執行即匯出 | 404 response |

## 測試集合計數驗證

```
collected 197 items
- 186 selected (non-integration, 全部 PASS)
- 11 deselected (integration marker，核准清單一致)
```

對照 `test_deselection_guard.py:_EXPECTED_COUNTS = (197, 186, 11)` → 一致。

## 結論

**通過**。三步驟驗證完成：
1. 受影響模組 `correction.py`/`twinkle.py`/`web.py` 的精準測試集全部通過
2. 正常路徑（原文保留、confidence 分級、跨格式一致性）確認無回歸
3. 異常與邊界路徑（缺 written、修改原文、缺段、全文不符、空白輸入、連線錯誤、404）均以斷言或預期行為顯式暴露，無靜默遺失
