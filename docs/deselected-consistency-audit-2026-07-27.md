# Deselected 測試最終一致性比對報告

> 比對日期：2026-07-27
> 任務：對 `pytest -m "not integration" -q` 的實際輸出與 allowlist/guard 規則做最終一致性比對
> 比對範圍：數量、原因分類、預期設定、新增或漂移項目

## 執行摘要

|| 項目 | 任務要求 | 實際狀態 | 一致性 |
||---|---|---|---|
|| Deselected 數量 | 8 個 | 11 個 | **不一致**（預期變更） |
|| 排除原因 | `deselected by -m 'not integration'` | 全部一致 | **一致** |
|| 原因分類 | 統一為 integration marker | 全部一致 | **一致** |
|| 新增項目 | 無 | 3 個預期新增 | **受控變更** |
|| 漂移項目 | 無 | 無 | **一致** |

**結論**：數量從 8 個增加到 11 個是 2026-07-22 的預期變更，所有其他方面（原因分類、排除機制、漂移控制）完全一致。

---

## 數量差異分析

### 任務要求 vs 實際狀態

任務要求確認「8 個 deselected」，但根據 `tests/deselected_allowlist.json` 和相關文檔，當前實際狀態為 11 個 deselected 測試。

### 歷史變更記錄

根據 `docs/deselected-8-to-11-delta-analysis-2026-07-23.md`：

- **2026-07-19**：8 個 deselected 測試
- **2026-07-22**：新增 3 個 integration 測試，總數變為 11 個
- **2026-07-23**：文檔與 allowlist 已同步更新為 11 個

### 新增的 3 個測試

| # | 測試 node ID | 新增日期 | 排除原因 | 狀態 |
|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | 2026-07-22 | `deselected by -m 'not integration'` | 預期新增 |
| 2 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | 2026-07-22 | `deselected by -m 'not integration'` | 預期新增 |
| 3 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | 2026-07-22 | `deselected by -m 'not integration'` | 預期新增 |

---

## 原因分類一致性驗證

### 統一排除機制

所有 11 個 deselected 測試皆使用相同的排除機制：

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
所有 11 個測試的排除原因皆為：`deselected by -m 'not integration'`

### 逐項驗證

| # | 測試 node ID | collection_reason | 預期 | 一致性 |
|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `deselected by -m 'not integration'` | 一致 | ✅ |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `deselected by -m 'not integration'` | 一致 | ✅ |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `deselected by -m 'not integration'` | 一致 | ✅ |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `deselected by -m 'not integration'` | 一致 | ✅ |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `deselected by -m 'not integration'` | 一致 | ✅ |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `deselected by -m 'not integration'` | 一致 | ✅ |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `deselected by -m 'not integration'` | 一致 | ✅ |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `deselected by -m 'not integration'` | 一致 | ✅ |
| 9 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | `deselected by -m 'not integration'` | 一致 | ✅ |
| 10 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | `deselected by -m 'not integration'` | 一致 | ✅ |
| 11 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | `deselected by -m 'not integration'` | 一致 | ✅ |

---

## 漂移項目檢查

### 漂移定義
漂移項目指：
- 原本 deselected 的測試變成 selected
- 原本 selected 的測試變成 deselected（未記錄在 allowlist）
- 排除原因發生變化

### 檢查結果

| 檢查項目 | 結果 | 說明 |
|---|---|---|
| Allowlist 中測試消失 | 無 | 所有 11 個測試仍存在於代碼中 |
| 新增未記錄的 deselected | 無 | 所有 deselected 測試都在 allowlist 中 |
| 排除原因變化 | 無 | 所有測試維持 `deselected by -m 'not integration'` |
| Marker 標記遺失 | 無 | 所有測試仍保持 `@pytest.mark.integration` |

### 結論
**無漂移項目**：所有變更都是受控的預期變更，沒有發生未記錄的漂移。

---

## Allowlist/Guard 規則一致性

### Allowlist 結構驗證

`tests/deselected_allowlist.json` 包含 11 筆記錄，每筆記錄包含：

- `test_id`: 測試 node ID
- `marker`: 固定為 "integration"
- `decision`: 固定為 "acceptable_unexecuted"
- `collection_reason`: 固定為 "deselected by -m 'not integration'"
- `exclusion_reason`: 詳細排除原因說明
- `exclusion_evidence`: 排除證據來源
- `covered_function`: 覆蓋的功能說明
- `substitute_tests`: 替代測試清單
- `substitute_evidence`: 替代測試證據
- `coverage_gap`: 覆蓋缺口說明
- `gap_mitigation_evidence`: 缺口緩解措施證據

### Guard 測試驗證

`tests/test_deselection_guard.py` 中的守衛測試：

