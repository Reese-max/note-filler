# Note-Filler 元件責任清單（最小版）

## 版本

- 日期：2026-07-19

## 追溯資訊

- **設計編號**: D-04
- **需求編號**: R-03（復用策略）, R-04（系統架構）, R-10（開發方式）
- **驗收編號**: A-01（test_index_returns_upload_form）, A-05（test_run_pipeline_invariant）, A-06（test_e2e_minimal_quality_gates_offline_regression）, A-08（test_retrieved_five_but_only_two_cited）
- **追溯狀態**: 完整
- **追溯索引**: `docs/specs/design-traceability-index.md`

## 1) 入口/展示元件

| 元件 | 責任 | 應用檔 |
|---|---|---|
| `server.app` | FastAPI 應用初始化、路由註冊、結果狀態容器 `app.state.results`（result capability→doc，TTL/上限逐出） | `app/server.py` |
| `index.html` | 上傳表單（唯一入口） | `app/templates/index.html` |
| `result.html` | 雙欄展示結果、補充高亮、來源展開、下載入口 | `app/templates/result.html` |

## 2) 資料流程元件

| 元件 | 責任 | 應用檔 |
|---|---|---|
| `parse_note` | 讀取原始筆記文字為段落化結構 (`Document`/`Paragraph`)。 | `src/note_filler/parse.py` |
| `detect_domain` | 依筆記文字決定研究領域。 | `src/note_filler/domain.py` |
| `generate_questions` | 從原文與領域產生缺口問題。 | `src/note_filler/questions.py` |
| `detect_gaps` | 將問題與原文比對，保留 `partial`/`missing`。 | `src/note_filler/gap.py` |
| `retrieve_for_gap` | 針對每個 gap 拉取候選來源。 | `src/note_filler/retrieve/__init__.py`、`src/note_filler/retrieve/*.py` |
| `write_supplement` | 以來源為根據撰寫補充段，解析 `[^n]` 註腳並回傳 `used_source_ids`。 | `src/note_filler/write.py` |
| `cross_validate` | 對問題與實際使用來源做交叉驗證（已設計：依 `used_source_ids`）。 | `src/note_filler/verify.py` |
| `assemble_correction` | 組合 `original/supplement` 段，計算 `confidence`。 | `src/note_filler/correction.py` |
| `to_markdown` | 匯出附件 Markdown（含 `correction.md`）。 | `src/note_filler/export.py` |
| `check_law_citations` | 法條離線核驗，失敗時降低信心等級。 | `src/note_filler/knowledge/law_citation_check.py` |

## 3) 測試對應責任

| 責任 | 直接對應測試 |
|---|---|
| 路由行為（上傳/結果/匯出） | `tests/test_server.py` |
| pipeline C6 不變式（無來源 pending） | `tests/test_pipeline.py` |
| acceptance 門檻（原稿保留、pending_evidence、引用與法條查核） | `tests/test_e2e_acceptance.py` |
| failing-first 驗證銜接（契約） | `tests/test_excluded_failing_controls.py`, `tests/test_deselection_guard.py` |

## 4) 元件邊界聲明（不新增抽象）

- 目前僅需維持「可讀」責任分離，不再新增 controller/service/repository 三層；所有責任已落在上述薄層元件中，方便一眼追溯。
- 任何跨域變更，先改資料流程元件，最後再更新 `result.html` 呈現。
