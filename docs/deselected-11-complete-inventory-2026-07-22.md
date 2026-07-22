# Deselected 測試完整盤點報告

## 產生時間
2026-07-22

## 執行環境
- Python 路徑: `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe` (實際使用系統 Python 3.11.9)
- 執行參數: `-X utf8`
- 工作目錄: `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\4c5e8da2`

## Pytest 執行指令與配置

### CI Job 設定
CI 配置檔案: `.github/workflows/ci.yml`

主要測試 Job 指令:
- **test-pinned**: `python -m pytest tests/ -m "not integration" -v`
- **test-latest**: `python -m pytest tests/ -m "not integration" -v`
- **test-integration**: `python -m pytest tests/ -m "integration" -v` (僅 workflow_dispatch)

CI 驗證腳本: `python scripts/validate_deselection_ci.py`

### Pytest 配置
配置檔案: `pyproject.toml`

關鍵設定:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

### Conftest.py 自定義選項
檔案: `tests/conftest.py`

自定義選項:
- `--deselected-details`: 列出 deselected 測試的完整 node ID 與排除原因

### 環境變數
- 無特定環境變數要求於 CI 配置中
- Integration 測試需要:
  - `TWINKLE_HUB_TOKEN`: Twinkle Hub 認證 token
  - Grok proxy at `http://127.0.0.1:8318/v1` (model grok-4.3)

## 實際執行結果

### 執行指令
```bash
python -X utf8 -m pytest tests/ -ra --deselected-details
```

### Collection 統計
- **總收集測試數**: 167
- **預設 selected**: 156
- **Deselected**: 11

### 完整 Deselected 測試清單

以下為 11 個實際被 deselected 的測試及其排除條件:

#### 1. tests/test_domain.py::test_detect_domain_real_grok_representative_domains
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: `note_filler.domain.detect_domain` — 真 Grok 四類代表文本語意矩陣
- **替代測試**:
  - `tests/test_domain.py::test_detect_domain_law`
  - `tests/test_domain.py::test_detect_domain_admin`
  - `tests/test_domain.py::test_detect_domain_exam`
  - `tests/test_domain.py::test_detect_domain_noise_falls_back_to_other`
- **排除條件**: 預設 `-m 'not integration'` 排除；四類代表文本需真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過

#### 2. tests/test_domain.py::test_detect_domain_real_grok_returns_law
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: `note_filler.domain.detect_domain` — LLM 領域偵測 (law/admin/exam/other)
- **替代測試**:
  - `tests/test_domain.py::test_detect_domain_law`
  - `tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract`
- **排除條件**: 預設 `-m 'not integration'` 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過

#### 3. tests/test_e2e_acceptance.py::test_e2e_acceptance_real
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: §12 端到端驗收: parse→domain→questions→gaps→retrieve→assemble→export; 5 個硬不變式
- **替代測試**:
  - `tests/test_e2e_acceptance.py::test_e2e_structural_invariants`
  - `tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary`
  - `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression`
  - `tests/test_pipeline.py::test_run_pipeline_invariant`
  - `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`
  - `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`
  - `tests/test_correction.py::test_retrieved_five_but_only_two_cited`
  - `tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates`
- **排除條件**: 預設 `-m 'not integration'` 在 collection 階段排除；真跑需要 data/law_index.db、grok proxy 與 TWINKLE_HUB_TOKEN，任一前置條件不足即 skip

#### 4. tests/test_gap.py::test_detect_gaps_real_grok
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: `note_filler.gap.detect_gaps` — LLM 缺口偵測 (partial/missing 過濾)
- **替代測試**:
  - `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`
  - `tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface`
- **排除條件**: 預設 `-m 'not integration'` 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過

#### 5. tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: `note_filler.gap.detect_gaps` — 真 Grok covered/missing 對照語意
- **替代測試**:
  - `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`
  - `tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface`
- **排除條件**: 預設 `-m 'not integration'` 排除；covered/missing 語意矩陣需真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過

#### 6. tests/test_llm.py::test_grok_pong_integration
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: `note_filler.llm.GrokClient.complete` — 真實 HTTP 連線 + 回應解析
- **替代測試**:
  - `tests/test_llm.py::test_grokclient_builds_request_body`
  - `tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract`
- **排除條件**: 預設 `-m 'not integration'` 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過

#### 7. tests/test_pipeline.py::test_run_pipeline_real_grok
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: `note_filler.pipeline.run_pipeline` — 完整 pipeline 在真 Grok 輸出下不炸 + C6 不變式
- **替代測試**:
  - `tests/test_pipeline.py::test_run_pipeline_invariant`
  - `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`
  - `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`
  - `tests/test_correction.py::test_retrieved_five_but_only_two_cited`
  - `tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources`
- **排除條件**: 預設 `-m 'not integration'` 在 collection 階段排除；只要真實 grok proxy 才能執行，Twinkle 與 law 雖以 fake 隔離仍保留 integration 邊界

