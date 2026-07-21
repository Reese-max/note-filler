# 最小回歸測試實跑證據（2026-07-21）

> 任務範圍：**只**執行新建立的最小回歸測試與對應 node id 的收集/執行命令，保留完整原始輸出、退出碼與實際執行清單，作為是否存在**實質回歸風險**的直接證據。  
> 本輪**未修改**產品主程式、**未弱化**品質閘、**未**執行 integration 真跑、**未**改 `BACKLOG.md` / `BACKLOG-adng.md`。

## 執行環境

| 項目 | 值 |
|------|-----|
| CWD | `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\0bb09a22` |
| Python | `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8` |
| git HEAD（執行當下） | `f2390f15b369fc58774d627773ca328fd87d1fde` |
| 重跑腳本 | `scripts/_run_minimal_regression_evidence.py` |
| 機器可讀索引 | `docs/pytest-audit/minimal-regression-evidence-2026-07-21.json` |

## 實際執行清單

來源：`docs/pytest-audit/minimal-regression-nodeids-2026-07-21.txt`

### A. 最小回歸核心（6）

1. `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression`
2. `tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary`
3. `tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates`
4. `tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot`
5. `tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`
6. `tests/test_twinkle.py::test_search_clamps_similarity_input_to_distance_range`

選定理由：

- `test_e2e_minimal_quality_gates_offline_regression`：命名上的最小品質閘回歸（四硬閘）。
- offline supplement / control_02：同品質閘離線路徑。
- blind_spot ×2：#7 retrieve vacuous-empty 與 Level A 非空產品路徑。
- `test_search_clamps_similarity_input_to_distance_range`：近期新增 Twinkle similarity 邊界替代（commit `39e7c15`）。

### B. 對應 substitute node id（28 allowlist 唯一項 + 1 clamp = 29）

由 `tests/deselected_allowlist.json` 的 `substitute_tests` 去重，再附加 clamp 新測。完整列表見 nodeids 檔與 collect-all 原始輸出。

## 可重現命令

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
& $py -X utf8 scripts/_run_minimal_regression_evidence.py
```

等價分段命令（與腳本一致）：

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"

# 1) collect-only 最小核心
& $py -X utf8 -m pytest --collect-only -q --color=no `
  tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression `
  tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary `
  tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates `
  tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot `
  tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty `
  tests/test_twinkle.py::test_search_clamps_similarity_input_to_distance_range

# 2) collect-only 29 個對應 node id（allowlist substitutes + clamp）
# 完整 node id 清單見 docs/pytest-audit/minimal-regression-nodeids-2026-07-21.txt

# 3) 執行最小核心 ×2（穩定性）
# 4) 執行 29 個對應 node id ×1
```

## 步驟結果總表（退出碼 + 原始輸出路徑）

| 步驟 | 收集/執行數 | 結果摘要 | EXIT | 完整原始輸出 |
|------|-------------|----------|------|--------------|
| collect-only 最小核心 | 6 collected | 6 tests collected in 0.10s | **0** | [`docs/pytest-audit/minimal-regression-collect-core-2026-07-21.txt`](pytest-audit/minimal-regression-collect-core-2026-07-21.txt) |
| collect-only 對應 node id | 29 collected | 29 tests collected in 0.23s | **0** | [`docs/pytest-audit/minimal-regression-collect-all-nodeids-2026-07-21.txt`](pytest-audit/minimal-regression-collect-all-nodeids-2026-07-21.txt) |
| run 最小核心 #1 | 6 passed | 6 passed in 0.19s | **0** | [`docs/pytest-audit/minimal-regression-run-core-1-2026-07-21.txt`](pytest-audit/minimal-regression-run-core-1-2026-07-21.txt) |
| run 最小核心 #2 | 6 passed | 6 passed in 0.14s | **0** | [`docs/pytest-audit/minimal-regression-run-core-2-2026-07-21.txt`](pytest-audit/minimal-regression-run-core-2-2026-07-21.txt) |
| run 全部對應 node id | 29 passed | 29 passed in 2.34s | **0** | [`docs/pytest-audit/minimal-regression-run-all-nodeids-2026-07-21.txt`](pytest-audit/minimal-regression-run-all-nodeids-2026-07-21.txt) |

`all_exit_zero = true`（見 JSON 索引）。

