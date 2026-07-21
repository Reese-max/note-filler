# 8 個 deselected node ID：排除規則追溯鏈對照表

> **任務**：將每個 deselected node ID 的排除證據補成可追溯鏈——逐一定位
> `pytest.ini` / `pyproject.toml` / `conftest.py` / 測試模組中的 marker、
> skip/xfail、path 或 `-k` 規則，整理成「規則位置 → 觸發條件 → 影響到的
> correctness 路徑」對照表。
>
> **驗證日**：2026-07-21
> **Python**：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`
> **工作目錄**：本 worktree root（禁止跨 repo）

---

## 0. 全局規則索引

| # | 規則位置 | 規則類型 | 設定值 / 行為 | 影響範圍 |
|---|---|---|---|---|
| **G1** | `pyproject.toml:32` | **addopts mark 過濾** | `-m 'not integration'` | 所有帶 `@pytest.mark.integration` 的 item 在 collection 階段被 deselect |
| **G2** | `pyproject.toml:33-34` | **markers 宣告** | `integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過` | 配合 `--strict-markers` 確保 marker 合法 |
| **G3** | `pyproject.toml:32` | **strict-markers** | `--strict-markers` | 未宣告的 marker 會報錯；不直接 deselect |
| **G4** | `pyproject.toml:32` | **asyncio plugin 禁用** | `-p no:asyncio` | 禁用 pytest-asyncio plugin；不參與 deselect |
| **G5** | `pyproject.toml:32` | **deprecation 錯誤化** | `-W error::DeprecationWarning -W error::PendingDeprecationWarning` | Deprecation 變成 error；不直接 deselect |
| **G6** | `pyproject.toml:25-26` | **testpaths** | `testpaths = ["tests"]` | 只收集 `tests/` 下測試；不縮篩 deselected |
| **G7** | `tests/conftest.py:6-11` | **addoption --deselected-details** | `parser.addoption("--deselected-details", ...)` | 開啟 deselected 詳情報告；不修改 selection |
| **G8** | `tests/conftest.py:14-34` | **pytest_deselected hook** | 讀取 deselected items 並記錄原因 | 觀察 hook；不修改 selection |
| **G9** | `tests/conftest.py:37-45` | **pytest_terminal_summary hook** | 輸出 deselected details | 觀察 hook；不修改 selection |
| **G10** | `.github/workflows/ci.yml` | **CI job** | 日常 job `-m "not integration"`；手動 job `-m "integration"` | CI 與預設規則一致 |

---

## 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

### 規則追溯鏈

| 層級 | 規則位置 | 規則類型 | 觸發條件 | 預設下是否觸發 |
|---|---|---|---|---|
| **L1** | `pyproject.toml:32` addopts | `-m 'not integration'` | item 帶 `integration=True` marker | **是 — 唯一 deselect 主因** |
| **L2** | `tests/test_domain.py:50` | `@pytest.mark.integration` | 為測試函式標記 | 是（被 L1 命中） |
| **L3** | `tests/test_domain.py:51` | `@pytest.mark.skipif(not _grok_reachable())` | `socket.create_connection("127.0.0.1:8318", 1.0)` 失敗 | 否（預設下不走到 runtime） |
| **L4** | `tests/conftest.py:14-34` | `pytest_deselected` hook | items 被 deselect 後觸發 | 觀察；不修改 |

### correctness 路徑影響

| 正確性保證 | 被排除測試驗證的內容 | 替代覆蓋 | 殘留缺口 |
|---|---|---|---|
| **domain 標籤 determinism** | 真 Grok 對法律文字回傳 `"law"` | `test_detect_domain_law`（FakeLLM, L17-19）、`test_control_01_domain_legal_label_contract`（FakeLLM, 多標籤） | 真 Grok 語意品質（外部模型） |
| **strip/fallback 穩健性** | `"law."` → `"law"`、`"  LAW  "` → `"law"` | 同上 | — |

### 追溯摘要

```
pyproject.toml:32  addopts="-m 'not integration'"
        │
        ▼
test_domain.py:50  @pytest.mark.integration
        │
        ▼
pytest core mark selector: not integration → False → deselect
        │
        ▼
test_domain.py:51  skipif(not _grok_reachable()) ← runtime guard（預設不觸發）
        │
        ▼
