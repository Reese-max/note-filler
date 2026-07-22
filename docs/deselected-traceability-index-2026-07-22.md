# Deselected 測試可追溯索引

> 產生日期：2026-07-22
> 基準集合：163 collected / 152 selected / 11 deselected
> 唯一排除機制：`pyproject.toml` `[tool.pytest.ini_options].addopts` → `-m 'not integration'`
> 機器可讀索引：`tests/deselected_allowlist.json`（11 筆）

---

## 總覽

| # | deselected 測試 | marker 位置 | runtime skip 條件 |
|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `test_domain.py:62` | `skipif(not _grok_reachable())` :63 |
| 2 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | `test_domain.py:76` | `skipif(not _grok_reachable())` :77 |
| 3 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `test_e2e_acceptance.py:244` | inline `pytest.skip()` :248,251（缺 law_db / grok / token） |
| 4 | `tests/test_gap.py::test_detect_gaps_real_grok` | `test_gap.py:83` | `skipif(not _grok_reachable())` :84 |
| 5 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | `test_gap.py:106` | `skipif(not _grok_reachable())` :107 |
| 6 | `tests/test_llm.py::test_grok_pong_integration` | `test_llm.py:95` | `skipif(not _grok_reachable())` :96 |
| 7 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `test_pipeline.py:151` | `skipif(not _grok_reachable())` :152 |
| 8 | `tests/test_questions.py::test_generate_questions_real_grok` | `test_questions.py:74` | `skipif(not _grok_reachable())` :75 |
| 9 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `test_retrieve.py:102` | `skipif` :103-104 + inline :108（law_db / grok / token） |
| 10 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `test_twinkle.py:166` | inline `pytest.skip()` :172（缺 token） |
| 11 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | `test_write.py:63` | `skipif(not _grok_reachable())` :64 |

**集合恆等式**（經反向驗證）：
- `full(163) \ default(152) == integration(11)`
- `default ∪ integration == full`、`default ∩ integration == ∅`
- 除 `-m 'not integration'` 外無第二層篩選（無 `-k`、無 `--deselect`）

---

## 逐項可追溯索引

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_domain.py:62` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch` 手動觸發 |
| **替代路徑** | `tests/test_domain.py::test_detect_domain_law`（:19）— 同一 `detect_domain()` 入口、FakeLLM 鎖定 law 回傳 |
| | `tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract`（:70）— failing-first 對照 |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract -q` |
| **NOT-REPRODUCIBLE 證據** | `docs/excluded-failing-controls-2026-07-19.md` — domain 標籤 determinism 對照穩定 PASS |
| **coverage_gap** | 真 grok 對法律文字的實際回應正確性（FakeLLM 不驗模型品質） |

---

### 2. `tests/test_domain.py::test_detect_domain_real_grok_representative_domains`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_domain.py:76` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch` 手動觸發 |
| **替代路徑** | `tests/test_domain.py::test_detect_domain_law`（:19）— FakeLLM 鎖定 law |
| | `tests/test_domain.py::test_detect_domain_admin`（:24）— FakeLLM 鎖定 admin |
| | `tests/test_domain.py::test_detect_domain_exam`（:29）— FakeLLM 鎖定 exam |
| | `tests/test_domain.py::test_detect_domain_noise_falls_back_to_other`（:35）— FakeLLM 鎖定 other |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law tests/test_domain.py::test_detect_domain_admin tests/test_domain.py::test_detect_domain_exam tests/test_domain.py::test_detect_domain_noise_falls_back_to_other -q` |
| **NOT-REPRODUCIBLE 證據** | **【待補證】** — 無對應 failing-controls 或 blind-spot 文檔；allowlist.json 中有 substitute_evidence 但未有獨立 NOT-REPRODUCIBLE 判定文件 |
| **coverage_gap** | 真模型四類代表文本語意矩陣的分類品質；替代只覆蓋標籤解析契約 |

---

