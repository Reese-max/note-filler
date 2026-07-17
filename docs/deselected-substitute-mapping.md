# Deselected 測試 → 替代測試逐項覆蓋對照表

> 本表追蹤 8 個因 `-m 'not integration'` 而 deselected 的整合測試，逐一標明
> 被驗證的功能、測試情境、具體斷言、替代測試 node ID 與覆蓋缺口。
> 機器可讀版：`tests/deselected_allowlist.json`。

---

## 對照總表

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 項目 | 內容 |
|---|---|
| **排除原因** | 需要真實 grok proxy (127.0.0.1:8318)；附 `@pytest.mark.skipif(not _grok_reachable())` |
| **被驗證功能** | `note_filler.domain.detect_domain` — LLM 領域偵測（將筆記文字分類為 law/admin/exam/other） |
| **Deselected 情境** | 真打 Grok (grok-4.3)，餵刑法第271條殺人罪文字，驗證回傳 `"law"` |
| **Deselected 斷言** | `assert detect_domain(text, GrokClient()) == "law"` |
| **替代測試** | `tests/test_domain.py::test_detect_domain_law` |
| **替代情境** | `FakeLLM(["law"])` 餵同一法律文字（行政程序法第92條），驗證 `detect_domain` 正確解析 LLM 回應並回傳 domain 字串 |
| **替代斷言** | `assert detect_domain("行政程序法第92條…", FakeLLM(["law"])) == "law"` |
| **覆蓋的確定性路徑** | (a) LLM 回應字串 `"law"` 經正規化後正確回傳；(b) 法律文字輸入格式處理 |
| **覆蓋缺口** | 真 Grok 對法律文字的實際回應正確性（模型品質）——無法用 FakeLLM 替代 |

---

### 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 項目 | 內容 |
|---|---|
| **排除原因** | 需要真實 Grok + Twinkle Hub + `data/law_index.db`；多重 skip 條件 |
| **被驗證功能** | §12 端到端驗收：parse → domain → questions → gaps → retrieve → assemble → export 全流程 + 5 個硬不變式 |
| **Deselected 情境** | 真 grok + 真 TwinkleClient + 真 LawLookup 跑完整 pipeline，含有界重跑最多 6 次取 Level A 路由穩定性 |
| **Deselected 斷言** | 5 個結構不變式 + `_assert_supplement_quality`（含 Level A 路由、非原始記錄倒出、`[^n]` 註腳標引用）+ verified 合規斷言 |
| **替代測試 × 4** | 見下表 |

#### 替代 A：`tests/test_e2e_acceptance.py::test_e2e_structural_invariants`

| 項目 | 內容 |
|---|---|
| **替代情境** | 用 `FakeLLM` + `_StubTwinkle`（回兩個獨立 A/B 來源）+ 真 `LawLookup` 跑完整 pipeline |
| **替代斷言** | `_assert_immutable_original`：`doc.original.full_text == "\n".join(p.text for p in doc.original.paragraphs)` + 每段 `para.text in note_text` + 每個 original segment 逐字出現在原文 |
| | `_assert_no_source_gate`：無源 supplement → `confidence == "pending_evidence"`；verified → sources 非空且 level ∈ A/B/C/D |
| | `_assert_law_citations_ok`：`check_law_citations(text=seg.text, lookup=law)` 無 `article_not_found` |
| | `_assert_markdown_contract`：`to_markdown(doc)` 含 `> 【補充】`、pending_evidence 含 `⚠待補證`、`to_json(doc)` 可序列化 |

#### 替代 B：`tests/test_pipeline.py::test_run_pipeline_invariant`

| 項目 | 內容 |
|---|---|
| **替代情境** | `FakeLLM`（7 個 canned 回應）+ `FakeTwinkle`（gap1 無源、gap2 兩獨立 A/B）+ `FakeLaw` 跑 pipeline |
| **替代斷言** | C6 不變式：無源 supplement → `confidence == "pending_evidence"`；>=2 獨立 A/B 源 → `confidence == "verified"` |
| | `gap2[0].confidence == "verified"` + `len(gap2[0].sources) == 2` + `"聽證程序" in gap2[0].text` |
| | `len(twinkle.queries) == 2`（每個 gap 恰觸發一次 twinkle retrieve） |

