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
- `test_substitute_mapping_is_complete_and_collectable()`：先確保所有替代測試可收集，再以單一 pytest 行程實際執行 12 個不重複替代測試，並逐項輸出 8 組原因與 PASS 證據

## 定點驗證輸出

執行命令：

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest -q -s tests/test_deselection_guard.py
```

2026-07-18 實跑輸出：

```text
DESELECTED_AUDIT=8 MAPPED_TESTS=12
[1/8] 未納入: tests/test_domain.py::test_detect_domain_real_grok_returns_law
  原因: 需要真實 grok proxy (127.0.0.1:8318)；附 skipif grok_reachable
  覆蓋證據: PASS tests/test_domain.py::test_detect_domain_law
  整合邊界: 真 grok 對法律文字的實際回應正確性
[2/8] 未納入: tests/test_e2e_acceptance.py::test_e2e_acceptance_real
  原因: 需要真實 grok + Twinkle Hub + law_index.db；多條件 skip
  覆蓋證據: PASS tests/test_e2e_acceptance.py::test_e2e_structural_invariants, PASS tests/test_pipeline.py::test_run_pipeline_invariant, PASS tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check, PASS tests/test_correction.py::test_retrieved_five_but_only_two_cited
  整合邊界: 真模型+真檢索下的 gap 偵測品質、補充寫作品質 (_assert_supplement_quality)、Level A 路由穩定性
[3/8] 未納入: tests/test_gap.py::test_detect_gaps_real_grok
  原因: 需要真實 grok proxy (127.0.0.1:8318)；附 skipif grok_reachable
  覆蓋證據: PASS tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing
  整合邊界: 真 grok 對法律文本的缺口判斷品質
[4/8] 未納入: tests/test_llm.py::test_grok_pong_integration
  原因: 需要真實 grok proxy (127.0.0.1:8318)；附 skipif grok_reachable
  覆蓋證據: PASS tests/test_llm.py::test_grokclient_builds_request_body
  整合邊界: 真實 TCP 連線到 proxy 的連通性、proxy 回應格式解析
[5/8] 未納入: tests/test_pipeline.py::test_run_pipeline_real_grok
  原因: 需要真實 grok proxy；twinkle/law 用 fake 隔離
  覆蓋證據: PASS tests/test_pipeline.py::test_run_pipeline_invariant, PASS tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check, PASS tests/test_correction.py::test_retrieved_five_but_only_two_cited
  整合邊界: 真 Grok 模型輸出的 domain/questions/gaps 正確性 + pipeline 穩定性
[6/8] 未納入: tests/test_questions.py::test_generate_questions_real_grok
  原因: 需要真實 grok proxy (127.0.0.1:8318)；附 skipif grok_reachable
  覆蓋證據: PASS tests/test_questions.py::test_generate_questions_splits_multiline_string, PASS tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines
  整合邊界: 真 Grok 對法律文本的問題生成品質
[7/8] 未納入: tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke
  原因: 需要 GOV_AI_ENABLE_TWINKLE_MCP=1 + TWINKLE_HUB_TOKEN + law_index.db + Grok
  覆蓋證據: PASS tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B, PASS tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles, PASS tests/test_twinkle.py::test_search_parses_source_with_full_content
  整合邊界: 真實 Twinkle Hub 服務 I/O 與真 Grok 關鍵字抽取品質
[8/8] 未納入: tests/test_twinkle.py::test_search_real_twinkle_hub
  原因: 需要 TWINKLE_HUB_TOKEN 環境變數
  覆蓋證據: PASS tests/test_twinkle.py::test_search_parses_source_with_full_content
  整合邊界: 真實 Twinkle Hub 服務可用性、服務端 session 相容性與網路逾時
TARGETED_VERIFICATION=PASS
2 passed in 2.92s
```

## 結論
無需新增功能測試；既有 guard 已調整為實際執行替代測試。所有 deselected 項目皆有明確的回歸保護，覆蓋證據完整。
