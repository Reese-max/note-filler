# 資料處理流程：異常與跳過分支可追蹤清單

**日期**: 2026-07-24  
**範圍**: `src/note_filler/**`、`app/server.py` 資料處理路徑（不含 tests/、scripts/ 測試輔助）  
**任務**: 盤點可能造成**未處理 / 未持久化 / 未轉送 / 未記錄**的異常與跳過分支；逐分支對應檔案、函式、處理機制  
**方法**: 人工讀碼 + AST 掃描腳本  
**機器證據**:
- 掃描腳本: [`scripts/_scan_exception_skip_branches.py`](../scripts/_scan_exception_skip_branches.py)
- 掃描輸出: [`docs/evidence/exception-skip-branch-scan-2026-07-24.json`](evidence/exception-skip-branch-scan-2026-07-24.json)
- 掃描摘要: `except=13` / `continue=19` / `return_emptyish=23` / `raise=11`（合計 66 個語法節點；本報告僅列**資料處理語意**相關分支，排除純 helper 正常返回）

---

## 0. 風險語意定義

| 代碼 | 名稱 | 定義 |
|------|------|------|
| **U-H** | 未處理 | 例外向上拋出或流程中斷，呼叫端未保證有回執/manifest |
| **U-P** | 未持久化 | 執行中狀態或失敗原因未寫入輸出檔 / delivery_manifest / DB |
| **U-F** | 未轉送 | 中間結果被丟棄或未傳入下一階段（sources/gaps/validations 等） |
| **U-L** | 未記錄 | 跳過/降級/吞例外時無 `logger` / `stderr` / 可機器比對標記 |

處理機制標籤：

| 標籤 | 意義 |
|------|------|
| `raise` | 明確拋例外中斷 |
| `return_empty` | 回 `[]` / `None` / `{}` 繼續下游 |
| `continue_skip` | 迴圈內略過單一元素 |
| `degrade_pending` | 降為 `pending_evidence` 或【待補證】 |
| `degrade_fallback` | 保守 fallback（如 all-missing、domain=other） |
| `log_warning` | 有 `logger.warning` |
| `stderr_print` | CLI `print(..., file=sys.stderr)` |
| `silent` | 無 log / 無占位標記 |

---

## 1. 主流程拓樸（資料如何流動）

```
CLI(__main__.process_file) / Web(app.server.run)
  └─ run_pipeline (pipeline.py)
       T2 parse_note
       T3 detect_domain
       T4 generate_questions
       T5 detect_gaps
       loop gaps:
         T9 retrieve_for_gap → law_search | twinkle | web
         Q3 write_supplement
         T10 cross_validate  → validations[q]
       T12 assemble_correction(doc, gaps, retrieved, written, validations)
       C6 _verify_law_citations (domain==law)
  └─ export to_markdown | to_json | to_docx
  └─ write_delivery_receipt (CLI only)
```

**跨階段轉送缺口（結構級）** — 見 B-PIPE-03、B-PIPE-04。

---

## 2. 逐分支可追蹤清單

欄位說明：`ID` 穩定編號；`檔案:行` 對應當前 worktree 原始碼；`影響` 為 U-H/U-P/U-F/U-L 組合。

### 2.1 CLI / 交付層 — `__main__.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-CLI-01 | `__main__.py:115-116` | `process_file` | docx 輸出不存在或 size=0 | `raise RuntimeError` | U-H | 明確拒絕假送達；例外外傳 |
| B-CLI-02 | `__main__.py:119-121` | `process_file` | md/json body 空白 | `raise RuntimeError` | U-H | 同上 |
| B-CLI-03 | `__main__.py:125-132` | `process_file` | 成功路徑寫 receipt | `write_delivery_receipt` status=delivered | — | 成功有持久化回執 |
| B-CLI-04 | `__main__.py:165-166` | `main` | 單檔任意 Exception | `except Exception` + `stderr_print`；**不寫 failed receipt** | **U-P**, U-L(部分) | 有 stderr 類型+訊息，但 `delivery_manifest.json` 不記 failed；批次可部分成功 |
| B-CLI-05 | `__main__.py:146-148` | `main` | 無任何 .txt/.docx | `return 2` + stderr | U-H | 無檔可處理，exit 2 |
| B-CLI-06 | `__main__.py:149-150` | `main` | 無 TWINKLE_HUB_TOKEN | `stderr_print` 警告，繼續 | — | 有記錄；twinkle 後續回 [] |
| B-CLI-07 | `__main__.py:151-152` | `main` | 法條 DB 不存在 | `stderr_print` 警告，繼續 | — | 有記錄；Level A 查無結果 |
| B-CLI-08 | `__main__.py:168-169` | `main` | 部分失敗 | exit 1 if ok!=len(files) | — | 批次結果有 exit code |