#### 替代 C：`tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`

| 項目 | 內容 |
|---|---|
| **替代情境** | law 領域 FakeLLM + monkeypatch `check_law_citations` 為 recording fake，驗證每個補充段都經過法規引用檢查 |
| **替代斷言** | `len(calls) == len(supplements)` — 每個補充段至少跑一次 `check_law_citations(text=..., lookup)` |
| | `assert calls` — law 領域至少跑一次（非空） |

#### 替代 D：`tests/test_correction.py::test_retrieved_five_but_only_two_cited`

| 項目 | 內容 |
|---|---|
| **替代情境** | `assemble_correction` 有 5 個 retrieved sources 但 writer 只引用 2 個（id "2" 和 "4"） |
| **替代斷言** | `sup.sources == ["2", "4"]` — segment 只掛實際引用的來源 |
| | `sup.confidence == "verified"` — 2 個獨立 A → verified |
| **覆蓋的確定性路徑** | (a) 原稿逐字不變；(b) 無來源閘 C6；(c) 法條引用合法；(d) markdown 格式合規；(e) 補充段來源過濾（只掛 used） |
| **覆蓋缺口** | 真模型 + 真檢索下的 gap 偵測品質、`_assert_supplement_quality`（Level A 路由穩定性、非原始記錄倒出）、真 Twinkle Hub I/O |

---

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`

| 項目 | 內容 |
|---|---|
| **排除原因** | 需要真實 grok proxy (127.0.0.1:8318)；附 `@pytest.mark.skipif(not _grok_reachable())` |
| **被驗證功能** | `note_filler.gap.detect_gaps` — LLM 缺口偵測（過濾 covered，只留 partial/missing） |
| **Deselected 情境** | 真 Grok + 行政程序法第92條筆記 + 2 題（1 題已涵蓋、1 題明顯未涵蓋），驗缺口結構與語意正確 |
| **Deselected 斷言** | `isinstance(gaps, list)` + `all(isinstance(g, Gap))` + `all(g.status in ("partial", "missing"))` + `"裁量基準" in g.question or "罰鍰" in g.question` |
| **替代測試** | `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing` |
| **替代情境** | `FakeLLM` 回 3 題（1 covered + 1 partial + 1 missing），驗過濾邏輯 |
| **替代斷言** | `[g.status for g in gaps] == ["partial", "missing"]` — covered 被正確過濾 |
| | `[g.question for g in gaps] == ["乙問題", "丙問題"]` — 順序正確 |
| | `all(isinstance(g, Gap) for g in gaps)` — 型別正確 |
| | `all(g.reason for g in gaps)` — reason 非空 |
| **覆蓋的確定性路徑** | (a) JSON 陣列解析；(b) `covered` 狀態過濾；(c) `Gap` 物件結構；(d) `reason` 欄位填充 |
| **覆蓋缺口** | 真 Grok 對法律文本的缺口判斷語意品質（模型品質） |

> 額外覆蓋：同檔 `test_detect_gaps_calls_llm_exactly_once`（呼叫次數=1）、
> `test_detect_gaps_parse_failure_marks_all_missing`（JSON 解析失敗保守 fallback）、
> `test_detect_gaps_non_array_json_also_fallbacks`（dict 回應 fallback）、
> `test_detect_gaps_strips_code_fence`（```json 圍欄剝除）、
> `test_detect_gaps_empty_questions_short_circuits`（空問題短路）——共 5 個非 integration 測試補足邊界情境。

---

### 4. `tests/test_llm.py::test_grok_pong_integration`

