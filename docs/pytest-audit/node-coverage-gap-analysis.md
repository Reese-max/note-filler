# 8 筆 Integration Node ID 覆蓋缺口分析

**分析日期**：2026-07-22  
**分析範圍**：`tests/deselected_allowlist.json` 前 8 筆 deselected node id  
**方法**：逐 node 比對 integration test 的驗證語義 vs. 非 integration 測試路徑（含 substitute tests + failing controls + blind spot tests）中的等價覆蓋  
**基準**：「同失敗語義、同邊界條件、同回傳值」直接覆蓋  

---

## 總覽

| # | Node ID | 非 integration 直接等價覆蓋？ | 最小缺口標記 |
|---|---------|---------------------------|-------------|
| 1 | `test_domain.py::test_detect_domain_real_grok_returns_law` | **部分** | real Grok 回應格式相容性 |
| 2 | `test_e2e_acceptance.py::test_e2e_acceptance_real` | **部分** | real model 輸出品質 + 補充寫作品質 |
| 3 | `test_gap.py::test_detect_gaps_real_grok` | **部分** | real model 覆蓋度語意判斷 |
| 4 | `test_llm.py::test_grok_pong_integration` | **部分** | real TCP 連線 + proxy 回應解析 |
| 5 | `test_pipeline.py::test_run_pipeline_real_grok` | **部分** | real model 多步驟輸出正確性 |
| 6 | `test_questions.py::test_generate_questions_real_grok` | **部分** | real model 問題品質 |
| 7 | `test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | **部分** | real Twinkle Hub I/O + Grok keyword 品質 |
| 8 | `test_twinkle.py::test_search_real_twinkle_hub` | **部分** | real Twinkle Hub 服務可用性 |

**結論**：8 筆 integration test 皆無「同失敗語義、同邊界條件、同回傳值」的**完整**直接覆蓋。離線 substitute tests 已覆蓋合約層（回傳型別、過濾邏輯、fallback 路徑、error propagation），但皆以 FakeLLM/FakeTwinkle 隔離，無法驗證真實外部依賴的行為。

---

## 逐項分析

### #1 `test_domain.py::test_detect_domain_real_grok_returns_law`

**Integration 語義**：真 GrokClient → 真 grok proxy → 明顯法律文字 → `detect_domain` 回傳 `"law"`

**非 integration 覆蓋**：
- `test_domain.py::test_detect_domain_law`（FakeLLM 回 `"law"`，驗證 `detect_domain` 合約）
- `test_domain.py::test_detect_domain_grok_error_propagates`（monkeypatch GrokClient，驗證錯誤傳播）
- `test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract`（FakeLLM 多情境：law/law./LAW/other fallback）

**覆蓋判定**：FakeLLM 驗證了 `detect_domain` 的標籤解析、strip/大小寫容忍、fallback 至 other 的合約。GrokClient 建構與 endpoint 設定由 `test_grokclient_builds_request_body` 覆蓋。

**缺口**：真 Grok 回應格式相容性。若 proxy 回應格式微調（如多包一層 JSON、content 內有額外 marker），unit test 的 monkeypatch 仍回 `"OK"` 或 `"PONG"`，無法攔截此類 proxy 側退化。離線測試無法驗證 grok proxy 的實際回應格式與 `detect_domain` 的端到端相容性。

**待補位置**：`tests/test_domain.py` — 需一筆驗證「proxy 回應格式 → `detect_domain` parse」的直接斷言，或明確標記為需 integration 執行。

---

### #2 `test_e2e_acceptance.py::test_e2e_acceptance_real`

**Integration 語義**：真 Grok + 真 Twinkle + 真 law_index.db → 端到端 pipeline → 5 項硬不變式 + `_assert_supplement_quality`

**非 integration 覆蓋**：
- `test_e2e_acceptance.py::test_e2e_structural_invariants`（FakeLLM + _StubTwinkle + LawLookup → 4 項結構不變式）
- `test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary`（同上 + `_assert_supplement_quality`）
- `test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression`（同上 + 四硬閘 + 只掛引用）
- `test_pipeline.py::test_run_pipeline_invariant`（FakeLLM + FakeTwinkle → C6 不變式 + verified 路徑）
- `test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`
- `test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`
- `test_correction.py::test_retrieved_five_but_only_two_cited`
- `test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates`

**覆蓋判定**：離線 substitute 覆蓋了原稿不可變、C6 pending_evidence、只掛引用、法條離線查核、markdown 格式、`_assert_supplement_quality` 的離線路徑。

**缺口**：real model 輸出品質 + 真實補充寫作品質。離線 `_assert_supplement_quality` 用 FakeLLM 固定回覆驗證，但真實 Grok 寫出的補充可能含無效註腳、混入原始記錄、或 Level A 路由不穩定。integration test 的 `_has_a` 有界重跑機制和 verified 資料源數量判準（`>=1 A/C 或 >=2 distinct`）離線無等價覆蓋。

**待補位置**：`tests/test_e2e_acceptance.py` — 需補「離線 verified 路徑的資料源判準完整性」斷言（`has_a or has_c or len(distinct) >= 2`），或明確標記需 integration。

---

### #3 `test_gap.py::test_detect_gaps_real_grok`

**Integration 語義**：真 GrokClient → 給法律文字 + 明顯未涵蓋題 → `detect_gaps` 回傳 partial/missing，明顯未涵蓋題出現在結果中

**非 integration 覆蓋**：
- `test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`（FakeLLM 回 JSON，驗證 covered 過濾 + Gap 結構）
- `test_gap.py::test_detect_gaps_grok_error_propagates`（錯誤傳播）
- `test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface`（FakeLLM 鎖定明顯未涵蓋題必須浮現）

**覆蓋判定**：FakeLLM 驗證了 JSON 解析、code fence 剝除、covered 過濾、fallback 全 missing、空問題 short circuit。

**缺口**：real model 覆蓋度語意判斷。若 Grok 模型升級或 prompt 格式微調，離線 FakeLLM 無法驗證「明顯未涵蓋題」是否仍被正確標記為 missing。`test_detect_gaps_real_grok_semantic_matrix`（第 9 筆 allowlist）的特定 covered/missing 邊界離線無等價。

**待補位置**：`tests/test_gap.py` — 需補「FakeLLM 回 covered 但文本中確實未涵蓋」的反向邊界測試，或明確標記需 integration。

---

### #4 `test_llm.py::test_grok_pong_integration`

**Integration 語義**：真 TCP 連線到 proxy → `GrokClient.complete` → 回應含 `"PONG"`

**非 integration 覆蓋**：
- `test_llm.py::test_grokclient_builds_request_body`（monkeypatch urlopen，驗證 request body/Bearer/POST/timeout/response parse）
- `test_llm.py::test_grokclient_urlopen_error`（URLError 傳播）
- `test_llm.py::test_grokclient_json_decode_error`（JSON 解析失敗）
- `test_llm.py::test_grokclient_malformed_response_error`（畸形回應）
- `test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract`（monkeypatch 驗證 PONG 契約 + endpoint/model 鎖定）

**覆蓋判定**：unit test 覆蓋了 GrokClient 的完整內部邏輯（建構、request body、response parse、error paths）。`test_control_04` 用 monkeypatch 驗證了 PONG 回傳契約。

**缺口**：real TCP 連線到 proxy 的連通性。monkeypatch 繞過了 `urllib.request.urlopen` 的真實 HTTP 行為，無法驗證 proxy 是否真的在 port 8318 回應、proxy 回應格式是否與 `GrokClient.complete` 相容。若 proxy crash 或 port 被佔用，離線測試仍綠。

**待補位置**：`tests/test_llm.py` — 需補「proxy 不可達時 `GrokClient` 的錯誤行為」斷言（已有 `test_grokclient_urlopen_error`，但需確認與 proxy 不可達的語義一致），或明確標記需 integration。

---

### #5 `test_pipeline.py::test_run_pipeline_real_grok`

**Integration 語義**：真 GrokClient + FakeTwinkle + FakeLaw → 完整 pipeline → 驗 C6 不變式 + 真模型至少產生一個 gap

**非 integration 覆蓋**：
- `test_pipeline.py::test_run_pipeline_invariant`（FakeLLM + FakeTwinkle → C6 + verified 路徑）
- `test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`
- `test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`
- `test_correction.py::test_retrieved_five_but_only_two_cited`
- `test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources`

**覆蓋判定**：離線 substitute 覆蓋了 C6 不變式（空源 → pending_evidence）、畸形輸出降級、law citation check、source 只掛引用。

**缺口**：real model 多步驟輸出正確性。integration test 驗證 domain/questions/gaps 三步驟在真 Grok 輸出下不炸，離線用 FakeLLM 固定回覆無法驗證。若 Grok 升級後 domain 標籤格式改變（如回 `"Law"` 而非 `"law"`），`detect_domain` 的 `strip().lower()` 可能仍通過，但 pipeline 整體穩定性離線無法驗證。

**待補位置**：`tests/test_pipeline.py` — 需補「FakeLLM 模擬多步驟 pipeline 的 domain/questions/gaps 串接」完整路徑測試，或明確標記需 integration。

---

### #6 `test_questions.py::test_generate_questions_real_grok`

**Integration 語義**：真 GrokClient → 法律文字 → `generate_questions` 回傳非空乾淨問題清單

**非 integration 覆蓋**：
- `test_questions.py::test_generate_questions_splits_multiline_string`（FakeLLM 多行切換）
- `test_questions.py::test_generate_questions_strips_and_drops_blank_lines`（strip + 空行移除）
- `test_questions.py::test_generate_questions_empty_response_returns_empty_list`（空回傳）
- `test_questions.py::test_generate_questions_calls_llm_exactly_once`（單次呼叫）
- `test_questions.py::test_generate_questions_grok_error_propagates`（錯誤傳播）
- `test_questions.py::test_generate_questions_rejects_json_shaped_response`（JSON 格式拒絕）
- `test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract`（非空 + 無 JSON 結構符）

**覆蓋判定**：FakeLLM 覆蓋了行切換、strip、空行移除、單次呼叫、JSON 拒絕、錯誤傳播。`test_control_06` 驗證了非空乾淨清單合約。

**缺口**：real model 問題品質。integration test 驗證真 Grok 對法律文字產出的問題是具體可查證的（非空、非 JSON），離線用 FakeLLM 固定回覆 `"本法的立法目的為何?\n..."` 無法驗證。若 Grok 升級後問題品質退化（如產出空行、含 JSON 括號、或完全不相關），離線測試仍綠。

**待補位置**：`tests/test_questions.py` — 需補「FakeLLM 回覆含常見 Grok 退化格式（如含 markdown 標記、空行混雜）」的邊界測試，或明確標記需 integration。

---

### #7 `test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

