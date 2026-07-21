# Deselected 測試排除審計報告

日期：2026-07-21  
依據：pytest `--collect-only --deselected-details` 輸出 + 原始碼逐項核對

## 觸發排除的設定來源

pyproject.toml:32 `addopts` 中的 `-m 'not integration'` 是唯一起作用的 collection 篩選器。
沒有 `-k` 表達式、`--ignore` / `--deselect` 旗標或 repo 自定義收集 hook 參與這 8 項排除。

## 排除總覽

- 收集總數：150 items
- deselected：8
- selected：142
- 排除原因：全部為 `-m 'not integration'`

## 8 項完整清單

| # | 完整 node ID | 所在檔案（定義行） | 測試名稱 | 導致 deselection 的具體條件 |
|---:|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `tests/test_domain.py:52` | `test_detect_domain_real_grok_returns_law` | `tests/test_domain.py:50` 的 `@pytest.mark.integration` 被 `pyproject.toml:32` 預設 `-m 'not integration'` 排除 |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py:245` | `test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py:244` 的 `@pytest.mark.integration` 被 `pyproject.toml:32` 預設 `-m 'not integration'` 排除 |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `tests/test_gap.py:73` | `test_detect_gaps_real_grok` | `tests/test_gap.py:71` 的 `@pytest.mark.integration` 被 `pyproject.toml:32` 預設 `-m 'not integration'` 排除 |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `tests/test_llm.py:68` | `test_grok_pong_integration` | `tests/test_llm.py:66` 的 `@pytest.mark.integration` 被 `pyproject.toml:32` 預設 `-m 'not integration'` 排除 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `tests/test_pipeline.py:153` | `test_run_pipeline_real_grok` | `tests/test_pipeline.py:151` 的 `@pytest.mark.integration` 被 `pyproject.toml:32` 預設 `-m 'not integration'` 排除 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `tests/test_questions.py:64` | `test_generate_questions_real_grok` | `tests/test_questions.py:62` 的 `@pytest.mark.integration` 被 `pyproject.toml:32` 預設 `-m 'not integration'` 排除 |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py:105` | `test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py:102` 的 `@pytest.mark.integration` 被 `pyproject.toml:32` 預設 `-m 'not integration'` 排除 |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `tests/test_twinkle.py:142` | `test_search_real_twinkle_hub` | `tests/test_twinkle.py:141` 的 `@pytest.mark.integration` 被 `pyproject.toml:32` 預設 `-m 'not integration'` 排除 |

## Selection 機制排除對照

| 機制 | 是否造成這 8 項 deselection | 具體條件與證據 |
|---|---|---|
| pytest marker | **是** | `pyproject.toml:32` 的 `addopts` 預設套用 `-m 'not integration'`；8 個函式均有 `@pytest.mark.integration`。pytest 內建 marker selection 在 collection 階段將它們 deselect。 |
| `-k` | 否 | 本次命令與 `PYTEST_ADDOPTS` 都沒有 keyword expression；repo 的 `pyproject.toml` / `.github` / `scripts` / `tests` 也沒有作業用 `-k`。`--deselected-details` 實跑的 8 行原因只有 `-m 'not integration'`。 |
| `--ignore` | 否 | 命令、`addopts`、CI 與腳本皆無 `--ignore`；`testpaths = ["tests"]` 只限定收集根目錄，8 個 node 都在其中。 |
| `--deselect` | 否 | 本次未傳入，`config.getoption("deselect")` 為空；`tests/conftest.py:28-31` 僅能在有傳入時顯示該原因。 |
| repo 收集 hook | 否 | repo 只定義 `pytest_addoption`、`pytest_deselected` 與 `pytest_terminal_summary`。`pytest_deselected` 只接收 pytest 已排除的 items 供輸出，不改寫 item 集合；無 `pytest_collection_modifyitems`、`pytest_ignore_collect` 或 `collect_ignore`。 |
| `skipif` / `pytest.skip()` | 否 | 這些是取消 `-m` 排除、真正執行 integration 時才評估的 runtime skip，不是 collection deselection。各 node 條件見下方「額外防護」。 |
| 環境附加參數 | 否 | 實跑時 `PYTEST_ADDOPTS` 與 `PYTEST_PLUGINS` 均為空，沒有隱藏的環境篩選。 |

