# 驗收輸出擴充：禁止僅以彙總數字驗收（2026-07-19）

> **任務**：將驗收輸出擴充為包含完整 pytest invocation、8 個 node ID、各自排除原因、單獨執行結果及失敗測試或 `NOT-REPRODUCIBLE` 證據，避免僅以彙總數字驗收。

## 1. 問題

既有驗收語意常停在：

```text
113 passed, 8 deselected
DESELECTED_AUDIT=8 MAPPED_TESTS=N
TARGETED_VERIFICATION=PASS
```

此類**彙總數字**無法回答：

1. 實際用了哪一條完整 pytest invocation？
2. 被排除的 8 個 node ID 各自為何排除？
3. 每個替代／live 測試的**單獨**結果為何？
4. 若有產品 correctness 主張失敗，證據是失敗重現還是 `NOT-REPRODUCIBLE`？

## 2. 落地變更（主張 ↔ 產物）

| 主張 | 可見產物 |
|------|----------|
| 正式驗收套件 schema | `note-filler.deselected-acceptance/v1` |
| Guard 強制擴充輸出 | [`tests/test_deselection_guard.py`](../tests/test_deselection_guard.py) |
| 禁止 count-only 驗收之結構測試 | `test_acceptance_package_rejects_count_only_summary` |
| 替代測試**逐一** subprocess 實跑 | `test_substitute_mapping_is_complete_and_collectable` 內 `_run_one_test` |
| Audit 腳本寫出 acceptance package | [`scripts/refresh_pytest_audit.py`](../scripts/refresh_pytest_audit.py) |
| 機器可讀套件 | [`docs/pytest-audit/acceptance-package.json`](pytest-audit/acceptance-package.json) |
| 人類可讀套件 | [`docs/pytest-audit/acceptance-package.md`](pytest-audit/acceptance-package.md) |
| 舊 evidence 報告同步擴充 | [`docs/pytest-audit/deselected-evidence.md`](pytest-audit/deselected-evidence.md) |
| live 8 支單獨結果（既有） | [`docs/pytest-audit/deselected-individual-results-2026-07-19.json`](pytest-audit/deselected-individual-results-2026-07-19.json) |

## 3. 驗收套件必備欄位

```text
schema
invocations.{collect_all,collect_default,deselected_details,...}
node_ids[8]
per_node[].{
  node_id,
  exclusion_reason,
  collection_reason,
  substitute_individual_results[] {test_id,status,summary,invocation},
  live_individual_result?,
  failure_or_not_reproducible[]
}
failed_tests_or_not_reproducible[]
acceptance_mode = per-node-evidence
```

`counts` 僅作上下文；**缺少 per_node / invocations / node_ids 即不合格**（見 guard 結構測試）。

## 4. 本輪實測證據

### 4.1 Python 執行器

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8
```

### 4.2 Guard（含 ACCEPTANCE_PACKAGE 區塊）

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_deselection_guard.py -vv --tb=short --color=no -s
```

```text
4 passed in 23.39s
===== ACCEPTANCE_PACKAGE_BEGIN =====
SCHEMA: note-filler.deselected-acceptance/v1
...
NODE_ID_COUNT: 8
[1/8] ... [8/8] ... 各含 exclusion_reason + substitute_individual_results + live_individual_result
FAILED_OR_NOT_REPRODUCIBLE_INDEX: 3 筆 NOT-REPRODUCIBLE
ACCEPTANCE_MODE: per-node-evidence
TARGETED_VERIFICATION=PASS
===== ACCEPTANCE_PACKAGE_END =====
```

### 4.3 刷新 audit／acceptance package

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 scripts/refresh_pytest_audit.py
```

```text
COLLECTED=121 SELECTED=113 DESELECTED=8
ACCEPTANCE_MODE=per-node-evidence
ACCEPTANCE_NODES=8
FAILED_OR_NR=3
PYTEST_AUDIT=PASS
```

### 4.4 非 integration 全集

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  -m "not integration" -q --color=no --tb=line
```

```text
113 passed, 8 deselected in 21.99s
```

> 注意：`113 passed, 8 deselected` **僅上下文**；正式驗收以 §2 套件欄位與 `docs/pytest-audit/acceptance-package.*` 為準。

## 5. 8 個 node ID 摘要

| # | node ID | 排除原因（摘要） | 替代單獨結果 | live 單獨 | 失敗/NR |
|---|---------|------------------|--------------|-----------|---------|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `-m 'not integration'` + grok | 1× PASSED | pass | — |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | mark + law_db/grok/token | 7× PASSED | pass | NOT-REPRODUCIBLE ×2 |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | mark + grok | 1× PASSED | pass | — |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | mark + grok | 1× PASSED | pass | — |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | mark + grok | 4× PASSED | pass | — |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | mark + grok | 2× PASSED | pass | — |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | mark + law/grok/token/MCP | 7× PASSED | pass | NOT-REPRODUCIBLE ×1 |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | mark + token | 3× PASSED | pass | — |

### NOT-REPRODUCIBLE 索引

| node ID | 證據檔 |
|---------|--------|
| `test_e2e_acceptance_real` | `docs/minimal-quality-gates-regression-2026-07-19.md` |
| `test_e2e_acceptance_real` | `docs/e2e-offline-quality-boundary-2026-07-18.md` |
| `test_retrieve_for_gap_real_twinkle_smoke` | `docs/exclusion-correctness-blind-spot-2026-07-19.md` |

## 6. 品質閘未弱化

| 硬約束 | 狀態 |
|--------|------|
| 原稿逐字不可變 | 未改主程式；離線 e2e 回歸仍鎖定 |
| 無來源/【待補證】→`pending_evidence` | 同上 |
| 只掛實際引用來源 | 同上 |
| 法條引用離線查核 | 同上 |
| integration 平時跳過 | 維持 `-m 'not integration'`；8 deselected |

## 7. 重現指令

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
& $py -X utf8 -m pytest tests/test_deselection_guard.py -vv -s --color=no
& $py -X utf8 scripts/refresh_pytest_audit.py
& $py -X utf8 -m pytest -m "not integration" -q --color=no
# 讀套件：
#   docs/pytest-audit/acceptance-package.md
#   docs/pytest-audit/acceptance-package.json
```

## 8. 結論

1. 驗收輸出已擴充為 **per-node-evidence** 套件，不再接受「只有 113/8」式通過。
2. 套件內含完整 invocation、8 個 node ID、各自排除原因、替代與 live 單獨結果、失敗或 `NOT-REPRODUCIBLE` 證據鏈。
3. Guard 4 passed；非 integration 113 passed / 8 deselected；audit `PYTEST_AUDIT=PASS`。