**Integration 語義**：真 TwinkleClient + 真 LawLookup + 真 GrokClient → `retrieve_for_gap` → 有 A/B 來源 + 排序不變式

**非 integration 覆蓋**：
- `test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B`（FakeLaw + FakeTwinkle → Level A 優先 + distance 排序）
- `test_retrieve.py::test_retrieve_for_gap_other_domain_uses_web_not_twinkle`（other 領域只走 web）
- `test_law_search.py::test_search_law_sources_returns_level_A_law_articles`（離線 law_index 查詢）
- `test_twinkle.py::test_search_parses_source_with_full_content`（mock MCP → Source 映射）
- `test_twinkle.py::test_search_reuses_mcp_session`（session header 傳遞）
- `test_twinkle.py::test_search_transport_failure_returns_empty`（timeout 降級）
- `test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot`（證明 smoke 對 empty vacuous PASS）
- `test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`（law+LawLookup 強制非空 Level A）
- `test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot`
- `test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous`

**覆蓋判定**：離線 substitute 覆蓋了 Level A/B 排序不變式、law 路由、twinkle mock 解析、transport failure 降級、vacuous pass 盲區。

**缺口**：real Twinkle Hub MCP 協議相容性 + real Grok keyword 抽取品質。mock MCP 回應是靜態 JSON，無法驗證真實 Twinkle Hub 的 SSE 解析、session 相容性、或 Grok 關鍵字抽取的正確性。若 Twinkle Hub API 協議升級，mock 仍回舊格式。

