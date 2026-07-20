# 非 integration 測試逐測計時審計（2026-07-20）

## 目的

對 `pytest -m "not integration" -q` 的 140 個通過測試做逐測試 wall time 計時，輸出每個 node id、累積耗時與前 10 名最慢測試，並判斷是否存在少數長尾主導約 73.31 秒的總耗時。

## 可重現命令

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -m "not integration" -q --durations=0 -vv --junitxml=docs/pytest-audit/per-test-durations-junit-2026-07-20.xml
```

原始產物：

- junit XML：`docs/pytest-audit/per-test-durations-junit-2026-07-20.xml`
- pytest 完整輸出：`docs/pytest-audit/per-test-durations-vv-2026-07-20.txt`
- 機器可讀索引：`docs/pytest-audit/per-test-durations-2026-07-20.json`
- CSV 明細：`docs/pytest-audit/per-test-durations-2026-07-20.csv`

## 執行摘要

| 項目 | 數值 |
|---|---|
| 通過測試數 | 140 |
| junit testcase 筆數 | 140 |
| 各 testcase time 加總（call+setup/teardown 由 junit 彙總） | 56.0580 s |
| junit suite time | 56.6260 s |
| 任務參考總耗時 | 73.31 s |
| 本次 pytest 摘要（vv 輸出） | 140 passed, 8 deselected in 56.67s |
| 平均每測 | 0.4004 s |
| 中位（第 71 慢） | 0.0030 s |

說明：任務提到的 **73.31 s** 為先前一次全量 wall time 參考值；本次實測 junit suite / pytest 摘要約 **56–57 s**（同篩選、同 venv）。長尾分析以 **各 testcase wall time 加總** 與 **排名累積占比** 為準，不受 session 固定開銷波動影響。

## 前 10 名最慢測試

| 排名 | wall_time_s | 累積_s | 累積占加總% | node id |
|---:|---:|---:|---:|---|
| 1 | 36.8830 | 36.8830 | 65.79% | tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable |
| 2 | 4.6860 | 41.5690 | 74.15% | tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_fails_when_deselected_allowlist_count_is_too_small |
| 3 | 3.9970 | 45.5660 | 81.28% | tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_accepts_only_authorized_deselected_nodes_with_reasons |
| 4 | 2.9140 | 48.4800 | 86.48% | tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_fails_when_deselected_allowlist_contains_non_deselected_node |
| 5 | 2.5780 | 51.0580 | 91.08% | tests/test_deselection_guard.py::test_integration_allowlist_is_stable |
| 6 | 1.1860 | 52.2440 | 93.20% | tests/test_deselection_guard.py::test_deselected_details_lists_node_ids_and_reasons |
| 7 | 0.8980 | 53.1420 | 94.80% | tests/test_requirements_test_coverage.py::test_default_gate_collects_every_equivalent_and_safety_regression |
| 8 | 0.4430 | 53.5850 | 95.59% | tests/test_law_check.py::test_search_articles_keyword_only |
| 9 | 0.2610 | 53.8460 | 96.05% | tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources |
| 10 | 0.2510 | 54.0970 | 96.50% | tests/test_export_docx.py::test_to_docx_roundtrip_preserves_original_and_marks_supplement |

- Top 1 占加總：65.79%（36.8830s）
- Top 3 占加總：81.28%（45.5660s）
- Top 5 占加總：91.08%（51.0580s）
- Top 10 占加總：**96.50%**（54.0970s）
- Top 10% 測試（n=14）占加總：**97.91%**（54.8850s）
- 達 50% 加總需前 **1** 測（36.8830s）
- 達 80% 加總需前 **3** 測（45.5660s）
- 達 90% 加總需前 **5** 測（51.0580s）

## 長尾是否主導 73.31 秒？

**是：存在極少數長尾測試主導總耗時。**

判定依據（以本次 junit 140 筆 testcase time 加總 56.058s 為分母；結構占比可套用至參考 73.31s）：

1. **單一測試即過半**：`tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable` 單獨 **36.883s（65.79%）**。
2. **Top 3 即達 81.28%**（45.566s）：再加兩個 `test_deselected_ci_gate_acceptance` 收集/允許名單閘門測試即可覆蓋八成以上。
3. **Top 5 達 91.08%**、**Top 10 達 96.50%**；其餘 130 測合計僅 **3.50%**（約 1.96s）。
4. 達 50% 加總只需前 **1** 測；達 80% 只需前 **3** 測（2.1% 的測試集合）——屬 **極端 Pareto / 長尾主導**，不是均勻分布。
5. 與參考 **73.31s** 對照：本次 suite wall **56.63s**（pytest 摘要 56.67s）。絕對秒數因機器負載/快取不同而波動，但 **時間集中在 deselection guard / CI gate 類「會再 spawn pytest collect」的少數測試** 此一結構結論穩定；8 deselected 正常，非 integration 誤跑所致。

### 結論（可稽核）

- **少數長尾主導成立**：Top 1 占 65.8%、Top 3 占 81.3%、Top 10 占 96.5%。
- 若把同一結構套到參考 73.31s，約 **48s** 級（65.8%）可歸因於最慢 1 測、約 **60s** 級（81%）可歸因於最慢 3 測（比例推估，非二次實跑 73.31s）。
- 優化優先序應鎖定：
  1. `test_substitute_mapping_is_complete_and_collectable`（~37s）
  2. 三個 `test_ci_gate_*`（合計 ~11.6s）
  3. `test_integration_allowlist_is_stable` / `test_deselected_details_*`（合計 ~3.8s）
- 其餘約 130 個單元測試合計不到 2s，再壓榨邊際效益極低；總 wall 要明顯下降，必須處理上述會重複 collect 的 guard/gate 測試，而非均勻加速全庫。

## 全量 node id 明細（依 wall time 降序）

| 排名 | wall_time_s | 累積_s | 累積% | node id |
|---:|---:|---:|---:|---|
| 1 | 36.8830 | 36.8830 | 65.79% | tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable |
| 2 | 4.6860 | 41.5690 | 74.15% | tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_fails_when_deselected_allowlist_count_is_too_small |
| 3 | 3.9970 | 45.5660 | 81.28% | tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_accepts_only_authorized_deselected_nodes_with_reasons |
| 4 | 2.9140 | 48.4800 | 86.48% | tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_fails_when_deselected_allowlist_contains_non_deselected_node |
| 5 | 2.5780 | 51.0580 | 91.08% | tests/test_deselection_guard.py::test_integration_allowlist_is_stable |
| 6 | 1.1860 | 52.2440 | 93.20% | tests/test_deselection_guard.py::test_deselected_details_lists_node_ids_and_reasons |
| 7 | 0.8980 | 53.1420 | 94.80% | tests/test_requirements_test_coverage.py::test_default_gate_collects_every_equivalent_and_safety_regression |
| 8 | 0.4430 | 53.5850 | 95.59% | tests/test_law_check.py::test_search_articles_keyword_only |
| 9 | 0.2610 | 53.8460 | 96.05% | tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources |
| 10 | 0.2510 | 54.0970 | 96.50% | tests/test_export_docx.py::test_to_docx_roundtrip_preserves_original_and_marks_supplement |
| 11 | 0.2350 | 54.3320 | 96.92% | tests/test_law_search.py::test_search_law_sources_accepts_plain_keyword_response |
| 12 | 0.1940 | 54.5260 | 97.27% | tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check |
| 13 | 0.1880 | 54.7140 | 97.60% | tests/test_parse.py::test_parse_docx_roundtrip |
| 14 | 0.1710 | 54.8850 | 97.91% | tests/test_pipeline.py::test_run_pipeline_invariant |
| 15 | 0.1650 | 55.0500 | 98.20% | tests/test_law_check.py::test_search_articles_limit |
| 16 | 0.1430 | 55.1930 | 98.46% | tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending |
| 17 | 0.1350 | 55.3280 | 98.70% | tests/test_design_acceptance.py::test_design_package_head_matches_repo_and_claim_map_printable |
| 18 | 0.0550 | 55.3830 | 98.80% | tests/test_design_acceptance.py::test_design_claims_index_is_complete |
| 19 | 0.0460 | 55.4290 | 98.88% | tests/test_server.py::test_index_returns_upload_form[asyncio] |
| 20 | 0.0370 | 55.4660 | 98.94% | tests/test_server.py::test_run_renders_two_columns[asyncio] |
| 21 | 0.0360 | 55.5020 | 99.01% | tests/test_law_lookup.py::test_search_articles_orders_by_numeric_article_no |
| 22 | 0.0340 | 55.5360 | 99.07% | tests/test_law_lookup.py::test_search_articles_limit_after_numeric_sort |
| 23 | 0.0310 | 55.5670 | 99.12% | tests/test_cli.py::test_process_file_json_format_and_outdir |
| 24 | 0.0310 | 55.5980 | 99.18% | tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty |
| 25 | 0.0240 | 55.6220 | 99.22% | tests/test_server.py::test_export_returns_markdown_attachment[asyncio] |
| 26 | 0.0230 | 55.6450 | 99.26% | tests/test_e2e_acceptance.py::test_e2e_structural_invariants |
| 27 | 0.0200 | 55.6650 | 99.30% | tests/test_grading.py::test_is_stale_under_max_age_is_not_stale |
| 28 | 0.0180 | 55.6830 | 99.33% | tests/test_design_acceptance.py::test_design_acceptance_package_is_machine_checkable |
| 29 | 0.0180 | 55.7010 | 99.36% | tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression |
| 30 | 0.0160 | 55.7170 | 99.39% | tests/test_cli.py::test_iter_inputs_expands_dir_filters_suffix_and_dedups |
| 31 | 0.0140 | 55.7310 | 99.42% | tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates |
| 32 | 0.0140 | 55.7450 | 99.44% | tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous |
| 33 | 0.0110 | 55.7560 | 99.46% | tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary |
| 34 | 0.0110 | 55.7670 | 99.48% | tests/test_server.py::test_export_without_run_returns_404[asyncio] |
| 35 | 0.0090 | 55.7760 | 99.50% | tests/test_law_check.py::test_real_law_article_exists |
| 36 | 0.0080 | 55.7840 | 99.51% | tests/test_cli.py::test_process_file_writes_md_and_counts |
| 37 | 0.0070 | 55.7910 | 99.52% | tests/test_design_acceptance.py::test_design_acceptance_rejects_claim_without_artifact |
| 38 | 0.0070 | 55.7980 | 99.54% | tests/test_domain.py::test_detect_domain_noise_falls_back_to_other |
| 39 | 0.0070 | 55.8050 | 99.55% | tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract |
| 40 | 0.0060 | 55.8110 | 99.56% | tests/test_domain.py::test_detect_domain_exam |
| 41 | 0.0060 | 55.8170 | 99.57% | tests/test_domain.py::test_detect_domain_label_with_trailing_punctuation |
| 42 | 0.0060 | 55.8230 | 99.58% | tests/test_excluded_failing_controls.py::test_control_map_covers_all_eight_excluded |
| 43 | 0.0060 | 55.8290 | 99.59% | tests/test_law_check.py::test_unknown_law_not_false_reported |
| 44 | 0.0060 | 55.8350 | 99.60% | tests/test_requirements_test_coverage.py::test_coverage_matrix_classifies_all_eight_and_has_no_missing_requirement |
| 45 | 0.0050 | 55.8400 | 99.61% | tests/test_deselection_guard.py::test_acceptance_package_rejects_count_only_summary |
| 46 | 0.0050 | 55.8450 | 99.62% | tests/test_domain.py::test_detect_domain_law |
| 47 | 0.0050 | 55.8500 | 99.63% | tests/test_domain.py::test_detect_domain_uppercase_and_whitespace |
| 48 | 0.0050 | 55.8550 | 99.64% | tests/test_export.py::test_to_markdown_format_locked |
| 49 | 0.0050 | 55.8600 | 99.65% | tests/test_law_check.py::test_fake_article_no_flagged_not_found |
| 50 | 0.0050 | 55.8650 | 99.66% | tests/test_law_check.py::test_search_articles_keyword_with_law_name |
| 51 | 0.0050 | 55.8700 | 99.66% | tests/test_llm.py::test_grokclient_builds_request_body |
| 52 | 0.0050 | 55.8750 | 99.67% | tests/test_parse.py::test_paragraph_and_document_are_frozen |
| 53 | 0.0040 | 55.8790 | 99.68% | tests/test_domain.py::test_detect_domain_admin |
| 54 | 0.0040 | 55.8830 | 99.69% | tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract |
| 55 | 0.0040 | 55.8870 | 99.69% | tests/test_gap.py::test_detect_gaps_strips_code_fence |
| 56 | 0.0040 | 55.8910 | 99.70% | tests/test_gap.py::test_detect_gaps_empty_questions_short_circuits |
| 57 | 0.0040 | 55.8950 | 99.71% | tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles |
| 58 | 0.0040 | 55.8990 | 99.72% | tests/test_law_search.py::test_search_law_sources_unions_multiple_keywords_dedup_and_order |
| 59 | 0.0040 | 55.9030 | 99.72% | tests/test_law_search.py::test_search_law_sources_non_json_treated_as_single_keyword |
| 60 | 0.0040 | 55.9070 | 99.73% | tests/test_twinkle.py::test_search_returns_empty_without_token |
| 61 | 0.0030 | 55.9100 | 99.74% | tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract |
| 62 | 0.0030 | 55.9130 | 99.74% | tests/test_export.py::test_to_json_serializes_segments |
| 63 | 0.0030 | 55.9160 | 99.75% | tests/test_export.py::test_to_markdown_pending_segment_has_no_footnote |
| 64 | 0.0030 | 55.9190 | 99.75% | tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing |
| 65 | 0.0030 | 55.9220 | 99.76% | tests/test_gap.py::test_detect_gaps_parse_failure_marks_all_missing |
| 66 | 0.0030 | 55.9250 | 99.76% | tests/test_gap.py::test_detect_gaps_non_array_json_also_fallbacks |
| 67 | 0.0030 | 55.9280 | 99.77% | tests/test_grading.py::test_grade_law_returns_A |
| 68 | 0.0030 | 55.9310 | 99.77% | tests/test_grading.py::test_is_stale_over_max_age_is_stale |
| 69 | 0.0030 | 55.9340 | 99.78% | tests/test_grading.py::test_is_stale_today_is_not_stale |
| 70 | 0.0030 | 55.9370 | 99.78% | tests/test_twinkle.py::test_search_reuses_mcp_session |
| 71 | 0.0030 | 55.9400 | 99.79% | tests/test_twinkle.py::test_search_transport_failure_returns_empty |
| 72 | 0.0030 | 55.9430 | 99.79% | tests/test_verify.py::test_two_distinct_b_verified |
| 73 | 0.0020 | 55.9450 | 99.80% | tests/test_conclusion_classification.py::test_classification_index_schema_and_labels |
| 74 | 0.0020 | 55.9470 | 99.80% | tests/test_correction.py::test_two_distinct_d_verified |
| 75 | 0.0020 | 55.9490 | 99.81% | tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface |
| 76 | 0.0020 | 55.9510 | 99.81% | tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract |
| 77 | 0.0020 | 55.9530 | 99.81% | tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot |
| 78 | 0.0020 | 55.9550 | 99.82% | tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot |
| 79 | 0.0020 | 55.9570 | 99.82% | tests/test_gap.py::test_detect_gaps_calls_llm_exactly_once |
| 80 | 0.0020 | 55.9590 | 99.82% | tests/test_grading.py::test_source_dataclass_has_locked_fields |
| 81 | 0.0020 | 55.9610 | 99.83% | tests/test_grading.py::test_grade_twinkle_returns_B |
| 82 | 0.0020 | 55.9630 | 99.83% | tests/test_grading.py::test_is_stale_exactly_max_age_is_not_stale |
| 83 | 0.0020 | 55.9650 | 99.83% | tests/test_law_check.py::test_check_law_citations_first_param_is_text |
| 84 | 0.0020 | 55.9670 | 99.84% | tests/test_law_search.py::test_search_law_sources_uses_single_llm_call_and_empty_on_no_hit |
| 85 | 0.0020 | 55.9690 | 99.84% | tests/test_law_search.py::test_search_law_sources_backward_compat_single_keyword |
| 86 | 0.0020 | 55.9710 | 99.84% | tests/test_law_search.py::test_search_law_sources_empty_keywords_returns_empty |
| 87 | 0.0020 | 55.9730 | 99.85% | tests/test_llm.py::test_fakellm_returns_canned_in_order |
| 88 | 0.0020 | 55.9750 | 99.85% | tests/test_parse.py::test_parse_txt_splits_on_blank_lines |
| 89 | 0.0020 | 55.9770 | 99.86% | tests/test_questions.py::test_generate_questions_splits_multiline_string |
| 90 | 0.0020 | 55.9790 | 99.86% | tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines |
| 91 | 0.0020 | 55.9810 | 99.86% | tests/test_questions.py::test_generate_questions_empty_response_returns_empty_list |
| 92 | 0.0020 | 55.9830 | 99.87% | tests/test_questions.py::test_generate_questions_calls_llm_exactly_once |
| 93 | 0.0020 | 55.9850 | 99.87% | tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B |
| 94 | 0.0020 | 55.9870 | 99.87% | tests/test_retrieve.py::test_retrieve_for_gap_other_domain_uses_web_not_twinkle |
| 95 | 0.0020 | 55.9890 | 99.88% | tests/test_twinkle.py::test_default_timeout_is_60 |
| 96 | 0.0020 | 55.9910 | 99.88% | tests/test_verify.py::test_two_independent_ab_sources_verified |
| 97 | 0.0020 | 55.9930 | 99.88% | tests/test_verify.py::test_three_articles_same_law_same_url_verified |
| 98 | 0.0020 | 55.9950 | 99.89% | tests/test_verify.py::test_single_a_source_verified |
| 99 | 0.0020 | 55.9970 | 99.89% | tests/test_verify.py::test_single_b_no_a_pending |
| 100 | 0.0020 | 55.9990 | 99.89% | tests/test_verify.py::test_single_c_verified |
| 101 | 0.0020 | 56.0010 | 99.90% | tests/test_verify.py::test_single_d_pending |
| 102 | 0.0020 | 56.0030 | 99.90% | tests/test_verify.py::test_two_distinct_d_verified |
| 103 | 0.0020 | 56.0050 | 99.91% | tests/test_verify.py::test_conflict_detected_and_no_side_taken |
| 104 | 0.0020 | 56.0070 | 99.91% | tests/test_verify.py::test_no_conflict_when_consistent |
| 105 | 0.0020 | 56.0090 | 99.91% | tests/test_verify.py::test_negation_substring_not_false_positive |
| 106 | 0.0020 | 56.0110 | 99.92% | tests/test_verify.py::test_independent_ab_orders_A_before_B_and_by_distance |
| 107 | 0.0020 | 56.0130 | 99.92% | tests/test_verify.py::test_distinct_by_id_not_url |
| 108 | 0.0020 | 56.0150 | 99.92% | tests/test_web.py::test_two_pages_graded_c_and_d |
| 109 | 0.0020 | 56.0170 | 99.93% | tests/test_web.py::test_drop_page_excluded |
| 110 | 0.0020 | 56.0190 | 99.93% | tests/test_web.py::test_fetch_none_skipped |
| 111 | 0.0020 | 56.0210 | 99.93% | tests/test_web.py::test_too_short_fulltext_skipped |
| 112 | 0.0020 | 56.0230 | 99.94% | tests/test_web.py::test_search_exception_degrades_to_empty |
| 113 | 0.0020 | 56.0250 | 99.94% | tests/test_web.py::test_content_truncated_with_note |
| 114 | 0.0020 | 56.0270 | 99.94% | tests/test_web.py::test_query_extraction_falls_back_to_question |
| 115 | 0.0020 | 56.0290 | 99.95% | tests/test_web.py::test_retrieve_other_domain_calls_web |
| 116 | 0.0020 | 56.0310 | 99.95% | tests/test_web.py::test_retrieve_law_domain_does_not_call_web |
| 117 | 0.0020 | 56.0330 | 99.96% | tests/test_write.py::test_used_source_ids_from_markers |
| 118 | 0.0020 | 56.0350 | 99.96% | tests/test_write.py::test_pending_evidence_when_insufficient |
| 119 | 0.0020 | 56.0370 | 99.96% | tests/test_write.py::test_out_of_range_marker_removed_and_not_used |
| 120 | 0.0010 | 56.0380 | 99.96% | tests/test_citation_formatter.py::test_build_reference_lines_two_sources |
| 121 | 0.0010 | 56.0390 | 99.97% | tests/test_conclusion_classification.py::test_classification_covers_all_eight_allowlist_nodes |
| 122 | 0.0010 | 56.0400 | 99.97% | tests/test_conclusion_classification.py::test_non_defect_items_have_no_gap_package |
| 123 | 0.0010 | 56.0410 | 99.97% | tests/test_conclusion_classification.py::test_true_gap_items_have_full_package |
| 124 | 0.0010 | 56.0420 | 99.97% | tests/test_conclusion_classification.py::test_human_report_exists_and_mentions_both_labels |
| 125 | 0.0010 | 56.0430 | 99.97% | tests/test_conclusion_classification.py::test_gap_c7_current_smoke_vacuous_pass_on_empty |
| 126 | 0.0010 | 56.0440 | 99.98% | tests/test_conclusion_classification.py::test_gap_c7_strengthened_contract_fails_on_empty |
| 127 | 0.0010 | 56.0450 | 99.98% | tests/test_conclusion_classification.py::test_gap_c7_package_acceptance_commands_are_non_empty_shell |
| 128 | 0.0010 | 56.0460 | 99.98% | tests/test_correction.py::test_original_segments_verbatim_and_immutable |
| 129 | 0.0010 | 56.0470 | 99.98% | tests/test_correction.py::test_written_two_independent_a_verified_only_used_sources |
| 130 | 0.0010 | 56.0480 | 99.98% | tests/test_correction.py::test_pending_evidence_written_empty_sources |
| 131 | 0.0010 | 56.0490 | 99.98% | tests/test_correction.py::test_retrieved_five_but_only_two_cited |
| 132 | 0.0010 | 56.0500 | 99.99% | tests/test_correction.py::test_single_a_used_source_verified |
| 133 | 0.0010 | 56.0510 | 99.99% | tests/test_correction.py::test_three_articles_same_law_same_url_verified |
| 134 | 0.0010 | 56.0520 | 99.99% | tests/test_correction.py::test_two_distinct_b_verified |
| 135 | 0.0010 | 56.0530 | 99.99% | tests/test_correction.py::test_single_b_no_a_pending |
| 136 | 0.0010 | 56.0540 | 99.99% | tests/test_correction.py::test_single_c_used_source_verified |
| 137 | 0.0010 | 56.0550 | 99.99% | tests/test_correction.py::test_single_d_used_source_pending |
| 138 | 0.0010 | 56.0560 | 100.00% | tests/test_correction.py::test_anchor_picks_keyword_overlap |
| 139 | 0.0010 | 56.0570 | 100.00% | tests/test_correction.py::test_anchor_none_when_no_overlap |
| 140 | 0.0010 | 56.0580 | 100.00% | tests/test_twinkle.py::test_search_parses_source_with_full_content |

## 證據對照（L001/L006/L019）

| 主張 | 實體產物 |
|---|---|
| 140 通過、8 deselected | `docs/pytest-audit/per-test-durations-vv-2026-07-20.txt` 末行 |
| 每測 wall time | junit XML + JSON/CSV 全 140 筆 |
| Top 10 與累積占比 | 本報告表格 + JSON `top10` / `concentration` |
| 長尾結論 | 本報告「長尾是否主導」+ JSON `long_tail_verdict` |

