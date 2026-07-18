# 8 個預設未執行測試盤點

日期：2026-07-18

## 結論

目前 `pyproject.toml:32` 的預設 `addopts` 使用 `-m 'not integration'`，因此整合測試在 collection 階段被排除，不是測試失敗。現行 collection 結果為 117 個測試，其中 109 個選取、8 個排除；8 個 node ID 與 `tests/deselected_allowlist.json` 一致，全部判定為 `acceptable_unexecuted`。

本次盤點只執行離線回歸、collection 與 guard，沒有因為盤點而啟動或執行真實外部整合測試。每項的「未覆蓋」主要是：真 Grok 的語意品質、真 Twinkle Hub 的網路 I/O，以及外部資料／服務漂移；原稿不可變、`pending_evidence`、只掛實際引用來源、法條離線查核等品質閘已有離線替代測試保護。

本次逐一核對 8 個 integration 測試函式本體及其呼叫的 repo 實作：7 項直接使用 Grok（#1、#2、#3、#4、#5、#6、#7），3 項使用 Twinkle Hub（#2、#7、#8），2 項使用 `data/law_index.db`（#2、#7）。各項下方分別記錄測試情境、實際依賴、離線替代與失敗所代表的風險；不把替代測試的通過誤稱為真服務已驗證。

## 關聯需求基線

需求規格 `docs/specs/2026-07-15-note-filler-design.md` 定義了：

- 流程為領域判定、研究問題生成、Gap 偵測、分領域檢索、交叉驗證、引用強制及訂正稿組裝（第 58–63 行）。
- Gap 偵測要依研究問題與筆記全文判定 `covered`、`partial`、`missing`，只有後兩者進補充佇列（第 70–73 行）。
- 品質閘包括無來源降為 `pending_evidence`、優先 A/B 一手來源、來源數量、原稿 immutable、來源日期及來源分級（第 94–101 行）。
- 研究層使用 `http://127.0.0.1:8318/v1` 的 `grok-4.3`（第 105 行）。
- MVP 驗收要求補充來源、原文不變、法條引用查核及端到端自動測試（第 133–139 行）。

## 逐項盤點

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

- **覆蓋功能**：`tests/test_domain.py:52–61` 真呼叫 `GrokClient`，將明確的刑法文字送入 `note_filler.domain.detect_domain`，要求模型分類為 `law`。對應需求流程的領域判定（規格第 58 行）。
- **風險**：真 `grok-4.3` 對法律文字的語意分類錯誤，會把後續研究問題與檢索路由導向 `admin`、`exam` 或 `other`。FakeLLM 測試只證明標籤解析、大小寫、標點及 fallback 契約，不證明模型理解品質。
- **跳過條件**：預設因 `@pytest.mark.integration`（第 50 行）被 `-m 'not integration'` 排除；選擇整合測試執行時，`@pytest.mark.skipif(not _grok_reachable())`（第 51 行）會在 `127.0.0.1:8318` TCP 不可達時略過。
- **依賴環境**：目前 repo 的 Python 3.11+ venv、pytest 與專案套件；Grok proxy `127.0.0.1:8318`；`GrokClient` 預設 endpoint/model 為 `http://127.0.0.1:8318/v1`／`grok-4.3`（`src/note_filler/llm.py:17–18`）。不直接依賴 Twinkle token 或 `data/law_index.db`。
- **離線替代**：`tests/test_domain.py::test_detect_domain_law`；本次 guard 映射測試通過。

### 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

