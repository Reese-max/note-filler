# 覆蓋等價性審計報告

> 日期：2026-07-18
> 目標：比對 109 個已通過測試的覆蓋範圍，判定 8 個未執行測試是否已有等價覆蓋
> 基線：`109 passed, 8 deselected in 5.00s`（2026-07-18 實測）

---

## 一、環境與基線

| 項目 | 值 |
|---|---|
| 測試總數 | 117 |
| 預設執行（`-m 'not integration'`） | 109 |
| 被排除（integration） | 8 |
| Guard 測試 | 3（全部 PASSED） |
| 排除機制 | L1 collection marker + L2 skipif + L3 runtime skip + L4 CI |

```bash
# 實測輸出
109 passed, 8 deselected in 5.00s
3 passed in 4.22s  (test_deselection_guard.py)
```

---

## 二、八項未執行測試總覽

| # | 測試 ID | 覆蓋函式 | 外部依賴 | 未執行原因 |
|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `domain.detect_domain` | grok TCP 8318 | marker + skipif |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | §12 端到端 pipeline | grok + Twinkle + law_index.db | marker + 三重 skip |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `gap.detect_gaps` | grok TCP 8318 | marker + skipif |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `llm.GrokClient.complete` | grok TCP 8318 | marker + skipif |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `pipeline.run_pipeline` | grok TCP 8318 | marker + skipif |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `questions.generate_questions` | grok TCP 8318 | marker + skipif |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `retrieve.retrieve_for_gap` | Twinkle Hub + grok + law_index.db | marker + 四重 skip |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `twinkle.TwinkleClient.search` | Twinkle Hub token | marker + runtime skip |

---

## 三、逐項覆蓋等價性判定

### #1 `test_detect_domain_real_grok_returns_law`

| 維度 | 整合測試 | 替代測試 |
|---|---|---|
| 生產函式 | `domain.py:22-40` `detect_domain()` | 同左 |
| 程式碼路徑 | clean label match (branch 1) | branch 1 + 2 + 3（三分支全覆蓋） |
| 差異 | 真 grok 回應驗證 | FakeLLM 注入 |
| 替代測試 | — | `test_detect_domain_law` (line 19) |
| 等價判定 | — | **等價，且替代覆蓋更廣** |

**結論**：替代測試透過 FakeLLM 驗證 `detect_domain` 的三條分支（clean match / substring extraction / fallback to other），覆蓋範圍**大於**整合測試（僅 branch 1）。未覆蓋部分為「真 grok 對法律文字的語意品質」，屬模型品質驗證，不屬程式碼路徑。

---

### #2 `test_e2e_acceptance_real`

| 維度 | 整合測試 | 替代測試 |
|---|---|---|
| 生產函式 | `pipeline.run_pipeline` + 5 個 assert helper | 同左 |
| 5 個共用 assert helper | `_assert_immutable_original` / `_assert_no_source_gate` / `_assert_law_citations_ok` / `_assert_markdown_contract` / `_assert_supplement_quality` | structural_invariants 覆蓋前 4 個；quality_boundary 覆蓋第 5 個 |
| 差異 | 真 grok + 真 Twinkle | FakeLLM + _StubTwinkle |
| 替代測試 | — | `test_e2e_structural_invariants` (line 170-173), `test_e2e_offline_supplement_quality_boundary` (line 204), `test_run_pipeline_invariant` (line 85), `test_run_pipeline_malformed_gap_output_falls_back_to_pending` (line 145), `test_run_pipeline_law_domain_runs_citation_check` (line 122), `test_retrieved_five_but_only_two_cited` (line 82) |
| 等價判定 | — | **等價**（6 個替代全覆蓋） |

**結論**：6 個替代測試共同覆蓋 `run_pipeline` 全部程式碼路徑 + 5 個硬不變式（原稿不可變、無來源閘、法條查核、Markdown 契約、補充品質邊界）。未覆蓋部分為「真模型產出的 gap 偵測品質」與「Level A 路由穩定性」，均為模型/服務品質驗證。

