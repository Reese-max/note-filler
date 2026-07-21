# 驗收 pytest 參數與 8 個 deselected 規則稽核

> 驗證日期：2026-07-21
> 調查基準：`e2d08f6` 及其目前工作樹
> 範圍：驗收入口、pytest 設定來源、環境選項、平台／相依套件條件，以及 8 個 deselected 測試

## 結論

8 個測試的直接篩除原因完全相同：它們都帶有
`@pytest.mark.integration`，而驗收的有效 marker 表達式是
`-m "not integration"`。它們是在 collection 階段被 **deselected**，不是因
Grok、Twinkle、法規資料庫、平台或套件條件而 **skipped**。

本次 live collection 結果為：全量 `150`、預設選入 `142`、
`8 deselected`；integration-only 集合恰好就是這 8 個 node ID。

## 驗收指令實際吃到的參數

本機明確驗收指令為：

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest -m "not integration" -q
```

其中兩個 `-m` 不同：

- Python 的 `-m pytest` 是以模組啟動 pytest，不是測試篩選器。
- pytest 的 `-m "not integration"` 才是 marker 篩選器。
- `-q` 只控制輸出詳細度，不影響測試集合。

三個 repo 入口最後使用同一個測試集合：

| 入口 | 明列的 pytest 參數 | 與設定合併後的選擇結果 |
|---|---|---|
| 本機明確驗收 | `-m "not integration" -q` | `142 selected / 8 deselected` |
| `.github/workflows/ci.yml` 的 pinned/latest job | `tests/ -m "not integration" -v` | `142 selected / 8 deselected` |
| `scripts/run_tests.sh` 預設／`unit` 模式 | `tests/ -m "not integration" -v`，另保留 `PYTEST_EXTRA` 輸入 | `PYTEST_EXTRA` 未設定時同上 |

`tests/` 與 `pyproject.toml` 的 `testpaths = ["tests"]` 指向同一範圍；
`-q`／`-v` 僅改變輸出。`pyproject.toml` 已含同一個
`-m 'not integration'`，明確驗收與 CI 再寫一次相同表達式不會改變結果；
有效值仍是 `not integration`。

## 設定來源盤點

| 候選來源 | 實際狀態 | 是否改變選擇 |
|---|---|---|
| `pytest.ini` | 不存在 | 否 |
| `.pytest.ini` | 不存在 | 否 |
| `tox.ini` | 不存在 | 否；也沒有 tox env 注入參數 |
| `setup.cfg` | 不存在 | 否 |
| 根目錄 `conftest.py` | 不存在 | 否 |
| `pyproject.toml` | pytest 唯一設定檔 | 是；提供預設 `-m 'not integration'` |
| `tests/conftest.py` | 存在 | 只新增 `--deselected-details`、原因輸出與 fixture，不修改集合 |

`pyproject.toml` 的有效 pytest 設定是：

```toml
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

以指定 venv 啟動 pytest 並在 `pytest_configure` 讀取的有效值為：

```text
inifile=pyproject.toml
ini_addopts=['-p', 'no:asyncio', '--strict-markers', '-m', 'not integration', '-W', 'error::DeprecationWarning', '-W', 'error::PendingDeprecationWarning']
ini_testpaths=['tests']
ini_pythonpath=['src']
markexpr='not integration'
keyword=''
strict_markers=True
pythonwarnings=['error::DeprecationWarning', 'error::PendingDeprecationWarning']
asyncio_plugin_loaded=False
```

因此：

- 沒有 `-k`：有效 `keyword=''`。
- 沒有 `--deselect`。
- `--strict-markers` 已啟用，`integration` 也已註冊；marker 拼錯會使驗收失敗。
- 兩種 deprecation warning 仍視為錯誤；本次沒有弱化品質閘。
- `tests/conftest.py` 沒有 `pytest_collection_modifyitems`，其
  `pytest_deselected` hook 只記錄 pytest 已決定排除的項目與原因。

## 環境、平台與相依套件快照

本次只保存環境變數是否設定，不保存 token 值。