- **覆蓋功能**：`tests/test_e2e_acceptance.py:208–262` 以真 Grok、真 Twinkle Hub、真 `LawLookup` 執行 parse→domain→questions→gaps→retrieve→write→assemble，並檢查原稿 immutable、無來源閘、法條引用、Markdown 格式、Level A 路由、非原始記錄倒出及註腳品質。這是對應規格第 12 節 MVP 驗收的複合 smoke test。
- **風險**：同時承擔真模型輸出品質、Twinkle Hub MCP I/O、法規索引內容及網路服務漂移；模型是否產生 `[^n]` 註腳及 Level A 來源具有不穩定性，測試在初次執行後最多再重跑 5 次尋找 Level A 路徑（第 238–243 行，總計最多 6 次），因此結果可能受外部服務與資料狀態影響。離線替代不能證明真模型的 gap／寫作品質或真 Twinkle 服務相容性。
- **跳過條件**：預設因第 208 行 integration marker 被排除；選擇執行時，`data/law_index.db` 不存在（第 211–212 行）、Grok proxy 不可達，或 `TWINKLE_HUB_TOKEN` 未設定（第 42、215–217 行）任一條件成立即 `pytest.skip`。
- **依賴環境**：`tests/fixtures/real_note.txt`、可讀的 `data/law_index.db`、Grok proxy `127.0.0.1:8318`／`grok-4.3`、有效 `TWINKLE_HUB_TOKEN`、可連線的 Twinkle Hub `https://api.twinkleai.tw/mcp/`（`src/note_filler/retrieve/twinkle.py:20、202`）。現行測試碼沒有檢查 `GOV_AI_ENABLE_TWINKLE_MCP`。
- **離線替代**：`test_e2e_structural_invariants`、`test_e2e_offline_supplement_quality_boundary`、3 個 pipeline 回歸，以及 `test_retrieved_five_but_only_two_cited`；本次 6 個映射均通過。

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`

- **覆蓋功能**：`tests/test_gap.py:73–91` 以真 Grok 判定一段行政法筆記對兩個研究問題的涵蓋程度，要求回傳 `list[Gap]`、只含 `partial`／`missing`，且明顯未涵蓋的「裁量基準／罰鍰」問題出現在結果。對應規格 Gap 偵測（第 70–73 行）。
- **風險**：模型可能把 `covered`、`partial`、`missing` 判錯，或漏掉真正缺口；這是語意品質風險，不是 JSON 解析、圍欄剝除、一次呼叫及保守 fallback 的程式契約風險。
- **跳過條件**：預設因第 71 行 integration marker 排除；選擇執行時，`@pytest.mark.skipif(not _grok_reachable())`（第 72 行）在 `127.0.0.1:8318` 不可達時略過。
- **依賴環境**：Python venv、pytest、Grok proxy `127.0.0.1:8318`／`grok-4.3`。不直接依賴 Twinkle token 或法規資料庫。
- **離線替代**：`tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing` 及同檔的解析失敗、非陣列、code fence、空問題邊界測試；本次 guard 映射測試通過。

### 4. `tests/test_llm.py::test_grok_pong_integration`

- **覆蓋功能**：`tests/test_llm.py:68–73` 對本機 Grok proxy 發送真實 chat completion，要求回應包含 `PONG`；驗證實際 TCP、HTTP endpoint、服務可用性及回應能被 `GrokClient.complete` 解析。對應規格研究層 Grok 接法（第 105 行）。
- **風險**：proxy 未啟動、endpoint／model 不相容、回應 schema 漂移或服務逾時會使整個 LLM 路徑失效。它不是完整模型品質測試；`PONG` 也只是一個連通性 smoke assertion。
- **跳過條件**：預設因第 66 行 integration marker 排除；選擇執行時，`@pytest.mark.skipif(not _grok_reachable())`（第 67 行）在 TCP port 不可達時略過。port 開啟但 HTTP 回應錯誤時不會 skip，而會失敗。
- **依賴環境**：Python venv、Grok proxy `127.0.0.1:8318`、`grok-4.3` 及可用的 OpenAI 相容 `/v1/chat/completions`；不依賴 Twinkle token 或法規資料庫。
- **離線替代**：`tests/test_llm.py::test_grokclient_builds_request_body` 以 monkeypatch 鎖定 POST、Bearer、JSON body、timeout 及 response parse；本次 guard 映射測試通過。

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

- **覆蓋功能**：`tests/test_pipeline.py:153–168` 以真 Grok 執行 `run_pipeline` 的 domain→questions→gaps→assemble 主路徑；Twinkle 與 LawLookup 使用 fake，並檢查文件存在、segments 為 list，以及無來源補充必須是 `pending_evidence`。對應規格流程（第 58–63 行）及無來源品質閘（第 94 行）。
- **風險**：真模型的 domain、問題清單、gap JSON 或 writer 輸出畸形時，pipeline 可能中斷或路由偏移。此測試沒有要求一定產生 gap／補充，也沒有真實檢索，因此「不炸」不等於真模型端到端品質通過；真正的 Twinkle、法條 DB 與服務 I/O 不在覆蓋範圍。
- **跳過條件**：預設因第 151 行 integration marker 排除；選擇執行時，`@pytest.mark.skipif(not _grok_reachable())`（第 152 行）在 Grok proxy 不可達時略過。
- **依賴環境**：Python venv、`python-docx`（`note_path` fixture 在第 18–25 行建立 `.docx`）、Grok proxy `127.0.0.1:8318`／`grok-4.3`。使用 `FakeTwinkle`／`FakeLaw`，不需 Twinkle token、外部 Twinkle 網路或 `data/law_index.db`。
- **離線替代**：`test_run_pipeline_invariant`、`test_run_pipeline_malformed_gap_output_falls_back_to_pending`、`test_run_pipeline_law_domain_runs_citation_check`、`test_retrieved_five_but_only_two_cited`；本次 4 個映射均通過。

### 6. `tests/test_questions.py::test_generate_questions_real_grok`

- **覆蓋功能**：`tests/test_questions.py:64–79` 以真 Grok 從個資法筆記生成研究問題，檢查輸出為非空 `list[str]`、每題非空，且沒有殘留 JSON 括號。對應規格研究問題生成（第 59 行）及問題必須緊扣筆記概念的需求約束。
- **風險**：真模型可能產生無關、不可查證、偏離筆記概念或法律上不適當的問題，進而污染後續 Gap 偵測與檢索。FakeLLM 替代只驗換行切割、strip、空行移除與一次呼叫，不驗問題語意品質。
- **跳過條件**：預設因第 62 行 integration marker 排除；選擇執行時，`@pytest.mark.skipif(not _grok_reachable())`（第 63 行）在 Grok proxy 不可達時略過。
- **依賴環境**：Python venv、Grok proxy `127.0.0.1:8318`／`grok-4.3`；不依賴 Twinkle token 或法規資料庫。
- **離線替代**：`test_generate_questions_splits_multiline_string`、`test_generate_questions_strips_and_drops_blank_lines` 及同檔空回應／呼叫次數測試；本次 guard 映射測試通過。

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

- **覆蓋功能**：`tests/test_retrieve.py:105–125` 以真 Grok 產生 law keyword、以真 `LawLookup` 查 Level A 法條、以真 Twinkle Hub 查 Level B 來源，最後驗 `Source` 型別、級別為 A/B，以及 `(level rank, distance)` 排序。對應規格分領域檢索、交叉驗證及來源分級／優先一手源（第 61–62、94–101 行）。
- **風險**：真 Grok keyword 抽取錯誤、法規索引沒有命中、Twinkle Hub MCP／網路失敗或來源資料漂移，都可能使檢索結果不完整。現有斷言沒有要求 `out` 非空；`all(...)` 與排序檢查對空清單會通過，所以空結果可能造成假綠，不能單獨證明真的取得 A/B 來源。
- **跳過條件**：預設因第 102 行 integration marker 排除；選擇執行時，法規 DB 不存在（第 103 行）、Grok proxy 不可達（第 104 行），或 `TWINKLE_HUB_TOKEN` 未設定（第 106–108 行）會略過。
- **依賴環境**：可讀的 `data/law_index.db`、Grok proxy `127.0.0.1:8318`／`grok-4.3`、有效 `TWINKLE_HUB_TOKEN`、可連線的 `https://api.twinkleai.tw/mcp/`。現行 `tests/test_retrieve.py` 沒有檢查 `GOV_AI_ENABLE_TWINKLE_MCP`；雖然舊報告與 `docs/testing-guide.md:60` 將它列為環境項目，不能當成目前測試碼的實際 skip 條件。
- **離線替代**：LawLookup Level A、mock MCP/SSE 全文與 metadata、MCP session、transport failure，以及 FakeLaw/FakeTwinkle 排序測試；本次 5 個映射均通過。

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

