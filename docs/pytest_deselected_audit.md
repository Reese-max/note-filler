# pytest deselected 整合測試對照清單

> 自動產生日期：2026-07-18
> deselection 機制：`pyproject.toml` addopts `-m 'not integration'`
> guard 來源：`tests/test_deselection_guard.py` + `tests/deselected_allowlist.json`
> 共 8 項 deselected 測試

## JSON 格式（機器可讀）

機器可讀版：`tests/deselected_allowlist.json`

## 覆蓋定位映射表

判定原則：只列入與被排除案例共用相同 production 入口、且斷言重疊的非 integration 案例；外部服務可用性與模型品質不假裝為離線可等價驗證，仍由原 integration 案例保留。

| 被排除案例 | 已實際執行的非 integration 案例 | 相同情境覆蓋定位 | 僅 integration 可驗證的邊界 |
|---|---|---|---|
| `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `tests/test_domain.py::test_detect_domain_law` | 同一 `detect_domain()` 入口與 `law` 回傳契約 | 真 Grok 對法律文字的分類品質 |
| `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py::test_e2e_structural_invariants`<br>`tests/test_pipeline.py::test_run_pipeline_invariant`<br>`tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`<br>`tests/test_correction.py::test_retrieved_five_but_only_two_cited` | 同一 pipeline；原稿逐字不可變、無來源→`pending_evidence`、法條離線查核、輸出契約、只掛實際引用來源 | 真模型與真檢索的 gap、寫作與 Level A 路由品質 |
| `tests/test_gap.py::test_detect_gaps_real_grok` | `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing` | 同一 `detect_gaps()` 入口；`Gap` 型別與 partial/missing 過濾 | 真 Grok 對法律文本的缺口語意判斷 |
| `tests/test_llm.py::test_grok_pong_integration` | `tests/test_llm.py::test_grokclient_builds_request_body` | 同一 `GrokClient.complete()`；URL、POST、授權、body、timeout 與回應解析 | proxy TCP 連線與真實回應格式 |
| `tests/test_pipeline.py::test_run_pipeline_real_grok` | `tests/test_pipeline.py::test_run_pipeline_invariant`<br>`tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`<br>`tests/test_correction.py::test_retrieved_five_but_only_two_cited` | 同一 `run_pipeline()` 主路徑；C6、法條查核與引用來源篩選 | 真 Grok 輸出下的穩定性與語意品質 |
| `tests/test_questions.py::test_generate_questions_real_grok` | `tests/test_questions.py::test_generate_questions_splits_multiline_string`<br>`tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines` | 同一 `generate_questions()`；`list[str]`、逐行切分、淨空行 | 真 Grok 問題相關性與法律正確性 |
| `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B`<br>`tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles`<br>`tests/test_twinkle.py::test_search_parses_source_with_full_content` | 同一 law 檢索路徑；真離線 LawLookup、A/B `Source`、`(rank, distance)` 排序、JSON-RPC/SSE 解析 | 真 Twinkle Hub I/O 與真 Grok 關鍵字抽取品質 |
| `tests/test_twinkle.py::test_search_real_twinkle_hub` | `tests/test_twinkle.py::test_search_parses_source_with_full_content` | 同一 `TwinkleClient.search()`；session、JSON-RPC/SSE、全文 `Source`、日期與 distance | 真實服務可用性、服務端 session 相容性與網路逾時 |

### 實跑證據（2026-07-18）

從 `tests/deselected_allowlist.json[*].substitute_tests` 取不重複 node ID，以主專案 venv 實際執行：

```text
MAPPED_TESTS=12
............                                                             [100%]
12 passed in 0.24s
```

永久 guard：`tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable` 會確認 8 項排除案例均有映射，且映射到的 node ID 實際存在於 `-m "not integration"` 集合。本次實跑該 guard 結果為 `2 passed in 1.75s`。

完整預設品質門 `python -X utf8 -m pytest -m "not integration" -q` 結果為 `104 passed, 8 deselected in 2.02s`。

## 逐項清單

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `@pytest.mark.skipif(not _grok_reachable())` — 需真實 grok proxy(127.0.0.1:8318) |
| **覆蓋功能點** | `note_filler.domain.detect_domain()` — LLM 領域偵測（law/admin/exam/other），真模型下法律文字回傳 "law" |
| **替代測試證據** | `tests/test_domain.py::test_detect_domain_law` — 同一入口與 `law` 回傳契約；以 FakeLLM 固定模型回應 |
| **缺失覆蓋** | 真 grok 對法律文字的實際回應正確性（FakeLLM 只驗邏輯，不驗模型品質） |

---

### 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` — 需真實 grok + Twinkle Hub + law_index.db；`pytest.skip()` 條件含 `_grok_up()` 及 `_twinkle_ready()` |
| **覆蓋功能點** | §12 全端到端驗收：parse → domain → questions → gaps → retrieve(Grok+Twinkle+LawDB) → assemble → export(markdown/json)；驗證 5 個硬不變式：(1)原稿逐字不可變 (2)無來源閘+pending_evidence (3)交叉驗證 verified (4)法條引用真實 (5)to_markdown 格式合約 |
| **替代測試證據** | `tests/test_e2e_acceptance.py::test_e2e_structural_invariants` — 離線版：用 FakeLLM + _StubTwinkle 驗同一 4 個結構不變式(§12(1)(2)(4)(5)) |
| | `tests/test_pipeline.py::test_run_pipeline_invariant` — pipeline 層級：FakeLLM + FakeTwinkle 驗 C6 不變式 + verified 判準 |
| | `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check` — 法律領域法規引用檢查呼叫 |
| | `tests/test_correction.py::test_retrieved_five_but_only_two_cited` — 只掛實際引用來源 |
| **缺失覆蓋** | 真模型+真檢索下的 gap 偵測品質、補充寫作品質（`_assert_supplement_quality`）、Level A 路由在真 Grok 下的穩定性 |