### 3. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_e2e_acceptance.py:244` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch`，需 grok + Twinkle + law_db |
| **替代路徑** | `tests/test_e2e_acceptance.py::test_e2e_structural_invariants`（:170）— 離線四硬不變式 |
| | `tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary`（:204）— 離線品質邊界 |
| | `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression`（:223）— 最小品質閘 |
| | `tests/test_pipeline.py::test_run_pipeline_invariant`（:85）— C6 + verified |
| | `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`（:145）— 畸形降級 |
| | `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`（:122）— 法規查核 |
| | `tests/test_correction.py::test_retrieved_five_but_only_two_cited`（:82）— 只掛引用來源 |
| | `tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates`（:145）— failing-first |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_structural_invariants tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression tests/test_pipeline.py::test_run_pipeline_invariant tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check tests/test_correction.py::test_retrieved_five_but_only_two_cited tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates -q` |
| **NOT-REPRODUCIBLE 證據** | `docs/excluded-failing-controls-2026-07-19.md`、`docs/minimal-quality-gates-regression-2026-07-19.md`、`docs/e2e-offline-quality-boundary-2026-07-18.md` |
| **coverage_gap** | 真模型+真檢索下的 gap 偵測品質、補充寫作品質、Level A 路由穩定性 |

---

### 4. `tests/test_gap.py::test_detect_gaps_real_grok`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_gap.py:83` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch` 手動觸發 |
| **替代路徑** | `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`（:26）— FakeLLM 驗 covered 過濾 |
| | `tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface`（:175）— failing-first |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface -q` |
| **NOT-REPRODUCIBLE 證據** | `docs/excluded-failing-controls-2026-07-19.md` — 缺口過濾 determinism 對照穩定 PASS |
| **coverage_gap** | 真 grok 對法律文本的缺口判斷品質（FakeLLM 不驗模型理解能力） |

---

### 5. `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_gap.py:106` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch` 手動觸發 |
| **替代路徑** | `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`（:26）— FakeLLM 驗 covered 過濾 |
| | `tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface`（:175）— 離線對照 |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface -q` |
| **NOT-REPRODUCIBLE 證據** | **【待補證】** — 無獨立 NOT-REPRODUCIBLE 判定文件；allowlist.json 有 substitute_evidence 但未有盲區或控制對照的獨立驗證文檔 |
| **coverage_gap** | 真模型對筆記涵蓋度的語意判斷；替代只覆蓋解析與過濾邏輯 |

---

### 6. `tests/test_llm.py::test_grok_pong_integration`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_llm.py:95` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch` 手動觸發 |
| **替代路徑** | `tests/test_llm.py::test_grokclient_builds_request_body`（:54）— monkeypatch 驗請求結構與回應解析 |
| | `tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract`（:211）— failing-first PONG 契約 |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_llm.py::test_grokclient_builds_request_body tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract -q` |
| **NOT-REPRODUCIBLE 證據** | `docs/excluded-failing-controls-2026-07-19.md` — GrokClient parse/endpoint 對照 PASS |
| **coverage_gap** | 真實 TCP 連線到 proxy 的連通性、proxy 回應格式解析 |

---

