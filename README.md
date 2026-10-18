# note_filler — 法律／行政／考試筆記補齊

讀一份既有筆記（`.txt` / `.docx`）→ AI 找出知識缺口 → 檢索台灣官方
一手來源 → 交叉驗證 → 產出「**訂正稿**」：保留已解析的原文段落、補充內容
就地標記、列出實際引用來源。解析與輸出隔離限制見「原稿保護」。

這不是「一句話生成新文件」的工具，而是「輸入既有筆記、原地補洞、
逐筆揭露引用來源與待補證狀態」的研究輔助工具。

## 安全契約（Safety Contract）

1. **原稿不可變**：解析器只讀輸入，補充以 overlay 疊加已解析的段落。
   CLI 輸出沒有碰撞防護，須依下方規則隔離輸出才能保護輸入與舊成品。
2. **無來源不進正文**：補充段落若無法引用實際檢索到的來源，程式硬性
   降級為 `pending_evidence`；匯出訂正稿仍保留該段並顯示待補證警示，
   不可當成已驗證正文。JSON 的 `text` 不保證有 `【待補證】` 前綴，
   判讀須以 `confidence` 為準，並由使用者審核後決定是否納入正典筆記。
3. **一手來源優先**：來源分級 A–D（`level` 欄位）；僅 Level A
   （法規一手，本地 `data/law_index.db`）/ Level C（官方／標準組織
   一手）或 ≥2 個相異來源可判定 `verified`。
4. **衝突只標記不選邊**：多來源表述矛盾時並列標記，交由人工判讀。
5. **交付可稽核**：僅 CLI 交付寫出 `delivery_manifest.json` 與
   `binding_report.json`，含內容雜湊與逐論點綁定檢查；網頁介面不寫這兩份回執。
6. **secrets 不入庫**：repo 不含任何 API key／token；憑證只經環境變數
   或本機 proxy 持有（見「Provider 邊界」）。

## 非目的（Non-goals）

- 不產生法律意見書，不取代專業判斷；輸出為研究用訂正稿。
- 不做多租戶、帳號、計費或對外公開部署（MVP 為本機單機使用）。
- 不支援 PDF OCR；法律／行政／考試以外領域的開放網路研究不在 MVP。
- 不接 grok 以外的模型 API。

## 目錄導覽：generated vs authoritative

| 路徑 | 角色 | authoritative / generated |
|---|---|---|
| 輸入筆記（使用者指定的 `.txt`／`.docx`） | 正典原稿 | **authoritative**，須備份並隔離輸出 |
| `data/law_index.db` | 本地法條索引快照（Level A 來源） | **authoritative**（入庫快照） |
| `src/note_filler/` | 產品套件本體 | authoritative（程式碼） |
| `app/` | FastAPI 網頁介面（上傳→訂正稿→匯出） | authoritative（程式碼） |
| `tests/`、`tests/fixtures/` | 測試與範例筆記 | authoritative |
| `docs/` | 設計 spec、稽核報告、證據 | authoritative（專案紀錄） |
| `scripts/` | 維護／稽核腳本（含 `run_tests.sh`） | authoritative |
| `output/` | 各次執行產物（`*.訂正稿.*`、manifest、報告） | **generated**，可由原稿重建 |
| `metrics_output/` | 品質指標量測產物 | **generated** |
| `.task_state/` | 執行期任務狀態 journal | **generated**（已 gitignore） |

CLI 指定的輸出目錄內每次交付包含：`<原檔名>.訂正稿.<md|json|docx>`（成品）、
`delivery_manifest.json`（交付回執）、`binding_report.json`
（論點—來源綁定報告）；由證據腳本產出的 run 另有 `run-meta.json`
與 `verification.json`（如 `output/main-flow-2026-07-24T061023Z/`）。

## 如何判讀訂正稿（五種文字狀態）

不需讀程式碼即可分辨成品中每一段是什麼：

| 狀態 | 外觀標記 | 內部欄位 |
|---|---|---|
| original（原文） | 無前綴的正文段 | `type=original`；追溯 `原始輸入 <檔>#paragraph-N` |
| AI-researched（AI 補充） | `> 【補充】` 開頭 | `type=supplement`，由研究層生成 |
| source-backed（來源佐證） | `【補充】` 段含 `[^n]` 註腳＋文末來源清單 | 須確認 `confidence=verified` 與 `binding_status=pass`；註腳本身不足以判定 |
| pending review（待審核） | `【補充】⚠待補證`，也可能含註腳 | `confidence=pending_evidence`；來源清單可能非空，保留 `來源識別碼 <id>…`；僅無引用來源時為 `sources=[]` 與 `處理紀錄 gap:N` |
| final（最終交付） | `.訂正稿` 檔本身 | `delivery_manifest.json` 的 `status=delivered` 且雜湊一致 |

`delivered` 表示成品已寫出，不表示所有補充已驗證或已經人工接受。

**read-only 檢視路徑**：本工具沒有 `--dry-run` 旗標；唯讀檢視請直接
讀取既有成品及回執，或執行下方的 JSON 查證命令：

