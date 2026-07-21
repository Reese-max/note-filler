# CI workflow 與 8 個 deselected 測試覆蓋追溯（2026-07-21）

> 調查基準：`a9e3dd8`；範圍限定目前 repo。
> 判定用語：**選入**表示 pytest collection 包含 node；**實跑**表示測試本體完成且有結果；兩者不可互換。

## 結論

1. Repo 只有一份 CI 定義：`.github/workflows/ci.yml`。沒有 GitLab CI、Azure Pipelines、CircleCI、Jenkins、Travis CI 或 Buildkite 定義。
2. 8 個 node 都會被 `test-integration` job 的 `-m "integration"` **選入**；該 job 只在手動 `workflow_dispatch` 執行，`push main` 與 `pull_request main` 都不執行它（`.github/workflows/ci.yml:3-8,73-99`）。
3. 目前 workflow 沒有啟動 `127.0.0.1:8318` 的 Grok proxy，也沒有把 `TWINKLE_HUB_TOKEN` 注入 job。依 8 個測試的 `skipif`／`pytest.skip()` 條件推論，乾淨的 `ubuntu-latest` runner 雖會選入 8 個 node，測試本體預期為 **8 SKIPPED**。這是配置推論，不是 GitHub Actions 實跑結果。
4. Repo 內沒有 Actions run URL、run ID 或 job log，因此無法證明 `test-integration` 曾在 GitHub Actions 實跑任何一個測試本體。既有 2026-07-18／19 實跑證據是本機執行，不是 CI job 證據。
5. `test-pinned` 與 `test-latest` 不執行這 8 個 node；兩者在 `push main`、`pull_request main`、`workflow_dispatch` 執行 `-m "not integration"`，會執行 allowlist 對應的 28 個唯一離線替代測試。本次逐項 guard 為 **28/28 PASS**。
6. 因此答案是：**有 integration 選入路徑，也有日常替代覆蓋；但目前沒有可追溯證據證明 GitHub Actions 實際執行這 8 個整合測試本體。**

## Pipeline 定義盤點

| 定義 | 類型 | 觸發方式 | 對 8 個 node 的作用 |
|---|---|---|---|
| `.github/workflows/ci.yml` | 唯一 CI workflow | `push main`、`pull_request main`、`workflow_dispatch` | 定義兩個非 integration job 與一個手動 integration job |
| `scripts/run_tests.sh` | 本機手動測試入口，不是 CI job | 人工執行；`unit`／預設、`all`、`integ`、`check` | `integ` 以 `-m "integration"` 選入 8 個；`all` 以空 markexpr 選入全量；預設排除 8 個（`scripts/run_tests.sh:32-69`） |
| `scripts/dep_upgrade_check.py` | 本機相依套件升級檢查，不是 CI job | 人工執行 | 只跑 `-m "not integration"`，不執行 8 個本體（`scripts/dep_upgrade_check.py:98-107`） |
| `scripts/validate_deselection_ci.py` | 三個 CI job 共用的 collection policy gate | 由 workflow step 呼叫 | 只做 `--collect-only` 與 allowlist 核對，不是 8 個本體的覆蓋證據（`scripts/validate_deselection_ci.py:28-55,168-175`） |
| `scripts/refresh_pytest_audit.py`、`scripts/_run_minimal_regression_evidence.py`、`scripts/refresh_design_acceptance.py` | 本機證據產生工具，不是 pipeline job | 人工執行 | 收集 integration node 或執行非 integration／最小回歸；沒有 CI 觸發 |

`src/note_filler/pipeline.py` 是產品執行流程，不是 CI pipeline 定義，故不列為 workflow。

## CI job 與觸發條件

| Job ID／顯示名稱 | Python matrix | 觸發條件 | pytest 選擇結果 |
|---|---:|---|---|
| `test-pinned`／`test (pinned …)` | 3.11、3.12 | workflow 的三種事件都執行；job 無額外 `if` | `-m "not integration"`：142 selected／8 deselected（`.github/workflows/ci.yml:11-40`） |
| `test-latest`／`test (latest …)` | 3.11、3.12、3.13 | workflow 的三種事件都執行；job 無額外 `if` | `-m "not integration"`：142 selected／8 deselected（`.github/workflows/ci.yml:42-71`） |
| `test-integration`／`integration (3.12)` | 3.12 | 僅 `github.event_name == 'workflow_dispatch'` | `-m "integration"`：8 selected／142 deselected（`.github/workflows/ci.yml:73-99`） |

