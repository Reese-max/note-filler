# 預期排除測試可追溯對照表

## 產生時間
2026-07-23

## 執行環境
- Python 路徑: `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe`
- 執行參數: `-X utf8`
- 工作目錄: `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\5ca8bb57`

## 排除機制總覽

### 統一排除規則
所有 11 個 deselected 測試皆透過以下統一機制排除：

1. **Marker 標記**: 每個測試都有 `@pytest.mark.integration` 標記
2. **Pytest 配置**: `pyproject.toml` 中的 `addopts = "-m 'not integration'"`
3. **排除原因**: 所有測試的排除原因皆為 `deselected by -m 'not integration'`

### CI 配置
- **主要測試 Job**: `test-pinned` 和 `test-latest` 使用 `python -m pytest tests/ -m "not integration" -v`
- **Integration Job**: `test-integration` 使用 `python -m pytest tests/ -m "integration" -v` (僅 workflow_dispatch)
- **驗證腳本**: `python scripts/validate_deselection_ci.py`

## 完整可追溯對照表

### 1. tests/test_domain.py::test_detect_domain_real_grok_returns_law

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過 |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_domain.py::test_detect_domain_law<br>tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract |
| **驗證指令** | `python -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law -v` |
| **驗證結果** | FakeLLM 回 law 並驗證 detect_domain 的 law 回傳契約 |
| **覆蓋功能** | note_filler.domain.detect_domain — LLM 領域偵測 (law/admin/exam/other) |
| **證據來源** | pyproject.toml:32, tests/test_domain.py:62, tests/test_domain.py:63 |

### 2. tests/test_domain.py::test_detect_domain_real_grok_representative_domains

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 排除；四類代表文本需真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過 |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_domain.py::test_detect_domain_law<br>tests/test_domain.py::test_detect_domain_admin<br>tests/test_domain.py::test_detect_domain_exam<br>tests/test_domain.py::test_detect_domain_noise_falls_back_to_other |
| **驗證指令** | `python -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law tests/test_domain.py::test_detect_domain_admin tests/test_domain.py::test_detect_domain_exam tests/test_domain.py::test_detect_domain_noise_falls_back_to_other -v` |
| **驗證結果** | FakeLLM 鎖定 law/admin/exam/other 回傳契約與 fallback 行為 |
| **覆蓋功能** | note_filler.domain.detect_domain — 真 Grok 四類代表文本語意矩陣 |
| **證據來源** | pyproject.toml:32, tests/test_domain.py:76, tests/test_domain.py:77 |

### 3. tests/test_e2e_acceptance.py::test_e2e_acceptance_real

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 在 collection 階段排除；真跑需要 data/law_index.db、grok proxy 與 TWINKLE_HUB_TOKEN，任一前置條件不足即 skip |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_e2e_acceptance.py::test_e2e_structural_invariants<br>tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary<br>tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression<br>tests/test_pipeline.py::test_run_pipeline_invariant<br>tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending<br>tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check<br>tests/test_correction.py::test_retrieved_five_but_only_two_cited<br>tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates |
| **驗證指令** | `python -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_structural_invariants tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression -v` |
| **驗證結果** | 離線完整 pipeline 驗證原稿不可變、無來源閘、法條查核與輸出契約 |
| **覆蓋功能** | §12 端到端驗收: parse→domain→questions→gaps→retrieve→assemble→export; 5 個硬不變式 |
| **證據來源** | pyproject.toml:32, tests/test_e2e_acceptance.py:244, tests/test_e2e_acceptance.py:247, tests/test_e2e_acceptance.py:42, tests/test_e2e_acceptance.py:251 |

### 4. tests/test_gap.py::test_detect_gaps_real_grok

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過 |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing<br>tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface |
| **驗證指令** | `python -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface -v` |
| **驗證結果** | FakeLLM 驗證 covered 過濾，只保留 partial/missing 並建立 Gap |
| **覆蓋功能** | note_filler.gap.detect_gaps — LLM 缺口偵測 (partial/missing 過濾) |
| **證據來源** | pyproject.toml:32, tests/test_gap.py:83, tests/test_gap.py:84 |

### 5. tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 排除；covered/missing 語意矩陣需真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過 |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing<br>tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface |
| **驗證指令** | `python -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface -v` |
| **驗證結果** | FakeLLM 鎖定 covered 過濾與 partial/missing 結構 |
| **覆蓋功能** | note_filler.gap.detect_gaps — 真 Grok covered/missing 對照語意 |
| **證據來源** | pyproject.toml:32, tests/test_gap.py:106, tests/test_gap.py:107 |

### 6. tests/test_llm.py::test_grok_pong_integration

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過 |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_llm.py::test_grokclient_builds_request_body<br>tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract |
| **驗證指令** | `python -X utf8 -m pytest tests/test_llm.py::test_grokclient_builds_request_body tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract -v` |
| **驗證結果** | monkeypatch 驗證 request body、Bearer、POST endpoint、timeout 與 response parse |
| **覆蓋功能** | note_filler.llm.GrokClient.complete — 真實 HTTP 連線 + 回應解析 |
| **證據來源** | pyproject.toml:32, tests/test_llm.py:95, tests/test_llm.py:96 |

