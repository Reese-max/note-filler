# Failing Test → Correctness 問題修正閘

> 任務：若有任一測試能在非 integration 情境下重現 correctness 問題，直接修正對應程式邏輯，並只重跑該回歸測試與 `pytest -m "not integration" -q` 驗證修補後未再出現排除缺口。
>
> 工作樹：`63adf14f`  
> 日期：2026-07-19  
> 硬約束：原稿逐字不可變、無來源/【待補證】→`pending_evidence`、只掛實際引用來源、法條引用須通過離線查核；integration 平時跳過。

## 結論

| 項目 | 結果 |
|------|------|
| 非 integration 情境是否有失敗測試 | **否**（0 failed） |
| 是否成功以失敗形式重現產品 correctness 問題 | **否** |
| 修正條件是否觸發 | **未觸發** |
| 主程式（`src/`）變更 | **無** |
| 測試選取邏輯／品質閘變更 | **無** |
| 排除缺口狀態 | **無新增產品缺口可關**；8 個 deselected 仍由 allowlist + failing-first 對照鎖定 |

## 判定邏輯（對齊任務條件句）

```text
IF any_test.fails_under(not integration) AND reproduces_product_correctness_issue:
    fix(program_logic)
    re-run(that_regression_test)
    re-run(pytest -m "not integration" -q)
    assert exclusion_gap_closed
ELSE:
    document(condition_not_triggered)
    do_not_weaken_quality_gates
    do_not_change_unrelated_code
```

本輪：

1. `pytest -m "not integration" -q` → **137 passed, 8 deselected, 0 failed**
2. 所有 correctness 候選回歸（blind-spot / failing-controls / 最小品質閘）→ **13 passed**
3. 產品 law Level A 路徑（`test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`、`test_control_07b_*`）穩定 **PASS** → 無法主張「產品已回空／correctness 已壞」
4. vacuous empty smoke 屬**驗證層**設計事實（`all([])` 仍 True），由既有對照測鎖定，**不是**本輪可重現的產品程式邏輯失敗，故**不得**越權改主程式或弱化閘門

## 候選回歸清單（非 integration）

| 測試 | 角色 | 本輪 |
|------|------|------|
| `tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot` | 驗證層：empty 滿足 #7 smoke 三斷言 | PASSED |
| `tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty` | 產品：law+LawLookup 不得 vacuous empty | PASSED |
| `tests/test_excluded_failing_controls.py`（10 tests，含 8 排除對照 + map 閘 + 07b） | 8 個 deselected 的 failing-first 對照 | 全部 PASSED |
| `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression` | 四硬閘離線最小回歸 | PASSED |

## 執行證據

### Python 執行器

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8
```

### 1) Correctness 候選回歸（13 items）

命令：

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_exclusion_correctness_blind_spot.py `
  tests/test_excluded_failing_controls.py `
  tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression `
  -vv --tb=short --color=no
```

完整輸出落盤：

- [`docs/pytest-audit/correctness-fix-candidates-2026-07-19.txt`](pytest-audit/correctness-fix-candidates-2026-07-19.txt)

摘要：

```text
collected 13 items
... 全部 PASSED ...
============================= 13 passed in 0.21s ==============================
```

### 2) 非 integration 全集

命令：

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  -m "not integration" -q --color=no --tb=line
```

完整輸出落盤：

- [`docs/pytest-audit/correctness-fix-non-integration-2026-07-19.txt`](pytest-audit/correctness-fix-non-integration-2026-07-19.txt)

摘要：

```text
........................................................................ [ 52%]
.................................................................        [100%]
137 passed, 8 deselected in 47.88s
```

## 與既有證據鏈對齊

| 既有文件 | 本輪對照 |
|----------|----------|
| `docs/exclusion-correctness-blind-spot-2026-07-19.md` | 產品缺陷路徑仍 **NOT-REPRODUCIBLE**；驗證層 vacuous smoke 仍由對照鎖定 |
| `docs/excluded-failing-controls-2026-07-19.md` | 8 項 control 本輪再跑全 PASS |
| `docs/failing-test-correctness-fix-gate-2026-07-19.md`（本檔） | 以 **當前工作樹** 重跑並更新計數為 137/8 |

## 品質閘未弱化聲明

| 硬約束 | 本輪狀態 |
|--------|----------|
| 原稿逐字不可變 | 仍由 e2e 離線回歸斷言；未改主程式 |
| 無來源/【待補證】→`pending_evidence` | 同上 + pipeline C6 control |
| 只掛實際引用來源 | 同上 |
| 法條引用須通過離線查核 | 同上 |
| integration 平時跳過 | 維持 `-m "not integration"`；**8 deselected** 不變 |

## 產物與主張對照

| 主張 | 可見產物 |
|------|----------|
| 已重跑 correctness 候選回歸 | `docs/pytest-audit/correctness-fix-candidates-2026-07-19.txt`（13 passed） |
| 已重跑非 integration 全集 | `docs/pytest-audit/correctness-fix-non-integration-2026-07-19.txt`（137 passed, 8 deselected） |
| 修正條件未觸發 | 本檔結論表 |
| 未改 `src/`／pytest 選取 | commit diff 僅 docs／audit 證據 |
| 未動 `BACKLOG.md` | 提交檔案清單可查 |
| 未弱化品質閘 | 上方硬約束表 |

## 可重跑命令

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"

# 候選 correctness 回歸
& $py -X utf8 -m pytest `
  tests/test_exclusion_correctness_blind_spot.py `
  tests/test_excluded_failing_controls.py `
  tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression `
  -vv --tb=short --color=no

# 非 integration 回歸
& $py -X utf8 -m pytest -m "not integration" -q --color=no --tb=line
```

## 最終判決

**修正條件未觸發（condition not triggered）。**

- 非 integration 情境**無法**以失敗測試重現產品 correctness 問題。
- 依任務條件句：**不得**擅自修改程式邏輯；僅落盤可重現證據與判定。
- 預設閘門現況：**137 passed, 8 deselected, 0 failed**。
