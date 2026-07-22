# Deselected 測試 CI 覆蓋矩陣

## 產生時間
2026-07-23

## 執行環境
- Python 路徑: `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe`
- 執行參數: `-X utf8`
- 工作目錄: `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\c257ce23`

## CI 配置分析

### CI Job 配置 (.github/workflows/ci.yml)

| Job | 平台 | Python 版本 | 觸發條件 | 測試指令 | 執行範圍 |
|-----|------|-------------|----------|----------|----------|
| test-pinned | ubuntu-latest | 3.11, 3.12 | push, pull_request | `python -m pytest tests/ -m "not integration" -v` | 非 integration 測試 |
| test-latest | ubuntu-latest | 3.11, 3.12, 3.13 | push, pull_request | `python -m pytest tests/ -m "not integration" -v` | 非 integration 測試 |
| test-integration | ubuntu-latest | 3.12 | workflow_dispatch | `python -m pytest tests/ -m "integration" -v` | 僅 integration 測試 |

### 執行路徑總結
- **預設 CI (push/PR)**: 所有 deselected 測試被排除，不執行
- **手動觸發 (workflow_dispatch)**: 僅 Python 3.12 環境執行 integration 測試
- **本地執行**: 可透過 `-m integration` 或移除 `-m 'not integration'` 執行

## 11 個 Deselected 測試覆蓋矩陣

### 1. tests/test_domain.py::test_detect_domain_real_grok_representative_domains

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | `note_filler.domain.detect_domain` — 真 Grok 四類代表文本語意矩陣 |
| **外部依賴** | Grok proxy at http://127.0.0.1:8318/v1 (model grok-4.3) |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_domain.py::test_detect_domain_real_grok_representative_domains -m integration -v` |
| **替代測試** | `tests/test_domain.py::test_detect_domain_law`<br>`tests/test_domain.py::test_detect_domain_admin`<br>`tests/test_domain.py::test_detect_domain_exam`<br>`tests/test_domain.py::test_detect_domain_noise_falls_back_to_other` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 真 Grok 對四類代表文本的實際語意分類品質 |