| 項目 | 2026-07-21 本機狀態 | 對 8 個 deselected 的影響 |
|---|---|---|
| `PYTEST_ADDOPTS` | 未設定 | 沒有額外 `addopts`、`-m` 或 `-k` |
| `PYTEST_EXTRA` | 未設定 | `scripts/run_tests.sh` 沒有額外篩選參數 |
| `PYTEST_PLUGINS` | 未設定 | 沒有環境注入 plugin |
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD` | 未設定 | 不改變 marker 選擇；`-p no:asyncio` 仍由 repo 設定生效 |
| `TOX_ENV_NAME` | 未設定 | 沒有 tox 環境 |
| `PYTHON` | 未設定 | 腳本未被環境覆寫 Python；本次命令直接指定主專案 venv |
| 平台 | Windows、Python `3.11.9` | 8 個測試都沒有平台 selector |
| `TWINKLE_HUB_TOKEN` | 已設定，值未保存 | 只影響被選入後的 runtime skip |
| `GOV_AI_ENABLE_TWINKLE_MCP` | 未設定 | 目前 8 個測試沒有以此變數篩選 |
| `data/law_index.db` | 存在 | 只影響相關測試被選入後是否 skip |
| Grok `127.0.0.1:8318` | TCP 可達 | 只影響相關測試被選入後是否 skip |

指定 venv 的必要套件可匯入，版本為：`pytest 9.1.1`、`pluggy 1.6.0`、
`fastapi 0.139.2`、`starlette 1.3.1`、`httpx 0.28.1`、`anyio 4.14.2`、
`python-docx 1.2.0`。專案宣告 `requires-python = ">=3.11"`，目前
Python `3.11.9` 符合。若必要套件缺少，結果會是 import／collection error，
不是把這 8 個測試 deselect；目前沒有此情形。

## 8 個測試逐項篩除規則

下表的「直接 deselection 規則」才是本次預設驗收沒執行該測試的原因；
「選入後的 runtime 條件」只在改用 `-m integration` 或清空 marker 表達式後生效。

| # | 完整 node ID | marker 位置 | 直接 deselection 規則 | 選入後的 runtime 條件 |
|---:|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `tests/test_domain.py:50` | `integration` 不符合 `not integration` | `tests/test_domain.py:51`：Grok `127.0.0.1:8318` 不可達則 `skipif` |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py:244` | `integration` 不符合 `not integration` | `tests/test_e2e_acceptance.py:247-255`：缺 `data/law_index.db`，或 Grok 不可達，或沒有 `TWINKLE_HUB_TOKEN` 時 `pytest.skip()` |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `tests/test_gap.py:71` | `integration` 不符合 `not integration` | `tests/test_gap.py:72`：Grok 不可達則 `skipif` |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `tests/test_llm.py:66` | `integration` 不符合 `not integration` | `tests/test_llm.py:67`：Grok 不可達則 `skipif` |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `tests/test_pipeline.py:151` | `integration` 不符合 `not integration` | `tests/test_pipeline.py:152`：Grok 不可達則 `skipif`；`python-docx` 是 collection import 前置，不是 skip 規則 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `tests/test_questions.py:62` | `integration` 不符合 `not integration` | `tests/test_questions.py:63`：Grok 不可達則 `skipif` |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py:102` | `integration` 不符合 `not integration` | `tests/test_retrieve.py:103-108`：缺 law DB、Grok 不可達或沒有 `TWINKLE_HUB_TOKEN` 則 skip |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `tests/test_twinkle.py:141` | `integration` 不符合 `not integration` | `tests/test_twinkle.py:145-147`：沒有 `TWINKLE_HUB_TOKEN` 則 `pytest.skip()`；沒有平台條件 |

本次環境雖同時具備 Grok、token 與 law DB，預設驗收仍會先依
`-m "not integration"` deselect 這 8 個測試。環境就緒不會覆蓋 marker
表達式；也不能據此聲稱 8 個 integration 測試已執行或通過。

## 可重現證據

### 1. 預設集合與逐項原因

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -q --deselected-details --color=no
```

```text
142/150 tests collected (8 deselected)
tests/test_domain.py::test_detect_domain_real_grok_returns_law | reason: deselected by -m 'not integration'
tests/test_e2e_acceptance.py::test_e2e_acceptance_real | reason: deselected by -m 'not integration'
tests/test_gap.py::test_detect_gaps_real_grok | reason: deselected by -m 'not integration'
tests/test_llm.py::test_grok_pong_integration | reason: deselected by -m 'not integration'
tests/test_pipeline.py::test_run_pipeline_real_grok | reason: deselected by -m 'not integration'
tests/test_questions.py::test_generate_questions_real_grok | reason: deselected by -m 'not integration'
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke | reason: deselected by -m 'not integration'
tests/test_twinkle.py::test_search_real_twinkle_hub | reason: deselected by -m 'not integration'
```

完整原始 collection 輸出另見：

- `docs/evidence/pytest-collect-only-q.txt`
- `docs/evidence/pytest-collect-only-q-vv.txt`
- `docs/evidence/pytest-collect-only-integration-only.txt`
- `docs/evidence/deselected-8-with-marks.json`

### 2. 全量與 integration-only 對照

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -q -o addopts= --strict-markers --color=no
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -q -o addopts= --strict-markers -m integration --color=no
```

```text
150 tests collected
8/150 tests collected (142 deselected)
```

這裡的 `-o addopts=` 僅用於建立全量對照，隨即明列
`--strict-markers`；正式驗收仍使用 `pyproject.toml` 的完整 `addopts`，沒有
移除 warning gate 或 plugin 設定。

### 3. Repo 既有 guard

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 scripts/validate_deselection_ci.py
```

```text
[gate] total=150 selected=142 deselected=8
[gate] PASS: deselected policy 核驗通過
```

guard 產物已刷新至 `docs/pytest-audit/deselected-ci-gate.md`，其中逐項保存
node ID、`deselected by -m 'not integration'`、風險等級與 allowlist 決策。

### 4. 最小關聯回歸

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_deselection_guard.py::test_integration_allowlist_is_stable tests/test_deselection_guard.py::test_deselected_details_lists_node_ids_and_reasons tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_accepts_only_authorized_deselected_nodes_with_reasons -q --color=no
```

```text
3 passed in 7.25s
```

## 本次變更邊界

- 更新本報告、測試指南的現行數量／integration 指令，以及既有 guard 產物。
- 未修改 `pyproject.toml`、CI、`conftest.py`、任何 marker、測試或產品程式碼。
- 未執行 8 個 integration 測試；本任務只驗證 collection／selection 規則。
