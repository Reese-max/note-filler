# Deselected 關鍵覆蓋最小補測

## 結論

第 1 步列出的 6 個 singleton 與 2 個零覆蓋點已拆成可單獨執行的最小補測或補強既有斷言。新增 3 個 `integration` node 與 1 個預設回歸 node；預設 selection 由 `157/149/8` 更新為核准後的 `161/150/11`。

| 路徑 | 最小補測／補強 | 本輪結果 |
|---|---|---|
| T1-P2 | `test_detect_domain_real_grok_representative_domains` | 1 passed，14.84s |
| T2-P6 | `test_write_supplement_real_grok_grounded_output` | 1 passed，4.14s |
| T3-P2 | `test_detect_gaps_real_grok_semantic_matrix` | 1 passed，5.01s |
| T5-P3 | `test_run_pipeline_real_grok` 明確要求 supplement 非空 | 1 passed，71.20s |
| T6-P2 | `test_generate_questions_rejects_json_shaped_response` | 1 passed，1.58s |
| T7-P1／P3 | retrieve smoke 明確要求非空且同時有 Level A／B | 1 passed，12.76s |
| T8-P3 | Twinkle Hub smoke 明確要求 results 非空 | 1 passed，7.50s |

writer 補測首次使用「附款種類」問題時正確回 `【待補證】`；原因是兩筆固定來源只支撐附款條件與目的限制。fixture 改成來源可直接回答的問題後通過，未放寬 grounded／註腳／實際來源 ID 斷言。

## Selection 與原因驗證

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest -m "not integration" -q
```

結果：`150 passed, 11 deselected in 46.39s`。

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 scripts/validate_deselection_ci.py
```

結果：`total=161 selected=150 deselected=11`；11 個 node 逐項原因皆為 `deselected by -m 'not integration'`，allowlist 數量、完整集合與原因比對 `PASS`。

JSON-shaped 問題回應採保守回空，不會流入 pipeline；原稿不可變、無來源／`【待補證】` → `pending_evidence`、只掛實際引用來源與法條離線查核等既有品質閘未變更。