**待補位置**：`tests/test_retrieve.py` — 需補「GrokClient keyword 抽取 + law.search_articles 串接」的端到端離線測試（FakeLLM 模擬 keyword JSON → law.search_articles → 檢查 Level A 來源），或明確標記需 integration。

---

### #8 `test_twinkle.py::test_search_real_twinkle_hub`

**Integration 語義**：真 TwinkleClient.search → Twinkle Hub MCP → 回傳非空 Source 清單 + level∈A/B + content 非空 + fetched_date 當日

**非 integration 覆蓋**：
- `test_twinkle.py::test_search_parses_source_with_full_content`（mock MCP → Source 全文映射 + distance 計算）
- `test_twinkle.py::test_search_reuses_mcp_session`（session header 傳遞三次 RPC）
- `test_twinkle.py::test_search_transport_failure_returns_empty`（timeout 降級）
- `test_twinkle.py::test_search_returns_empty_without_token`（空 token → 空結果）
- `test_twinkle.py::test_search_clamps_similarity_input_to_distance_range`（similarity 邊界 clamping）
- `test_twinkle.py::test_default_timeout_is_60`
- `test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract`（mock MCP → Source 契約）

**覆蓋判定**：mock MCP 覆蓋了 SSE 解析、session reuse、全文 content 映射、distance 計算、timeout 降級、token 驗證。