correctness 路徑: domain label contract → 被 FakeLLM 測試覆蓋
```

---

## 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

### 規則追溯鏈

| 層級 | 規則位置 | 規則類型 | 觸發條件 | 預設下是否觸發 |
|---|---|---|---|---|
| **L1** | `pyproject.toml:32` | `-m 'not integration'` | item 帶 `integration=True` marker | **是** |
| **L2** | `tests/test_e2e_acceptance.py:244` | `@pytest.mark.integration` | 為測試函式標記 | 是 |
| **L3** | `tests/test_e2e_acceptance.py:247-248` | `if not LAW_DB.exists(): pytest.skip()` | `data/law_index.db` 不存在 | 否（runtime guard） |
| **L4** | `tests/test_e2e_acceptance.py:251-254` | `if not (_grok_up() and _twinkle_ready()): pytest.skip()` | grok proxy 未上線或無 `TWINKLE_HUB_TOKEN` | 否（runtime guard） |

### correctness 路徑影響

| 正確性保證 | 被排除測試驗證的內容 | 替代覆蓋 | 殘留缺口 |
|---|---|---|---|
| **§12(1) 原稿逐字不可變** | 真 Grok+真 Twinkle 下原稿不被竄改 | `test_e2e_structural_invariants`（FakeLLM+StubTwinkle, L150-173） | — |
| **§12(2) 無來源閘 C6** | 真跑下 supplement sources 空 → `pending_evidence` | `test_run_pipeline_invariant`（L56-95） | — |
| **§12(3) verified 交叉驗證** | `>=1 Level A` 且 `>=2` 獨立來源 | `test_e2e_offline_supplement_quality_boundary`（L196-204） | — |
| **§12(4) 法條引用離線查核** | 補充內法條真實存在 | `test_run_pipeline_law_domain_runs_citation_check`（L98-123） | — |
| **§12(5) to_markdown 格式** | 含【補充】/⚠待補證/參考區塊 | `test_e2e_minimal_quality_gates_offline_regression`（L211-240） | — |
| **端到端品質** | 真 Grok+真 Twinkle 組合下全路徑正確 | `test_control_02_e2e_offline_quality_gates` | 真外部服務組合品質 |

### 追溯摘要

```
pyproject.toml:32  addopts="-m 'not integration'"
        │
        ▼
test_e2e_acceptance.py:244  @pytest.mark.integration
        │
        ▼
pytest core mark selector → deselect
        │
        ▼
test_e2e_acceptance.py:247  if not LAW_DB.exists(): pytest.skip()
test_e2e_acceptance.py:251  if not (_grok_up() and _twinkle_ready()): pytest.skip()
        │
        ▼
correctness 路徑: 五項 §12 不變式 → 被結構類/離線替代測試覆蓋
```

---

## 3. `tests/test_gap.py::test_detect_gaps_real_grok`

### 規則追溯鏈

| 層級 | 規則位置 | 規則類型 | 觸發條件 | 預設下是否觸發 |
|---|---|---|---|---|
| **L1** | `pyproject.toml:32` | `-m 'not integration'` | item 帶 `integration=True` marker | **是** |
| **L2** | `tests/test_gap.py:71` | `@pytest.mark.integration` | 為測試函式標記 | 是 |
| **L3** | `tests/test_gap.py:72` | `@pytest.mark.skipif(not _grok_reachable())` | grok proxy 未上線 | 否（runtime guard） |

### correctness 路徑影響

| 正確性保證 | 被排除測試驗證的內容 | 替代覆蓋 | 殘留缺口 |
|---|---|---|---|
| **缺口過濾 determinism** | 真 Grok 回傳的 JSON 陣列中 covered 被過濾 | `test_detect_gaps_keeps_only_partial_and_missing`（L17-29, FakeLLM） | 真 Grok 對法律文本的缺口判斷品質 |
| **解析失敗降級** | JSON 解析失敗 → 全部標 missing | `test_detect_gaps_parse_failure_marks_all_missing`（L39-46） | — |
| **code fence 剝除** | `\`\`\`json` 圍欄可被剝除 | `test_detect_gaps_strips_code_fence`（L57-62） | — |
| **failing-first 對照** | 未涵蓋問題必須進缺口 | `test_control_03_gap_uncovered_question_must_surface` | — |

### 追溯摘要

```
pyproject.toml:32  addopts="-m 'not integration'"
        │
        ▼
test_gap.py:71  @pytest.mark.integration
        │
        ▼
pytest core mark selector → deselect
        │
        ▼
test_gap.py:72  skipif(not _grok_reachable()) ← runtime guard
        │
        ▼
correctness 路徑: gap filter / parse fallback / code fence → 被 6 個 FakeLLM 測試覆蓋
```

---

## 4. `tests/test_llm.py::test_grok_pong_integration`

### 規則追溯鏈

