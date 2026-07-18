# Deselected 可接受未執行追溯證據

> 本檔由 `scripts/refresh_pytest_audit.py` 產生；每一項都同時列出
> 排除程式碼 anchor、替代測試程式碼 anchor，以及該替代測試在本次測試輸出中的結果。

## 集合判定

- 全量 collection：`116`
- 預設 selected：`108`
- `deselected`：`8`
- `integration` 集合：`8`
- allowlist 與實際 `deselected` 完全相等：`True`
- collection 原始輸出：[`collection.txt`](collection.txt)
- 預設測試原始輸出：[`test-report.txt`](test-report.txt)

## 逐項證據鏈

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

- 判定：`acceptable_unexecuted`
- 排除理由：預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
- 排除程式碼證據：
  - `pyproject.toml:32` — `-m 'not integration'`：預設集合排除 integration marker
  - `tests/test_domain.py:50` — `@pytest.mark.integration`：目標測試標記為 integration
  - `tests/test_domain.py:51` — `@pytest.mark.skipif`：grok proxy 不可達時 runtime skip
- 替代測試證據：
  - `tests/test_domain.py::test_detect_domain_law` — `tests/test_domain.py:19` — `assert detect_domain`：FakeLLM 回 law 並驗證 detect_domain 的 law 回傳契約 — **PASSED**
    - 測試輸出：`tests/test_domain.py::test_detect_domain_law PASSED                      [ 18%]`
- 未覆蓋邊界：真 grok 對法律文字的實際回應正確性
- 結論：替代測試已保護確定性程式契約；剩餘邊界屬真實模型／外部服務，故可接受未執行。

### 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

- 判定：`acceptable_unexecuted`
- 排除理由：預設 -m 'not integration' 在 collection 階段排除；真跑需要 data/law_index.db、grok proxy 與 TWINKLE_HUB_TOKEN，任一前置條件不足即 skip
- 排除程式碼證據：
  - `pyproject.toml:32` — `-m 'not integration'`：預設集合排除 integration marker
  - `tests/test_e2e_acceptance.py:208` — `@pytest.mark.integration`：目標測試標記為 integration
  - `tests/test_e2e_acceptance.py:211` — `if not LAW_DB.exists()`：缺法規資料庫時 runtime skip
  - `tests/test_e2e_acceptance.py:42` — `return bool(os.environ.get("TWINKLE_HUB_TOKEN"))`：Twinkle token 是真跑前置條件
  - `tests/test_e2e_acceptance.py:215` — `if not (_grok_up() and _twinkle_ready())`：grok 或 Twinkle 未就緒時 runtime skip
- 替代測試證據：
  - `tests/test_e2e_acceptance.py::test_e2e_structural_invariants` — `tests/test_e2e_acceptance.py:170` — `_assert_immutable_original`：離線完整 pipeline 驗證原稿不可變、無來源閘、法條查核與輸出契約 — **PASSED**
    - 測試輸出：`tests/test_e2e_acceptance.py::test_e2e_structural_invariants PASSED      [ 24%]`
  - `tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary` — `tests/test_e2e_acceptance.py:204` — `_assert_supplement_quality(doc)`：離線驗證 Level A 路由、非原始記錄倒出與註腳品質邊界 — **PASSED**
    - 測試輸出：`tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary PASSED [ 25%]`
  - `tests/test_pipeline.py::test_run_pipeline_invariant` — `tests/test_pipeline.py:85` — `if not seg.sources`：pipeline C6：無來源補充必為 pending_evidence，雙來源補充為 verified — **PASSED**
    - 測試輸出：`tests/test_pipeline.py::test_run_pipeline_invariant PASSED               [ 61%]`
  - `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending` — `tests/test_pipeline.py:145` — `assert supplements[0].text.startswith`：畸形 gap 輸出保守降級為待補證且不掛來源 — **PASSED**
    - 測試輸出：`tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending PASSED [ 62%]`
  - `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check` — `tests/test_pipeline.py:122` — `assert len(calls)`：law 領域每個補充段都觸發法規引用查核 — **PASSED**
    - 測試輸出：`tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check PASSED [ 62%]`
  - `tests/test_correction.py::test_retrieved_five_but_only_two_cited` — `tests/test_correction.py:82` — `assert [s.id for s in sup.sources]`：只掛實際引用來源，不把未引用的 retrieved source 帶入正文 — **PASSED**
    - 測試輸出：`tests/test_correction.py::test_retrieved_five_but_only_two_cited PASSED  [  7%]`