**缺口**：real Twinkle Hub 服務可用性 + 真實 MCP 協議相容性。mock MCP 是靜態 `_FakeResponse`，無法驗證真實 Twinkle Hub 的 HTTP 狀態碼、MCP 協議版本相容性、或 SSE stream 格式。若 Twinkle Hub 升級 MCP 協議，mock 仍回舊格式。

**待補位置**：`tests/test_twinkle.py` — 需補「MCP protocol error（如 `isError: true`、缺少 content）」的離線邊界測試，或明確標記需 integration。

---

## 最小缺口彙總

| Node ID | 最小缺口（待補） | 建議補測類型 |
|---------|----------------|-------------|
| #1 domain | proxy 回應格式 → detect_domain parse 相容性 | 離線：monkeypatch GrokClient 回含雜訊的 JSON content |
| #2 e2e | verified 路徑資料源判準（A/C/distinct）離線完整性 | 離線：_StubTwinkle 回多種 level 組合 + 斷言 A/C/distinct 邏輯 |
| #3 gap | FakeLLM 模擬「明顯 covered 但回 missing」的反向邊界 | 離線：FakeLLM 回 covered 結果但問題確實不在文本中 |
| #4 llm | proxy 不可達 → GrokClient 錯誤行為（已有 urlopen_error） | **已覆蓋**（test_grokclient_urlopen_error 語義等價） |
| #5 pipeline | 多步驟 pipeline 的 domain/questions/gaps 串接離線完整路徑 | 離線：FakeLLM 模擬完整 pipeline 串接（已有 test_run_pipeline_invariant，缺口較小） |
| #6 questions | Grok 退化格式（markdown 標記、空行混雜）的邊界 | 離線：FakeLLM 回含 ```markdown``` 或空行混雜的回覆 |
| #7 retrieve | GrokClient keyword → law.search_articles 串接離線路徑 | 離線：FakeLLM 模擬 keyword JSON + FakeLaw 驗證 Level A 來源 |
| #8 twinkle | MCP protocol error（isError、缺少 content）的離線邊界 | 離線：mock MCP 回 `{"error": ...}` 或空 content |

---

## 判定

8 筆 deselected integration test 中：
- **#4 llm**（PONG 契約）的離線 substitute 已達「同失敗語義」直接覆蓋（monkeypatch urlopen → 驗證 endpoint + response parse + PONG 回傳），缺口最小。
- **#5 pipeline**（C6 不變式）的離線 substitute 已覆蓋核心合約，缺口僅在 real model 多步驟穩定性。
- 其餘 6 筆的離線 substitute 覆蓋了合約層但未覆蓋 real model/service 的輸出品質與協議相容性。

所有缺口皆為「real model/service 行為驗證」類型，無法在離線環境以 FakeLLM/FakeTwinkle 完全替代，需由 integration 執行（CI workflow_dispatch 或本地手動）補足。
