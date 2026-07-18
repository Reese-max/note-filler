# Deselected 測試盤點（2026-07-19）

> 任務：執行 `pytest --collect-only -q`，比對實際執行清單，列出 8 個 deselected 測試的完整 node ID、所在檔案，以及選取/排除它們的 pytest 參數或設定。
>
> 驗證 Python：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`
>
> 原始 collect 輸出存檔：
> - [`docs/pytest-audit/deselected-collect-2026-07-19.txt`](pytest-audit/deselected-collect-2026-07-19.txt)（預設 addopts）
> - [`docs/pytest-audit/integration-collect-2026-07-19.txt`](pytest-audit/integration-collect-2026-07-19.txt)（`-m integration`）
> - [`docs/pytest-audit/full-collect-no-mark-2026-07-19.txt`](pytest-audit/full-collect-no-mark-2026-07-19.txt)（覆寫 addopts 拿掉 mark 過濾）

## 1. 收集結果摘要

| 命令 | 選取 | deselected | 合計 |
|------|------|------------|------|
| `python -X utf8 -m pytest --collect-only -q`（預設） | **110** | **8** | 118 |
| 同上 + `--deselected-details` | 110 | 8（含完整 node ID） | 118 |
| `python -X utf8 -m pytest --collect-only -q -m integration` | **8** | 110 | 118 |
| 覆寫 addopts（去掉 `-m` 過濾） | **118** | 0 | 118 |

預設摘要行（可重現）：

```text
110/118 tests collected (8 deselected)
```

## 2. 比對：預設執行清單 vs 全量清單 vs deselected

### 2.1 差異定義

- **全量清單**（118）：移除 `addopts` 中的 `-m 'not integration'` 後可收集到的全部測試。
- **預設執行清單**（110）：日常 `pytest` / `pytest --collect-only -q` 實際會選取並執行的集合（仍受 runtime skip 影響，但 collection 已固定 110）。
- **deselected 清單**（8）：全量 − 預設執行 = 8 個帶 `@pytest.mark.integration` 的測試。

### 2.2 集合運算驗證

```text
全量(118) − 預設選取(110) = deselected(8)
預設選取(110) ∩ integration 選取(8) = ∅
預設選取(110) ∪ integration 選取(8) = 全量(118)
```

`pytest --collect-only -q --deselected-details` 印出的 8 個 node ID，與 `pytest --collect-only -q -m integration` 選取的 8 個 **完全一致**（順序亦一致，依檔案路徑排序）。

## 3. 8 個 deselected 測試完整清單

| # | 完整 node ID | 所在檔案 | 排除參數/設定 | 若要選取的參數 |
|---|--------------|----------|---------------|----------------|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | [`tests/test_domain.py`](../tests/test_domain.py) | 預設 `addopts` 內 `-m 'not integration'` | `-m integration` 或覆寫/拿掉 mark 過濾 |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | [`tests/test_e2e_acceptance.py`](../tests/test_e2e_acceptance.py) | 同上 | 同上 |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | [`tests/test_gap.py`](../tests/test_gap.py) | 同上 | 同上 |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | [`tests/test_llm.py`](../tests/test_llm.py) | 同上 | 同上 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | [`tests/test_pipeline.py`](../tests/test_pipeline.py) | 同上 | 同上 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | [`tests/test_questions.py`](../tests/test_questions.py) | 同上 | 同上 |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | [`tests/test_retrieve.py`](../tests/test_retrieve.py) | 同上 | 同上 |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | [`tests/test_twinkle.py`](../tests/test_twinkle.py) | 同上 | 同上 |

### 3.1 `--deselected-details` 原始輸出（可追溯）

```text
============================= deselected details ==============================
tests/test_domain.py::test_detect_domain_real_grok_returns_law | reason: deselected by -m 'not integration'
tests/test_e2e_acceptance.py::test_e2e_acceptance_real | reason: deselected by -m 'not integration'
tests/test_gap.py::test_detect_gaps_real_grok | reason: deselected by -m 'not integration'
tests/test_llm.py::test_grok_pong_integration | reason: deselected by -m 'not integration'
tests/test_pipeline.py::test_run_pipeline_real_grok | reason: deselected by -m 'not integration'
tests/test_questions.py::test_generate_questions_real_grok | reason: deselected by -m 'not integration'
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke | reason: deselected by -m 'not integration'
tests/test_twinkle.py::test_search_real_twinkle_hub | reason: deselected by -m 'not integration'
110/118 tests collected (8 deselected)
```

## 4. 選取 / 排除設定來源

### 4.1 Collection 階段（本次 deselected 的唯一直接原因）

設定檔：[`pyproject.toml`](../pyproject.toml) → `[tool.pytest.ini_options]`

```toml
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