### 2. tests/test_domain.py::test_detect_domain_real_grok_returns_law

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | `note_filler.domain.detect_domain` — LLM 領域偵測 (law/admin/exam/other) |
| **外部依賴** | Grok proxy at http://127.0.0.1:8318/v1 (model grok-4.3) |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_domain.py::test_detect_domain_real_grok_returns_law -m integration -v` |
| **替代測試** | `tests/test_domain.py::test_detect_domain_law`<br>`tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 真 Grok 對法律文字的實際分類品質 |

### 3. tests/test_e2e_acceptance.py::test_e2e_acceptance_real

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | §12 端到端驗收: parse→domain→questions→gaps→retrieve→assemble→export; 5 個硬不變式 |
| **外部依賴** | Grok proxy, Twinkle Hub (TWINKLE_HUB_TOKEN), data/law_index.db |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_acceptance_real -m integration -v` |
| **替代測試** | `tests/test_e2e_acceptance.py::test_e2e_structural_invariants`<br>`tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary`<br>`tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression`<br>`tests/test_pipeline.py::test_run_pipeline_invariant`<br>`tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`<br>`tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`<br>`tests/test_correction.py::test_retrieved_five_but_only_two_cited`<br>`tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 真模型 + 真檢索下的 gap 偵測品質、Level A 路由穩定性、真 Twinkle Hub I/O |

### 4. tests/test_gap.py::test_detect_gaps_real_grok

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | `note_filler.gap.detect_gaps` — LLM 缺口偵測 (partial/missing 過濾) |
| **外部依賴** | Grok proxy at http://127.0.0.1:8318/v1 (model grok-4.3) |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_real_grok -m integration -v` |
| **替代測試** | `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`<br>`tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 真 Grok 對法律文本的缺口判斷語意品質 |

### 5. tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | `note_filler.gap.detect_gaps` — 真 Grok covered/missing 對照語意 |
| **外部依賴** | Grok proxy at http://127.0.0.1:8318/v1 (model grok-4.3) |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix -m integration -v` |
| **替代測試** | `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`<br>`tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 真 Grok covered/missing 語意矩陣的實際品質 |

### 6. tests/test_llm.py::test_grok_pong_integration

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | `note_filler.llm.GrokClient.complete` — 真實 HTTP 連線 + 回應解析 |
| **外部依賴** | Grok proxy at http://127.0.0.1:8318/v1 (model grok-4.3) |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_llm.py::test_grok_pong_integration -m integration -v` |
| **替代測試** | `tests/test_llm.py::test_grokclient_builds_request_body`<br>`tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 真實 TCP 連線到 proxy 的連通性、proxy 端回應格式相容性 |

### 7. tests/test_pipeline.py::test_run_pipeline_real_grok

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | `note_filler.pipeline.run_pipeline` — 完整 pipeline 在真 Grok 輸出下不炸 + C6 不變式 |
| **外部依賴** | Grok proxy at http://127.0.0.1:8318/v1 (model grok-4.3) |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_real_grok -m integration -v` |
| **替代測試** | `tests/test_pipeline.py::test_run_pipeline_invariant`<br>`tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`<br>`tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`<br>`tests/test_correction.py::test_retrieved_five_but_only_two_cited`<br>`tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 真 Grok 模型輸出的 domain/questions/gaps 正確性 + pipeline 穩定性 |

### 8. tests/test_questions.py::test_generate_questions_real_grok

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | `note_filler.questions.generate_questions` — 真模型問題生成格式與品質 |
| **外部依賴** | Grok proxy at http://127.0.0.1:8318/v1 (model grok-4.3) |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_questions.py::test_generate_questions_real_grok -m integration -v` |
| **替代測試** | `tests/test_questions.py::test_generate_questions_splits_multiline_string`<br>`tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines`<br>`tests/test_questions.py::test_generate_questions_strips_markdown_fence`<br>`tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 真 Grok 對法律文本的問題生成品質 |

### 9. tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | `note_filler.retrieve.retrieve_for_gap` — 真實 Twinkle Hub MCP + LawLookup + Grok keyword + 排序不變式 |
| **外部依賴** | Grok proxy, Twinkle Hub (TWINKLE_HUB_TOKEN), data/law_index.db |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke -m integration -v` |
| **替代測試** | `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B`<br>`tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles`<br>`tests/test_twinkle.py::test_search_parses_source_with_full_content`<br>`tests/test_twinkle.py::test_search_reuses_mcp_session`<br>`tests/test_twinkle.py::test_search_transport_failure_returns_empty`<br>`tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot`<br>`tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`<br>`tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot`<br>`tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 真實 Twinkle Hub 服務 I/O + 真 Grok 關鍵字抽取品質 |

### 10. tests/test_twinkle.py::test_search_real_twinkle_hub

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | `note_filler.retrieve.twinkle.TwinkleClient.search` — 真實 Twinkle Hub MCP 搜尋 |
| **外部依賴** | Twinkle Hub (TWINKLE_HUB_TOKEN) |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_twinkle.py::test_search_real_twinkle_hub -m integration -v` |
| **替代測試** | `tests/test_twinkle.py::test_search_parses_source_with_full_content`<br>`tests/test_twinkle.py::test_search_reuses_mcp_session`<br>`tests/test_twinkle.py::test_search_transport_failure_returns_empty`<br>`tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty`<br>`tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 真實 Twinkle Hub 服務可用性、服務端 session 相容性、網路逾時處理 |

### 11. tests/test_write.py::test_write_supplement_real_grok_grounded_output

| 項目 | 內容 |
|------|------|
| **排除原因** | `-m 'not integration'` (pyproject.toml addopts) |
| **標記** | `@pytest.mark.integration` |
| **覆蓋功能** | `note_filler.write.write_supplement` — 固定兩筆 Level A 來源下的真 Grok grounded 輸出 |
| **外部依賴** | Grok proxy at http://127.0.0.1:8318/v1 (model grok-4.3) |
| **CI 執行路徑** | ❌ 無 - 預設 CI 不執行，僅 workflow_dispatch test-integration (Python 3.12) |
| **平台覆蓋** | ubuntu-latest (Python 3.12 僅) |
| **觸發條件** | workflow_dispatch 手動觸發 |
| **可重現命令** | `python -X utf8 -m pytest tests/test_write.py::test_write_supplement_real_grok_grounded_output -m integration -v` |
| **替代測試** | `tests/test_write.py::test_used_source_ids_from_markers`<br>`tests/test_write.py::test_pending_evidence_when_insufficient` |
| **替代覆蓋狀態** | ✅ 有替代覆蓋 - 非 integration 測試在預設 CI 執行 |
| **覆蓋缺口** | 固定來源的 grounded writer 語意需真實 grok proxy 的實際品質 |

## 覆蓋矩陣總結

### CI 執行路徑分析

| 測試類型 | 預設 CI (push/PR) | 手動觸發 (workflow_dispatch) | 本地執行 |
|---------|------------------|------------------------------|----------|
| 非 integration 測試 | ✅ test-pinned (3.11, 3.12), test-latest (3.11, 3.12, 3.13) | ✅ test-integration (3.12) | ✅ 可執行 |
| Integration 測試 | ❌ 被排除 | ✅ test-integration (3.12 僅) | ✅ `-m integration` |

### 替代覆蓋狀態

| 測試編號 | 替代覆蓋狀態 | 替代測試數量 | 替代測試在預設 CI 執行 |
|---------|-------------|-------------|---------------------|
| 1 | ✅ 有 | 4 | ✅ 是 |
| 2 | ✅ 有 | 2 | ✅ 是 |
| 3 | ✅ 有 | 8 | ✅ 是 |
| 4 | ✅ 有 | 2 | ✅ 是 |
| 5 | ✅ 有 | 2 | ✅ 是 |
| 6 | ✅ 有 | 2 | ✅ 是 |
| 7 | ✅ 有 | 5 | ✅ 是 |
| 8 | ✅ 有 | 4 | ✅ 是 |
| 9 | ✅ 有 | 9 | ✅ 是 |
| 10 | ✅ 有 | 5 | ✅ 是 |
| 11 | ✅ 有 | 2 | ✅ 是 |

### 平台覆蓋缺口

| 測試類型 | Python 3.11 | Python 3.12 | Python 3.13 |
|---------|-------------|-------------|-------------|
| 非 integration 測試 | ✅ test-pinned, test-latest | ✅ test-pinned, test-latest | ✅ test-latest |
| Integration 測試 | ❌ 無 | ✅ test-integration (workflow_dispatch) | ❌ 無 |

### 修正行動需求

根據覆蓋矩陣分析，所有 11 個 deselected 測試都有替代覆蓋，且替代測試都在預設 CI 中執行。因此：

1. **無替代執行路徑的測試**: 無 - 所有測試都有替代覆蓋
2. **需要加入 CI 階段的測試**: 無 - 替代測試已在預設 CI 執行
3. **需要取消排除的測試**: 無 - 排除理由合理（外部依賴）

### 建議改進

1. **平台覆蓋**: 可考慮在 test-integration 中加入 Python 3.11 和 3.13 的矩陣，以提升平台覆蓋
2. **觸發條件**: 可考慮在特定條件下（如 release branch）自動觸發 integration 測試
3. **監控**: 持續監控 workflow_dispatch 的執行頻率，確保 integration 測試定期執行

## 可重現驗證命令

### 驗證 deselected 清單
```bash
python -X utf8 -m pytest tests/ -m "not integration" --collect-only -q --deselected-details
```

### 執行所有 integration 測試（需外部依賴）
```bash
python -X utf8 -m pytest tests/ -m integration -v
```

### 執行特定 integration 測試
```bash
python -X utf8 -m pytest tests/test_domain.py::test_detect_domain_real_grok_representative_domains -m integration -v
```

### 驗證替代測試覆蓋
```bash
python -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law -v
python -X utf8 -m pytest tests/test_domain.py::test_detect_domain_admin -v
python -X utf8 -m pytest tests/test_domain.py::test_detect_domain_exam -v
python -X utf8 -m pytest tests/test_domain.py::test_detect_domain_noise_falls_back_to_other -v
```

## 結論

1. **所有 11 個 deselected 測試都有完整的替代覆蓋**
2. **替代測試都在預設 CI 中執行**，覆蓋了關鍵的確定性路徑
3. **無需要取消排除的測試**，排除理由合理（外部依賴 grok proxy 和 Twinkle Hub）
4. **無需要加入 CI 階段的測試**，替代覆蓋已足夠
5. **覆蓋缺口僅限於模型品質和外部服務可用性**，這些是 integration 測試的設計目的
