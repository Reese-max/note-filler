# Deselected 11：完整測試流程實跑與回歸保護判定

## 產生時間與工作目錄

- 日期：2026-07-23
- 工作目錄：`D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\ce174d2b`
- Python：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`
- 權威 allowlist：`tests/deselected_allowlist.json`（11 項，`decision=acceptable_unexecuted`）
- 機器可讀索引：`docs/pytest-audit/full-flow-2026-07-23/machine-index.json`
- 原始輸出目錄：`docs/pytest-audit/full-flow-2026-07-23/`

## 任務目標

在包含替代 CI 路徑的完整測試流程中實際執行並保存報告，證明 **11 個被主流程排除的測試** 均有：

1. **實跑通過**，或
2. **明確核准的不可執行理由**（allowlist + authorized collection reason）

並據此判定 **回歸保護未受影響**。

## 環境前置（preflight）

來源：`docs/pytest-audit/full-flow-2026-07-23/preflight.txt`

| 檢查項 | 結果 |
|--------|------|
| Grok proxy `http://127.0.0.1:8318/v1` | HTTP 200 |
| `TWINKLE_HUB_TOKEN` | set |
| `data/law_index.db` | present |

因此替代 CI 路徑（`-m integration`）可真跑，而非僅以 skip 帶過。

## 執行路徑對照

| 代碼 | 路徑 | 對應 CI / 用途 | 結果 |
|------|------|----------------|------|
| C1 | `--collect-only -q --deselected-details` | 還原 11 個 deselected node + 原因 | exit 0；`152/163 tests collected (11 deselected)` |
| C2 | `scripts/validate_deselection_ci.py` | allowlist 集合／原因閘 | exit 0；`[gate] PASS` |
| C3 | allowlist 35 個唯一 `substitute_tests` | 預設 CI 等價覆蓋 | exit 0；**35 passed** |
| C4 | `pytest tests/ -m integration` | 替代 CI job `test-integration` | 首次 **10 passed / 1 failed** |
| C4b | 單獨重跑 `test_e2e_acceptance_real` | 釐清 C4 外部瞬斷 | exit 0；**1 passed** |
| C5 | 預設 `pytest -q`（`addopts` 含 `-m 'not integration'`） | 主流程 CI | exit 0；**152 passed, 11 deselected** |
| C6 | guard / ci-gate / requirements coverage | 防回歸機制本身 | exit 0；**11 passed** |

可重現命令（完整字串見 `machine-index.json` → `commands`）。

## 11 個 deselected 節點最終狀態

排除原因一律：`deselected by -m 'not integration'`（authorized）。  
核准決策一律：`acceptable_unexecuted`。

| # | Node ID | 替代測試 | integration 首次 | integration 最終 | 判定 |
|---:|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | 全 PASSED | PASSED | PASSED | 實跑通過 |
| 2 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | 全 PASSED | PASSED | PASSED | 實跑通過 |
| 3 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | 全 PASSED | FAILED（空 choices） | **PASSED_ON_RETRY** | 實跑通過（重跑）+ 核准排除理由 |
| 4 | `tests/test_gap.py::test_detect_gaps_real_grok` | 全 PASSED | PASSED | PASSED | 實跑通過 |
| 5 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | 全 PASSED | PASSED | PASSED | 實跑通過 |
| 6 | `tests/test_llm.py::test_grok_pong_integration` | 全 PASSED | PASSED | PASSED | 實跑通過 |
| 7 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | 全 PASSED | PASSED | PASSED | 實跑通過 |
| 8 | `tests/test_questions.py::test_generate_questions_real_grok` | 全 PASSED | PASSED | PASSED | 實跑通過 |
| 9 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | 全 PASSED | PASSED | PASSED | 實跑通過 |
| 10 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | 全 PASSED | PASSED | PASSED | 實跑通過 |
| 11 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | 全 PASSED | PASSED | PASSED | 實跑通過 |

### #3 首次失敗說明（不弱化品質閘）

