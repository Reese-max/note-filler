# 筆記補齊（Note-Filler）介面契約（最小可核實版）

## 版本

- 日期：2026-07-19
- 專案：`D:/Users/Administrator/Desktop/筆記補齊`
- 目的：把前端/路由行為以可追溯條列，避免口頭契約漂移。

## 追溯資訊

- **設計編號**: D-01
- **需求編號**: R-01（目標與一句話定義）, R-02（範圍 - MVP）, R-08（LLM 接法）, R-09（UI MVP）
- **驗收編號**: A-01（test_index_returns_upload_form）, A-02（test_run_renders_two_columns）, A-03（test_export_returns_markdown_attachment）, A-04（test_export_without_run_returns_404）, A-09（test_export_b_cannot_receive_a_result）, A-10（test_export_two_clients_each_receive_own_result）, A-11（test_export_interleaved_runs_no_last_writer_mixup）, A-12（test_export_expired_result_returns_404）, A-13（test_failed_run_creates_no_export_capability）
- **追溯狀態**: 完整
- **追溯索引**: `docs/specs/design-traceability-index.md`

## 部署模型（Issue #4）

- **支援範圍**：單機 loopback 的單人工具；不在多使用者共享 endpoint 的授權模型內。
- **隔離機制**：匯出以 `secrets.token_urlsafe(16)` 產生的不透明 result capability 綁定結果，不再是 process-global 最新文件；即使同程序被多個瀏覽器/分頁共用，未持有 capability 的一方也拿不到他人結果。
- **非認證聲明**：result ID 是能力令牌而非登入驗證；若未來部署為共享/遠端服務，仍需另行加入呼叫者認證與結果擁有者授權。
- **狀態生命週期**：結果只存於記憶體（`app.state.results`），TTL = `NOTE_FILLER_RESULT_TTL_SECONDS`（預設 3600s），容量上限 = `NOTE_FILLER_RESULT_MAX_ENTRIES`（預設 64，超出**全域**逐出最舊——共享情境下他人可間接逐出你的結果，這是單機範圍內可接受的行為）；重啟或過期一律 404，永遠不落回「最新一份文件」。
- **並發模型**：`app.state.results` 的所有讀寫都在事件迴圈執行緒（`/export/{result_id}` 為 `async def`）；`run_pipeline` 在 threadpool 執行不阻塞迴圈，且不觸碰結果容器。
- **匯出標頭**：`Cache-Control: no-store`＋`X-Content-Type-Options: nosniff`——client/proxy 快取不得超過伺服器端 TTL 生命週期。

## 1) 路由介面契約

### `GET /`（上傳頁）

- **方法 / 回傳**：`GET` → `HTMLResponse`，內容為上傳表單頁。
- **必要元件**：
  - `form action="/run" method="post" enctype="multipart/form-data"`
  - `input type="file" name="file" accept=".txt,.docx" required`
  - `button type="submit"` 上傳按鈕
- **實作錨點**：`app/templates/index.html`
- **驗證證據**：`tests/test_server.py::test_index_returns_upload_form`

### `POST /run`（產生訂正稿）

- **方法 / 輸入**：`POST`，multipart 上傳欄位 `file`（`.txt` 或 `.docx`）。
- **行為**：
  - 以暫存檔寫入上傳內容（保留副檔名）；
  - 組建 LLM/Twinkle/Law clients；
  - 呼叫 `run_pipeline(...)` 取得訂正稿；
  - 以 `secrets.token_urlsafe(16)` 產生 `result_id`，將訂正稿存入 `app.state.results[result_id]`；
  - 回傳 `result.html`（雙欄檢視，下載連結含 `result_id`）。
- **實作錨點**：`app/server.py` `run()`
- **驗證證據**：
  - `tests/test_server.py::test_run_renders_two_columns`
  - `tests/test_server.py::_fixed_doc`（測試 fixture 驗證補充/原稿路徑）

### `GET /export`（相容端點）

