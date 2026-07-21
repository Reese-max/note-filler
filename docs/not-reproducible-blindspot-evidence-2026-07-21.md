# NOT-REPRODUCIBLE 最小證據包

> **聲明**：本包記錄一項在當前環境下無法重現的產品缺陷路徑，供驗收者直接驗證 `NOT-REPRODUCIBLE` 判定。

---

## 對應 Node ID

**原始 Deselected 測試**：`tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`（#7）

**缺陷主張出處**：`tests/test_exclusion_correctness_blind_spot.py:21-22`

```
判定：若 (2) 穩定 PASS → 產品缺陷路徑 **NOT-REPRODUCIBLE**；
vacuous 設計缺口仍列為「真實驗證缺口」（見 docs/）。
```

---

## 原始命令（PowerShell）

```powershell
# 命令 1：盲區確認測試 — 證明 deselected smoke 斷言對 empty 仍 vacuous PASS
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 `
  -m pytest tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot `
  -v --tb=long --color=no

# 命令 2：產品缺陷路徑重現測試 — 若產品有缺陷（law+LawLookup 回空），此測應失敗
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 `
  -m pytest tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty `
  -v --tb=long --color=no
```

---

## 完整輸出（stdout/stderr）

### 命令 1 輸出

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\7b564656
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item

tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot PASSED [100%]

============================== 1 passed in 0.03s ==============================
```

### 命令 2 輸出

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\7b564656
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item

tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty PASSED [100%]

============================== 1 passed in 0.03s ==============================
```

### Exit Code 與耗時

| 命令 | Exit Code | 耗時 |
|------|-----------|------|
| 命令 1（vacuous 盲區） | 0 | 0.03s |
| 命令 2（產品路徑） | 0 | 0.03s |

---

## 排除原因

### 為何此測試被 deselected

| 層級 | 規則位置 | 規則類型 | 觸發條件 |
|------|----------|----------|----------|
| **L1** | `pyproject.toml:32` | `addopts = -m 'not integration'` | item 帶 `integration=True` marker |
| **L2** | `tests/test_retrieve.py:102` | `@pytest.mark.integration` | 為測試函式標記 |
| **L3** | `tests/test_retrieve.py:103-108` | `skipif` + `pytest.skip` | 缺 law_index.db / grok proxy / TWINKLE_HUB_TOKEN |

### 盲區本質

`test_retrieve_for_gap_real_twinkle_smoke` 的三道 smoke 斷言對 **空清單** 均為 vacuous True：

```python
assert all(isinstance(s, Source) for s in out)   # empty → True
assert all(s.level in ("A", "B") for s in out)   # empty → True
keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
assert keys == sorted(keys)                       # empty == sorted(empty) → True
```

因此「檢索全滅」不會被該 smoke 攔截。但**此盲區屬於斷言設計缺陷，而非產品本身有缺陷**。

---

## 結論

### `NOT-REPRODUCIBLE`

**產品缺陷路徑無法重現**——理由如下：

1. **命令 2 穩定 PASS**（0.03s, exit=0）：`test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty` 在 FakeLLM + _EmptyTwinkle + 真實 LawLookup 組合下，成功回傳 Level A 法條來源。此測試正是專門設計來重現產品缺陷的 failing-first 候選——若產品有 bug（law 領域 + LawLookup 回空），此測應失敗。

2. **產品邏輯健康**：`retrieve_for_gap` 在 `"law"` 領域下成功呼叫 LawLookup 取得法條，Twinkle 雖被隔離為空，但 LawLookup 仍產出有效的 Level A 來源。產品路徑無缺陷。

3. **盲區依然存在**（命令 1 PASS）：vacuous pass 是**測試斷言設計的驗證缺口**，不是產品的執行缺陷。該盲區已在 `test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot` 中文件化鎖定。

| 判定 | 依據 |
|------|------|
| **產品缺陷路徑** | **NOT-REPRODUCIBLE** — 產品邏輯正確，law+LawLookup 回傳 Level A 來源 |
| **驗證盲區** | **CONFIRMED** — vacuous smoke 斷言仍允許 empty 通過（設計缺口，非產品缺陷） |

### 建議

- 產品缺陷路徑不需追蹤（不存在）。
- vacuous 驗證盲區已由 `test_exclusion_correctness_blind_spot.py` 文件化，建議在未來強化 `test_retrieve_for_gap_real_twinkle_smoke` 的斷言以徹底關閉盲區。

---

## 可重現驗證命令

驗收者可直接複製以下命令確認本報告結論：

```powershell
$py = 'D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe'
# 驗證 vacuous 盲區仍存在（預期 PASS）
& $py -X utf8 -m pytest tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot -v --tb=short --color=no

# 驗證產品路徑健康（預期 PASS → NOT-REPRODUCIBLE）
& $py -X utf8 -m pytest tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty -v --tb=short --color=no
```

---

## 證據索引

| 類別 | 路徑 | 用途 |
|------|------|------|
| 原始測試 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | 被排除的 #7 integration smoke |
| 盲區證明 | `tests/test_exclusion_correctness_blind_spot.py:61-70` `test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot` | 證明 vacuous 盲區存在 |
| 產品路徑證明 | `tests/test_exclusion_correctness_blind_spot.py:73-96` `test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty` | 穩定 PASS → 產品無缺陷 |
| 本報告 | `docs/not-reproducible-blindspot-evidence-2026-07-21.md` | NOT-REPRODUCIBLE 最小證據包 |
| 排除規則追溯 | `docs/exclusion-traceability-chain-2026-07-21.md` (#7) | #7 排除規則完整追溯鏈 |
| 風險分級 | `docs/deselected-risk-reclassification-2026-07-21.md` (#7) | Medium 風險、不需補測 |
