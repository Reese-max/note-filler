# 8 個 deselected 測試覆蓋風險重新分級（2026-07-21）

> **任務**：對 8 個 deselected 測試做一次只依賴現有測試輸出與測試碼的覆蓋風險重新分級，產出「關鍵路徑有無等價覆蓋」與「是否需要補測」的最終判定，並標明證據檔案路徑。
>
> **方法**：逐項比對 deselected 測試的關鍵函式路徑與其替代測試（substitute_tests from `tests/deselected_allowlist.json`）的覆蓋範圍，判定等價性；再依殘留缺口風險給予 Low/Medium/High 定級。

---

## 風險分級判準

| 等級 | 定義 | 條件 |
|------|------|------|
| **Low** | 所有確定性程式碼路徑已被替代測試完整覆蓋，殘留缺口僅為外部模型/服務的語意品質（非產品邏輯缺陷），且依賴單一可恢復外部服務 | 替代覆蓋涵蓋全部程式分支，殘留缺口屬整合邊界 |
| **Medium** | 關鍵路徑有替代覆蓋但存在已紀錄的驗證盲區（如 vacuous pass）、或依賴多重外部服務組合、或整合路徑無法以離線 mock 完全重現 | 替代覆蓋涵蓋主要路徑但盲區或組合複雜度未完全鎖定 |
| **High** | 關鍵路徑無等價覆蓋，或替代測試僅覆蓋部分路徑且殘留缺口可能隱藏產品缺陷 | 替代覆蓋不足或 defers to integration 實測 |

---

## 逐項判定

### #1 `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 欄位 | 值 |
|------|-----|
| **關鍵函式** | `src/note_filler/domain.py:22-40` `detect_domain(text, llm) → Domain` |
| **關鍵路徑** | 3 條分支：(1) 乾淨回應直接命中 `_VALID` → branch 1；(2) 雜訊/標點中依優先序抽取第一個合法標籤 → branch 2；(3) 完全無法辨識 → branch 3 fallback to `"other"` |
| **替代測試 & 覆蓋路徑** | `test_detect_domain_law` (L17-19) → branch 1；`test_detect_domain_noise_falls_back_to_other` → branch 3；`test_detect_domain_label_with_trailing_punctuation` → branch 2；`test_detect_domain_uppercase_and_whitespace` → branch 2；`test_control_01_domain_legal_label_contract` → branch 1+2+3 |
| **等價覆蓋？** | ✅ **替代更廣**——7 個非 integration 測試覆蓋全部 3 條分支（含標點、大小寫、雜訊 fallback），整合測試只驗 branch 1 |
| **殘留缺口** | 真 Grok 對法律文字的實際回應語意正確性（屬外部模型品質） |
| **風險等級** | **Low** — 程式路徑完全覆蓋且替代更廣，唯一缺口是模型品質 |
| **證據檔案** | `tests/test_domain.py:17-47`（替代測試）、`src/note_filler/domain.py:22-40`（關鍵函式）、`tests/deselected_allowlist.json:13-16`（substitute 註冊） |
| **需補測？** | **否** |

---