- **方法 / 行為**：一律回傳 `404`，訊息「尚無可匯出的訂正稿,請先上傳筆記。」；不再代表任何文件。

### `GET /export/{result_id}`（下載訂正稿）

- **方法 / 行為**：
  - `result_id` 不存在或已過 TTL：回傳 `404`，訊息「結果不存在或已過期,請重新上傳筆記。」
  - 命中有效 capability：用 `to_markdown(doc)` 產生純文字，回傳 `text/markdown; charset=utf-8`，含 `Content-Disposition: attachment; filename="correction.md"`。
- **實作錨點**：`app/server.py` `export_result()`
- **驗證證據**：
  - `tests/test_server.py::test_export_returns_markdown_attachment`
  - `tests/test_server.py::test_export_without_run_returns_404`
  - `tests/test_server.py::test_export_b_cannot_receive_a_result`
  - `tests/test_server.py::test_export_two_clients_each_receive_own_result`
  - `tests/test_server.py::test_export_interleaved_runs_no_last_writer_mixup`
  - `tests/test_server.py::test_export_expired_result_returns_404`
  - `tests/test_server.py::test_failed_run_creates_no_export_capability`

## 2) 視覺元件契約（薄弱但可核實）

### `index.html`

- `h1` 文案：`筆記補齊`
- 表單區為唯一輸入入口；不含其他互動控制元件。

### `result.html`

- 頁首：`訂正結果`
- 下載連結：`/export/{result_id}`。
- 雙欄容器：`.cols`
- 原稿欄位：`.col#original`、標題 `原稿(不可變)`。
- 訂正欄位：`.col#correction`、標題 `訂正稿`。
- 補充段落（`supplement`）以 `.supplement` 容器呈現，含 `.pending` 警示文案 `[待補依據]`；來源使用 `details.sources` 可展開清單顯示 `Level`、`title`、`url`、`fetched_date`、`doc_date`。
- **實作錨點**：`app/templates/result.html`
- **驗證證據**：
  - `tests/test_server.py::test_run_renders_two_columns`

## 3) 資料契約（欄位層）

### `app.state.results`

- 型別：`dict[result_id, {doc: CorrectionDoc, created_at: float}]`
- 使用範圍：僅在 `/run` 成功後寫入新 `result_id`、`/export/{result_id}` 讀取並判斷是否可匯出。
- 目前行為：in-memory only；TTL 與容量上限見「部署模型」；失敗的 `/run` 不產生任何 capability。
- **實作錨點**：`app/server.py`
- **驗證證據**：`tests/test_server.py::test_export_without_run_returns_404`、`test_export_expired_result_returns_404`、`test_failed_run_creates_no_export_capability`

### `Segment` / `CorrectionDoc`

- 型別與欄位：
  - `type: "original" | "supplement"`
  - `text: str`
  - `anchor_idx: int|None`
  - `sources: list`
  - `confidence: "verified" | "pending_evidence"`
  - `traceability: [{kind, id, ...}]`：逐段回指 `original_input`（含 `paragraph_idx`）、實際引用 `source` ID，或無來源補充的 `processing_record`（含問題與結果）。
- pipeline 在交付前執行逐段追溯硬閘；原稿文字／段號、實際 `sources` ID 或處理紀錄任一漂移即拒絕成功。
- **實作錨點**：`src/note_filler/correction.py`

## 4) 交付對照表（回到「對照項目」）

| 對照項目 | 設計證據 | 實作文件 |
|---|---|---|
| 上傳 + 跑 pipeline + 雙欄回傳 | `note-filler-user-flow.md`（流程） | `app/server.py`, `app/templates/index.html`, `app/templates/result.html` |
| 匯出 200 / 404 | `note-filler-interface-contract.md`（路由） | `app/server.py`, `tests/test_server.py` |
| 補充段落高亮與來源展開 | `note-filler-component-responsibilities.md`（UI 元件） | `app/templates/result.html` |