### 2.2 Web — `app/server.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-WEB-01 | `app/server.py:40-52` | `run` | pipeline/讀檔任一例外 | **無 try/except** → FastAPI 500 | **U-H**, **U-P**, **U-L** | 無 delivery receipt；失敗不落盤；僅 HTTP 錯誤 |
| B-WEB-02 | `app/server.py:49` | `run` | 成功 | `app.state.last_doc = doc` 記憶體 | **U-P** | 結果只在行程記憶體；重啟即失 |
| B-WEB-03 | `app/server.py:56-60` | `export` | last_doc is None | 404 PlainText | — | 有明確訊息，非靜默 |
| B-WEB-04 | `app/server.py:44-46` | `run` | NamedTemporaryFile delete=False | 暫存檔未刪 | U-P(本機垃圾) | 非業務資料遺失，但 I/O 殘留 |

### 2.3 管線編排 — `pipeline.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-PIPE-01 | `pipeline.py:28-34` | `run_pipeline` | 僅對 T5 回傳之 gaps 迭代 | 正常迴圈 | U-F(設計) | covered 問題永不進 retrieve/write |
| B-PIPE-02 | `pipeline.py:38-39` | `run_pipeline` | domain != "law" | 跳過 `_verify_law_citations` | U-F | admin/exam 含法條引用時不跑 C6 |
| B-PIPE-03 | `pipeline.py:34,36` | `run_pipeline` | 計算 `validations` 並傳入 assemble | **assemble 未使用 validations** | **U-F** | conflict/verified 結果未轉送進 Segment；confidence 改由 assemble 重算 |
| B-PIPE-04 | `pipeline.py:51-53` | `_verify_law_citations` | findings 含 `article_not_found` | `degrade_pending` 改 confidence | **U-L** | 無 logger；`penalty_mismatch` **完全不處理**（U-F） |
| B-PIPE-05 | `pipeline.py:49-50` | `_verify_law_citations` | seg.type != supplement | `continue_skip` | — | 設計正確，略過原文段 |

### 2.4 解析 — `parse.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-PAR-01 | `parse.py:47` | `parse_note` | 副檔名非 .txt/.docx | `raise ValueError` | U-H | 明確錯誤 |
| B-PAR-02 | `parse.py:42-43` | `parse_note` | 檔案讀取 OSError | 未攔截 → 上拋 | U-H | 由 CLI B-CLI-04 或 Web B-WEB-01 接 |
| B-PAR-03 | `parse.py:28` | `_split_txt` | 空白段 | 過濾不進 paragraphs | U-F(設計) | 原文空白段不保留為 Paragraph |
| B-PAR-04 | `parse.py:36` | `_read_docx` | 空白段落 | 過濾 | U-F(設計) | 同上 |
| B-PAR-05 | `parse.py:49-53` | `parse_note` | 全空檔 → empty Document | `return Document(..., paragraphs=(), full_text="")` | **U-L**, U-F | **無告警**；下游可能 0 gaps / 空訂正稿 |

### 2.5 領域 — `domain.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-DOM-01 | `domain.py:31-32` | `detect_domain` | token 精準命中 | 直接回傳 | — | 正常 |
| B-DOM-02 | `domain.py:35-37` | `detect_domain` | 雜訊中含合法標籤 | 優先序抽取 | **U-L** | 無 log；可能誤抽 |
| B-DOM-03 | `domain.py:39-40` | `detect_domain` | 完全無法辨識 | `degrade_fallback` → `"other"` | **U-L**, U-F | **無 log**；改走 web 不走 law/twinkle |
| B-DOM-04 | `domain.py:27` | `detect_domain` | llm.complete 拋錯 | 未攔截 → 上拋 | U-H | 整檔失敗 |