| 層級 | 規則位置 | 規則類型 | 觸發條件 | 預設下是否觸發 |
|---|---|---|---|---|
| **L1** | `pyproject.toml:32` | `-m 'not integration'` | item 帶 `integration=True` marker | **是** |
| **L2** | `tests/test_llm.py:66` | `@pytest.mark.integration` | 為測試函式標記 | 是 |
| **L3** | `tests/test_llm.py:67` | `@pytest.mark.skipif(not _grok_reachable())` | grok proxy 未上線 | 否（runtime guard） |

### correctness 路徑影響

| 正確性保證 | 被排除測試驗證的內容 | 替代覆蓋 | 殘留缺口 |
|---|---|---|---|
| **GrokClient request body** | endpoint URL、method、model、timeout | `test_grokclient_builds_request_body`（L24-63, monkeypatch） | — |
| **GrokClient response parse** | `choices[0].message.content` 解析 | 同上 | — |
| **TCP 連通性** | 真實 proxy 可達 | `test_control_04_grok_client_parse_and_endpoint_contract` | 純 TCP 連通性（基礎設施） |

### 追溯摘要

```
pyproject.toml:32  addopts="-m 'not integration'"
        │
        ▼
test_llm.py:66  @pytest.mark.integration
        │
        ▼
pytest core mark selector → deselect
        │
        ▼
test_llm.py:67  skipif(not _grok_reachable()) ← runtime guard
        │
        ▼
correctness 路徑: request body / response parse → 被 monkeypatch 測試覆蓋
```

---

## 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

### 規則追溯鏈

| 層級 | 規則位置 | 規則類型 | 觸發條件 | 預設下是否觸發 |
|---|---|---|---|---|
| **L1** | `pyproject.toml:32` | `-m 'not integration'` | item 帶 `integration=True` marker | **是** |
| **L2** | `tests/test_pipeline.py:151` | `@pytest.mark.integration` | 為測試函式標記 | 是 |
| **L3** | `tests/test_pipeline.py:152` | `@pytest.mark.skipif(not _grok_reachable())` | grok proxy 未上線 | 否（runtime guard） |

### correctness 路徑影響

| 正確性保證 | 被排除測試驗證的內容 | 替代覆蓋 | 殘留缺口 |
|---|---|---|---|
| **C6 不變式** | 真模型下無源 supplement → `pending_evidence` | `test_run_pipeline_invariant`（L56-95） | — |
| **法規引用查核** | law 領域補充段經過 `check_law_citations` | `test_run_pipeline_law_domain_runs_citation_check`（L98-123） | — |
| **畸形輸出降級** | LLM 回非 JSON → 降級 pending | `test_run_pipeline_malformed_gap_output_falls_back_to_pending`（L126-148） | — |
| **來源引用正確性** | verified 補充掛 `[^n]` 註腳 | `test_retrieved_five_but_only_two_cited`（test_correction.py） | — |
| **failing-first 對照** | C6 pending守門 | `test_control_05_pipeline_c6_pending_when_no_sources` | 真模型輸出品質 |

### 追溯摘要

```
pyproject.toml:32  addopts="-m 'not integration'"
        │
        ▼
test_pipeline.py:151  @pytest.mark.integration
        │
        ▼
pytest core mark selector → deselect
        │
        ▼
test_pipeline.py:152  skipif(not _grok_reachable()) ← runtime guard
        │
        ▼
correctness 路徑: C6 / citation check / malformed fallback → 被 FakeLLM 測試覆蓋
```

---

## 6. `tests/test_questions.py::test_generate_questions_real_grok`

### 規則追溯鏈

| 層級 | 規則位置 | 規則類型 | 觸發條件 | 預設下是否觸發 |
|---|---|---|---|---|
| **L1** | `pyproject.toml:32` | `-m 'not integration'` | item 帶 `integration=True` marker | **是** |
| **L2** | `tests/test_questions.py:62` | `@pytest.mark.integration` | 為測試函式標記 | 是 |
| **L3** | `tests/test_questions.py:63` | `@pytest.mark.skipif(not _grok_reachable())` | grok proxy 未上線 | 否（runtime guard） |

### correctness 路徑影響

| 正確性保證 | 被排除測試驗證的內容 | 替代覆蓋 | 殘留缺口 |
|---|---|---|---|
| **多行切割** | 換行分隔的問題清單正確解析 | `test_generate_questions_splits_multiline_string`（L17-29） | — |
| **strip/空行移除** | 前後空白 + 空行過濾 | `test_generate_questions_strips_and_drops_blank_lines`（L32-38） | — |
| **乾淨清單契約** | 不殘留 JSON 括號 | `test_control_06_questions_clean_list_contract` | 真 Grok 出題品質 |
| **LLM 呼叫次數** | 恰一次呼叫 | `test_generate_questions_calls_llm_exactly_once`（L49-59） | — |

