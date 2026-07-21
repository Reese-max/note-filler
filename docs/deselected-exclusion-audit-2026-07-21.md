# Deselected 測試排除審計報告

日期：2026-07-21  
依據：pytest `--collect-only --deselected-details` 輸出 + 原始碼逐項核對

## 觸發排除的設定來源

pyproject.toml:32 `addopts` 中的 `-m 'not integration'` 是唯一起作用的 collection 篩選器。
沒有 `-k` 表達式、沒有 `--deselect` 旗標、沒有 path 規則參與排除。

## 排除總覽

- 收集總數：150 items
- deselected：8
- selected：142
- 排除原因：全部為 `-m 'not integration'`

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
| 原始檔 | `tests/test_twinkle.py:148` |
| 參數化來源 | 無 |
| 排除機制 | `@pytest.mark.integration` (line 141) → `-m 'not integration'` |
| 額外防護 | 函式內 `pytest.skip()` if no TWINKLE_HUB_TOKEN (line 146-147) |
| 設計意圖 | 真實 Twinkle Hub MCP 連線、搜尋與 Source 解析 |
| 受控判定 | **受控，設計意圖明確** — 4 個替代測試（mock MCP 契約）+ failing-first `test_control_08` |

## 綜合結論

1. **排除原因單一**：全部 8 項僅因 `-m 'not integration'` 在 collection 階段被排除；無 `-k`、path 或 config 其他規則介入。
2. **原始對應明確**：每個 deselected node 可直接追溯到對應測試檔中明確的 `@pytest.mark.integration` decorator。
3. **參數化**：全部 8 項皆為純函式，**無** `@pytest.mark.parametrize`。
4. **受控程度**：8/8 皆為**受控且有明確設計意圖**。每個排除都有：
   - `@pytest.mark.skipif` 或 `pytest.skip()` 的雙重防護
   - 在 `tests/deselected_allowlist.json` 中註冊（機器可讀）
   - 等價的非 integration 替代測試
   - failing-first 對照測試 (`tests/test_excluded_failing_controls.py`)
   - CI `workflow_dispatch` 或本機手動的繞路執行管道
5. **設計意圖模式**：全部 8 項都是因為需要**真實網路/模型服務**（grok proxy :8318 或 Twinkle Hub）而標記 integration，這些環境在預設 CI 中不可用，因此被合理排除。