### 2.6 問題生成 — `questions.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-Q-01 | `questions.py:46-49` | `generate_questions` | markdown 圍欄 | 剝離後再解析 | — | 可能截斷但意圖明確 |
| B-Q-02 | `questions.py:51-52` | `generate_questions` | 回應以 `[`/`{` 開頭 | `return_empty` `[]` | **U-L**, **U-F** | **無 log**；禁止 JSON 問題 → 整批 gap 為 0 |
| B-Q-03 | `questions.py:54-55` | `generate_questions` | 空行 | 過濾 | — | 設計正確 |
| B-Q-04 | `questions.py:43` | `generate_questions` | llm 拋錯 | 上拋 | U-H | 整檔失敗 |

### 2.7 缺口偵測 — `gap.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-GAP-01 | `gap.py:58-59` | `detect_gaps` | questions 空 | `return_empty` `[]` | U-F, **U-L** | 跟隨上游；無 log |
| B-GAP-02 | `gap.py:67-73` | `detect_gaps` | JSON 解析失敗或非 list | `except` → `_all_missing` | **U-L** | 保守補齊（安全）但**無 log**；reason 字串有「解析失敗」 |
| B-GAP-03 | `gap.py:77-78` | `detect_gaps` | item 非 dict | `continue_skip` | **U-L**, **U-F** | 該元素靜默消失，可能漏 gap |
| B-GAP-04 | `gap.py:80-81` | `detect_gaps` | status 非 partial/missing | `continue_skip` | — | covered 過濾，設計正確 |
| B-GAP-05 | `gap.py:84-86` | `detect_gaps` | 缺 question/reason 鍵 | 預設 `""` | U-F, **U-L** | 空 question 仍可能進 gaps |
| B-GAP-06 | `gap.py:65` | `detect_gaps` | llm 拋錯 | 上拋 | U-H | 整檔失敗 |

### 2.8 檢索路由 — `retrieve/__init__.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-RET-01 | `retrieve/__init__.py:37-38` | `retrieve_for_gap` | law/admin/exam 且 law+llm 齊 | 加法條 Level A | — | 正常 |
| B-RET-02 | `retrieve/__init__.py:37` | `retrieve_for_gap` | law 域但 law is None 或 llm is None | **跳過** search_law_sources | **U-F**, **U-L** | 無 log；Level A 整批缺失 |
| B-RET-03 | `retrieve/__init__.py:39-41` | `retrieve_for_gap` | domain==other 且 llm 齊 | 只 web | — | 設計 |
| B-RET-04 | `retrieve/__init__.py:39` | `retrieve_for_gap` | other 但 llm is None | 不加 web | **U-F**, **U-L** | 無 log |
| B-RET-05 | `retrieve/__init__.py:42-43` | `retrieve_for_gap` | law 域 | 加 twinkle；other 不打 | — | 設計 |

### 2.9 法條搜尋 — `retrieve/law_search.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-LAW-01 | `law_search.py:38-41` | `_parse_llm` | JSON 失敗 | data=None → 整串當 keyword | **U-L** | 無 log；可能誤關鍵詞 |
| B-LAW-02 | `law_search.py:51-52` | `_parse_llm` | 非 dict | 整串當 keyword | **U-L** | 同上 |
| B-LAW-03 | `law_search.py:61-62` | `search_law_sources` | keywords 空 | `return_empty` `[]` | **U-L**, **U-F** | **無 log**；Level A 空 |
| B-LAW-04 | `law_search.py:70-71` | `search_law_sources` | (pcode, article) 重複 | `continue_skip` 去重 | — | 設計 |
| B-LAW-05 | `law_search.py:74` | `search_law_sources` | rows 超過 20 | 截斷 `[:20]` | **U-F**, **U-L** | 多餘法條未轉送；無 log |
| B-LAW-06 | `law_search.py:59` | `search_law_sources` | llm 拋錯 | 上拋 | U-H | 中斷該 gap 整檔 |

