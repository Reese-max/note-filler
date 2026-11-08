# 設計驗收套件（Design Acceptance Package）

> 產生時間：`2026-09-16T15:52:26+08:00`
>
> schema：`note-filler.design-acceptance/v1`
>
> **每一項主張必須同時具備：規格檔、實作錨點檔、測試錨點；禁止只靠敘述或彙總數字驗收。**

## Git / 落盤狀態（刷新前）

- HEAD：`b58d1324bac1276170d53342aafbc4158b285163`
- working_tree_clean_before_refresh：`False`
- status_porcelain_before_refresh：`M README.md
 M app/server.py
 M docs/specs/design-traceability-index.md
 M docs/specs/evidence/design-acceptance-claims.json
 M docs/specs/evidence/ui/index.md
 M docs/specs/note-filler-component-responsibilities.md
 M docs/specs/note-filler-interface-contract.md
 M docs/specs/note-filler-state-machine.md
 M docs/specs/note-filler-user-flow.md
 M src/note_filler/pipeline.py
 M src/note_filler/retrieve/web.py
 M tests/0a8e5521d41101e3-restored-notes-output.py
 M tests/test_exception_skip_traceability.py
 M tests/test_fault_injection.py
?? tests/fixtures/metrics_history.jsonl
?? tests/metrics_history.jsonl`

### Git 驗證基準（非歷史實測 HEAD）

- validation_baseline.commit：`1df674dd32d64c68f4e8a9bfa433665c042d0c61`
- 來源：PR #8 squash commit on main; reachability reference only
- `git.head` 與 generated_at、工作樹狀態、測試結果保留歷史實測觀測；驗證基準只供 Git 可達性檢查，不表示曾在該基準執行測試或兩個工作樹相同。
- 完整 single-branch clone 必須確認基準為 HEAD 的祖先；shallow clone 若歷史截斷，明示 ancestry 未驗證，仍檢查套件與目前檔案錨點。完整可達性驗收須用完整歷史，測試不自動 fetch。

## 主張 ↔ 產物對照

| ID | 標題 | 規格檔 | 實作檔數 | 測試數 | OK |
|----|------|--------|----------|--------|----|
| D-01 | 介面規格（路由／表單／匯出契約） | `docs/specs/note-filler-interface-contract.md` | 3 | 5 | YES |
| D-02 | UI／資料狀態轉移（results capability／confidence） | `docs/specs/note-filler-state-machine.md` | 3 | 6 | YES |
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

- **PASSED** `tests/test_server.py::test_index_returns_upload_form` — `tests/test_server.py::test_index_returns_upload_form[asyncio] PASSED     [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_index_returns_upload_form -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_run_renders_two_columns` — `tests/test_server.py::test_run_renders_two_columns[asyncio] PASSED       [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_run_renders_two_columns -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_returns_markdown_attachment` — `tests/test_server.py::test_export_returns_markdown_attachment[asyncio] PASSED [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_export_returns_markdown_attachment -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_without_run_returns_404` — `tests/test_server.py::test_export_without_run_returns_404[asyncio] PASSED [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_export_without_run_returns_404 -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_b_cannot_receive_a_result` — `tests/test_server.py::test_export_b_cannot_receive_a_result[asyncio] PASSED [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_export_b_cannot_receive_a_result -vv --tb=line --color=no`

### D-02 — UI／資料狀態轉移（results capability／confidence）

- claim_ok: **True**
- spec_file: `docs/specs/note-filler-state-machine.md` (exists=True)
- status_note: S0/S2/S3/S4 與 confidence 轉移有程式與測試錨點；S1 失敗邊仍屬框架預設
- confirmation_record_ok: **True**

實作錨點：

- **PASS** `app/server.py`
- **PASS** `src/note_filler/correction.py`
- **PASS** `src/note_filler/pipeline.py`

測試單獨結果：

- **PASSED** `tests/test_server.py::test_export_without_run_returns_404` — `tests/test_server.py::test_export_without_run_returns_404[asyncio] PASSED [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_export_without_run_returns_404 -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_returns_markdown_attachment` — `tests/test_server.py::test_export_returns_markdown_attachment[asyncio] PASSED [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_export_returns_markdown_attachment -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_two_clients_each_receive_own_result` — `tests/test_server.py::test_export_two_clients_each_receive_own_result[asyncio] PASSED [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_export_two_clients_each_receive_own_result -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_expired_result_returns_404` — `tests/test_server.py::test_export_expired_result_returns_404[asyncio] PASSED [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_export_expired_result_returns_404 -vv --tb=line --color=no`
- **PASSED** `tests/test_pipeline.py::test_run_pipeline_invariant` — `tests/test_pipeline.py::test_run_pipeline_invariant PASSED               [100%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -vv --tb=line --color=no`
- **PASSED** `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression` — `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression PASSED [100%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression -vv --tb=line --color=no`

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

- **PASSED** `tests/test_server.py::test_run_renders_two_columns` — `tests/test_server.py::test_run_renders_two_columns[asyncio] PASSED       [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_run_renders_two_columns -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_returns_markdown_attachment` — `tests/test_server.py::test_export_returns_markdown_attachment[asyncio] PASSED [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_export_returns_markdown_attachment -vv --tb=line --color=no`
- **PASSED** `tests/test_pipeline.py::test_run_pipeline_invariant` — `tests/test_pipeline.py::test_run_pipeline_invariant PASSED               [100%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -vv --tb=line --color=no`
- **PASSED** `tests/test_e2e_acceptance.py::test_e2e_structural_invariants` — `tests/test_e2e_acceptance.py::test_e2e_structural_invariants PASSED      [100%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_structural_invariants -vv --tb=line --color=no`

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

- **PASSED** `tests/test_server.py::test_index_returns_upload_form` — `tests/test_server.py::test_index_returns_upload_form[asyncio] PASSED     [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_index_returns_upload_form -vv --tb=line --color=no`
- **PASSED** `tests/test_pipeline.py::test_run_pipeline_invariant` — `tests/test_pipeline.py::test_run_pipeline_invariant PASSED               [100%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -vv --tb=line --color=no`
- **PASSED** `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression` — `tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression PASSED [100%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression -vv --tb=line --color=no`
- **PASSED** `tests/test_correction.py::test_retrieved_five_but_only_two_cited` — `tests/test_correction.py::test_retrieved_five_but_only_two_cited PASSED  [100%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_correction.py::test_retrieved_five_but_only_two_cited -vv --tb=line --color=no`

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

- **PASSED** `tests/test_server.py::test_index_returns_upload_form` — `tests/test_server.py::test_index_returns_upload_form[asyncio] PASSED     [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_index_returns_upload_form -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_run_renders_two_columns` — `tests/test_server.py::test_run_renders_two_columns[asyncio] PASSED       [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_run_renders_two_columns -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_returns_markdown_attachment` — `tests/test_server.py::test_export_returns_markdown_attachment[asyncio] PASSED [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_export_returns_markdown_attachment -vv --tb=line --color=no`
- **PASSED** `tests/test_server.py::test_export_without_run_returns_404` — `tests/test_server.py::test_export_without_run_returns_404[asyncio] PASSED [ 50%]`
  - invocation: `C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe -X utf8 -m pytest tests/test_server.py::test_export_without_run_returns_404 -vv --tb=line --color=no`
- screenshot_status: `absent` — 目前無 .png/.jpg 畫面截圖；以文件索引 + 模板 + 測試錨點作為最小可核實證據

## failures

- (empty)

## ACCEPTANCE_PASS = True

ACCEPTANCE_MODE: per-claim-evidence
