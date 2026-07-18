# 8 個被排除測試：原因追查、分類與可重現命令

> **日期**：2026-07-19  
> **任務**：逐一追查 8 個測試被排除的原因；檢查 CLI `-k/-m/--ignore`、`pytest.ini`/`pyproject.toml`/`setup.cfg`、conftest hooks 與環境條件；分類為**刻意不執行**／**條件性跳過**／**測試收斂**；附可重現命令。  
> **工作目錄**：本 worktree（僅本 repo）  
> **Python**：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`  
> **實測證據**：[`docs/pytest-audit/excluded-cause-*-2026-07-19.txt`](pytest-audit/)

---

## 0. 結論摘要

| 項目 | 結果 |
|------|------|
| 預設收集 | **110 selected / 8 deselected / 118 total** |
| 排除機制（唯一 collection 原因） | `pyproject.toml` `addopts` 內 **`-m 'not integration'`** |
| `-k` 是否參與預設排除 | **否**（預設無 keyword 表達式） |
| `--ignore` 是否參與 | **否**（設定與預設 CLI 均無） |
| `--deselect` 是否參與 | **否** |
| `pytest.ini` / `setup.cfg` / `tox.ini` | **皆不存在** |
| conftest 是否主動 deselect | **否**（僅在 `--deselected-details` 時**報告**原因） |
| 8 個 node ID 與 `-m integration` | **完全一致** |
| 與 `tests/deselected_allowlist.json` | **完全一致** |

**總判**：8 支皆為「**刻意不執行**」（collection 階段 deselect）。  
若以 `-m integration` 強制選入，多數會再落入「**條件性跳過**」（proxy／token／DB）。  
確定性契約已由離線 substitute 形成「**測試收斂**」；殘餘缺口僅外部 I/O 與真模型品質。

---

## 1. 排除來源盤點（逐層）

### 1.1 CLI 參數（預設呼叫）

| 參數 | 預設是否使用 | 對 8 支的影響 |
|------|--------------|---------------|
| `-m` | **是**（經 `addopts`，非手動 CLI） | 表達式 `'not integration'` → deselect 全部 `@pytest.mark.integration` |
| `-k` | 否 | 無 |
| `--ignore` | 否 | 無 |
| `--deselect` | 否 | 無 |

手動覆寫示例（本報告實測）：

- 去掉 mark 過濾 → **118 collected, 0 deselected**
- `-m integration` → **8 selected / 110 deselected**（恰為同一組 8 支）

### 1.2 設定檔

| 檔案 | 狀態 | 內容 |
|------|------|------|
| `pytest.ini` | 不存在 | — |
| `setup.cfg` | 不存在 | — |
| `tox.ini` | 不存在 | — |
| [`pyproject.toml`](../pyproject.toml) | **唯一 pytest 設定源** | 見下 |

[`pyproject.toml`](../pyproject.toml) 第 25–35 行（重點）：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

- **直接排除責任**：`addopts` 中的 `-m 'not integration'`  
- **標記宣告**：`integration` marker（`--strict-markers` 強制需先註冊）  
- 其餘 addopts（`-p no:asyncio`、warning 升級）**不**負責 deselect

輔助腳本（非 pytest 設定，但會再傳 `-m`）：

- [`scripts/run_tests.sh`](../scripts/run_tests.sh)：`default` 模式明確 `-m "not integration"`
- [`scripts/dep_upgrade_check.py`](../scripts/dep_upgrade_check.py)：同樣排除 integration

### 1.3 conftest hooks

[`tests/conftest.py`](../tests/conftest.py)：

| Hook | 行為 | 是否造成排除 |
|------|------|--------------|
| `pytest_addoption(--deselected-details)` | 開啟詳情報告 | 否 |
| `pytest_deselected` | 記錄 markexpr／keyword／deselect 原因 | **否**（只觀測） |
| `pytest_terminal_summary` | 印出 `nodeid \| reason: deselected by ...` | 否 |
| `async_client` fixture | ASGI 測試用 | 否 |

實測 8 支 reason 一律：

```text
deselected by -m 'not integration'
```

### 1.4 環境條件（與 deselected 的層級差異）

| 層級 | 時機 | 本報告 8 支在預設跑法下 |
|------|------|-------------------------|
| **deselected** | collection | **是** — 唯一預設排除原因 |
| **skipped** | runtime（選入後） | **否** — 預設根本未執行，故不會出現 skipped |

環境條件只在 **選入 integration 後** 才可能觸發 `skipif` / `pytest.skip`：

| 條件 | 檢查方式 | 相關測試 |
|------|----------|----------|
| Grok proxy `127.0.0.1:8318` | TCP / `_grok_reachable()` / `_grok_up()` | domain, gap, llm, pipeline, questions, retrieve, e2e |
| `TWINKLE_HUB_TOKEN` | `os.environ` | twinkle, retrieve, e2e |
| `data/law_index.db` | `Path.exists()` | retrieve, e2e |
| model `grok-4.3` | 客戶端預設 | 真打 Grok 的 integration 測試 |

---

## 2. 分類定義（本報告採用）

| 分類 | 定義 | 本 repo 對應 |
|------|------|--------------|
| **刻意不執行** | 設定／策略在 collection 即排除，日常 CI 不跑 | `addopts` + `@pytest.mark.integration` |
| **條件性跳過** | 已選入，但依環境 `skipif`／`pytest.skip` | proxy 未上線、缺 token、缺 DB |
| **測試收斂** | 離線 substitute 已覆蓋確定性契約，integration 僅驗證外部真實 I/O／模型品質 | `tests/deselected_allowlist.json` 的 `substitute_tests` |

單一測試可同時具備多層標籤：**預設 = 刻意不執行**；強制選入後 = 可能 **條件性跳過**；契約面 = **測試收斂**。

---

## 3. 逐一追查（8 支）

### #1 `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 欄位 | 內容 |
|------|------|
| 標記 | `@pytest.mark.integration`（`tests/test_domain.py:50`） |
| 預設排除 | **刻意不執行** — `-m 'not integration'` |
| 選入後條件 | **條件性跳過** — `@pytest.mark.skipif(not _grok_reachable(), ...)`（:51） |
| 測試收斂 | `tests/test_domain.py::test_detect_domain_law`（FakeLLM 契約） |
| 殘餘缺口 | 真 grok 對法律文字回 `law` 的模型正確性 |
| allowlist decision | `acceptable_unexecuted` |

