# 擴充驗收套件（Acceptance Package）

> 產生時間：`2026-07-19T01:55:54+08:00`
>
> schema：`note-filler.deselected-acceptance/v1`
>
> **禁止僅以 collected/selected/deselected 彙總數字驗收；必須具備下列欄位**

## 完整 pytest invocation

- **collect_all**: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest --collect-only -q -o addopts= --strict-markers`
- **collect_default**: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest --collect-only -q`
- **collect_integration**: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest --collect-only -q -o addopts= --strict-markers -m integration`
- **deselected_details**: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest --collect-only -q --deselected-details`
- **default_test_run**: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest -vv --no-header --tb=short --deselected-details --color=no`
- **markers**: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest --markers`

## 彙總數字（僅上下文）

`collected=121 selected=113 deselected=8`

上述數字**不可**單獨作為驗收通過依據。

## 8 個 node ID × 排除原因 × 單獨結果 × 失敗/NOT-REPRODUCIBLE

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

- 排除原因：預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
- collection 原因：`deselected by -m 'not integration'`
- 替代測試單獨結果：
  - **PASSED** `tests/test_domain.py::test_detect_domain_law` — `tests/test_domain.py::test_detect_domain_law PASSED                      [ 19%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law -vv --tb=line --color=no`
- live 單獨執行：`pass` (exit=0, wall_s=5.44)
  - source: `docs/pytest-audit/deselected-individual-results-2026-07-19.json`
  - invocation template: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_domain.py::test_detect_domain_real_grok_returns_law -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" -v --tb=short`
- 失敗／NOT-REPRODUCIBLE：（無）

### 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

- 排除原因：預設 -m 'not integration' 在 collection 階段排除；真跑需要 data/law_index.db、grok proxy 與 TWINKLE_HUB_TOKEN，任一前置條件不足即 skip
- collection 原因：`deselected by -m 'not integration'`
- 替代測試單獨結果：
  - **PASSED** `tests/test_e2e_acceptance.py::test_e2e_structural_invariants` — `tests/test_e2e_acceptance.py::test_e2e_structural_invariants PASSED      [ 24%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_structural_invariants -vv --tb=line --color=no`
  - **PASSED** `tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary` — `tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary PASSED [ 25%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary -vv --tb=line --color=no`
  - **PASSED** `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression` — `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression PASSED [ 26%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression -vv --tb=line --color=no`
  - **PASSED** `tests/test_pipeline.py::test_run_pipeline_invariant` — `tests/test_pipeline.py::test_run_pipeline_invariant PASSED               [ 62%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -vv --tb=line --color=no`
  - **PASSED** `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending` — `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending PASSED [ 64%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending -vv --tb=line --color=no`
  - **PASSED** `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check` — `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check PASSED [ 63%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check -vv --tb=line --color=no`
  - **PASSED** `tests/test_correction.py::test_retrieved_five_but_only_two_cited` — `tests/test_correction.py::test_retrieved_five_but_only_two_cited PASSED  [  7%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_correction.py::test_retrieved_five_but_only_two_cited -vv --tb=line --color=no`
- live 單獨執行：`pass` (exit=0, wall_s=118.5)
  - source: `docs/pytest-audit/deselected-individual-results-2026-07-19.json`
  - invocation template: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_acceptance_real -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" -v --tb=short`
