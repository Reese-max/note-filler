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
claim_to_artifact_map[]
failures[]
git.head / working_tree_clean_before_refresh
acceptance_mode = per-claim-evidence
```

禁止僅以「文件已存在」或計數摘要驗收；必須有 per-claim 錨點與實跑結果。

## 3. 本輪實測

- generated_at: `2026-07-19T08:12:54+08:00`
- HEAD（刷新前）: `6a22a0de9d88772c5dc92f4a9b2c6afd609df1de`
- working_tree_clean_before_refresh: `False`
- acceptance_pass: **True**
- unique offline test anchors: 8
- failures: 0

### 逐項 claim

| ID | OK | 規格 | 測試全部 PASSED |
|----|----|------|-----------------|
| D-01 | True | `docs/specs/note-filler-interface-contract.md` | True |
| D-02 | True | `docs/specs/note-filler-state-machine.md` | True |
| D-03 | True | `docs/specs/note-filler-user-flow.md` | True |
| D-04 | True | `docs/specs/note-filler-component-responsibilities.md` | True |
| D-05 | True | `docs/specs/evidence/ui/index.md` | True |

### 重現指令

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
& $py -X utf8 scripts/refresh_design_acceptance.py
& $py -X utf8 -m pytest tests/test_design_acceptance.py -vv --tb=short --color=no
& $py -X utf8 -m pytest -m "not integration" -q --color=no --tb=line
git status --porcelain   # 提交後應為空
```

## 4. 品質閘未弱化

| 硬約束 | 狀態 |
|--------|------|
| 原稿逐字不可變 | 未改主程式語意；由 e2e/pipeline 錨點鎖定 |
| 無來源/【待補證】→pending_evidence | 未改主程式語意；由 e2e/pipeline 錨點鎖定 |
| 只掛實際引用來源 | 未改主程式語意；由 e2e/pipeline 錨點鎖定 |
| 法條引用須通過離線查核 | 未改主程式語意；由 e2e/pipeline 錨點鎖定 |
| integration 平時跳過 | 維持；本套件只跑非 integration 錨點 |

## 5. 已知限制

- D-05 實體截圖（png/jpg）仍缺；套件以 `screenshot_status=absent` 明示，
  不以截圖存在作為本輪通過條件。
- 刷新完成後工作樹會含新產物，必須 `git add -A && git commit` 後再驗 `git status --porcelain` 為空。

## 6. 本輪閘門實跑（提交前）

| 命令 | 結果 |
|------|------|
| `scripts/refresh_design_acceptance.py` | `ACCEPTANCE_PASS=True` `FAILURES=0` `CLAIM_IDS=D-01..D-05` |
| `pytest tests/test_design_acceptance.py -vv` | `4 passed` |
| `pytest tests/test_deselection_guard.py::test_integration_allowlist_is_stable` | `1 passed`（counts 更新為 143/135/8） |
| `pytest -m "not integration" -q` | `135 passed, 8 deselected` |

> 彙總 `135 passed, 8 deselected` 僅作上下文；設計驗收以 `design-acceptance-package.json` 的 per-claim 欄位為準。

## 7. 結論

1. 設計驗收輸出 schema=`note-filler.design-acceptance/v1`，mode=`per-claim-evidence`。
2. D-01..D-05 每一項皆對到規格檔、實作錨點與單獨測試結果（見 package `claim_to_artifact_map`）。
3. ACCEPTANCE_PASS=True（以 package JSON 為準）。
4. 提交後以 `git status --porcelain` 必須為空，證明變更已落盤且工作樹乾淨。
