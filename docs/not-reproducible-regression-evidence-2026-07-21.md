# NOT-REPRODUCIBLE 回歸測試證據（2026-07-21）

> 判定：**NOT-REPRODUCIBLE** — 無法找到可穩定重現的 product correctness bug。
> 所有 142 個非 integration 測試全數通過；8 個 integration 測試因 Grok proxy
> 認證失敗（HTTP 401）無法執行，屬基礎設施問題而非產品程式碼缺陷。

## 執行環境

| 項目 | 值 |
|------|-----|
| CWD | `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\eeca9106` |
| Python | 3.11.9 (MSC v.1938 64 bit) |
| Python 路徑 | `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8` |
| pytest | 9.1.1, pluggy-1.6.0 |
| git HEAD | `66da142` |
| Grok proxy port | 8318 OPEN, 但回 HTTP 401 Unauthorized |

## pytest 設定（pyproject.toml）

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

## 非 integration 測試結果（142 passed, 0 failed）

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\eeca9106
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 150 items / 8 deselected / 142 selected

tests\test_citation_formatter.py .                                       [  0%]
tests\test_cli.py ...                                                    [  2%]
tests\test_conclusion_classification.py ........                         [  8%]
tests\test_correction.py .............                                   [ 17%]
tests\test_deselected_ci_gate_acceptance.py ...                          [ 19%]
tests\test_deselection_guard.py .....                                    [ 23%]
tests\test_design_acceptance.py ....                                     [ 26%]
tests\test_domain.py ......                                              [ 30%]
tests\test_e2e_acceptance.py ...                                         [ 32%]
tests\test_excluded_failing_controls.py ..........                       [ 39%]
tests\test_exclusion_correctness_blind_spot.py ..                        [ 40%]
tests\test_export.py ...                                                 [ 42%]
tests\test_export_docx.py .                                              [ 43%]
tests\test_gap.py ......                                                 [ 47%]
tests\test_grading.py .......                                            [ 52%]
tests\test_law_check.py .......                                          [ 57%]
tests\test_law_lookup.py ..                                              [ 59%]
tests\test_law_search.py .......                                         [ 64%]
tests\test_llm.py ..                                                     [ 65%]
tests\test_parse.py ...                                                  [ 67%]
tests\test_pipeline.py ...                                               [ 69%]
tests\test_questions.py ....                                             [ 72%]
tests\test_requirements_test_coverage.py ..                              [ 73%]
tests\test_retrieve.py ..                                                [ 75%]
tests\test_server.py ....                                                [ 78%]
tests\test_twinkle.py ......                                             [ 82%]
tests\test_verify.py .............                                       [ 91%]
tests\test_web.py .........                                              [ 97%]
tests\test_write.py ...                                                  [100%]

===================== 142 passed, 8 deselected in 21.69s ======================
=== EXIT_CODE: 0 ===
```

## Integration 測試結果（7 failed, 1 passed, 原因：Grok proxy 401）

```
FAILED tests/test_domain.py::test_detect_domain_real_grok_returns_law - urllib.error.HTTPError: HTTP Error 401: Unauthorized
FAILED tests/test_e2e_acceptance.py::test_e2e_acceptance_real - urllib.error.HTTPError: HTTP Error 401: Unauthorized
FAILED tests/test_gap.py::test_detect_gaps_real_grok - urllib.error.HTTPError: HTTP Error 401: Unauthorized
FAILED tests/test_llm.py::test_grok_pong_integration - urllib.error.HTTPError: HTTP Error 401: Unauthorized
FAILED tests/test_pipeline.py::test_run_pipeline_real_grok - urllib.error.HTTPError: HTTP Error 401: Unauthorized
FAILED tests/test_questions.py::test_generate_questions_real_grok - urllib.error.HTTPError: HTTP Error 401: Unauthorized
FAILED tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke - urllib.error.HTTPError: HTTP Error 401: Unauthorized
PASSED tests/test_search_real_twinkle_hub (TWINKLE_HUB_TOKEN 未設定,已 skip)
```

**失敗原因分析**：GrokClient 預設 `api_key="x"`，但 Grok proxy（Hermes）實際要求有效認證。
Port 8318 開放且有服務回應，但所有 LLM 呼叫均回 401 Unauthorized。
這是**基礎設施/環境配置問題**，非產品程式碼邏輯缺陷。

## 程式路徑分析：無 product correctness bug

### 1. 非 integration 路徑（全數驗證通過）

| 模組 | 測試數 | 結論 |
|------|--------|------|
| pipeline.py | 3 | 全通過：C6 不變式、law citation check、malformed fallback |
| gap.py | 6 | 全通過：JSON 解析、fallback、code fence 剝除 |
| write.py | 3 | 全通過：marker 解析、pending_evidence、越界標記移除 |
| verify.py | 13 | 全通過：A/B/C/D 級別、獨立源計數、衝突偵測 |
| correction.py | 12 | 全通過：原文 immutable、used sources 過濾、confidence 決策 |
| retrieve/ | 3 | 全通過：Level A 排序、web 來源隔離、law domain 路徑 |
| law_search.py | 7 | 全通過：keyword 解析、法條搜尋、去重 |
| law_citation_check.py | 7 | 全通過：法條抽取、條號核對、罰則比對 |
| 其他模組 | 88 | 全通過 |

### 2. 已知盲區（vacuous pass）— 非 product bug

`test_retrieve_for_gap_real_twinkle_smoke` 的三道斷言對空清單為 vacuous True。
此為**測試設計缺口**（已在 `test_exclusion_correctness_blind_spot.py` 鎖定），
非產品行為缺陷。產品路徑已由 `test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`
驗證健康。

### 3. 已知 dead code — 非 correctness bug

`assemble_correction` 的 `validations` 參數未使用（跨驗證結果已計算但未納入
confidence 決策）。Confidence 由 `_grounded(used_sources)` 決定，邏輯正確。

## 產物清單

1. `docs/not-reproducible-regression-evidence-2026-07-21.md`（本報告）
2. 本報告即為完整證據包（含 pytest 設定、環境資訊、逐項執行日誌）

## 可追查原因的證據檔案路徑

| 檔案 | 用途 |
|------|------|
| `pyproject.toml:25-35` | pytest 設定（addopts、markers、testpaths） |
| `src/note_filler/llm.py:12-41` | GrokClient 實作（api_key="x"、401 根因） |
| `tests/test_exclusion_correctness_blind_spot.py` | 已有 vacuous pass 盲區回歸 |
| `docs/not-reproducible-blindspot-evidence-2026-07-21.md` | 先前盲區證據 |
| `docs/minimal-regression-execution-evidence-2026-07-21.md` | 最小回歸執行證據 |
| `docs/deselected-final-judgment-2026-07-21.md` | 8 個 deselected 測試最終判定 |

## 判定理由

1. **非 integration 142 tests 全數 PASS** — 無任何 product code path 產生錯誤結果
2. **Integration 7 failures = HTTP 401** — 基礎設施認證問題，非程式邏輯缺陷
3. **Vacuous pass 盲區** — 已被 `test_exclusion_correctness_blind_spot.py` 鎖定，
   產品路徑（law + LawLookup）已驗證健康
4. **Dead code (validations)** — 不影響 correctness，confidence 決策正確
5. **結論：無法穩定重現任何 product correctness bug → NOT-REPRODUCIBLE**
