# pytest deselected 測試選擇條件盤點

> 驗證日期：2026-07-18  
> 範圍：目前 checkout 的預設 pytest 設定

## 實際收集結果

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -q --deselected-details
```

```text
109/117 tests collected (8 deselected)
```

`pyproject.toml:32` 的 `addopts` 設定了 `-m 'not integration'`。下列八個
節點都帶有 `@pytest.mark.integration`，因此在 collection 階段被排除；本次
命令沒有以 `-k` 或 `--deselect` 排除任何測試。

| # | 完整測試 ID | 所在檔案 | marker 來源 | 被排除的選擇條件 |
|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `tests/test_domain.py` | `tests/test_domain.py:50` 的 `@pytest.mark.integration` | `pyproject.toml:32` 的 `-m 'not integration'` 不選取 `integration` marker |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py` | `tests/test_e2e_acceptance.py:208` 的 `@pytest.mark.integration` | `pyproject.toml:32` 的 `-m 'not integration'` 不選取 `integration` marker |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `tests/test_gap.py` | `tests/test_gap.py:71` 的 `@pytest.mark.integration` | `pyproject.toml:32` 的 `-m 'not integration'` 不選取 `integration` marker |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `tests/test_llm.py` | `tests/test_llm.py:66` 的 `@pytest.mark.integration` | `pyproject.toml:32` 的 `-m 'not integration'` 不選取 `integration` marker |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `tests/test_pipeline.py` | `tests/test_pipeline.py:151` 的 `@pytest.mark.integration` | `pyproject.toml:32` 的 `-m 'not integration'` 不選取 `integration` marker |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `tests/test_questions.py` | `tests/test_questions.py:62` 的 `@pytest.mark.integration` | `pyproject.toml:32` 的 `-m 'not integration'` 不選取 `integration` marker |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py` | `tests/test_retrieve.py:102` 的 `@pytest.mark.integration` | `pyproject.toml:32` 的 `-m 'not integration'` 不選取 `integration` marker |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `tests/test_twinkle.py` | `tests/test_twinkle.py:122` 的 `@pytest.mark.integration` | `pyproject.toml:32` 的 `-m 'not integration'` 不選取 `integration` marker |

## 與 runtime skip 的界線

上述八筆都是由 marker 表達式在收集階段 **deselected**。部分測試另有 Grok proxy、
`data/law_index.db` 或 `TWINKLE_HUB_TOKEN` 的 `skipif`／`pytest.skip()` 前置條件；
那些條件只會在以 `-m integration` 選入後決定是否 **skipped**，不屬於本次預設集合的
deselection 原因。

