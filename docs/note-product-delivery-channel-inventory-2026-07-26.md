# 成品筆記輸出路徑與直接送達缺口盤點

日期：2026-07-26

## 結論

唯一尚未直接送達使用者的路徑是 **CLI**。`process_file()` 產生的 digest、綁定報告與交付回執都只寫到同一個本機目錄；`delivery_manifest.json` 證明的是本機持久化，不是對外傳輸或使用者收件。Web 路徑已把結果頁與下載附件放進 HTTP response，沒有這個缺口。

後續唯一需要修改的實作位置如下：

| 項目 | 唯一目標 |
|---|---|
| 檔案 | `src/note_filler/__main__.py` |
| 函式 | `main()` |
| 新增通道 | CLI `stdout` 成品資料流：成功後輸出實際 digest payload，而非只輸出本機路徑 |
| 調整通道 | 現有進度、路徑、計數與完成訊息改走 `stderr`，避免污染 stdout 的成品內容 |

不需修改 `pipeline.py`、`export.py`、`app/server.py`、`process_file()` 或品質閘；它們已完成成品建立、驗證、序列化與本機留存。直接送達屬於 CLI 最外層的使用者介面責任。

## 現況輸出路徑

| 入口 | 成品資料流 | 最終通道 | 是否直接送達 |
|---|---|---|---|
| Pipeline | `run_pipeline()` 回傳記憶體中的 `CorrectionDoc` | Python 回傳值 | 否；這是內部資料，不是使用者通道 |
| CLI Markdown／JSON | `process_file()` → `to_markdown()`／`to_json()` → `Path.write_text()` | `<輸出目錄>/<原檔名>.訂正稿.md|json` | 否；只落本機檔案 |
| CLI DOCX | `process_file()` → `to_docx()` | `<輸出目錄>/<原檔名>.訂正稿.docx` | 否；只落本機檔案 |
| CLI 附屬產物 | `write_binding_report()`、`write_delivery_receipt()` | 同目錄的 `binding_report.json`、`delivery_manifest.json` | 否；兩者仍是本機檔案 |
| CLI 終端輸出 | `main()` 成功分支 | stdout 的輸入路徑、輸出路徑、補充／verified 計數與總完成數 | 否；未包含 digest 本文或檔案 bytes |
| Web 結果頁 | `POST /run` → `result.html` | HTTP HTML response | 是；訂正稿內容直接呈現在使用者 response |
| Web 下載 | `GET /export` → `to_markdown()` | HTTP `text/markdown` attachment (`correction.md`) | 是；成品直接在 response body |

## 缺口證據

1. `src/note_filler/__main__.py:145-158` 只建立目的路徑並寫入 MD／JSON／DOCX。
2. `src/note_filler/__main__.py:161-173` 再把 `binding_report.json` 與 `delivery_manifest.json` 寫到目的檔同目錄，回傳值仍只有路徑與計數。
3. `src/note_filler/__main__.py:202-204` 的 CLI 成功分支只印 `input → output` 與統計；digest 內容沒有進入 stdout。
4. `tests/test_delivery_receipt.py:155-172` 所謂「外部查詢」實際上是再用 `Path.read_text()` 讀本機 manifest，且以 `Path(...).exists()` 驗證本機輸出；未覆蓋任何對外傳輸。
5. 對照之下，`app/server.py:44-65` 已在 HTTP response 顯示訂正稿，`app/server.py:96-107` 也把 Markdown 放入 attachment response body。

因此，`status="delivered"` 目前只能解讀為「已成功持久化到本機輸出目錄」。它不能證明使用者已取得 digest。

## 唯一修正邊界

直接輸出應綁在 `main()`，因為它同時掌握每個 `process_file()` 成功結果、CLI 的 stdout／stderr 與最終 exit code。最小調整是保留既有本機產物與驗證鏈，另將成功成品送入乾淨的 stdout；stdout 寫出失敗也必須沿用現有失敗語義，不得計入成功。

未選擇 email、LINE、Discord 或 webhook：repo 目前沒有收件者身分、端點或認證契約，任選其一都會超出本盤點可由程式碼證實的範圍。stdout 是現有 CLI 原生、無新依賴且可由上層直接轉送給使用者的唯一明確通道。

## 品質閘影響

這個缺口位於成品驗證之後，不應改動下列不變式：

- 原稿逐字不可變。
- 無來源或 `【待補證】` 必須維持 `pending_evidence`。
- 成品只掛實際引用來源。
- 法條引用必須通過既有離線查核。
