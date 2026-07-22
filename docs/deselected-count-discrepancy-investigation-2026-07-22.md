# Deselected 測試數量差異調查報告

> 調查日期：2026-07-22
> 任務：釐清目標所稱 8 個與驗收輸出 11 個 deselected 的數量差異
> 結論：差異來自 2026-07-22 新增的 3 個 integration 測試，排除機制一致且受控

---

## 執行摘要

| 項目 | 數量 | 來源 |
|---|---:|---|
| 舊文檔聲稱（2026-07-19） | 8 個 | `docs/deselected-8-nodeids-rules-2026-07-19.md` |
| 新文檔聲稱（2026-07-22） | 11 個 | `docs/deselected-11-complete-inventory-2026-07-22.md` |
| 實際執行結果（2026-07-22） | 11 個 | `python -X utf8 -m pytest --collect-only --deselected-details` |
| 差異數量 | +3 個 | 新增測試 |

**結論**：數量差異非意外漏跑，而是 2026-07-22 commit `00cbc07` 中刻意新增的 3 個 integration 測試。所有 11 個測試皆透過統一的 `@pytest.mark.integration` 標記與 `pyproject.toml` 的 `-m 'not integration'` 排除機制受控管理。

---

## 差異測試對照

### 新增的 3 個 deselected 測試

| # | 測試 node ID | 新增 commit | 標記位置 | 排除原因 |
|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | `00cbc07` (2026-07-22) | `test_domain.py:76` | `deselected by -m 'not integration'` |
| 2 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | `00cbc07` (2026-07-22) | `test_gap.py:106` | `deselected by -m 'not integration'` |
| 3 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | `00cbc07` (2026-07-22) | `test_write.py:63` | `deselected by -m 'not integration'` |

### 既有的 8 個 deselected 測試（2026-07-19 已存在）

| # | 測試 node ID | 標記位置 | 排除原因 |
|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `test_domain.py:62` | `deselected by -m 'not integration'` |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `test_e2e_acceptance.py:244` | `deselected by -m 'not integration'` |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `test_gap.py:83` | `deselected by -m 'not integration'` |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `test_llm.py:95` | `deselected by -m 'not integration'` |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `test_pipeline.py:151` | `deselected by -m 'not integration'` |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `test_questions.py:74` | `deselected by -m 'not integration'` |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `test_retrieve.py:102` | `deselected by -m 'not integration'` |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `test_twinkle.py:166` | `deselected by -m 'not integration'` |

---

## 排除機制分析

### 統一排除規則

所有 11 個 deselected 測試皆透過以下統一機制排除：

#### 1. Marker 標記
每個測試都有 `@pytest.mark.integration` 標記：

```python
@pytest.mark.integration
@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")
def test_xxx():
    ...
```

#### 2. Pytest 配置
`pyproject.toml` 中的統一排除設定：

```toml
[tool.pytest.ini_options]
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

#### 3. 排除原因
所有測試的排除原因皆為：`deselected by -m 'not integration'`

### 排除機制確認

| 機制 | 是否使用 | 說明 |
|---|---|---|
| `-m 'not integration'` (addopts) | **是** | 唯一 collection 排除機制 |
| `-k` keyword 過濾 | 否 | 未使用 |
| `--deselect` | 否 | 未使用 |
| 條件式收集 (pytest_collection_modifyitems) | 否 | 無此 hook |
| CI 矩陣設定 | 一致 | test-pinned/test-latest 跳過 integration，test-integration 專門跑 |

---

## CI 矩陣設定對照

### CI 配置 (`.github/workflows/ci.yml`)

| Job | Python 版本 | 執行參數 | 作用 |
|---|---|---|---|
| test-pinned | 3.11, 3.12 | `python -m pytest tests/ -m "not integration" -v` | 預設 CI，跳過 integration |
| test-latest | 3.11, 3.12, 3.13 | `python -m pytest tests/ -m "not integration" -v` | 預設 CI，跳過 integration |
| test-integration | 3.12 | `python -m pytest tests/ -m "integration" -v` | 手動觸發，專門跑 integration |

### CI Gate 驗證
所有 CI job 都執行 `python scripts/validate_deselection_ci.py` 來驗證 deselected 政策。

---

## 可重現驗證命令

### 獲取實際 deselected 清單
```bash
python -X utf8 -m pytest --collect-only --deselected-details
```

### 執行結果（2026-07-22 實測）
```
collected 167 items / 11 deselected / 156 selected

