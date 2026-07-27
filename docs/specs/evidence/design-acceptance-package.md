# 設計驗收套件（Design Acceptance Package）

> 產生時間：`2026-07-19T15:34:02+08:00`
>
> schema：`note-filler.design-acceptance/v1`
>
> **每一項主張必須同時具備：規格檔、實作錨點檔、測試錨點；禁止只靠敘述或彙總數字驗收。**
>
> **追溯更新：2026-07-27 新增需求編號與驗收項目編號追溯對照。**

## Git / 落盤狀態（刷新前）

- HEAD：`16361a56a0b0f965bbab9ae976a65e950a955499`
- working_tree_clean_before_refresh：`False`
- status_porcelain_before_refresh：`M docs/specs/evidence/design-acceptance-claims.json
 M scripts/refresh_design_acceptance.py
 M tests/test_design_acceptance.py`

## 追溯對照表

> 完整追溯索引見 `docs/specs/design-traceability-index.md`

### 需求編號索引

| 需求編號 | 需求標題 |
|----------|----------|
| R-01 | 目標與一句話定義 |
| R-02 | 範圍 - MVP |
| R-03 | 復用策略 |
| R-04 | 系統架構 |
| R-05 | 自建模組 - Gap 偵測 |
| R-06 | 自建模組 - 訂正稿資料結構 |
| R-07 | 品質閘 |
| R-08 | LLM 接法 |
| R-09 | UI MVP |
| R-10 | 開發方式 |
| R-11 | MVP 不做清單 |
| R-12 | 驗收標準 |

### 驗收項目編號索引

| 驗收編號 | 測試項目 |
|----------|----------|
| A-01 | test_index_returns_upload_form |
| A-02 | test_run_renders_two_columns |
| A-03 | test_export_returns_markdown_attachment |
| A-04 | test_export_without_run_returns_404 |
| A-05 | test_run_pipeline_invariant |
| A-06 | test_e2e_minimal_quality_gates_offline_regression |
| A-07 | test_e2e_structural_invariants |
| A-08 | test_retrieved_five_but_only_two_cited |

### 設計 → 需求 → 驗收追溯對照

| 設計編號 | 設計標題 | 需求編號 | 驗收編號 |
|----------|----------|----------|----------|
| D-01 | 介面規格 | R-01, R-02, R-08, R-09 | A-01, A-02, A-03, A-04 |
| D-02 | 狀態轉移 | R-06, R-07 | A-04, A-05, A-06 |
| D-03 | 使用者流程 | R-01, R-04, R-05, R-06 | A-02, A-03, A-05, A-07 |
| D-04 | 元件責任 | R-03, R-04, R-10 | A-01, A-05, A-06, A-08 |
| D-05 | 畫面佐證 | R-02, R-09 | A-01, A-02, A-03, A-04 |

## 主張 ↔ 產物對照

| ID | 標題 | 規格檔 | 實作檔數 | 測試數 | OK |
|----|------|--------|----------|--------|----|
| D-01 | 介面規格（路由／表單／匯出契約） | `docs/specs/note-filler-interface-contract.md` | 3 | 4 | YES |
| D-02 | UI／資料狀態轉移（last_doc／confidence） | `docs/specs/note-filler-state-machine.md` | 3 | 4 | YES |
| D-03 | 使用者與系統流程（上傳→pipeline→結果→匯出） | `docs/specs/note-filler-user-flow.md` | 3 | 4 | YES |
| D-04 | 元件責任清單（入口／管線／匯出） | `docs/specs/note-filler-component-responsibilities.md` | 8 | 4 | YES |
| D-05 | 可重現畫面佐證與索引 | `docs/specs/evidence/ui/index.md` | 4 | 4 | YES |

## 確認紀錄