**可重現（排除證明）**：

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  --collect-only -q --deselected-details --color=no
# 預期含：...test_detect_domain_real_grok_returns_law | reason: deselected by -m 'not integration'
```

**可重現（強制選入）**：

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_domain.py::test_detect_domain_real_grok_returns_law `
  -m integration -q --tb=short --color=no
# proxy 離線 → skipped；proxy 在線 → 真打 8318
```

---

### #2 `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 欄位 | 內容 |
|------|------|
| 標記 | `@pytest.mark.integration`（`tests/test_e2e_acceptance.py:244`） |
| 預設排除 | **刻意不執行** |
| 選入後條件 | **條件性跳過** — 函式內 `pytest.skip`：缺 `data/law_index.db`；或 `not (_grok_up() and _twinkle_ready())`（:247–255） |
| 測試收斂 | `test_e2e_structural_invariants`、`test_e2e_offline_supplement_quality_boundary`、`test_e2e_minimal_quality_gates_offline_regression`、pipeline／correction 品質閘替代 |
| 殘餘缺口 | 真模型+真檢索下 gap／寫作品質、Level A 路由穩定性 |
| allowlist decision | `acceptable_unexecuted` |

**可重現（排除證明）**：同上 `--deselected-details`。

**可重現（強制選入）**：

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_e2e_acceptance.py::test_e2e_acceptance_real `
  -m integration -q --tb=short --color=no
# 需：law_index.db + grok:8318 + $env:TWINKLE_HUB_TOKEN
```

---

### #3 `tests/test_gap.py::test_detect_gaps_real_grok`

| 欄位 | 內容 |
|------|------|
| 標記 | `@pytest.mark.integration`（:71） |
| 預設排除 | **刻意不執行** |
| 選入後條件 | **條件性跳過** — `skipif(not _grok_reachable())`（:72） |
| 測試收斂 | `test_detect_gaps_keeps_only_partial_and_missing` |
| 殘餘缺口 | 真 grok 缺口判斷品質 |
| allowlist decision | `acceptable_unexecuted` |

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_gap.py::test_detect_gaps_real_grok -m integration -q --tb=short --color=no
```

---

### #4 `tests/test_llm.py::test_grok_pong_integration`

| 欄位 | 內容 |
|------|------|
| 標記 | `@pytest.mark.integration`（:66） |
| 預設排除 | **刻意不執行** |
| 選入後條件 | **條件性跳過** — `skipif(not _grok_reachable())`（:67） |
| 測試收斂 | `test_grokclient_builds_request_body`（request body／Bearer／parse） |
| 殘餘缺口 | 真實 TCP 至 proxy 與回應格式 |
| allowlist decision | `acceptable_unexecuted` |

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_llm.py::test_grok_pong_integration -m integration -q --tb=short --color=no
```

---