## Node ID → job → 觸發條件 → 實際覆蓋證據

每列的「替代 job」都是 `test-pinned` 與 `test-latest`；兩者會跑對應的非 integration 測試，但不會跑原 node。`docs/pytest-audit/acceptance-package.json` 保存替代 node、逐項 invocation、結果及歷史本體結果；本次重新執行同一個 guard，28 個唯一替代 node 全部通過。

| # | 完整 node ID | 原 node job／觸發條件 | 實際覆蓋證據與判定 |
|---:|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `test-integration`；僅手動 `workflow_dispatch` | 本次 integration collection 有選入；Grok 不可達即 skip（`tests/test_domain.py:50-51`），故現行 CI 預期不實跑。本機本體曾 PASS（`docs/pytest-audit/deselected-individual-results-2026-07-19.json:4-7`）。替代 job 對應 2 項，本次 2/2 PASS；逐項證據在 `docs/pytest-audit/acceptance-package.json:30-50`。外部缺口仍是真 Grok 法律分類品質。 |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `test-integration`；僅手動 `workflow_dispatch` | 本次 integration collection 有選入；缺 Grok 或 `TWINKLE_HUB_TOKEN` 即 skip（`tests/test_e2e_acceptance.py:244-255`），故現行 CI 預期不實跑。本機本體曾 PASS（`docs/pytest-audit/deselected-individual-results-2026-07-19.json:13-16`）。替代 job 對應 8 項，本次 8/8 PASS；逐項證據在 `docs/pytest-audit/acceptance-package.json:55-122`。外部缺口仍是真模型加真檢索的端到端品質。 |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `test-integration`；僅手動 `workflow_dispatch` | 本次 integration collection 有選入；Grok 不可達即 skip（`tests/test_gap.py:71-72`），故現行 CI 預期不實跑。本機本體曾 PASS（`docs/pytest-audit/deselected-individual-results-2026-07-19.json:22-25`）。替代 job 對應 2 項，本次 2/2 PASS；逐項證據在 `docs/pytest-audit/acceptance-package.json:127-147`。外部缺口仍是真 Grok 缺口判斷品質。 |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `test-integration`；僅手動 `workflow_dispatch` | 本次 integration collection 有選入；Grok 不可達即 skip（`tests/test_llm.py:66-67`），故現行 CI 預期不實跑。本機本體曾 PASS（`docs/pytest-audit/deselected-individual-results-2026-07-19.json:31-34`）。替代 job 對應 2 項，本次 2/2 PASS；逐項證據在 `docs/pytest-audit/acceptance-package.json:152-172`。外部缺口仍是真 proxy TCP／回應相容性。 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `test-integration`；僅手動 `workflow_dispatch` | 本次 integration collection 有選入；Grok 不可達即 skip（`tests/test_pipeline.py:151-152`），故現行 CI 預期不實跑。本機本體 2026-07-19 曾 PASS（`docs/pytest-audit/deselected-individual-results-2026-07-19.json:40-43`），但 2026-07-21 另一次因 proxy `401 Unauthorized` FAIL（`docs/deselected-8-individual-execution-2026-07-21.md:20-27`），證明外部條件不穩定。替代 job 對應 5 項，本次 5/5 PASS；逐項證據在 `docs/pytest-audit/acceptance-package.json:177-215`。 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `test-integration`；僅手動 `workflow_dispatch` | 本次 integration collection 有選入；Grok 不可達即 skip（`tests/test_questions.py:62-63`），故現行 CI 預期不實跑。本機本體曾 PASS（`docs/pytest-audit/deselected-individual-results-2026-07-19.json:49-52`）。替代 job 對應 3 項，本次 3/3 PASS；逐項證據在 `docs/pytest-audit/acceptance-package.json:220-246`。外部缺口仍是真 Grok 出題品質。 |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `test-integration`；僅手動 `workflow_dispatch` | 本次 integration collection 有選入；缺法規 DB、Grok 或 token 即 skip（`tests/test_retrieve.py:102-108`），故現行 CI 預期不實跑。本機本體曾 PASS（`docs/pytest-audit/deselected-individual-results-2026-07-19.json:58-61`）。替代 job 對應 9 項，本次 9/9 PASS，含非空 Level A guard；逐項證據在 `docs/pytest-audit/acceptance-package.json:251-313`。外部缺口仍是真 Twinkle I/O 與真 Grok 關鍵字品質。 |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `test-integration`；僅手動 `workflow_dispatch` | 本次 integration collection 有選入；缺 `TWINKLE_HUB_TOKEN` 即函式內 skip（`tests/test_twinkle.py:141-147`），故現行 CI 預期不實跑。本機本體曾 PASS（`docs/pytest-audit/deselected-individual-results-2026-07-19.json:67-70`）。替代 job 對應 4 項，本次 4/4 PASS；逐項證據在 `docs/pytest-audit/acceptance-package.json:318-352`。外部缺口仍是真 Hub 可用性與服務端 session 相容性。 |

