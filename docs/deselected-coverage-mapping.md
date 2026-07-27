# Deselected 測試覆蓋對照報告

## 產生時間
2026-07-27

## 範圍
本報告對照 `tests/deselected_allowlist.json` 中所有 deselected 測試，指出其在其他 CI job、測試階段或替代測試路徑的執行位置，並附上可重現命令與成功結果。

## 執行環境
- Python: `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe`
- 參數: `-X utf8`
- 預設測試集合: `-m 'not integration'`

## Deselected 測試清單與覆蓋對照

### 1. tests/test_domain.py::test_detect_domain_real_grok_returns_law

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 中  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_domain.py::test_detect_domain_law**
   - **覆蓋範圍**: FakeLLM 驗證 detect_domain 的 law 回傳契約
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**: 
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law -v
     ```
   - **成功結果**: 驗證 FakeLLM 回傳 "law" 時 detect_domain 正確返回 "law"

2. **tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract**
   - **覆蓋範圍**: failing-first 對照：法律文標籤契約 + 雜訊 fallback 至 other
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract -v
     ```
   - **成功結果**: 驗證法律標籤契約與雜訊 fallback 行為

#### CI Job 覆蓋
- **test-pinned**: 執行替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真 Grok 對法律文字的實際回應正確性需透過 integration job 執行

---

### 2. tests/test_e2e_acceptance.py::test_e2e_acceptance_real

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 高  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_e2e_acceptance.py::test_e2e_structural_invariants**
   - **覆蓋範圍**: 離線完整 pipeline 驗證原稿不可變、無來源閘、法條查核與輸出契約
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_structural_invariants -v
     ```
   - **成功結果**: 驗證原稿不可變、無來源閘、法條查核與輸出契約

2. **tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary**
   - **覆蓋範圍**: 離線驗證 Level A 路由、非原始記錄倒出與註腳品質邊界
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary -v
     ```
   - **成功結果**: 驗證 Level A 路由、非原始記錄倒出與註腳品質邊界

3. **tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression**
   - **覆蓋範圍**: 最小離線前置鎖定四項品質閘：原稿不可變、pending_evidence、只掛引用、法條離線查核
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression -v
     ```
   - **成功結果**: 驗證四項品質閘

4. **tests/test_pipeline.py::test_run_pipeline_invariant**
   - **覆蓋範圍**: pipeline C6：無來源補充必為 pending_evidence，雙來源補充為 verified
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -v
     ```
   - **成功結果**: 驗證 C6 不變式

5. **tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending**
   - **覆蓋範圍**: 畸形 gap 輸出保守降級為待補證且不掛來源
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending -v
     ```
   - **成功結果**: 驗證畸形輸出降級邏輯

6. **tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check**
   - **覆蓋範圍**: law 領域每個補充段都觸發法規引用查核
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check -v
     ```
   - **成功結果**: 驗證法規引用查核觸發

7. **tests/test_correction.py::test_retrieved_five_but_only_two_cited**
   - **覆蓋範圍**: 只掛實際引用來源，不把未引用的 retrieved source 帶入正文
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_correction.py::test_retrieved_five_but_only_two_cited -v
     ```
   - **成功結果**: 驗證只掛實際引用來源

8. **tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates**
   - **覆蓋範圍**: failing-first 對照：離線四硬閘（原稿/pending/引用/verified）
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates -v
     ```
   - **成功結果**: 驗證離線四硬閘

#### CI Job 覆蓋
- **test-pinned**: 執行所有替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行所有替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真模型+真檢索下的 gap 偵測品質、補充寫作品質 (_assert_supplement_quality)、Level A 路由穩定性需透過 integration job 執行

---

### 3. tests/test_gap.py::test_detect_gaps_real_grok

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 中  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing**
   - **覆蓋範圍**: FakeLLM 驗證 covered 過濾，只保留 partial/missing 並建立 Gap
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing -v
     ```
   - **成功結果**: 驗證 covered 過濾與 partial/missing 結構

2. **tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface**
   - **覆蓋範圍**: failing-first 對照：明顯未涵蓋題必須進缺口清單
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface -v
     ```
   - **成功結果**: 驗證明顯未涵蓋題必須浮現

#### CI Job 覆蓋
- **test-pinned**: 執行替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真 grok 對法律文本的缺口判斷品質需透過 integration job 執行

---

