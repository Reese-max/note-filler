# 筆記補齊（Note-Filler）

法律／行政／考試筆記的**自動補齊研究工具**：讀一份筆記，找出內容缺口，研究補充素材，產出一份**可稽核**的訂正稿。

## 產品契約（安全承諾）

| 是什麼 | 不是什麼 |
|---|---|
| 一個「研究層」補充工具：產生**有來源標註**的補充段落，放在原稿旁供人工查核 | 自動改寫你筆記正文的工具 |
| 每段補充都帶追溯欄位：實際引用的來源 ID、法條等級、信心標記 | 無來源聲稱可以進入正文的產品 |
| 原稿**不可變**：產出的訂正稿保留原稿段落，網頁以「原稿欄 + 訂正欄」並排呈現 | 會覆寫或刪除你檔案的工具 |

**核心規則：無來源的聲稱不進訂正稿正文。** 補充段有兩種信心狀態：

- `verified`：段落引用的 `[^n]` 來源通過程式的交叉驗證規則（`cross_validate`），法規領域再經過本地法條庫核對。
- `pending_evidence`：來源不足或寫作/檢核流程中斷，以 `[待補依據]` 高亮呈現，**不偽裝成已核實內容**。

這是系統證據狀態，並非人工核准或法律正確性保證。訂正稿是供審查的生成物，可能含明確標示的待補證段落；正式採用前仍須逐項核對來源、適用日期與管轄區。主分支尚未提供 Issue #3 的持久化逐主張人工決策／accepted-only 匯出工作流。

## 資料流向：哪些檔案是生成物、哪些是權威

| 路徑 | 性質 |
|---|---|
| 上傳的 `.txt`/`.docx` 筆記 | **權威輸入**——原稿，永不覆寫 |
| `data/law_index.db` | **參考快照**——本地法條索引（Level A 來源）；仍須核對官方原文及現行版本 |
| CLI `--outdir` 指定的資料夾（範例 `output/`） | **生成物**——訂正稿、binding report 與 manifest；未指定時寫在輸入檔旁。多檔 sidecar 以各輸入身份隔離，可重新產生 |
| `metrics_output/` | **生成物**——聚合 KPI/品質報表 |
| `app.state.results`（記憶體） | **暫存**——`/run` 產生的結果以不透明 `result_id` capability 綁定，TTL 預設 3600s（`NOTE_FILLER_RESULT_TTL_SECONDS`），上限 64 筆（`NOTE_FILLER_RESULT_MAX_ENTRIES`）；兩個設定都必須為正值，TTL 也必須為有限數；重啟即清空，過期一律 404 |

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

`GET /export/{result_id}` 使用 `secrets.token_urlsafe(16)` 產生的不透明 capability。**不支援共享部署**——這是單機 loopback、單一 Worker 程序的工具；capability 保證的是「同程序多個瀏覽器分頁互不串檔」，不是登入驗證。若未來要部署為共享服務，需另行加入呼叫者認證、結果擁有者授權與跨 Worker 的結果儲存。

## Provider 邊界（無 secrets 落盤）

| Provider | 用途 | 端點/憑證 |
|---|---|---|
| `GrokClient` | LLM 研究/寫作 | 預設 `http://127.0.0.1:8318/v1`（本地代理） |
| `TwinkleClient` | 網頁檢索補充 | `TWINKLE_HUB_TOKEN` 環境變數；缺省時降級為空結果，法條 Level A 仍可用 |
| `LawLookup` | 法條查證 | 本地 `data/law_index.db`（CLI 用 `--db`；網頁用 `NOTE_FILLER_DB`）——查庫可離線，完整研究流程仍需 LLM |

web `/run` 失敗紀錄只記固定事件識別碼與例外型別，不記上傳本文、結果、例外訊息或 traceback；錯誤頁也不回顯例外訊息。網頁請求執行 pipeline 或格式化匯出時，普通日誌紀錄（含稽核事件與 exception traceback）會以固定診斷標記遮蔽，以免把原稿或產出的訂正內容寫進日誌；CLI 執行不受這個網頁專用遮蔽影響。網頁回應和下載仍包含使用者的內容，請保護應用程式與其下載連結。

## 快速開始

```bash
# 安裝（含開發依賴）
pip install -e ".[dev]"
# 網頁伺服器是額外依賴
pip install uvicorn

# 唯讀確認 CLI 契約，不呼叫 provider、不建立輸出
python -m note_filler --help

# 網頁介面
uvicorn app.server:app --host 127.0.0.1 --port 8000
# 開啟 http://127.0.0.1:8000 → 上傳 .txt/.docx → 雙欄檢視 → 下載 Markdown

# CLI
python -m note_filler 筆記.txt -o output/
python -m note_filler 筆記資料夾/ --format md

# 測試（單元層，provider 全部 stub）
python -m pytest tests/ -q
# 整合測試（需真實 LLM/Twinkle 憑證）
python -m pytest tests/test_integration_main.py -q -m integration
```

離線測試預設排除 `integration` 標記；整合測試需明確選取，GitHub CI 的 provider 整合亦受手動觸發政策限制。一般 CLI 會執行研究並建立輸出，不提供 `--dry-run` 選項；首次使用先以 `--help` 與離線測試確認環境，再用不含私人資料的測試筆記和獨立輸出資料夾。

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

使用者審閱流程：看 `[待補依據]` 高亮 → 展開 `details.sources` 查來源原文與日期 → 下載供審查的 Markdown → 人工將支持充分且適用的補充另存為正式採用稿，保留原稿及訂正稿以便回溯。下載與 `verified` 都不代表人工接受；待補證主張不得直接當作正式結論。

## 文件索引

- 介面契約（路由/資料欄位/驗收）：`docs/specs/note-filler-interface-contract.md`
- 設計追溯：`docs/specs/design-traceability-index.md`
- 50-persona 稽核：`docs/audits/`