| 項目 | 內容 |
|---|---|
| **排除原因** | 需要真實 grok proxy (127.0.0.1:8318)；附 `@pytest.mark.skipif(not _grok_reachable())` |
| **被驗證功能** | `note_filler.llm.GrokClient.complete` — 真實 HTTP 連線 + 回應解析 |
| **Deselected 情境** | 真 GrokClient 送 "Reply with exactly one word: PONG"，驗回應含 `"PONG"` |
| **Deselected 斷言** | `assert "PONG" in out.upper()` |
| **替代測試** | `tests/test_llm.py::test_grokclient_builds_request_body` |
| **替代情境** | monkeypatch `urllib.request.urlopen`，驗 GrokClient 構造的完整 HTTP 請求 |
| **替代斷言** | `out == "OK"` — 回應解析正確 |
| | `captured["url"] == "http://127.0.0.1:8318/v1/chat/completions"` — URL 正確 |
| | `captured["method"] == "POST"` — HTTP 方法 |
| | `captured["auth"] == "Bearer secret"` — API key 格式 |
| | `captured["content_type"] == "application/json"` — Content-Type |
| | `captured["body"] == {"model": "grok-4.3", "messages": [...], "temperature": 0.0}` — 請求體結構 |
| | `captured["timeout"] == 42` — 自訂逾時傳入 |
| **覆蓋的確定性路徑** | (a) URL 組裝（base_url + endpoint）；(b) Authorization header；(c) JSON 請求體序列化；(d) 回應 JSON 解析（`choices[0].message.content`）；(e) 自訂參數（model, timeout, temperature） |
| **覆蓋缺口** | 真實 TCP 連線到 proxy 的連通性、proxy 端回應格式相容性 |

---

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 項目 | 內容 |
|---|---|
| **排除原因** | 需要真實 grok proxy；twinkle/law 用 fake 隔離 |
| **被驗證功能** | `note_filler.pipeline.run_pipeline` — 完整 pipeline 在真 Grok 輸出下不崩潰 + C6 不變式 |
| **Deselected 情境** | 真 `GrokClient` + `FakeTwinkle`（全回空）+ `FakeLaw`，驗 parse → domain → questions → gaps → assemble 整條不炸 |
| **Deselected 斷言** | `doc.original is not None` + `isinstance(doc.segments, list)` + `seg.confidence == "pending_evidence"`（無源 supplement） |
| **替代測試 × 3** | 見替代 B/C/D（同 §2 中已列出的 3 個測試） |

| 替代 | Node ID | 覆蓋內容 |
|---|---|---|
| B | `tests/test_pipeline.py::test_run_pipeline_invariant` | C6 不變式（無源→pending_evidence、有源≥2獨立→verified）；twinkle 呼叫次數 |
| C | `tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check` | law 領域每個補充段跑 `check_law_citations` |
| D | `tests/test_correction.py::test_retrieved_five_but_only_two_cited` | 來源過濾（只掛 used）+ 2 獨立 A→verified |

| **覆蓋的確定性路徑** | (a) domain/questions/gaps 各階段 FakeLLM 回應處理；(b) C6 confidence 不變式；(c) law citation check 觸發；(d) 補充段來源過濾 |
| **覆蓋缺口** | 真 Grok 模型輸出的 domain/questions/gaps 正確性 + pipeline 穩定性（模型品質） |

---

### 6. `tests/test_questions.py::test_generate_questions_real_grok`

| 項目 | 內容 |
|---|---|
| **排除原因** | 需要真實 grok proxy (127.0.0.1:8318)；附 `@pytest.mark.skipif(not _grok_reachable())` |
| **被驗證功能** | `note_filler.questions.generate_questions` — 從筆記文字 + domain 標籤產生問題清單 |
| **Deselected 情境** | 真 Grok + 個資料保護法文字 + law domain，驗回傳 list≥1、每題為非空白字串、不含 JSON 括號 |
| **Deselected 斷言** | `isinstance(result, list)` + `len(result) >= 1` + `all(isinstance(q, str) and q.strip())` + `not any(q.strip().startswith(("[", "{")) for q in result)` |
| **替代測試 × 2** | 見下表 |