### 2.10 Twinkle — `retrieve/twinkle.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-TW-01 | `twinkle.py:38-39` | `_decode_streamable_http` | 空 body | `return None` | U-F | 上層 call_tool → `{}` |
| B-TW-02 | `twinkle.py:42-44` | `_decode_streamable_http` | 非物件 / JSON-RPC error | `raise MCPProtocolError` | U-H→吞 | 被 search 外層 except 吞 |
| B-TW-03 | `twinkle.py:63-64` | `_rpc` | 無 token | `raise MCPProtocolError` | U-H→吞 | 同上；正常路徑 token 空在 search 前置回 [] |
| B-TW-04 | `twinkle.py:104-105` | `call_tool` | response falsy | `return {}` | **U-L**, U-F | 無 log；hits 空 |
| B-TW-05 | `twinkle.py:107-116` | `call_tool` | 缺 result/content / isError | `raise` | U-H→吞 | 被 search 吞 |
| B-TW-06 | `twinkle.py:118-122` | `call_tool` | content item 非 text | `continue_skip` | **U-L** | 略過非 text block |
| B-TW-07 | `twinkle.py:126` | `call_tool` | 無可用 payload | `return {}` | **U-L**, U-F | 無 log |
| B-TW-08 | `twinkle.py:141-142` | `_clamp_similarity` | 非數值 | `return 0.0` | — | distance 偏大，可排序 |
| B-TW-09 | `twinkle.py:151` | `_extract_hits` | 無 hits/results/data | `return []` | **U-L**, U-F | 無 log |
| B-TW-10 | `twinkle.py:171-177` | `_to_source` | 缺 title | `return None` + **log_warning** | — | 有記錄 |
| B-TW-11 | `twinkle.py:213-214` | `TwinkleClient.search` | 無 token 或空 query | `return_empty` `[]` | U-F, **U-L**(本層) | CLI 有 token 警告；本函式無 log |
| B-TW-12 | `twinkle.py:217-218` | `search` | n 非 int | limit=3 | — | 容錯 |
| B-TW-13 | `twinkle.py:224-226` | `search` | 任一 Exception | **log_warning** + `return []` | U-F | 吞例外但**有 log**；Level B 靜默空 |
| B-TW-14 | `twinkle.py:229-230` | `search` | hit 非 dict | `continue_skip` | **U-L**, U-F | 無 log |
| B-TW-15 | `twinkle.py:231-233` | `search` | `_to_source` 回 None | 不 append | — | 依 B-TW-10 已 log |

### 2.11 開放網路 — `retrieve/web.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-WEBSRC-01 | `web.py:56-61` | `_extract_query` | llm 抽取失敗 | `except Exception` → 退回 gap.question | **U-L** | **無 log** |
| B-WEBSRC-02 | `web.py:67-70` | `_grade` | JSON 解析失敗 | `return ("drop", None)` | **U-L**, U-F | 當 drop；**無 log** |
| B-WEBSRC-03 | `web.py:72-73` | `_grade` | level 非 C/D | drop | — | 設計 |
| B-WEBSRC-04 | `web.py:95-97` | `search_web_sources` | search/query 階段 Exception | **log_warning** + `return []` | U-F | 整批空但有 log |
| B-WEBSRC-05 | `web.py:103-104` | `search_web_sources` | hit 無 href | `continue_skip` | **U-L**, U-F | **無 log** |
| B-WEBSRC-06 | `web.py:107-108` | `search_web_sources` | fetch 拋例外 | `continue_skip` | **U-L**, U-F | **無 log**（底層 `_fetch_fulltext` 自己有 log 若走預設） |
| B-WEBSRC-07 | `web.py:109-110` | `search_web_sources` | text None/過短 `<200` | `continue_skip` | **U-L**, U-F | **無 log** |
| B-WEBSRC-08 | `web.py:113-114` | `search_web_sources` | _grade 拋例外 | `continue_skip` | **U-L**, U-F | **無 log** |
| B-WEBSRC-09 | `web.py:115-116` | `search_web_sources` | level drop | `continue_skip` | — | 設計（品質閘） |
| B-WEBSRC-10 | `web.py:117` | `search_web_sources` | 全文 >2500 | 截斷 + note | U-F(截斷) | 有截斷註記字串 |
| B-WEBSRC-11 | `web.py:141-143` | `_ddg_search` | DDGS 失敗 | **log_warning** + `[]` | U-F | 有 log |
| B-WEBSRC-12 | `web.py:152-153` | `_fetch_fulltext` | html 空 | `return None` | **U-L** | 無 log |
| B-WEBSRC-13 | `web.py:155-157` | `_fetch_fulltext` | 例外 | **log_warning** + None | U-F | 有 log |