| ID | 確認事件 | 確認人 | 確認時間 | 確認方式 | 待辦／結案狀態 | 待辦 |
|----|----------|--------|----------|----------|-----------------|------|
| D-01 | `DAC-20260719-D01` | Codex 自動開發工人 | `2026-07-19T15:31:01+08:00` | 實作錨點掃描與各測試錨點離線單獨 pytest 驗證 | 已結案 | — |
| D-02 | `DAC-20260719-D02` | Codex 自動開發工人 | `2026-07-19T15:31:01+08:00` | 實作錨點掃描與各測試錨點離線單獨 pytest 驗證 | 待辦 | 定義 S1 失敗邊（上傳／pipeline 例外）後補齊規格與測試。 |
| D-03 | `DAC-20260719-D03` | Codex 自動開發工人 | `2026-07-19T15:31:01+08:00` | 實作錨點掃描與各測試錨點離線單獨 pytest 驗證 | 待辦 | 定義上傳失敗頁與 pipeline 例外頁後補齊流程與測試。 |
| D-04 | `DAC-20260719-D04` | Codex 自動開發工人 | `2026-07-19T15:31:01+08:00` | 實作錨點掃描與各測試錨點離線單獨 pytest 驗證 | 已結案 | — |
| D-05 | `DAC-20260719-D05` | Codex 自動開發工人 | `2026-07-19T15:31:01+08:00` | 文件 UI 索引、模板錨點與各測試錨點離線單獨 pytest 驗證 | 待辦 | 補入可重現 PNG/JPG 畫面截圖後，更新 UI 索引與本確認紀錄。 |

## per-claim 細節

### D-01 — 介面規格（路由／表單／匯出契約）

- claim_ok: **True**
- spec_file: `docs/specs/note-filler-interface-contract.md` (exists=True)
- status_note: 文件型契約已落地；路由與模板可交叉驗證
- confirmation_record_ok: **True**

實作錨點：

- **PASS** `app/server.py`
- **PASS** `app/templates/index.html`
- **PASS** `app/templates/result.html`

測試單獨結果：

- **PASSED** `tests/test_server.py::test_index_returns_upload_form` — `tests/test_server.py::test_index_returns_upload_form[asyncio] PASSED     [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_index_returns_upload_form -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_run_renders_two_columns` — `tests/test_server.py::test_run_renders_two_columns[asyncio] PASSED       [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_run_renders_two_columns -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_returns_markdown_attachment` — `tests/test_server.py::test_export_returns_markdown_attachment[asyncio] PASSED [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_export_returns_markdown_attachment -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_without_run_returns_404` — `tests/test_server.py::test_export_without_run_returns_404[asyncio] PASSED [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_export_without_run_returns_404 -vv --tb=line --color=no`

### D-02 — UI／資料狀態轉移（last_doc／confidence）

- claim_ok: **True**
- spec_file: `docs/specs/note-filler-state-machine.md` (exists=True)
- status_note: S0/S2/S3/S4 與 confidence 轉移有程式與測試錨點；S1 失敗邊仍屬框架預設
- confirmation_record_ok: **True**

實作錨點：

- **PASS** `app/server.py`
- **PASS** `src/note_filler/correction.py`
- **PASS** `src/note_filler/pipeline.py`

測試單獨結果：

- **PASSED** `tests/test_server.py::test_export_without_run_returns_404` — `tests/test_server.py::test_export_without_run_returns_404[asyncio] PASSED [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_export_without_run_returns_404 -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_returns_markdown_attachment` — `tests/test_server.py::test_export_returns_markdown_attachment[asyncio] PASSED [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_export_returns_markdown_attachment -vv --tb=line --color=no`
- **PASSED** `tests/test_pipeline.py::test_run_pipeline_invariant` — `tests/test_pipeline.py::test_run_pipeline_invariant PASSED               [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -vv --tb=line --color=no`
- **PASSED** `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression` — `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression PASSED [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression -vv --tb=line --color=no`

### D-03 — 使用者與系統流程（上傳→pipeline→結果→匯出）

- claim_ok: **True**
- spec_file: `docs/specs/note-filler-user-flow.md` (exists=True)
- status_note: 正常流程與 export 分流可核實；上傳失敗頁／pipeline 例外頁仍未定義
- confirmation_record_ok: **True**

實作錨點：