| 項目 | 值 | 作用 |
|------|-----|------|
| **排除（預設）** | `-m 'not integration'`（經 `addopts`） | collection 時 deselect 所有 `@pytest.mark.integration` |
| **選取 integration** | CLI：`-m integration`（覆寫/取代 markexpr） | 只跑 8 個 integration |
| **選取全部** | 覆寫 addopts 去掉 `-m ...`，或明確給不會排除 integration 的 markexpr | 118 全收 |
| **marker 宣告** | `markers = ["integration: ..."]` + `--strict-markers` | 未宣告 marker 會報錯；8 支測試皆標 `@pytest.mark.integration` |

CLI 與設定對照：

| 目的 | 命令 |
|------|------|
| 預設日常（排除 8 支） | `python -X utf8 -m pytest -q` / `pytest --collect-only -q` |
| 只收集/只跑 8 支 integration | `python -X utf8 -m pytest -q -m integration` |
| 列出 deselected 原因 | `python -X utf8 -m pytest --collect-only -q --deselected-details`（hook 見 [`tests/conftest.py`](../tests/conftest.py)） |
| 全量收集（0 deselected） | `python -X utf8 -m pytest --collect-only -q -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning"` |

### 4.2 非 collection 的 runtime 條件（選取後才可能 skip，不計入 deselected）

本次 8 支是 **deselected（collection 過濾）**，不是 session 中的 skipped。若以 `-m integration` 選入後，仍可能因下列條件變成 **skipped**（與 deselected 不同層級）：

| node ID | 額外 runtime 條件（選取後） |
|---------|---------------------------|
| `...::test_detect_domain_real_grok_returns_law` | `@pytest.mark.skipif(not _grok_reachable())` — TCP `127.0.0.1:8318` |
| `...::test_e2e_acceptance_real` | 函式內：`LAW_DB` 存在、`_grok_up()`、`_twinkle_ready()`（`TWINKLE_HUB_TOKEN`） |
| `...::test_detect_gaps_real_grok` | `skipif(not _grok_reachable())` |
| `...::test_grok_pong_integration` | `skipif(not _grok_reachable())` |
| `...::test_run_pipeline_real_grok` | `skipif(not _grok_reachable())` |
| `...::test_generate_questions_real_grok` | `skipif(not _grok_reachable())` |
| `...::test_retrieve_for_gap_real_twinkle_smoke` | `skipif` law db / grok；函式內 `TWINKLE_HUB_TOKEN`、`GOV_AI_ENABLE_TWINKLE_MCP` 等 |
| `...::test_search_real_twinkle_hub` | 函式內 `TWINKLE_HUB_TOKEN` 空則 `pytest.skip` |

## 5. 結論

1. 預設 `pytest --collect-only -q`：**110 選取 / 8 deselected / 118 合計**。
2. 8 個 deselected 的完整 node ID 見 §3；全部位於 `tests/` 下 8 個不同檔案。
3. **唯一 collection 排除機制**：`pyproject.toml` `addopts` 中的 **`-m 'not integration'`**；`--deselected-details` 對 8 支一律回報 `deselected by -m 'not integration'`。
4. **選取方式**：CLI `-m integration` 恰好選出同一組 8 支；去掉 mark 過濾可收集 118 支全量。
5. 與 allowlist [`tests/deselected_allowlist.json`](../tests/deselected_allowlist.json) 的 8 個 `test_id` **一致**，無漂移。

## 6. 重現指令（本機）

```powershell
cd <本 worktree 根目錄>
$py = 'D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe'
& $py -X utf8 -m pytest --collect-only -q
& $py -X utf8 -m pytest --collect-only -q --deselected-details
& $py -X utf8 -m pytest --collect-only -q -m integration
```

預期：

- 預設：`110/118 tests collected (8 deselected)`
- integration：`8/118 tests collected (110 deselected)`，清單即 §3 八支