### 2.12 撰寫 — `write.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-WRI-01 | `write.py:47-48` | `write_supplement` | 以【待補證】開頭 | used_source_ids=[] | — | C6/pending 契約；可追蹤 |
| B-WRI-02 | `write.py:60` | `_sub` 內 | `[^n]` 越界 | 標記從 text 移除、不計 used | **U-L**, U-F | **無 log**；標記靜默消失 |
| B-WRI-03 | `write.py:62-63` | `write_supplement` | 無任何有效 `[^n]` | used=[] → 後續 pending | — | 由 assemble 定 confidence |
| B-WRI-04 | `write.py:45` | `write_supplement` | llm 拋錯 | 上拋 | U-H | 整檔失敗 |

### 2.13 交叉驗證 — `verify.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-VER-01 | `verify.py:77-94` | `cross_validate` | sources 空或不足 | verified=False | — | 純函式，結果進 validations |
| B-VER-02 | `verify.py:87` | `cross_validate` | 衝突關鍵詞 | conflict=True + note | — | 只標記不選邊 |
| B-VER-03 | *(結構)* | `assemble_correction` | validations 參數 | **完全未讀取** | **U-F**, **U-P** | conflict_note **未進 Segment/export**；屬最嚴重未轉送之一 |

### 2.14 訂正組裝 — `correction.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-COR-01 | `correction.py:97-104` | `assemble_correction` | written 缺 gap key | **log_warning** + MISSING_WRITTEN_TEXT + pending | — | 已修復靜默空字串 |
| B-COR-02 | `correction.py:109-110` | `assemble_correction` | used_id 不在 retrieved | 過濾略過 | **U-L**, U-F | **無 log**；來源靜默丟棄 |
| B-COR-03 | `correction.py:113-118` | `assemble_correction` | 待補證 / 未 grounded | `degrade_pending` | — | 契約行為 |
| B-COR-04 | `correction.py:48-49` | `_best_anchor` | question 無 token | anchor_idx=None | **U-L** | 補充段無錨點；無 log |
| B-COR-05 | `correction.py:80-90` | `assemble_correction` | 原文段 | 逐字 immutable | — | 品質閘：原稿不可變 |

### 2.15 法規引用核對 — `knowledge/law_citation_check.py` + pipeline C6

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-CITE-01 | `law_citation_check.py:51-53` | `check_law_citations` | 指代詞且無前文法規 | `continue_skip` | **U-L**, U-F | 不報；可能漏檢 |
| B-CITE-02 | `law_citation_check.py:60-71` | `check_law_citations` | 法規名不在庫 | **不發 article_not_found** | U-F(設計防誤報) | 簡稱/未收錄靜默略過 |
| B-CITE-03 | `law_citation_check.py:61-69` | `check_law_citations` | 條號不存在 | issue article_not_found | — | pipeline 會降 pending |
| B-CITE-04 | `law_citation_check.py:75-84` | `check_law_citations` | 罰則金額不符 | issue penalty_mismatch | **U-F** | pipeline **不讀此 kind** → 不降級不告警 |
| B-CITE-05 | `law_citation_check.py:97-98` | `annotate_law_mismatches` | 重複 issue | continue 去重 | — | 設計 |

