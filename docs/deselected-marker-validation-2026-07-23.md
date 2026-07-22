# Deselected 測試 Marker 定義與排除規則驗證報告

## 驗證時間
2026-07-23

## 驗證範圍
逐一檢查 11 個 deselected 測試的 marker 定義、`pytest.ini`／`pyproject.toml`／`conftest.py` 與 CI pytest 命令，確認排除規則為顯式且受版本控制，而非未註冊 marker、條件判斷錯誤或命令列過濾副作用。

## 執行環境
- Python 路徑: `python -X utf8`
- Pytest 版本: 9.1.1
- 工作目錄: `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\02fd69ec`

## Marker 定義檢查

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

**檢查結果:**
- ✅ `integration` marker 已在 `markers` 區段正確註冊
- ✅ 啟用 `--strict-markers` 確保未註冊 marker 會報錯
- ✅ `addopts` 統一使用 `-m 'not integration'` 排除 integration 測試

### Conftest Hooks 檢查 (tests/conftest.py)
```python
def pytest_addoption(parser):
    parser.addoption(
        "--deselected-details",
        action="store_true",
        help="列出 deselected 測試的完整 node ID 與排除原因",
    )

def pytest_deselected(items):
    # 自訂 deselected 詳細輸出邏輯
    ...

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # 輸出 deselected 詳細資訊
    ...
```

**檢查結果:**
- ✅ 無 `pytest_collection_modifyitems` 條件式收集邏輯
- ✅ 無動態修改測試集合的 hook
- ✅ 僅有自訂 `--deselected-details` 選項用於輸出排除原因

## CI 配置檢查 (.github/workflows/ci.yml)

### CI Pytest 命令
```yaml
# test-pinned job
- name: Run tests (skip integration)
  run: |
    python -m pytest tests/ -m "not integration" -v

# test-latest job
- name: Run tests (skip integration)
  run: |
    python -m pytest tests/ -m "not integration" -v

# test-integration job (僅 workflow_dispatch)
- name: Run integration tests
  run: |
    python -m pytest tests/ -m "integration" -v
```

**檢查結果:**
- ✅ CI 命令與 `pyproject.toml` `addopts` 一致使用 `-m 'not integration'`
- ✅ Integration 測試透過專門的 `test-integration` job 執行（需手動觸發）
- ✅ 無使用 `-k` keyword 過濾
- ✅ 無使用 `--deselect` 命令列過濾

## 11 個 Deselected 測試逐一驗證

### 實際 Collection 結果
執行命令: `python -X utf8 -m pytest tests/ -m "not integration" --collect-only -q --deselected-details`

```
156/167 tests collected (11 deselected)
```

### 測試清單與驗證結果

| # | Node ID | Marker 位置 | Skipif 條件 | 排除原因 | Marker 註冊 | 顯式排除 | 版本控制 |
|---|---------|-------------|-------------|----------|------------|----------|----------|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | test_domain.py:76 | test_domain.py:77 | deselected by -m 'not integration' | ✅ | ✅ | ✅ |
| 2 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | test_domain.py:62 | test_domain.py:63 | deselected by -m 'not integration' | ✅ | ✅ | ✅ |
| 3 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | test_e2e_acceptance.py:244 | 函式內 pytest.skip | deselected by -m 'not integration' | ✅ | ✅ | ✅ |
| 4 | `tests/test_gap.py::test_detect_gaps_real_grok` | test_gap.py:83 | test_gap.py:84 | deselected by -m 'not integration' | ✅ | ✅ | ✅ |
| 5 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | test_gap.py:106 | test_gap.py:107 | deselected by -m 'not integration' | ✅ | ✅ | ✅ |
| 6 | `tests/test_llm.py::test_grok_pong_integration` | test_llm.py:95 | test_llm.py:96 | deselected by -m 'not integration' | ✅ | ✅ | ✅ |
| 7 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | test_pipeline.py:151 | test_pipeline.py:152 | deselected by -m 'not integration' | ✅ | ✅ | ✅ |
| 8 | `tests/test_questions.py::test_generate_questions_real_grok` | test_questions.py:74 | test_questions.py:75 | deselected by -m 'not integration' | ✅ | ✅ | ✅ |
| 9 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | test_retrieve.py:102 | test_retrieve.py:103-104 (雙重 skipif) | deselected by -m 'not integration' | ✅ | ✅ | ✅ |
| 10 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | test_twinkle.py:166 | 函式內 pytest.skip | deselected by -m 'not integration' | ✅ | ✅ | ✅ |
| 11 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | test_write.py:63 | test_write.py:64 | deselected by -m 'not integration' | ✅ | ✅ | ✅ |

