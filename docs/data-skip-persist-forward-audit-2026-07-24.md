# 資料跳過、持久化、轉送與記錄分支稽核

日期：2026-07-24

範圍：`src/note_filler/**/*.py`、`app/**/*.py` 及對應離線測試。

機器清單：`docs/evidence/exception-skip-branch-scan-2026-07-24.json` 與同名 `.txt`。

## 結論

AST 掃描共找到 72 個語法候選：11 個 `raise`、16 個 `except`、23 個空值型回傳、22 個 `continue`。逐項沿呼叫鏈分類後，會丟棄、降級、截斷、去重、停止轉送或持久化失敗的資料分支，現在皆具備以下至少一項處理：

1. 單行 JSON 稽核事件，固定含 `event` 與 `data_id`；
2. 明確失敗回傳、例外或 CLI／HTTP 狀態；
3. 可查詢的 `delivery_manifest.json`；
4. 保守恢復為 `missing`／`pending_evidence`，不把無證據內容升級為已驗證。

此次另修正兩條會造成實際資料錯置的根因：

- `detect_gaps` 漏回輸入問題時，不再讓該問題從流程消失，而是補回 `missing` 並記錄 `gap_question_recovered`。
- Web 新上傳開始前先清除 `last_doc`；本次 pipeline 失敗後，`/export` 回 404，不再轉送上一份成功稿。

## 稽核格式

`src/note_filler/audit.py::audit_event` 是單一入口。每筆紀錄是一行 JSON：

```json
{"data_id":"case-123","event":"gap_question_recovered","reason":"LLM response omitted question; treating as missing"}
```

`data_id` 依資料層級使用輸入路徑、問題文字、來源 ID、URL、法規條號、工具名稱或上傳檔名；額外欄位記錄原因、錯誤、略過來源 ID、原始／保留數量與降級結果。

## 路徑矩陣

| 階段 | 可能跳過／遺失的資料 | 處理與事件 |
|---|---|---|
| 輸入展開 | 空資料夾、重複 resolved path | `input_directory_skipped`、`input_file_deduplicated` |
| 解析／分類 | 空筆記、無法辨識領域、問題格式錯誤或空輸出 | `note_parsed_empty`、`domain_detection_defaulted`、`question_generation_skipped`、`question_generation_empty` |
| 缺口判定 | 無問題、格式錯誤、非物件、covered、非法狀態、無題目、缺理由、漏回輸入題 | 明確 fallback；`gap_detection_skipped`、`gap_item_skipped`、`gap_item_filtered`、`gap_reason_defaulted`、`gap_question_recovered` |
| 檢索路由 | 法規／Web 依賴缺失 | `law_source_retrieval_skipped`、`web_source_retrieval_skipped`；問題 ID 保留 |
| 法條檢索 | 無關鍵詞、重複條文、超過 20 筆 | `law_search_skipped`、`law_source_deduplicated`、`law_sources_truncated`；截斷事件含 omitted IDs |
| Web 檢索 | 空 query、搜尋失敗、超量 hit、非物件、缺 URL、抓取失敗／過短、分級失敗／drop、全文截斷 | `web_query_defaulted`、`web_search_failed`、`web_hits_truncated`、`web_hit_skipped`、`web_fetch_failed`、`web_content_skipped`、`web_grading_failed`、`web_source_not_forwarded`、`web_content_truncated` |
| Twinkle | 空回應、非文字／空內容、不可用 JSON、錯誤 similarity、不可持久化欄位、空全文、缺 token／query、非法 limit、查詢失敗、空 hits、非物件 hit、結果截斷 | `twinkle_response_empty`、`twinkle_content_item_skipped`、`twinkle_response_unusable`、`twinkle_similarity_defaulted`、`twinkle_record_field_skipped`、`twinkle_source_content_empty`、`twinkle_search_skipped`、`twinkle_limit_defaulted`、`twinkle_search_failed`、`twinkle_hits_empty`、`twinkle_hit_skipped`、`twinkle_sources_truncated` |
| 寫作／驗證 | 待補證、重複／越界引用、無有效來源、未引用來源不送驗 | `supplement_writing_deferred`、`citation_source_deduplicated`、`out-of-range citation marker removed`、`supplement_has_no_forwardable_sources`、`sources_not_forwarded_to_validation` |
| 組稿／法規查核 | 缺寫作結果、引用 ID 對不上、缺 validation、法條不存在、法規不在離線庫、重複 issue | `written_supplement_missing`、`used_sources_not_forwarded`、`validation_not_forwarded`、`law_citation_not_forwarded_as_verified`、`law_citation_skipped`、`law_issue_deduplicated`；所有無來源段維持 `pending_evidence` |
| 法規索引持久化 | 語料缺 pcode 或條文 | `law_index_file_skipped`，含檔案路徑與解析計數 |
| CLI 交付 | 同目錄回執替換、單檔處理失敗、失敗回執也無法持久化 | `delivery_receipt_replaced` 明記被替換的最新回執契約；`file_processing_failed` 後先嘗試 failed manifest，再以 `delivery_receipt_persist_failed` 與 stderr 明確回報，批次最終 exit code 為 1 |
| Web 交付 | pipeline 失敗、暫存檔刪除失敗、舊稿誤匯出 | `web_pipeline_failed`、`temp_file_cleanup_failed`；失敗後 `/export` 回 404 |

## 掃描候選中不屬於資料遺失的分支

下列分支保留既有最小行為，並由資料合約或上游／下游處理覆蓋：

- `export.py` 對 original segment 的 `continue` 是原稿逐字輸出的分流；原文已先寫入，不是丟棄。
- `pipeline.py` 法規查核略過 original segment，只查 AI supplement；原文不得改寫。
- `citation_formatter.py` 對空來源回空參考區塊；段落本身仍輸出且標為 `pending_evidence`。
- `_best_anchor`／`fuzzy_find_law` 查無匹配回 `None` 是公開合約；補充仍保留、法規引用則不誤報。
- Twinkle `_ensure_session` 已有 session 時直接回傳，未略過請求；`_decode_streamable_http` 空傳輸會在 `call_tool` 產生 `twinkle_response_empty`。
- `_record_fulltext` 不把 `similarity`／`distance` 混入可引用全文；相似度已轉成 `Source.distance`，其他可引用 scalar 欄位仍保存。
- `_grounded`、引用去重與來源排序只決定信心或順序，不刪除 `CorrectionDoc` 原稿或實際引用來源。

## 可重現驗證

### 全量分支掃描

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 scripts/_scan_exception_skip_branches.py
KIND_COUNTS {'raise': 11, 'except': 16, 'return_emptyish': 23, 'continue': 22}
TOTAL 72
```

完整逐項輸出已保存於 `docs/evidence/exception-skip-branch-scan-2026-07-24.txt`，結構化資料保存於同名 JSON。

### 受影響路徑回歸

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_exception_skip_traceability.py tests/test_gap.py tests/test_web.py tests/test_twinkle.py tests/test_correction.py tests/test_pipeline.py tests/test_cli.py tests/test_server.py
78 passed, 4 deselected in 11.79s
```

### 完整預設品質閘

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -q
219 passed, 11 deselected in 67.04s (0:01:07)
```

預設閘依 `pyproject.toml` 排除 11 個 `integration` 測試；本次未宣稱外部 Grok／Twinkle 整合測試已執行。離線套件已驗證原稿逐字不變、無來源／`【待補證】` 維持 `pending_evidence`、只掛實際引用來源，以及法條引用通過離線查核。