### 2.16 法條索引 — `knowledge/law_lookup.py`（建庫/查詢）

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-IDX-01 | `law_lookup.py:119-120` | `build_law_index` | md 無 pcode 或無 articles | `continue_skip` | **U-L**, U-F | 建庫時略過檔案無 log |
| B-IDX-02 | `law_lookup.py:156` | `lookup_article` | 查無 | `return None` | — | 呼叫端處理 |
| B-IDX-03 | `law_lookup.py:218` | `fuzzy_find_law` | 無匹配 | `return None` | — | 主流程未呼叫 fuzzy |

### 2.17 匯出 — `export.py` / `citation_formatter.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-EXP-01 | `export.py:47-49` | `to_markdown` | original 段 | 原樣輸出 | — | 設計 |
| B-EXP-02 | `export.py:59-61` | `to_markdown` | pending_evidence | ⚠待補證 前綴 | — | 可機器/人眼追蹤 |
| B-EXP-03 | `export.py:65-68` | `to_markdown` | 無 cited sources | 無參考區塊 | — | 空 sources 契約 |
| B-EXP-04 | `export.py:105` | `to_docx` | save 失敗 | 上拋 | U-H | 由 CLI 接 |
| B-EXP-05 | `citation_formatter.py:39-40` | `build_reference_block` | 空 sources | `return ""` | — | 設計 |

### 2.18 LLM 傳輸 — `llm.py`

| ID | 檔案:行 | 函式 | 觸發條件 | 處理機制 | 影響 | 說明 |
|----|---------|------|----------|----------|------|------|
| B-LLM-01 | `llm.py:39-41` | `GrokClient.complete` | 網路/HTTP/JSON/缺 choices | **未攔截** 上拋 | U-H, **U-L** | 無模組內 log；整檔失敗 |
| B-LLM-02 | `llm.py:51-53` | `FakeLLM.complete` | responses 耗盡 | IndexError 上拋 | U-H | 測試用 |

---

## 3. 依四類風險彙總（優先關注）

### 3.1 未記錄（U-L）— 靜默跳過/降級 TOP

| 優先 | ID | 摘要 |
|------|-----|------|
| 高 | B-Q-02 | JSON 形問題回 `[]` → 整批不補 |
| 高 | B-GAP-03 | gap item 非 dict 靜默 continue |
| 高 | B-LAW-03 | 關鍵詞空 → Level A 空 |
| 高 | B-DOM-03 | domain 降級 other 無 log |
| 高 | B-PAR-05 | 空檔 Document 無告警 |
| 高 | B-PIPE-04 / B-CITE-04 | 法條降級與 penalty_mismatch 無 log / 未用 |
| 中 | B-WEBSRC-01,05,06,07,08 | web 單頁/分級/過短多處 silent continue |
| 中 | B-COR-02 | used_id 對不到 Source 靜默丟 |
| 中 | B-WRI-02 | 越界 `[^n]` 靜默移除 |
| 中 | B-RET-02/04 | law/llm 缺依賴時跳過檢索無 log |

### 3.2 未轉送（U-F）— 中間結果未進下游

| 優先 | ID | 摘要 |
|------|-----|------|
| **最高** | B-PIPE-03 / B-VER-03 | `validations`（含 conflict）算了但 assemble/export **完全不用** |
| 高 | B-CITE-04 + B-PIPE-04 | `penalty_mismatch` 產出但不影響 confidence |
| 高 | B-Q-02 → B-GAP-01 | 問題空 → gaps 空 → 無補充 |
| 中 | B-LAW-05 | 法條命中截斷 20 |
| 中 | B-TW-13 / B-WEBSRC-04 | 外部失敗 → 空 sources，寫作易走【待補證】 |

### 3.3 未持久化（U-P）

| 優先 | ID | 摘要 |
|------|-----|------|
| 高 | B-CLI-04 | 單檔失敗只有 stderr，**無 failed delivery_manifest** |
| 高 | B-WEB-01/02 | Web 無 receipt；成功只存 `app.state` 記憶體 |
| 中 | B-VER-03 | conflict_note 永不進輸出檔 |

### 3.4 未處理（U-H）— 例外中斷（有設計者）