### #5 `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 欄位 | 內容 |
|------|------|
| 標記 | `@pytest.mark.integration`（:151） |
| 預設排除 | **刻意不執行** |
| 選入後條件 | **條件性跳過** — `skipif(not _grok_reachable())`（:152）；Twinkle／law 以 fake 隔離 |
| 測試收斂 | `test_run_pipeline_invariant`、`test_run_pipeline_malformed_gap_output_falls_back_to_pending`、`test_run_pipeline_law_domain_runs_citation_check`、`test_retrieved_five_but_only_two_cited` |
| 殘餘缺口 | 真 Grok 輸出下 domain/questions/gaps 正確性 |
| allowlist decision | `acceptable_unexecuted` |

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_pipeline.py::test_run_pipeline_real_grok -m integration -q --tb=short --color=no
```

---

### #6 `tests/test_questions.py::test_generate_questions_real_grok`

| 欄位 | 內容 |
|------|------|
| 標記 | `@pytest.mark.integration`（:62） |
| 預設排除 | **刻意不執行** |
| 選入後條件 | **條件性跳過** — `skipif(not _grok_reachable())`（:63） |
| 測試收斂 | `test_generate_questions_splits_multiline_string`、`test_generate_questions_strips_and_drops_blank_lines` |
| 殘餘缺口 | 真模型問題生成品質 |
| allowlist decision | `acceptable_unexecuted` |

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_questions.py::test_generate_questions_real_grok -m integration -q --tb=short --color=no
```

---

### #7 `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 欄位 | 內容 |
|------|------|
| 標記 | `@pytest.mark.integration`（:102） |
| 預設排除 | **刻意不執行** |
| 選入後條件 | **條件性跳過** — `skipif(not LAW_DB.exists())`（:103）、`skipif(not _grok_reachable())`（:104）、函式內缺 `TWINKLE_HUB_TOKEN` → `pytest.skip`（:106–108） |
| 測試收斂 | Level A/B 排序、law_search、twinkle mock 系列 |
| 殘餘缺口 | 真實 Twinkle Hub I/O、真 Grok 關鍵字抽取 |
| allowlist decision | `acceptable_unexecuted` |

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke `
  -m integration -q --tb=short --color=no
# 需：data/law_index.db + grok:8318 + $env:TWINKLE_HUB_TOKEN
```

---

### #8 `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 欄位 | 內容 |
|------|------|
| 標記 | `@pytest.mark.integration`（:122） |
| 預設排除 | **刻意不執行** |
| 選入後條件 | **條件性跳過** — 缺 `TWINKLE_HUB_TOKEN` → `pytest.skip`（:126–128）；**無** grok skipif（純 Twinkle） |
| 測試收斂 | `test_search_parses_source_with_full_content`、`test_search_reuses_mcp_session`、`test_search_transport_failure_returns_empty` |
| 殘餘缺口 | 真實 Twinkle 服務可用性／session／逾時 |
| allowlist decision | `acceptable_unexecuted` |

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  tests/test_twinkle.py::test_search_real_twinkle_hub -m integration -q --tb=short --color=no
# 需：$env:TWINKLE_HUB_TOKEN
```

---

## 4. 分類總表

| # | node ID | 預設（collection） | 強制選入後（runtime） | 離線契約 | 是否誤排除 |
|---|---------|-------------------|----------------------|----------|------------|
| 1 | `test_detect_domain_real_grok_returns_law` | 刻意不執行 | 條件性跳過（proxy） | 測試收斂 | **否** |
| 2 | `test_e2e_acceptance_real` | 刻意不執行 | 條件性跳過（DB+proxy+token） | 測試收斂 | **否** |
| 3 | `test_detect_gaps_real_grok` | 刻意不執行 | 條件性跳過（proxy） | 測試收斂 | **否** |
| 4 | `test_grok_pong_integration` | 刻意不執行 | 條件性跳過（proxy） | 測試收斂 | **否** |
| 5 | `test_run_pipeline_real_grok` | 刻意不執行 | 條件性跳過（proxy） | 測試收斂 | **否** |
| 6 | `test_generate_questions_real_grok` | 刻意不執行 | 條件性跳過（proxy） | 測試收斂 | **否** |
| 7 | `test_retrieve_for_gap_real_twinkle_smoke` | 刻意不執行 | 條件性跳過（DB+proxy+token） | 測試收斂 | **否** |
| 8 | `test_search_real_twinkle_hub` | 刻意不執行 | 條件性跳過（token） | 測試收斂 | **否** |

**分類計數（預設日常路徑）**：

- 刻意不執行：**8 / 8**
- 條件性跳過（預設路徑）：**0 / 8**（未選入，故不發生 skip）
- 條件性跳過（僅在 `-m integration` 後可能）：**8 / 8** 皆有至少一層環境 gate
- 測試收斂（確定性路徑有 substitute）：**8 / 8**

---

## 5. 機制因果鏈（單一責任）

```text
@pytest.mark.integration  (各測試函式)
        │
        ▼