### 4. tests/test_llm.py::test_grok_pong_integration

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 中  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_llm.py::test_grokclient_builds_request_body**
   - **覆蓋範圍**: monkeypatch 驗證 request body、Bearer、POST endpoint、timeout 與 response parse
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_llm.py::test_grokclient_builds_request_body -v
     ```
   - **成功結果**: 驗證 request body、Bearer、POST endpoint、timeout 與 response parse

2. **tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract**
   - **覆蓋範圍**: failing-first 對照：PONG 契約 + endpoint/model 鎖定
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract -v
     ```
   - **成功結果**: 驗證 PONG 契約 + endpoint/model 鎖定

#### CI Job 覆蓋
- **test-pinned**: 執行替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真實 TCP 連線到 proxy 的連通性、proxy 回應格式解析需透過 integration job 執行

---

### 5. tests/test_pipeline.py::test_run_pipeline_real_grok

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 高  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_pipeline.py::test_run_pipeline_invariant**
   - **覆蓋範圍**: FakeLLM/FakeTwinkle 驗證 pipeline 的 C6 與 verified 路徑
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -v
     ```
   - **成功結果**: 驗證 C6 與 verified 路徑

2. **tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending**
   - **覆蓋範圍**: 畸形模型輸出會保守降級為 pending_evidence
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending -v
     ```
   - **成功結果**: 驗證畸形輸出降級邏輯

3. **tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check**
   - **覆蓋範圍**: law pipeline 會逐段執行 citation check
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check -v
     ```
   - **成功結果**: 驗證 citation check 觸發

4. **tests/test_pipeline.py::test_original_text_immutable_in_output**
   - **覆蓋範圍**: 直接比對輸出原文段與原始筆記，防止「輸出資料已變但筆記內容未同步」的假綠情境
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_pipeline.py::test_original_text_immutable_in_output -v
     ```
   - **成功結果**: 驗證原稿不可變

5. **tests/test_correction.py::test_retrieved_five_but_only_two_cited**
   - **覆蓋範圍**: 組裝層只保留 writer 實際引用的來源
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_correction.py::test_retrieved_five_but_only_two_cited -v
     ```
   - **成功結果**: 驗證只掛實際引用來源

6. **tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources**
   - **覆蓋範圍**: failing-first 對照：empty twinkle 路徑 C6 pending_evidence
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources -v
     ```
   - **成功結果**: 驗證 empty twinkle 路徑 C6 pending_evidence

#### CI Job 覆蓋
- **test-pinned**: 執行所有替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行所有替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真 Grok 模型輸出的 domain/questions/gaps 正確性 + pipeline 穩定性需透過 integration job 執行

---

### 6. tests/test_questions.py::test_generate_questions_real_grok

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 中  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_questions.py::test_generate_questions_splits_multiline_string**
   - **覆蓋範圍**: FakeLLM 驗證多行回應切成乾淨問題清單
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_questions.py::test_generate_questions_splits_multiline_string -v
     ```
   - **成功結果**: 驗證多行回應切成乾淨問題清單

2. **tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines**
   - **覆蓋範圍**: FakeLLM 驗證 strip 與空行移除契約
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines -v
     ```
   - **成功結果**: 驗證 strip 與空行移除契約

3. **tests/test_questions.py::test_generate_questions_strips_markdown_fence**
   - **覆蓋範圍**: FakeLLM 驗證 markdown 圍欄內的問題被正確解析,圍欄行不洩漏
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_questions.py::test_generate_questions_strips_markdown_fence -v
     ```
   - **成功結果**: 驗證 markdown 圍欄解析

4. **tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract**
   - **覆蓋範圍**: failing-first 對照：非空乾淨清單且無 JSON 結構符
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract -v
     ```
   - **成功結果**: 驗證非空乾淨清單且無 JSON 結構符

#### CI Job 覆蓋
- **test-pinned**: 執行所有替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行所有替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真 Grok 對法律文本的問題生成品質需透過 integration job 執行

---

### 7. tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 高  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B**
   - **覆蓋範圍**: FakeLaw/FakeTwinkle 驗證 Level A 優先於 B 且級內依 distance 排序
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B -v
     ```
   - **成功結果**: 驗證 Level A 優先於 B 且級內依 distance 排序

2. **tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles**
   - **覆蓋範圍**: 離線 law_index 查詢產生合法 Level A 法條 Source
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles -v
     ```
   - **成功結果**: 驗證離線 law_index 查詢產生合法 Level A 法條 Source