- 直接開啟 repo 已交付的範例成品 `output/main-flow-2026-07-24T061023Z/real_note.訂正稿.md`，
  用來認識格式。**歷史樣本的雜湊與回執不一致，不能作為已驗證交付**；
  同目錄 `verification.json` 的 `hash_match=true` 也已過期，須重新計算比對。
- `bash scripts/run_tests.sh check` 可只列出測試集合不執行。

需要重新生成時，以 `-o` 指定獨立空輸出夾、`--format json` 取得結構化結果；
此操作會寫成品、回執、任務狀態與輸入檔旁的 `metrics_history.jsonl`。

## 溯源欄位與查證（Provenance）

`.訂正稿.json` 的 `segments[]` 帶有以下機器可讀欄位：

- `confidence`：補充段為 `verified`（有實際引用來源且通過交叉驗證）或
  `pending_evidence`（來源不足／未通過；Markdown 顯示 `⚠待補證`）。
  原文段的 `verified` 不代表內容已查證，只表示保留輸入原文，須先看 `type`。
- `sources[]`：實際被引用的來源，欄位含 `id`、`title`、`url`、
  `level`（A–D）、`content`（來源片段全文）、`fetched_date`
  （檢索日期）、`doc_date`（文件本身日期）、`distance`。
- `traceability[]`：每段的回溯錨點，kind 為 `original_input`
  （對回原稿段落）、`source`（對回來源 id）、`processing_record`
  （對回 gap 處理紀錄，供 pending 段追溯）。
- `source_id`：單行摘要式識別：`input:<檔案>#p<段號>`／
  `sources:<id1,id2,…>`／`pending:gap:<id>`。
- `citation_spans` / 內文 `[^n]` 註腳：論點與來源的就地對應。

`binding_report.json` 的 `arguments[]` 使用另一組欄位：`confidence`、
`source_ids`、`trace_source_ids`、`source_fragments`（`source_id`／`text`）、
`source_id_field`、`citation_spans`、`checks` 與 `binding_status`。
它沒有完整的 `sources[]` 或 `traceability[]`；來源 URL、日期與層級須以
`source_ids` 對回訂正稿 JSON 的 `segments[].sources[]` 查閱。

查證方式：

```bash
# 逐論點綁定狀態（pass / fail / pending_evidence）與引用來源
# （repo 已入庫一份可檢視的 binding_report 樣本）
python3 -c "import json; r=json.load(open('metrics_output/repair_measurement_2026-08-02/after/main-flow-2026-07-24/binding_report.json', encoding='utf-8')); print([(a['argument_id'], a['binding_status'], a['source_ids']) for a in r['arguments']])"

# 交付回執：狀態、計數、內容雜湊
python3 -m json.tool output/main-flow-2026-07-24T061023Z/delivery_manifest.json
```

`binding_report.json`（schema `note_filler.binding_report.v2`）另有
`traceability_markers`、`claim_source_map`、`citation_span_map` 三個
固定投影欄位，供測試與下游逐項比對。

## 原稿保護與回滾／恢復

- 解析範圍：TXT 會移除段落首尾空白並重組換行；DOCX 僅讀頂層段落文字，
  表格、頁首頁尾、圖片與原始排版不會保留在訂正稿。輸入檔本身仍由解析器只讀。
- CLI 使用固定名稱 `<原檔名>.訂正稿.<fmt>`，會覆寫既有成品；同目錄的
  `delivery_manifest.json` 與 `binding_report.json` 也僅保留最後一份。
  批次 DOCX 輸出甚至可能覆寫另一份名為 `<原檔名>.訂正稿.docx` 的輸入。
  執行前備份輸入與舊成品；**每份輸入各用一個位於輸入集合之外的空輸出目錄**，
  一次處理一份檔案，避免名稱碰撞。`-o` 不會移走輸入檔旁的 `metrics_history.jsonl`；
  原稿目錄不可寫時，先複製輸入至獨立工作目錄再執行（見端到端範例）。
- 執行期狀態持久化於 `.task_state/`（可用 `NOTE_FILLER_TASK_STATE`
  改路徑），依 generation / transmission 階段記錄成敗。
- `delivery_manifest.json` 持久化 `delivery_status`、
  `output_content_hash`、`input_content_hash`、
  `transmission_confirmation_hash`（全長 SHA-256），交付後可驗證成品
  與交付時的原稿一致。歷史範例 manifest 僅有短版 `content_hash`，沒有
  上述三個全長雜湊欄位；新跑出的 CLI 交付才會帶完整欄位。
- 正式恢復入口 `recover_delivery(manifest_path)`
  （`src/note_filler/recovery.py`）：續跑前探測已持久化 artifact，
  不一致時記 `artifact_missing`／`artifact_integrity_mismatch`，
  狀態轉 `retryable`／`failed`——**絕不自動宣告 delivered**。
  僅可解析 manifest 的 artifact 驗證失敗會追加至 `recovery_history.jsonl`
  與 `recovery_attempts`；相同失敗特徵會去重，成功驗證不追加，manifest
  遺失或損壞時也不追加。此入口不會重新生成或傳送成品。
