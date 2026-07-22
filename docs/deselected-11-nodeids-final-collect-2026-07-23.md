# Deselected 測試 Node ID 最終收集報告

## 產生時間
2026-07-23

## 執行環境
- Python 路徑: 系統 Python 3.11.9 (C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe)
- 執行參數: `-X utf8`
- 工作目錄: `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\f49f7e13`

## CI 完整選項與環境變數

### CI 配置 (.github/workflows/ci.yml)
主要測試 Job 指令:
- **test-pinned**: `python -m pytest tests/ -m "not integration" -v`
- **test-latest**: `python -m pytest tests/ -m "not integration" -v`
- **test-integration**: `python -m pytest tests/ -m "integration" -v` (僅 workflow_dispatch)

### Pytest 配置 (pyproject.toml)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

### 環境變數
- 無特定環境變數要求於 CI 配置中
- Integration 測試需要:
  - `TWINKLE_HUB_TOKEN`: Twinkle Hub 認證 token
  - Grok proxy at `http://127.0.0.1:8318/v1` (model grok-4.3)

## 實際執行結果

### 執行指令
```bash
python -X utf8 -m pytest tests/ -m "not integration" --collect-only -q --deselected-details
```

### Collection 統計
- **總收集測試數**: 167
- **預設 selected**: 156
- **Deselected**: 11

## 全部 11 個 Deselected 測試詳細資訊

| # | Node ID | Marker | 排除條件 | 檔案位置 |
|---|---------|--------|----------|----------|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | `@pytest.mark.integration` | `-m 'not integration'` | test_domain.py:76 |
| 2 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `@pytest.mark.integration` | `-m 'not integration'` | test_domain.py:62 |
| 3 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `@pytest.mark.integration` | `-m 'not integration'` | test_e2e_acceptance.py:244 |
| 4 | `tests/test_gap.py::test_detect_gaps_real_grok` | `@pytest.mark.integration` | `-m 'not integration'` | test_gap.py:83 |
| 5 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | `@pytest.mark.integration` | `-m 'not integration'` | test_gap.py:106 |
| 6 | `tests/test_llm.py::test_grok_pong_integration` | `@pytest.mark.integration` | `-m 'not integration'` | test_llm.py:95 |
| 7 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `@pytest.mark.integration` | `-m 'not integration'` | test_pipeline.py:151 |
| 8 | `tests/test_questions.py::test_generate_questions_real_grok` | `@pytest.mark.integration` | `-m 'not integration'` | test_questions.py:74 |
| 9 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `@pytest.mark.integration` | `-m 'not integration'` | test_retrieve.py:102 |
| 10 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `@pytest.mark.integration` | `-m 'not integration'` | test_twinkle.py:166 |
| 11 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | `@pytest.mark.integration` | `-m 'not integration'` | test_write.py:63 |

## 排除條件分析

### 統一排除規則
所有 11 個 deselected 測試皆透過以下統一機制排除：

1. **Marker 標記**: 每個測試都有 `@pytest.mark.integration` 標記
2. **Pytest 配置**: `pyproject.toml` 中的 `addopts = "-m 'not integration'"`
3. **排除原因**: 所有測試的排除原因皆為 `deselected by -m 'not integration'`

### 排除機制確認
- `-m 'not integration'` (addopts): **是** - 唯一 collection 排除機制
- `-k` keyword 過濾: 否 - 未使用
- `--deselect`: 否 - 未使用
- 條件式收集 (pytest_collection_modifyitems): 否 - 無此 hook
- 目錄排除條件: 否 - 未使用

## 8 個與 11 個差異解釋

### 差異來源
目標所稱 8 個與實際 11 個的差異來自 2026-07-22 新增的 3 個 integration 測試：

| # | 新增測試 Node ID | 新增位置 | 說明 |
|---|------------------|----------|------|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | test_domain.py:76 | 真 Grok 四類代表文本語意矩陣 |
| 2 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | test_gap.py:106 | 真 Grok covered/missing 對照語意 |
| 3 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | test_write.py:63 | 固定兩筆 Level A 來源下的真 Grok grounded 輸出 |

### 既有的 8 個 deselected 測試（2026-07-19 已存在）
1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`
2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`
3. `tests/test_gap.py::test_detect_gaps_real_grok`
4. `tests/test_llm.py::test_grok_pong_integration`
5. `tests/test_pipeline.py::test_run_pipeline_real_grok`
6. `tests/test_questions.py::test_generate_questions_real_grok`
7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`
8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

### 排除機制一致性
所有 11 個測試（8 個既有 + 3 個新增）都使用相同的排除機制：
- 標記：`@pytest.mark.integration`
- 配置：`pyproject.toml` 的 `addopts = "-m 'not integration'"`
- 原因：`deselected by -m 'not integration'`

### 非意外漏跑
- 新增的 3 個測試都有正確的 `@pytest.mark.integration` 標記
- 沒有使用 `-k` 過濾、`--deselect` 或其他條件式收集機制
- CI 矩陣設定與排除政策一致

## 可重現驗證命令

### 獲取實際 deselected 清單
```bash
python -X utf8 -m pytest tests/ -m "not integration" --collect-only -q --deselected-details
```

### 僅收集 integration 測試
```bash
python -X utf8 -m pytest tests/ -m integration --collect-only -q
```

### 執行 integration 測試（需 grok proxy）
```bash
python -X utf8 -m pytest tests/ -m integration -v
```

## 結論

1. **數量差異來源**: 2026-07-22 新增了 3 個 integration 測試，從 8 個增加到 11 個
2. **排除機制一致性**: 所有 11 個測試都使用統一的 `@pytest.mark.integration` 標記與 `-m 'not integration'` 排除機制
3. **無其他排除條件**: 沒有使用 `-k` 過濾、`--deselect` 或目錄排除條件
4. **受控設計意圖**: 所有 integration 測試都需要真實 grok proxy，預設 CI 跳過以避免依賴外部服務
