# Deselected 8：替代測試覆蓋缺口分析

**日期**：2026-07-28
**分析對象**：`tests/deselected_allowlist.json` 前 8 筆（integration 測試被 `-m 'not integration'` 排除）
**目的**：逐一比對 substitute_tests 與 correctness 測試，找出「功能路徑或邊界條件只被同組其他測試覆蓋、但未被任何現有離線測試直接覆蓋」的最小缺口

---

## 方法

1. 從 `deselected_allowlist.json` 擷取 8 個 deselected 測試的 `covered_function`、`substitute_tests`、`coverage_gap`
2. 實際讀取每個 substitute test 與同組 sibling test，驗證其**覆蓋的代碼路徑**與**覆蓋的邊界條件**
3. 對照 deselected 測試的「真實模型/真實服務」功能路徑，標出離線測試無法覆蓋的最小缺口

---

## 逐項分析

### #1 `test_domain.py::test_detect_domain_real_grok_returns_law`

| 維度 | Deselected 測試 | Substitute 測試 | 差異 |
|---|---|---|---|
| **功能路徑** | 真 Grok 對刑法文字回 `law` | FakeLLM 回 `law` → 驗證標籤解析 | 路徑相同（detect_domain → LLM → parse → return），但 LLM 實體不同 |
| **邊界條件** | 真模型語意判斷正確性 | label strip/casefold/fallback/error propagation | **缺口：真模型分類品質** |
| **覆蓋的兄弟測試** | — | `test_detect_domain_law`（FakeLLM）、`test_detect_domain_noise_falls_back_to_other`（fallback）、`control_01`（label contract） | — |

**缺口判定**：離線 substitute 覆蓋了**標籤解析邏輯的所有邊界**（strip、casefold、fallback、error），唯一缺口是**真 Grok 對法律文字的語意分類品質**。此缺口無法用離線測試補償。

**最小缺口位置**：`tests/test_domain.py` — 無離線測試可取代，僅 `test_domain.py:52` 的 integration test 覆蓋真模型路徑。

---

### #2 `test_e2e_acceptance.py::test_e2e_acceptance_real`

| 維度 | Deselected 測試 | Substitute 測試 | 差異 |
|---|---|---|---|
| **功能路徑** | 真 Grok + 真 Twinkle + 真 LawLookup 端到端 | FakeLLM + StubTwinkle + 真 LawLookup（離線） | 路徑結構相同，但 LLM 輸出品質不同 |
| **邊界條件** | §12 全部 5 個不變式 + supplement quality | `_assert_immutable_original`、`_assert_no_source_gate`、`_assert_law_citations_ok`、`_assert_markdown_contract`、`_assert_supplement_quality` | **覆蓋完整**：離線 substitute 覆蓋全部結構不變式 |
| **覆蓋的兄弟測試** | — | `test_e2e_structural_invariants`（離線結構）、`test_e2e_minimal_quality_gates_offline_regression`（離線閘門）、`test_pipeline.py::test_run_pipeline_invariant`（C6）、`test_correction.py::test_retrieved_five_but_only_two_cited`（引用過濾）、`control_02`（failing-first） | — |

**缺口判定**：離線 substitute **已覆蓋全部 5 個結構不變式與 supplement quality 邊界**。唯一缺口是：(1) 真模型寫作品質（`_assert_supplement_quality` 在離線模式下是 NOT-REPRODUCIBLE boundary）；(2) 真 Twinkle 服務的 I/O 穩定性。

**最小缺口位置**：`tests/test_e2e_acceptance.py:303` — 離線 substitute 在 `test_e2e_structural_invariants:174` 已覆蓋結構路徑；真模型品質缺口無法離線補償。

---

### #3 `test_gap.py::test_detect_gaps_real_grok`

| 維度 | Deselected 測試 | Substitute 測試 | 差異 |
|---|---|---|---|
| **功能路徑** | 真 Grok 判斷法律文本涵蓋度 | FakeLLM 回 `covered/partial/missing` JSON → 驗證過濾 | 路徑相同（detect_gaps → LLM → parse → filter） |
| **邊界條件** | 真模型語意判斷（covered vs missing） | 過濾邏輯、JSON parse、code fence strip、empty questions、error propagation | **缺口：真模型涵蓋度判斷品質** |
| **覆蓋的兄弟測試** | — | `test_detect_gaps_keeps_only_partial_and_missing`（過濾）、`test_detect_gaps_parse_failure_marks_all_missing`（fallback）、`control_03`（failing-first） | — |

**缺口判定**：離線 substitute 覆蓋了**解析與過濾的所有邊界**（含畸形 JSON fallback），唯一缺口是**真模型對法律文本的涵蓋度語意判斷**。

**最小缺口位置**：`tests/test_gap.py:73` — 離線 substitute 在 `test_gap.py:26` 已覆蓋解析路徑；語意品質缺口無法離線補償。

---

### #4 `test_llm.py::test_grok_pong_integration`