| ID | 摘要 |
|----|------|
| B-PAR-01/02, B-DOM-04, B-Q-04, B-GAP-06, B-LAW-06, B-WRI-04, B-LLM-01 | LLM/IO 未局部攔截 → 整檔失敗 |
| B-CLI-01/02 | 空輸出明確 raise（**正確**拒假送達） |
| B-WEB-01 | Web 無包裝 → 500 |

外部檢索（twinkle/web）採 **吞例外 + 空結果**，屬「已處理但可能 U-F」而非 U-H。

---

## 4. 已有完整處理鏈（對照：非缺口）

| 機制 | 位置 | 說明 |
|------|------|------|
| pending_evidence /【待補證】 | write / correction / export | 無來源或不足時可追蹤標記 |
| written 缺失占位 | `correction.py:97-104` | logger.warning + MISSING_WRITTEN_TEXT |
| twinkle 查詢失敗 | `twinkle.py:224-226` | logger.warning + [] |
| web 搜尋失敗 | `web.py:95-97`, `_ddg_search` | logger.warning + [] |
| trafilatura 失敗 | `web.py:155-157` | logger.warning |
| 原稿 immutable | correction original 段 | 逐字保留 |
| 空訂正稿拒送達 | `__main__.process_file` | RuntimeError |
| 批次失敗 exit code | `main` return 1 | 部分失敗可偵測 |

---

## 5. 與既有報告關係

| 既有文件 | 關係 |
|----------|------|
| `docs/silent-data-loss-audit.md` | 2026-07-23 靜默遺失風險與測試覆蓋；本報告補**四類風險碼 + 全分支 ID + 現行行號** |
| `docs/靜默資料遺失分支盤點報告.md` | 告警缺口清單；本報告對齊並修正（如 assemble missing written 已有 log） |
| `docs/io-path-gap-audit-2026-07-23.md` | I/O 與測試覆蓋；本報告聚焦異常/跳過語意 |

本報告**不修改產品程式**；僅盤點。修復應另開任務，並同步測試（L030–L032）。

---

## 6. 重現掃描命令（證據）

工作目錄：本 worktree 根目錄。

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 scripts/_scan_exception_skip_branches.py
```

預期摘要（2026-07-24 實跑）：

```text
KIND_COUNTS {'raise': 11, 'except': 13, 'return_emptyish': 23, 'continue': 19}
TOTAL 66
WROTE .../docs/evidence/exception-skip-branch-scan-2026-07-24.json
```

---

## 7. 分支計數摘要

| 區段 | 分支 ID 數（本報告列） |
|------|------------------------|
| CLI | 8 |
| Web app | 4 |
| pipeline | 5 |
| parse | 5 |
| domain | 4 |
| questions | 4 |
| gap | 6 |
| retrieve 路由 | 5 |
| law_search | 6 |
| twinkle | 15 |
| web sources | 13 |
| write | 4 |
| verify | 3 |
| correction | 5 |
| citation/lookup | 8 |
| export/citation_formatter | 5 |
| llm | 2 |
| **合計（含正常設計分支）** | **約 102 列** |

其中標記含 **U-L 或高優先 U-F/U-P** 的「需關注」約 **35+**（見 §3）。

---

## 8. 結論

1. **資料處理主路徑**的致命例外多數**上拋**，CLI 以 stderr + 非零 exit 承接，但 **failed 狀態未寫 delivery_manifest（B-CLI-04）**；Web 更弱（B-WEB-01）。  
2. **外部檢索**（twinkle/web）採 resilience：`except` → 空結果，多數有 `logger.warning`；但 **單頁 continue 路徑仍大量 U-L**。  
3. **最關鍵未轉送**：`cross_validate` 的 `validations`（含 conflict）**未進入** `assemble_correction` / export（B-PIPE-03 / B-VER-03）。  
4. **最關鍵靜默降級**：questions JSON 拒收、gap 非 dict skip、domain→other、law 關鍵詞空、空檔 parse — 皆可能讓「看似成功、補充為零或檢索走錯」且缺 log。  
5. **品質閘契約**（原稿不可變、pending_evidence、只掛實際引用、法條 article_not_found 降級）在多處已落地；**penalty_mismatch 未接入 pipeline** 為契約覆蓋缺口。

— 報告結束 —