- **覆蓋功能**：`tests/test_twinkle.py:123–135` 以有效 token 呼叫真 `TwinkleClient.search`，檢查回傳清單中的物件是 `Source`、級別為 A/B、全文非空且 `fetched_date` 為當日。對應規格的官方來源檢索、來源分級與日期欄位（第 61、100–101 行）。
- **風險**：真 Twinkle Hub 的可用性、MCP session 相容性、SSE／JSON-RPC 回應格式及網路逾時仍未被離線測試證明。現有測試只要求 `results` 是 list，對空結果不會失敗；因此 token 存在但服務降級為空結果時可能假綠。
- **跳過條件**：預設因第 122 行 integration marker 排除；選擇執行時，`TWINKLE_HUB_TOKEN` 未設定或為空（第 126–128 行）即 `pytest.skip`。Twinkle 網路／協定錯誤則由 `TwinkleClient.search` 的外部服務降級行為處理，未必轉成測試 skip。
- **依賴環境**：Python venv、有效 `TWINKLE_HUB_TOKEN`、可連線的 `https://api.twinkleai.tw/mcp/`；不直接依賴 Grok proxy 或 `data/law_index.db`。`TwinkleClient` 預設 URL 與 token 後援見 `src/note_filler/retrieve/twinkle.py:20、202–207`。
- **離線替代**：mock MCP/SSE 全文與 Source metadata、session header 重用、transport failure 空結果；本次 3 個映射均通過。