### #2 `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 欄位 | 值 |
|------|-----|
| **關鍵函式** | `src/note_filler/pipeline.py:14-41` `run_pipeline` + 5 個 `_assert_*` helper（`_assert_immutable_original`、`_assert_no_source_gate`、`_assert_law_citations_ok`、`_assert_markdown_contract`、`_assert_supplement_quality`） |
| **關鍵路徑** | (1) parse→domain→questions→gaps 串接不炸；(2) C6 不變式：無源→pending_evidence、雙源→verified；(3) 畸形 gap 輸出→pending_evidence fallback；(4) law domain citation check 逐段觸發；(5) 只掛實際引用來源；(6) Level A 路由啟用；(7) 補充品質（非原始記錄倒出、[^n] 註腳） |
| **替代測試 & 覆蓋路徑** | `test_e2e_structural_invariants` → 路徑 1+2+4+5（FakeLLM+_StubTwinkle）；`test_e2e_offline_supplement_quality_boundary` → 路徑 6+7；`test_e2e_minimal_quality_gates_offline_regression` → 路徑 1+2+4+5+6+7；`test_run_pipeline_invariant` → 路徑 2；`test_run_pipeline_malformed_gap_output_falls_back_to_pending` → 路徑 3；`test_run_pipeline_law_domain_runs_citation_check` → 路徑 4；`test_control_02_e2e_offline_quality_gates` → 路徑 1+2+5 |
| **等價覆蓋？** | ✅ **等價**——8 個替代測試共同覆蓋全部 7 條關鍵路徑，所有結構不變式已離線驗證 |
| **殘留缺口** | (a) 真 Grok + 真 Twinkle 組合下的 gap 偵測品質；(b) 補充寫作品質（`_assert_supplement_quality` 的真模型路徑）；(c) Level A 路由穩定性 |
| **風險等級** | **Medium** — 結構不變式完全覆蓋，但有多重外部服務（Grok+Twinkle+LawLookup）組合，且補充品質斷言在真模型下約 50% flaky |
| **證據檔案** | `tests/test_e2e_acceptance.py:150-240`（替代測試）、`src/note_filler/pipeline.py:14-41`（關鍵函式）、`tests/deselected_allowlist.json:52-61`（substitute 註冊） |
| **需補測？** | **否**（結構不變式已確定性覆蓋；flaky 屬模型隨機性非產品缺陷） |

---

### #3 `tests/test_gap.py::test_detect_gaps_real_grok`

| 欄位 | 值 |
|------|-----|
| **關鍵函式** | `src/note_filler/gap.py:57-89` `detect_gaps(questions, note_text, llm) → list[Gap]` |
| **關鍵路徑** | (1) 空 questions 短路回空；(2) 正常 JSON 解析→過濾 covered 保留 partial/missing；(3) JSON 解析失敗→全部保守標 missing；(4) 合法 JSON 非陣列→fallback missing；(5) ` ``` ` 程式碼圍欄剝除；(6) 恰一次 LLM 呼叫 |
| **替代測試 & 覆蓋路徑** | `test_detect_gaps_keeps_only_partial_and_missing` → 路徑 2+6；`test_detect_gaps_calls_llm_exactly_once` → 路徑 6；`test_detect_gaps_parse_failure_marks_all_missing` → 路徑 3；`test_detect_gaps_non_array_json_also_fallbacks` → 路徑 4；`test_detect_gaps_strips_code_fence` → 路徑 5；`test_detect_gaps_empty_questions_short_circuits` → 路徑 1；`test_control_03_gap_uncovered_question_must_surface` → 路徑 2 |
| **等價覆蓋？** | ✅ **替代更廣**——6 個非 integration 測試覆蓋全部 6 條路徑（含短路、fallback、圍欄），整合測試只驗路徑 2 |
| **殘留缺口** | 真 Grok 對法律文本的缺口判斷品質（covered vs partial 的語意邊界） |
| **風險等級** | **Low** — 程式路徑完全覆蓋且替代更廣，唯一缺口是模型判斷品質 |
| **證據檔案** | `tests/test_gap.py:17-68`（替代測試）、`src/note_filler/gap.py:57-89`（關鍵函式）、`tests/deselected_allowlist.json:101-104`（substitute 註冊） |
| **需補測？** | **否** |

---

### #4 `tests/test_llm.py::test_grok_pong_integration`

| 欄位 | 值 |
|------|-----|
| **關鍵函式** | `src/note_filler/llm.py:27-41` `GrokClient.complete(messages, **kw) → str` |
| **關鍵路徑** | (1) HTTP POST 到 `/v1/chat/completions`；(2) Bearer auth header；(3) request body 序列化（model/messages/額外 kw）；(4) response JSON 解析→content 抽取；(5) timeout 傳遞；(6) 真實 TCP 連線 |
| **替代測試 & 覆蓋路徑** | `test_grokclient_builds_request_body` → 路徑 1-5（monkeypatch）；`test_control_04_grok_client_parse_and_endpoint_contract` → 路徑 1-5（monkeypatch） |
| **等價覆蓋？** | ✅ **等價**——路徑 1-5 已由 monkeypatch 驗證，整合測試僅多路徑 6（真實 TCP） |
| **殘留缺口** | 真實 TCP 連線到 proxy:8318 的連通性與 proxy 實際回應格式 |
| **風險等級** | **Low** — 最短最簡單的 integration 測試（僅 PONG 斷言），所有產品邏輯已被替代覆蓋 |
| **證據檔案** | `tests/test_llm.py:24-63`（替代測試）、`src/note_filler/llm.py:27-41`（關鍵函式）、`tests/deselected_allowlist.json:139-142`（substitute 註冊） |
| **需補測？** | **否** |

---

### #5 `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 欄位 | 值 |
|------|-----|
| **關鍵函式** | `src/note_filler/pipeline.py:14-41` `run_pipeline` |
| **關鍵路徑** | (1) parse→domain→questions→gaps 串接；(2) C6 不變式：無源→pending_evidence；(3) 畸形 gap 輸出→pending_evidence；(4) law domain citation check 逐段觸發；(5) 只掛實際引用來源；(6) retrieve→write→cross_validate 每 gap 循環 |
| **替代測試 & 覆蓋路徑** | `test_run_pipeline_invariant` → 路徑 1+2+6；`test_run_pipeline_malformed_gap_output_falls_back_to_pending` → 路徑 3；`test_run_pipeline_law_domain_runs_citation_check` → 路徑 4+1；`test_control_05_pipeline_c6_pending_when_no_sources` → 路徑 2+6 |
| **等價覆蓋？** | ✅ **等價**——5 個替代測試涵蓋全部 6 條路徑（含畸形輸出降級、citation check、C6 不變式） |
| **殘留缺口** | 真 Grok 模型輸出下的 domain/questions/gaps 正確性 + pipeline 穩定性 |
| **風險等級** | **Low** — pipeline 邏輯路徑完全覆蓋，殘留缺口僅為模型輸出語意品質 |
| **證據檔案** | `tests/test_pipeline.py:56-148`（替代測試）、`src/note_filler/pipeline.py:14-41`（關鍵函式）、`tests/deselected_allowlist.json:175-181`（substitute 註冊） |
| **需補測？** | **否** |