- 未覆蓋邊界：真模型+真檢索下的 gap 偵測品質、補充寫作品質 (_assert_supplement_quality)、Level A 路由穩定性
- 結論：替代測試已保護確定性程式契約；剩餘邊界屬真實模型／外部服務，故可接受未執行。

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`

- 判定：`acceptable_unexecuted`
- 排除理由：預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
- 排除程式碼證據：
  - `pyproject.toml:32` — `-m 'not integration'`：預設集合排除 integration marker
  - `tests/test_gap.py:71` — `@pytest.mark.integration`：目標測試標記為 integration
  - `tests/test_gap.py:72` — `@pytest.mark.skipif`：grok proxy 不可達時 runtime skip
- 替代測試證據：
  - `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing` — `tests/test_gap.py:26` — `assert [g.status for g in gaps]`：FakeLLM 驗證 covered 過濾，只保留 partial/missing 並建立 Gap — **PASSED**
    - 測試輸出：`tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing PASSED [ 29%]`
- 未覆蓋邊界：真 grok 對法律文本的缺口判斷品質
- 結論：替代測試已保護確定性程式契約；剩餘邊界屬真實模型／外部服務，故可接受未執行。

### 4. `tests/test_llm.py::test_grok_pong_integration`

- 判定：`acceptable_unexecuted`
- 排除理由：預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
- 排除程式碼證據：
  - `pyproject.toml:32` — `-m 'not integration'`：預設集合排除 integration marker
  - `tests/test_llm.py:66` — `@pytest.mark.integration`：目標測試標記為 integration
  - `tests/test_llm.py:67` — `@pytest.mark.skipif`：grok proxy 不可達時 runtime skip
- 替代測試證據：
  - `tests/test_llm.py::test_grokclient_builds_request_body` — `tests/test_llm.py:53` — `assert out == "OK"`：monkeypatch 驗證 request body、Bearer、POST endpoint、timeout 與 response parse — **PASSED**
    - 測試輸出：`tests/test_llm.py::test_grokclient_builds_request_body PASSED            [ 57%]`
- 未覆蓋邊界：真實 TCP 連線到 proxy 的連通性、proxy 回應格式解析
- 結論：替代測試已保護確定性程式契約；剩餘邊界屬真實模型／外部服務，故可接受未執行。

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

- 判定：`acceptable_unexecuted`
- 排除理由：預設 -m 'not integration' 在 collection 階段排除；只要真實 grok proxy 才能執行，Twinkle 與 law 雖以 fake 隔離仍保留 integration 邊界
- 排除程式碼證據：
  - `pyproject.toml:32` — `-m 'not integration'`：預設集合排除 integration marker
  - `tests/test_pipeline.py:151` — `@pytest.mark.integration`：目標測試標記為 integration
  - `tests/test_pipeline.py:152` — `@pytest.mark.skipif`：grok proxy 不可達時 runtime skip
- 替代測試證據：
  - `tests/test_pipeline.py::test_run_pipeline_invariant` — `tests/test_pipeline.py:85` — `if not seg.sources`：FakeLLM/FakeTwinkle 驗證 pipeline 的 C6 與 verified 路徑 — **PASSED**
    - 測試輸出：`tests/test_pipeline.py::test_run_pipeline_invariant PASSED               [ 61%]`
  - `tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending` — `tests/test_pipeline.py:145` — `assert supplements[0].text.startswith`：畸形模型輸出會保守降級為 pending_evidence — **PASSED**
    - 測試輸出：`tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending PASSED [ 62%]`
  - `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check` — `tests/test_pipeline.py:122` — `assert len(calls)`：law pipeline 會逐段執行 citation check — **PASSED**
    - 測試輸出：`tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check PASSED [ 62%]`
  - `tests/test_correction.py::test_retrieved_five_but_only_two_cited` — `tests/test_correction.py:82` — `assert [s.id for s in sup.sources]`：組裝層只保留 writer 實際引用的來源 — **PASSED**
    - 測試輸出：`tests/test_correction.py::test_retrieved_five_but_only_two_cited PASSED  [  7%]`
- 未覆蓋邊界：真 Grok 模型輸出的 domain/questions/gaps 正確性 + pipeline 穩定性
- 結論：替代測試已保護確定性程式契約；剩餘邊界屬真實模型／外部服務，故可接受未執行。

### 6. `tests/test_questions.py::test_generate_questions_real_grok`

- 判定：`acceptable_unexecuted`
- 排除理由：預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
- 排除程式碼證據：
  - `pyproject.toml:32` — `-m 'not integration'`：預設集合排除 integration marker
  - `tests/test_questions.py:62` — `@pytest.mark.integration`：目標測試標記為 integration
  - `tests/test_questions.py:63` — `@pytest.mark.skipif`：grok proxy 不可達時 runtime skip
- 替代測試證據：
  - `tests/test_questions.py::test_generate_questions_splits_multiline_string` — `tests/test_questions.py:25` — `assert result ==`：FakeLLM 驗證多行回應切成乾淨問題清單 — **PASSED**
    - 測試輸出：`tests/test_questions.py::test_generate_questions_splits_multiline_string PASSED [ 63%]`
  - `tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines` — `tests/test_questions.py:38` — `assert result ==`：FakeLLM 驗證 strip 與空行移除契約 — **PASSED**
    - 測試輸出：`tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines PASSED [ 64%]`
- 未覆蓋邊界：真 Grok 對法律文本的問題生成品質
- 結論：替代測試已保護確定性程式契約；剩餘邊界屬真實模型／外部服務，故可接受未執行。

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

- 判定：`acceptable_unexecuted`
- 排除理由：預設 -m 'not integration' 在 collection 階段排除；真跑需要 data/law_index.db、grok proxy、GOV_AI_ENABLE_TWINKLE_MCP=1 與 TWINKLE_HUB_TOKEN
- 排除程式碼證據：
  - `pyproject.toml:32` — `-m 'not integration'`：預設集合排除 integration marker
  - `tests/test_retrieve.py:102` — `@pytest.mark.integration`：目標測試標記為 integration
  - `tests/test_retrieve.py:103` — `@pytest.mark.skipif`：缺 law_index.db 時 runtime skip
  - `tests/test_retrieve.py:104` — `@pytest.mark.skipif`：grok proxy 不可達時 runtime skip
  - `tests/test_retrieve.py:106` — `TWINKLE_HUB_TOKEN`：Twinkle token 是真跑前置條件
  - `tests/test_retrieve.py:107` — `if not token`：缺 token 時 runtime skip
- 替代測試證據：
  - `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B` — `tests/test_retrieve.py:72` — `assert [s.level for s in out]`：FakeLaw/FakeTwinkle 驗證 Level A 優先於 B 且級內依 distance 排序 — **PASSED**
    - 測試輸出：`tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B PASSED [ 67%]`
  - `tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles` — `tests/test_law_search.py:35` — `assert all(s.level == "A"`：離線 law_index 查詢產生合法 Level A 法條 Source — **PASSED**
    - 測試輸出：`tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles PASSED [ 50%]`
  - `tests/test_twinkle.py::test_search_parses_source_with_full_content` — `tests/test_twinkle.py:77` — `assert "現行條文對累犯之處罰不足"`：mock MCP/SSE 驗證全文與 Source metadata 映射 — **PASSED**
    - 測試輸出：`tests/test_twinkle.py::test_search_parses_source_with_full_content PASSED [ 73%]`
  - `tests/test_twinkle.py::test_search_reuses_mcp_session` — `tests/test_twinkle.py:101` — `assert requests ==`：mock MCP 驗證 initialize、initialized、tools/call 共用 session — **PASSED**
    - 測試輸出：`tests/test_twinkle.py::test_search_reuses_mcp_session PASSED             [ 75%]`
  - `tests/test_twinkle.py::test_search_transport_failure_returns_empty` — `tests/test_twinkle.py:114` — `assert TwinkleClient(token="fake-token").search`：mock timeout 驗證 transport failure 安全降級為空結果 — **PASSED**
    - 測試輸出：`tests/test_twinkle.py::test_search_transport_failure_returns_empty PASSED [ 75%]`
- 未覆蓋邊界：真實 Twinkle Hub 服務 I/O 與真 Grok 關鍵字抽取品質
- 結論：替代測試已保護確定性程式契約；剩餘邊界屬真實模型／外部服務，故可接受未執行。

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

- 判定：`acceptable_unexecuted`
- 排除理由：預設 -m 'not integration' 在 collection 階段排除；真跑需要 TWINKLE_HUB_TOKEN，缺 token 時由函式內 pytest.skip 略過
- 排除程式碼證據：
  - `pyproject.toml:32` — `-m 'not integration'`：預設集合排除 integration marker
  - `tests/test_twinkle.py:122` — `@pytest.mark.integration`：目標測試標記為 integration
  - `tests/test_twinkle.py:126` — `TWINKLE_HUB_TOKEN`：真跑讀取 Twinkle token
  - `tests/test_twinkle.py:127` — `if not token`：缺 token 時 runtime skip
- 替代測試證據：
  - `tests/test_twinkle.py::test_search_parses_source_with_full_content` — `tests/test_twinkle.py:77` — `assert "現行條文對累犯之處罰不足"`：mock MCP/SSE 驗證全文 Source 與 metadata — **PASSED**
    - 測試輸出：`tests/test_twinkle.py::test_search_parses_source_with_full_content PASSED [ 73%]`
  - `tests/test_twinkle.py::test_search_reuses_mcp_session` — `tests/test_twinkle.py:101` — `assert requests ==`：mock MCP 驗證 session header 在三次 RPC 間傳遞 — **PASSED**
    - 測試輸出：`tests/test_twinkle.py::test_search_reuses_mcp_session PASSED             [ 75%]`
  - `tests/test_twinkle.py::test_search_transport_failure_returns_empty` — `tests/test_twinkle.py:114` — `assert TwinkleClient(token="fake-token").search`：mock timeout 驗證網路失敗安全降級 — **PASSED**
    - 測試輸出：`tests/test_twinkle.py::test_search_transport_failure_returns_empty PASSED [ 75%]`
- 未覆蓋邊界：真實 Twinkle Hub 服務可用性、服務端 session 相容性與網路逾時
- 結論：替代測試已保護確定性程式契約；剩餘邊界屬真實模型／外部服務，故可接受未執行。