## 可重現驗證

環境：Python 3.11.9、pytest 9.1.1。實跑結果：

| 命令目的 | 結果 | 證明 |
|---|---|---|
| 預設 collection + `--deselected-details` | `142/150 tests collected (8 deselected)` | 8 行完整 node ID 均回報 `deselected by -m 'not integration'` |
| 以 `-o "addopts=-p no:asyncio --strict-markers"` 移除預設 mark expression | `150 tests collected` | 8 項本身可收集，無 `--ignore`、path 或 hook 另行排除 |
| 同上並明確套用 `-m integration` | `8/150 tests collected (142 deselected)` | integration 集合與預設的 8 項 deselected 差集完全相等 |

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest --collect-only -q --deselected-details --color=no
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest --collect-only -q -o "addopts=-p no:asyncio --strict-markers" --color=no
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest --collect-only -q -o "addopts=-p no:asyncio --strict-markers" -m integration --deselected-details --color=no
```

## 逐項審計

### #1 `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 屬性 | 內容 |
|---|---|
| 原始檔 | `tests/test_domain.py:52` |
| 參數化來源 | 無（純函式，無 `@pytest.mark.parametrize`） |
| 排除機制 | `@pytest.mark.integration` (line 50) → `-m 'not integration'` |
| 額外防護 | `@pytest.mark.skipif(not _grok_reachable(), ...)` (line 51) |
| 設計意圖 | 驗證真實 GrokClient 對法律文字回傳 `"law"`；需要 grok proxy (:8318) |
| 受控判定 | **受控，設計意圖明確** — 有等價替代測試 `test_detect_domain_law` + failing-first 對照 `test_control_01` |

### #2 `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 屬性 | 內容 |
|---|---|
| 原始檔 | `tests/test_e2e_acceptance.py:245` |
| 參數化來源 | 無 |
| 排除機制 | `@pytest.mark.integration` (line 244) → `-m 'not integration'` |
| 額外防護 | 函式內 `pytest.skip()` 檢查 `LAW_DB.exists()` (line 247)、`_grok_up() and _twinkle_ready()` (line 251) |
| 設計意圖 | 端到端真實 pipeline 驗收（parse→domain→questions→gaps→retrieve→assemble→export）；需 grok proxy + TWINKLE_HUB_TOKEN + law_index.db |
| 受控判定 | **受控，設計意圖明確** — 8 個替代測試覆蓋各環節 + failing-first 對照 `test_control_02` |

### #3 `tests/test_gap.py::test_detect_gaps_real_grok`

| 屬性 | 內容 |
|---|---|
| 原始檔 | `tests/test_gap.py:73` |
| 參數化來源 | 無 |
| 排除機制 | `@pytest.mark.integration` (line 71) → `-m 'not integration'` |
| 額外防護 | `@pytest.mark.skipif(not _grok_reachable(), ...)` (line 72) |
| 設計意圖 | 驗證真實 Grok 對法律文本的缺口判斷品質 |
| 受控判定 | **受控，設計意圖明確** — 替代測試 `test_detect_gaps_keeps_only_partial_and_missing` + failing-first `test_control_03` |

### #4 `tests/test_llm.py::test_grok_pong_integration`

| 屬性 | 內容 |
|---|---|
| 原始檔 | `tests/test_llm.py:68` |
| 參數化來源 | 無 |
| 排除機制 | `@pytest.mark.integration` (line 66) → `-m 'not integration'` |
| 額外防護 | `@pytest.mark.skipif(not _grok_reachable(), ...)` (line 67) |
| 設計意圖 | 驗證 GrokClient TCP 連線 + PONG 契約；真實 proxy 連通性 |
| 受控判定 | **受控，設計意圖明確** — 替代 `test_grokclient_builds_request_body` + failing-first `test_control_04` |

