# 設計驗收套件（Design Acceptance Package）

> 產生時間：`2026-07-19T08:12:54+08:00`
>
> schema：`note-filler.design-acceptance/v1`
>
> **每一項主張必須同時具備：規格檔、實作錨點檔、測試錨點；禁止只靠敘述或彙總數字驗收。**

## Git / 落盤狀態（刷新前）

- HEAD：`6a22a0de9d88772c5dc92f4a9b2c6afd609df1de`
- working_tree_clean_before_refresh：`False`
- status_porcelain_before_refresh：`M tests/test_deselection_guard.py
?? docs/design-acceptance-2026-07-19.md
?? docs/specs/evidence/design-acceptance-claims.json
?? docs/specs/evidence/design-acceptance-package.json
?? docs/specs/evidence/design-acceptance-package.md
?? scripts/refresh_design_acceptance.py
?? tests/test_design_acceptance.py`

## 主張 ↔ 產物對照

| ID | 標題 | 規格檔 | 實作檔數 | 測試數 | OK |
|----|------|--------|----------|--------|----|
| D-01 | 介面規格（路由／表單／匯出契約） | `docs/specs/note-filler-interface-contract.md` | 3 | 4 | YES |
| D-02 | UI／資料狀態轉移（last_doc／confidence） | `docs/specs/note-filler-state-machine.md` | 3 | 4 | YES |
| D-03 | 使用者與系統流程（上傳→pipeline→結果→匯出） | `docs/specs/note-filler-user-flow.md` | 3 | 4 | YES |
| D-04 | 元件責任清單（入口／管線／匯出） | `docs/specs/note-filler-component-responsibilities.md` | 8 | 4 | YES |
| D-05 | 可重現畫面佐證與索引 | `docs/specs/evidence/ui/index.md` | 4 | 4 | YES |

## per-claim 細節

### D-01 — 介面規格（路由／表單／匯出契約）

- claim_ok: **True**
- spec_file: `docs/specs/note-filler-interface-contract.md` (exists=True)
- status_note: 文件型契約已落地；路由與模板可交叉驗證

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