### 7. `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_pipeline.py:151` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch`，需 grok proxy |
| **替代路徑** | `tests/test_pipeline.py::test_run_pipeline_invariant`（:85）— C6 + verified |
| | `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`（:145）— 畸形降級 |
| | `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`（:122）— 法規查核 |
| | `tests/test_correction.py::test_retrieved_five_but_only_two_cited`（:82）— 只掛引用來源 |
| | `tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources`（:274）— failing-first |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check tests/test_correction.py::test_retrieved_five_but_only_two_cited tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources -q` |
| **NOT-REPRODUCIBLE 證據** | `docs/excluded-failing-controls-2026-07-19.md` — C6 pending_evidence 對照 PASS |
| **coverage_gap** | 真 Grok 模型輸出的 domain/questions/gaps 正確性 + pipeline 穩定性 |

---

### 8. `tests/test_questions.py::test_generate_questions_real_grok`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_questions.py:74` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch` 手動觸發 |
| **替代路徑** | `tests/test_questions.py::test_generate_questions_splits_multiline_string`（:25）— 多行解析 |
| | `tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines`（:38）— strip + 空行移除 |
| | `tests/test_questions.py::test_generate_questions_strips_markdown_fence`（:104）— markdown 圍欄剝除 |
| | `tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract`（:292）— failing-first |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_questions.py::test_generate_questions_splits_multiline_string tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines tests/test_questions.py::test_generate_questions_strips_markdown_fence tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract -q` |
| **NOT-REPRODUCIBLE 證據** | `docs/excluded-failing-controls-2026-07-19.md` — 問題清單契約對照 PASS |
| **coverage_gap** | 真 Grok 對法律文本的問題生成品質 |

---

### 9. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_retrieve.py:102` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch`，需 grok + token + law_db |
| **替代路徑** | `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B`（:72）— Level A/B 排序 |
| | `tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles`（:35）— 離線 LawLookup |
| | `tests/test_twinkle.py::test_search_parses_source_with_full_content`（:77）— mock MCP/SSE |
| | `tests/test_twinkle.py::test_search_reuses_mcp_session`（:120）— session 重用 |
| | `tests/test_twinkle.py::test_search_transport_failure_returns_empty`（:133）— timeout 降級 |
| | `tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot`（:68）— vacuous 證明 |
| | `tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`（:87）— law Level A 非空 |
| | `tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot`（:314）— failing-first |
| | `tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous`（:326）— law Level A 對照 |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles tests/test_twinkle.py::test_search_parses_source_with_full_content tests/test_twinkle.py::test_search_reuses_mcp_session tests/test_twinkle.py::test_search_transport_failure_returns_empty tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous -q` |
| **NOT-REPRODUCIBLE 證據** | `docs/excluded-failing-controls-2026-07-19.md`、`docs/exclusion-correctness-blind-spot-2026-07-19.md` — law Level A 非空穩定 PASS |
| **coverage_gap** | 真實 Twinkle Hub 服務 I/O 與真 Grok 關鍵字抽取品質；smoke vacuous pass 已由離線盲區鎖定 |

---

### 10. `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_twinkle.py:166` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch`，需 `TWINKLE_HUB_TOKEN` |
| **替代路徑** | `tests/test_twinkle.py::test_search_parses_source_with_full_content`（:77）— mock MCP/SSE Source |
| | `tests/test_twinkle.py::test_search_reuses_mcp_session`（:120）— session 重用 |
| | `tests/test_twinkle.py::test_search_transport_failure_returns_empty`（:133）— timeout 降級 |
| | `tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty`（:163）— MCP 錯誤降級 |
| | `tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract`（:408）— failing-first |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_twinkle.py::test_search_parses_source_with_full_content tests/test_twinkle.py::test_search_reuses_mcp_session tests/test_twinkle.py::test_search_transport_failure_returns_empty tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract -q` |
| **NOT-REPRODUCIBLE 證據** | `docs/excluded-failing-controls-2026-07-19.md` — Twinkle Source 解析契約對照 PASS |
| **coverage_gap** | 真實 Twinkle Hub 服務可用性、session 相容性與網路逾時 |

---

### 11. `tests/test_write.py::test_write_supplement_real_grok_grounded_output`

| 欄位 | 值 |
|---|---|
| **排除規則** | `pyproject.toml:32` addopts `-m 'not integration'`；marker `test_write.py:63` |
| **CI/job** | `test-integration`（`.github/workflows/ci.yml:73`）— `workflow_dispatch` 手動觸發 |
| **替代路徑** | `tests/test_write.py::test_used_source_ids_from_markers`（:34）— FakeLLM 註腳到來源映射 |
| | `tests/test_write.py::test_pending_evidence_when_insufficient`（:42）— 來源不足降級 |
| **可重跑命令** | `& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_write.py::test_used_source_ids_from_markers tests/test_write.py::test_pending_evidence_when_insufficient -q` |
| **NOT-REPRODUCIBLE 證據** | **【待補證】** — 無獨立 NOT-REPRODUCIBLE 判定文件；allowlist.json 有 substitute_evidence 但未有盲區或控制對照的獨立驗證文檔 |
| **coverage_gap** | 真模型能否只依固定來源寫出帶有效註腳的補充 |

---

## 驗證缺口彙總

| # | deselected 測試 | 缺口類型 | 說明 |
|---|---|---|---|
| 2 | `test_detect_domain_real_grok_representative_domains` | **已解決** | 新增 `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md` |
| 5 | `test_detect_gaps_real_grok_semantic_matrix` | **已解決** | 新增 `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md` |
| 11 | `test_write_supplement_real_grok_grounded_output` | **已解決** | 新增 `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md` |

> 以上 3 筆原缺少像其他 8 筆那樣的獨立驗證文件來正式判定 `NOT-REPRODUCIBLE`。
> 已於 2026-07-22 新增 `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md` 補充驗證，
> 並更新 `tests/test_deselection_guard.py` 中的 `_NOT_REPRODUCIBLE_EVIDENCE` 映射。

---

## 穩定性控制機制

| 控制 | 路徑 | 作用 |
|---|---|---|
| allowlist 守衛 | `tests/test_deselection_guard.py::test_integration_allowlist_is_stable` | 運行時比對 `pytest --collect-only -m integration` 與 `ALLOWED_INTEGRATION_TESTS` |
| 替代映射守衛 | `tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable` | 逐項確認 11 筆替代映射存在、可收集、可通過 |
| CI gate 驗收 | `tests/test_deselected_ci_gate_acceptance.py` | 確認 gate 腳本只接受 authorized deselected nodes |
| CI gate 腳本 | `scripts/validate_deselection_ci.py` | 比對實際 deselected 與 allowlist，輸出稽核報告 |
| C7 correctness 回歸 | `tests/test_deselection_guard.py::test_c7_correctness_path_law_domain_level_a_not_excluded` | law+LawLookup 不得因 -m 'not integration' 被排除 |

---

## 重現命令速查

```powershell
# 預設品質門（非整合，152 passed + 11 deselected）
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest -m "not integration" -q

