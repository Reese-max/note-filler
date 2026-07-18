# Deselected 八項最終判讀表（2026-07-18）

> **任務**：逐一比對現有 `deselected allowlist / 映射表` 與最新
> `pytest --collect-only -m "not integration" -q` 輸出，為 8 個未執行測試
> 各自補上「功能範圍 / 風險範圍 / 是否需要補測」三欄判定。
>
> **機器可讀來源**：[`tests/deselected_allowlist.json`](../tests/deselected_allowlist.json)
>
> **既有映射表**：[`docs/deselected-substitute-mapping.md`](deselected-substitute-mapping.md)
>
> **Guard**：[`tests/test_deselection_guard.py`](../tests/test_deselection_guard.py)
>
> **目前可追溯證據快照**：[`docs/pytest-audit/deselected-evidence.md`](pytest-audit/deselected-evidence.md)

---

## 1. 驗證前置（可重現）

### 1.1 使用的 Python

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8
```

### 1.2 收集命令（僅 collection，不執行本體）

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -q -o addopts=
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -m "not integration" -q
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -m integration -q
```

### 1.3 實測計數（本工作樹）

| 集合 | 計數 | 說明 |
|---|---:|---|
| 全量 (`-o addopts=`) | **116** | 全部 node ID |
| `-m "not integration"` selected | **108** | 日常品質閘執行集合 |
| deselected（全量 − selected） | **8** | 本表判讀對象 |
| `-m integration` | **8** | 與 deselected 集合完全相等 |

### 1.4 比對結論（allowlist ↔ collect）

| 檢查項 | 結果 |
|---|---|
| allowlist 8 個 `test_id` == 實際 deselected | **True** |
| integration 集合 == deselected 集合 | **True** |
| allowlist 獨有 / collect 獨有 | **[] / []** |
| 全部 `substitute_tests`（去重 16 個）均在 selected 集合 | **True（0 missing）** |
| 排除機制 | 節點帶 `@pytest.mark.integration`，有效表達式 `-m 'not integration'` |

### 1.5 最新 deselected 完整清單（與 allowlist 順序一致，按 node ID 排序）

```text
1. tests/test_domain.py::test_detect_domain_real_grok_returns_law
2. tests/test_e2e_acceptance.py::test_e2e_acceptance_real
3. tests/test_gap.py::test_detect_gaps_real_grok
4. tests/test_llm.py::test_grok_pong_integration
5. tests/test_pipeline.py::test_run_pipeline_real_grok
6. tests/test_questions.py::test_generate_questions_real_grok
7. tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke
8. tests/test_twinkle.py::test_search_real_twinkle_hub
```

> 註：collection 層面的排除原因一律是 **marker 篩選**，不是 `skip`。
> 各測試的 Grok / Twinkle / DB / env 需求是「為何標成 integration」的執行時理由。

---

## 2. 最終判讀總表（三欄判定）

判定原則：

| 欄位 | 定義 |
|---|---|
| **功能範圍** | 該 deselected 測試實際鎖定的 production 入口與契約（確定性路徑） |
| **風險範圍** | 僅 integration 才能觸及的邊界；日常 CI 不覆蓋的部分屬何種風險 |
| **是否需要補測** | 在「確定性路徑已被 substitute 覆蓋 + guard 可收集可執行」前提下，是否仍須新增非 integration 測試 |