---

### #3 `test_detect_gaps_real_grok`

| 維度 | 整合測試 | 替代測試 |
|---|---|---|
| 生產函式 | `gap.py:15-44` `detect_gaps()` | 同左 |
| 程式碼路徑 | covered 過濾 + Gap 建立 | 同左 |
| 差異 | 真 grok 回應 | FakeLLM（回傳含 covered/partial/missing） |
| 替代測試 | — | `test_detect_gaps_keeps_only_partial_and_missing` (line 26) |
| 等價判定 | — | **等價** |

**結論**：替代測試精確驗證 `detect_gaps` 的核心過濾邏輯（只保留 partial/missing，移除 covered）。未覆蓋為「真 grok 對法律文本的缺口判斷品質」。

---

### #4 `test_grok_pong_integration`

| 維度 | 整合測試 | 替代測試 |
|---|---|---|
| 生產函式 | `llm.py` `GrokClient.complete()` | 同左 |
| 程式碼路徑 | HTTP POST + Bearer auth + response parse | monkeypatch 驗證相同路徑 |
| 差異 | 真 TCP 連線 | monkeypatch `requests.post` |
| 替代測試 | — | `test_grokclient_builds_request_body` (line 53) |
| 等價判定 | — | **等價**（程式碼路徑相同） |

**結論**：替代測試用 monkeypatch 驗證 request body、Bearer header、POST endpoint、timeout 與 response parse——與整合測試走完全相同的程式碼路徑，唯一差異為 TCP 層。未覆蓋為「真實 TCP 連線到 proxy 的連通性」，屬基礎設施驗證。

---

### #5 `test_run_pipeline_real_grok`

| 維度 | 整合測試 | 替代測試 |
|---|---|---|
| 生產函式 | `pipeline.run_pipeline` | 同左 |
| C6 不變式 | 無來源→pending_evidence；雙來源→verified | 同左 |
| 差異 | 真 grok 模型輸出 | FakeLLM |
| 替代測試 | — | `test_run_pipeline_invariant` (line 85), `test_run_pipeline_malformed_gap_output_falls_back_to_pending` (line 145), `test_run_pipeline_law_domain_runs_citation_check` (line 122), `test_retrieved_five_but_only_two_cited` (line 82) |
| 等價判定 | — | **等價** |

**結論**：4 個替代測試覆蓋 `run_pipeline` 全部確定性路徑：C6 不變式、畸形輸出降級、law 域 citation check、來源過濾。未覆蓋為「真 Grok 模型輸出的 domain/questions/gaps 正確性 + pipeline 穩定性」。

---

### #6 `test_generate_questions_real_grok`

| 維度 | 整合測試 | 替代測試 |
|---|---|---|
| 生產函式 | `questions.py` `generate_questions()` | 同左 |
| 程式碼路徑 | LLM 回應切割 + strip + 空行移除 | 同左 |
| 差異 | 真 grok 回應 | FakeLLM（多行字串） |
| 替代測試 | — | `test_generate_questions_splits_multiline_string` (line 25), `test_generate_questions_strips_and_drops_blank_lines` (line 38) |
| 等價判定 | — | **等價** |

**結論**：2 個替代測試精確驗證多行切割與 strip/空行移除的確定性邏輯。未覆蓋為「真 Grok 對法律文本的問題生成品質」。

---

### #7 `test_retrieve_for_gap_real_twinkle_smoke`

| 維度 | 整合測試 | 替代測試 |
|---|---|---|
| 生產函式 | `retrieve.py` `retrieve_for_gap()` + `twinkle.TwinkleClient.search()` + `law_search.search_law_sources()` | 同左 |
| Level A 優先排序 | 真 Twinkle + 真 law_index.db | FakeLaw + FakeTwinkle + 離線 law_index |
| 差異 | 真實全棧 I/O | mock/离线 |
| 替代測試 | — | `test_retrieve_for_gap_law_domain_puts_level_A_before_B` (line 72), `test_search_law_sources_returns_level_A_law_articles` (line 35), `test_search_parses_source_with_full_content` (line 77), `test_search_reuses_mcp_session` (line 101), `test_search_transport_failure_returns_empty` (line 114) |
| 等價判定 | — | **等價** |