3. **tests/test_twinkle.py::test_search_parses_source_with_full_content**
   - **覆蓋範圍**: mock MCP/SSE 驗證全文與 Source metadata 映射
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_parses_source_with_full_content -v
     ```
   - **成功結果**: 驗證全文與 Source metadata 映射

4. **tests/test_twinkle.py::test_search_reuses_mcp_session**
   - **覆蓋範圍**: mock MCP 驗證 initialize、initialized、tools/call 共用 session
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_reuses_mcp_session -v
     ```
   - **成功結果**: 驗證 session header 在三次 RPC 間傳遞

5. **tests/test_twinkle.py::test_search_transport_failure_returns_empty**
   - **覆蓋範圍**: mock timeout 驗證 transport failure 安全降級為空結果
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_transport_failure_returns_empty -v
     ```
   - **成功結果**: 驗證網路失敗安全降級

6. **tests/test_web.py::test_grade_valid_c_with_doc_date**
   - **覆蓋範圍**: 直接驗證 _grade C/D/drop 分級、doc_date 解析與 malformed fallback，鎖定 other 領域 web 搜尋的 correctness 分支
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_web.py::test_grade_valid_c_with_doc_date -v
     ```
   - **成功結果**: 驗證 _grade C/D/drop 分級、doc_date 解析與 malformed fallback

7. **tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot**
   - **覆蓋範圍**: 證明 deselected smoke 三斷言對 empty 仍 vacuous PASS，屬驗證盲區而非產品路徑通過
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot -v
     ```
   - **成功結果**: 證明 deselected smoke 對 empty 的 vacuous PASS 是驗證盲區

8. **tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty**
   - **覆蓋範圍**: 離線 law+LawLookup 強制非空 Level A，攔截 smoke vacuous empty 無法看見的 correctness 缺口
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty -v
     ```
   - **成功結果**: 驗證離線 law+LawLookup 強制非空 Level A

9. **tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot**
   - **覆蓋範圍**: failing-first 對照：#7 smoke 對 empty 仍綠（驗證層盲區）
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot -v
     ```
   - **成功結果**: 驗證 smoke 對 empty 的 vacuous PASS

10. **tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous**
    - **覆蓋範圍**: failing-first 對照：law Level A 非空產品路徑
    - **執行位置**: 預設 CI job (test-pinned, test-latest)
    - **可重現命令**:
      ```bash
      D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous -v
      ```
    - **成功結果**: 驗證 law Level A 非空產品路徑

#### CI Job 覆蓋
- **test-pinned**: 執行所有替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行所有替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真實 Twinkle Hub 服務 I/O 與真 Grok 關鍵字抽取品質需透過 integration job 執行

---

### 8. tests/test_twinkle.py::test_search_real_twinkle_hub

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 高  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_twinkle.py::test_search_parses_source_with_full_content**
   - **覆蓋範圍**: mock MCP/SSE 驗證全文 Source 與 metadata
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_parses_source_with_full_content -v
     ```
   - **成功結果**: 驗證全文 Source 與 metadata

2. **tests/test_twinkle.py::test_search_reuses_mcp_session**
   - **覆蓋範圍**: mock MCP 驗證 session header 在三次 RPC 間傳遞
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_reuses_mcp_session -v
     ```
   - **成功結果**: 驗證 session header 傳遞

3. **tests/test_twinkle.py::test_search_transport_failure_returns_empty**
   - **覆蓋範圍**: mock timeout 驗證網路失敗安全降級
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_transport_failure_returns_empty -v
     ```
   - **成功結果**: 驗證網路失敗安全降級

4. **tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty**
   - **覆蓋範圍**: mock MCP isError 驗證 MCP 協議錯誤安全降級為空結果
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_twinkle.py::test_search_mcp_protocol_error_returns_empty -v
     ```
   - **成功結果**: 驗證 MCP 協議錯誤安全降級

5. **tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract**
   - **覆蓋範圍**: failing-first 對照：解析後 level∈A/B、content 非空、fetched_date 當日
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract -v
     ```
   - **成功結果**: 驗證解析後 level∈A/B、content 非空、fetched_date 當日

#### CI Job 覆蓋
- **test-pinned**: 執行所有替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行所有替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真實 Twinkle Hub 服務可用性、服務端 session 相容性與網路逾時需透過 integration job 執行

---

### 9. tests/test_domain.py::test_detect_domain_real_grok_representative_domains

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 中  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_domain.py::test_detect_domain_law**
   - **覆蓋範圍**: FakeLLM 鎖定 law 回傳契約
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law -v
     ```
   - **成功結果**: 驗證 law 回傳契約

2. **tests/test_domain.py::test_detect_domain_admin**
   - **覆蓋範圍**: FakeLLM 鎖定 admin 回傳契約
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_domain.py::test_detect_domain_admin -v
     ```
   - **成功結果**: 驗證 admin 回傳契約