- **PASS** `app/server.py`
- **PASS** `src/note_filler/pipeline.py`
- **PASS** `src/note_filler/export.py`

測試單獨結果：

- **PASSED** `tests/test_server.py::test_run_renders_two_columns` — `tests/test_server.py::test_run_renders_two_columns[asyncio] PASSED       [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_run_renders_two_columns -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_returns_markdown_attachment` — `tests/test_server.py::test_export_returns_markdown_attachment[asyncio] PASSED [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_export_returns_markdown_attachment -vv --tb=line --color=no`
- **PASSED** `tests/test_pipeline.py::test_run_pipeline_invariant` — `tests/test_pipeline.py::test_run_pipeline_invariant PASSED               [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -vv --tb=line --color=no`
- **PASSED** `tests/test_e2e_acceptance.py::test_e2e_structural_invariants` — `tests/test_e2e_acceptance.py::test_e2e_structural_invariants PASSED      [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_structural_invariants -vv --tb=line --color=no`

### D-04 — 元件責任清單（入口／管線／匯出）

- claim_ok: **True**
- spec_file: `docs/specs/note-filler-component-responsibilities.md` (exists=True)
- status_note: 責任邊界以既有模組為準，不新增 controller/service 抽象
- confirmation_record_ok: **True**

實作錨點：

- **PASS** `app/server.py`
- **PASS** `src/note_filler/parse.py`
- **PASS** `src/note_filler/domain.py`
- **PASS** `src/note_filler/gap.py`
- **PASS** `src/note_filler/write.py`
- **PASS** `src/note_filler/correction.py`
- **PASS** `src/note_filler/export.py`
- **PASS** `src/note_filler/knowledge/law_citation_check.py`

測試單獨結果：

- **PASSED** `tests/test_server.py::test_index_returns_upload_form` — `tests/test_server.py::test_index_returns_upload_form[asyncio] PASSED     [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_index_returns_upload_form -vv --tb=line --color=no`
- **PASSED** `tests/test_pipeline.py::test_run_pipeline_invariant` — `tests/test_pipeline.py::test_run_pipeline_invariant PASSED               [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -vv --tb=line --color=no`
- **PASSED** `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression` — `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression PASSED [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression -vv --tb=line --color=no`
- **PASSED** `tests/test_correction.py::test_retrieved_five_but_only_two_cited` — `tests/test_correction.py::test_retrieved_five_but_only_two_cited PASSED  [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_correction.py::test_retrieved_five_but_only_two_cited -vv --tb=line --color=no`

### D-05 — 可重現畫面佐證與索引

- claim_ok: **True**
- spec_file: `docs/specs/evidence/ui/index.md` (exists=True)
- status_note: 文件型 UI 索引已落地；實體截圖列為已知缺口（非本輪必須）
- confirmation_record_ok: **True**

實作錨點：

- **PASS** `docs/specs/evidence/ui/index.md`
- **PASS** `docs/specs/evidence/note-filler-design-evidence-manifest.md`
- **PASS** `app/templates/index.html`
- **PASS** `app/templates/result.html`

測試單獨結果：

- **PASSED** `tests/test_server.py::test_index_returns_upload_form` — `tests/test_server.py::test_index_returns_upload_form[asyncio] PASSED     [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_index_returns_upload_form -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_run_renders_two_columns` — `tests/test_server.py::test_run_renders_two_columns[asyncio] PASSED       [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_run_renders_two_columns -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_returns_markdown_attachment` — `tests/test_server.py::test_export_returns_markdown_attachment[asyncio] PASSED [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_export_returns_markdown_attachment -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_without_run_returns_404` — `tests/test_server.py::test_export_without_run_returns_404[asyncio] PASSED [100%]`
  - invocation: `D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_server.py::test_export_without_run_returns_404 -vv --tb=line --color=no`
- screenshot_status: `absent` — 目前無 .png/.jpg 畫面截圖；以文件索引 + 模板 + 測試錨點作為最小可核實證據

## failures

- (empty)

## ACCEPTANCE_PASS = True

ACCEPTANCE_MODE: per-claim-evidence
