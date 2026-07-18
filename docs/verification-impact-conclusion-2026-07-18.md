# 整體驗證影響結論

> 日期：2026-07-18
> Python：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`
> 工作樹：`adng/0c8e6e28`（clean）
> 本報告為所有前期報告（盤點、覆蓋等價審計、guard 映射、live 補跑、離線回歸、failing test 驗證）之整合判定，並明確標示每個未執行測試的最終判決與其對整體驗證結論的限制。

---

## 1. 當前測試基線

| 項目 | 值 | 來源 |
|---|---|---|
| 測試總數 | 117 | `pytest --collect-only -q -o addopts=` |
| 預設執行（`-m 'not integration'`） | **109 passed** | `pytest -q` 實測 6.35s |
| 被排除（integration / deselected） | **8** | marker 篩選，非 skip |
| Guard 守衛 | **3 passed** | `test_deselection_guard.py`：allowlist 穩定、deselected details 正確、替代映射完整 |
| 去重替代測試 | **16** | 全部落在 109 passed 集合內，0 missing |
| Live 補跑結果（歷史） | **7/8 PASSED, 1/8 SKIPPED** | `30db593` 提交（#7 因缺 `GOV_AI_ENABLE_TWINKLE_MCP=1` 跳過） |

---

## 2. 判定規則

本報告採用以下規則決定「需補測」vs「可接受未執行」：

1. **必須補測**：若該 integration 測試的確定性程式契約（函式入口、資料結構、quality gate 硬約束）沒有被任何非 integration 測試覆蓋，或其替代測試失敗。
2. **可接受未執行**：若替代測試已覆蓋相同的確定性程式路徑與品質閘硬約束，且未覆蓋的部分僅涉及外部服務語意品質或環境連通性。
3. **品質閘硬約束**（原稿不可變、無來源 → `pending_evidence`、只掛實際引用來源、法條離線查核）不因 integration 未執行而被弱化。

---

## 3. 逐項判定與對整體結論的限制

### #1 `test_detect_domain_real_grok_returns_law`

| 欄位 | 內容 |
|---|---|
| **判定** | **可接受未執行** |
| 替代測試 | `test_detect_domain_law`（FakeLLM，覆蓋三條分支，比 integration 更廣） |
| 程式碼覆蓋 | ✅ 等價（FakeLLM 覆蓋 clean match / substring extraction / fallback to other） |
| **對整體結論的限制** | 真 Grok 對法律文字的**語意分類品質**未被證明。若模型版本更換或 prompt 變更導致 `detect_domain` 回傳錯誤 domain，日常 CI 不會攔截。**限制程度：低**——誤判只影響路由效率，不會破壞原稿不可變或來源閘。 |
| 觸發補跑時機 | Grok proxy / model / prompt 變更、發版 |

### #2 `test_e2e_acceptance_real`

| 欄位 | 內容 |
|---|---|
| **判定** | **可接受未執行**（已由 `30db593` live 補跑通過） |
| 替代測試 | 6 個：`test_e2e_structural_invariants`、`test_e2e_offline_supplement_quality_boundary`、`test_run_pipeline_invariant`、`test_run_pipeline_malformed_gap_output_falls_back_to_pending`、`test_run_pipeline_law_domain_runs_citation_check`、`test_retrieved_five_but_only_two_cited` |
| 程式碼覆蓋 | ✅ 等價（5 個 assert helper 全覆蓋 + pipeline 不變式） |
| **對整體結論的限制** | 真模型的**gap 偵測品質**與**補充寫作品質**（Level A 路由、`[^n]` 註腳）未被日常 CI 證明；真 Twinkle 的 **Level A 路由穩定性**依賴外部服務。四項硬品質閘（原稿不可變、`pending_evidence`、只掛引用、法條離線查核）仍由日常 109 passed 強制保護。**限制程度：中**——外部服務品質下降時使用者可見的補充品質會受影響，但不會產生無證偽造內容。 |
| 觸發補跑時機 | Grok / Twinkle / law_index.db 變更、發版 |

### #3 `test_detect_gaps_real_grok`

| 欄位 | 內容 |
|---|---|
| **判定** | **可接受未執行** |
| 替代測試 | `test_detect_gaps_keeps_only_partial_and_missing` + 同檔 parse failure / non-array / fence / empty 邊界測試 |
| 程式碼覆蓋 | ✅ 等價（過濾邏輯 + fallback 契約全覆蓋） |
| **對整體結論的限制** | 真 Grok 的**缺口語意判斷品質**（partial vs missing 分類準確度）未被證明。**限制程度：低**——語意誤判會影響補充範圍但不會改寫原稿或放寬來源閘。 |
| 觸發補跑時機 | 模型 prompt / 版本變更 |

### #4 `test_grok_pong_integration`

| 欄位 | 內容 |
|---|---|
| **判定** | **可接受未執行** |
| 替代測試 | `test_grokclient_builds_request_body`（monkeypatch 驗證相同程式碼路徑） |
| 程式碼覆蓋 | ✅ 等價（request body、Bearer、POST、timeout、response parse 全覆蓋） |
| **對整體結論的限制** | **TCP/proxy 連通性**未被日常 CI 證明。若 proxy 未啟動或 port 錯誤，LLM 路徑會 runtime 失敗。**限制程度：低**——連通性屬運維問題，不是邏輯回歸；proxy 不通時所有 grok 相關功能自然不可用，但不會產生靜默錯誤。 |
| 觸發補跑時機 | proxy 端點 / port / model 設定變更 |

### #5 `test_run_pipeline_real_grok`

| 欄位 | 內容 |
|---|---|
| **判定** | **可接受未執行** |
| 替代測試 | `test_run_pipeline_invariant`、`test_run_pipeline_malformed_gap_output_falls_back_to_pending`、`test_run_pipeline_law_domain_runs_citation_check`、`test_retrieved_five_but_only_two_cited` |
| 程式碼覆蓋 | ✅ 等價（C6 不變式、畸形 fallback、citation check、引用過濾全覆蓋） |
| **對整體結論的限制** | 真模型各階段（domain/questions/gaps/writer）的**輸出穩定性**未被證明；若模型回傳畸形 JSON 導致非 fallback 路徑的 edge case，日常 CI 不會攔截。**限制程度：中**——pipeline 穩定性依賴模型輸出品質，但畸形已有 fallback 吸收。 |
| 觸發補跑時機 | Grok 變更、發版 |

### #6 `test_generate_questions_real_grok`

| 欄位 | 內容 |
|---|---|
| **判定** | **可接受未執行** |
| 替代測試 | `test_generate_questions_splits_multiline_string`、`test_generate_questions_strips_and_drops_blank_lines` + 空回應 / 呼叫次數邊界 |
| 程式碼覆蓋 | ✅ 等價（字串切割、strip、空行移除、型別契約全覆蓋） |
| **對整體結論的限制** | 真 Grok 的**問題語意品質**（與法律文本的相關性、可查證性）未被證明。**限制程度：低**——問題品質下降會降低後續 gap/retrieve 品質，但不會破壞程式契約或品質閘。 |
| 觸發補跑時機 | 模型 prompt / 版本變更 |

### #7 `test_retrieve_for_gap_real_twinkle_smoke`

| 欄位 | 內容 |
|---|---|
| **判定** | **可接受未執行**（歷史補跑結果為 SKIPPED，因缺 `GOV_AI_ENABLE_TWINKLE_MCP=1`） |
| 替代測試 | 5 個：Level A 優先排序、離線 law_index 查詢、MCP/SSE 解析、session 重用、transport failure 降級 |
| 程式碼覆蓋 | ✅ 等價（排序、協議、DB 路徑、降級全覆蓋） |
| **對整體結論的限制** | 真 Twinkle Hub 的**服務 I/O** 與真 Grok 的**關鍵字抽取品質**未被證明。測試的 `all(...)` 對空清單為真，不能把 PASS 解讀為「一定取得結果」。**限制程度：中**——外部檢索失敗時空結果走 `pending_evidence`，不會把無證內容升為 verified，但使用者會看到空補充。 |
| 觸發補跑時機 | Twinkle / law DB / Grok 變更、發版 |

### #8 `test_search_real_twinkle_hub`

| 欄位 | 內容 |
|---|---|
| **判定** | **可接受未執行** |
| 替代測試 | 3 個：Source metadata 映射、MCP session 重用、transport failure 降級 |
| 程式碼覆蓋 | ✅ 等價（協議解析、session、降級全覆蓋） |
| **對整體結論的限制** | 真 Twinkle Hub 的**服務可用性**與**session 相容性**未被證明。測試對空 `results` 不失敗，PASS 不代表服務一定回傳非空資料。**限制程度：低**——服務中斷只影響檢索可用性，呼叫端維持安全的無來源路徑。 |
| 觸發補跑時機 | Twinkle 協定 / token / 發版 |

---

## 4. 判決彙總

| # | 測試 | 判決 | 替代數 | 程式碼等價 | 對整體限制程度 |
|---:|---|---|---:|---|---|
| 1 | `test_detect_domain_real_grok_returns_law` | **可接受未執行** | 1 | ✅ | 低 |
| 2 | `test_e2e_acceptance_real` | **可接受未執行** | 6 | ✅ | 中 |
| 3 | `test_detect_gaps_real_grok` | **可接受未執行** | 1 | ✅ | 低 |
| 4 | `test_grok_pong_integration` | **可接受未執行** | 1 | ✅ | 低 |
| 5 | `test_run_pipeline_real_grok` | **可接受未執行** | 4 | ✅ | 中 |
| 6 | `test_generate_questions_real_grok` | **可接受未執行** | 2 | ✅ | 低 |
| 7 | `test_retrieve_for_gap_real_twinkle_smoke` | **可接受未執行** | 5 | ✅ | 中 |
| 8 | `test_search_real_twinkle_hub` | **可接受未執行** | 3 | ✅ | 低 |

**結論：0/8 需補測，8/8 可接受未執行。**

---

## 5. 對整體驗證結論的綜合限制

### 5.1 品質閘不受影響

四項硬品質閘（原稿逐字不可變、無來源 → `pending_evidence`、只掛實際引用來源、法條引用離線查核）**全部由 109 passed 的日常回歸強制保護**，不受 8 項 integration 未執行的影響。

### 5.2 唯一未被日常 CI 證明的驗證維度

| 維度 | 受影響 # | 限制描述 |
|---|---|---|
| **模型語意品質** | 1, 2, 3, 5, 6 | 真 Grok 的分類、缺口判斷、問題生成、寫作品質無法在離線環境證明 |
| **外部服務 I/O** | 2, 7, 8 | 真 Twinkle Hub 的可用性、session 相容性、MCP 協議穩定性 |
| **TCP/Proxy 連通性** | 4, 及所有 grok live | proxy 8318 的實際連線與回應格式 |

以上三維度均為**外部依賴的環境/服務驗證**，不是確定性程式碼路徑；其失敗會導致功能不可用（可用性問題），但不會導致靜默的資料完整性破壞。

### 5.3 #7、#8 的假綠風險

#7（`test_retrieve_for_gap_real_twinkle_smoke`）和 #8（`test_search_real_twinkle_hub`）的現有斷言對空結果不失敗。即使歷史補跑 PASS，也不能宣稱「Twinkle 一定回傳非空資料」。若未來需要服務健康保證，應另行定義非空結果契約與穩定查詢，不應把不穩定外部服務塞進日常 CI。

### 5.4 結論

**預設驗證通過。** 現行 109 passed + 8 個有邊界的 integration deselected；整體品質閘通過；外部 integration 維持條件式補跑策略，不降低或移除測試。

---

## 6. 重跑驗證摘要（本報告撰寫時）

```powershell
# 全量收集
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -q -o addopts=
# 117 tests collected

# 日常回歸
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest -q
# 109 passed, 8 deselected in 6.35s

# Integration 收集
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -m integration -q
# 8/117 tests collected (109 deselected)

# Guard 守衛
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_deselection_guard.py -q -s
# DESELECTED_AUDIT=8 MAPPED_TESTS=16
# TARGETED_VERIFICATION=PASS
# 3 passed in 4.11s
```

---

## 7. 產物對應

| 產物 | 路徑 |
|---|---|
| 本整體驗證影響結論 | `docs/verification-impact-conclusion-2026-07-18.md` |
| 機器 allowlist | `tests/deselected_allowlist.json` |
| Guard 測試 | `tests/test_deselection_guard.py` |
| 詳細映射 | `docs/deselected-substitute-mapping.md` |
| 三欄判定表 | `docs/deselected-final-judgment-2026-07-18.md` |
| 覆蓋等價審計 | `docs/coverage-equivalence-audit-2026-07-18.md` |
| Live 補跑結果 | `docs/integration-test-individual-results-2026-07-18.md` |
| 最終驗證報告 | `docs/final-verification-report-2026-07-18.md` |
