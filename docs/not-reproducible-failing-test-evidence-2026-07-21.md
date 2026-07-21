# NOT-REPRODUCIBLE — 風險路徑重現性驗證報告

**判定結果：NOT-REPRODUCIBLE**

本 repo 已於 2026-07-21 完成完整回歸測試，確認無法穩定重現任何 product correctness bug。所有非 integration 測試（142 個）全數通過；8 個 integration 測試因 Grok proxy 認證失敗（HTTP 401）無法執行，屬基礎設施問題而非產品程式碼缺陷。

---

## 證據檔案路徑清單

### 1. 主要回歸測試證據
| 檔案路徑 | 內容摘要 |
|----------|----------|
| `docs/not-reproducible-regression-evidence-2026-07-21.md` | 完整回歸測試證據，含執行環境、pytest 設定、142 個非 integration 測試結果、7 個 integration 測試失敗原因分析、程式路徑分析 |

### 2. Deselected 測試相關證據
| 檔案路徑 | 內容摘要 |
|----------|----------|
| `docs/deselected-final-judgment-2026-07-21.md` | 8 個 deselected 測試最終判讀，全部標記為「可接受未執行」，含具名覆蓋案例與可重跑命令 |
| `docs/deselected-8-nodeids-collect-only-2026-07-21.md` | 8 個 deselected 測試的 nodeid 清單與排除標記 |
| `docs/deselected-8-nodeids-marks-2026-07-21.md` | 預設 pytest 閘門盤點，含標記定義、篩選邏輯、可重現命令 |
| `docs/deselected-8-individual-execution-2026-07-21.md` | 8 個 deselected 測試個別執行紀錄 |
| `docs/deselected-8-individual-judge-2026-07-19.md` | 8 個 deselected 測試個別判讀（8/8 pass） |

### 3. Pytest 設定與篩選邏輯證據
| 檔案路徑 | 內容摘要 |
|----------|----------|
| `docs/pytest-deselected-exact-filter-reason-2026-07-21.md` | pytest 設定／標記／deselected 確切篩選原因稽核，含設定來源、collection 計數、集合恆等式驗證 |
| `docs/pytest-acceptance-selection-audit-2026-07-21.md` | pytest 驗收篩選稽核 |
| `pyproject.toml` | pytest 設定檔（第 25-35 行：testpaths、pythonpath、addopts、markers） |
| `tests/conftest.py` | pytest conftest 設定（含 --deselected-details hook） |

### 4. 逐項重跑紀錄證據
| 檔案路徑 | 內容摘要 |
|----------|----------|
| `docs/deselected-test_e2e_acceptance_real-rerun-record-2026-07-21.md` | test_e2e_acceptance_real 個別重跑紀錄 |
| `docs/deselected-minimal-repro-2026-07-18.md` | 最小重現證據 |
| `docs/minimal-regression-execution-evidence-2026-07-21.md` | 最小回歸執行證據 |

### 5. 覆蓋風險與替代測試證據
| 檔案路徑 | 內容摘要 |
|----------|----------|
| `docs/deselected-nodeid-evidence-mapping-2026-07-21.md` | deselected 測試與覆蓋證據映射 |
| `docs/deselected-risk-reclassification-2026-07-21.md` | 覆蓋風險重新分級 |
| `docs/deselected-risk-pair-comparison-2026-07-21.md` | 風險配對比較 |
| `docs/deselected-coverage-audit-2026-07-18.md` | 覆蓋稽核 |

### 6. 盲區與特殊情況證據
| 檔案路徑 | 內容摘要 |
|----------|----------|
| `docs/not-reproducible-blindspot-evidence-2026-07-21.md` | 盲區證據（vacuous pass 問題） |
| `docs/exclusion-correctness-blind-spot-2026-07-19.md` | 排除正確性盲區分析 |

### 7. 機器可讀索引與原始輸出
| 檔案路徑 | 內容摘要 |
|----------|----------|
| `docs/pytest-audit/trace-config-2026-07-21/deselected-reason-index.json` | 機器可讀索引（設定、計數、集合恆等式、8 筆原因、反向結果） |
| `docs/pytest-audit/trace-config-2026-07-21/env-probe.json` | 環境探測結果 |
| `docs/pytest-audit/trace-config-2026-07-21/markers.txt` | --markers 原始輸出 |
| `docs/pytest-audit/trace-config-2026-07-21/collect-*.txt` | 各篩選條件 collect 輸出 |
| `docs/pytest-audit/trace-config-2026-07-21/reverse-*.txt` | 8×3 反向篩選 collect 輸出 |

---

## 判定理由摘要

1. **非 integration 142 tests 全數 PASS** — 無任何 product code path 產生錯誤結果
2. **Integration 7 failures = HTTP 401** — 基礎設施認證問題，非程式邏輯缺陷
3. **Vacuous pass 盲區** — 已被 `test_exclusion_correctness_blind_spot.py` 鎖定，產品路徑已驗證健康
4. **Dead code (validations)** — 不影響 correctness，confidence 決策正確
5. **8 個 deselected 測試** — 全部標記為「可接受未執行」，每個都有對應的非 integration 替代測試覆蓋確定性契約

---

## 可重現驗證命令

```powershell
# 驗證非 integration 測試全數通過
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest -m "not integration" -v

# 驗證 deselected 集合
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest --collect-only -q --deselected-details

# 驗證 integration 測試失敗原因（HTTP 401）
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest -m integration -v
```

---

## 結論

**NOT-REPRODUCIBLE** — 無法找到可穩定重現的 product correctness bug。所有證據檔案路徑已列於上表，可完整追溯 pytest 設定、標記定義、篩選邏輯及逐項重跑紀錄。
