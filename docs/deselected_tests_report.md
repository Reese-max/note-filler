# Deselected Tests 報告

> 產生方式：`pytest --co -q -m "integration"` 收集 + 原始碼 marker/ skipif/ pytest.skip 稽核
> 產生日期：2026-07-18

## 總覽

| 總測試數 | 預設執行 | Deselected |
|---------|---------|-----------|
| 112 | 104 | 8 |

所有 8 個 deselected 測試皆帶有 `@pytest.mark.integration` marker，被 `pyproject.toml` 的 `addopts` 預設選取條件 `-m 'not integration'` 排除。

## Deselected 測試清單

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 項目 | 內容 |
|------|------|
| **Marker** | `@pytest.mark.integration` |
| **選取排除** | `pyproject.toml` → `addopts = "-m 'not integration'"` 於 collection 階段 deselect |
| **Runtime skip** | `@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")` |
| **skip 條件** | `socket.create_connection(("127.0.0.1", 8318), timeout=1.0)` 失敗 → `OSError` → `False` |
| **覆蓋函數** | `note_filler.domain.detect_domain` — LLM 領域偵測 (law/admin/exam/other) |
| **替代測試** | `test_domain.py::test_detect_domain_law` |
| **覆蓋缺口** | 真 grok 對法律文字的實際回應正確性 |

### 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 項目 | 內容 |
|------|------|
| **Marker** | `@pytest.mark.integration` |
| **選取排除** | `pyproject.toml` → `addopts = "-m 'not integration'"` 於 collection 階段 deselect |
| **Runtime skip** | 函數體內三重 `pytest.skip()` 條件：(1) `data/law_index.db` 不存在 → `"缺 data/law_index.db"`；(2) `_grok_up()` 為 `False`（TCP port 8318 不通）；(3) `_twinkle_ready()` 為 `False`（`TWINKLE_HUB_TOKEN` 未設定） |
| **覆蓋函數** | §12 端到端驗收: parse→domain→questions→gaps→retrieve→assemble→export; 5 個硬不變式 |
| **替代測試** | `test_e2e_acceptance.py::test_e2e_structural_invariants`、`test_pipeline.py::test_run_pipeline_invariant`、`test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`、`test_correction.py::test_retrieved_five_but_only_two_cited` |
| **覆蓋缺口** | 真模型+真檢索下的 gap 偵測品質、補充寫作品質、Level A 路由穩定性 |

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`

| 項目 | 內容 |
|------|------|
| **Marker** | `@pytest.mark.integration` |
| **選取排除** | `pyproject.toml` → `addopts = "-m 'not integration'"` 於 collection 階段 deselect |
| **Runtime skip** | `@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")` |
| **skip 條件** | `socket.create_connection(("127.0.0.1", 8318), timeout=1.0)` 失敗 → `OSError` → `False` |
| **覆蓋函數** | `note_filler.gap.detect_gaps` — LLM 缺口偵測 (partial/missing 過濾) |
| **替代測試** | `test_gap.py::test_detect_gaps_keeps_only_partial_and_missing` |
| **覆蓋缺口** | 真 grok 對法律文本的缺口判斷品質 |

### 4. `tests/test_llm.py::test_grok_pong_integration`

| 項目 | 內容 |
|------|------|
| **Marker** | `@pytest.mark.integration` |
| **選取排除** | `pyproject.toml` → `addopts = "-m 'not integration'"` 於 collection 階段 deselect |
| **Runtime skip** | `@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")` |
| **skip 條件** | `socket.create_connection(("127.0.0.1", 8318), timeout=1.0)` 失敗 → `OSError` → `False` |
| **覆蓋函數** | `note_filler.llm.GrokClient.complete` — 真實 HTTP 連線 + 回應解析 |
| **替代測試** | `test_llm.py::test_grokclient_builds_request_body` |
| **覆蓋缺口** | 真實 TCP 連線到 proxy 的連通性、proxy 回應格式解析 |

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 項目 | 內容 |
|------|------|
| **Marker** | `@pytest.mark.integration` |
| **選取排除** | `pyproject.toml` → `addopts = "-m 'not integration'"` 於 collection 階段 deselect |
| **Runtime skip** | 無（twinkle/law 用 `FakeTwinkle`/`FakeLaw` 隔離，僅 grok 依賴真 proxy） |
| **覆蓋函數** | `note_filler.pipeline.run_pipeline` — 完整 pipeline 在真 Grok 輸出下不炸 + C6 不變式 |
| **替代測試** | `test_pipeline.py::test_run_pipeline_invariant`、`test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`、`test_correction.py::test_retrieved_five_but_only_two_cited` |
| **覆蓋缺口** | 真 Grok 模型輸出的 domain/questions/gaps 正確性 + pipeline 穩定性 |