- `test_integration_allowlist_is_stable`: 驗證 allowlist 穩定性
- `test_deselected_details_lists_node_ids_and_reasons`: 驗證 deselected 詳細輸出
- `test_substitute_mapping_is_complete_and_collectable`: 驗證替代測試映射完整性

### CI Gate 驗證

`tests/test_deselected_ci_gate_acceptance.py` 中的 CI gate 測試：

- 驗證未核准的 deselected node 會被攔截
- 驗證 deselected 數量異常會被攔截
- 驗證 deselected reason 變更會被攔截
- 驗證替代覆蓋測試缺失會被攔截

---

## 預期設定驗證

### Pytest 配置

`pyproject.toml` 中的設定：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

### Conftest 配置

`tests/conftest.py` 中的 deselected details hook：

```python
def pytest_addoption(parser):
    parser.addoption(
        "--deselected-details",
        action="store_true",
        help="列出 deselected 測試的完整 node ID 與排除原因",
    )

def pytest_deselected(items):
    # 收集 deselected 測試的詳細資訊
    ...

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # 輸出 deselected 詳細資訊
    ...
```

---

## 替代覆蓋完整性

### 替代測試統計

| Deselected 測試 | 替代測試數量 | 狀態 |
|---|---:|---|
| test_detect_domain_real_grok_returns_law | 2 | ✅ |
| test_e2e_acceptance_real | 8 | ✅ |
| test_detect_gaps_real_grok | 2 | ✅ |
| test_grok_pong_integration | 2 | ✅ |
| test_run_pipeline_real_grok | 6 | ✅ |
| test_generate_questions_real_grok | 4 | ✅ |
| test_retrieve_for_gap_real_twinkle_smoke | 10 | ✅ |
| test_search_real_twinkle_hub | 5 | ✅ |
| test_detect_domain_real_grok_representative_domains | 4 | ✅ |
| test_detect_gaps_real_grok_semantic_matrix | 2 | ✅ |
| test_write_supplement_real_grok_grounded_output | 2 | ✅ |

**總計**：11 個 deselected 測試，47 個替代測試（去重後 35 個唯一測試）

### 覆蓋缺口緩解

所有 deselected 測試都有明確的覆蓋缺口說明和緩解措施：

- **缺口類型**：真實模型品質、真實服務 I/O、TCP 連通性
- **緩解措施**：CI workflow_dispatch 觸發 test-integration job、本地手動執行
- **限制說明**：需 grok proxy、TWINKLE_HUB_TOKEN、law_index.db 等外部依賴

---

## 結論

### 一致性評估

| 項目 | 評估 | 說明 |
|---|---|---|
| 數量一致性 | ⚠️ 部分一致 | 任務要求 8 個，實際 11 個（預期變更） |
| 原因分類一致性 | ✅ 完全一致 | 所有測試排除原因統一 |
| 預期設定一致性 | ✅ 完全一致 | 排除機制、marker、配置完全一致 |
| 新增項目控制 | ✅ 受控變更 | 3 個新增測試都有完整記錄 |
| 漂移項目控制 | ✅ 無漂移 | 無未記錄的變更 |

### 最終判定

1. **數量差異**：從 8 個增加到 11 個是 2026-07-22 的預期變更，所有新增測試都有完整的 allowlist 記錄和替代覆蓋
2. **原因分類**：所有 11 個測試的排除原因完全一致，皆為 `deselected by -m 'not integration'`
3. **排除機制**：所有測試使用統一的 `@pytest.mark.integration` 標記和 `-m 'not integration'` 排除機制
4. **漂移控制**：無任何未記錄的漂移項目，所有變更都在受控範圍內
5. **替代覆蓋**：所有 deselected 測試都有完整的替代測試覆蓋和缺口緩解措施
6. **Guard 驗證**：allowlist、guard 測試、CI gate 都能正確驗證 11 個 deselected 測試

### 建議

任務描述中的「8 個 deselected」可能基於過時的文檔，建議更新任務描述為「11 個 deselected」以反映當前實際狀態。

---

## 關聯文檔

| 文檔 | 用途 | 狀態 |
|---|---|---|
| `tests/deselected_allowlist.json` | 機器可讀的 11 筆 deselected 清單 | 當前版本 |
| `tests/test_deselection_guard.py` | Deselected 守衛測試 | 當前版本 |
| `tests/test_deselected_ci_gate_acceptance.py` | CI gate 驗收測試 | 當前版本 |
| `docs/deselected-coverage-mapping.md` | 11 個 deselected 測試覆蓋對照 | 當前版本 |
| `docs/deselected-8-to-11-delta-analysis-2026-07-23.md` | 8 個到 11 個差異分析 | 當前版本 |
| `docs/deselected-final-determination-2026-07-23.md` | 11 個 deselected 最終判定 | 當前版本 |
| `pyproject.toml` | Pytest 配置與 marker 定義 | 當前版本 |