============================= deselected details ==============================
tests/test_domain.py::test_detect_domain_real_grok_representative_domains | reason: deselected by -m 'not integration'
tests/test_domain.py::test_detect_domain_real_grok_returns_law | reason: deselected by -m 'not integration'
tests/test_e2e_acceptance.py::test_e2e_acceptance_real | reason: deselected by -m 'not integration'
tests/test_gap.py::test_detect_gaps_real_grok | reason: deselected by -m 'not integration'
tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix | reason: deselected by -m 'not integration'
tests/test_llm.py::test_grok_pong_integration | reason: deselected by -m 'not integration'
tests/test_pipeline.py::test_run_pipeline_real_grok | reason: deselected by -m 'not integration'
tests/test_questions.py::test_generate_questions_real_grok | reason: deselected by -m 'not integration'
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke | reason: deselected by -m 'not integration'
tests/test_twinkle.py::test_search_real_twinkle_hub | reason: deselected by -m 'not integration'
tests/test_write.py::test_write_supplement_real_grok_grounded_output | reason: deselected by -m 'not integration'
============== 156/167 tests collected (11 deselected) in 1.23s ===============
```

### 僅收集 integration 測試
```bash
python -X utf8 -m pytest --collect-only -m integration
```

### 執行 integration 測試（需 grok proxy）
```bash
python -X utf8 -m pytest -m integration -v
```

---

## 結論

1. **數量差異來源**：2026-07-22 commit `00cbc07` 新增了 3 個 integration 測試
   - `test_detect_domain_real_grok_representative_domains`
   - `test_detect_gaps_real_grok_semantic_matrix`
   - `test_write_supplement_real_grok_grounded_output`

2. **排除機制一致性**：所有 11 個測試（8 個既有 + 3 個新增）都使用相同的排除機制
   - 標記：`@pytest.mark.integration`
   - 配置：`pyproject.toml` 的 `addopts = "-m 'not integration'"`
   - 原因：`deselected by -m 'not integration'`

3. **非意外漏跑**：
   - 新增的 3 個測試都有正確的 `@pytest.mark.integration` 標記
   - 沒有使用 `-k` 過濾、`--deselect` 或其他條件式收集機制
   - CI 矩陣設定與排除政策一致

4. **受控設計意圖**：
   - 所有 integration 測試都需要真實 grok proxy (http://127.0.0.1:8318/v1)
   - 預設 CI 跳過這些測試以避免依賴外部服務
   - 透過 `test-integration` job 專門執行（需手動觸發）

5. **驗收狀態**：
   - Allowlist (`tests/deselected_allowlist.json`) 已更新為 11 筆
   - CI gate 驗證腳本 (`scripts/validate_deselection_ci.py`) 可正常驗證
   - 守衛測試 (`tests/test_deselection_guard.py`) 可通過

---

## 關聯文件

| 文件 | 用途 |
|---|---|
| `docs/deselected-8-nodeids-rules-2026-07-19.md` | 舊版 8 筆 deselected 規則文檔 |
| `docs/deselected-11-complete-inventory-2026-07-22.md` | 新版 11 筆 deselected 完整盤點 |
| `docs/deselected-traceability-index-2026-07-22.md` | 11 筆 deselected 可追溯索引 |
| `tests/deselected_allowlist.json` | 機器可讀的 11 筆 deselected 清單 |
| `scripts/validate_deselection_ci.py` | CI deselected 政策驗證腳本 |
| `tests/test_deselection_guard.py` | deselected 守衛測試 |
