# 設計驗收輸出（可機器檢查）— 2026-07-19

> 任務：重新產出可機器檢查的設計驗收輸出，並確認工作樹乾淨、變更已落盤、
> 每一項主張都能在檔案與輸出中逐一對應。

## 1. 主張 ↔ 可見產物

| 主張 | 可見產物 |
|------|----------|
| 設計主張索引（source of truth） | [`docs/specs/evidence/design-acceptance-claims.json`](specs/evidence/design-acceptance-claims.json) |
| 機器可讀驗收套件 | [`docs/specs/evidence/design-acceptance-package.json`](specs/evidence/design-acceptance-package.json) |
| 人類可讀驗收套件 | [`docs/specs/evidence/design-acceptance-package.md`](specs/evidence/design-acceptance-package.md) |
| 刷新腳本 | [`scripts/refresh_design_acceptance.py`](../scripts/refresh_design_acceptance.py) |
| 結構／錨點驗收測試 | [`tests/test_design_acceptance.py`](../tests/test_design_acceptance.py) |
| 既有設計規格 D-01 | [`docs/specs/note-filler-interface-contract.md`](specs/note-filler-interface-contract.md) |
| 既有設計規格 D-02 | [`docs/specs/note-filler-state-machine.md`](specs/note-filler-state-machine.md) |
| 既有設計規格 D-03 | [`docs/specs/note-filler-user-flow.md`](specs/note-filler-user-flow.md) |
| 既有設計規格 D-04 | [`docs/specs/note-filler-component-responsibilities.md`](specs/note-filler-component-responsibilities.md) |
| 既有設計規格 D-05 | [`docs/specs/evidence/ui/index.md`](specs/evidence/ui/index.md) |
| Manifest | [`docs/specs/evidence/note-filler-design-evidence-manifest.md`](specs/evidence/note-filler-design-evidence-manifest.md) |
| 缺口對照 | [`docs/design-evidence-gap-map-2026-07-19.md`](design-evidence-gap-map-2026-07-19.md) |

## 2. 套件 schema

```text
schema = note-filler.design-acceptance/v1
claim_ids[5] = D-01..D-05
per_claim[].{spec_file, impl_anchors[], test_individual_results[]}
per_claim[].confirmation_record{event_id, confirmed_by, confirmed_at, method, resolution_status, todo}
claim_to_artifact_map[]
failures[]
git.head / working_tree_clean_before_refresh
git.validation_baseline{commit, source} (reachability reference only)
acceptance_mode = per-claim-evidence
```

禁止僅以「文件已存在」或計數摘要驗收；必須有 per-claim 錨點與實跑結果。

## 3. 本輪實測

- generated_at: `2026-09-16T15:52:26+08:00`
- HEAD（刷新前）: `b58d1324bac1276170d53342aafbc4158b285163`
- working_tree_clean_before_refresh: `False`
- acceptance_pass: **True**
- unique offline test anchors: 11
- failures: 0

### Git 驗證基準（非歷史實測 HEAD）

- validation_baseline.commit：`1df674dd32d64c68f4e8a9bfa433665c042d0c61`
- 來源：PR #8 squash commit on main; reachability reference only
- `git.head` 與 generated_at、工作樹狀態、測試結果保留歷史實測觀測；驗證基準只供 Git 可達性檢查，不表示曾在該基準執行測試或兩個工作樹相同。
- 完整 single-branch clone 必須確認基準為 HEAD 的祖先；shallow clone 若歷史截斷，明示 ancestry 未驗證，仍檢查套件與目前檔案錨點。完整可達性驗收須用完整歷史，測試不自動 fetch。

### 逐項 claim

| ID | OK | 規格 | 測試全部 PASSED |
|----|----|------|-----------------|
| D-01 | True | `docs/specs/note-filler-interface-contract.md` | True |
| D-02 | True | `docs/specs/note-filler-state-machine.md` | True |
| D-03 | True | `docs/specs/note-filler-user-flow.md` | True |
| D-04 | True | `docs/specs/note-filler-component-responsibilities.md` | True |
| D-05 | True | `docs/specs/evidence/ui/index.md` | True |

## 4. 確認紀錄

每一筆確認事件均保留確認人、時間、方式與待辦／結案狀態；`claim_ok` 只表示現有證據錨點通過，不會覆寫待辦。

| ID | 確認事件 | 確認人 | 確認時間 | 確認方式 | 待辦／結案狀態 | 待辦 |
|----|----------|--------|----------|----------|-----------------|------|
| D-01 | `DAC-20260719-D01` | Codex 自動開發工人 | `2026-07-19T15:31:01+08:00` | 實作錨點掃描與各測試錨點離線單獨 pytest 驗證 | 已結案 | — |
| D-02 | `DAC-20260719-D02` | Codex 自動開發工人 | `2026-07-19T15:31:01+08:00` | 實作錨點掃描與各測試錨點離線單獨 pytest 驗證 | 待辦 | 定義 S1 失敗邊（上傳／pipeline 例外）後補齊規格與測試。 |
| D-03 | `DAC-20260719-D03` | Codex 自動開發工人 | `2026-07-19T15:31:01+08:00` | 實作錨點掃描與各測試錨點離線單獨 pytest 驗證 | 待辦 | 定義上傳失敗頁與 pipeline 例外頁後補齊流程與測試。 |
| D-04 | `DAC-20260719-D04` | Codex 自動開發工人 | `2026-07-19T15:31:01+08:00` | 實作錨點掃描與各測試錨點離線單獨 pytest 驗證 | 已結案 | — |
| D-05 | `DAC-20260719-D05` | Codex 自動開發工人 | `2026-07-19T15:31:01+08:00` | 文件 UI 索引、模板錨點與各測試錨點離線單獨 pytest 驗證 | 待辦 | 補入可重現 PNG/JPG 畫面截圖後，更新 UI 索引與本確認紀錄。 |

### 重現指令

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
& $py -X utf8 scripts/refresh_design_acceptance.py
& $py -X utf8 -m pytest tests/test_design_acceptance.py -vv --tb=short --color=no
& $py -X utf8 -m pytest -m "not integration" -q --color=no --tb=line
git status --porcelain   # 提交後應為空
```

## 5. 品質閘未弱化

| 硬約束 | 狀態 |
|--------|------|
| 原稿逐字不可變 | 未改主程式語意；由 e2e/pipeline 錨點鎖定 |
| 無來源/【待補證】→pending_evidence | 未改主程式語意；由 e2e/pipeline 錨點鎖定 |
| 只掛實際引用來源 | 未改主程式語意；由 e2e/pipeline 錨點鎖定 |
| 法條引用須通過離線查核 | 未改主程式語意；由 e2e/pipeline 錨點鎖定 |
| integration 平時跳過 | 維持；本套件只跑非 integration 錨點 |

## 6. 已知限制

- D-05 實體截圖（png/jpg）仍缺；套件以 `screenshot_status=absent` 明示，
  不以截圖存在作為本輪通過條件。
- 刷新完成後工作樹會含新產物，必須 `git add -A && git commit` 後再驗 `git status --porcelain` 為空。

## 7. 結論

1. 設計驗收輸出 schema=`note-filler.design-acceptance/v1`，mode=`per-claim-evidence`。
2. D-01..D-05 每一項皆對到規格檔、實作錨點與單獨測試結果。
3. ACCEPTANCE_PASS=True（以 package JSON 為準）。
