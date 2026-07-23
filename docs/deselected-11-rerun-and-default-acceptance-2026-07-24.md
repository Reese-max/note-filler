# 11 個 deselected 測試重跑與預設驗收

## 結論

- 現場收集為 `263` 項：預設選取 `252` 項、排除 `11` 項；排除集合與 `tests/deselected_allowlist.json` 完全一致。
- 明確選取 `integration` 後，11 項全部真跑通過：`11 passed, 252 deselected in 330.28s`，沒有 skipped、failed 或 error。
- 預設驗收全部通過：`252 passed, 11 deselected in 51.94s`。
- 防漏跑 guard 通過：11 項各有排除理由，37 個唯一替代測試全數位於預設集合，`missing=0`。
- 本輪沒有可重現的產品缺陷，因此沒有捏造程式修復。需要外部 Grok／Twinkle 的 11 項依專案規則保留 `integration`；其可離線重現的資料處理、異常處理與品質閘已由預設測試實際執行，不以 deselect 規避。

## 可重現命令與原始結果

所有 Python 命令皆使用指定主專案 venv，並加上 `-X utf8`。

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest --collect-only -q
# 252/263 tests collected (11 deselected) in 0.64s

& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest -m integration -o "addopts=" -vv --tb=short --junitxml=docs/pytest-audit/deselected-11-rerun-2026-07-24.xml
# collected 263 items / 252 deselected / 11 selected
# 11 passed, 252 deselected in 330.28s (0:05:30)

& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 scripts/validate_deselection_ci.py --report docs/pytest-audit/deselected-11-rerun-ci-gate-2026-07-24.md
# [gate] total=263 selected=252 deselected=11 expected=11
# [gate] substitute_coverage: unique=37 selected=37 missing=0
# [gate] PASS: deselected 防漏跑政策核驗通過

& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest -q --junitxml=docs/pytest-audit/default-acceptance-after-deselected-rerun-2026-07-24.xml
# 252 passed, 11 deselected in 51.94s
```

機器可讀原始結果：

- `docs/pytest-audit/deselected-11-rerun-2026-07-24.xml`
- `docs/pytest-audit/default-acceptance-after-deselected-rerun-2026-07-24.xml`
- `docs/pytest-audit/deselected-11-rerun-ci-gate-2026-07-24.md`

## 逐項結果與排除說明

| # | 測試 | 真跑 | 耗時 | 為何不進預設外部整合批次 |
|---:|---|---|---:|---|
| 1 | `test_detect_domain_real_grok_returns_law` | PASSED | 4.262s | 驗證真 Grok 法律領域分類；需 `127.0.0.1:8318`。 |
| 2 | `test_detect_domain_real_grok_representative_domains` | PASSED | 18.644s | 驗證真模型 law/admin/exam/other 語意矩陣；需 Grok proxy。 |
| 3 | `test_e2e_acceptance_real` | PASSED | 169.094s | 真 Grok、Twinkle、law DB 的完整流程；外部依賴未齊時會 runtime skip。 |
| 4 | `test_detect_gaps_real_grok` | PASSED | 6.073s | 驗證真模型 partial/missing 判斷；需 Grok proxy。 |
| 5 | `test_detect_gaps_real_grok_semantic_matrix` | PASSED | 5.420s | 驗證真模型 covered/missing 語意矩陣；需 Grok proxy。 |
| 6 | `test_grok_pong_integration` | PASSED | 4.017s | 驗證真實 HTTP 連線與 PONG 回應；需 Grok proxy。 |
| 7 | `test_run_pipeline_real_grok` | PASSED | 85.643s | 驗證真模型輸出下 pipeline 與 C6；需 Grok proxy。 |
| 8 | `test_generate_questions_real_grok` | PASSED | 9.676s | 驗證真模型問題生成品質與格式；需 Grok proxy。 |
| 9 | `test_retrieve_for_gap_real_twinkle_smoke` | PASSED | 12.612s | 驗證真 Twinkle、Grok 關鍵字與 law DB 路由；需三項外部前置。 |
| 10 | `test_search_real_twinkle_hub` | PASSED | 6.472s | 驗證真 Twinkle session 與 Source 解析；需 `TWINKLE_HUB_TOKEN`。 |
| 11 | `test_write_supplement_real_grok_grounded_output` | PASSED | 6.480s | 驗證真模型只依固定來源產生註腳；需 Grok proxy。 |

共同 collection 原因是 `pyproject.toml` 預設 `-m 'not integration'`。這是外部服務邊界，不是用來隱藏本輪失敗；本輪以 `-m integration -o "addopts="` 反向明確選取後，11 項均實際執行且通過。

## 資料處理與異常分支判定

以下可決定性語義已在預設 252 項中執行：

- 原稿逐字不可變：`test_original_text_immutable_in_output`、`TestOutputConsistency` 與離線 e2e 結構不變式。
- 無來源／【待補證】必為 `pending_evidence`：`test_run_pipeline_invariant`、malformed gap fallback、fault injection 與離線最小品質閘。
- 只掛實際引用來源：correction、write marker 與 output consistency 測試。
- 法條引用離線查核：`test_e2e_minimal_quality_gates_offline_regression`、law check 與 citation failure forwarding 測試。
- Grok／Twinkle 的逾時、transport、malformed/empty response：`test_llm.py`、`test_twinkle.py`、`test_exception_skip_traceability.py` 與 `test_fault_injection.py`。
- law Level A 非空、排序與 vacuous-pass 盲區：`test_c7_correctness_path_law_domain_level_a_not_excluded` 及 exclusion correctness controls。

防漏跑 guard 逐項檢查 allowlist、原因、替代映射與 CI job，並確認 37 個唯一替代節點均為預設 selected。完整逐項理由與替代數量見本輪 gate 報告。因真跑與離線驗收皆通過，沒有失敗分支需要新增修復；若後續任一真實整合測試失敗，必須先建立可離線重現測試並修共同根因，不能新增 deselect 項目規避。