- 回滾：使用事前備份還原輸入或舊成品；確認隔離目錄中僅有 generated 產物後，
  可移除該次輸出或從備份原稿重跑。`recover_delivery` 不會還原已被覆寫的內容。

## 本機設定與測試

需求：Python ≥ 3.11。

```bash
# 安裝（CI 用 pinned 約束；本機亦可去掉 -c 參數用最新相容版）
python -m pip install -e ".[dev]" -c constraints-pinned.txt

# 預設測試（與 CI 相同，排除需要真實 grok 的整合測試）
python -m pytest tests/ -m "not integration" -v

# 或使用腳本：unit（預設）/ all / integ / check（只收集不執行）
bash scripts/run_tests.sh

# CI 防漏跑閘：校驗 deselected allowlist 與替代覆蓋
python scripts/validate_deselection_ci.py
```

**整合測試**（`@pytest.mark.integration`）包含本機 grok proxy
`http://127.0.0.1:8318/v1`、Twinkle 與公開網址檢查。Grok 測試在 proxy
不可達時 skip；Twinkle 測試未設定 `TWINKLE_HUB_TOKEN` 時 skip；公開網址
測試直接連網，外部服務失敗時可能 fail，整個集合不保證 skip。執行：
`bash scripts/run_tests.sh integ` 或 `python -m pytest tests/ -m integration`；
實際支數以 `python -m pytest tests/ -m integration --collect-only -q` 為準。
CI 中此 job 只在 `workflow_dispatch` 手動觸發時執行。

網頁介面為 `app/server.py`（FastAPI：`/` 上傳表單、`POST /run`、
`GET /export`）；uvicorn 等 ASGI server 未列為相依，需要時自行安裝後
以 `uvicorn app.server:app` 啟動。`NOTE_FILLER_DB` 僅網頁介面用於覆寫法條庫
路徑；CLI 請用 `--db`（預設 `data/law_index.db`）。

## Provider 邊界（repo 內無 secrets）

- **grok（研究層 LLM）**：只連本機 OpenAI 相容 proxy
  `http://127.0.0.1:8318/v1`，model `grok-4.3`。程式內 `api_key`
  為佔位字串 `"x"`；真實憑證由 proxy 端持有，repo 與本檔不含任何 key。
- **twinkle-hub（Level B，立法院議案）**：`https://api.twinkleai.tw/mcp/`，
  token 由環境變數 `TWINKLE_HUB_TOKEN` 或 CLI `--token` 提供；缺省時
  Level B 降級為空結果並在 stderr 警告，Level A 法條仍可用。
  **請勿把 token 寫進任何檔案或命令歷史會留存的位置。**
- **本地法條庫（Level A）**：`data/law_index.db` 入庫快照，完全離線可用。
- **開放網路檢索**（Level C/D）：`ddgs` 搜尋 → `trafilatura` 抓全文
  （絕不存搜尋摘要）；僅在領域判定為 `other`（非法律／行政／考試）時
  加掛，MVP 法律領域不走此路。無網路或無可用結果時來源為空，
  補充段依規則降級 `pending_evidence`。

## 最小端到端範例

以入庫範例筆記跑一次完整流程（需要 grok proxy 在 `127.0.0.1:8318`
運作；否則生成階段會明確失敗而非產出假內容）：

```bash
run_dir=$(mktemp -d)
cp tests/fixtures/real_note.txt "$run_dir/real_note.txt"
python -m note_filler "$run_dir/real_note.txt" -o "$run_dir/output" --format md
```

產生並依序檢視：

1. **original note**：`tests/fixtures/real_note.txt` 為範例原稿；流程讀取其工作複本
   `$run_dir/real_note.txt`，指標寫入工作目錄，原始範例不變。
2. **research suggestions**：pipeline 產生研究問題→缺口清單
   （`parse → domain → questions → gaps`）。
3. **evidence review**：`$run_dir/output/binding_report.json` 逐論點列出
   `source_ids`、`checks`、`binding_status`；`.訂正稿.md` 內 `[^n]`
   註腳對應文末 `[Level X] 標題 | URL | Date | Hash | Evidence`
   來源清單（`Hash` 為來源片段內容 sha1 前 8 碼）。
4. **accepted output**：檢視 `$run_dir/output/real_note.訂正稿.md` 與
   `delivery_manifest.json`，重新計算檔案 SHA-256 比對 `output_content_hash`／
   `input_content_hash`，確認 `status=delivered`；逐段審查 `confidence` 與
   綁定結果後再人工接受。待補證段仍需查證。

想在不連任何 provider 的情況下看成果：直接開啟已入庫的
`output/main-flow-2026-07-24T061023Z/`（含 `.訂正稿.md`、
`delivery_manifest.json`、`run-meta.json`、`verification.json`）；這是上述
雜湊失配的歷史格式樣本，不能作為已驗證交付或接受依據。

## 相關文件

- 設計 spec：`docs/specs/2026-07-15-note-filler-design.md`
- 品質閘／稽核紀錄：`docs/`（含 `docs/audits/50-persona-round-*`）
- 交付回執欄位定義：`src/note_filler/__main__.py` 的
  `write_delivery_receipt`；恢復語意：`src/note_filler/recovery.py`