### 關鍵發現

#### Marker 使用模式
所有 11 個 deselected 測試都使用統一的標記模式:
```python
@pytest.mark.integration
@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")
def test_xxx():
    ...
```

例外情況:
- `test_e2e_acceptance_real`: 無 `@pytest.mark.skipif`，但函式內有 `pytest.skip` 條件檢查
- `test_search_real_twinkle_hub`: 無 `@pytest.mark.skipif`，但函式內有 `pytest.skip` 條件檢查
- `test_retrieve_for_gap_real_twinkle_smoke`: 使用雙重 `@pytest.mark.skipif` (LAW_DB + grok proxy)

#### 排除機制一致性
- **統一排除來源**: 所有測試的排除原因皆為 `deselected by -m 'not integration'`
- **配置來源**: 排除規則來自 `pyproject.toml` 的 `addopts = "-m 'not integration'"`
- **無其他過濾**: 無使用 `-k` keyword 過濾、`--deselect` 或目錄排除條件

## 問題檢查結果

### ❌ 未註冊 Marker
**狀態**: 無此問題
- `integration` marker 已在 `pyproject.toml` 中正確註冊
- 啟用 `--strict-markers` 會在未註冊 marker 使用時報錯

### ❌ 條件判斷錯誤
**狀態**: 無此問題
- 無 `pytest_collection_modifyitems` hook 動態修改測試集合
- 無條件式收集邏輯
- Skipif 條件僅影響執行階段，不影響 collection 階段的 deselected 判定

### ❌ 命令列過濾副作用
**狀態**: 無此問題
- CI 命令與 `pyproject.toml` `addopts` 一致
- 無使用 `-k` keyword 過濾
- 無使用 `--deselect` 命令列過濾
- 排除機制完全透過 marker 與配置檔案控制

## 驗證結論

### 通過項目
✅ 所有 11 個 deselected 測試都有 `@pytest.mark.integration` 標記
✅ `integration` marker 已在 `pyproject.toml` 中正確註冊
✅ 啟用 `--strict-markers` 確保未註冊 marker 會報錯
✅ 排除機制統一為 `pyproject.toml` `addopts = "-m 'not integration'"`
✅ CI 命令與 `pyproject.toml` 配置一致
✅ 無使用 `pytest_collection_modifyitems` 條件式收集
✅ 無使用 `-k` keyword 過濾
✅ 無使用 `--deselect` 命令列過濾
✅ 所有排除規則皆受版本控制（`pyproject.toml` 與測試檔案）

### 最終結論
所有 11 個 deselected 測試的排除規則皆為**顯式且受版本控制**，透過統一的 `@pytest.mark.integration` 標記與 `pyproject.toml` `addopts = "-m 'not integration'"` 排除機制實作，**無未註冊 marker、條件判斷錯誤或命令列過濾副作用問題**。

## 可重現驗證命令

### 檢查 Marker 註冊
```bash
python -X utf8 -m pytest --markers
```

### 執行 Collection 並查看 Deselected 詳細資訊
```bash
python -X utf8 -m pytest tests/ -m "not integration" --collect-only -q --deselected-details
```

### 僅收集 Integration 測試
```bash
python -X utf8 -m pytest tests/ -m integration --collect-only -q
```

### 驗證 CI Gate 腳本
```bash
python scripts/validate_deselection_ci.py
```

## 相關檔案
- Marker 定義: <ref_file file="D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\02fd69ec\pyproject.toml" />
- Conftest Hooks: <ref_file file="D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\02fd69ec\tests\conftest.py" />
- CI 配置: <ref_file file="D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\02fd69ec\.github\workflows\ci.yml" />
- Deselected Allowlist: <ref_file file="D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\02fd69ec\tests\deselected_allowlist.json" />
- 機器可讀驗證結果: <ref_file file="D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\02fd69ec\docs\deselected-marker-validation-2026-07-23.json" />