### 追溯摘要

```
pyproject.toml:32  addopts="-m 'not integration'"
        │
        ▼
test_questions.py:62  @pytest.mark.integration
        │
        ▼
pytest core mark selector → deselect
        │
        ▼
test_questions.py:63  skipif(not _grok_reachable()) ← runtime guard
        │
        ▼
correctness 路徑: multiline / strip / clean list → 被 4 個 FakeLLM 測試覆蓋
```

---

## 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

### 規則追溯鏈

| 層級 | 規則位置 | 規則類型 | 觸發條件 | 預設下是否觸發 |
|---|---|---|---|---|
| **L1** | `pyproject.toml:32` | `-m 'not integration'` | item 帶 `integration=True` marker | **是** |
| **L2** | `tests/test_retrieve.py:102` | `@pytest.mark.integration` | 為測試函式標記 | 是 |
| **L3** | `tests/test_retrieve.py:103` | `@pytest.mark.skipif(not LAW_DB.exists())` | `data/law_index.db` 不存在 | 否（runtime guard） |
| **L4** | `tests/test_retrieve.py:104` | `@pytest.mark.skipif(not _grok_reachable())` | grok proxy 未上線 | 否（runtime guard） |
| **L5** | `tests/test_retrieve.py:107-108` | `if not token: pytest.skip()` | `TWINKLE_HUB_TOKEN` 未設定 | 否（runtime guard） |

### correctness 路徑影響

| 正確性保證 | 被排除測試驗證的內容 | 替代覆蓋 | 殘留缺口 |
|---|---|---|---|
| **Level A 優先排序** | 法條 A 在 twinkle B 之前 | `test_retrieve_for_gap_law_domain_puts_level_A_before_B`（L62-77） | — |
| **vacuous pass 盲區** | smoke 斷言對 empty 仍綠 | `test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot` | — |
| **law+LawLookup 非空** | law 領域 + LawLookup 不得回空 | `test_control_07b_retrieve_law_level_a_not_vacuous` | 真 Twinkle Hub I/O |
| **Twinkle 解析** | Source 正確解析 | `test_search_parses_source_with_full_content`（test_twinkle.py:61-80） | — |
| **transport 安全降級** | timeout → 回空 | `test_search_transport_failure_returns_empty`（test_twinkle.py:127-133） | — |
| **failing-first 對照** | law Level A 非空 | `test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot` | 真 Grok 關鍵字抽取品質 |

### 追溯摘要

```
pyproject.toml:32  addopts="-m 'not integration'"
        │
        ▼
test_retrieve.py:102  @pytest.mark.integration
        │
        ▼
pytest core mark selector → deselect
        │
        ▼
test_retrieve.py:103  skipif(not LAW_DB.exists()) ← runtime guard
test_retrieve.py:104  skipif(not _grok_reachable()) ← runtime guard
test_retrieve.py:107  if not token: pytest.skip() ← runtime guard
        │
        ▼
correctness 路徑: Level A 排序 / vacuous blind spot / LawLookup → 被 FakeLLM+FakeLaw 測試覆蓋
```

---

## 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

### 規則追溯鏈

| 層級 | 規則位置 | 規則類型 | 觸發條件 | 預設下是否觸發 |
|---|---|---|---|---|
| **L1** | `pyproject.toml:32` | `-m 'not integration'` | item 帶 `integration=True` marker | **是** |
| **L2** | `tests/test_twinkle.py:141` | `@pytest.mark.integration` | 為測試函式標記 | 是 |
| **L3** | `tests/test_twinkle.py:145-147` | `if not token: pytest.skip()` | `TWINKLE_HUB_TOKEN` 未設定 | 否（runtime guard） |

### correctness 路徑影響

| 正確性保證 | 被排除測試驗證的內容 | 替代覆蓋 | 殘留缺口 |
|---|---|---|---|
| **Source 全文解析** | 案由+說明全文非空 | `test_search_parses_source_with_full_content`（L61-80） | — |
| **session 重用** | MCP session initialize → reuse | `test_search_reuses_mcp_session`（L107-124） | — |
| **transport 安全降級** | timeout → 回空 | `test_search_transport_failure_returns_empty`（L127-133） | — |
| **fetched_date 當日** | `fetched_date == date.today()` | `test_control_08_twinkle_parsed_source_contract` | 真 Hub 服務可用性 |

### 追溯摘要