pyproject.toml addopts: -m 'not integration'
        │
        ▼
pytest collection: deselect 8 items
        │
        ▼
conftest pytest_deselected（僅報告，不決策）
        │
        ▼
日常結果: 110 selected, 8 deselected  （非 skipped）
```

**非原因**（已排除）：

- 無 `-k` 關鍵字過濾
- 無 `--ignore` 路徑忽略
- 無 `--deselect` 前綴剔除
- 無 `pytest.ini` / `setup.cfg`
- conftest **不**主動過濾 collection

---

## 6. 可重現命令套件（完整）

以主專案 venv（任務硬性規定）：

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"

# 6.1 預設：8 deselected + 原因
& $py -X utf8 -m pytest --collect-only -q --deselected-details --color=no
# 期望：110/118 tests collected (8 deselected)
# 期望：8 行 "reason: deselected by -m 'not integration'"

# 6.2 恰選 integration 集合
& $py -X utf8 -m pytest --collect-only -q -m integration --color=no
# 期望：8/118 tests collected (110 deselected)；清單 = §3 八支

# 6.3 全量（無 mark 過濾）— 證明非 --ignore
& $py -X utf8 -m pytest --collect-only -q `
  -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" `
  --color=no
# 期望：118 tests collected（0 deselected）

# 6.4 否定：-k 不是預設排除源（僅示範 keyword 可選到同集合）
& $py -X utf8 -m pytest --collect-only -q `
  -k "real_grok or real_twinkle or pong_integration or e2e_acceptance_real" `
  -o "addopts=-p no:asyncio --strict-markers" --color=no
# 期望：同一組 8 支；但預設跑法並未使用此 -k

# 6.5 日常品質閘（不跑 8 支）
& $py -X utf8 -m pytest -m "not integration" -q --color=no
# 期望：N passed, 8 deselected（N 隨測試總數；目前 110）

# 6.6 allowlist / guard 穩定
& $py -X utf8 -m pytest tests/test_deselection_guard.py -q --tb=short --color=no

# 6.7 批次強制補跑 8 支（環境齊備時；平時可能大量 skip）
& $py -X utf8 -m pytest -m integration -q --tb=line --color=no
```

### 6.8 本輪實測輸出摘錄（2026-07-19）

**預設 + `--deselected-details` 尾端**（完整清單見  
[`docs/pytest-audit/excluded-cause-collect-2026-07-19.txt`](pytest-audit/excluded-cause-collect-2026-07-19.txt)）：

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

**設定掃描**（[`excluded-cause-config-scan-2026-07-19.txt`](pytest-audit/excluded-cause-config-scan-2026-07-19.txt)）：

```text
pytest.ini exists: False
setup.cfg exists: False
tox.ini exists: False
```

**全量 collect 末行**：`118 tests collected`  
**integration collect 末行**：`8/118 tests collected (110 deselected)`

---

## 7. 與品質閘／既有產物對齊

| 產物 | 角色 |
|------|------|
| 本報告 | 排除**原因追查** + 三分類 + 可重現命令 |
| [`tests/deselected_allowlist.json`](../tests/deselected_allowlist.json) | 機器可讀 allowlist + substitute |
| [`tests/test_deselection_guard.py`](../tests/test_deselection_guard.py) | 計數／node ID／映射穩定 guard |
| [`docs/deselected-tests-inventory-2026-07-19.md`](deselected-tests-inventory-2026-07-19.md) | 清單盤點（姊妹文件） |

**品質閘未弱化**：本任務為調查／落盤報告，**未**改 `addopts`、**未**移除 `integration` marker、**未**動 `BACKLOG.md`。

---

## 8. 最終判定

1. **8 支被排除的直接且唯一 collection 原因**：`pyproject.toml` 的 `-m 'not integration'`，對應各函式 `@pytest.mark.integration`。  
2. **分類（日常預設）**：全部為 **刻意不執行**；非 flaky skip、非誤用 `--ignore`/`-k`。  
3. **次層**：強制 `-m integration` 後，8 支皆可因環境不足進入 **條件性跳過**。  
4. **契約層**：8 支皆有離線 substitute → **測試收斂**；殘餘為外部服務／真模型，屬 integration 本分，不應強行納入預設閘。  
5. **可稽核性**：node ID、reason 字串、設定掃描、collect 數字均已寫入 `docs/pytest-audit/excluded-cause-*-2026-07-19.txt` 與本報告。
