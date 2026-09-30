# note-filler — 法律/行政/考試筆記自動補齊

讀 `.txt`/`.docx` 筆記，找出知識缺口，由研究層（grok）檢索一手來源後產生
**訂正稿**：原稿逐字保留，缺口處以帶來源註腳的補充段補齊。

## 安全合約（先讀這段）

- **原稿不可變**：整個流程對輸入檔是**唯讀**的——工具只讀取原稿，絕不會
  覆寫、修改或更動它。補齊結果一律寫成獨立新檔 `<檔名>.訂正稿.<md|json|docx>`。
- **無來源不進正文**：補充段的每一個論點都必須就近標註 `[^n]` 引用到實際
  檢索到的來源。來源不足時，該段降級為 `pending_evidence` 並以
  `【補充】⚠待補證` 標示保留在成品中——不會假裝已查證，也不會混入無依據
  文字充當已定稿內容。
- **降級只降不升**：法條引用若在離線法條庫查無對應或罰則不符，段落降為
  `pending_evidence`；系統絕不把待補證內容升級成 `verified`。
- **可追溯**：每個補充段附 `> 追溯：` 行與來源清單，文末有參考來源區塊與
  來源綁定摘要；機器可讀的回執見 `delivery_manifest.json` 與
  `binding_report.json`。

## 用途與非用途

**用途**

- 法律、行政、考試準備筆記的知識缺口補齊（領域：`law`/`admin`/`exam`；
  其他領域 `other` 只掛開放網路來源）。
- 以一手來源（法條原文、立法院議案文件、開放網路文件）為補充段舉證。
- 產生可追溯、可審閱的訂正稿（Markdown / JSON / DOCX）。

**非用途**

- 不是法律意見或法律建議；產出內容仍需人工判讀，尤其標示 `⚠待補證` 或
  `⚠️衝突告警` 的段落。
- 不取代法規原文與官方公告；來源層級與日期都標在成品中，請以官方發布為準。
- 不會修改你的原稿，也不是筆記管理工具。

## 目錄與產物權威性

| 路徑 | 性質 | 說明 |
|---|---|---|
| 你的筆記檔（`.txt`/`.docx`） | **權威輸入** | 原稿，工具只讀不寫 |
| `data/law_index.db` | **權威輸入** | 離線法條索引庫（Level A 來源） |
| `tests/fixtures/` | 權威輸入 | 測試用範例筆記 |
| `<檔名>.訂正稿.md/.json/.docx` | **生成產物** | 補齊結果；刪掉重跑即可再生 |
| `delivery_manifest.json` | 生成產物 | 交付回執：狀態、來回檔案 sha256、補充/verified 計數 |
| `binding_report.json` | 生成產物 | 逐論點來源綁定驗證報告 |
| `.task_state/` | 生成產物 | 任務狀態與重試歷程（已 gitignore） |
| `output/`, `metrics_output/` | 生成產物 | 歷次量測/再現執行的歸檔 |
| `docs/` | 權威文件 | 設計規格、稽核與驗收紀錄 |
| `src/note_filler/`, `app/`, `scripts/`, `tests/` | 權威來源碼 | 實作與測試 |

判斷原則：**輸入與來源碼是權威，輸出是產物**。產物可刪可重建；權威輸入
永不會被本工具覆寫。

## 來源與證據檢視（provenance）

每個來源攜帶固定欄位：`id`、`title`、`url`、`level`、`content`、
`fetched_date`（檢索日）、`doc_date`（文件自身日期）、`distance`（相關性距離）。

來源層級：

- **Level A**：離線法條庫（`data/law_index.db`），法條原文，最優先。
- **Level B**：twinkle-hub 立法院議案文件（需 `TWINKLE_HUB_TOKEN`）。
- **Level C/D**：開放網路來源，僅 `other` 領域加掛。

在成品 Markdown 中檢視證據的方式：

- `[^n]` 行內註腳 → 文末 `[^n]: [Level X] 標題 | URL | Date | Hash | Evidence: 原文摘錄`。
- `> 追溯：` 行 → 該段對應的 `original_input`（原稿段落）或 `source` /
  `processing_record` 識別碼。
- `> **來源清單**`、`> **來源比較**`、`> **差異分析**`、`> **適用條件**`、
  `> **延伸閱讀**` → 每個論點的舉證結構。
- `delivery_manifest.json` → 交付狀態、輸入/輸出檔 sha256 雜湊、
  `delivery_status`（含逐段 `confidence`/`has_sources`/`degraded`）、
  `polaris_metrics` 品質指標。
- `binding_report.json` → 逐論點的 `binding_status`（pass/fail/
  pending_evidence）與 `source_ids` 對應。
- `--format json` → `segments[]` 內含 `type`、`confidence`、`source_id`/
  `source_ids`、`traceability`、`citation_spans`、完整 `sources` 物件。

## 原稿保護與回復

- **不會覆寫原稿**：輸出檔名固定為 `<檔名>.訂正稿.<副檔名>`，與輸入檔名
  不同；加 `-o 輸出夾` 可把所有產物集中到獨立目錄，原稿所在資料夾完全
  不受影響。
