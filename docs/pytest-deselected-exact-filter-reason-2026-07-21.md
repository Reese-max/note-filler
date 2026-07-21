# pytest 設定／標記／deselected 確切篩選原因稽核

- **日期**：2026-07-21
- **工作目錄**：`D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\7d3662a0`
- **Python**：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`
- **pytest**：9.1.1（platform win32 / Python 3.11.9）
- **機器可讀索引**：[`docs/pytest-audit/trace-config-2026-07-21/deselected-reason-index.json`](pytest-audit/trace-config-2026-07-21/deselected-reason-index.json)
- **原始輸出目錄**：[`docs/pytest-audit/trace-config-2026-07-21/`](pytest-audit/trace-config-2026-07-21/)

> 本報告只做 **collection 層** 的 deselect 歸因。  
> runtime `skipif`／環境變數不足造成的 **skip** 屬執行期行為，不是本次 8 筆 deselected 的原因。

---

## 1. 設定來源（CLI／ini／env／markers）

### 1.1 `pyproject.toml` → `[tool.pytest.ini_options]`

| 鍵 | 值 | 作用 |
|---|---|---|
| `testpaths` | `["tests"]` | 只收集 `tests/` |
| `pythonpath` | `["src"]` | 本 checkout 的 `src` 優先於 venv editable |
| `addopts` | `-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning` | **預設 mark 篩選** + 關閉 asyncio plugin + 嚴格 marker + deprecation 當錯 |
| `markers` | `integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過` | 註冊唯一專案 marker |

**有效篩選表達式（預設）**：`markexpr = not integration`  
來源：`addopts` 內的 `-m 'not integration'`（`pyproject.toml` 第 32 行）。

### 1.2 `tests/conftest.py` 相關 hook

| hook / option | 作用 |
|---|---|
| `--deselected-details` | 在 terminal summary 列出每个 deselected nodeid 與原因 |
| `pytest_deselected` | 讀 `markexpr` / `keyword` / `--deselect`，寫入 `_deselected_details` |
| `pytest_terminal_summary` | 印出 `nodeid \| reason: deselected by ...` |

本次報告全部使用 `--deselected-details`，故原因字串可直接從輸出還原。

### 1.3 命令列參數（本次實跑）

所有命令均為 **collect-only**（不執行測試本體），避免超時：

```text
python -X utf8 -m pytest --markers
python -X utf8 -m pytest --trace-config --collect-only
python -X utf8 -m pytest --collect-only -q --deselected-details
python -X utf8 -m pytest --collect-only -q -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" --deselected-details
python -X utf8 -m pytest --collect-only -q -m integration --deselected-details
python -X utf8 -m pytest --collect-only -q -m "not integration" --deselected-details
# 反向：對每個 deselected nodeid 各跑三組
python -X utf8 -m pytest --collect-only -q --deselected-details <nodeid>
python -X utf8 -m pytest --collect-only -q -m integration --deselected-details <nodeid>
python -X utf8 -m pytest --collect-only -q -o "addopts=-p no:asyncio --strict-markers" <nodeid>
```

**未使用**：`-k`、`--deselect`、`PYTEST_ADDOPTS` 覆寫。

### 1.4 環境變數探測（唯讀，不影響 collection deselect）

來源：[`env-probe.json`](pytest-audit/trace-config-2026-07-21/env-probe.json)

| 項目 | 值 | 對 collection deselect 的影響 |
|---|---|---|
| `GROK_PROXY_REACHABLE` (127.0.0.1:8318) | `true` | **無**（僅 runtime skipif） |
| `TWINKLE_HUB_TOKEN_SET` | `true` | **無** |
| `GOV_AI_ENABLE_TWINKLE_MCP` | 未設定 (`null`) | **無**（retrieve smoke 真跑時函式內 skip） |
| `LAW_DB_EXISTS` (`data/law_index.db`) | `true` | **無** |

結論：即使 proxy／token／DB 齊備，**預設仍會 deselect 8 筆 integration**，因為篩選發生在 marker 表達式，不是環境探測。

### 1.5 `pytest --markers`（專案自訂）

原始輸出：[`markers.txt`](pytest-audit/trace-config-2026-07-21/markers.txt)

```text
@pytest.mark.integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過
```

另見內建 / 第三方：`anyio`、`skip`、`skipif`、`xfail`、`parametrize` 等。

### 1.6 `pytest --trace-config` 摘要

原始輸出：

- [`trace-config-only.txt`](pytest-audit/trace-config-2026-07-21/trace-config-only.txt)（`--trace-config --collect-only -q`）
- [`trace-config-collect-only-full.txt`](pytest-audit/trace-config-2026-07-21/trace-config-collect-only-full.txt)（無 `-q`）

| 項 | 值 |
|---|---|
| rootdir | 本 worktree |
| configfile | `pyproject.toml` |
| testpaths | `tests` |
| plugins | `anyio-4.14.2`（`asyncio` / `pytest_asyncio` 被 `-p no:asyncio` 關閉） |
| conftest | `tests/conftest.py` 已註冊 |
| 預設 collection | `collected 150 items / 8 deselected / 142 selected` |

---

## 2. Collection 計數與集合恆等式

| 命令條件 | selected | deselected | 摘要（去 ANSI） | 證據檔 |
|---|---:|---:|---|---|
| 無 markexpr（覆寫 addopts，保留 plugin/warning 設定） | 150 | 0 | `150 tests collected` | `collect-full-no-markexpr.txt` |
| **預設 addopts** | **142** | **8** | `142/150 tests collected (8 deselected)` | `collect-default.txt` |
| 明確 `-m "not integration"` | 142 | 8 | 同預設 | `collect-m-not-integration-explicit.txt` |
| 反向 `-m integration` | 8 | 142 | `8/150 tests collected (142 deselected)` | `collect-m-integration.txt` |

**集合恆等式（全部為 true，見 JSON `set_identities`）**：

1. `full \ default == integration_selected`（8 筆完全一致）
2. `default == explicit(-m "not integration")`
3. `default ∪ integration == full`
4. `default ∩ integration == ∅`

這證明：**唯一 collection 排除機制是 `-m 'not integration'`**，沒有第二層 `-k`／`--deselect`／路徑忽略。

---

## 3. 每個 deselected 測試的確切篩選原因

下列 8 筆的 **確切 collection 原因完全相同**：

> **deselected by mark expression `-m 'not integration'`**  
> 來源：`pyproject.toml` `[tool.pytest.ini_options].addopts`  
> hook 回報字串：`deselected by -m 'not integration'`（`--deselected-details`）

**不是** collection 原因（即使標記／函式內存在）：`skipif`、proxy 不可達、缺 `TWINKLE_HUB_TOKEN`、缺 `law_index.db`、`GOV_AI_ENABLE_TWINKLE_MCP`。那些只會在 **取消 mark 篩選並實際執行** 時變成 skip。

| # | nodeid | `@pytest.mark.integration` 位置 | hook 原因 | 反向驗證（def / integ / nomark） |
|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `tests/test_domain.py:50` | `-m 'not integration'` | 0 sel / 1 des · 1 sel · 1 sel |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py:244` | `-m 'not integration'` | 0 sel / 1 des · 1 sel · 1 sel |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `tests/test_gap.py:71` | `-m 'not integration'` | 0 sel / 1 des · 1 sel · 1 sel |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `tests/test_llm.py:66` | `-m 'not integration'` | 0 sel / 1 des · 1 sel · 1 sel |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `tests/test_pipeline.py:151` | `-m 'not integration'` | 0 sel / 1 des · 1 sel · 1 sel |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `tests/test_questions.py:62` | `-m 'not integration'` | 0 sel / 1 des · 1 sel · 1 sel |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py:102` | `-m 'not integration'` | 0 sel / 1 des · 1 sel · 1 sel |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `tests/test_twinkle.py:141` | `-m 'not integration'` | 0 sel / 1 des · 1 sel · 1 sel |

### 3.1 反向篩選協議（逐 nodeid）

對每個 deselected nodeid 執行三組 **collect-only** 對照：

| 組 | 命令意圖 | 預期 | 8/8 結果 |
|---|---|---|---|
| A 預設 filter | 預設 addopts + 指定 nodeid | `no tests collected (1 deselected)`，details 含 `-m 'not integration'` | 全部 ok |
| B 反向 marker | `-m integration` + 指定 nodeid | `1 test collected` | 全部 ok |
| C 無 markexpr | 覆寫 addopts 去掉 `-m` + 指定 nodeid | `1 test collected`（證明節點存在，僅 markexpr 排除它） | 全部 ok |

逐檔證據命名：

- `reverse-default-<test_name>.txt`
- `reverse-integ-<test_name>.txt`
- `reverse-nomark-<test_name>.txt`

### 3.2 預設 collect 的 hook 原文（完整 8 行）

來源：[`collect-default.txt`](pytest-audit/trace-config-2026-07-21/collect-default.txt)

```text
============================= deselected details ==============================
tests/test_domain.py::test_detect_domain_real_grok_returns_law | reason: deselected by -m 'not integration'
tests/test_e2e_acceptance.py::test_e2e_acceptance_real | reason: deselected by -m 'not integration'
tests/test_gap.py::test_detect_gaps_real_grok | reason: deselected by -m 'not integration'
tests/test_llm.py::test_grok_pong_integration | reason: deselected by -m 'not integration'
tests/test_pipeline.py::test_run_pipeline_real_grok | reason: deselected by -m 'not integration'
tests/test_questions.py::test_generate_questions_real_grok | reason: deselected by -m 'not integration'
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke | reason: deselected by -m 'not integration'
tests/test_twinkle.py::test_search_real_twinkle_hub | reason: deselected by -m 'not integration'
142/150 tests collected (8 deselected) in 0.18s
```

---

## 4. 結論（可稽核）

1. **deselected 數量**：8（總 150；預設 selected 142）。
2. **每一筆的確切篩選原因**：節點帶 `@pytest.mark.integration`，被 `pyproject.toml` `addopts` 的 **`-m 'not integration'`** 在 collection 階段排除。
3. **沒有其他 collection 篩選源**：無 `-k`、無 `--deselect`、無路徑 ignore、env 不參與 deselect。
4. **反向篩選**：`-m integration` 正好選中同一 8 筆；去掉 markexpr 後 8 筆皆可單獨收集。
5. **整合測試平時跳過** 的行為符合專案設計與品質閘（integration 需 grok `:8318`；平時不進預設門）。

---

## 5. 產物清單（可重現）

| 路徑 | 內容 |
|---|---|
| `docs/pytest-deselected-exact-filter-reason-2026-07-21.md` | 本報告 |
| `docs/pytest-audit/trace-config-2026-07-21/deselected-reason-index.json` | 機器可讀索引（設定、計數、集合恆等式、8 筆原因、反向結果） |
| `docs/pytest-audit/trace-config-2026-07-21/env-probe.json` | 環境探測 |
| `docs/pytest-audit/trace-config-2026-07-21/markers.txt` | `--markers` 原始輸出 |
| `docs/pytest-audit/trace-config-2026-07-21/trace-config-*.txt` | `--trace-config` 原始輸出 |
| `docs/pytest-audit/trace-config-2026-07-21/collect-*.txt` | 各篩選條件 collect 輸出 |
| `docs/pytest-audit/trace-config-2026-07-21/reverse-*.txt` | 8×3 反向篩選 collect 輸出 |

### 重現命令（最小）

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
& $py -X utf8 -m pytest --markers
& $py -X utf8 -m pytest --trace-config --collect-only -q
& $py -X utf8 -m pytest --collect-only -q --deselected-details
& $py -X utf8 -m pytest --collect-only -q -m integration --deselected-details
```
