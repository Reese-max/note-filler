# Testing Guide

## 兩種測試模式

本專案的測試分為兩類，**明確以 `@pytest.mark.integration` 標記分界**：

| 模式 | 數量 | 預設行為 | 需要外部服務 |
|------|------|---------|-------------|
| **非整合測試**（unit/integration=off） | 109 | 預設執行 | 否（FakeLLM/mocked） |
| **整合測試**（integration=on） | 8 | 預設跳過 | 是（grok proxy :8318, Twinkle Hub） |

### 非整合測試（CI 預設）

不需要任何外部服務。所有 LLM 呼叫使用 `FakeLLM`，外部 API 使用 monkeypatch。
這是 CI（GitHub Actions）與日常開發唯一執行的測試集合。

```bash
# 等效指令（三選一）：
pytest                                    # pyproject.toml addopts 已內含 -m 'not integration'
pytest -m "not integration" -v           # 明確寫出排除條件
./scripts/run_tests.sh                   # 透過腳本執行
```

**109 個測試，全部不需要網路或 grok proxy。**

### 顯示 deselected 詳情

需要追溯被排除的完整 node ID 與選擇器原因時，加入 `--deselected-details`：

```bash
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest --collect-only -q --deselected-details
```

目前預設輸出會列出 8 個 integration node ID，原因為 `-m 'not integration'`。
稽核腳本也會將同一份原始輸出保存至 `docs/pytest-audit/deselected-details.txt`。

### 完整測試（含整合）

包含上述 109 個 + 8 個整合測試。整合測試**依賴本機 grok proxy**（`http://127.0.0.1:8318`）。
若 grok proxy 不在線，整合測試會被 `skipif` 安全跳過（不報失敗）。

```bash
# 一鍵跑完整套件（整合測試不在線時自動跳過）：
./scripts/run_tests.sh all

# 只跑整合測試：
./scripts/run_tests.sh integ

# 明確的 pytest 指令：
pytest -m "" -v                          # 清空 marker 過濾，跑全部
pytest -m "integration" -v               # 只跑整合測試
```

### 整合測試前提條件

| 服務 | 位址 | 檢查方式 |
|------|------|---------|
| Grok proxy (Hermes/xAI) | `127.0.0.1:8318` | `python -c "import socket; s=socket.create_connection(('127.0.0.1',8318),2); s.close(); print('OK')"` |
| Twinkle Hub Token | env `TWINKLE_HUB_TOKEN` | `echo $TWINKLE_HUB_TOKEN` |
| Twinkle MCP flag | env `GOV_AI_ENABLE_TWINKLE_MCP` | `echo $GOV_AI_ENABLE_TWINKLE_MCP` |

## CI 行為（GitHub Actions）

CI 只執行**非整合測試**，分兩個矩陣：

| Job | Python 版本 | 約束 | 指令 |
|-----|------------|------|------|
| `test-pinned` | 3.11, 3.12 | `constraints-pinned.txt` | `pytest -m "not integration" -v` |
| `test-latest` | 3.11, 3.12, 3.13 | 最新相容版 | `pytest -m "not integration" -v` |
| `test-integration` | 3.12 | workflow_dispatch 手動觸發 | `pytest -m "all" -v` |

**標準 CI 流程（push/PR）不會跑整合測試。** 整合測試需透過 `workflow_dispatch` 手動觸發，
或在有 grok proxy 的本機環境手動執行。

## 如何避免「把應跑的回歸誤排除」

### 規則

1. **所有新測試必須明確標記**：需要外部服務的測試加 `@pytest.mark.integration`；
   純單元測試**不要**加此 marker。
2. **CI 只跑 `not integration`**：這是防線——CI 永遠跑 109 個非整合測試。
3. **整合測試雙重防護**：除了 marker，整合測試還有 `@pytest.mark.skipif(not _grok_reachable())`
   在運行時檢查——即使 marker 被誤移除，grok 不在線時仍安全跳過。
4. **新增整合測試時**：必須同時滿足以下兩項才正確：
   - 函式上有 `@pytest.mark.integration` 裝飾器
   - 函式內或 `@pytest.mark.skipif` 有運行時環境檢查

### 新增測試時的檢查清單

- [ ] 測試是否需要 grok proxy 或網路？→ 是 = 加 `@pytest.mark.integration`
- [ ] 測試是否純 FakeLLM/mocked？→ 是 = **不加** integration marker
- [ ] 執行 `pytest --co -q -o addopts=` 確認 `collected` 數量符合預期（117 total）
- [ ] 執行 `pytest -m "not integration" --co -q` 確認排除數量（109 selected, 8 deselected）
- [ ] 執行 `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 scripts/refresh_pytest_audit.py` 產生逐項 source anchor 與 `PASSED` 證據

## 本地快速指令

```bash
# 日常開發（推薦）：
pytest -v

# 完整回歸（手動）：
./scripts/run_tests.sh all

# 確認測試清單（不執行）：
./scripts/run_tests.sh check

# 重建 collection、marker 與逐項測試結果稽核檔：
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 scripts/refresh_pytest_audit.py
```

`tests/deselected_allowlist.json` 的每項 `decision` 必須是
`acceptable_unexecuted`，並同時列出 `exclusion_evidence`（排除 marker／runtime
前置條件的程式碼 anchor）與 `substitute_evidence`（替代測試斷言的程式碼 anchor）。
guard 會檢查 anchor 仍存在，且替代測試實際通過；產生的逐項結論見
[`docs/pytest-audit/deselected-evidence.md`](pytest-audit/deselected-evidence.md)。

## 相關文件

- `docs/integration-test-audit.md` — 整合測試排除清單審查（2026-07-16）
- `docs/integration-exclusion-audit.md` — marker 一致性修正（2026-07-17）
- `docs/pytest-audit/` — 最新 collection、marker、測試結果與機器可讀清單
- `docs/pytest-audit/deselected-evidence.md` — 每個 `deselected` 的程式碼與測試輸出追溯鏈
- `pyproject.toml` `[tool.pytest.ini_options]` — pytest 設定與 marker 定義