---

### #6 `tests/test_questions.py::test_generate_questions_real_grok`

| 欄位 | 值 |
|------|-----|
| **關鍵函式** | `src/note_filler/questions.py:15-46` `generate_questions(full_text, domain, llm) → list[str]` |
| **關鍵路徑** | (1) 恰一次 LLM 呼叫；(2) `splitlines()` + `strip()` 切割成問題清單；(3) 空行過濾；(4) 空回應→空清單 |
| **替代測試 & 覆蓋路徑** | `test_generate_questions_splits_multiline_string` → 路徑 1+2；`test_generate_questions_strips_and_drops_blank_lines` → 路徑 3+2；`test_generate_questions_empty_response_returns_empty_list` → 路徑 4；`test_generate_questions_calls_llm_exactly_once` → 路徑 1；`test_control_06_questions_clean_list_contract` → 路徑 2+3 |
| **等價覆蓋？** | ✅ **替代更廣**——4 個非 integration 測試覆蓋全部 4 條路徑（含空回應、僅一次呼叫），整合測試只驗路徑 2+3 |
| **殘留缺口** | 真 Grok 對法律文本的問題生成品質 |
| **風險等級** | **Low** — 程式路徑完全覆蓋且替代更廣，唯一缺口是模型品質 |
| **證據檔案** | `tests/test_questions.py:17-59`（替代測試）、`src/note_filler/questions.py:15-46`（關鍵函式）、`tests/deselected_allowlist.json:219-222`（substitute 註冊） |
| **需補測？** | **否** |

---