# 全量基線（含 integration，163 collected）
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest -o "addopts=" -q

# 只跑 integration（11 個，需 grok proxy）
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest -m "integration" -q

# deselected 詳情
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -q --deselected-details

# CI gate 驗證
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 scripts/validate_deselection_ci.py

# 守衛測試
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_deselection_guard.py tests/test_deselected_ci_gate_acceptance.py -q

# 替代映射驗證
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_requirements_test_coverage.py -q
```

---

## 關聯文件

| 文件 | 內容 |
|---|---|
| `tests/deselected_allowlist.json` | 機器可讀索引（11 筆 node ID、排除原因、替代映射、gap mitigation） |
| `docs/pytest_deselected_audit.md` | 原版 8 筆整合測試對照清單（2026-07-18） |
| `docs/pytest-deselected-exact-filter-reason-2026-07-21.md` | 確切篩選原因稽核（反向驗證、集合恆等式） |
| `docs/pytest-acceptance-selection-audit-2026-07-21.md` | 驗收參數與環境盤點 |
| `docs/pytest-audit/deselected-ci-gate.md` | CI gate 稽核報告 |
| `docs/pytest-audit/requirements-test-coverage-2026-07-19.json` | 需求分類與等價覆蓋矩陣 |
| `.github/workflows/ci.yml` | CI workflow（test-pinned / test-latest / test-integration） |
| `scripts/run_tests.sh` | 本機執行腳本（unit / all / integ / check） |
| `scripts/validate_deselection_ci.py` | CI deselected 政策驗證腳本 |
