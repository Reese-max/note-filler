# 主張級人工審查佇列與決策履歷（issue #3）

把「evidence-backed 訂正稿」升級成「可審查工作流」：每個 supplement/argument 有
獨立的人類審查狀態（與系統 `confidence` 分欄），決策寫進可序列化、可重播的
append-only ledger，匯出端新增 `accepted-only` 正式稿閘門。

## 狀態機

`src/note_filler/review.py`：`ReviewState`

| 狀態 | 來源 | 說明 |
| --- | --- | --- |
| `unreviewed` | 衍生 | 尚未有人類決策（預設） |
| `accepted` | 人類 | 核准進正式稿 |
| `rejected` | 人類 | 拒絕（不進正式稿） |
| `needs_more_evidence` | 人類 | 退回待補證 |
| `edited_accepted` | 人類 | 手動修訂後核准（理由碼預設 `manual_edit`） |
| `stale_review` | 衍生 | 舊決策綁定的指紋失效，需重新審查 |

`stale_review` / `unreviewed` 為衍生態，不可手動記錄（`record()` 拒絕）。

## 決策綁定與失效

每筆 `DecisionRecord` 記錄：`decision_id`、`argument_id`、`decision`、
`reason_code`（快捷碼 `source_not_supporting` / `out_of_scope` / `duplicate` /
`needs_primary_source` / `manual_edit`）、`note`、`reviewer`、`reviewed_at`、
`claim_hash`、`evidence_hash`、`previous_decision_id`（重審時指回前一筆）。

失效（fail closed → `stale_review`）：

- `claim_changed`：claim text / citation span 任一變動（`claim_revision_hash`）
- `evidence_changed`：引用來源 content/level/doc_date/url、confidence、
  conflict_note 任一變動（`evidence_bundle_hash`）
- `evidence_unavailable`：`source_ids` 宣告的來源物件已不存在

## Ledger 持久化

`ReviewLedger.save(path)` / `ReviewLedger.load_for_document(path, doc)`：

- schema `note_filler.review_ledger.v1`，atomic tmp+replace 寫入
- 以 `doc_fingerprint`（full_text + paragraphs 的 SHA-256，不依檔名）綁定
  文件；檔案不存在、毀損、schema 不符或文件指紋不符 → 回傳全新 ledger
  （全部 `unreviewed`，匯出端 fail closed）
- Web 端每份文件一個履歷檔：`LEDGER_PATH` 衍生為
  `review_ledger.<fingerprint16>.json`，新文件不覆寫舊文件的決策歷史

## 匯出閘

`to_markdown` / `to_json` / `to_docx` 皆接受 `export_mode` 與 `ledger`：

- `review-draft`（預設，行為相容）：全部 supplement 保留，每段附
  `> **審查狀態**：review_state=…` 標記行；文首有 `> **匯出模式**` 行
- `accepted-only`：只輸出 original 段與 `is_exportable()` 為真的 supplement
  —— 有效 `accepted`/`edited_accepted` 決策 **且** `confidence=="verified"`
  （人類核准凌駕不了無來源的安全契約）

CLI：`python -m note_filler … --export-mode accepted-only --review-ledger <path>`
（`--review-ledger` 預設 `.task_state/review_ledger.json`，亦可用
`NOTE_FILLER_REVIEW_LEDGER` 環境變數）。

## Web 介面（`app/server.py`）

- `POST /run`：產出訂正稿並載入/重建本文件的 ledger；結果頁上方顯示
  審查佇列計數（待審 N 筆）、狀態篩選連結與「下一個待審」錨點
- `POST /review`：`argument_id` + `decision`（`accepted`/`rejected`/
  `needs_more_evidence`）+ `reason_code`/`note`/`reviewer`/`edited_text`；
  `edited_text` 只能搭配核准類決策（文字有變動一律記 `edited_accepted`）；
  決策寫入每文件履歷檔（`LEDGER_PATH` 衍生，預設
  `.task_state/review_ledger.json` → `review_ledger.<fp16>.json`）
- `GET /result?filter=<state>`：依審查狀態篩選審查卡
- `GET /export?mode=review-draft|accepted-only`：匯出閘

審查卡顯示：審查狀態（含 stale 原因）、系統 confidence 與待補證/衝突原因、
逐來源立場（`supports`/`conflicts`/`context_only`/`unresolved` + 來源遺失標記）、
理由碼選單、備註/審查者/修訂文字欄位、三個決策按鈕、決策履歷。

## 來源立場（deterministic）

`source_stances(segment)` 不用 LLM 自評：

- segment 有 `conflict_note`：來源內容含反面詞 → `conflicts`；
  含正面詞（且不含反面詞）→ `supports`；皆無 → `unresolved`
- 無衝突：來源（title+content）與 claim 共享 ≥2 個詞彙單位
  （CJK bigram / ≥2 字元 ASCII token）→ `supports`，否則 `unresolved`
- `extended_readings` 檢索到但未引用 → `context_only`
- `source_ids` 宣告但無物件 → `unresolved` + `missing=True`

## 原稿不可變

`Document`/`Paragraph` 為 frozen dataclass；審查操作只改 supplement 的
`text`（建立新修訂），原稿段落 byte-for-byte 不變（測試鎖定）。

## 測試

`tests/test_review_queue.py`：accept/reject/needs-evidence、claim 編輯失效與
EDITED_ACCEPTED、source hash drift、citation span 變動、驗證契約變動、
來源遺失（evidence_unavailable）、衝突來源立場、accepted-only 匯出閘
（含無 ledger fail-closed）、ledger 存取/重播/指紋不符、原稿不可變、
`POST /review` + `GET /export?mode=` 端對端。
