# 筆記補齊（Note-Filler）介面契約（最小可核實版）

## 版本

- 日期：2026-07-19（2026-09-30 修訂：`/export` 改為 per-result capability，移除 process-global `last_doc`）
- 專案：`D:/Users/Administrator/Desktop/筆記補齊`
- 目的：把前端/路由行為以可追溯條列，避免口頭契約漂移。

## 追溯資訊

- **設計編號**: D-01
- **需求編號**: R-01（目標與一句話定義）, R-02（範圍 - MVP）, R-08（LLM 接法）, R-09（UI MVP）
- **驗收編號**: A-01（test_index_returns_upload_form）, A-02（test_run_renders_two_columns）, A-03（test_export_returns_markdown_attachment）, A-04（test_export_without_run_returns_404）
- **追溯狀態**: 完整
- **追溯索引**: `docs/specs/design-traceability-index.md`

## 1) 路由介面契約

### `GET /`（上傳頁）

- **方法 / 回傳**：`GET` → `HTMLResponse`，內容為上傳表單頁；若請求未帶 `nf_session` cookie 則順帶簽發（`HttpOnly`, `SameSite=Lax`），讓後續 `/run` 沿用同一 session。
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
  - 若請求未帶 `nf_session` cookie：以 `secrets.token_urlsafe(32)` 建立 session id，回應帶 `Set-Cookie`（`HttpOnly`, `SameSite=Lax`）；
  - 先 `discard_owner(session)` 清掉本 session 舊結果（本次失敗時不得讓舊稿被當成本次產物匯出，且不影響其他 client）；
  - 組建 LLM/Twinkle/Law clients；
  - 呼叫 `run_pipeline(...)` 取得訂正稿；
  - 以 `secrets.token_urlsafe(24)` 產生 `result_id`，把訂正稿以 `{doc, owner=session, expires_at}` 存入 `app.state.results`；
  - 回傳 `result.html`（雙欄檢視），下載連結為 `/export/{result_id}`。
- **實作錨點**：`app/server.py` `run()`、`app/result_store.py`
- **驗證證據**：
  - `tests/test_server.py::test_run_renders_two_columns`
  - `tests/test_server.py::_fixed_doc`（測試 fixture 驗證補充/原稿路徑）

### `GET /export`（無結果身分）

- **方法 / 行為**：一律回 `404`，訊息「匯出需使用本次訂正結果頁提供的下載連結。」——不存在全域「最新一份」可匯出。
- **實作錨點**：`app/server.py` `export()`
- **驗證證據**：`tests/test_server.py::test_export_without_run_returns_404`

### `GET /export/{result_id}`（下載指定訂正稿）

- **方法 / 行為**：以 `result_id` 與呼叫端 `nf_session` cookie 雙重比對：
  - 查無此 `result_id`，或 `result_id` 屬於其他 session（含未帶 cookie）：回 `404`，不洩漏存在性；
  - 已過期：回 `410`，訊息「該訂正稿已過期,請重新上傳筆記。」；
  - 通過：`to_markdown(doc)` 產生純文字，回傳 `text/markdown; charset=utf-8`，含 `Content-Disposition: attachment; filename="correction.md"`。
- **實作錨點**：`app/server.py` `export_result()`
- **驗證證據**：
  - `tests/test_server.py::test_export_returns_markdown_attachment`
  - `tests/test_server.py::test_export_without_run_returns_404`
  - `tests/test_server.py::test_two_clients_export_only_own_result`
  - `tests/test_server.py::test_other_client_cannot_export_after_only_first_ran`
  - `tests/test_server.py::test_concurrent_runs_do_not_mix_results`
  - `tests/test_server.py::test_expired_result_returns_410`
  - `tests/test_server.py::test_restarted_result_store_returns_404`

## 2) 視覺元件契約（薄弱但可核實）

### `index.html`

- `h1` 文案：`筆記補齊`
- 表單區為唯一輸入入口；不含其他互動控制元件。

### `result.html`