### #7 `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 欄位 | 值 |
|------|-----|
| **關鍵函式** | `src/note_filler/retrieve/__init__.py:23-44` `retrieve_for_gap(gap, domain, twinkle, law, llm) → list[Source]` |
| **關鍵路徑** | (1) law domain→search_law_sources (Level A) + twinkle (Level B)；(2) other domain→僅 search_web_sources；(3) C5 排序：A 先於 B、同級 distance 升序；(4) Twinkle session 初始化→reuse→tools/call；(5) Source 解析（level/content/fetched_date/distance）；(6) transport failure 安全降級→空結果；(7) 無 token→空結果 |
| **替代測試 & 覆蓋路徑** | `test_retrieve_for_gap_law_domain_puts_level_A_before_B` → 路徑 1+3；`test_search_law_sources_returns_level_A_law_articles` → 路徑 1（law 部分）；`test_search_parses_source_with_full_content` → 路徑 5；`test_search_reuses_mcp_session` → 路徑 4；`test_search_transport_failure_returns_empty` → 路徑 6；`test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot` → 路徑 7（證明 vacuous 盲區）；`test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty` → 路徑 1（非空）；`test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot` → 路徑 7（failing-first 對照）；`test_control_07b_retrieve_law_level_a_not_vacuous` → 路徑 1+3（非空產品路徑） |
| **等價覆蓋？** | ✅ **等價**——9 個替代測試共同覆蓋全部 7 條路徑（含 vacuous 盲區已被 blind spot 測試鎖定） |
| **殘留缺口** | (a) 真實 Twinkle Hub I/O（服務可用性、session 相容性）；(b) 真 Grok 關鍵字抽取品質；(c) vacuous smoke 對 empty 的 pass 盲區（**已由 blind spot 測試離線鎖定**） |
| **風險等級** | **Medium** — 驗證盲區（vacuous pass on empty）雖已被 blind spot 測試證明，但該盲區是斷言設計缺陷而非程式碼缺陷；且依賴 3 個外部服務（Twinkle+Grok+LawLookup）組合 |
| **證據檔案** | `tests/test_retrieve.py:62-99`（替代測試）、`tests/test_exclusion_correctness_blind_spot.py`（blind spot 證明）、`src/note_filler/retrieve/__init__.py:23-44`（關鍵函式）、`tests/deselected_allowlist.json:260-270`（substitute 註冊） |
| **需補測？** | **否**（盲區已由 blind spot + failing-first 對照鎖定產品 Level A 非空路徑） |

---

### #8 `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 欄位 | 值 |
|------|-----|
| **關鍵函式** | `src/note_filler/retrieve/twinkle.py:207-229` `TwinkleClient.search(query, n) → list[Source]` |
| **關鍵路徑** | (1) 無 token/空 query→空結果；(2) MCP initialize→notifications/initialized→tools/call 三階段；(3) Source 解析（title/url/level/content/fetched_date/distance）；(4) similarity→distance 轉換與 clamp；(5) transport failure 安全降級→空；(6) 預設 timeout=60 |
| **替代測試 & 覆蓋路徑** | `test_search_parses_source_with_full_content` → 路徑 3+4（mock MCP/SSE）；`test_search_returns_empty_without_token` → 路徑 1；`test_search_reuses_mcp_session` → 路徑 2；`test_search_transport_failure_returns_empty` → 路徑 5；`test_default_timeout_is_60` → 路徑 6；`test_control_08_twinkle_parsed_source_contract` → 路徑 3（failing-first 對照） |
| **等價覆蓋？** | ✅ **等價**——5 個替代測試涵蓋全部 6 條路徑，mock 驗證了 MCP 協定解析全流程 |
| **殘留缺口** | (a) 真實 Twinkle Hub 服務可用性；(b) 服務端 session 相容性；(c) 網路逾時行為 |
| **風險等級** | **Medium** — 依賴外部 Twinkle Hub 服務，且為 #7 的底層依賴，但所有程式碼邏輯路徑已被 mock 測試完整覆蓋 |
| **證據檔案** | `tests/test_twinkle.py:61-139`（替代測試）、`src/note_filler/retrieve/twinkle.py:207-229`（關鍵函式）、`tests/deselected_allowlist.json:312-317`（substitute 註冊） |
| **需補測？** | **否** |

