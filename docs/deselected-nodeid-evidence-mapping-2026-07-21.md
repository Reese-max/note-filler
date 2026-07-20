# 8 個 deselected 測試之「node id → 排除依據 → 共享覆蓋證據」對照表（2026-07-21）

## 前置結論

逐一比對全部 8 個 `@pytest.mark.integration` **deselected** 測試與三種解釋機制後，認定：

**零個測試存在「無法以刻意分組 / 重複覆蓋 / 明確排除條件完整解釋」的情況。** 所有 deselection 均可完全歸因於
`pyproject.toml` 中 `addopts = "... -m 'not integration' ..."` 的預設標記過濾，屬於**刻意分組（deliberate grouping）**。

下表逐項驗證三層解釋的適用性，並標註殘留缺口（屬於**替代覆蓋**的已知限制，非 deselection 本身無法解釋）。

---

## 解釋機制定義

| 機制 | 判斷條件 |
|---|---|
| **刻意分組** | 測試帶 `@pytest.mark.integration` 且 `pyproject.toml` addopts 合 `-m 'not integration'` |
| **重複覆蓋** | 該測試在 `deselected_allowlist.json` 中有非空的 `substitute_tests`，且替代測試已正式歸檔 |
| **明確排除條件** | 測試帶 `@pytest.mark.skipif()` 或函式內 `pytest.skip()`，於 runtime 提供第二層保護 |

---

## 對照表

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 維度 | 內容 | 原始檔案行號 |
|---|---|---|
| **path pattern** | `tests/test_domain.py` — 共用 `_grok_reachable()` helper（L9-14）、`detect_domain` import | L1-L7 |
| **fixtures** | 無 pytest fixture（使用 helper 函式 `_grok_reachable()`） | L50-61 |
| **marks** | `@pytest.mark.integration` `@pytest.mark.skipif(not _grok_reachable())` | L50-51 |
| **parametrize** | 無 `@pytest.mark.parametrize`，無參數化 | — |
| **同檔兄弟** | `test_detect_domain_law` `test_detect_domain_admin` `test_detect_domain_exam` `test_detect_domain_noise_falls_back_to_other` `test_detect_domain_label_with_trailing_punctuation` `test_detect_domain_uppercase_and_whitespace` | L17-47 |

| 解釋機制 | 適用？ | 證據 |
|---|---|---|
| **刻意分組** | ✅ 完全解釋 deselection | `pyproject.toml:32` addopts `-m 'not integration'`：collection 階段排除所有 integration marker |
| **重複覆蓋** | ✅ 有 2 個替代測試 | `test_detect_domain_law`（L17-19）以 FakeLLM 驗證 law 回傳契約；`test_control_01_domain_legal_label_contract` 驗證法律標籤 + 雜訊 fallback |
| **明確排除條件** | ✅ skipif 為 L2 防線 | `@pytest.mark.skipif(not _grok_reachable())`：若 proxy 突然可達但 addopts 未改，仍會在 runtime skip |

**殘留缺口**: 真 Grok 對法律文字的實際回應語意正確性（屬外部模型品質，非 deselection 機制可解釋）。

---

### 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 維度 | 內容 | 原始檔案行號 |
|---|---|---|
| **path pattern** | `tests/test_e2e_acceptance.py` — 共用 `_grok_up()`、`_twinkle_ready()`、4 個 `_assert_*` 不變式、`_StubTwinkle` 類別、`_Grok0` 類別 | L1-L299 |
| **fixtures** | 無 pytest fixture（使用 helper 函式與環境變數） | L244-299 |
| **marks** | `@pytest.mark.integration`（無 `@skipif`，改用內部 `pytest.skip()`） | L244 |
| **parametrize** | 無 | — |
| **同檔兄弟** | `test_e2e_structural_invariants`（L150-173） `test_e2e_offline_supplement_quality_boundary`（L196-204） `test_e2e_minimal_quality_gates_offline_regression`（L211-240） | 同檔 3 個非 integration 測試 |