| 維度 | Deselected 測試 | Substitute 測試 | 差異 |
|---|---|---|---|
| **功能路徑** | 真實 TCP 連線到 proxy → PONG | monkeypatch `urlopen` → 驗證 request body + 解析 response | **路徑不同**：substitute 跳過了真實網路 I/O |
| **邊界條件** | proxy 連通性 + 回應格式相容性 | endpoint URL、auth header、body shape、timeout、response parse、URLError/JSONDecode/error propagation | **覆蓋完整**：離線 substitute 覆蓋了 `GrokClient.complete()` 的所有代碼分支（建構 → 呼叫 → 解析 → 錯誤） |
| **覆蓋的兄弟測試** | — | `test_grokclient_builds_request_body`（request 建構）、`test_grokclient_urlopen_error`（網路錯誤）、`test_grokclient_json_decode_error`（格式）、`test_grokclient_malformed_response_error`（結構）、`control_04`（PONG contract） | — |

**缺口判定**：離線 substitute **已覆蓋 `GrokClient.complete()` 的全部代碼路徑與邊界**。唯一缺口是**真實 TCP 連線到 proxy port 8318 的連通性**——這是基礎設施層級驗證，非功能邏輯缺口。

**最小缺口位置**：`tests/test_llm.py:95` — 離線 substitute 在 `test_llm.py:54` 已覆蓋完整 request/response 邏輯；TCP 連通性缺口無法用離線測試補償。

---

### #5 `test_pipeline.py::test_run_pipeline_real_grok`

| 維度 | Deselected 測試 | Substitute 測試 | 差異 |
|---|---|---|---|
| **功能路徑** | 真 Grok 輸出下完整 pipeline | FakeLLM + FakeTwinkle 驗證 C6 | 路徑結構相同，但 LLM 輸出品質不同 |
| **邊界條件** | 真模型 domain/questions/gaps 正確性 + C6 不變式 | C6 invariant（pending_evidence/verified）、malformed gap fallback、law citation check、original text immutability | **覆蓋完整**：離線 substitute 覆蓋了 pipeline 的所有代碼分支 |
| **覆蓋的兄弟測試** | — | `test_run_pipeline_invariant`（C6）、`test_run_pipeline_malformed_gap_output_falls_back_to_pending`（fallback）、`test_run_pipeline_law_domain_runs_citation_check`（citation gate）、`test_original_text_immutable_in_output`（immutability）、`control_05`（C6 failing-first） | — |

**缺口判定**：離線 substitute **已覆蓋 pipeline 的所有代碼分支與不變式**。唯一缺口是**真 Grok 模型輸出的 domain/questions/gaps 正確性**——模型品質缺口無法離線補償。

**最小缺口位置**：`tests/test_pipeline.py:190` — 離線 substitute 在 `test_pipeline.py:85` 已覆蓋完整 pipeline 邏輯。

---

### #6 `test_questions.py::test_generate_questions_real_grok`

| 維度 | Deselected 測試 | Substitute 測試 | 差異 |
|---|---|---|---|
| **功能路徑** | 真 Grok 對法律文本生成問題 | FakeLLM 回多行文字 → 驗證解析 | 路徑相同（generate_questions → LLM → split → filter） |
| **邊界條件** | 真模型問題生成品質 | multiline split、blank-line strip、JSON rejection、markdown fence strip、single-call invariant | **缺口：真模型問題生成品質** |
| **覆蓋的兄弟測試** | — | `test_generate_questions_splits_multiline_string`（split）、`test_generate_questions_strips_and_drops_blank_lines`（strip）、`test_generate_questions_rejects_json_shaped_response`（JSON rejection）、`test_generate_questions_strips_markdown_fence`（fence）、`control_06`（clean list contract） | — |

**缺口判定**：離線 substitute 覆蓋了**輸出解析的所有邊界**（split、strip、JSON rejection、fence、empty），唯一缺口是**真 Grok 對法律文本的問題生成品質**。

**最小缺口位置**：`tests/test_questions.py:74` — 離線 substitute 在 `test_questions.py:25` 已覆蓋解析路徑。

---

### #7 `test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 維度 | Deselected 測試 | Substitute 測試 | 差異 |
|---|---|---|---|
| **功能路徑** | 真 Twinkle + 真 LawLookup + 真 Grok keyword | FakeLaw + FakeTwinkle 驗證排序 | **路徑差異最大**：substitute 隔離了所有外部服務 |
| **邊界條件** | 排序不變式（Level A > B > distance） | Level-based sort、domain routing（law vs other） | **部分覆蓋**：排序邏輯覆蓋，但 vacuous pass 盲區需額外測試 |
| **覆蓋的兄弟測試** | — | `test_retrieve_for_gap_law_domain_puts_level_A_before_B`（排序）、`test_retrieve_for_gap_other_domain_uses_web_not_twinkle`（routing）、`test_law_search.py::test_search_law_sources_returns_level_A_law_articles`（law DB）、`test_twinkle.py` 4 個 mock tests（MCP protocol）、`control_07/07b`（vacuous pass + Level A）、`exclusion_blind_spot`（vacuous proof） | — |

