# note-filler — 法律/行政/考試筆記自動補齊

讀 `.txt`/`.docx` 筆記，找出知識缺口，由研究層（grok）檢索一手來源後產生
**訂正稿**：保留擷取的原文段落，缺口處以帶來源註腳的補充段補齊。

## 安全合約（先讀這段）

- **以工作副本保護原稿**：筆記解析是**唯讀**的，補齊結果寫成
  `<檔名>.訂正稿.<md|json|docx>`。固定檔名會覆寫既有檔案，甚至可能碰到同批
  另一份輸入；請先複製工作副本，並讓輸出目錄與所有輸入分開，不會覆寫原稿。
- **擷取限制**：TXT 會去除段落首尾空白、合併分段；DOCX 只讀一般段落，
  不含表格、頁首頁尾與原始格式。訂正稿不是原檔的逐字或版面備份。
- **無來源不進正文**：補充段的每一個論點都必須就近標註 `[^n]` 引用到實際
  檢索到的來源。來源不足時，該段降級為 `pending_evidence` 並以
  `【補充】⚠待補證` 標示保留在成品中——不會假裝已查證，也不會混入無依據
  文字充當已定稿內容。
- **法條查核範圍**：只有 `law` 領域額外核對法條；已收錄法規的條號查無對應
  或罰則不符時，段落降為 `pending_evidence`，此查核只降不升。
  `admin`/`exam` 不跑這項查核，未收錄的法規也會跳過，仍需人工確認。
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
- 請保留原稿並使用工作副本；本工具不提供筆記管理或備份。

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
| 原稿旁的 `metrics_history.jsonl` | 生成產物 | 管線追加的品質量測歷史，不受 `-o` 控制 |
| `output/`, `metrics_output/` | 生成產物 | 歷次量測/再現執行的歸檔 |
| `docs/` | 權威文件 | 設計規格、稽核與驗收紀錄 |
| `src/note_filler/`, `app/`, `scripts/`, `tests/` | 權威來源碼 | 實作與測試 |

判斷原則：**輸入與來源碼是權威，輸出是產物**。先保留原檔並以工作副本執行。
同一輸出目錄的 `delivery_manifest.json` 與 `binding_report.json` 只保留
最後一份筆記；多檔處理時，請為每份筆記使用獨立輸出目錄並分別驗收。

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

- **原稿保護**：下方範例先複製原稿，並將輸出與所有輸入隔開。直接對含
  `note.docx`、`note.訂正稿.docx` 的資料夾執行 `--format docx`，可能覆寫
  尚待讀取的輸入；目前沒有碰撞防護。
- **寫入位置**：`-o` 控制訂正稿、來源報告與回執；管線仍在輸入檔旁追加
  `metrics_history.jsonl`，因此輸入目錄需要可寫。任務狀態預設寫到目前工作
  目錄的 `.task_state/`，可用環境變數 `NOTE_FILLER_TASK_STATE` 指定位置。
- **失敗不會留下假象**：交付前硬性檢查成品非空且逐段可追溯，並拒絕外洩
  底層錯誤訊息（traceback/provider error）的內容；失敗時會嘗試寫出
  `status: "failed"` 的 `delivery_manifest.json`；目錄不可寫時回執也可能失敗。
- **續跑與回復**：`.task_state/` 記錄 generation/transmission 階段與錯誤歷程，
  失敗時若累計嘗試已達三次會標記 `exhausted`；CLI 未用這個狀態阻擋生成，
  不能視為執行上限。
  每次手動重跑都會重新生成，CLI 不會自動呼叫 `recover_delivery` 核對舊成品。
  獨立 recovery API 可比對輸入、輸出與傳輸確認的 sha256；不一致時記錄
  `artifact_missing`/`artifact_integrity_mismatch`，並更新回執與恢復歷程。
  檢查通過只代表雜湊一致，不會把狀態升為 delivered。
- **回復原稿**：使用保留的原檔即可。刪除訂正稿及 manifest 不會移除
  `binding_report.json`、量測歷史或任務狀態，也不會還原被覆寫的既有輸出。

完成下方端到端範例後，可手動檢查該筆記的回執（失敗時會寫入恢復歷程）：

```bash
python -X utf8 - "$nf_run/output/delivery_manifest.json" <<'PY'
import json
import sys
from note_filler.recovery import recover_delivery

verdict = recover_delivery(sys.argv[1])
print(json.dumps(verdict.as_dict(), ensure_ascii=False, indent=2))
PY
```

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
bash scripts/run_tests.sh         # 等同上面（unit）
bash scripts/run_tests.sh all     # 含整合測試
bash scripts/run_tests.sh integ   # 只跑整合測試
bash scripts/run_tests.sh check   # 只收集不執行
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
  `data/law_index.db`）；需要含 `law_articles` 資料表的可讀有效索引。
  DB 不存在時 CLI 雖會先警告，實際檢索仍可能拋出 `OperationalError`
  （SQLite 可能先建立空 DB，再因缺少資料表失敗），不保證降級為空結果。
