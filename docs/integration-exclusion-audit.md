# Integration Marker 排除一致性審計

**日期**：2026-07-17（修訂）

## 問題描述

`pyproject.toml` 定義了 `integration` marker 且 `addopts` 已含 `-m 'not integration'`，但 5 個整合測試**缺少 `@pytest.mark.integration` 裝飾器**，導致它們在預設 `pytest -m "not integration"` 時仍被收集。當 grok proxy 不在線時這些測試會被 `skipif` 跳過，但在 proxy 在線時會被執行，產生不穩定的測試集合。

## 受影響的 8 個整合測試

| # | 檔案 | 測試函式 | 修正前 marker |
|---|---|---|---|
| 1 | `test_domain.py:51` | `test_detect_domain_real_grok_returns_law` | ❌ 缺少（僅有 skipif） |
| 2 | `test_e2e_acceptance.py:177` | `test_e2e_acceptance_real` | ✅ 已有 |
| 3 | `test_gap.py:72` | `test_detect_gaps_real_grok` | ❌ 缺少（僅有 skipif） |
| 4 | `test_llm.py:67` | `test_grok_pong_integration` | ❌ 缺少（僅有 skipif） |
| 5 | `test_pipeline.py:118` | `test_run_pipeline_real_grok` | ✅ 已有 |
| 6 | `test_questions.py:63` | `test_generate_questions_real_grok` | ❌ 缺少（僅有 skipif） |
| 7 | `test_retrieve.py:90` | `test_retrieve_for_gap_real_twinkle_smoke` | ✅ 已有 |
| 8 | `test_twinkle.py:93` | `test_search_real_twinkle_hub` | ❌ 缺少（無任何 marker） |

## 修正內容

在 5 個缺少 marker 的測試函式上方加上 `@pytest.mark.integration`：

| 檔案 | 變更 |
|---|---|
| `tests/test_domain.py:50` | 新增 `@pytest.mark.integration` |
| `tests/test_gap.py:71` | 新增 `@pytest.mark.integration` |
| `tests/test_llm.py:66` | 新增 `@pytest.mark.integration` |
| `tests/test_questions.py:62` | 新增 `@pytest.mark.integration` |
| `tests/test_twinkle.py:93` | 新增 `@pytest.mark.integration` |

保留原有的 `@pytest.mark.skipif` 作為雙重防護：即使誤執行 `pytest -m integration` 但 grok 不在線時仍安全跳過。

## 驗證結果

```
$ pytest --co -q
102/110 tests collected (8 deselected) in 0.51s

$ pytest -m integration --co -q
8/110 tests collected (102 deselected) in 0.45s

$ pytest -m "not integration" -q
102 passed, 8 deselected in 3.38s
```

**結論**：全部 8 個整合測試現在均有 `@pytest.mark.integration`，預設跑 `pytest -m "not integration"` 一致收集 102 個非整合測試、排除 8 個整合測試。