| # | deselected test_id | 功能範圍 | 風險範圍 | 是否需要補測 | 判定依據摘要 |
|---:|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `note_filler.domain.detect_domain`：將筆記文字分類為 law/admin/exam/other；回傳契約為 domain 字串 | **模型品質**：真 Grok（proxy 8318 / grok-4.3）對法律文字的分類正確性；非請求構造或解析邏輯 | **否** | substitute `test_detect_domain_law` 覆蓋同一入口與 `law` 回傳契約（FakeLLM）；缺口僅模型語意 |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | §12 端到端：parse→domain→questions→gaps→retrieve→assemble→export；硬不變式含原稿逐字不可變、無來源→`pending_evidence`、只掛實際引用、法條離線查核 | **模型+外部服務複合品質**：真 Grok 寫作/ gap 品質、真 Twinkle I/O、Level A 路由穩定性 | **否** | 6 個 substitute 覆蓋結構不變式與 C6/引用閘（含 `test_e2e_offline_supplement_quality_boundary`）；缺口為外部依賴品質 |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `note_filler.gap.detect_gaps`：解析 LLM 缺口 JSON，過濾 covered，只留 partial/missing，回傳 `Gap` | **模型品質**：真 Grok 對法律文本的缺口語意判斷 | **否** | substitute `test_detect_gaps_keeps_only_partial_and_missing` + 同檔邊界測試覆蓋解析/過濾/fallback |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `note_filler.llm.GrokClient.complete`：HTTP POST、Authorization、JSON body、回應 `choices[0].message.content` 解析 | **TCP/服務連通性**：真實連到 127.0.0.1:8318 與 proxy 回應格式相容性 | **否** | substitute `test_grokclient_builds_request_body` 以 monkeypatch 鎖定請求構造與解析；連通性屬環境探測，非回歸邏輯 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `note_filler.pipeline.run_pipeline` 全鏈：domain/questions/gaps/assemble；C6 無源→`pending_evidence` | **模型輸出下的 pipeline 穩定性**：真 Grok 各階段輸出語意正確性 | **否** | substitute 四件套覆蓋 C6、畸形輸出 fallback、法條查核觸發、只掛 used sources |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `note_filler.questions.generate_questions`：多行字串→`list[str]`、strip、drop 空行 | **模型品質**：真 Grok 問題相關性與法律正確性 | **否** | substitute 兩件套覆蓋切割/淨空；另有 empty/呼叫次數邊界 |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `note_filler.retrieve.retrieve_for_gap`：LawLookup A + Twinkle B + 排序 `(rank, distance)`；`Source` 結構 | **外部服務 I/O + 真 keyword 抽取**：真 Twinkle Hub 與真 Grok keyword 品質 | **否** | substitute 五件套覆蓋 A 先於 B、真 DB Level A、MCP/SSE session 與 transport fallback |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `note_filler.retrieve.twinkle.TwinkleClient.search`：MCP initialize、`tools/call`、SSE/JSON-RPC→`Source` | **真實服務可用性**：token、session 相容、網路逾時 | **否** | substitute 三件套覆蓋協議解析、session 傳遞與 transport fallback |

### 2.1 三欄彙總統計

| 是否需要補測 | 數量 | 說明 |
|---|---:|---|
| **否** | **8 / 8** | 確定性路徑均有可收集、且位於 `-m "not integration"` 的 substitute |
| **是** | **0 / 8** | 無「映射空缺」或「substitute 不在 selected」 |

---

## 3. 逐項完整判讀卡（可稽核）

下列每卡固定欄位：collect 對齊、allowlist 對齊、功能範圍、風險範圍、映射替代、覆蓋缺口、是否需要補測、理由。

### 3.1 `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 欄位 | 內容 |
|---|---|
| collect 狀態 | 在 integration 集合；被 `-m "not integration"` deselected |
| allowlist 對齊 | 是（`tests/deselected_allowlist.json` 第 1 項） |
| marker / 排除理由 | `integration`；執行時另有 `skipif` grok 不可達 |
| **功能範圍** | `detect_domain(text, llm)`：法律文字應回 `"law"`；入口契約與字串正規化 |
| **風險範圍** | 真 grok-4.3 分類品質（誤標 admin/exam/other）→ 後續問題生成/檢索路由偏差；**不影響** FakeLLM 路徑下的契約回歸 |
| 映射替代 | `tests/test_domain.py::test_detect_domain_law` |
| allowlist.coverage_gap | 真 grok 對法律文字的實際回應正確性 |
| **是否需要補測** | **否** |
| 理由 | 確定性契約已由 FakeLLM 測試鎖定；模型品質屬 integration 邊界，日常閘不要求線上 LLM |