- 頁首：`訂正結果`
- 下載連結：`{{ export_url }}`（即 `/export/{result_id}`，僅本次 run 的結果）。
- 雙欄容器：`.cols`
- 原稿欄位：`.col#original`、標題 `原稿(不可變)`。
- 訂正欄位：`.col#correction`、標題 `訂正稿`。
- 補充段落（`supplement`）以 `.supplement` 容器呈現，含 `.pending` 警示文案 `[待補依據]`；來源使用 `details.sources` 可展開清單顯示 `Level`、`title`、`url`、`fetched_date`、`doc_date`。
- **實作錨點**：`app/templates/result.html`
- **驗證證據**：
  - `tests/test_server.py::test_run_renders_two_columns`

## 3) 資料契約（欄位層）

### `app.state.results`（`ResultStore`）

- 型別：`dict[result_id] -> {doc: CorrectionDoc, owner: str, expires_at: float}`；`result_id` 為 `secrets.token_urlsafe(24)`，`owner` 為呼叫端 `nf_session` session id。
- 使用範圍：僅在 `/run` 成功後 `put()`、`GET /export/{result_id}` 以 `get(result_id, session)` 判讀；`POST /run` 開始時 `discard_owner(session)` 清掉本 session 舊結果。
- TTL：`NOTE_FILLER_RESULT_TTL_SECONDS`（預設 3600 秒，monotonic clock）；過期回 `410` 並刪除。
- 容量：上限 64 筆，超出時逐出最快到期者；每次寫入先清掉已過期項目。
- 生命週期：in-memory，process 重啟即清空，舊 `result_id` 一律 `404`，永不回退到其他文件。
- **實作錨點**：`app/result_store.py`、`app/server.py`
- **驗證證據**：`tests/test_server.py::test_expired_result_returns_410`、`tests/test_server.py::test_restarted_result_store_returns_404`

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

## 4) 部署模型與隔離邊界

- **支援部署型態：單機 loopback、單使用者。** 本工具設計為本機 `127.0.0.1` 上跑的個人工具,不提供多用戶共享部署。
- **隔離機制（能力模型,非登入認證）**：每份結果同時要求 (a) `secrets.token_urlsafe(24)` 產生的 unguessable `result_id`（出現在結果頁的下載連結中,伺服器不主動揭露）與 (b) 呼叫端 `nf_session` cookie 與結果 owner 相符;任一不符即 `404`。`nf_session` 為 `HttpOnly + SameSite=Lax` 的 256-bit 隨機值,於 `GET /` 首次請求簽發（若 client 直接呼叫 `/run` 而未經首頁,則於 `/run` 補發）。
- **失敗與重啟**：失敗的 `/run` 不產生 capability 且先清掉本 session 舊結果;process 重啟後 in-memory 結果全失,舊 `result_id` 確定性 `404`;TTL 過期確定性 `410`。任何路徑都不存在「回退到最新一份文件」。
- **共用/遠端部署（不支援）**：若未來要把本服務暴露給多使用者或網路共享,必須另外加入呼叫端驗證（authentication）與結果擁有者授權檢查——目前的 `nf_session` 只是 per-browser 能力綁定,不是帳號身分,不得以它當作共享部署的授權控制。
- **日誌**：成功路徑不記錄上傳筆記內文或訂正稿內容（`tests/test_server.py::test_uploaded_note_and_result_body_not_logged`）；失敗路徑僅記錄檔名、錯誤型別與訊息。

## 5) 交付對照表（回到「對照項目」）

| 對照項目 | 設計證據 | 實作文件 |
|---|---|---|
| 上傳 + 跑 pipeline + 雙欄回傳 | `note-filler-user-flow.md`（流程） | `app/server.py`, `app/templates/index.html`, `app/templates/result.html` |
| 匯出 200 / 404 | `note-filler-interface-contract.md`（路由） | `app/server.py`, `tests/test_server.py` |
| 補充段落高亮與來源展開 | `note-filler-component-responsibilities.md`（UI 元件） | `app/templates/result.html` |

