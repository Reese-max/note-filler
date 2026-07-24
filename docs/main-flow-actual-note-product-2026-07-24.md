# 主流程實際筆記成品執行報告（2026-07-24）

## 任務

執行既有主流程生成至少一份實際筆記成品，保存產出檔案及完整執行日誌，並驗證檔案存在且正文非空白。

## 執行環境

| 項目 | 值 |
|---|---|
| 工作目錄 | 本 worktree（未 `cd` 他處、未 `git -C` 他 repo） |
| Python | `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8` |
| LLM | `http://127.0.0.1:8318/v1` / model `grok-4.3` |
| 法條 DB | `data/law_index.db`（存在） |
| Twinkle token | 已設定（環境變數） |
| 入口 | `python -m note_filler`（`src/note_filler/__main__.py`） |

## 執行命令

```text
python -X utf8 -m note_filler tests/fixtures/real_note.txt \
  -o output/main-flow-2026-07-24 \
  --db data/law_index.db \
  --format md
```

- 開始：2026-07-24T11:04:09+08:00
- 結束：2026-07-24T11:08:09+08:00
- **exit_code=0**

## 產出清單（可追溯路徑）

| 檔案 | 角色 | 驗證 |
|---|---|---|
| [output/main-flow-2026-07-24/real_note.訂正稿.md](../output/main-flow-2026-07-24/real_note.訂正稿.md) | 實際筆記成品（markdown） | 存在、7269 bytes、3187 字元、正文非空白 |
| [output/main-flow-2026-07-24/delivery_manifest.json](../output/main-flow-2026-07-24/delivery_manifest.json) | CLI 交付回執 | `status=delivered`、`content_hash=be7dede59bf5bb90`、supplements=8、verified=3 |
| [docs/evidence/main-flow-2026-07-24/execution.log](evidence/main-flow-2026-07-24/execution.log) | 完整執行日誌 | 含命令、時間、exit_code、stdout、驗證結果 |
| [docs/evidence/main-flow-2026-07-24/run-meta.txt](evidence/main-flow-2026-07-24/run-meta.txt) | 執行 meta | 環境與參數快照 |
| [docs/evidence/main-flow-2026-07-24/verification.json](evidence/main-flow-2026-07-24/verification.json) | 機器可讀驗證結果 | `ok=true`、`errors=[]` |

## 成品內容抽樣（直接可對照檔案）

原稿段落（逐字保留於成品開頭，來源 `tests/fixtures/real_note.txt`）：

- 標題：`行政法重點筆記 — 行政處分`
- 含 `行政程序法第92條` 定義段、種類段、救濟途徑段

補充與來源（成品內可見，非摘要臆測）：

- 補充段 8 則（含 `【待補證】` pending_evidence 與有 `[^n]` 引用之 verified 段）
- 註腳區塊 `[^1]`…`[^7]` 掛 Level A 法條來源（行政程序法／行政訴訟法），含 URL 與 Date
- delivery_manifest：`supplements=8`、`verified=3`

內容雜湊對齊：

- 檔案正文 `sha256` 前 16 碼：`be7dede59bf5bb90`
- manifest `content_hash`：`be7dede59bf5bb90`（一致）

## 驗證步驟與結果

以同一 venv Python 讀檔驗證（結果寫入 `verification.json`）：

1. `output/main-flow-2026-07-24/*.md` 存在  
2. 正文 `strip()` 後非空  
3. `delivery_manifest.json` 存在且 `status == "delivered"`  
4. `content_hash` 非空且與正文 hash 前 16 碼一致  
5. `execution.log` / `run-meta.txt` 存在且非空  

**結論：全部通過（verification.ok=true）。**

## 品質閘（本次未弱化）

本次僅**執行**既有 CLI 主流程，未修改品質閘邏輯：

- 原稿逐字不可變（成品保留原文段）
- 無來源／僅【待補證】→ pending_evidence（成品可見 `⚠待補證 【待補證】`）
- 只掛實際引用來源（註腳對應正文 `[^n]`）
- 法條引用走離線 DB 查核路徑（Level A 來源 URL 為 law.moj.gov.tw）

## 範圍聲明

- 未改 `BACKLOG.md` / 未新增任務
- 未 `pip install` 到全域 Python
- integration 標記測試平時跳過；本次走正式 CLI 主流程而非 pytest integration 套件