### 7. tests/test_pipeline.py::test_run_pipeline_real_grok

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 在 collection 階段排除；只要真實 grok proxy 才能執行，Twinkle 與 law 雖以 fake 隔離仍保留 integration 邊界 |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_pipeline.py::test_run_pipeline_invariant<br>tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending<br>tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check<br>tests/test_correction.py::test_retrieved_five_but_only_two_cited<br>tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources |
| **驗證指令** | `python -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check tests/test_correction.py::test_retrieved_five_but_only_two_cited -v` |
| **驗證結果** | FakeLLM/FakeTwinkle 驗證 pipeline 的 C6 與 verified 路徑 |
| **覆蓋功能** | note_filler.pipeline.run_pipeline — 完整 pipeline 在真 Grok 輸出下不炸 + C6 不變式 |
| **證據來源** | pyproject.toml:32, tests/test_pipeline.py:151, tests/test_pipeline.py:152 |

### 8. tests/test_questions.py::test_generate_questions_real_grok

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過 |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_questions.py::test_generate_questions_splits_multiline_string<br>tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines<br>tests/test_questions.py::test_generate_questions_strips_markdown_fence<br>tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract |
| **驗證指令** | `python -X utf8 -m pytest tests/test_questions.py::test_generate_questions_splits_multiline_string tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines tests/test_questions.py::test_generate_questions_strips_markdown_fence tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract -v` |
| **驗證結果** | FakeLLM 驗證多行回應切成乾淨問題清單、strip 與空行移除契約、markdown 圍欄解析 |
| **覆蓋功能** | note_filler.questions.generate_questions — 真模型問題生成格式與品質 |
| **證據來源** | pyproject.toml:32, tests/test_questions.py:74, tests/test_questions.py:75 |

### 9. tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 在 collection 階段排除；真跑需要 data/law_index.db、grok proxy 與 TWINKLE_HUB_TOKEN |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B<br>tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles<br>tests/test_twinkle.py::test_search_parses_source_with_full_content<br>tests/test_twinkle.py::test_search_reuses_mcp_session<br>tests/test_twinkle.py::test_search_transport_failure_returns_empty<br>tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot<br>tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty<br>tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot<br>tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous |
| **驗證指令** | `python -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles tests/test_twinkle.py::test_search_parses_source_with_full_content tests/test_twinkle.py::test_search_reuses_mcp_session tests/test_twinkle.py::test_search_transport_failure_returns_empty -v` |
| **驗證結果** | FakeLaw/FakeTwinkle 驗證 Level A 優先於 B 且級內依 distance 排序、離線 law_index 查詢產生合法 Level A 法條 Source、mock MCP/SSE 驗證全文與 Source metadata 映射 |
| **覆蓋功能** | note_filler.retrieve.retrieve_for_gap — 真實 Twinkle Hub MCP + LawLookup + Grok keyword + 排序不變式 |
| **證據來源** | pyproject.toml:32, tests/test_retrieve.py:102, tests/test_retrieve.py:103, tests/test_retrieve.py:104, tests/test_retrieve.py:106, tests/test_retrieve.py:107 |

### 10. tests/test_twinkle.py::test_search_real_twinkle_hub

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 在 collection 階段排除；真跑需要 TWINKLE_HUB_TOKEN，缺 token 時由函式內 pytest.skip 略過 |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_twinkle.py::test_search_parses_source_with_full_content<br>tests/test_twinkle.py::test_search_reuses_mcp_session<br>tests/test_twinkle.py::test_search_transport_failure_returns_empty<br>tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty<br>tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract |
| **驗證指令** | `python -X utf8 -m pytest tests/test_twinkle.py::test_search_parses_source_with_full_content tests/test_twinkle.py::test_search_reuses_mcp_session tests/test_twinkle.py::test_search_transport_failure_returns_empty tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract -v` |
| **驗證結果** | mock MCP/SSE 驗證全文 Source 與 metadata、mock MCP 驗證 session header 在三次 RPC 間傳遞、mock timeout 驗證網路失敗安全降級、mock MCP isError 驗證 MCP 協議錯誤安全降級為空結果 |
| **覆蓋功能** | note_filler.retrieve.twinkle.TwinkleClient.search — 真實 Twinkle Hub MCP 搜尋 |
| **證據來源** | pyproject.toml:32, tests/test_twinkle.py:166, tests/test_twinkle.py:170, tests/test_twinkle.py:171 |

### 11. tests/test_write.py::test_write_supplement_real_grok_grounded_output

