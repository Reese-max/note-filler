# Note-Filler UI 介面回歸索引（最小版）

## 版本

- 日期：2026-07-19

## 追溯資訊

- **設計編號**: D-05
- **需求編號**: R-02（範圍 - MVP）, R-09（UI MVP）
- **驗收編號**: A-01（test_index_returns_upload_form）, A-02（test_run_renders_two_columns）, A-03（test_export_returns_markdown_attachment）, A-04（test_export_without_run_returns_404）
- **追溯狀態**: 完整
- **追溯索引**: `docs/specs/design-traceability-index.md`

## 1) 可核實的 UI 觀察點

| 項目 | 位置 | 佐證 |
|---|---|---|
| 上傳入口 | `app/templates/index.html` | `tests/test_server.py::test_index_returns_upload_form` |
| 雙欄結果頁 | `app/templates/result.html` | `tests/test_server.py::test_run_renders_two_columns` |
| 原稿可見欄 | `.col#original` | 同上 |
| 補充高亮欄位 | `.supplement` | 同上 |
| 無來源警示 | `.pending` | 同上 |
| 來源展開 | `details.sources` | 同上 |
| 匯出連結 | `/export/{result_id}` | `app/templates/result.html`, `tests/test_server.py::test_export_returns_markdown_attachment` |

## 2) 與路由證據對照

- `/run` 成功後，`app.state.results[result_id]` 可供 `/export/{result_id}` 使用：`app/server.py`
- `/export` 或 `/export/{未知id}` 無有效 capability 時回 `404`：`tests/test_server.py::test_export_without_run_returns_404`、`test_export_b_cannot_receive_a_result`

## 3) 畫面截圖與回歸命名規則（草案）

### 目前狀態

- 尚未加入實際 screenshot 檔；本輪以「命名文件 + 錨點可核查」完成。

### 規則（未來可補）

- 檔名以 `docs/specs/evidence/ui/<scenario>.md` 或 `.png`，並在本頁加上「route / scenario / viewport / 驗證命令」欄位。