- 證據：`C4-integration-runs.txt`
- 錯誤：`IndexError: list index out of range` at `note_filler.llm.GrokClient.complete` → `payload["choices"][0]`
- 性質：**外部 grok proxy 瞬時空 `choices` 回應**，非產品契約被關閉或測試被刪除
- 重跑證據：`C4b-e2e-retry.txt` → `1 passed in 212.36s`
- 同時：該 node 的離線替代測試（結構不變式、品質閘、pipeline C6、只掛引用等）均 PASSED
- allowlist 仍標 `acceptable_unexecuted`，主流程排除理由維持核准

## 證據檔案清單

| 檔案 | 內容 |
|------|------|
| `docs/pytest-audit/full-flow-2026-07-23/preflight.txt` | proxy / token / law DB |
| `docs/pytest-audit/full-flow-2026-07-23/C1-collect-deselected-details.txt` | 11 項 deselected + 原因全文 |
| `docs/pytest-audit/full-flow-2026-07-23/C2-validate-deselection-ci.txt` | gate 終端輸出 |
| `docs/pytest-audit/full-flow-2026-07-23/C2-deselected-ci-gate.md` | gate markdown 報告 |
| `docs/pytest-audit/full-flow-2026-07-23/C3-substitute-runs.txt` | 35 替代測試逐一 PASSED |
| `docs/pytest-audit/full-flow-2026-07-23/substitute-nodeids.txt` | 35 個唯一 nodeid |
| `docs/pytest-audit/full-flow-2026-07-23/C4-integration-runs.txt` | 11 integration 首次結果 |
| `docs/pytest-audit/full-flow-2026-07-23/C4b-e2e-retry.txt` | e2e 重跑 PASSED |
| `docs/pytest-audit/full-flow-2026-07-23/C5-default-suite.txt` | 主流程 152 passed |
| `docs/pytest-audit/full-flow-2026-07-23/C6-guard-tests.txt` | 防回歸 11 passed |
| `docs/pytest-audit/full-flow-2026-07-23/machine-index.json` | 機器可讀總索引 |
| `scripts/_build_full_flow_index.py` | 由原始輸出重建索引的腳本 |

## 回歸保護判定

### 結論：**回歸保護未受影響**（`regression_protection.status = unaffected`）

判定依據（均可在本 commit 差異內逐項對照）：

1. **主流程品質閘綠燈**：C5 `152 passed, 11 deselected`，exit=0。
2. **排除集合穩定且核准**：C1/C2 顯示 11 個 deselected 與 allowlist 完全一致；原因全部為 authorized `deselected by -m 'not integration'`；decision 全部為 `acceptable_unexecuted`。
3. **替代覆蓋完整且實跑通過**：C3 對 allowlist 映射的 35 個唯一非 integration 測試 **35/35 PASSED**。
4. **防回歸機制本身通過**：C6 deselect guard / ci-gate acceptance / requirements coverage **11 passed**。
5. **替代 CI 路徑可執行且 11 節點最終皆有通過證據**：C4 + C4b 覆蓋全部 11 個 integration node（10 首次 + 1 重跑）。
6. **未弱化既有品質閘**：本任務未修改產品契約、未放寬 `pending_evidence`／原稿不可變／來源引用／法條離線查核等硬閘；僅新增實跑證據與報告。

### 明確非宣稱事項

- 不宣稱「integration 首次全跑零失敗」（e2e 首次因外部空 choices 失敗，已如實記錄）。
- 不宣稱「預設 CI 已覆蓋真服務語意品質」——真 Grok／Twinkle 仍屬殘餘風險，由手動 / workflow_dispatch integration job 承擔。
- 不宣稱「外部服務永遠穩定」——e2e 瞬斷即為反證；回歸保護依賴離線替代與 allowlist 閘門，而非單次外部回應。

## 數量總結

| 指標 | 數值 |
|------|-----:|
| 全量 collected | 163 |
| 主流程 selected | 152 |
| 主流程 deselected | 11 |
| allowlist 數 | 11 |
| 唯一替代測試 | 35 |
| 替代測試通過 | 35 |
| integration 最終通過（含重跑） | 11 |
| 需新增補測缺口 | 0 |
| 回歸保護 | unaffected |
