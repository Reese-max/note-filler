# 乾淨環境主流程連續三次執行驗證（2026-07-24）

## 任務

在乾淨環境連續執行主流程至少三次，保存每次成品與日誌，並驗證皆成功產出符合品質閘條件的筆記。

## 執行環境

| 項目 | 值 |
|---|---|
| 工作目錄 | 本 worktree（未 `cd` 他處、未 `git -C` 他 repo） |
| Python | `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8` |
| `PYTHONPATH` | 本 worktree `src` |
| LLM | `http://127.0.0.1:8318/v1` / model `grok-4.3`（執行前 models 端點 HTTP 200） |
| 法條 DB | `data/law_index.db`（存在） |
| Twinkle | `TWINKLE_HUB_TOKEN` 已設定 |
| 入口 | `python -m note_filler` |
| 輸入 | `tests/fixtures/real_note.txt` |

## 執行命令（三次獨立輸出目錄）

```text
python -X utf8 -m note_filler tests/fixtures/real_note.txt \
  -o output/clean-repro-3x-2026-07-24/run-N \
  --db data/law_index.db \
  --format md
```

N = 1、2、3。每次輸出目錄在執行前清空重建，避免殘留污染。

## 執行結果摘要

| Run | Exit | 完成訊號 | 狀態 | 補充 | verified | 成品 bytes | content_hash | 耗時 (s) |
|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 完成 1/1 檔 | delivered | 7 | 3 | 16240 | `53f20577f21d5b9f` | 165.1 |
| 2 | 0 | 完成 1/1 檔 | delivered | 8 | 3 | 19254 | `111f995a7bbe8f06` | 188.5 |
| 3 | 0 | 完成 1/1 檔 | delivered | 8 | 3 | 13915 | `9bd2282ae0ea161a` | 185.5 |

時間戳（UTC）：

| Run | START | END |
|---|---|---|
| 1 | 2026-07-24T08:58:32.2136458Z | 2026-07-24T09:01:17.3013716Z |
| 2 | 2026-07-24T09:01:17.8062874Z | 2026-07-24T09:04:26.3051779Z |
| 3 | 2026-07-24T09:04:26.3992496Z | 2026-07-24T09:07:31.9458066Z |

## 產物與證據路徑

### 每次執行成品（`output/`）

| 路徑 | 角色 |
|---|---|
| [output/clean-repro-3x-2026-07-24/run-1/real_note.訂正稿.md](../output/clean-repro-3x-2026-07-24/run-1/real_note.訂正稿.md) | Run1 筆記成品 |
| [output/clean-repro-3x-2026-07-24/run-1/delivery_manifest.json](../output/clean-repro-3x-2026-07-24/run-1/delivery_manifest.json) | Run1 交付回執 |
| [output/clean-repro-3x-2026-07-24/run-1/run-meta.json](../output/clean-repro-3x-2026-07-24/run-1/run-meta.json) | Run1 執行 meta |
| [output/clean-repro-3x-2026-07-24/run-1/verification.json](../output/clean-repro-3x-2026-07-24/run-1/verification.json) | Run1 機器驗證 |
| [output/clean-repro-3x-2026-07-24/run-2/real_note.訂正稿.md](../output/clean-repro-3x-2026-07-24/run-2/real_note.訂正稿.md) | Run2 筆記成品 |
| [output/clean-repro-3x-2026-07-24/run-2/delivery_manifest.json](../output/clean-repro-3x-2026-07-24/run-2/delivery_manifest.json) | Run2 交付回執 |
| [output/clean-repro-3x-2026-07-24/run-2/run-meta.json](../output/clean-repro-3x-2026-07-24/run-2/run-meta.json) | Run2 執行 meta |
| [output/clean-repro-3x-2026-07-24/run-2/verification.json](../output/clean-repro-3x-2026-07-24/run-2/verification.json) | Run2 機器驗證 |
| [output/clean-repro-3x-2026-07-24/run-3/real_note.訂正稿.md](../output/clean-repro-3x-2026-07-24/run-3/real_note.訂正稿.md) | Run3 筆記成品 |
| [output/clean-repro-3x-2026-07-24/run-3/delivery_manifest.json](../output/clean-repro-3x-2026-07-24/run-3/delivery_manifest.json) | Run3 交付回執 |
| [output/clean-repro-3x-2026-07-24/run-3/run-meta.json](../output/clean-repro-3x-2026-07-24/run-3/run-meta.json) | Run3 執行 meta |
| [output/clean-repro-3x-2026-07-24/run-3/verification.json](../output/clean-repro-3x-2026-07-24/run-3/verification.json) | Run3 機器驗證 |

### 證據副本與彙總（`docs/evidence/`）