- 本 repo 不含任何 token/金鑰；請只透過環境變數或 CLI 參數注入，
  不要寫入設定檔或文件。

## 離線唯讀導覽

安裝後從 repo 根目錄執行；只讀原稿與既存範例，不呼叫 provider、不產生補齊
產物或任務狀態。這是內容分類導覽；目前 CLI（`python -m note_filler`）沒有
`--dry-run`，一般補齊會寫入前述產物。

```bash
python -X utf8 -B - <<'PY'
from pathlib import Path
from note_filler.parse import parse_note

print("原稿擷取文字（原檔不變；未執行研究）：")
print(parse_note("tests/fixtures/real_note.txt").full_text)
for name in ("sufficient_sources.md", "insufficient_sources.md"):
    print(f"\n既存輸出範例：{name}（非本次研究／非已接受內容）")
    print(Path("tests/fixtures/final_output", name).read_text(encoding="utf-8"))
PY
```

對照下方分類表，區分原稿擷取文字、有來源的 AI 補充及待補證段落。
這些範例不代表你的筆記已完成研究或已獲人工接受。

## 最小端到端範例

前置需求：研究層需要本機 grok proxy（`http://127.0.0.1:8318`，見
「Provider 邊界」）；連不上時 CLI 會以 `status: "failed"` 收場而非產出
delivered 訂正稿。

```bash
# 1. 複製工作副本；原稿、量測歷史、輸出及任務狀態各有明確位置
nf_run="$(mktemp -d)"
cp tests/fixtures/real_note.txt "$nf_run/my_note.txt"

# 2. 執行補齊：研究層檢索來源 → 產生帶證據的補充建議 → 組裝訂正稿
NOTE_FILLER_TASK_STATE="$nf_run/.task_state" \
  python -X utf8 -m note_filler "$nf_run/my_note.txt" -o "$nf_run/output" --format md

# 3. 證據檢視：讀取訂正稿與逐論點報告
cat "$nf_run/output/my_note.訂正稿.md"
cat "$nf_run/output/binding_report.json"
#    - 無標記的段落 = 原稿擷取文字（見擷取限制）
#    - "> 【補充】..." = AI 研究產生的補充段，[^n] 註腳對應文末來源
#    - "> 【補充】⚠待補證 ..." = 來源不足、待審/待補證的段落
#    - "> 追溯：..." = 該段的來源識別碼或原稿段落錨點
#    - 文末來源綁定摘要屬結構檢查；全部通過仍可能含 pending_evidence

# 4. 技術送達：核對該筆記回執的路徑、status 與 output_content_hash
cat "$nf_run/output/delivery_manifest.json"
#    delivered 表示已產出及送達，雜湊可用上方 recovery 範例核對
#    原稿副本旁仍有 metrics_history.jsonl；所有寫入都留在 nf_run 內
```

**5. 人工接受**：逐段閱讀註腳原文、來源日期、衝突與待補證原因；只有人工
查核並接受的內容才整理進另外保留的正式筆記。`pending_evidence` 保留待審，
無來源不進正文；目前沒有持久化的 accepted 狀態，也沒有自動接受指令。

也有網頁介面可選（需另行安裝 uvicorn：`pip install uvicorn`）：
`uvicorn app.server:app` 後於 `/` 上傳筆記、
`/export` 下載 `correction.md`（同一份安全合約：原稿不動、無來源待補證）。

## 內容分類速查

| 你在成品看到的 | 意義 |
|---|---|
| 無 `【補充】` 前綴的段落 | 原稿擷取文字；權威輸入仍是保留的原檔 |
| `> 【補充】...` + `[^n]` | AI 補齊且有來源佐證（`verified`） |
| `> 【補充】⚠待補證 ...` | 來源不足或降級，待審（`pending_evidence`） |
| `> ⚠️衝突告警` | 來源間表述不一致，需人工判讀 |
| `delivery_manifest.json` `status` | `delivered` 是技術送達，仍可含 `pending_evidence`；`failed` 表示失敗 |
| 人工接受後的正式筆記 | 人工查核及取捨後另存；系統未記錄人工接受狀態 |

## 深入文件

- 設計規格：`docs/specs/2026-07-15-note-filler-design.md`
- 介面合約：`docs/specs/note-filler-interface-contract.md`
- 使用者流程與降級路徑：`docs/specs/note-filler-user-flow.md`
- 50-persona 稽核：`docs/audits/`
- 測試指南：`docs/testing-guide.md`