**缺口判定**：離線 substitute **已覆蓋排序邏輯、domain routing、vacuous pass 盲區（含 Level A 強制非空回歸）**。唯一缺口是：(1) 真 Twinkle Hub 服務 I/O；(2) 真 Grok keyword extraction 品質。

**最小缺口位置**：`tests/test_retrieve.py:102` — 離線 substitute 在 `test_retrieve.py:72` 已覆蓋排序路徑；vacuous pass 盲區已被 `test_exclusion_correctness_blind_spot.py:68` 與 `test_excluded_failing_controls.py:324` 鎖定。

---

### #8 `test_twinkle.py::test_search_real_twinkle_hub`

| 維度 | Deselected 測試 | Substitute 測試 | 差異 |
|---|---|---|---|
| **功能路徑** | 真 Twinkle Hub MCP 搜尋 | mock MCP → 驗證 parse/session/transport/protocol | **路徑不同**：substitute 跳過了真實 MCP 服務 |
| **邊界條件** | 真實服務可用性 + session 相容性 + 網路逾時 | full content parse、similarity clamping、session reuse、transport failure、protocol error、missing title logging、no-token guard | **覆蓋完整**：離線 substitute 覆蓋了 `TwinkleClient.search()` 的全部代碼分支（含 7 個邊界） |
| **覆蓋的兄弟測試** | — | `test_search_parses_source_with_full_content`（parse）、`test_search_clamps_similarity_input_to_distance_range`（clamping）、`test_search_reuses_mcp_session`（session）、`test_search_transport_failure_returns_empty`（transport）、`test_search_mcp_protocol_error_returns_empty`（protocol）、`test_search_skips_records_without_title`（missing title）、`test_search_returns_empty_without_token`（no-token）、`control_08`（Source contract） | — |

**缺口判定**：離線 substitute **已覆蓋 `TwinkleClient.search()` 的全部 7 個代碼分支與邊界**。唯一缺口是**真實 Twinkle Hub 服務可用性**——基礎設施層級缺口。

**最小缺口位置**：`tests/test_twinkle.py:185` — 離線 substitute 在 `tests/test_twinkle.py:78`–`164` 已覆蓋完整 MCP 協議路徑。

---

## 總結

| # | Deselected 測試 | 離線覆蓋完整度 | 最小缺口 | 缺口性質 |
|---|---|---|---|---|
| 1 | `test_detect_domain_real_grok_returns_law` | 標籤解析 100% | 真模型分類品質 | 語意品質（不可離線） |
| 2 | `test_e2e_acceptance_real` | 結構不變式 100% | 真模型寫作品質 + 真服務 I/O | 品質+基礎設施（不可離線） |
| 3 | `test_detect_gaps_real_grok` | 解析過濾 100% | 真模型涵蓋度判斷 | 語意品質（不可離線） |
| 4 | `test_grok_pong_integration` | 代碼分支 100% | TCP 連通性 | 基礎設施（不可離線） |
| 5 | `test_run_pipeline_real_grok` | Pipeline 邏輯 100% | 真模型輸出品質 | 語意品質（不可離線） |
| 6 | `test_generate_questions_real_grok` | 輸出解析 100% | 真模型問題生成品質 | 語意品質（不可離線） |
| 7 | `test_retrieve_for_gap_real_twinkle_smoke` | 排序+routing+盲區 100% | 真 Twinkle I/O + 真 keyword 品質 | 品質+基礎設施（不可離線） |
| 8 | `test_search_real_twinkle_hub` | MCP 協議 7/7 分支 | 真實服務可用性 | 基礎設施（不可離線） |

### 關鍵結論

1. **無功能性覆蓋缺口**：所有 8 個 deselected 測試的 substitute_tests **已完整覆蓋**對應的代碼路徑與離線邊界條件（標籤解析、JSON parse、filtering、sorting、MCP protocol、error handling、C6 invariant）。

2. **缺口集中在「語意品質」與「基礎設施」**：所有缺口本質上是「真模型推論品質」或「真實服務連通性」——這些無法用 FakeLLM 或 mock MCP 替代，必須透過 integration 測試或 CI workflow_dispatch 覆蓋。

3. **vacuous pass 盲區已被離線鎖定**：deselected #7 的 smoke assertions vacuous pass 問題已被 `test_exclusion_correctness_blind_spot.py`（離線 proof）與 `test_excluded_failing_controls.py::control_07b`（Level A 非空 regression）雙重鎖定。

4. **建議**：若要補最小可替代回歸測試，可在離線模式下新增一個 smoke test 驗證「substitute_tests 清單中每個測試的 node_id 確實存在且可 collect」，以防止 substitute test 本身被誤刪或失效。此測試位置建議放在 `tests/test_deselected_ci_gate_acceptance.py`。
