# pytest --collect-only 完整輸出：11 個 deselected 測試

執行命令：
```
python -X utf8 -m pytest --collect-only -q -p no:asyncio --strict-markers -m "not integration" -W error::DeprecationWarning -W error::PendingDeprecationWarning --deselected-details
```

## 結果摘要

- 總收集：163 測試
- 選擇執行：152 測試
- 被排除（deselected）：**11 測試**
- 排除原因：全部由 `-m 'not integration'` 規則排除
- 規則來源：`pyproject.toml` line 32 `addopts = "-p no:asyncio --strict-markers -m 'not integration' ..."`

## 11 個 deselected node ID 一覽

| # | Node ID | Marker | 來源檔案 | 行號 |
|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | `@pytest.mark.integration` | `tests/test_domain.py` | 62 |
| 2 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `@pytest.mark.integration` | `tests/test_domain.py` | 76 |
| 3 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `@pytest.mark.integration` | `tests/test_e2e_acceptance.py` | 244 |
| 4 | `tests/test_gap.py::test_detect_gaps_real_grok` | `@pytest.mark.integration` | `tests/test_gap.py` | 83 |
| 5 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | `@pytest.mark.integration` | `tests/test_gap.py` | 106 |
| 6 | `tests/test_llm.py::test_grok_pong_integration` | `@pytest.mark.integration` | `tests/test_llm.py` | 95 |
| 7 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `@pytest.mark.integration` | `tests/test_pipeline.py` | 151 |
| 8 | `tests/test_questions.py::test_generate_questions_real_grok` | `@pytest.mark.integration` | `tests/test_questions.py` | 74 |
| 9 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `@pytest.mark.integration` | `tests/test_retrieve.py` | 102 |
| 10 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `@pytest.mark.integration` | `tests/test_twinkle.py` | 166 |
| 11 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | `@pytest.mark.integration` | `tests/test_write.py` | 63 |

## 排除規則來源

- **規則**：`-m 'not integration'`
- **定義位置**：`pyproject.toml` [tool.pytest.ini_options] `addopts`（line 32）
- **Marker 定義**：同檔案 line 34 `markers = ["integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過"]`
- **無 `--deselect` 或 `-k` 過濾**：本次收集僅透過 `-m` marker expression 排除，未使用 `-k` 或 `--deselect` 參數

## 驗證結論

所有 11 個 deselected 測試均符合以下條件：
1. 測試函數或其所屬類別明確標記 `@pytest.mark.integration`
2. `-m 'not integration'` 篩選器正確排除了這些節點
3. 無其他排除機制（ignore、conftest 過濾、自訂 collect 鉤子）參與
4. `--deselected-details` 插件輸出之 `reason` 欄位一致顯示 `deselected by -m 'not integration'`