---

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `@pytest.mark.skipif(not _grok_reachable())` — 需真實 grok proxy |
| **覆蓋功能點** | `note_filler.gap.detect_gaps()` — LLM 缺口偵測：給筆記+問題清單，回傳 partial/missing 缺口清單 |
| **替代測試證據** | `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing` — 同一入口、Gap 型別與 partial/missing 過濾契約 |
| **缺失覆蓋** | 真 grok 對法律文本的缺口判斷品質（ FakeLLM 不驗模型理解能力） |

---

### 4. `tests/test_llm.py::test_grok_pong_integration`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `@pytest.mark.skipif(not _grok_reachable())` — 需真實 grok proxy |
| **覆蓋功能點** | `note_filler.llm.GrokClient.complete()` — 真實 HTTP 連線到 grok proxy，基本連通性 + 回應解析 |
| **替代測試證據** | `tests/test_llm.py::test_grokclient_builds_request_body` — 同一 `GrokClient.complete()`；monkeypatch transport 驗請求結構與回應解析 |
| **缺失覆蓋** | 真實 TCP 連線到 proxy 的連通性、proxy 回應格式解析（monkeypatch 只驗請求構造，不驗真實 I/O） |

---

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` — 需真實 grok proxy；twinkle/law 用 FakeTwinkle/FakeLaw 隔離 |
| **覆蓋功能點** | `note_filler.pipeline.run_pipeline()` — 完整 pipeline(parse→domain→questions→gaps→assemble)在真 Grok 模型輸出下不炸；驗證 C6 不變式（無源補充 → pending_evidence） |
| **替代測試證據** | `tests/test_pipeline.py::test_run_pipeline_invariant` — 全 Fake 環境驗 pipeline 不變式（C6 + verified 判準 + twinkle 呼叫次數） |
| | `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check` — 法律領域法規引用檢查 |
| | `tests/test_correction.py::test_retrieved_five_but_only_two_cited` — 組裝層只掛實際引用來源 |
| **缺失覆蓋** | 真 Grok 模型輸出的 domain 判斷正確性、問題生成品質、缺口偵測品質；pipeline 在真模型下的端到端穩定性 |

---

### 6. `tests/test_questions.py::test_generate_questions_real_grok`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `@pytest.mark.skipif(not _grok_reachable())` — 需真實 grok proxy |
| **覆蓋功能點** | `note_filler.questions.generate_questions()` — 真模型下從筆記內容生成問題清單：格式（換行分隔、無 JSON 殘留）、數量（>=1）、型別（str） |
| **替代測試證據** | `tests/test_questions.py::test_generate_questions_splits_multiline_string` — 同一入口，驗 list/str 型別與逐行解析 |
| | `tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines` — 同一輸出清理契約 |
| **缺失覆蓋** | 真 Grok 對法律文本的問題生成品質（問題相關性、法律正確性） |

---

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `pytest.skip()` 條件：需 `GOV_AI_ENABLE_TWINKLE_MCP=1` + `TWINKLE_HUB_TOKEN` + `data/law_index.db` + Grok |
| **覆蓋功能點** | `note_filler.retrieve.retrieve_for_gap()` — 真實 Twinkle Hub MCP 檢索 + LawLookup DB 查詢 + Grok keyword 抽取；驗證 Source 型別正確、level 僅 A/B、排序不變式(rank,distance 升序) |
| **替代測試證據** | `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B` — 同一 law 路徑，驗 A/B 型別與 `(rank, distance)` 排序 |
| | `tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles` — 真離線 LawLookup DB 查詢與 Level A Source 組裝 |
| | `tests/test_twinkle.py::test_search_parses_source_with_full_content` — 模擬 JSON-RPC/SSE transport，驗 Level B Source 組裝 |
| **缺失覆蓋** | 真實 Twinkle Hub 服務 I/O 與真 Grok 關鍵字抽取品質 |

---

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `pytest.skip()` 條件：需 `TWINKLE_HUB_TOKEN` 環境變數 |
| **覆蓋功能點** | `note_filler.retrieve.twinkle.TwinkleClient.search()` — 真實 Twinkle Hub MCP 搜尋：JSON-RPC 連線 → SSE 解析 → Source 物件組裝 |
| **替代測試證據** | `tests/test_twinkle.py::test_search_parses_source_with_full_content` — 同一 `TwinkleClient.search()`；模擬 session、JSON-RPC/SSE、Source 全文與日期 |
| **缺失覆蓋** | 真實 Twinkle Hub 服務可用性、服務端 session 相容性與網路逾時 |

---

## 穩定性控制

- `tests/test_deselection_guard.py::test_integration_allowlist_is_stable`：運行時比對 `pytest --collect-only -m integration` 與 `ALLOWED_INTEGRATION_TESTS`，不符即 fail。
- `tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable`：逐項確認映射非空，且所有替代 node ID 均可由預設測試集合收集。
- 多數整合測試另附 `skipif`/`skip` 條件（grok_reachable、TWINKLE_HUB_TOKEN、law_index.db），作為 defense-in-depth。
