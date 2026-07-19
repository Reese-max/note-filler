# 8 個 deselected 測試：完整 node ID、collection/selection 規則與未執行原因

> **任務**：列出 8 個被 deselect 的測試完整 node ID，並附上 pytest collection/selection 規則與每個測試未執行的具體原因。
>
> **驗證日**：2026-07-19  
> **Python**：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`  
> **工作目錄**：本 worktree root（禁止跨 repo）

---

## 1. 可重現驗證命令與計數

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
$env:PYTHONIOENCODING = "utf-8"

# (A) 預設選取（含 addopts 的 -m 'not integration'）+ deselected 詳情
& $py -X utf8 -m pytest --collect-only -q --deselected-details --color=no

# (B) 全量收集（只移除 mark 過濾，保留其餘品質閘）
& $py -X utf8 -m pytest --collect-only -q `
  -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" `
  --color=no

# (C) 僅 integration 集合
& $py -X utf8 -m pytest --collect-only -q -m integration `
  -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" `
  --color=no
```

### 2026-07-19 實測結果

| 命令 | collected | selected | deselected |
|---|---:|---:|---:|
| (A) 預設 `addopts`（含 `-m 'not integration'`） | 143 | 135 | **8** |
| (B) 覆寫 `addopts`（無 mark 過濾） | 143 | 143 | 0 |
| (C) `-m integration` | 143 | **8** | 135 |

**集合等式（已驗證）**：

- 預設 deselected 集合 **==** `-m integration` selected 集合 **==** 下表 8 個 node ID  
- 預設 selected + deselected **==** 全量 143

原始輸出（UTF-8）：[`docs/pytest-audit/collect-only-143-2026-07-19.txt`](pytest-audit/collect-only-143-2026-07-19.txt)

---

## 2. Pytest collection / selection 規則總表

| # | 規則來源 | 設定值 / 行為 | 對 deselected 的作用 |
|---|---|---|---|
| R1 | [`pyproject.toml`](../pyproject.toml) `[tool.pytest.ini_options].testpaths` | `["tests"]` | 只收集 `tests/` 下測試；**非**本 8 項排除原因（路徑未再縮篩） |
| R2 | 同上 `pythonpath` | `["src"]` | import 路徑；不參與 deselect |
| R3 | 同上 **`addopts`** | `-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning` | **主因**：`-m 'not integration'` 在 **collection 階段** 將帶 `integration` marker 的 item deselect |
| R4 | 同上 `markers` | `integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過` | 宣告合法 marker；配合 `--strict-markers` |
| R5 | 本次 CLI | `--collect-only -q --deselected-details --color=no`；未傳 `-k`、`--deselect`、測試路徑或額外 `-m` | `--deselected-details` 只開啟報告；本輪沒有第二個選擇條件 |
| R6 | 本次 process environment | `PYTEST_ADDOPTS`、`PYTEST_PLUGINS`、`PYTEST_DISABLE_PLUGIN_AUTOLOAD` 均未設定 | 沒有環境變數注入額外 selector 或 plugin |
| R7 | [`scripts/run_tests.sh`](../scripts/run_tests.sh) `:11,16–17,38,48,58` | 可由 `PYTEST_EXTRA` 附加參數；`unit/all/integ` 分別傳 `-m "not integration"`、`-m ""`、`-m "integration"` | 本輪直接呼叫 Python，且 `PYTEST_EXTRA`、`PYTHON` 均未設定，因此 wrapper 未介入 |
| R8 | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) `:36,63,87` | 日常 job 明傳 `-m "not integration"`；手動 integration job 明傳 `-m "integration"` | CI 與預設規則一致；不是本次本機命令的額外來源 |
| R9 | [`tests/conftest.py`](../tests/conftest.py) `:6–45` | `pytest_addoption` 註冊旗標；`pytest_deselected` 讀取既成結果；`pytest_terminal_summary` 輸出摘要 | 三個 hook 都不修改 collection；本輪 8 項一律回報 `deselected by -m 'not integration'` |
| R10 | 各測試檔 `@pytest.mark.integration` | 見 §3 逐項 | **為何命中 R3**：item 的 `integration=True`，所以 `not integration=False`，pytest core mark selector 將其 deselect |
| R11 | 各測試檔 `skipif` / `pytest.skip` | 見 §3 逐項 | **執行時**條件；預設閘門下不會走到。僅在選入 integration 集合後才可能 skip |

### 規則判定摘要（未執行的直接原因）

| 機制 | 本輪是否作用 | 說明 |
|---|---|---|
| **`-m 'not integration'`（addopts / R3）** | **是 — 唯一 collection 排除機制** | 8 項全部因此 deselect |
| `-k` keyword | 否 | 未使用 |
| `--deselect` | 否 | 未使用 |
| 路徑篩選（例如只跑單一檔） | 否 | 全 `tests/` 收集 |
| `pytest.ini` 另檔 | 無此檔 | 設定全在 `pyproject.toml` |
| `skipif` / `pytest.skip` | 否（預設閘） | 屬 runtime；預設未執行，原因是 deselect 而非 skip |

### 命令列、環境變數與 hooks 的交叉檢查

- `pytest --help` 確認可影響選擇的原生入口為 `-m`、`-k`、`--deselect` 與 `PYTEST_ADDOPTS`；本輪只有設定檔提供的 `-m 'not integration'` 有值。
- process environment 快照：`PYTEST_ADDOPTS=<unset>`、`PYTEST_PLUGINS=<unset>`、`PYTEST_DISABLE_PLUGIN_AUTOLOAD=<unset>`、`PYTEST_EXTRA=<unset>`、`PYTHON=<unset>`。
- runtime 前置快照：`TWINKLE_HUB_TOKEN=<set>`、Grok `127.0.0.1:8318=reachable`、`data/law_index.db=True`；這些值不參與 collection selection。
- `GOV_AI_ENABLE_TWINKLE_MCP` 未設定，且現行 `tests/` 與 `src/` 都不讀取它；`TwinkleClient` 已移除舊 opt-in gate（`src/note_filler/retrieve/twinkle.py:5`）。因此它既不是 deselect 條件，也不是目前 runtime skip 條件。
- repo 內沒有 `pytest_collection_modifyitems`、`pytest_ignore_collect` 或其他會改寫 item 集合的 hook。`--trace-config` 只確認 pytest core mark plugin 與 `tests/conftest.py` 載入；本地 hook 僅觀察及輸出。

`--deselected-details` 終端摘要（逐字）：

```
============================= deselected details ==============================
tests/test_domain.py::test_detect_domain_real_grok_returns_law | reason: deselected by -m 'not integration'
tests/test_e2e_acceptance.py::test_e2e_acceptance_real | reason: deselected by -m 'not integration'
tests/test_gap.py::test_detect_gaps_real_grok | reason: deselected by -m 'not integration'
tests/test_llm.py::test_grok_pong_integration | reason: deselected by -m 'not integration'
tests/test_pipeline.py::test_run_pipeline_real_grok | reason: deselected by -m 'not integration'
tests/test_questions.py::test_generate_questions_real_grok | reason: deselected by -m 'not integration'
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke | reason: deselected by -m 'not integration'
tests/test_twinkle.py::test_search_real_twinkle_hub | reason: deselected by -m 'not integration'
135/143 tests collected (8 deselected) in 0.23s
```

---

## 3. 8 個完整 node ID 與逐項未執行原因

> **Collection 未執行原因**（8/8 相同）：預設 `addopts` 內 `-m 'not integration'`（R3），因該 item 標記 `@pytest.mark.integration`（R10）。
> **Runtime 條件**（若改以 `-m integration` 強制選入後才生效）：列於各列「若被選入後的 skip 條件」。

| # | 完整 node ID | Marker 錨點 | Collection 未執行原因 | 若被選入後的 runtime skip 條件（非本輪 deselect 主因） |
|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `tests/test_domain.py:50` `@pytest.mark.integration` | **`-m 'not integration'`**（addopts R3）；非 `-k`、非路徑、非 `--deselect` | `skipif(not _grok_reachable())`：`grok proxy(127.0.0.1:8318)未上線,條件式略過`（`:51`） |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py:244` `@pytest.mark.integration` | **`-m 'not integration'`**（addopts R3） | 函式內：`缺 data/law_index.db`；或 `grok proxy 未上線或無 TWINKLE_HUB_TOKEN`（`:247–254`） |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `tests/test_gap.py:71` `@pytest.mark.integration` | **`-m 'not integration'`**（addopts R3） | `skipif(not _grok_reachable())`（`:72`） |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `tests/test_llm.py:66` `@pytest.mark.integration` | **`-m 'not integration'`**（addopts R3） | `skipif(not _grok_reachable())`（`:67`） |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `tests/test_pipeline.py:151` `@pytest.mark.integration` | **`-m 'not integration'`**（addopts R3） | `skipif(not _grok_reachable())`（`:152`） |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `tests/test_questions.py:62` `@pytest.mark.integration` | **`-m 'not integration'`**（addopts R3） | `skipif(not _grok_reachable())`（`:63`） |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py:102` `@pytest.mark.integration` | **`-m 'not integration'`**（addopts R3） | `skipif` 缺 `data/law_index.db`（`:103`）；`skipif` grok 未上線（`:104`）；函式內 `需設定 TWINKLE_HUB_TOKEN`（`:107–108`） |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `tests/test_twinkle.py:122` `@pytest.mark.integration` | **`-m 'not integration'`**（addopts R3） | 函式內 `未設定 TWINKLE_HUB_TOKEN,跳過 twinkle-hub 真打整合測試`（`:126–128`） |

### 純 node ID 清單（機器可複製）

```
tests/test_domain.py::test_detect_domain_real_grok_returns_law
tests/test_e2e_acceptance.py::test_e2e_acceptance_real
tests/test_gap.py::test_detect_gaps_real_grok
tests/test_llm.py::test_grok_pong_integration
tests/test_pipeline.py::test_run_pipeline_real_grok
tests/test_questions.py::test_generate_questions_real_grok
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke
tests/test_twinkle.py::test_search_real_twinkle_hub
```

---

## 4. 設定檔對照（證據錨點）

### 4.1 `pyproject.toml`（預設 mark 過濾）

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

### 4.2 與 allowlist 對齊

[`tests/deselected_allowlist.json`](../tests/deselected_allowlist.json) 的 8 個 `test_id` **等於** 本報告 §3 清單（排序後全等）。  
Guard：[`tests/test_deselection_guard.py`](../tests/test_deselection_guard.py) 持續鎖定此集合。

---

## 5. 結論

1. **被 deselect 的測試恰為 8 個**，完整 node ID 見 §3。  
2. **pytest collection/selection 規則**見 §2（R1–R11）；預設閘門排除機制**僅**為 `addopts` 中的 **`-m 'not integration'`**。
3. **未執行的具體原因（預設閘）**：每項皆因標記 `@pytest.mark.integration`，在 mark expression `not integration` 下於 collection 階段 deselected——**不是** `-k`、**不是**路徑篩選、**不是** `--deselect`、**不是** runtime `skip`。  
4. Runtime `skipif`/`pytest.skip` 僅說明「若強制選入 integration 集合後可能仍略過」的依賴（grok:8318、`TWINKLE_HUB_TOKEN`、`data/law_index.db`），**不是**預設 `pytest` 下未執行的主因。  
5. 可追溯原始 collection 輸出已落盤：`docs/pytest-audit/collect-only-143-2026-07-19.txt`。

---

## 6. 產物清單

| 檔案 | 用途 |
|---|---|
| `docs/deselected-8-nodeids-rules-2026-07-19.md` | 本報告（規則 + 8 node ID + 原因） |
| `docs/pytest-audit/collect-only-143-2026-07-19.txt` | 143 項預設 collect + 8 項 `--deselected-details` UTF-8 原始輸出 |