## 依賴環境總表

| 依賴 | 需要的測試 | 現行碼中的用途 |
|---|---|---|
| Python 3.11+ venv、pytest 與專案依賴 | 全部 8 項 | 收集／執行測試與載入 repo 程式碼；本次固定使用指定 venv |
| Grok proxy `127.0.0.1:8318`、`grok-4.3` | #1、#2、#3、#4、#5、#6、#7 | 真 LLM 呼叫；測試以 TCP 探測作 runtime skip，實際 client endpoint 為 `/v1/chat/completions` |
| `TWINKLE_HUB_TOKEN` | #2、#7、#8 | 真 Twinkle Hub 驗證與搜尋授權 |
| Twinkle Hub 網路 `https://api.twinkleai.tw/mcp/` | #2、#7、#8 | 真 MCP initialize／tools/call／來源轉換 |
| `data/law_index.db` | #2、#7 | LawLookup Level A 查詢與法條引用查核 |
| `tests/fixtures/real_note.txt` | #2 | 真端到端輸入筆記 |
| `python-docx` | #5 | fixture 建立暫存 `.docx`；#2 的 fixture 是 `.txt` |
| `GOV_AI_ENABLE_TWINKLE_MCP=1` | **現行 8 項測試碼未實際讀取** | 舊文件仍列為操作前提，但 `src/note_filler/retrieve/twinkle.py` 已移除 opt-in env 閘；目前不可列為 #7 的實際 skip 條件 |

本次環境探測只檢查是否存在／可達，不輸出 token 值：

```text
grok_proxy_tcp_8318=True
law_index_db_exists=True
twinkle_token_present=True
twinkle_flag_is_1=False
```

`twinkle_flag_is_1=False` 不影響本次預設 collection，因為 8 項先被 integration marker 排除；它也證實不能把舊文件中的 flag 描述直接當成現行 `test_retrieve` 的程式行為。

## 可重現驗證

使用目前工作樹的指定 venv 執行：

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest --collect-only -q --deselected-details
109/117 tests collected (8 deselected)

D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest --collect-only -q -o addopts= -m integration
8/117 tests collected (109 deselected)

D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -q
109 passed, 8 deselected in 4.42s

D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_deselection_guard.py -q -s
DESELECTED_AUDIT=8 MAPPED_TESTS=16
TARGETED_VERIFICATION=PASS
3 passed in 3.82s
```

## 最終判讀

8 項全部屬於「預設不執行、具明確 integration 邊界」；不是應被偷偷納入日常回歸的單元測試。離線替代映射共 16 項且已通過，足以保護目前可確定的程式契約與品質閘。仍保留的驗證缺口是外部模型語意、外部 MCP I/O，以及 #7／#8 空結果斷言不足造成的假綠風險；若要把這些風險納入自動回歸，應另行提供穩定的外部服務與明確的非空結果契約。