### 3.2 `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 欄位 | 內容 |
|---|---|
| collect 狀態 | deselected（integration） |
| allowlist 對齊 | 是（第 2 項） |
| marker / 排除理由 | `integration`；需 grok + Twinkle + `law_index.db` |
| **功能範圍** | 全 pipeline 端到端與品質閘硬約束：原稿逐字不可變；無來源/`【待補證】`→`pending_evidence`；只掛實際引用來源；法條引用離線查核 |
| **風險範圍** | 真模型寫作與 gap 偵測品質、真 Twinkle 路由、Level A 穩定命中；複合失敗會在真實部署顯現，但離線結構契約已鎖 |
| 映射替代 | `test_e2e_structural_invariants`、`test_e2e_offline_supplement_quality_boundary`、`test_run_pipeline_invariant`、`test_run_pipeline_malformed_gap_output_falls_back_to_pending`、`test_run_pipeline_law_domain_runs_citation_check`、`test_retrieved_five_but_only_two_cited` |
| allowlist.coverage_gap | 真模型+真檢索下 gap/寫作品質、Level A 路由穩定性 |
| **是否需要補測** | **否** |
| 理由 | 六項 substitute 已覆蓋品質閘四硬約束與 pipeline 不變式；剩餘為外部依賴品質，不應塞進預設 non-integration 閘 |

### 3.3 `tests/test_gap.py::test_detect_gaps_real_grok`

| 欄位 | 內容 |
|---|---|
| collect 狀態 | deselected（integration） |
| allowlist 對齊 | 是（第 3 項） |
| **功能範圍** | `detect_gaps`：JSON 解析、covered 過濾、`Gap` 結構、reason 非空 |
| **風險範圍** | 真 Grok 語意漏判/誤判 partial vs missing → 檢索範圍偏差 |
| 映射替代 | `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`（另有 parse failure / fence / empty 邊界於同檔） |
| **是否需要補測** | **否** |
| 理由 | 過濾與結構契約已覆蓋；語意品質僅能 live 驗證 |

### 3.4 `tests/test_llm.py::test_grok_pong_integration`

| 欄位 | 內容 |
|---|---|
| collect 狀態 | deselected（integration） |
| allowlist 對齊 | 是（第 4 項） |
| **功能範圍** | `GrokClient.complete` 請求 URL/POST/Bearer/body/timeout 與回應解析 |
| **風險範圍** | proxy 未啟動、port 錯誤、回應 schema 漂移 → 全 LLM 路徑 runtime 失敗 |
| 映射替代 | `tests/test_llm.py::test_grokclient_builds_request_body` |
| **是否需要補測** | **否** |
| 理由 | 客戶端構造與解析已單元覆蓋；連通性應以環境/smoke 探測，不應拖垮預設 CI |

### 3.5 `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 欄位 | 內容 |
|---|---|
| collect 狀態 | deselected（integration） |
| allowlist 對齊 | 是（第 5 項） |
| **功能範圍** | `run_pipeline` 主路徑與 C6：無源 supplement → `pending_evidence`；law 領域 citation check 觸發 |
| **風險範圍** | 真 Grok 中間產物畸形導致 pipeline 行為偏移（仍應被解析/fallback 吸收時除外） |
| 映射替代 | `test_run_pipeline_invariant`、`test_run_pipeline_law_domain_runs_citation_check`、`test_retrieved_five_but_only_two_cited` |
| **是否需要補測** | **否** |
| 理由 | 不變式與引用閘已離線鎖定；真模型輸出屬 integration |

### 3.6 `tests/test_questions.py::test_generate_questions_real_grok`

| 欄位 | 內容 |
|---|---|
| collect 狀態 | deselected（integration） |
| allowlist 對齊 | 是（第 6 項） |
| **功能範圍** | `generate_questions`：多行→list、strip、去空行、型別契約 |
| **風險範圍** | 真模型產生無關/非法問題字串 → 後續 gap/retrieve 品質下降 |
| 映射替代 | `test_generate_questions_splits_multiline_string`、`test_generate_questions_strips_and_drops_blank_lines` |
| **是否需要補測** | **否** |
| 理由 | 字串處理契約已覆蓋；問題語意屬模型品質 |