另有一份符合本任務指定 venv 的歷史整合補跑：`docs/integration-test-rerun-results-2026-07-18.md:5-6,64-73` 記錄 8/8 PASSED。它證明這 8 個本體在前置條件齊備時可執行，但仍是本機證據，不能冒充 `test-integration` job log。

## 本次可重現驗證

### 1. Pipeline 定義與 CI 外部前置

```powershell
git ls-files '.github/workflows/*' '.gitlab-ci.yml' 'azure-pipelines*.yml' '.circleci/*' 'Jenkinsfile' '.travis.yml' 'buildkite*'
```

```text
.github/workflows/ci.yml
```

```powershell
rg -n 'env:|secrets\.|services:|8318|TWINKLE_HUB_TOKEN|GROK' .github/workflows
```

```text
NO_MATCH: workflow 未宣告外部整合服務或憑證環境變數
```

### 2. 以 CI markexpr 收集 integration

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/ -m 'integration' --collect-only -q --color=no
```

```text
tests/test_domain.py::test_detect_domain_real_grok_returns_law
tests/test_e2e_acceptance.py::test_e2e_acceptance_real
tests/test_gap.py::test_detect_gaps_real_grok
tests/test_llm.py::test_grok_pong_integration
tests/test_pipeline.py::test_run_pipeline_real_grok
tests/test_questions.py::test_generate_questions_real_grok
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke
tests/test_twinkle.py::test_search_real_twinkle_hub

8/150 tests collected (142 deselected) in 3.12s
```

### 3. Selection／allowlist 前置 guard

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_deselection_guard.py::test_integration_allowlist_is_stable tests/test_deselection_guard.py::test_deselected_details_lists_node_ids_and_reasons tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_accepts_only_authorized_deselected_nodes_with_reasons -q --color=no
```

```text
3 passed in 10.30s
```

### 4. 28 個替代測試逐項實跑 guard

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable -q -s --color=no
```

```text
NODE_ID_COUNT: 8
ACCEPTANCE_MODE: per-node-evidence
TARGETED_VERIFICATION=PASS
LEGACY_COUNTERS_CONTEXT_ONLY: DESELECTED_AUDIT=8 MAPPED_TESTS=28 ...
1 passed in 16.07s
```

完整的 8 組對應、28 個替代 node、各自 invocation 與狀態位於 `docs/pytest-audit/acceptance-package.json:24-352`；本次 guard 是針對這份 allowlist／映射重新逐項執行，不以彙總數字取代逐項驗證。

### 5. CI job 實跑證據搜尋

```powershell
rg -n -i 'actions/runs|github actions run|workflow run id|gh run' docs .github
```

```text
NO_MATCH: repo 內無 GitHub Actions run URL／run ID／job log 證據
```

## 最終判定

| 問題 | 判定 |
|---|---|
| 8 個 node 是否有 integration job？ | **有**；`test-integration`。 |
| 何時觸發？ | **只在手動 `workflow_dispatch`**；push／PR 不跑。 |
| job 是否會選入全部 8 個？ | **會**；本次 collection 為 8/8。 |
| 現行 GitHub-hosted job 是否可證明實跑 8 個本體？ | **否**；無 run artifact，且 workflow 未供應 Grok／Twinkle 前置，靜態判定預期 8 SKIPPED。 |
| 其他 CI job 是否執行原 8 個 node？ | **否**；`test-pinned`／`test-latest` 明確 deselect。 |
| 其他 CI job 是否有替代覆蓋？ | **有**；28 個唯一離線替代 node 會被兩個日常 job 選入，本次逐項 28/28 PASS。 |
| 外部整合缺口是否被替代測試消除？ | **否**；真 Grok／Twinkle 的可用性與語意品質仍只能由具備前置條件的整合實跑證明。 |

本次只新增稽核報告，未修改 workflow、pytest marker、allowlist、測試或產品程式碼，也未弱化任何既有品質閘。
