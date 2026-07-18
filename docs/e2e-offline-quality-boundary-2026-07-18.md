# e2e 離線品質邊界：最小 failing regression 嘗試結果

> 對應任務：以 `docs/deselected-minimal-repro-2026-07-18.md` 之邊界條件，新增最小 failing regression test；**不修正主程式**；確認能否穩定失敗；否則標 `NOT-REPRODUCIBLE`。

## 邊界條件（鎖定）

| 項目 | 內容 |
|------|------|
| 來源 deselected | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` |
| 覆蓋缺口 | `_assert_supplement_quality`（Level A 路由、非原始記錄倒出、`[^n]` 註腳） |
| 最小離線前置 | `FakeLLM` + `_StubTwinkle` + `data/law_index.db`（`LawLookup`） |
| 新增測試 | `tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary` |

## 判定：**NOT-REPRODUCIBLE**

在**不修改主程式**的前提下，以上最小離線路徑執行 `_assert_supplement_quality(doc)` **兩次皆 PASS**（exit=0），無法形成穩定失敗。

### 實測觀察

- offline pipeline 會經 `retrieve_for_gap` 啟用 law 領域 Level A（離線 `LawLookup` 查條），supplement `sources` 含 `level=="A"`。
- FakeLLM writer 回文含 `[^1][^2]`，且非「議案編號」+「hybrid_score」原始記錄倒出。
- 故品質斷言 (a)(b)(c) 在確定性 stub 下皆成立；**失敗無法離線重現**。

仍無法離線重現的部分（維持 integration 專屬）：

- 真 Grok 模型輸出品質 / 隨機性
- 真 Twinkle Hub I/O
- 真跑有界重跑（最多 6 次）下的 Level A 路由穩定性

## 可重跑命令

```powershell
# 1) 單測（兩次確認穩定性）
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary `
  -vv --tb=short

& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary `
  -vv --tb=short

# 2) allowlist 計數與替代映射守衛
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_deselection_guard.py -q --tb=short

# 3) 預設非 integration 全集
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  -m "not integration" -q
```

### 2026-07-18 實跑節錄

```text
# 單測連續兩次
tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary PASSED
EXIT1=0
tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary PASSED
EXIT2=0

# allowlist 守衛
2 passed in 3.13s

# 非 integration 全集
105 passed, 8 deselected in 5.97s
```

## 產物清單（與主張對齊）

| 檔案 | 角色 |
|------|------|
| `tests/test_e2e_acceptance.py` | 新增 `test_e2e_offline_supplement_quality_boundary` + `_offline_structural_doc` |
| `tests/test_deselection_guard.py` | `_EXPECTED_COUNTS`→`(113, 105, 8)`；subprocess 加 `--color=no` 避免 ANSI 導致 PASSED 解析落空 |
| `tests/deselected_allowlist.json` | e2e 項 substitute 納入新邊界測試 |
| 本檔 | NOT-REPRODUCIBLE 判定與可重跑命令 |

## 結論

- **失敗可否離線穩定重現：**否 → **`NOT-REPRODUCIBLE`**
- **仍提交的價值：**把 `_assert_supplement_quality` 從「僅 integration」鎖進預設回歸；若 Level A 離線路斷線，此測會紅。
- **主程式：**依任務要求，未修改。