### 6. `tests/test_questions.py::test_generate_questions_real_grok`

| 項目 | 內容 |
|------|------|
| **Marker** | `@pytest.mark.integration` |
| **選取排除** | `pyproject.toml` → `addopts = "-m 'not integration'"` 於 collection 階段 deselect |
| **Runtime skip** | `@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")` |
| **skip 條件** | `socket.create_connection(("127.0.0.1", 8318), timeout=1.0)` 失敗 → `OSError` → `False` |
| **覆蓋函數** | `note_filler.questions.generate_questions` — 真模型問題生成格式與品質 |
| **替代測試** | `test_questions.py::test_generate_questions_splits_multiline_string`、`test_questions.py::test_generate_questions_strips_and_drops_blank_lines` |
| **覆蓋缺口** | 真 Grok 對法律文本的問題生成品質 |

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 項目 | 內容 |
|------|------|
| **Marker** | `@pytest.mark.integration` |
| **選取排除** | `pyproject.toml` → `addopts = "-m 'not integration'"` 於 collection 階段 deselect |
| **Runtime skip** | 函數體內 `pytest.skip("需 GOV_AI_ENABLE_TWINKLE_MCP=1 且設 TWINKLE_HUB_TOKEN")` |
| **skip 條件** | `os.environ.get("GOV_AI_ENABLE_TWINKLE_MCP") != "1"` 或 `os.environ.get("TWINKLE_HUB_TOKEN")` 為 falsy |
| **覆蓋函數** | `note_filler.retrieve.retrieve_for_gap` — 真實 Twinkle Hub MCP + LawLookup + Grok keyword + 排序不變式 |
| **替代測試** | `test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B`、`test_law_search.py::test_search_law_sources_returns_level_A_law_articles`、`test_twinkle.py::test_search_parses_source_with_full_content` |
| **覆蓋缺口** | 真實 Twinkle Hub 服務 I/O 與真 Grok 關鍵字抽取品質 |

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 項目 | 內容 |
|------|------|
| **Marker** | `@pytest.mark.integration` |
| **選取排除** | `pyproject.toml` → `addopts = "-m 'not integration'"` 於 collection 階段 deselect |
| **Runtime skip** | 函數體內 `pytest.skip("未設定 TWINKLE_HUB_TOKEN,跳過 twinkle-hub 真打整合測試")` |
| **skip 條件** | `os.environ.get("TWINKLE_HUB_TOKEN", "")` 為空字串（未設定或空值） |
| **覆蓋函數** | `note_filler.retrieve.twinkle.TwinkleClient.search` — 真實 Twinkle Hub MCP 搜尋 |
| **替代測試** | `test_twinkle.py::test_search_parses_source_with_full_content` |
| **覆蓋缺口** | 真實 Twinkle Hub 服務可用性、服務端 session 相容性與網路逾時 |

## 排除機制彙整

| 排除層級 | 機制 | 設定位置 |
|----------|------|----------|
| **L1: Collection 階段** | `addopts = "-m 'not integration'"` → pytest collection 時 deselect 所有 `@pytest.mark.integration` 測試 | `pyproject.toml` `[tool.pytest.ini_options]` |
| **L2: Runtime skipif** | `@pytest.mark.skipif(not _grok_reachable(), ...)` → TCP port 8318 連線失敗則 skip | 4 個測試（domain/gap/llm/questions） |
| **L3: Runtime pytest.skip** | 函數體內依環境變數 / 檔案存在與否動態 skip | 4 個測試（e2e/pipeline 用 grok_up+twinkle_ready+law_db; retrieve 用 GOV_AI_ENABLE_TWINKLE_MCP+TWINKLE_HUB_TOKEN; twinkle 用 TWINKLE_HUB_TOKEN） |
| **L4: CI 隔離** | CI 的 push/PR jobs 僅跑 `-m "not integration"`；整合測試僅 `workflow_dispatch` 手動觸發 | `.github/workflows/ci.yml` |

## 所需環境條件

| 條件 | 涉及測試 | 檢查方式 |
|------|---------|---------|
| Grok proxy (`127.0.0.1:8318`) TCP 連通 | 1-6 | `socket.create_connection(("127.0.0.1", 8318), timeout=1)` |
| `TWINKLE_HUB_TOKEN` 環境變數 | 2, 7, 8 | `os.environ.get("TWINKLE_HUB_TOKEN")` |
| `GOV_AI_ENABLE_TWINKLE_MCP=1` 環境變數 | 7 | `os.environ.get("GOV_AI_ENABLE_TWINKLE_MCP")` |
| `data/law_index.db` 檔案存在 | 2 | `Path("data/law_index.db").exists()` |