**結論**：5 個替代測試覆蓋 `retrieve_for_gap` 的 Level A 優先排序、law_index 查詢、Twinkle MCP session 管理、SSE 全文解析、transport failure 降級。未覆蓋為「真實 Twinkle Hub 服務 I/O 與真 Grok 關鍵字抽取品質」。

---

### #8 `test_search_real_twinkle_hub`

| 維度 | 整合測試 | 替代測試 |
|---|---|---|
| 生產函式 | `twinkle.py` `TwinkleClient.search()` | 同左 |
| MCP session | 真實 Twinkle Hub MCP 服務 | mock MCP/SSE |
| 差異 | 真實網路 I/O | mock |
| 替代測試 | — | `test_search_parses_source_with_full_content` (line 77), `test_search_reuses_mcp_session` (line 101), `test_search_transport_failure_returns_empty` (line 114) |
| 等價判定 | — | **等價** |

**結論**：3 個替代測試覆蓋 `TwinkleClient.search` 的 Source metadata 映射、MCP session 重用（initialize→initialized→tools/call）、transport failure 安全降級。未覆蓋為「真實 Twinkle Hub 服務可用性與服務端 session 相容性」。

---

## 四、覆蓋缺口分類

所有 8 個整合測試未覆蓋的部分**均非程式碼路徑**，而是：

| 缺口類型 | 受影響測試 | 說明 |
|---|---|---|
| 模型語意品質 | #1, #2, #3, #5, #6 | 真 Grok 對法律文字的回應品質（domain 分類、gap 偵測、問題生成） |
| 外部服務 I/O | #2, #7, #8 | 真 Twinkle Hub 服務的可用性與回應格式 |
| TCP/Proxy 連通性 | #4 + 所有 grok 相關 | 真實 TCP 連線到 proxy 8318 |

以上缺口均為**外部依賴的環境/服務驗證**，不影響確定性程式碼路徑的覆蓋。

---

## 五、結論

### 等價覆蓋判定

| # | 測試 | 程式碼路徑等價 | 替代測試數 | 判定 |
|---|---|---|---|---|
| 1 | `test_detect_domain_real_grok_returns_law` | ✅ | 1 | 等價（替代覆蓋更廣） |
| 2 | `test_e2e_acceptance_real` | ✅ | 6 | 等價 |
| 3 | `test_detect_gaps_real_grok` | ✅ | 1 | 等價 |
| 4 | `test_grok_pong_integration` | ✅ | 1 | 等價 |
| 5 | `test_run_pipeline_real_grok` | ✅ | 4 | 等價 |
| 6 | `test_generate_questions_real_grok` | ✅ | 2 | 等價 |
| 7 | `test_retrieve_for_gap_real_twinkle_smoke` | ✅ | 5 | 等價 |
| 8 | `test_search_real_twinkle_hub` | ✅ | 3 | 等價 |

### 總結

- **8/8 已通過等價覆蓋判定**：所有確定性程式碼路徑均有非 integration 測試覆蓋
- **16 個去重替代測試**全部在 109 個已通過測試中，且由 `test_deselection_guard.py` 持續監控
- **覆蓋缺口**全部為外部服務品質驗證（模型語意、網路連通、服務可用性），不影響 CI 閘的確定性覆蓋
- **Guard 機制**：3 個守衛測試持續驗證 allowlist 穩定性、deselected details 正確性、substitute mapping 完整性

---

## 六、驗證命令

```bash
# 預設執行（109 passed）
pytest -q --tb=short

# Guard 測試（3 passed）
pytest tests/test_deselection_guard.py -vv --tb=short

# 替代測試靶向驗證
pytest -vv --tb=short tests/test_domain.py::test_detect_domain_law tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing tests/test_llm.py::test_grokclient_builds_request_body
```
