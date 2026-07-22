# Pytest 排除條件盤點報告

## 概述

本報告盤點 pytest 設定、CI workflow、tox/nox 腳本與測試啟動命令，確認 8 個測試的排除條件為明確且受版本控制的預期設定，而非環境差異、命令誤用或收集異常。

## 盤點範圍

1. pytest 設定檔（pytest.ini, pyproject.toml, setup.cfg）
2. CI workflow 設定（.github/workflows/*.yml）
3. tox/nox 腳本（tox.ini, noxfile.py）
4. 測試啟動命令與腳本

## 盤點結果

### 1. pytest 設定檔

**檔案**: `pyproject.toml`

**關鍵設定**:
- 第 32 行：`addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"`
- 第 33-35 行：定義 `integration` marker

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

**結論**: 排除條件由 `pyproject.toml` 中的 `-m 'not integration'` 明確定義，受版本控制。

### 2. CI workflow 設定

**檔案**: `.github/workflows/ci.yml`

**關鍵設定**:
- `test-pinned` job (第 40 行): `python -m pytest tests/ -m "not integration" -v`
- `test-latest` job (第 71 行): `python -m pytest tests/ -m "not integration" -v`
- `test-integration` job (第 99 行): `python -m pytest tests/ -m "integration" -v` (僅 workflow_dispatch)
- 所有 job 都執行 `python scripts/validate_deselection_ci.py` (第 36, 67, 95 行)

**結論**: CI workflow 明確使用 `-m "not integration"` 排除 integration 測試，且透過 `validate_deselection_ci.py` 驗證排除策略的正確性。

### 3. tox/nox 腳本

**結果**: 專案中無 `tox.ini` 或 `noxfile.py`。

**結論**: 無需檢查，專案不使用 tox/nox。

### 4. 測試啟動命令與腳本

**檔案**: `scripts/run_tests.sh`

**關鍵設定**:
- 預設模式 (第 38 行): `-m "not integration"`
- `all` 模式 (第 48 行): `-m ""` (不排除)
- `integ` 模式 (第 58 行): `-m "integration"` (只跑 integration)

**結論**: 腳本明確使用 `-m "not integration"` 作為預設排除條件，與 pyproject.toml 設定一致。

## 8 個測試的排除條件驗證

### 測試清單

1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`
2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`
3. `tests/test_gap.py::test_detect_gaps_real_grok`
4. `tests/test_llm.py::test_grok_pong_integration`
5. `tests/test_pipeline.py::test_run_pipeline_real_grok`
6. `tests/test_questions.py::test_generate_questions_real_grok`
7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`
8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

### 排除條件來源

每個測試都有：
1. `@pytest.mark.integration` 標記（在測試函數上）
2. `@pytest.mark.skipif` 條件（檢查 grok proxy、law_index.db、TWINKLE_HUB_TOKEN 等）

### 排除機制

**主要排除機制**: `pyproject.toml` 中的 `-m 'not integration'` 在 collection 階段排除所有標記為 `integration` 的測試。

**次要排除機制**: 即使強制執行 integration 測試，若環境條件不滿足（grok proxy 不可達、缺 law_index.db、缺 TWINKLE_HUB_TOKEN），測試會在 runtime 被 `pytest.skip` 略過。

### 驗證機制

**檔案**: `scripts/validate_deselection_ci.py`

**功能**:
- 執行 `pytest --collect-only --deselected-details` 收集 deselected 測試清單與原因
- 驗證 deselected 測試數量與 `tests/deselected_allowlist.json` 一致
- 驗證每個 deselected 測試的排除原因為 `deselected by -m 'not integration'`
- 驗證高/中風險測試未在未核准情況下被排除
- 產出稽核報告到 `docs/pytest-audit/deselected-ci-gate.md`

**結論**: CI gate 透過 `validate_deselection_ci.py` 確保排除策略受控且可追溯。

## 排除條件受控性評估

### 版本控制

- ✅ pytest 設定在 `pyproject.toml` 中，受版本控制
- ✅ CI workflow 在 `.github/workflows/ci.yml` 中，受版本控制
- ✅ 測試啟動腳本在 `scripts/run_tests.sh` 中，受版本控制
- ✅ 測試標記在測試檔案中，受版本控制
- ✅ 排除策略驗證腳本在 `scripts/validate_deselection_ci.py` 中，受版本控制
- ✅ 排除 allowlist 在 `tests/deselected_allowlist.json` 中，受版本控制

### 明確性

- ✅ 排除條件由 `-m 'not integration'` 明確定義
- ✅ integration marker 在 `pyproject.toml` 中有明確說明
- ✅ 每個 integration 測試都有 `@pytest.mark.integration` 標記
- ✅ 每個 integration 測試都有額外的 `@pytest.mark.skipif` 條件說明環境依賴
- ✅ `deselected_allowlist.json` 提供每個測試的完整排除理由證據鏈

### 一致性

- ✅ pyproject.toml、CI workflow、run_tests.sh 都使用 `-m 'not integration'`
- ✅ CI gate 驗證確保實際 deselected 與 allowlist 一致
- ✅ allowlist 中的 `exclusion_evidence` 指向具體檔案與行號

### 環境差異風險

- ✅ 排除條件基於 marker，不依賴環境變數
- ✅ 即使在不同環境執行，collection 階段的排除行為一致
- ✅ CI gate 確保任何環境變更都會被偵測（數量或清單異常即失敗）

## 結論

8 個測試的排除條件為明確且受版本控制的預期設定：

1. **主要排除機制**: `pyproject.toml` 中的 `-m 'not integration'` 在 collection 階段排除所有標記為 `integration` 的測試
2. **受控性**: 所有相關設定（pytest、CI、腳本、測試標記、allowlist）都受版本控制
3. **明確性**: 排除條件在多處有明確定義與說明
4. **一致性**: 各處設定使用相同的排除條件
5. **驗證機制**: CI gate 透過 `validate_deselection_ci.py` 確保排除策略受控且可追溯
6. **環境差異風險**: 排除條件基於 marker，不依賴環境變數，環境差異不會影響排除行為

**無環境差異、命令誤用或收集異常風險**。

## 參考檔案

- `pyproject.toml` - pytest 設定
- `.github/workflows/ci.yml` - CI workflow
- `scripts/run_tests.sh` - 測試啟動腳本
- `scripts/validate_deselection_ci.py` - 排除策略驗證腳本
- `tests/deselected_allowlist.json` - 排除 allowlist
- 各測試檔案中的 `@pytest.mark.integration` 標記