| 解釋機制 | 適用？ | 證據 |
|---|---|---|
| **刻意分組** | ✅ 完全解釋 deselection | L244 `@pytest.mark.integration` → 被 `-m 'not integration'` 排除 |
| **重複覆蓋** | ✅ 8 個替代測試覆蓋所有不變式 | `test_e2e_structural_invariants`（L150-173）涵蓋四項 §12 不變式；`test_run_pipeline_invariant` 涵蓋 C6；`test_control_02` 為 failing-first 對照 |
| **明確排除條件** | ✅ 3 層 runtime guard | L247 `if not LAW_DB.exists(): pytest.skip(...)`；L251 `if not _grok_up() and _twinkle_ready(): pytest.skip(...)` |

**殘留缺口**: 真 Grok + 真 Twinkle 組合下的端到端品質、Level A 路由穩定性（已由 6 次 bounded retry 部分補償，仍非 100% 可重現）。

---

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`

| 維度 | 內容 | 原始檔案行號 |
|---|---|---|
| **path pattern** | `tests/test_gap.py` — 共用 `_grok_reachable()`、`Gap`/`detect_gaps` import | L1-L6 |
| **fixtures** | 無 | — |
| **marks** | `@pytest.mark.integration` `@pytest.mark.skipif(not _grok_reachable())` | L71-72 |
| **parametrize** | 無 | — |
| **同檔兄弟** | `test_detect_gaps_keeps_only_partial_and_missing`（L17-29） `test_detect_gaps_calls_llm_exactly_once`（L32-36） `test_detect_gaps_parse_failure_marks_all_missing`（L39-46） `test_detect_gaps_non_array_json_also_fallbacks`（L49-54） `test_detect_gaps_strips_code_fence`（L57-62） `test_detect_gaps_empty_questions_short_circuits`（L65-68） | 同檔 6 個非 integration 測試 |

| 解釋機制 | 適用？ | 證據 |
|---|---|---|
| **刻意分組** | ✅ | L71 `@pytest.mark.integration` |
| **重複覆蓋** | ✅ 2 個替代測試 | `test_detect_gaps_keeps_only_partial_and_missing`（L17-29）以 FakeLLM 驗證 covered 過濾；`test_control_03_gap_uncovered_question_must_surface` 為 failing-first 對照 |
| **明確排除條件** | ✅ | L72 `@pytest.mark.skipif(not _grok_reachable())` |

**殘留缺口**: 真 Grok 對法律文本的缺口判斷品質。

---

### 4. `tests/test_llm.py::test_grok_pong_integration`

| 維度 | 內容 | 原始檔案行號 |
|---|---|---|
| **path pattern** | `tests/test_llm.py` — 共用 `_grok_reachable()`、`GrokClient`/`FakeLLM` import | L1-L7 |
| **fixtures** | 同檔 `test_grokclient_builds_request_body` 使用 `monkeypatch`；但 integration 測試**未使用** fixture | L24-63（非 integration 使用），L66-73（integration 不用 fixture） |
| **marks** | `@pytest.mark.integration` `@pytest.mark.skipif(not _grok_reachable())` | L66-67 |
| **parametrize** | 無 | — |
| **同檔兄弟** | `test_fakellm_returns_canned_in_order`（L18-21） `test_grokclient_builds_request_body`（L24-63） | 同檔 2 個非 integration 測試 |

| 解釋機制 | 適用？ | 證據 |
|---|---|---|
| **刻意分組** | ✅ | L66 `@pytest.mark.integration` |
| **重複覆蓋** | ✅ 2 個替代測試 | `test_grokclient_builds_request_body`（L24-63）monkeypatch 驗證 request body、Bearer、endpoint、timeout、response parse；`test_control_04_grok_client_parse_and_endpoint_contract` 為 failing-first 對照 |
| **明確排除條件** | ✅ | L67 `@pytest.mark.skipif(not _grok_reachable())` |

**殘留缺口**: 真實 TCP 連線與 proxy 實際回應格式（屬基礎設施連通性，非產品邏輯缺陷）。

---

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 維度 | 內容 | 原始檔案行號 |
|---|---|---|
| **path pattern** | `tests/test_pipeline.py` — 共用 `_grok_reachable()`、`note_path` fixture、`FakeTwinkle`、`FakeLaw`、`_src()` 工廠 | L1-L53 |
| **fixtures** | 使用 `note_path`（L19-27, `@pytest.fixture` 內造 .docx） | L153 |
| **marks** | `@pytest.mark.integration` `@pytest.mark.skipif(not _grok_reachable())` | L151-152 |
| **parametrize** | 無 | — |
| **同檔兄弟** | `test_run_pipeline_invariant`（L56-95, 用 `note_path`） `test_run_pipeline_law_domain_runs_citation_check`（L98-123, 用 `note_path`+`monkeypatch`） `test_run_pipeline_malformed_gap_output_falls_back_to_pending`（L126-148, 用 `note_path`） | 同檔 3 個非 integration 測試 |

| 解釋機制 | 適用？ | 證據 |
|---|---|---|
| **刻意分組** | ✅ | L151 `@pytest.mark.integration` |
| **重複覆蓋** | ✅ 5 個替代測試 | C6 不變式由 `test_run_pipeline_invariant`（L56-95）驗證；畸形輸出降級由 `test_run_pipeline_malformed_gap_output_falls_back_to_pending`（L126-148）驗證；法規引用查核由 `test_run_pipeline_law_domain_runs_citation_check`（L98-123）驗證；來源引用正確性由 `test_correction.py::test_retrieved_five_but_only_two_cited` 驗證；C6 pending 由 `test_control_05_pipeline_c6_pending_when_no_sources` 驗證 |
| **明確排除條件** | ✅ | L152 `@pytest.mark.skipif(not _grok_reachable())` |

**殘留缺口**: 真 Grok 模型輸出下的 domain/questions/gaps 正確性。

---

### 6. `tests/test_questions.py::test_generate_questions_real_grok`

| 維度 | 內容 | 原始檔案行號 |
|---|---|---|
| **path pattern** | `tests/test_questions.py` — 共用 `_grok_reachable()`、`generate_questions`/`FakeLLM` import | L1-L6 |
| **fixtures** | 無 | — |
| **marks** | `@pytest.mark.integration` `@pytest.mark.skipif(not _grok_reachable())` | L62-63 |
| **parametrize** | 無 | — |
| **同檔兄弟** | `test_generate_questions_splits_multiline_string`（L17-29） `test_generate_questions_strips_and_drops_blank_lines`（L32-38） `test_generate_questions_empty_response_returns_empty_list`（L41-46） `test_generate_questions_calls_llm_exactly_once`（L49-59） | 同檔 4 個非 integration 測試 |

| 解釋機制 | 適用？ | 證據 |
|---|---|---|
| **刻意分組** | ✅ | L62 `@pytest.mark.integration` |
| **重複覆蓋** | ✅ 3 個替代測試 | 多行切割（L17-29）、strip 與空行移除（L32-38）由 FakeLLM 驗證；乾淨清單契約由 `test_control_06_questions_clean_list_contract` 驗證 |
| **明確排除條件** | ✅ | L63 `@pytest.mark.skipif(not _grok_reachable())` |

**殘留缺口**: 真 Grok 對法律文本的問題生成品質。

---

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 維度 | 內容 | 原始檔案行號 |
|---|---|---|
| **path pattern** | `tests/test_retrieve.py` — 共用 `LAW_DB`、`_grok_reachable()`、`FakeTwinkle`、`FakeLaw`、`_src()` / `_row()` 工廠 | L1-L60 |
| **fixtures** | 同檔 `test_retrieve_for_gap_other_domain_uses_web_not_twinkle` 使用 `monkeypatch`；但 integration 測試**未使用** fixture | L80-99（非 integration），L102-125（integration） |
| **marks** | `@pytest.mark.integration` `@pytest.mark.skipif(not LAW_DB.exists())` `@pytest.mark.skipif(not _grok_reachable())` + 函式內 `pytest.skip()` | L102-108 |
| **parametrize** | 無 | — |
| **同檔兄弟** | `test_retrieve_for_gap_law_domain_puts_level_A_before_B`（L62-77） `test_retrieve_for_gap_other_domain_uses_web_not_twinkle`（L80-99） | 同檔 2 個非 integration 測試 |

| 解釋機制 | 適用？ | 證據 |
|---|---|---|
| **刻意分組** | ✅ | L102 `@pytest.mark.integration` |
| **重複覆蓋** | ✅ 9 個替代測試（最多） | 排序契約（L62-77）、離線 law source（`test_search_law_sources_returns_level_A_law_articles`）、Twinkle 解析（`test_search_parses_source_with_full_content`）、session 重用（`test_search_reuses_mcp_session`）、transport 安全降級（`test_search_transport_failure_returns_empty`）、vacuous pass 盲區（`test_exclusion_correctness_blind_spot.py` 兩項）、failing-first 對照（`test_control_07` 與 `test_control_07b`） |
| **明確排除條件** | ✅ 三層 runtime guard | L103 `skipif(not LAW_DB.exists())`、L104 `skipif(not _grok_reachable())`、L107-108 `if not token: pytest.skip(...)` |

**殘留缺口**: 真實 Twinkle Hub I/O 與真 Grok 關鍵字抽取品質；vacuous smoke 對 empty 的驗證盲區已由 `test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot` 與 `test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty` 鎖定。

---

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 維度 | 內容 | 原始檔案行號 |
|---|---|---|
| **path pattern** | `tests/test_twinkle.py` — 共用 `_BILL`、`_FakeResponse`、`_make_fake_urlopen()`、`TwinkleClient`/`Source` import | L1-L8 |
| **fixtures** | 同檔 4 個非 integration 測試使用 `monkeypatch`；但 integration 測試**未使用** fixture | L61-114（非 integration），L122-135（integration） |
| **marks** | `@pytest.mark.integration`（無 `@skipif`，改用函式內 `pytest.skip()`） | L122 |
| **parametrize** | 無 | — |
| **同檔兄弟** | `test_search_parses_source_with_full_content`（L61-80, `monkeypatch`） `test_search_returns_empty_without_token`（L83-85, `monkeypatch`） `test_search_reuses_mcp_session`（L88-105, `monkeypatch`） `test_search_transport_failure_returns_empty`（L108-114, `monkeypatch`） `test_default_timeout_is_60`（L117-119） | 同檔 5 個非 integration 測試 |

| 解釋機制 | 適用？ | 證據 |
|---|---|---|
| **刻意分組** | ✅ | L122 `@pytest.mark.integration` |
| **重複覆蓋** | ✅ 4 個替代測試 | 全文 Source 解析（L61-80）、session 重用（L88-105）、transport 安全降級（L108-114）均由 mock 驗證；failing-first 契約對照由 `test_control_08_twinkle_parsed_source_contract` 驗證 |
| **明確排除條件** | ✅ runtime guard | L127-128 `if not token: pytest.skip(...)` |

**殘留缺口**: 真實 Twinkle Hub 服務可用性、服務端 session 相容性與網路逾時行為（屬外部 I/O，非產品邏輯 determinism 缺陷）。

---

## 整合判斷

| 測試 | 刻意分組 | 重複覆蓋 | 明確排除條件 | 無法完整解釋？ |
|---|---|---|---|---|
| #1 test_domain::test_detect_domain_real_grok_returns_law | ✅ | ✅ | ✅ | 否 |
| #2 test_e2e_acceptance::test_e2e_acceptance_real | ✅ | ✅ | ✅ | 否 |
| #3 test_gap::test_detect_gaps_real_grok | ✅ | ✅ | ✅ | 否 |
| #4 test_llm::test_grok_pong_integration | ✅ | ✅ | ✅ | 否 |
| #5 test_pipeline::test_run_pipeline_real_grok | ✅ | ✅ | ✅ | 否 |
| #6 test_questions::test_generate_questions_real_grok | ✅ | ✅ | ✅ | 否 |
| #7 test_retrieve::test_retrieve_for_gap_real_twinkle_smoke | ✅ | ✅ | ✅ | 否 |
| #8 test_twinkle::test_search_real_twinkle_hub | ✅ | ✅ | ✅ | 否 |

**最終判定**: 全部 8 個 deselected 測試均可被三個機制完整解釋。唯一未由替代測試覆蓋的部分是「真外部服務（Grok / Twinkle Hub）」的實際 I/O 行為 —— 這屬於 integration 測試的本質邊界，不是 deselection 合規性或解釋完整性的缺失。

---

## 驗證命令

```powershell
# 確認 collection 與 deselected 清單（含原因）
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 `
  -m pytest --collect-only -q --deselected-details --color=no

# 確認無 addopts 時 8 個 integration 測試全部可見
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 `
  -m pytest --collect-only -q --color=no -o "addopts="

# 確認 allowlist 閘道通過
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 `
  scripts/validate_deselection_ci.py

# 確認 guard 測試全綠
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 `
  -m pytest tests/test_deselection_guard.py -v --color=no
```
