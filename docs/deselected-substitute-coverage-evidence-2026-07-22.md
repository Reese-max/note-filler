# Deselected 測試替代覆蓋證據完整報告

> **產出日期**：2026-07-22
> **範圍**：11 個被 `-m 'not integration'` 排除的測試
> **目的**：提供每個 deselected 測試的可稽核替代覆蓋證據

## 執行環境

- Python 路徑: `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe`
- 執行參數: `-X utf8`
- 工作目錄: `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\3b14b39f`

## CI 覆蓋機制

### 主要 CI Jobs
- **test-pinned**: `python -m pytest tests/ -m "not integration" -v` (預設執行)
- **test-latest**: `python -m pytest tests/ -m "not integration" -v` (預設執行)
- **test-integration**: `python -m pytest tests/ -m "integration" -v` (workflow_dispatch 手動觸發)

### CI Gate 驗證
```bash
python scripts/validate_deselection_ci.py
```

## 逐項替代覆蓋證據

### 1. test_detect_domain_real_grok_returns_law

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.domain.detect_domain` — LLM 領域偵測 (law/admin/exam/other)

#### 替代測試
- `tests/test_domain.py::test_detect_domain_law`
- `tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract`

#### 執行證據
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract -v
```

**結果**: PASSED (參見 `docs/excluded-failing-controls-2026-07-19.md`)

#### NOT-REPRODUCIBLE 判定
- domain 標籤 determinism 對照 PASS
- 真模型語意品質缺口無法以產品失敗重現
- 證據來源: `docs/excluded-failing-controls-2026-07-19.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 grok proxy)

---

### 2. test_detect_domain_real_grok_representative_domains

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.domain.detect_domain` — 真 Grok 四類代表文本語意矩陣

#### 替代測試
- `tests/test_domain.py::test_detect_domain_law`
- `tests/test_domain.py::test_detect_domain_admin`
- `tests/test_domain.py::test_detect_domain_exam`
- `tests/test_domain.py::test_detect_domain_noise_falls_back_to_other`

#### 執行證據
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law tests/test_domain.py::test_detect_domain_admin tests/test_domain.py::test_detect_domain_exam tests/test_domain.py::test_detect_domain_noise_falls_back_to_other -v
```

**結果**: 
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\3b14b39f
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 4 items

tests/test_domain.py::test_detect_domain_law PASSED                      [ 25%]
tests/test_domain.py::test_detect_domain_admin PASSED                    [ 50%]
tests/test_domain.py::test_detect_domain_exam PASSED                     [ 75%]
tests/test_domain.py::test_detect_domain_noise_falls_back_to_other PASSED [100%]

============================== 4 passed in 0.32s ==============================
```

#### NOT-REPRODUCIBLE 判定
- 四類標籤解析契約對照 PASS
- 真模型四類代表文本語意分類品質無法以產品失敗重現
- 證據來源: `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 grok proxy)

---

### 3. test_e2e_acceptance_real

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: §12 端到端驗收: parse→domain→questions→gaps→retrieve→assemble→export; 5 個硬不變式

#### 替代測試
- `tests/test_e2e_acceptance.py::test_e2e_structural_invariants`
- `tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary`
- `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression`
- `tests/test_pipeline.py::test_run_pipeline_invariant`
- `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`
- `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`
- `tests/test_correction.py::test_retrieved_five_but_only_two_cited`
- `tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates`

#### 執行證據
**結果**: PASSED (參見 `docs/excluded-failing-controls-2026-07-19.md`)

#### NOT-REPRODUCIBLE 判定
- 離線四硬閘 failing-first 對照穩定 PASS
- 真模型+真檢索下的 gap 偵測品質、補充寫作品質無法以產品失敗重現
- 證據來源: `docs/excluded-failing-controls-2026-07-19.md`, `docs/minimal-quality-gates-regression-2026-07-19.md`, `docs/e2e-offline-quality-boundary-2026-07-18.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 grok proxy + Twinkle + law_index.db)

---

### 4. test_detect_gaps_real_grok

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.gap.detect_gaps` — LLM 缺口偵測 (partial/missing 過濾)

#### 替代測試
- `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`
- `tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface`

#### 執行證據
**結果**: PASSED (參見 `docs/excluded-failing-controls-2026-07-19.md`)

#### NOT-REPRODUCIBLE 判定
- 缺口過濾 determinism 對照 PASS
- 真模型缺口判斷品質無法以產品失敗重現
- 證據來源: `docs/excluded-failing-controls-2026-07-19.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 grok proxy)