#### 8. tests/test_questions.py::test_generate_questions_real_grok
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: `note_filler.questions.generate_questions` — 真模型問題生成格式與品質
- **替代測試**:
  - `tests/test_questions.py::test_generate_questions_splits_multiline_string`
  - `tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines`
  - `tests/test_questions.py::test_generate_questions_strips_markdown_fence`
  - `tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract`
- **排除條件**: 預設 `-m 'not integration'` 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過

#### 9. tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: `note_filler.retrieve.retrieve_for_gap` — 真實 Twinkle Hub MCP + LawLookup + Grok keyword + 排序不變式
- **替代測試**:
  - `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B`
  - `tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles`
  - `tests/test_twinkle.py::test_search_parses_source_with_full_content`
  - `tests/test_twinkle.py::test_search_reuses_mcp_session`
  - `tests/test_twinkle.py::test_search_transport_failure_returns_empty`
  - `tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot`
  - `tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`
  - `tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot`
  - `tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous`
- **排除條件**: 預設 `-m 'not integration'` 在 collection 階段排除；真跑需要 data/law_index.db、grok proxy 與 TWINKLE_HUB_TOKEN

#### 10. tests/test_twinkle.py::test_search_real_twinkle_hub
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: `note_filler.retrieve.twinkle.TwinkleClient.search` — 真實 Twinkle Hub MCP 搜尋
- **替代測試**:
  - `tests/test_twinkle.py::test_search_parses_source_with_full_content`
  - `tests/test_twinkle.py::test_search_reuses_mcp_session`
  - `tests/test_twinkle.py::test_search_transport_failure_returns_empty`
  - `tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty`
  - `tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract`
- **排除條件**: 預設 `-m 'not integration'` 在 collection 階段排除；真跑需要 TWINKLE_HUB_TOKEN，缺 token 時由函式內 pytest.skip 略過

#### 11. tests/test_write.py::test_write_supplement_real_grok_grounded_output
- **排除原因**: `deselected by -m 'not integration'`
- **標記**: `@pytest.mark.integration`
- **覆蓋功能**: `note_filler.write.write_supplement` — 固定兩筆 Level A 來源下的真 Grok grounded 輸出
- **替代測試**:
  - `tests/test_write.py::test_used_source_ids_from_markers`
  - `tests/test_write.py::test_pending_evidence_when_insufficient`
- **排除條件**: 預設 `-m 'not integration'` 排除；固定來源的 grounded writer 語意需真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過

## 排除規則總結

所有 11 個 deselected 測試皆因以下統一規則被排除:

1. **主要排除機制**: `pyproject.toml` 中的 `addopts = "-m 'not integration'"`
2. **標記要求**: 所有測試都標記為 `@pytest.mark.integration`
3. **外部依賴**: 需要真實 grok proxy (http://127.0.0.1:8318/v1) 或 TWINKLE_HUB_TOKEN
4. **Runtime 保護**: 大部分測試有 `@pytest.mark.skipif` 在外部服務不可達時跳過

## 與 Allowlist 對照

Allowlist 檔案: `tests/deselected_allowlist.json`

Allowlist 中包含 11 筆記錄，與實際 deselected 測試完全對應。每筆記錄包含:
- `test_id`: 測試 node ID
- `marker`: "integration"
- `decision`: "acceptable_unexecuted"
- `collection_reason`: "deselected by -m 'not integration'"
- `exclusion_reason`: 詳細排除原因說明
- `exclusion_evidence`: 排除證據來源
- `covered_function`: 覆蓋的功能
- `substitute_tests`: 替代測試清單
- `substitute_evidence`: 替代測試證據
- `coverage_gap`: 覆蓋缺口說明
- `gap_mitigation_evidence`: 缺口緩解證據

## 可重跑指令

### 完整測試執行 (含 deselected details)
```bash
python -X utf8 -m pytest tests/ -ra --deselected-details
```

### 僅收集測試 (不執行)
```bash
python -X utf8 -m pytest --collect-only -vv --deselected-details
```

### 僅執行 integration 測試
```bash
python -X utf8 -m pytest tests/ -m "integration" -v
```

### CI 驗證腳本
```bash
python scripts/validate_deselection_ci.py
```

## 注意事項

1. **數量差異**: 實際收集顯示 167 個測試 (156 selected, 11 deselected)，與舊版 matrix 預期的 163 個 (152 selected, 11 deselected) 有差異，表示新增了 4 個非 integration 測試
2. **所有 deselected 測試都有完整的替代覆蓋**: 根據 allowlist，每個 deselected 測試都有對應的替代測試來覆蓋關鍵路徑
3. **安全性考量**: 高風險測試 (security_risk=高/中) 都有經過核准並有替代覆蓋
4. **CI 執行**: 預設 CI 不執行 integration 測試，需透過 workflow_dispatch 手動觸發