#### 替代 A：`tests/test_questions.py::test_generate_questions_splits_multiline_string`

| 項目 | 內容 |
|---|---|
| **替代情境** | `FakeLLM` 回 3 行字串（每行一題含 `?`），驗逐行切割 |
| **替代斷言** | `isinstance(result, list)` + `all(isinstance(q, str) for q in result)` |
| | `result == ["本法的立法目的為何?", "適用範圍包含哪些對象?", "違反時的罰則規定為何?"]` |

#### 替代 B：`tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines`

| 項目 | 內容 |
|---|---|
| **替代情境** | `FakeLLM` 回含前後空白 + 空行的字串，驗 strip 與空行過濾 |
| **替代斷言** | `result == ["第一題應涵蓋什麼?", "第二題的依據為何?"]` |

| **覆蓋的確定性路徑** | (a) LLM 回應字串逐行切割；(b) 前後空白 strip；(c) 空行 drop；(d) 回傳 list 型別與元素型別 |
| **覆蓋缺口** | 真 Grok 對法律文本的問題生成品質（模型品質） |

> 額外覆蓋：同檔 `test_generate_questions_empty_response_returns_empty_list`（空回應→空 list）、
> `test_generate_questions_calls_llm_exactly_once`（呼叫次數=1）。

---

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 項目 | 內容 |
|---|---|
| **排除原因** | 需要 `GOV_AI_ENABLE_TWINKLE_MCP=1` + `TWINKLE_HUB_TOKEN` + `data/law_index.db` + Grok |
| **被驗證功能** | `note_filler.retrieve.retrieve_for_gap` — 真實 Twinkle Hub MCP + LawLookup + Grok keyword + 排序不變式 |
| **Deselected 情境** | 真 `TwinkleClient` + 真 `LawLookup` + 真 `GrokClient`，驗所有結果為 `Source`、level∈A/B、`(rank, distance)` 升序 |
| **Deselected 斷言** | `all(isinstance(s, Source))` + `all(s.level in ("A", "B"))` + `keys == sorted(keys)` |
| **替代測試 × 3** | 見下表 |

#### 替代 A：`tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B`

| 項目 | 內容 |
|---|---|
| **替代情境** | `FakeTwinkle`（Level B）+ `FakeLaw`（Level A 法條）+ `FakeLLM`（keyword JSON），law 領域 |
| **替代斷言** | `[s.level for s in out] == ["A", "A", "B", "B"]` — A 法條整批排在 B 之前 |
| | `[s.id for s in out] == ["law:A0030055:93", "law:A0030055:94", "b2", "b1"]` — 級內 distance 升序 |
| | `law.calls == [("附款", 25, "行政程序法")]` — keyword + law_name 正確傳入 |
| | `twinkle.calls[0][0] == gap.question` — twinkle query 用 gap 原文 |
| | `len(llm.calls) == 1` — LLM 呼叫恰好一次 |

#### 替代 B：`tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles`

| 項目 | 內容 |
|---|---|
| **替代情境** | 真 `LawLookup(str(LAW_DB))` + `FakeLLM`（keyword JSON），驗法條搜尋結果結構 |
| **替代斷言** | `out` 非空 + `all(s.level == "A")` + title 形如 `《行政程序法》第N條` + url 含 `pcode=` + content 非空 + id 形如 `law:<pcode>:<article_no>` + distance 0.1/0.2/... + fetched_date=今天 + 至少命中第93條 |
| **覆蓋的額外路徑** | 真 SQLite DB 查詢 → 法條原文擷取 → Source 物件構造 |

#### 替代 C：`tests/test_twinkle.py::test_search_parses_source_with_full_content`