| 項目 | 內容 |
|------|------|
| **排除條件** | `-m 'not integration'` (pyproject.toml:32) |
| **排除理由** | 預設 -m 'not integration' 排除；固定來源的 grounded writer 語意需真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過 |
| **負責 CI Job** | test-integration (workflow_dispatch) |
| **替代測試路徑** | tests/test_write.py::test_used_source_ids_from_markers<br>tests/test_write.py::test_pending_evidence_when_insufficient |
| **驗證指令** | `python -X utf8 -m pytest tests/test_write.py::test_used_source_ids_from_markers tests/test_write.py::test_pending_evidence_when_insufficient -v` |
| **驗證結果** | FakeLLM 鎖定合法註腳到實際來源 ID 的映射、FakeLLM 鎖定來源不足時保守回 pending_evidence 文本 |
| **覆蓋功能** | note_filler.write.write_supplement — 固定兩筆 Level A 來源下的真 Grok grounded 輸出 |
| **證據來源** | pyproject.toml:32, tests/test_write.py:63, tests/test_write.py:64 |

## CI Job 覆蓋矩陣

### test-pinned / test-latest (預設 CI)
- **執行指令**: `python -m pytest tests/ -m "not integration" -v`
- **覆蓋範圍**: 156 個非 integration 測試
- **排除測試**: 11 個 integration 測試 (本對照表)

### test-integration (workflow_dispatch)
- **執行指令**: `python -m pytest tests/ -m "integration" -v`
- **覆蓋範圍**: 11 個 integration 測試 (本對照表)
- **執行條件**: 需要手動觸發 workflow_dispatch，並備齊 grok proxy 與 TWINKLE_HUB_TOKEN

## 驗證指令總結

### 完整驗證所有替代測試
```bash
python -X utf8 -m pytest tests/ -m "not integration" -v
```

### 驗證特定測試的替代覆蓋
```bash
# Domain 測試替代覆蓋
python -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law tests/test_domain.py::test_detect_domain_admin tests/test_domain.py::test_detect_domain_exam tests/test_domain.py::test_detect_domain_noise_falls_back_to_other tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract -v

# E2E 測試替代覆蓋
python -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_structural_invariants tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression tests/test_pipeline.py::test_run_pipeline_invariant tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check tests/test_correction.py::test_retrieved_five_but_only_two_cited tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates -v

# Gap 測試替代覆蓋
python -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface -v

# LLM 測試替代覆蓋
python -X utf8 -m pytest tests/test_llm.py::test_grokclient_builds_request_body tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract -v

# Pipeline 測試替代覆蓋
python -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check tests/test_correction.py::test_retrieved_five_but_only_two_cited tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources -v

# Questions 測試替代覆蓋
python -X utf8 -m pytest tests/test_questions.py::test_generate_questions_splits_multiline_string tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines tests/test_questions.py::test_generate_questions_strips_markdown_fence tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract -v

# Retrieve 測試替代覆蓋
python -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles tests/test_twinkle.py::test_search_parses_source_with_full_content tests/test_twinkle.py::test_search_reuses_mcp_session tests/test_twinkle.py::test_search_transport_failure_returns_empty tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous -v

# Twinkle 測試替代覆蓋
python -X utf8 -m pytest tests/test_twinkle.py::test_search_parses_source_with_full_content tests/test_twinkle.py::test_search_reuses_mcp_session tests/test_twinkle.py::test_search_transport_failure_returns_empty tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract -v

# Write 測試替代覆蓋
python -X utf8 -m pytest tests/test_write.py::test_used_source_ids_from_markers tests/test_write.py::test_pending_evidence_when_insufficient -v
```

### 驗證 CI Gate 腳本
```bash
python scripts/validate_deselection_ci.py
```

### 執行 Integration 測試 (需外部服務)
```bash
python -X utf8 -m pytest tests/ -m "integration" -v
```

## 覆蓋缺口與緩解措施

### 覆蓋缺口總結
所有 11 個 deselected 測試的共同覆蓋缺口：
1. **真實 Grok 模型回應正確性**: 預設測試只覆蓋契約解析，不驗證實際模型輸出品質
2. **真實外部服務連線**: Twinkle Hub、Grok Proxy 的實際可用性與相容性
3. **端到端整合穩定性**: 真實服務組合下的完整流程驗證

### 緩解措施
1. **CI workflow_dispatch**: 提供手動觸發機制，在有外部服務環境下執行完整 integration 測試
2. **本地執行**: 支援本地環境設定 TWINKLE_HUB_TOKEN 與 grok proxy 後執行
3. **離線替代覆蓋**: 每個 integration 測試都有對應的離線替代測試，覆蓋關鍵路徑與契約
4. **CI Gate 驗證**: 透過 validate_deselection_ci.py 確保 deselected 集合穩定性與一致性

## 參考文件
- Allowlist: `tests/deselected_allowlist.json`
- CI 配置: `.github/workflows/ci.yml`
- Pytest 配置: `pyproject.toml`
- 驗證腳本: `scripts/validate_deselection_ci.py`
- 相關分析報告:
  - `docs/deselected-11-nodeids-final-collect-2026-07-23.md`
  - `docs/deselected-11-complete-inventory-2026-07-22.md`
  - `docs/deselected-ci-coverage-matrix-2026-07-23.md`