- **失敗不會留下假象**：交付前硬性檢查成品非空且逐段可追溯，並拒絕外洩
  底層錯誤訊息（traceback/provider error）的內容；失敗會寫
  `status: "failed"` 的 `delivery_manifest.json`。
- **續跑與回復**：`.task_state/` 記錄每個任務的階段
  （generation/transmission）、累加的嘗試歷程（上限 3 次，之後
  exhausted 不再自動重試）與錯誤原因。`recovery` 模組在續跑前比對
  manifest 中的 sha256 雜湊：檔案仍在且雜湊一致才可視為已交付；不一致
  則標記 `artifact_missing`/`artifact_integrity_mismatch`，絕不誤報完成。
- **回滾**：因為原稿從未被更動，刪除生成的 `*.訂正稿.*` 與 manifest 即
  回到執行前狀態；重跑即可再生產物。

## 安裝與測試

需求：Python ≥ 3.11。

```bash
# 釘定版本安裝（對齊 CI 的 test-pinned 工作）
python -m pip install -e ".[dev]" -c constraints-pinned.txt

# 或安裝最新相容版本（對齊 CI 的 test-latest 工作）
python -m pip install -e ".[dev]"
```

測試：

```bash
# 離線測試（預設；不需要 grok 或任何外部服務）
python -m pytest tests/ -m "not integration" -v

# 或透過腳本
./scripts/run_tests.sh         # 等同上面（unit）
./scripts/run_tests.sh all     # 含整合測試
./scripts/run_tests.sh integ   # 只跑整合測試
./scripts/run_tests.sh check   # 只收集不執行
```

整合測試（`@pytest.mark.integration`）需要本機 grok proxy
`http://127.0.0.1:8318`；連不上時會 skip 而非 fail。

## Provider 邊界（無機密）

- **grok（研究層 LLM）**：`GrokClient` 走 OpenAI 相容端點
  `http://127.0.0.1:8318/v1`（本機 proxy），模型 `grok-4.3`；程式碼內的
  `api_key` 是佔位字串，真正的驗證由 proxy 負責。
- **twinkle-hub（Level B 來源）**：`TwinkleClient` 讀環境變數
  `TWINKLE_HUB_TOKEN`（或 CLI `--token`）。未提供時啟動即警告，Level B
  降級為空結果——Level A 法條仍可用，相關補充段自然落入待補證。
- **法條庫（Level A）**：`LawLookup` 讀 `--db` 指定路徑（預設
  `data/law_index.db`）；DB 不存在時警告並查無結果。
- 本 repo 不含任何 token/金鑰；請只透過環境變數或 CLI 參數注入，
  不要寫入設定檔或文件。

## 最小端到端範例

前置需求：研究層需要本機 grok proxy（`http://127.0.0.1:8318`，見
「Provider 邊界」）；連不上時 CLI 會以 `status: "failed"` 收場而非產出
delivered 訂正稿。

```bash
# 1. 準備原稿（或用 tests/fixtures/real_note.txt）
cp tests/fixtures/real_note.txt /tmp/my_note.txt

# 2. 執行補齊：研究層檢索來源 → 產生帶證據的補充建議 → 組裝訂正稿
python -m note_filler /tmp/my_note.txt -o /tmp/nf-out --format md

# 3. 證據檢視：打開 /tmp/nf-out/my_note.訂正稿.md
#    - 無標記的段落 = 原稿原文（逐字保留）
#    - "> 【補充】..." = AI 研究產生的補充段，[^n] 註腳對應文末來源
#    - "> 【補充】⚠待補證 ..." = 來源不足、待審/待補證的段落
#    - "> 追溯：..." = 該段的來源識別碼或原稿段落錨點
#    - 文末 "來源綁定：全部通過 ✓ / 有綁定問題 ✗" 為整體驗收

# 4. 機器回執：cat /tmp/nf-out/delivery_manifest.json
#    status=delivered，且 output_content_hash 為輸出檔的完整 sha256，
#    可用於核對到手成品與回執一致才算接受交付
```

也有網頁介面可選（需另行安裝 uvicorn：`pip install uvicorn`）：
`uvicorn app.server:app` 後於 `/` 上傳筆記、
`/export` 下載 `correction.md`（同一份安全合約：原稿不動、無來源待補證）。

## 內容分類速查

| 你在成品看到的 | 意義 |
|---|---|
| 無 `【補充】` 前綴的段落 | 原稿原文（authoritative） |
| `> 【補充】...` + `[^n]` | AI 補齊且有來源佐證（`verified`） |
| `> 【補充】⚠待補證 ...` | 來源不足或降級，待審（`pending_evidence`） |
| `> ⚠️衝突告警` | 來源間表述不一致，需人工判讀 |
| `delivery_manifest.json` `status` | `delivered` 才算最終接受；`failed` 代表未完成 |

## 深入文件

- 設計規格：`docs/specs/2026-07-15-note-filler-design.md`
- 介面合約：`docs/specs/note-filler-interface-contract.md`
- 使用者流程與降級路徑：`docs/specs/note-filler-user-flow.md`
- 50-persona 稽核：`docs/audits/`
- 測試指南：`docs/testing-guide.md`