| 路徑 | 角色 |
|---|---|
| [docs/evidence/clean-repro-3x-2026-07-24/run-1.log](evidence/clean-repro-3x-2026-07-24/run-1.log) | Run1 日誌 |
| [docs/evidence/clean-repro-3x-2026-07-24/run-2.log](evidence/clean-repro-3x-2026-07-24/run-2.log) | Run2 日誌 |
| [docs/evidence/clean-repro-3x-2026-07-24/run-3.log](evidence/clean-repro-3x-2026-07-24/run-3.log) | Run3 日誌 |
| [docs/evidence/clean-repro-3x-2026-07-24/run1-product.md](evidence/clean-repro-3x-2026-07-24/run1-product.md) | Run1 成品副本 |
| [docs/evidence/clean-repro-3x-2026-07-24/run2-product.md](evidence/clean-repro-3x-2026-07-24/run2-product.md) | Run2 成品副本 |
| [docs/evidence/clean-repro-3x-2026-07-24/run3-product.md](evidence/clean-repro-3x-2026-07-24/run3-product.md) | Run3 成品副本 |
| [docs/evidence/clean-repro-3x-2026-07-24/run1-manifest.json](evidence/clean-repro-3x-2026-07-24/run1-manifest.json) | Run1 manifest 副本 |
| [docs/evidence/clean-repro-3x-2026-07-24/run2-manifest.json](evidence/clean-repro-3x-2026-07-24/run2-manifest.json) | Run2 manifest 副本 |
| [docs/evidence/clean-repro-3x-2026-07-24/run3-manifest.json](evidence/clean-repro-3x-2026-07-24/run3-manifest.json) | Run3 manifest 副本 |
| [docs/evidence/clean-repro-3x-2026-07-24/run1-verification.json](evidence/clean-repro-3x-2026-07-24/run1-verification.json) | Run1 驗證副本 |
| [docs/evidence/clean-repro-3x-2026-07-24/run2-verification.json](evidence/clean-repro-3x-2026-07-24/run2-verification.json) | Run2 驗證副本 |
| [docs/evidence/clean-repro-3x-2026-07-24/run3-verification.json](evidence/clean-repro-3x-2026-07-24/run3-verification.json) | Run3 驗證副本 |
| [docs/evidence/clean-repro-3x-2026-07-24/execution-summary.json](evidence/clean-repro-3x-2026-07-24/execution-summary.json) | 三次執行機器摘要 |
| [docs/evidence/clean-repro-3x-2026-07-24/verification-summary.json](evidence/clean-repro-3x-2026-07-24/verification-summary.json) | 品質閘驗證彙總（`all_ok=true`） |

## 品質閘驗證（三次皆通過）

不依賴「僅 exit code」。每次皆同時檢查：

1. **exit_code=0** 且日誌含 `STATUS=SUCCESS` / `完成 1/1 檔`
2. **非空成品**：`.md` 存在且 `strip()` 後非空
3. **交付回執**：`delivery_manifest.json` 的 `status=delivered`，`content_hash` 非空
4. **hash 對齊**：檔案 sha256 前 16 碼 = manifest `content_hash`
5. **原稿逐字不可變**：輸入四段正文皆原樣出現於成品開頭
6. **無來源 → pending_evidence**：成品可見 `⚠待補證 【待補證】` 與 `pending:gap:*` 追溯
7. **只掛實際引用來源**：正文 `[^n]` 與註腳定義一致；Level A 註腳 URL 為 `law.moj.gov.tw`
8. **法條離線查核路徑**：註腳 Evidence 來自本地 `data/law_index.db` 查核結果（Level A）

| 品質閘 | Run1 | Run2 | Run3 |
|---|---|---|---|
| original_verbatim | PASS | PASS | PASS |
| non_empty_product | PASS | PASS | PASS |
| delivered_manifest | PASS | PASS | PASS |
| hash_aligned | PASS | PASS | PASS |
| footnotes_consistent | PASS | PASS | PASS |
| pending_evidence 標記存在 | PASS（8） | PASS（10） | PASS（10） |
| moj Level A 註腳 | PASS（25） | PASS（30） | PASS（21） |

機器可讀總結：`verification-summary.json` → **`all_ok: true`**。

## 內容差異說明

三次成品 hash 不同、補充段數/大小不同，屬 LLM 生成不確定性預期行為。重現性定義為：

1. 流程穩定完成（不崩潰）
2. 每次落盤非空實際筆記
3. 符合品質閘
4. 有可對照的日誌、manifest、hash

**非**要求三次逐字相同。

## 結論

✅ 乾淨環境連續三次主流程均成功  
✅ 每次均有成品 + 日誌 + manifest + verification 落盤  
✅ 品質閘（原稿不可變、待補證、實際來源、法條離線查核）三次皆成立  

## 範圍聲明

- 未改 `BACKLOG.md`、未自行新增任務
- 未 `pip install` 到全域 Python
- 未弱化既有品質閘邏輯（僅執行既有 CLI）
- integration 標記測試平時跳過；本次走正式 CLI 主流程
- 所有操作僅在本 worktree 內