```
pyproject.toml:32  addopts="-m 'not integration'"
        │
        ▼
test_twinkle.py:141  @pytest.mark.integration
        │
        ▼
pytest core mark selector → deselect
        │
        ▼
test_twinkle.py:145  if not token: pytest.skip() ← runtime guard
        │
        ▼
correctness 路徑: Source parse / session reuse / transport fail → 被 monkeypatch 測試覆蓋
```

---

## 整合判斷：追溯鏈完整性

| # | node ID | L1 addopts deselect | L2 marker | L3+ runtime guard | correctness 路徑替代覆蓋 | 追溯完整？ |
|---|---|---|---|---|---|---|
| 1 | test_domain::test_detect_domain_real_grok_returns_law | ✅ `pyproject.toml:32` | ✅ `test_domain.py:50` | ✅ `skipif` L51 | ✅ FakeLLM 2 + control 1 | **完整** |
| 2 | test_e2e_acceptance::test_e2e_acceptance_real | ✅ `pyproject.toml:32` | ✅ `test_e2e_acceptance.py:244` | ✅ `skip` L247,251 | ✅ 結構類 3 + control 1 | **完整** |
| 3 | test_gap::test_detect_gaps_real_grok | ✅ `pyproject.toml:32` | ✅ `test_gap.py:71` | ✅ `skipif` L72 | ✅ FakeLLM 6 + control 1 | **完整** |
| 4 | test_llm::test_grok_pong_integration | ✅ `pyproject.toml:32` | ✅ `test_llm.py:66` | ✅ `skipif` L67 | ✅ monkeypatch 1 + control 1 | **完整** |
| 5 | test_pipeline::test_run_pipeline_real_grok | ✅ `pyproject.toml:32` | ✅ `test_pipeline.py:151` | ✅ `skipif` L152 | ✅ FakeLLM 3 + correction 1 + control 1 | **完整** |
| 6 | test_questions::test_generate_questions_real_grok | ✅ `pyproject.toml:32` | ✅ `test_questions.py:62` | ✅ `skipif` L63 | ✅ FakeLLM 4 + control 1 | **完整** |
| 7 | test_retrieve::test_retrieve_for_gap_real_twinkle_smoke | ✅ `pyproject.toml:32` | ✅ `test_retrieve.py:102` | ✅ `skipif` L103,104 + `skip` L107 | ✅ FakeLLM+FakeLaw 2 + blind_spot 2 + control 2 | **完整** |
| 8 | test_twinkle::test_search_real_twinkle_hub | ✅ `pyproject.toml:32` | ✅ `test_twinkle.py:141` | ✅ `skip` L145 | ✅ monkeypatch 3 + control 1 | **完整** |

**結論**：全部 8 個 deselected node ID 的排除追溯鏈**完整可追溯**：
- **唯一 deselect 主因**：`pyproject.toml:32` 的 `-m 'not integration'`（G1）
- **所有 marker 錨點**：各測試模組中的 `@pytest.mark.integration`（L2）
- **runtime guard**：`skipif` / `pytest.skip` 在各測試模組中（L3+），屬第二層保護
- **correctness 路徑**：全部由非 integration 測試（FakeLLM / monkeypatch / stub）覆蓋
- **無 xfail、無 path pattern、無 -k 規則**參與 deselect

---

## 驗證命令

```powershell
# 確認 collection 與 deselected 清單（含原因）
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 `
  -m pytest --collect-only -q --deselected-details --color=no

# 確認無 addopts 時 8 個 integration 測試全部可見
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 `
  -m pytest --collect-only -q --color=no -o "addopts="

# 確認 guard 測試全綠
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 `
  -m pytest tests/test_deselection_guard.py -v --color=no
```

---

## 產物清單

| 檔案 | 用途 |
|---|---|
| `docs/exclusion-traceability-chain-2026-07-21.md` | 本報告（追溯鏈對照表） |
| `pyproject.toml:32` | addopts 規則位置（G1） |
| `tests/test_domain.py:50-51` | #1 marker + skipif 錨點 |
| `tests/test_e2e_acceptance.py:244-254` | #2 marker + skip 錨點 |
| `tests/test_gap.py:71-72` | #3 marker + skipif 錨點 |
| `tests/test_llm.py:66-67` | #4 marker + skipif 錨點 |
| `tests/test_pipeline.py:151-152` | #5 marker + skipif 錨點 |
| `tests/test_questions.py:62-63` | #6 marker + skipif 錨點 |
| `tests/test_retrieve.py:102-108` | #7 marker + skipif + skip 錨點 |
| `tests/test_twinkle.py:141-147` | #8 marker + skip 錨點 |
