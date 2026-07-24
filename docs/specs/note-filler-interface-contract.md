# 筆記補齊（Note-Filler）介面契約（最小可核實版）

## 版本

- 日期：2026-07-19
- 專案：`D:/Users/Administrator/Desktop/筆記補齊`
- 目的：把前端/路由行為以可追溯條列，避免口頭契約漂移。

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
  - 將訂正稿存到 `app.state.last_doc`；
  - 回傳 `result.html`（雙欄檢視）。
- **實作錨點**：`app/server.py` `run()`
- **驗證證據**：
  - `tests/test_server.py::test_run_renders_two_columns`
  - `tests/test_server.py::_fixed_doc`（測試 fixture 驗證補充/原稿路徑）

### `GET /export`（下載訂正稿）

- **方法 / 行為**：
  - 若 `app.state.last_doc is None`：回傳 `404`，訊息「尚無可匯出的訂正稿,請先上傳筆記。」
  - 若存在 last_doc：用 `to_markdown(doc)` 產生純文字，回傳 `text/markdown; charset=utf-8`，含 `Content-Disposition: attachment; filename="correction.md"`。
- **實作錨點**：`app/server.py` `export()`
- **驗證證據**：
  - `tests/test_server.py::test_export_returns_markdown_attachment`
  - `tests/test_server.py::test_export_without_run_returns_404`

## 2) 視覺元件契約（薄弱但可核實）

### `index.html`

- `h1` 文案：`筆記補齊`
- 表單區為唯一輸入入口；不含其他互動控制元件。

### `result.html`

- 頁首：`訂正結果`
- 下載連結：`/export`。
- 雙欄容器：`.cols`
- 原稿欄位：`.col#original`、標題 `原稿(不可變)`。
- 訂正欄位：`.col#correction`、標題 `訂正稿`。
- 補充段落（`supplement`）以 `.supplement` 容器呈現，含 `.pending` 警示文案 `[待補依據]`；來源使用 `details.sources` 可展開清單顯示 `Level`、`title`、`url`、`fetched_date`、`doc_date`。
- **實作錨點**：`app/templates/result.html`
- **驗證證據**：
  - `tests/test_server.py::test_run_renders_two_columns`

## 3) 資料契約（欄位層）

### `app.state.last_doc`

- 型別：`CorrectionDoc`
- 使用範圍：僅在 `/run` 成功後設值、`/export` 讀取並判斷是否可匯出。
- 目前行為：未提供分頁、快取過期機制；為跨請求快取使用此欄位，重啟服務即清空。
- **實作錨點**：`app/server.py`
- **驗證證據**：`tests/test_server.py::test_export_without_run_returns_404`

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