- 失敗／NOT-REPRODUCIBLE：
  - **NOT-REPRODUCIBLE** — 離線最小品質閘與 supplement 品質邊界皆穩定 PASS，無法以產品失敗重現 — `docs/minimal-quality-gates-regression-2026-07-19.md`
  - **NOT-REPRODUCIBLE** — e2e offline quality boundary 無法穩定失敗 — `docs/e2e-offline-quality-boundary-2026-07-18.md`

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`

- 排除原因：預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
- collection 原因：`deselected by -m 'not integration'`
- 替代測試單獨結果：
  - **PASSED** `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing` — `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing PASSED [ 32%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing -vv --tb=line --color=no`
- live 單獨執行：`pass` (exit=0, wall_s=5.74)
  - source: `docs/pytest-audit/deselected-individual-results-2026-07-19.json`
  - invocation template: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_real_grok -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" -v --tb=short`
- 失敗／NOT-REPRODUCIBLE：（無）

### 4. `tests/test_llm.py::test_grok_pong_integration`

- 排除原因：預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
- collection 原因：`deselected by -m 'not integration'`
- 替代測試單獨結果：
  - **PASSED** `tests/test_llm.py::test_grokclient_builds_request_body` — `tests/test_llm.py::test_grokclient_builds_request_body PASSED            [ 59%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_llm.py::test_grokclient_builds_request_body -vv --tb=line --color=no`
- live 單獨執行：`pass` (exit=0, wall_s=1.94)
  - source: `docs/pytest-audit/deselected-individual-results-2026-07-19.json`
  - invocation template: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_llm.py::test_grok_pong_integration -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" -v --tb=short`
- 失敗／NOT-REPRODUCIBLE：（無）

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

- 排除原因：預設 -m 'not integration' 在 collection 階段排除；只要真實 grok proxy 才能執行，Twinkle 與 law 雖以 fake 隔離仍保留 integration 邊界
- collection 原因：`deselected by -m 'not integration'`
- 替代測試單獨結果：
  - **PASSED** `tests/test_pipeline.py::test_run_pipeline_invariant` — `tests/test_pipeline.py::test_run_pipeline_invariant PASSED               [ 62%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -vv --tb=line --color=no`
  - **PASSED** `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending` — `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending PASSED [ 64%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending -vv --tb=line --color=no`
  - **PASSED** `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check` — `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check PASSED [ 63%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check -vv --tb=line --color=no`
  - **PASSED** `tests/test_correction.py::test_retrieved_five_but_only_two_cited` — `tests/test_correction.py::test_retrieved_five_but_only_two_cited PASSED  [  7%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_correction.py::test_retrieved_five_but_only_two_cited -vv --tb=line --color=no`
- live 單獨執行：`pass` (exit=0, wall_s=67.3)
  - source: `docs/pytest-audit/deselected-individual-results-2026-07-19.json`
  - invocation template: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_real_grok -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" -v --tb=short`
- 失敗／NOT-REPRODUCIBLE：（無）

### 6. `tests/test_questions.py::test_generate_questions_real_grok`

- 排除原因：預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
- collection 原因：`deselected by -m 'not integration'`
- 替代測試單獨結果：
  - **PASSED** `tests/test_questions.py::test_generate_questions_splits_multiline_string` — `tests/test_questions.py::test_generate_questions_splits_multiline_string PASSED [ 65%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_questions.py::test_generate_questions_splits_multiline_string -vv --tb=line --color=no`
  - **PASSED** `tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines` — `tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines PASSED [ 66%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines -vv --tb=line --color=no`
- live 單獨執行：`pass` (exit=0, wall_s=6.59)
  - source: `docs/pytest-audit/deselected-individual-results-2026-07-19.json`
  - invocation template: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_questions.py::test_generate_questions_real_grok -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" -v --tb=short`
- 失敗／NOT-REPRODUCIBLE：（無）

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

- 排除原因：預設 -m 'not integration' 在 collection 階段排除；真跑需要 data/law_index.db、grok proxy、GOV_AI_ENABLE_TWINKLE_MCP=1 與 TWINKLE_HUB_TOKEN
- collection 原因：`deselected by -m 'not integration'`
- 替代測試單獨結果：
  - **PASSED** `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B` — `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B PASSED [ 69%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B -vv --tb=line --color=no`
  - **PASSED** `tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles` — `tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles PASSED [ 52%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles -vv --tb=line --color=no`
  - **PASSED** `tests/test_twinkle.py::test_search_parses_source_with_full_content` — `tests/test_twinkle.py::test_search_parses_source_with_full_content PASSED [ 74%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_parses_source_with_full_content -vv --tb=line --color=no`
  - **PASSED** `tests/test_twinkle.py::test_search_reuses_mcp_session` — `tests/test_twinkle.py::test_search_reuses_mcp_session PASSED             [ 76%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_reuses_mcp_session -vv --tb=line --color=no`
  - **PASSED** `tests/test_twinkle.py::test_search_transport_failure_returns_empty` — `tests/test_twinkle.py::test_search_transport_failure_returns_empty PASSED [ 76%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_transport_failure_returns_empty -vv --tb=line --color=no`
  - **PASSED** `tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot` — `tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot PASSED [ 27%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot -vv --tb=line --color=no`
  - **PASSED** `tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty` — `tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty PASSED [ 28%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty -vv --tb=line --color=no`
- live 單獨執行：`pass` (exit=0, wall_s=7.28)
  - source: `docs/pytest-audit/deselected-individual-results-2026-07-19.json`
  - invocation template: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" -v --tb=short`
- 失敗／NOT-REPRODUCIBLE：
  - **NOT-REPRODUCIBLE** — 產品 law+LawLookup 路徑穩定回 Level A 非空；產品缺陷路徑不可重現 — `docs/exclusion-correctness-blind-spot-2026-07-19.md`

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

- 排除原因：預設 -m 'not integration' 在 collection 階段排除；真跑需要 TWINKLE_HUB_TOKEN，缺 token 時由函式內 pytest.skip 略過
- collection 原因：`deselected by -m 'not integration'`
- 替代測試單獨結果：
  - **PASSED** `tests/test_twinkle.py::test_search_parses_source_with_full_content` — `tests/test_twinkle.py::test_search_parses_source_with_full_content PASSED [ 74%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_parses_source_with_full_content -vv --tb=line --color=no`
  - **PASSED** `tests/test_twinkle.py::test_search_reuses_mcp_session` — `tests/test_twinkle.py::test_search_reuses_mcp_session PASSED             [ 76%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_reuses_mcp_session -vv --tb=line --color=no`
  - **PASSED** `tests/test_twinkle.py::test_search_transport_failure_returns_empty` — `tests/test_twinkle.py::test_search_transport_failure_returns_empty PASSED [ 76%]`
    - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_transport_failure_returns_empty -vv --tb=line --color=no`
- live 單獨執行：`pass` (exit=0, wall_s=4.58)
  - source: `docs/pytest-audit/deselected-individual-results-2026-07-19.json`
  - invocation template: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_real_twinkle_hub -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" -v --tb=short`
- 失敗／NOT-REPRODUCIBLE：（無）

## 失敗測試或 NOT-REPRODUCIBLE 索引

- `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` — **NOT-REPRODUCIBLE** — 離線最小品質閘與 supplement 品質邊界皆穩定 PASS，無法以產品失敗重現 — `docs/minimal-quality-gates-regression-2026-07-19.md`
- `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` — **NOT-REPRODUCIBLE** — e2e offline quality boundary 無法穩定失敗 — `docs/e2e-offline-quality-boundary-2026-07-18.md`
- `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` — **NOT-REPRODUCIBLE** — 產品 law+LawLookup 路徑穩定回 Level A 非空；產品缺陷路徑不可重現 — `docs/exclusion-correctness-blind-spot-2026-07-19.md`