---

### 5. test_detect_gaps_real_grok_semantic_matrix

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.gap.detect_gaps` — 真 Grok covered/missing 對照語意

#### 替代測試
- `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`
- `tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface`

#### 執行證據
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface -v
```

**結果**:
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\3b14b39f
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 2 items

tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing PASSED [ 50%]
tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface PASSED [100%]

============================== 2 passed in 3.38s ==============================
```

#### NOT-REPRODUCIBLE 判定
- covered 過濾與 partial/missing 結構對照 PASS
- 真模型對筆記涵蓋度的語意判斷無法以產品失敗重現
- 證據來源: `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 grok proxy)

---

### 6. test_grok_pong_integration

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.llm.GrokClient.complete` — 真實 HTTP 連線 + 回應解析

#### 替代測試
- `tests/test_llm.py::test_grokclient_builds_request_body`
- `tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract`

#### 執行證據
**結果**: PASSED (參見 `docs/excluded-failing-controls-2026-07-19.md`)

#### NOT-REPRODUCIBLE 判定
- GrokClient parse/endpoint 對照 PASS
- 純 TCP 連通性屬運維非產品邏輯缺陷
- 證據來源: `docs/excluded-failing-controls-2026-07-19.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 grok proxy)

---

### 7. test_run_pipeline_real_grok

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.pipeline.run_pipeline` — 完整 pipeline 在真 Grok 輸出下不炸 + C6 不變式

#### 替代測試
- `tests/test_pipeline.py::test_run_pipeline_invariant`
- `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`
- `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`
- `tests/test_correction.py::test_retrieved_five_but_only_two_cited`
- `tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources`

#### 執行證據
**結果**: PASSED (參見 `docs/excluded-failing-controls-2026-07-19.md`)

#### NOT-REPRODUCIBLE 判定
- C6 pending_evidence 對照 PASS
- 真模型輸出的 domain/questions/gaps 正確性無法以產品失敗重現
- 證據來源: `docs/excluded-failing-controls-2026-07-19.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 grok proxy)

---

### 8. test_generate_questions_real_grok

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.questions.generate_questions` — 真模型問題生成格式與品質

#### 替代測試
- `tests/test_questions.py::test_generate_questions_splits_multiline_string`
- `tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines`
- `tests/test_questions.py::test_generate_questions_strips_markdown_fence`
- `tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract`

#### 執行證據
**結果**: PASSED (參見 `docs/excluded-failing-controls-2026-07-19.md`)

#### NOT-REPRODUCIBLE 判定
- 問題清單契約對照 PASS
- 真模型出題品質無法以產品失敗重現
- 證據來源: `docs/excluded-failing-controls-2026-07-19.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 grok proxy)

---

### 9. test_retrieve_for_gap_real_twinkle_smoke

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.retrieve.retrieve_for_gap` — 真實 Twinkle Hub MCP + LawLookup + Grok keyword + 排序不變式

#### 替代測試
- `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B`
- `tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles`
- `tests/test_twinkle.py::test_search_parses_source_with_full_content`
- `tests/test_twinkle.py::test_search_reuses_mcp_session`
- `tests/test_twinkle.py::test_search_transport_failure_returns_empty`
- `tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot`
- `tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`
- `tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot`
- `tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous`

#### 執行證據
**結果**: PASSED (參見 `docs/excluded-failing-controls-2026-07-19.md`, `docs/exclusion-correctness-blind-spot-2026-07-19.md`)

#### NOT-REPRODUCIBLE 判定
- law Level A 非空對照 PASS
- 產品缺陷路徑不可重現（vacuous smoke 為驗證層盲區已鎖定）
- 證據來源: `docs/excluded-failing-controls-2026-07-19.md`, `docs/exclusion-correctness-blind-spot-2026-07-19.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 grok proxy + Twinkle + law_index.db)

---