| 項目 | 內容 |
|---|---|
| **替代情境** | monkeypatch `urlopen`，模擬 Twinkle Hub MCP JSON-RPC `tools/call` 回應（含 SSE 包裝） |
| **替代斷言** | `len(results) == 1` + `isinstance(src, Source)` |
| | `src.title == "道路交通管理處罰條例部分條文修正草案"` — metadata 映射 |
| | `src.url == "https://ly.gov.tw/bill/1120001"` — URL 映射 |
| | `src.level == "B"` — 無 source_level → 預設 B |
| | `src.doc_date == "2024-03-15"` — 日期映射 |
| | `src.fetched_date == date.today().isoformat()` — fetched 日期 |
| | `"現行條文對累犯之處罰不足" in src.content` — 全文 content 含案由 |
| | `"參酌日本立法例" in src.content` — 全文 content 含說明 |
| | `abs(src.distance - (0.6 + 0.4 * (1 - 0.82))) < 1e-9` — distance 計算公式 |

| **覆蓋的確定性路徑** | (a) Level A 法條搜尋（LawLookup）；(b) Level B Twinkle 搜尋（TwinkleClient）；(c) A 排在 B 前（排序不變式）；(d) keyword JSON 解析 + law_name 傳入；(e) SSE/JSON-RPC 協議解析；(f) Source 物件構造含全文 |
| **覆蓋缺口** | 真實 Twinkle Hub 服務 I/O + 真 Grok 關鍵字抽取品質（外部依賴品質） |

---

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 項目 | 內容 |
|---|---|
| **排除原因** | 需要 `TWINKLE_HUB_TOKEN` 環境變數 |
| **被驗證功能** | `note_filler.retrieve.twinkle.TwinkleClient.search` — 真實 Twinkle Hub MCP 搜尋 |
| **Deselected 情境** | 真 `TwinkleClient(token=token).search("道路交通管理處罰條例", n=3)`，驗回傳 list + Source 結構 |
| **Deselected 斷言** | `isinstance(results, list)` + `all(isinstance(s, Source))` + `all(s.level in ("A", "B"))` + `all(s.content.strip())` + `all(s.fetched_date == date.today().isoformat())` |
| **替代測試** | `tests/test_twinkle.py::test_search_parses_source_with_full_content` |
| **替代情境** | 同上 §7 替代 C — monkeypatch `urlopen` 模擬完整 JSON-RPC + SSE 回應 |
| **替代斷言** | 同 §7 替代 C 的 10 個斷言 |
| **覆蓋的確定性路徑** | (a) MCP initialize 握手；(b) `tools/call` 方法呼叫；(c) SSE 串流解析；(d) JSON-RPC response 解包；(e) metadata→Source 映射（title, url, level, dates, content, distance） |
| **覆蓋缺口** | 真實 Twinkle Hub 服務可用性、服務端 session 相容性、網路逾時處理 |

---

## 覆蓋缺口彙總

| 缺口類型 | 受影響 deselected 測試 | 說明 |
|---|---|---|
| **模型品質** | #1, #2, #3, #5, #6 | 真 Grok 對法律文字的分類/缺口偵測/問題生成正確性——FakeLLM 只驗結構，不驗模型品質 |
| **外部服務 I/O** | #2, #7, #8 | 真 Twinkle Hub 網路連線、MCP session、逾時——monkeypatch 只驗協議解析 |
| **TCP 連通性** | #4 | 真 proxy port 8318 連線——monkeypatch 只驗請求構造 |
| **Level A 路由穩定性** | #2 | `_assert_supplement_quality(a)` 要求真 Grok 產出的補充能觸及 Level A 法條路由——FakeLLM 可能觸發不同路由 |

> 以上缺口均為「模型品質」或「外部服務可用性」類，確定性路徑已由替代測試 fully covered。
> 這 8 個 deselected 測試的存在意義是驗證「外部依賴整合」，不影響日常 CI 的回歸保護。

---

## Guard 機制

| Guard 函式 | 驗證內容 |
|---|---|
| `test_integration_allowlist_is_stable` | 實際 deselected 集合恰好 = allowlist 中 8 個 node ID |
| `test_substitute_mapping_is_complete_and_collectable` | 所有替代測試可收集 + 實跑全部 PASS（12 個不重複 node ID） |

Guard 自身的實跑輸出見 `docs/deselected-coverage-audit-2026-07-18.md`。