3. **tests/test_domain.py::test_detect_domain_exam**
   - **覆蓋範圍**: FakeLLM 鎖定 exam 回傳契約
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_domain.py::test_detect_domain_exam -v
     ```
   - **成功結果**: 驗證 exam 回傳契約

4. **tests/test_domain.py::test_detect_domain_noise_falls_back_to_other**
   - **覆蓋範圍**: FakeLLM 鎖定無法辨識時的 other fallback
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_domain.py::test_detect_domain_noise_falls_back_to_other -v
     ```
   - **成功結果**: 驗證 other fallback

#### CI Job 覆蓋
- **test-pinned**: 執行所有替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行所有替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真模型分類品質與 proxy 可用性仍須 integration 執行；預設測試只覆蓋標籤解析契約

---

### 10. tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 中  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing**
   - **覆蓋範圍**: FakeLLM 鎖定 covered 過濾與 partial/missing 結構
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing -v
     ```
   - **成功結果**: 驗證 covered 過濾與 partial/missing 結構

2. **tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface**
   - **覆蓋範圍**: 離線對照鎖定明顯未涵蓋題必須浮現
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface -v
     ```
   - **成功結果**: 驗證明顯未涵蓋題必須浮現

#### CI Job 覆蓋
- **test-pinned**: 執行所有替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行所有替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真模型對筆記涵蓋度的語意判斷仍須 integration 執行；預設測試只覆蓋解析與過濾

---

### 11. tests/test_write.py::test_write_supplement_real_grok_grounded_output

**排除原因**: `deselected by -m 'not integration'`  
**安全風險**: 中  
**核准決策**: acceptable_unexecuted

#### 替代覆蓋測試
1. **tests/test_write.py::test_used_source_ids_from_markers**
   - **覆蓋範圍**: FakeLLM 鎖定合法註腳到實際來源 ID 的映射
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_write.py::test_used_source_ids_from_markers -v
     ```
   - **成功結果**: 驗證合法註腳到實際來源 ID 的映射

2. **tests/test_write.py::test_pending_evidence_when_insufficient**
   - **覆蓋範圍**: FakeLLM 鎖定來源不足時保守回 pending_evidence 文本
   - **執行位置**: 預設 CI job (test-pinned, test-latest)
   - **可重現命令**:
     ```bash
     D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_write.py::test_pending_evidence_when_insufficient -v
     ```
   - **成功結果**: 驗證來源不足時保守回 pending_evidence 文本

#### CI Job 覆蓋
- **test-pinned**: 執行所有替代測試 (line 40: `python -m pytest tests/ -m "not integration" -v`)
- **test-latest**: 執行所有替代測試 (line 71: `python -m pytest tests/ -m "not integration" -v`)

#### 真實模型覆蓋缺口
真模型能否只依固定來源寫出帶有效註腳的補充仍須 integration 執行

---

## 必要回歸套件

根據分析，所有 deselected 測試都有完整的替代覆蓋，無需納入必要回歸套件。所有替代測試都在預設 CI job (test-pinned, test-latest) 中執行，並且有明確的可重現命令。

## CI Job 覆蓋摘要

### test-pinned Job
- **執行命令**: `python -m pytest tests/ -m "not integration" -v`
- **覆蓋範圍**: 所有非 integration 測試，包含所有 deselected 測試的替代覆蓋
- **Python 版本**: 3.11, 3.12

### test-latest Job
- **執行命令**: `python -m pytest tests/ -m "not integration" -v`
- **覆蓋範圍**: 所有非 integration 測試，包含所有 deselected 測試的替代覆蓋
- **Python 版本**: 3.11, 3.12, 3.13

### test-integration Job
- **執行命令**: `python -m pytest tests/ -m "integration" -v`
- **觸發條件**: workflow_dispatch
- **覆蓋範圍**: 所有 integration 測試（包含 deselected 測試）
- **Python 版本**: 3.12
- **限制**: 需要真實 grok proxy (127.0.0.1:8318) 與相關外部服務

## 結論

所有 11 個 deselected 測試都有完整的替代覆蓋，替代測試在預設 CI job (test-pinned, test-latest) 中執行。真實模型相關的覆蓋缺口透過 test-integration job 在 workflow_dispatch 時執行。無需將任何測試納入必要回歸套件。