# 未篩選完整 pytest 執行結果（2026-07-19）

## 結論

- 完整測試集：`143 passed`；`0 failed`、`0 errors`、`0 skipped`。
- 原本由預設 `-m 'not integration'` 排除的 8 個 integration 測試均實際執行且通過。
- 原始、可機器讀取的逐項結果保存於
  [`full-unfiltered-2026-07-19.xml`](full-unfiltered-2026-07-19.xml)。

## 執行方式

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -q -o addopts= --strict-markers --color=no
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest -o 'addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning' -vv --tb=short --color=no --junitxml=docs/pytest-audit/full-unfiltered-2026-07-19.xml
```

第一個命令收集到 143 項。第二個命令未使用 `-m`、`-k`、檔名或 node ID
篩選；它只移除預設的 integration 排除，並明確保留既有的 strict markers、
DeprecationWarning／PendingDeprecationWarning 視為錯誤，以及停用 asyncio 外掛的品質閘。

pytest JUnit suite 記錄：`tests=143 errors=0 failures=0 skipped=0 time=263.521s`；
終端完成時間為 `263.58s`。

## 8 個 integration 測試結果

| 測試 | 結果 | 秒數 |
| --- | --- | ---: |
| `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | PASSED | 3.557 |
| `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | PASSED | 126.174 |
| `tests/test_gap.py::test_detect_gaps_real_grok` | PASSED | 3.639 |
| `tests/test_llm.py::test_grok_pong_integration` | PASSED | 1.083 |
| `tests/test_pipeline.py::test_run_pipeline_real_grok` | PASSED | 71.091 |
| `tests/test_questions.py::test_generate_questions_real_grok` | PASSED | 8.966 |
| `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | PASSED | 13.213 |
| `tests/test_twinkle.py::test_search_real_twinkle_hub` | PASSED | 3.128 |

## 前置條件、排除與 correctness 影響

本次沒有未執行、跳過或排除的測試，因此沒有需要以替代測試補償的
correctness 缺口。8 項整合測試均通過，表示此次執行時 Grok proxy、法條資料與
Twinkle 所需條件皆足以完成其測試路徑；這是本次執行的證據，不保證未來外部服務可用性。

既有品質閘未被弱化：完整集同時通過原稿不可變、無來源
`pending_evidence`、僅掛實際引用來源，以及法條離線查核的既有測試。