## 原始輸出節錄（完整內容以檔案為準，此處不截斷關鍵判定行）

### collect 最小核心（EXIT=0）

```text
tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression
tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary
tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates
tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot
tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty
tests/test_twinkle.py::test_search_clamps_similarity_input_to_distance_range

6 tests collected in 0.10s
=== EXIT_CODE: 0 ===
```

### run 最小核心 #1（EXIT=0）

```text
tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression PASSED [ 16%]
tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary PASSED [ 33%]
tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates PASSED [ 50%]
tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot PASSED [ 66%]
tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty PASSED [ 83%]
tests/test_twinkle.py::test_search_clamps_similarity_input_to_distance_range PASSED [100%]

============================== 6 passed in 0.19s ==============================
=== EXIT_CODE: 0 ===
```

### run 最小核心 #2（EXIT=0）

```text
============================== 6 passed in 0.14s ==============================
=== EXIT_CODE: 0 ===
```

### run 29 對應 node id（EXIT=0）

```text
collecting ... collected 29 items
...（29 行皆 PASSED，見完整檔）...
============================= 29 passed in 2.34s ==============================
=== EXIT_CODE: 0 ===
```

29 個 PASSED 的完整 node id 行已寫入  
`docs/pytest-audit/minimal-regression-run-all-nodeids-2026-07-21.txt`（全文未截斷）。

## 主張 ↔ 產物對照

| 主張 | 可檢查產物 |
|------|------------|
| 已鎖定實際執行清單 | `docs/pytest-audit/minimal-regression-nodeids-2026-07-21.txt` |
| collect-only 最小核心完整輸出 + 退出碼 | `...-collect-core-2026-07-21.txt`（EXIT=0） |
| collect-only 對應 node id 完整輸出 + 退出碼 | `...-collect-all-nodeids-2026-07-21.txt`（EXIT=0，29 collected） |
| 最小核心連續兩次通過 | `...-run-core-1-...` / `...-run-core-2-...`（皆 EXIT=0，6 passed） |
| 對應 substitute+clamp 全數通過 | `...-run-all-nodeids-...`（EXIT=0，29 passed） |
| 機器可讀索引 | `docs/pytest-audit/minimal-regression-evidence-2026-07-21.json` |
| 可重現 runner | `scripts/_run_minimal_regression_evidence.py` |
| 執行當下 git HEAD | `f2390f15b369fc58774d627773ca328fd87d1fde`（JSON 內 `git_head_at_run`） |
| 未改產品碼 | 本 commit 僅 docs/pytest-audit + scripts runner + 本報告 |

## 判定：實質回歸風險

| 問題 | 判定 | 依據 |
|------|------|------|
| 最小品質閘離線路徑是否紅燈？ | **否** | 核心 6 測 ×2 皆 PASS |
| allowlist 替代覆蓋（28）+ clamp 是否紅燈？ | **否** | 29 passed / EXIT=0 |
| 本輪是否觀察到實質回歸風險？ | **未觀察到（none_observed）** | `all_exit_zero=true`；JSON `substantive_regression_risk=none_observed_in_minimal_and_substitute_set` |

### 明確邊界（不外推）

- **未**宣稱 8 個 integration 真跑已通過（本輪刻意不跑 integration）。
- **未**宣稱非 integration 全集 140+ 已全跑；僅跑任務指定的最小回歸與對應 node id。
- 真 Grok / 真 Twinkle Hub I/O 風險仍屬 integration 邊界，不在本輪證據覆蓋內。

## 產物清單

1. `docs/minimal-regression-execution-evidence-2026-07-21.md`（本檔）
2. `docs/pytest-audit/minimal-regression-nodeids-2026-07-21.txt`
3. `docs/pytest-audit/minimal-regression-collect-core-2026-07-21.txt`
4. `docs/pytest-audit/minimal-regression-collect-all-nodeids-2026-07-21.txt`
5. `docs/pytest-audit/minimal-regression-run-core-1-2026-07-21.txt`
6. `docs/pytest-audit/minimal-regression-run-core-2-2026-07-21.txt`
7. `docs/pytest-audit/minimal-regression-run-all-nodeids-2026-07-21.txt`
8. `docs/pytest-audit/minimal-regression-evidence-2026-07-21.json`
9. `scripts/_run_minimal_regression_evidence.py`
