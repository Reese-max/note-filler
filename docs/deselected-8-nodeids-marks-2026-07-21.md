# 預設 pytest 閘門：8 個 deselected 測試盤點

日期：2026-07-21  
工作目錄：目前 note-filler worktree（本 repo）  
Python：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`

## 1. 任務與結論

依任務要求執行：

1. `pytest --collect-only -q`
2. `pytest --collect-only -q -vv`

並完整保存輸出。預設設定下結果為：

| 項目 | 數量 |
|---|---:|
| 收集總數 | 150 |
| 預設閘門選中 | 142 |
| **deselected** | **8** |

**結論：** 8 個 deselected 測試皆帶有 `@pytest.mark.integration`，被 `pyproject.toml` 的 `addopts = ... -m 'not integration' ...` 在 collection 階段排除。此為預期行為（整合測試平時跳過），並非漏測設定錯誤。

補充對照：`pytest --collect-only -q -m integration` 剛好選中同一 8 項（見證據檔）。

## 2. 可重現命令

```text
# 預設閘門（會 deselect integration）
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest --collect-only -q
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest --collect-only -q -vv

# 反證：只收集 integration 標記
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest --collect-only -q -m integration
```

## 3. 完整輸出證據檔

| 檔案 | 內容 | 摘要行 |
|---|---|---|
| [docs/evidence/pytest-collect-only-q.txt](evidence/pytest-collect-only-q.txt) | `pytest --collect-only -q` 完整輸出 | `142/150 tests collected (8 deselected)` |
| [docs/evidence/pytest-collect-only-q-vv.txt](evidence/pytest-collect-only-q-vv.txt) | `pytest --collect-only -q -vv` 完整輸出 | `142/150 tests collected (8 deselected)` |
| [docs/evidence/pytest-collect-only-integration-only.txt](evidence/pytest-collect-only-integration-only.txt) | `-m integration` 完整輸出（反證 8 項） | `8/150 tests collected (142 deselected)` |
| [docs/evidence/deselected-8-with-marks.json](evidence/deselected-8-with-marks.json) | 機器可讀：nodeid / 來源檔 / marks | 8 筆 |

## 4. 排除機制（設定來源）

[`pyproject.toml`](../pyproject.toml) → `[tool.pytest.ini_options]`：

- `addopts` 含：`-m 'not integration'`
- `markers` 定義：`integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過`

因此：**deselect 原因 = 標記 `integration` 不符合預設 mark 表達式 `not integration`**。

（`skipif` 僅在「實際執行 integration 測試」時才可能再 skip；預設閘門階段是 **deselect**，不是 skip。）

## 5. 8 個 deselected 測試一覽

| # | node ID | 來源檔案 | 標記（pytest marks） |
|---:|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `tests/test_domain.py` | `integration`, `skipif`（reason: grok proxy 未上線） |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py` | `integration` |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `tests/test_gap.py` | `integration`, `skipif`（reason: grok proxy 未上線） |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `tests/test_llm.py` | `integration`, `skipif`（reason: grok proxy 未上線） |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `tests/test_pipeline.py` | `integration`, `skipif`（reason: grok proxy 未上線） |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `tests/test_questions.py` | `integration`, `skipif`（reason: grok proxy 未上線） |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py` | `integration`, `skipif`×2（law_index.db / grok proxy） |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `tests/test_twinkle.py` | `integration` |

### 5.1 逐項細節

1. **nodeid:** `tests/test_domain.py::test_detect_domain_real_grok_returns_law`  
   **來源:** `tests/test_domain.py`  
   **標記:** `@pytest.mark.integration`；`@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")`  
   **預設 deselect 原因:** `not integration`

2. **nodeid:** `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`  
   **來源:** `tests/test_e2e_acceptance.py`  
   **標記:** `@pytest.mark.integration`  
   **預設 deselect 原因:** `not integration`

3. **nodeid:** `tests/test_gap.py::test_detect_gaps_real_grok`  
   **來源:** `tests/test_gap.py`  
   **標記:** `@pytest.mark.integration`；`@pytest.mark.skipif(...grok proxy...)`  
   **預設 deselect 原因:** `not integration`

4. **nodeid:** `tests/test_llm.py::test_grok_pong_integration`  
   **來源:** `tests/test_llm.py`  
   **標記:** `@pytest.mark.integration`；`@pytest.mark.skipif(...grok proxy...)`  
   **預設 deselect 原因:** `not integration`

5. **nodeid:** `tests/test_pipeline.py::test_run_pipeline_real_grok`  
   **來源:** `tests/test_pipeline.py`  
   **標記:** `@pytest.mark.integration`；`@pytest.mark.skipif(...grok proxy...)`  
   **預設 deselect 原因:** `not integration`

6. **nodeid:** `tests/test_questions.py::test_generate_questions_real_grok`  
   **來源:** `tests/test_questions.py`  
   **標記:** `@pytest.mark.integration`；`@pytest.mark.skipif(...grok proxy...)`  
   **預設 deselect 原因:** `not integration`

7. **nodeid:** `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`  
   **來源:** `tests/test_retrieve.py`  
   **標記:** `@pytest.mark.integration`；`@pytest.mark.skipif(not LAW_DB.exists(), reason="缺 data/law_index.db")`；`@pytest.mark.skipif(...grok proxy...)`  
   **預設 deselect 原因:** `not integration`

8. **nodeid:** `tests/test_twinkle.py::test_search_real_twinkle_hub`  
   **來源:** `tests/test_twinkle.py`  
   **標記:** `@pytest.mark.integration`  
   **預設 deselect 原因:** `not integration`

## 6. 交叉驗證

- 預設 collect 摘要：`142/150 tests collected (8 deselected)`（見 q / q-vv 證據檔末行）
- 反向 collect：`-m integration` → 恰好 8 個 nodeid，與上表一致（見 `pytest-collect-only-integration-only.txt`）
- 標記來源：各測試檔案內 `@pytest.mark.integration`（及附帶 `skipif`）可直接對照

## 7. 範圍聲明

本任務僅盤點預設閘門下 deselected 的 8 個測試（node ID、來源檔、標記），並保存 collect 完整輸出。  
**未**修改測試篩選、**未**改 `BACKLOG.md`、**未**新增功能任務、**未**執行整合測試本體。
