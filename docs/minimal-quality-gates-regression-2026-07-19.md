# 最小品質閘 failing regression 驗證

> 任務：依 `docs/deselected-minimal-repro-2026-07-18.md` 最小條件，新增最小化 failing regression test；直接執行驗證；若無法穩定重現失敗 → 標記 **`NOT-REPRODUCIBLE`**，並保留可重跑命令與輸出證據。
>
> 硬約束（不得弱化）：原稿逐字不可變、無來源/【待補證】→`pending_evidence`、只掛實際引用來源、法條引用須通過離線查核。

## 鎖定邊界

| 項目 | 內容 |
|------|------|
| 來源 deselected | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` |
| 最小離線前置 | `FakeLLM` + `_StubTwinkle` + `data/law_index.db`（`LawLookup`） |
| 最小真跑前置 | `TWINKLE_HUB_TOKEN` + Grok proxy `127.0.0.1:8318` + `data/law_index.db` |
| 新增測試 | `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression` |
| 鎖定閘門 | (1) 原稿不可變 (2) 無來源→pending_evidence (3) 法條離線查核 (4) 只掛實際引用（verified + `[^n]`）+ `_assert_supplement_quality` |

## 判定：**NOT-REPRODUCIBLE**

在**不修改主程式**的前提下：

1. **離線最小路徑**連續兩次執行新回歸 → **皆 PASS**（exit=0）
2. **真跑 integration**（最小真跑前置皆就緒）→ **PASS**（exit=0，約 122s）
3. 預設非 integration 全集 → **110 passed, 8 deselected**

**無法以失敗形式穩定重現**既有品質閘缺口；四項硬閘在現況環境下皆成立。

### 實測觀察

- 離線 pipeline 經 `retrieve_for_gap` 啟用 law 領域 Level A；verified 補充含 `[^1][^2]` 且 sources 非空。
- 法條 `check_law_citations` 無 `article_not_found`。
- 真 Grok + 真 Twinkle + 真 LawLookup 的 e2e 亦通過 5 個 §12 不變式 + `_assert_supplement_quality`。

仍屬 integration 專屬、離線無法「失敗重現」的部分：

- 真模型輸出品質／隨機性（gap 偵測、寫作 `[^n]` 穩定性）
- 真 Twinkle Hub I/O 服務語意
- 有界重跑（最多 6 次）下 Level A 路由在真環境的 flaky 邊界

## 可重跑命令

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"

# 1) 最小品質閘回歸（兩次確認穩定性）
& $py -X utf8 -m pytest `
  tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression `
  -vv --tb=short --color=no

& $py -X utf8 -m pytest `
  tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression `
  -vv --tb=short --color=no

# 2) allowlist / 計數守衛
& $py -X utf8 -m pytest tests/test_deselection_guard.py -q --tb=short --color=no

# 3) 預設非 integration 全集
& $py -X utf8 -m pytest -m "not integration" -q --color=no

# 4)（可選）真跑 e2e；需 TWINKLE_HUB_TOKEN + 127.0.0.1:8318
& $py -X utf8 -m pytest `
  tests/test_e2e_acceptance.py::test_e2e_acceptance_real `
  -m integration -vv --tb=short --color=no
```

### 2026-07-19 實跑節錄

```text
# 離線最小品質閘回歸 ×2
tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression PASSED
EXIT1=0
tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression PASSED
EXIT2=0

# allowlist 守衛
3 passed in 4.78s
EXITG=0

# 非 integration 全集
110 passed, 8 deselected in 5.51s
EXITN=0

# 真跑 e2e（前置：TOKEN=True, GROK=True）
tests/test_e2e_acceptance.py::test_e2e_acceptance_real PASSED
======================== 1 passed in 122.16s (0:02:02) ========================
EXIT=0

# collect 基線
118 tests collected
110/118 tests collected (8 deselected)
```

## 產物清單（與主張對齊）

| 檔案 | 角色 |
|------|------|
| `tests/test_e2e_acceptance.py` | 新增 `test_e2e_minimal_quality_gates_offline_regression` |
| `tests/test_deselection_guard.py` | `_EXPECTED_COUNTS` → `(118, 110, 8)` |
| `tests/deselected_allowlist.json` | e2e 替代映射納入新回歸；exclusion 行號同步 |
| 本檔 | **NOT-REPRODUCIBLE** 判定與可重跑命令／輸出證據 |

## 結論

| 主張 | 證據 |
|------|------|
| 已新增最小化 failing regression 候選 | `test_e2e_minimal_quality_gates_offline_regression` |
| 直接執行驗證 | 離線×2 + guard + 110 passed + 真 e2e |
| 無法穩定重現失敗 | **`NOT-REPRODUCIBLE`** |
| 未弱化四項品質閘 | 新測同時斷言四閘；全集通過 |
| 主程式 | **未修改**（依任務：只加回歸／證據） |
