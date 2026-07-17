# pytest deselected 整合測試對照清單

> 自動產生日期：2026-07-18
> deselection 機制：`pyproject.toml` addopts `-m 'not integration'`
> guard 來源：`tests/test_deselection_guard.py` ALLOWED_INTEGRATION_TESTS
> 共 8 項 deselected 測試

## JSON 格式（機器可讀）

機器可讀版：`tests/deselected_allowlist.json`

## 逐項清單

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `@pytest.mark.skipif(not _grok_reachable())` — 需真實 grok proxy(127.0.0.1:8318) |
| **覆蓋功能點** | `note_filler.domain.detect_domain()` — LLM 領域偵測（law/admin/exam/other），真模型下法律文字回傳 "law" |
| **替代測試證據** | `tests/test_domain.py::test_detect_domain_law` — 用 FakeLLM 驗 same 功能邏輯 |
| | `tests/test_domain.py::test_detect_domain_admin` — FakeLLM admin 路徑 |
| | `tests/test_domain.py::test_detect_domain_exam` — FakeLLM exam 路徑 |
| | `tests/test_domain.py::test_detect_domain_noise_falls_back_to_other` — fallback 邏輯 |
| | `tests/test_domain.py::test_detect_domain_label_with_trailing_punctuation` — 雜訊容忍 |
| | `tests/test_domain.py::test_detect_domain_uppercase_and_whitespace` — 大小寫容忍 |
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
| **缺失覆蓋** | 真模型+真檢索下的 gap 偵測品質、補充寫作品質（`_assert_supplement_quality`）、Level A 路由在真 Grok 下的穩定性 |

---

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `@pytest.mark.skipif(not _grok_reachable())` — 需真實 grok proxy |
| **覆蓋功能點** | `note_filler.gap.detect_gaps()` — LLM 缺口偵測：給筆記+問題清單，回傳 partial/missing 缺口清單 |
| **替代測試證據** | `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing` — FakeLLM 驗 covered 濾除 + 結構 |
| | `tests/test_gap.py::test_detect_gaps_calls_llm_exactly_once` — 呼叫次數 |
| | `tests/test_gap.py::test_detect_gaps_parse_failure_marks_all_missing` — JSON 解析失敗 fallback |
| | `tests/test_gap.py::test_detect_gaps_non_array_json_also_fallbacks` — dict 回傳 fallback |
| | `tests/test_gap.py::test_detect_gaps_strips_code_fence` — code fence 剝除 |
| | `tests/test_gap.py::test_detect_gaps_empty_questions_short_circuits` — 空輸入短路 |
| **缺失覆蓋** | 真 grok 對法律文本的缺口判斷品質（ FakeLLM 不驗模型理解能力） |

---

### 4. `tests/test_llm.py::test_grok_pong_integration`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `@pytest.mark.skipif(not _grok_reachable())` — 需真實 grok proxy |
| **覆蓋功能點** | `note_filler.llm.GrokClient.complete()` — 真實 HTTP 連線到 grok proxy，基本連通性 + 回應解析 |
| **替代測試證據** | `tests/test_llm.py::test_fakellm_returns_canned_in_order` — FakeLLM 呼叫順序 |
| | `tests/test_llm.py::test_grokclient_builds_request_body` — monkeypatch urlopen 驗 GrokClient 請求結構(url/method/auth/body/timeout) |
| **缺失覆蓋** | 真實 TCP 連線到 proxy 的連通性、proxy 回應格式解析（monkeypatch 只驗請求構造，不驗真實 I/O） |

---

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` — 需真實 grok proxy；twinkle/law 用 FakeTwinkle/FakeLaw 隔離 |
| **覆蓋功能點** | `note_filler.pipeline.run_pipeline()` — 完整 pipeline(parse→domain→questions→gaps→assemble)在真 Grok 模型輸出下不炸；驗證 C6 不變式（無源補充 → pending_evidence） |
| **替代測試證據** | `tests/test_pipeline.py::test_run_pipeline_invariant` — 全 Fake 環境驗 pipeline 不變式（C6 + verified 判準 + twinkle 呼叫次數） |
| | `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check` — 法律領域法規引用檢查 |
| **缺失覆蓋** | 真 Grok 模型輸出的 domain 判斷正確性、問題生成品質、缺口偵測品質；pipeline 在真模型下的端到端穩定性 |

---

### 6. `tests/test_questions.py::test_generate_questions_real_grok`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `@pytest.mark.skipif(not _grok_reachable())` — 需真實 grok proxy |
| **覆蓋功能點** | `note_filler.questions.generate_questions()` — 真模型下從筆記內容生成問題清單：格式（換行分隔、無 JSON 殘留）、數量（>=1）、型別（str） |
| **替代測試證據** | `tests/test_questions.py::test_generate_questions_splits_multiline_string` — FakeLLM 驗換行分割 |
| | `tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines` — 空行過濾 |
| | `tests/test_questions.py::test_generate_questions_empty_response_returns_empty_list` — 空回傳 |
| | `tests/test_questions.py::test_generate_questions_calls_llm_exactly_once` — 呼叫次數 |
| **缺失覆蓋** | 真 Grok 對法律文本的問題生成品質（問題相關性、法律正確性） |

---

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `pytest.skip()` 條件：需 `GOV_AI_ENABLE_TWINKLE_MCP=1` + `TWINKLE_HUB_TOKEN` + `data/law_index.db` + Grok |
| **覆蓋功能點** | `note_filler.retrieve.retrieve_for_gap()` — 真實 Twinkle Hub MCP 檢索 + LawLookup DB 查詢 + Grok keyword 抽取；驗證 Source 型別正確、level 僅 A/B、排序不變式(rank,distance 升序) |
| **替代測試證據** | `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B` — FakeTwinkle+FakeLaw 驗 Level A 排序壓過 B + distance 升序 + 呼叫參數 |
| | `tests/test_retrieve.py::test_retrieve_for_gap_other_domain_uses_web_not_twinkle` — other 領域走 web 不走 twinkle |
| **缺失覆蓋** | 真實 Twinkle Hub MCP 連線 + JSON-RPC 協議 + SSE 解析（`test_twinkle.py` 的 FakeResponse 覆蓋協議格式，但非真實 I/O） |

---

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 欄位 | 值 |
|---|---|
| **排除原因** | `@pytest.mark.integration` + `pytest.skip()` 條件：需 `TWINKLE_HUB_TOKEN` 環境變數 |
| **覆蓋功能點** | `note_filler.retrieve.twinkle.TwinkleClient.search()` — 真實 Twinkle Hub MCP 搜尋：JSON-RPC 連線 → SSE 解析 → Source 物件組裝 |
| **替代測試證據** | `tests/test_twinkle.py::test_search_parses_source_with_full_content` — monkeypatch urlopen 驗 SSE 解析+Source 組裝+distance 計算+全文 content |
| | `tests/test_twinkle.py::test_search_returns_empty_without_token` — 空 token 回空 |
| | `tests/test_twinkle.py::test_default_timeout_is_60` — 預設逾時 |
| **缺失覆蓋** | 真實 Twinkle Hub 服務可用性、MCP session 建立、網路逾時處理 |

---

## 穩定性控制

- `tests/test_deselection_guard.py::test_integration_allowlist_is_stable`：運行時比對 `pytest --collect-only -m integration` 與 `ALLOWED_INTEGRATION_TESTS`，不符即 fail。
- 多數整合測試另附 `skipif`/`skip` 條件（grok_reachable、TWINKLE_HUB_TOKEN、law_index.db），作為 defense-in-depth。
