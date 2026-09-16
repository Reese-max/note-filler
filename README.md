# 筆記補齊（Note-Filler）

法律／行政／考試筆記的**自動補齊研究工具**：讀一份筆記，找出內容缺口，研究補充素材，產出一份**可稽核**的訂正稿。

## 產品契約（安全承諾）

| 是什麼 | 不是什麼 |
|---|---|
| 一個「研究層」補充工具：產生**有來源標註**的補充段落，放在原稿旁供人工查核 | 自動改寫你筆記正文的工具 |
| 每段補充都帶追溯欄位：實際引用的來源 ID、法條等級、信心標記 | 無來源聲稱可以進入正文的產品 |
| 原稿**不可不可變**：產出的訂正稿永遠以「原稿欄 + 訂正欄」呈現，原稿逐段對應原始輸入 | 會覆寫或刪除你檔案的工具 |

**核心規則：無來源的聲稱不進訂正稿正文。** 補充段有兩種信心狀態：

- `verified`：段落引用的 `[ ^n ]` 來源經過交叉驗證（`cross_validate`），法規領域再經過本地法條庫核對。
- `pending_evidence`：來源不足或寫作/檢核流程中斷，以 `[待補依據]` 高亮呈現，**不偽裝成已核實內容**。

## 資料流向：哪些檔案是生成物、哪些是權威

| 路徑 | 性質 |
|---|---|
| 上傳的 `.txt`/`.docx` 筆記 | **權威輸入**——原稿，永不覆寫 |
| `data/law_index.db` | **權威參考**——本地法條索引（Level A 來源） |
| `output/<run>/` | **生成物**——每次 run 的訂正稿、稽核摘要、metric 記錄；可重新產生 |
| `metrics_output/` | **生成物**——聚合 KPI/品質報表 |
| `app.state.results`（記憶體） | **暫存**——`/run` 產生的結果以不透明 `result_id` capability 綁定，TTL 預設 3600s（`NOTE_FILLER_RESULT_TTL_SECONDS`），上限 64 筆（`NOTE_FILLER_RESULT_MAX_ENTRIES`）；重啟即清空，過期一律 404 |

## 追溯欄位：怎麼看一段補充的證據

每個 `Segment` 攜帶：

- `confidence`: `verified | pending_evidence`
- `traceability`: 逐段回指 `original_input`（原稿段號）、實際引用 `source` ID，或無來源補充的 `processing_record`
- `sources`: 每筆來源含 `Level`（A=法條庫、B=檢索、C=弱證）、`title`、`url`、`fetched_date`、`doc_date`
- `functional_gap` / `user_value` / `related_knowledge` / `argument_id`：缺口分類、使用者價值、延伸閱讀、論點結構

網頁介面中，來源以 `details.sources` 展開呈現；Markdown 匯出含腳註式引用。

## 原稿保護與回復

- 上傳內容寫入**暫存檔**（`tempfile.NamedTemporaryFile`），`finally` 區塊保證刪除——不碰你的原檔。
- `/run` 失敗時**不產生任何 result capability**；無法把上一份成功結果當成失敗請求的產出。
- 「回復」= 原稿就是權威；`output/` 下的所有產出都可丟棄重跑。

## 匯出隔離（Issue #4）

`GET /export/{result_id}` 使用 `secrets.token_urlsafe(16)` 產生的不透明 capability。**不支援共享部署**——這是單機 loopback 工具；capability 保證的是「同程序多個瀏覽器分頁互不串檔」，不是登入驗證。若未來要部署為共享服務，需另行加入呼叫者認證。

## Provider 邊界（無 secrets 落盤）

| Provider | 用途 | 端點/憑證 |
|---|---|---|
| `GrokClient` | LLM 研究/寫作 | 預設 `http://127.0.0.1:8318/v1`（本地代理） |
| `TwinkleClient` | 網頁檢索補充 | `TWINKLE_HUB_TOKEN` 環境變數；缺省時降級為空結果，法條 Level A 仍可用 |
| `LawLookup` | 法條查證 | 本地 `data/law_index.db`（`NOTE_FILLER_DB` 可覆寫）——**離線可用** |

上傳內容與結果本文**不進一般日誌**：web 層只記檔名＋例外摘要＋traceback；pipeline 稽核事件以 `segment#N`、`argument_id`、來源 ID 等非內容識別碼關聯（法條查核的 finding detail 為法條名，非筆記本文）。已知殘留：`gap.question`（LLM 由筆記衍生的問題字串）仍作為部分 audit 事件的 `data_id` 關聯鍵——為衍生內容非原文，未來若要嚴格零內容可再替換為雜湊。

## 快速開始

```bash
# 安裝（含開發依賴）
pip install -e ".[dev]"

# 網頁介面
uvicorn app.server:app --port 8000
# 開啟 http://127.0.0.1:8000 → 上傳 .txt/.docx → 雙欄檢視 → 下載 Markdown

# CLI
python -m note_filler 筆記.txt -o output/
python -m note_filler 筆記資料夾/ --format md

# 測試（單元層，provider 全部 stub）
python -m pytest tests/ -q
# 整合測試（需真實 LLM/Twinkle 憑證）
python -m pytest tests/test_integration_main.py -q
```

## 最小端到端範例

```
原稿 note.txt:「行政處分是行政機關之單方行為，具有(   )。律師費約$5萬。」
        │
        ▼
detect_domain → "law" → 產生補齊問題 → detect_gaps 標出 (   ) 缺口
        │
        ▼
每個 gap → LawLookup 查法條(Level A) + Twinkle 檢索(Level B/C)
        → write_supplement 產出帶 [^1] 引用的補充段
        → cross_validate 驗證實際引用的來源
        │
        ▼
assemble → law 領域法條核對 → 硬閘檢查(非空+可追溯)
        │
        ▼
訂正稿：原稿欄(不可變) | 訂正欄
   補充段 [verified]「…依行政程序法第 92 條…[^1]」
   或 [pending_evidence]「[待補依據] 來源不足」
```

使用者審閱流程：看 `[待補依據]` 高亮 → 展開 `details.sources` 查證據 → 下載 Markdown。

## 文件索引

- 介面契約（路由/資料欄位/驗收）：`docs/specs/note-filler-interface-contract.md`
- 設計追溯：`docs/specs/design-traceability-index.md`
- 50-persona 稽核：`docs/audits/`