### 3.7 `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 欄位 | 內容 |
|---|---|
| collect 狀態 | deselected（integration） |
| allowlist 對齊 | 是（第 7 項） |
| **功能範圍** | `retrieve_for_gap`：A/B `Source`、level 排序、keyword→LawLookup、Twinkle 查詢路徑 |
| **風險範圍** | 真 Twinkle 不可用或真 keyword 抽壞 → 檢索空結果/排序偏移；品質閘硬約束（pending_evidence）仍可守底線 |
| 映射替代 | `test_retrieve_for_gap_law_domain_puts_level_A_before_B`、`test_search_law_sources_returns_level_A_law_articles`、`test_search_parses_source_with_full_content` |
| **是否需要補測** | **否** |
| 理由 | 排序與協議/DB 路徑已覆蓋；live I/O 保留 integration |

### 3.8 `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 欄位 | 內容 |
|---|---|
| collect 狀態 | deselected（integration） |
| allowlist 對齊 | 是（第 8 項） |
| **功能範圍** | `TwinkleClient.search`：MCP 握手、tools/call、SSE 解包、Source 映射 |
| **風險範圍** | 服務端 session/逾時/token 失效 → 僅影響真 Twinkle 路徑 |
| 映射替代 | `tests/test_twinkle.py::test_search_parses_source_with_full_content` |
| **是否需要補測** | **否** |
| 理由 | 協議解析已 mock 覆蓋；服務可用性屬運維/integration smoke |

---

## 4. 風險分級（跨 8 項）

| 風險類型 | 涉及 # | 預設 CI 暴露？ | 緩解 |
|---|---|---|---|
| 模型語意品質（Grok） | 1, 2, 3, 5, 6 | 否 | 保留 integration；必要時手動 `-m integration` |
| 外部服務 I/O（Twinkle） | 2, 7, 8 | 否 | token/env 就緒後跑 integration smoke |
| TCP/proxy 連通（8318） | 4, 及所有 grok live | 否 | 環境探測 + pong integration |
| 品質閘硬約束（原稿不可變、pending_evidence、只掛引用、法條離線查核） | 2, 5 為主 | **是（已覆蓋）** | 108 項 non-integration 回歸 |

---

## 5. 最終結論

1. **集合一致**：最新 collect 的 8 個 deselected 與 `tests/deselected_allowlist.json` **完全一致**；與 `-m integration` 亦一致。
2. **映射完整**：8 項皆有非空 `substitute_tests`，且 16 個去重替代 node ID **全部落在** `-m "not integration"` selected 集合。
3. **三欄判定**：8 項之「是否需要補測」**全部為否**——缺口皆屬模型品質或外部服務可用性，不應擴張日常 non-integration 閘。
4. **證據契約已落地**：allowlist 已補上 `decision`、排除程式碼 anchor 與替代斷言 anchor；guard 會驗證 anchor 存在且替代測試實際通過。
5. **後續若需 live 驗證**：在代理與 token 就緒時，可單獨執行  
   `pytest -m integration -q`（預期可能因 env 條件 skip 部分項目，不納入本判讀表之補測義務）。

---

## 6. 產物與稽核鏈

| 產物 | 路徑 | 角色 |
|---|---|---|
| 本最終判讀表 | `docs/deselected-final-judgment-2026-07-18.md` | 三欄判定 + collect 比對證據 |
| 機器 allowlist | `tests/deselected_allowlist.json` | 8 項 + decision + 排除/替代程式碼 anchor + gap |
| 詳細映射 | `docs/deselected-substitute-mapping.md` | 斷言級對照 |
| 穩定 guard | `tests/test_deselection_guard.py` | 計數 (116,108,8)、anchor 與映射可收集/可執行 |
| 逐項證據快照 | `docs/pytest-audit/deselected-evidence.md` | source anchor + PASSED 輸出 + 結論 |

### 6.1 本報告產生時的比對腳本輸出（摘要）

```text
TOTAL 116 SELECTED 108 DESELECTED 8 INTEGRATION 8
ALLOWLIST_MATCH True
INTEGRATION_EQ_DESELECTED True
SUBS 16 MISSING_FROM_SELECTED []
```
