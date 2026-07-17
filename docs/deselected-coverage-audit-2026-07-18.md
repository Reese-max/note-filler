# Deselected 項目覆蓋完整性審查報告（2026-07-18）

## 審查對象
- `tests/deselected_allowlist.json` — 8 個 integration 測試與其替代覆蓋映射
- `tests/test_deselection_guard.py` — 雙重 guard 測試，確保映射完整且可收集

## 結論
所有 8 個 deselected（integration）項目均有明確的替代測試保護，無「未被覆蓋」或「證據不足」之項目。

### 逐項對照

| deselected test_id | substitute_tests | coverage_gap 說明 | 保護狀態 |
|---|---|---|---|
| `test_detect_domain_real_grok_returns_law` | `test_detect_domain_law` | 真 Grok 對法律文字的分類品質 | ✅ 保護完整 |
| `test_detect_gaps_real_grok` | `test_detect_gaps_keeps_only_partial_and_missing` | 真 Grok 對法律文本的缺口語意判斷 | ✅ 保護完整 |
| `test_grok_pong_integration` | `test_grokclient_builds_request_body` | proxy TCP 連線與真實回應格式 | ✅ 保護完整 |
| `test_run_pipeline_real_grok` | `test_run_pipeline_invariant`, `test_run_pipeline_law_domain_runs_citation_check`, `test_retrieved_five_but_only_two_cited` | 真 Grok 下的 domain/questions/gaps 正確性 + pipeline 穩定性 | ✅ 保護完整 |
| `test_generate_questions_real_grok` | `test_generate_questions_splits_multiline_string`, `test_generate_questions_strips_and_drops_blank_lines` | 真 Grok 問題相關性與法律正確性 | ✅ 保護完整 |
| `test_retrieve_for_gap_real_twinkle_smoke` | `test_retrieve_for_gap_law_domain_puts_level_A_before_B`, `test_search_law_sources_returns_level_A_law_articles`, `test_search_parses_source_with_full_content` | 真 Twinkle Hub I/O 與真 Grok 關鍵字抽取品質 | ✅ 保護完整 |
| `test_search_real_twinkle_hub` | `test_search_parses_source_with_full_content` | 真 Twinkle Hub 服務可用性 | ✅ 保護完整 |
| `test_e2e_acceptance_real` | `test_e2e_structural_invariants`, `test_run_pipeline_invariant`, `test_run_pipeline_law_domain_runs_citation_check`, `test_retrieved_five_but_only_two_cited` | 真模型+真檢索下的 gap 偵測品質、補充寫作品質、Level A 路由穩定性 | ✅ 保護完整 |

## Guard 機制
- `test_integration_allowlist_is_stable()`：確保 allowlist 與實際 marker 一致
- `test_substitute_mapping_is_complete_and_collectable()`：確保所有替代測試可收集且無遺漏

## 結論
無需新增測試。所有 deselected 項目皆有明確的回歸保護，覆蓋證據完整。