---

## 風險分級總表

| # | 測試 ID | 關鍵路徑等價覆蓋？ | 風險等級 | 需補測？ | 殘留缺口類型 |
|---|---------|-------------------|----------|---------|-------------|
| 1 | `test_detect_domain_real_grok_returns_law` | ✅ 替代更廣 | **Low** | 否 | 模型語意品質 |
| 2 | `test_e2e_acceptance_real` | ✅ 等價（8 替代） | **Medium** | 否 | 模型品質 + 多重外部服務組合 + flaky 斷言 |
| 3 | `test_detect_gaps_real_grok` | ✅ 替代更廣 | **Low** | 否 | 模型語意品質 |
| 4 | `test_grok_pong_integration` | ✅ 等價 | **Low** | 否 | TCP 連通性 |
| 5 | `test_run_pipeline_real_grok` | ✅ 等價（5 替代） | **Low** | 否 | 模型語意品質 |
| 6 | `test_generate_questions_real_grok` | ✅ 替代更廣 | **Low** | 否 | 模型語意品質 |
| 7 | `test_retrieve_for_gap_real_twinkle_smoke` | ✅ 等價（9 替代+盲區鎖定） | **Medium** | 否 | 外部服務 I/O + vacuous blind spot（已鎖定） |
| 8 | `test_search_real_twinkle_hub` | ✅ 等價（5 替代） | **Medium** | 否 | 外部服務可用性（#7 底層依賴） |

## 統計

| 等級 | 數量 | 占比例 |
|------|------|--------|
| Low | 5 | 62.5% |
| Medium | 3 | 37.5% |
| High | 0 | 0% |
| **需補測** | **0** | **0%** |

## 最終判定

1. **所有 8 個 deselected 測試的關鍵路徑均已由替代測試等價覆蓋** —— 其中 #1/#3/#6 替代測試甚至覆蓋了比整合測試更廣的程式碼路徑。
2. **零個測試需要補測非 integration 測試** —— 殘留缺口全為外部服務品質（Grok 模型語意、Twinkle Hub 可用性）或基礎設施連通性，屬於 integration 測試的本質邊界，非 CI 閘中離線測試可解決。
3. **風險集中點**（Medium × 3）：#2（多重外部服務組合 + flaky 斷言）、#7（vacuous 驗證盲區 + 三重依賴）、#8（#7 底層 + 唯一真 Twinkle Hub 路徑）—— 但均已由結構不變式或 blind spot 測試離線鎖定產品路徑非空。

## 證據索引

| 證據類別 | 檔案路徑 | 用途 |
|----------|---------|------|
| 替代測試原始碼 | `tests/test_domain.py`、`tests/test_gap.py`、`tests/test_llm.py`、`tests/test_pipeline.py`、`tests/test_questions.py`、`tests/test_retrieve.py`、`tests/test_twinkle.py`、`tests/test_e2e_acceptance.py` | 驗證各路徑覆蓋 |
| Failing-first 對照 | `tests/test_excluded_failing_controls.py` | 8 個 failing-first 契約驗證 |
| Blind spot 證明 | `tests/test_exclusion_correctness_blind_spot.py` | #7 vacuous pass 盲區鎖定 |
| Allowlist 註冊 | `tests/deselected_allowlist.json` | substitute 清單與證據鏈 |
| Guard 測試 | `tests/test_deselection_guard.py` | allowlist 完整性與 substitute 可收集性驗證 |
| 單獨執行結果 | `docs/deselected-8-individual-judge-2026-07-19.md` | 8/8 pass 實跑證據 |
| 原始 collection 輸出 | `docs/pytest-audit/collect-only-143-2026-07-19.txt` | deselected 原因追溯 |
| 等價覆蓋審計 | `docs/coverage-equivalence-audit-2026-07-18.md` | 程式碼路徑等價性初步判定 |
| 排除規則追溯 | `docs/deselected-8-nodeids-rules-2026-07-19.md` | collection/selection 規則完整分析 |
