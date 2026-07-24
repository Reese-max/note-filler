# 主流程實際筆記成品執行報告（2026-07-24 最新）

## 任務

在既有主流程中執行一次真實筆記生成，將非空白成品筆記、輸入來源、執行命令、時間戳與執行日誌保存為可驗證產物。

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
  -o output/main-flow-2026-07-24T061023Z \
  --db data/law_index.db \
  --format md
```

- 開始：2026-07-24T06:10:23.122176+00:00（UTC）
- 結束：2026-07-24T06:13:29.644272+00:00（UTC）
- 耗時：186.5 秒
- **exit_code=0**

## 產出清單（可追溯路徑）

| 檔案 | 角色 | 驗證 |
|---|---|---|
| [output/main-flow-2026-07-24T061023Z/real_note.訂正稿.md](../output/main-flow-2026-07-24T061023Z/real_note.訂正稿.md) | 實際筆記成品（markdown） | 存在、8691 bytes、4197 字元、正文非空白 |
| [output/main-flow-2026-07-24T061023Z/delivery_manifest.json](../output/main-flow-2026-07-24T061023Z/delivery_manifest.json) | CLI 交付回執 | `status=delivered`、`content_hash=348d48b4729d5aa4`、supplements=8、verified=4 |
| [output/main-flow-2026-07-24T061023Z/run-meta.json](../output/main-flow-2026-07-24T061023Z/run-meta.json) | 執行 meta（環境參數、時間戳、命令） | 存在且完整 |
| [output/main-flow-2026-07-24T061023Z/verification.json](../output/main-flow-2026-07-24T061023Z/verification.json) | 機器可讀驗證結果 | `ok=true`、`errors=[]` |
| [scripts/_run_main_flow_evidence.py](../scripts/_run_main_flow_evidence.py) | 本次執行腳本（可重跑） | 存在 |

## 成品內容抽樣（直接可對照檔案）

輸入來源（逐字保留於成品開頭）：

| 原稿段落 | 來源 | 成品內保留 |
|---|---|---|
| 標題：`行政法重點筆記 — 行政處分` | `tests/fixtures/real_note.txt` | 是 |
| 一、行政處分之定義（行政程序法第92條…） | 同上 | 是 |
| 二、行政處分之種類 | 同上 | 是 |
| 三、救濟途徑 | 同上 | 是 |

補充與來源：

- 補充段 8 則：其中 2 則為 `⚠待補證 【待補證】`（pending_evidence），6 則有 `[^n]` 引用
- 註腳區塊 `[^1]`…`[^10]` 掛 Level A 法條來源（行政程序法／訴願法／行政訴訟法），含 URL 與 Date
- `delivery_manifest`：`supplements=8`、`verified=4`

內容雜湊對齊：

- 檔案正文 `sha256` 前 16 碼：`348d48b4729d5aa4`
- manifest `content_hash`：`348d48b4729d5aa4`（一致）

## 驗證步驟與結果

以 `verification.json` 為機器可讀驗證源，全部通過：

1. `output/main-flow-2026-07-24T061023Z/*.md` 存在 → **PASS**
2. 正文 `strip()` 後非空（4197 字元） → **PASS**
3. `delivery_manifest.json` 存在且 `status == "delivered"` → **PASS**
4. `content_hash` 非空且與正文 hash 前 16 碼一致（`348d48b4729d5aa4`） → **PASS**
5. `run-meta.json` / `verification.json` 存在且非空 → **PASS**

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
- 所有操作均在本 worktree repo 內完成