### #5 `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 屬性 | 內容 |
|---|---|
| 原始檔 | `tests/test_pipeline.py:153` |
| 參數化來源 | 無（但使用 `note_path` fixture） |
| 排除機制 | `@pytest.mark.integration` (line 151) → `-m 'not integration'` |
| 額外防護 | `@pytest.mark.skipif(not _grok_reachable(), ...)` (line 152) |
| 設計意圖 | 驗證完整 pipeline 在真 Grok 輸出下不炸 + C6 不變式；twinkle/law 用 fake 隔離 |
| 受控判定 | **受控，設計意圖明確** — 3 個 pipeline 替代測試 + failing-first `test_control_05` |

### #6 `tests/test_questions.py::test_generate_questions_real_grok`

| 屬性 | 內容 |
|---|---|
| 原始檔 | `tests/test_questions.py:64` |
| 參數化來源 | 無 |
| 排除機制 | `@pytest.mark.integration` (line 62) → `-m 'not integration'` |
| 額外防護 | `@pytest.mark.skipif(not _grok_reachable(), ...)` (line 63) |
| 設計意圖 | 驗證真實 Grok 對法律文本的問題生成品質 |
| 受控判定 | **受控，設計意圖明確** — 替代測試 `test_generate_questions_splits_multiline_string` + failing-first `test_control_06` |

### #7 `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 屬性 | 內容 |
|---|---|
| 原始檔 | `tests/test_retrieve.py:105` |
| 參數化來源 | 無 |
| 排除機制 | `@pytest.mark.integration` (line 102) → `-m 'not integration'` |
| 額外防護 | `@pytest.mark.skipif(not LAW_DB.exists(), ...)` (line 103)；`@pytest.mark.skipif(not _grok_reachable(), ...)` (line 104)；函式內 `pytest.skip()` if no TWINKLE_HUB_TOKEN (line 107-108) |
| 設計意圖 | 真實 Twinkle Hub MCP + LawLookup + Grok keyword + 排序不變式 |
| 受控判定 | **受控，設計意圖明確** — 9 個替代測試（含盲區回歸 `test_exclusion_correctness_blind_spot.py`）+ failing-first `test_control_07`/`07b` |

### #8 `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 屬性 | 內容 |
|---|---|
| 原始檔 | `tests/test_twinkle.py:142` |
| 參數化來源 | 無 |
| 排除機制 | `@pytest.mark.integration` (line 141) → `-m 'not integration'` |
| 額外防護 | 函式內 `pytest.skip()` if no TWINKLE_HUB_TOKEN (line 146-147) |
| 設計意圖 | 真實 Twinkle Hub MCP 連線、搜尋與 Source 解析 |
| 受控判定 | **受控，設計意圖明確** — 4 個替代測試（mock MCP 契約）+ failing-first `test_control_08` |

## 綜合結論

1. **排除原因單一**：全部 8 項僅因 `-m 'not integration'` 在 collection 階段被排除；無 `-k`、`--ignore`、`--deselect` 或 repo 自定義收集 hook 介入。
2. **原始對應明確**：每個 deselected node 可直接追溯到對應測試檔中明確的 `@pytest.mark.integration` decorator。
3. **參數化**：全部 8 項皆為純函式，**無** `@pytest.mark.parametrize`。
4. **受控程度**：8/8 皆為**受控且有明確設計意圖**。每個排除都有：
   - `@pytest.mark.skipif` 或 `pytest.skip()` 的雙重防護
   - 在 `tests/deselected_allowlist.json` 中註冊（機器可讀）
   - 等價的非 integration 替代測試
   - failing-first 對照測試 (`tests/test_excluded_failing_controls.py`)
   - CI `workflow_dispatch` 或本機手動的繞路執行管道
5. **設計意圖模式**：全部 8 項都是因為需要**真實網路/模型服務**（grok proxy :8318 或 Twinkle Hub）而標記 integration，這些環境在預設 CI 中不可用，因此被合理排除。