### 10. test_search_real_twinkle_hub

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.retrieve.twinkle.TwinkleClient.search` — 真實 Twinkle Hub MCP 搜尋

#### 替代測試
- `tests/test_twinkle.py::test_search_parses_source_with_full_content`
- `tests/test_twinkle.py::test_search_reuses_mcp_session`
- `tests/test_twinkle.py::test_search_transport_failure_returns_empty`
- `tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty`
- `tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract`

#### 執行證據
**結果**: PASSED (參見 `docs/excluded-failing-controls-2026-07-19.md`)

#### NOT-REPRODUCIBLE 判定
- Twinkle Source 解析契約對照 PASS
- 真實 Twinkle Hub 服務可用性屬外部 I/O 非 determinism 產品缺陷
- 證據來源: `docs/excluded-failing-controls-2026-07-19.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 TWINKLE_HUB_TOKEN)

---

### 11. test_write_supplement_real_grok_grounded_output

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.write.write_supplement` — 固定兩筆 Level A 來源下的真 Grok grounded 輸出

#### 替代測試
- `tests/test_write.py::test_used_source_ids_from_markers`
- `tests/test_write.py::test_pending_evidence_when_insufficient`

#### 執行證據
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_write.py::test_used_source_ids_from_markers tests/test_write.py::test_pending_evidence_when_insufficient -v
```

**結果**:
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\3b14b39f
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 2 items

tests/test_write.py::test_used_source_ids_from_markers PASSED            [ 50%]
tests/test_write.py::test_pending_evidence_when_insufficient PASSED      [100%]

============================== 2 passed in 0.06s ==============================
```

#### NOT-REPRODUCIBLE 判定
- 註腳到來源 ID 映射與降級邏輯對照 PASS
- 真模型固定來源 grounded 寫作品質無法以產品失敗重現
- 證據來源: `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md`

#### CI 覆蓋
- test-pinned/test-latest: 覆蓋替代測試
- test-integration: 可執行原始 integration 測試 (需 grok proxy)

---

## 總結

| # | Deselected 測試 | 替代測試數 | 執行結果 | NOT-REPRODUCIBLE 證據 | CI 覆蓋 |
|---|----------------|-----------|---------|---------------------|---------|
| 1 | `test_detect_domain_real_grok_returns_law` | 2 | PASSED | `docs/excluded-failing-controls-2026-07-19.md` | ✅ |
| 2 | `test_detect_domain_real_grok_representative_domains` | 4 | PASSED | `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md` | ✅ |
| 3 | `test_e2e_acceptance_real` | 8 | PASSED | `docs/excluded-failing-controls-2026-07-19.md` + 2 | ✅ |
| 4 | `test_detect_gaps_real_grok` | 2 | PASSED | `docs/excluded-failing-controls-2026-07-19.md` | ✅ |
| 5 | `test_detect_gaps_real_grok_semantic_matrix` | 2 | PASSED | `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md` | ✅ |
| 6 | `test_grok_pong_integration` | 2 | PASSED | `docs/excluded-failing-controls-2026-07-19.md` | ✅ |
| 7 | `test_run_pipeline_real_grok` | 5 | PASSED | `docs/excluded-failing-controls-2026-07-19.md` | ✅ |
| 8 | `test_generate_questions_real_grok` | 4 | PASSED | `docs/excluded-failing-controls-2026-07-19.md` | ✅ |
| 9 | `test_retrieve_for_gap_real_twinkle_smoke` | 9 | PASSED | `docs/excluded-failing-controls-2026-07-19.md` + blind-spot | ✅ |
| 10 | `test_search_real_twinkle_hub` | 5 | PASSED | `docs/excluded-failing-controls-2026-07-19.md` | ✅ |
| 11 | `test_write_supplement_real_grok_grounded_output` | 2 | PASSED | `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md` | ✅ |

## 驗證命令

### 完整替代測試驗證
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/ -m "not integration" -v
```

### CI Gate 驗證
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 scripts/validate_deselection_ci.py
```

### 守衛測試驗證
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_deselection_guard.py -v
```

## 關聯文件

- `tests/deselected_allowlist.json` — 機器可讀索引
- `docs/deselected-traceability-index-2026-07-22.md` — 可追溯索引
- `docs/excluded-failing-controls-2026-07-19.md` — 8 筆 failing-first 對照
- `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md` — 3 筆補充驗證
- `tests/test_deselection_guard.py` — 守衛測試
- `scripts/validate_deselection_ci.py` — CI gate 驗證腳本
