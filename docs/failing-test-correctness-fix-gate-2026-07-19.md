# Failing Test → Correctness 盲區修正閘

> 任務：若該 failing test 成功重現 correctness 盲區，立刻修正對應程式或測試選取邏輯，並只重跑該測試與 `pytest -m "not integration" -q`，確認缺口已被關閉。
>
> 候選測試來源：`docs/minimal-quality-gates-regression-2026-07-19.md`  
> 候選測試：`tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression`

## 結論

| 項目 | 結果 |
|------|------|
| 候選 failing test 是否失敗 | **否（PASSED）** |
| 是否成功重現 correctness 盲區 | **否** |
| 修正條件是否觸發 | **未觸發** |
| 主程式／測試選取邏輯變更 | **無**（條件未成立，不得越權修改） |
| 缺口關閉狀態 | **無新增缺口可關**；現況四項品質閘在離線最小前置下成立 |

## 執行證據

### Python 執行器

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8
```

### 1) 候選 failing regression（單測）

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression `
  -vv --tb=short --color=no
```

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\bab31033
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 1 item

tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression PASSED [100%]

============================== 1 passed in 0.03s ==============================
EXIT=0
```

### 2) 非 integration 全集回歸

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  -m "not integration" -q --color=no --tb=line
```

```text
........................................................................ [ 65%]
......................................                                   [100%]
110 passed, 8 deselected in 6.11s
EXIT=0
```

## 判定邏輯（對齊任務條件句）

```text
IF failing_test.fails AND reproduces_correctness_blind_spot:
    fix(program OR test_selection_logic)
    re-run(failing_test)
    re-run(pytest -m "not integration" -q)
    assert gap_closed
ELSE:
    # 本輪路徑
    document(condition_not_triggered)
    do_not_weaken_quality_gates
    do_not_change_unrelated_code
```

本輪：

1. `test_e2e_minimal_quality_gates_offline_regression` **PASSED**（exit=0）
2. 與前輪 `NOT-REPRODUCIBLE` 判定一致（見 `docs/minimal-quality-gates-regression-2026-07-19.md`）
3. 四項硬閘仍被離線回歸鎖定：原稿不可變、無來源→`pending_evidence`、法條離線查核、verified 只掛實際引用 + `_assert_supplement_quality`
4. 非 integration 全集 **110 passed, 8 deselected, 0 failed**

## 品質閘未弱化聲明

| 硬約束 | 本輪狀態 |
|--------|----------|
| 原稿逐字不可變 | 仍由 e2e 離線回歸斷言；未改主程式 |
| 無來源/【待補證】→`pending_evidence` | 同上 |
| 只掛實際引用來源 | 同上 |
| 法條引用須通過離線查核 | 同上 |
| integration 平時跳過 | 維持 `-m "not integration"`；8 deselected 不變 |

## 產物與主張對照

| 主張 | 可見產物 |
|------|----------|
| 已重跑候選 failing test | 上方單測輸出：`1 passed` |
| 已重跑非 integration 全集 | 上方輸出：`110 passed, 8 deselected` |
| 修正條件未觸發 | 本檔結論表 |
| 未改主程式／選取邏輯 | `git status` 僅本報告；無 `src/` 或 pytest 選取 diff |
| 工作樹提交後乾淨 | commit 後 `git status` 應 clean |

## 可重跑命令（完整）

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"

# 候選 failing regression
& $py -X utf8 -m pytest `
  tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression `
  -vv --tb=short --color=no

# 非 integration 回歸
& $py -X utf8 -m pytest -m "not integration" -q --color=no --tb=line
```

## 最終判決

**修正條件未觸發（condition not triggered）。**  
failing-regression 候選無法以失敗形式重現 correctness 盲區；無需修正程式或測試選取邏輯。預設非 integration 回歸全綠，缺口狀態維持「無離線可重現之 correctness 盲區」。
