# 8 個 Deselected 測試 Node ID 清單

**執行命令：** `pytest --collect-only -vv`  
**執行時間：** 2026-07-21  
**證據檔：** `docs/evidence/pytest-collect-only-vv-2026-07-21.txt`  
**統計結果：** collected 154 items / 8 deselected / 146 selected

## 8 個 Deselected 測試詳細資訊

| # | Node ID | 所在檔案 | 測試名稱 | 排除標記 |
|---|---------|----------|----------|----------|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `tests/test_domain.py` | `test_detect_domain_real_grok_returns_law` | `integration` |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py` | `test_e2e_acceptance_real` | `integration` |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `tests/test_gap.py` | `test_detect_gaps_real_grok` | `integration` |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `tests/test_llm.py` | `test_grok_pong_integration` | `integration` |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `tests/test_pipeline.py` | `test_run_pipeline_real_grok` | `integration` |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `tests/test_questions.py` | `test_generate_questions_real_grok` | `integration` |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py` | `test_retrieve_for_gap_real_twinkle_smoke` | `integration` |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `tests/test_twinkle.py` | `test_search_real_twinkle_hub` | `integration` |

## 排除原因摘要

所有 8 個測試均因 `pyproject.toml` 中的預設設定 `-m 'not integration'` 而在 collection 階段被排除。這些測試都標記了 `@pytest.mark.integration`，需要真實的外部服務（grok proxy、Twinkle Hub）才能執行。

## 與 deselected_allowlist.json 對照

本清單與 `tests/deselected_allowlist.json` 中定義的 8 個測試完全一致，確認預設閘門的排除範圍穩定且可追溯。
