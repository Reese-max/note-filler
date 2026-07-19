# 8 個 deselected：pytest 設定／markers 文件化缺口稽核

> **任務**：針對 `pytest -m "not integration" -q` 產生的 8 個 `deselected`，比對目前 pytest 設定與 markers 定義，判定是否仍有**未被明確文件化的排除條件**或**新出現的篩選規則**。  
> **驗證日**：2026-07-19  
> **HEAD（撰寫前）**：`60a23f4e2653f8f211c59d59292266648959910f`  
> **Python**：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`  
> **範圍**：僅本 worktree；不改 `BACKLOG.md`、不新增任務、不變更篩選邏輯本身。

---

## 1. 結論（先講）

| 判定項 | 結果 | 證據 |
|---|---|---|
| 是否存在**未文件化**的 collection 排除條件？ | **否** | 8/8 原因皆為 `deselected by -m 'not integration'` |
| 是否出現**新的**篩選規則（超越既有 integration marker）？ | **否** | 無 `pytest_collection_modifyitems` / `pytest_ignore_collect` / 預設 `--deselect` / `PYTEST_ADDOPTS` |
| 唯一 collection 層 deselect 機制 | **`addopts`／CLI 的 `-m 'not integration'`** | `pyproject.toml:32` + `--deselected-details` |
| markers 定義是否完整覆蓋 8 項？ | **是** | 僅註冊 `integration`；源碼恰 8 處 `@pytest.mark.integration` |
| allowlist 是否與實況一致？ | **是** | `tests/deselected_allowlist.json` 8 ids ≡ 實跑 deselected |
| 文件化缺口 | **無 collection 層缺口**；歷史報告中的「總測試數」可能過時，但 **8-node 集合穩定** | 見 §5 |

**一句話**：目前 8 個 `deselected` 仍完全由已文件化的 `integration` marker + `-m 'not integration'` 造成；未發現第二道隱藏篩選器，也未發現新規則。

---

## 2. 可重現命令與計數（本輪實跑）

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
$env:PYTHONIOENCODING = "utf-8"

# (A) 任務指定等價：明確 -m "not integration"
& $py -X utf8 -m pytest -m "not integration" -q --collect-only --deselected-details --color=no

# (B) 全量收集（去掉 mark 過濾，保留其餘 addopts 品質閘）
& $py -X utf8 -m pytest --collect-only -q --color=no `
  -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning"

# (C) 僅 integration
& $py -X utf8 -m pytest --collect-only -q -m integration --color=no `
  -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning"

# (D) 預設 addopts（已含 -m 'not integration'）
& $py -X utf8 -m pytest --collect-only -q --deselected-details --color=no
```

| 命令 | collected | selected | deselected | 原始輸出 |
|---|---:|---:|---:|---|
| (A) `-m "not integration"` | 145 | 137 | **8** | [`docs/pytest-audit/deselect-doc-gap-collect-A-2026-07-19.txt`](pytest-audit/deselect-doc-gap-collect-A-2026-07-19.txt) |
| (B) 無 mark 過濾 | 145 | 145 | 0 | [`docs/pytest-audit/deselect-doc-gap-collect-B-full-2026-07-19.txt`](pytest-audit/deselect-doc-gap-collect-B-full-2026-07-19.txt) |
| (C) `-m integration` | 145 | **8** | 137 | [`docs/pytest-audit/deselect-doc-gap-collect-C-integration-2026-07-19.txt`](pytest-audit/deselect-doc-gap-collect-C-integration-2026-07-19.txt) |
| (D) 預設 addopts | 145 | 137 | **8** | [`docs/pytest-audit/deselect-doc-gap-collect-D-default-2026-07-19.txt`](pytest-audit/deselect-doc-gap-collect-D-default-2026-07-19.txt) |

**集合等式（已機器驗證）**：

- deselected(A) **==** selected(C) **==** allowlist 8 ids  
- selected(A) ∪ deselected(A) **==** collected(B) = 145  
- (A) 與 (D) 計數與 8 node 完全一致（CLI 再傳 `-m "not integration"` 與 addopts 不疊加第二道不同規則）

機器索引：[`docs/pytest-audit/deselect-doc-gap-index-2026-07-19.json`](pytest-audit/deselect-doc-gap-index-2026-07-19.json)

輕量 guard（本輪）：

```text
tests/test_deselection_guard.py::test_integration_allowlist_is_stable PASSED
tests/test_deselection_guard.py::test_deselected_details_lists_node_ids_and_reasons PASSED
2 passed in 4.81s
```

---

## 3. 設定與 markers 對照（現況）

### 3.1 `pyproject.toml` `[tool.pytest.ini_options]`

| 鍵 | 值 | 與 deselect 關係 |
|---|---|---|
| `testpaths` | `["tests"]` | 只決定收集根；**不**製造 8 項差集 |
| `pythonpath` | `["src"]` | import；不參與 selection |
| **`addopts`** | `-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning` | **唯一 collection 排除來源**：`-m 'not integration'` |
| **`markers`** | `integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過` | 合法 marker 宣告；配合 `--strict-markers` |
| 其他 markers | **無** | 專案自訂 marker 只有 `integration`（`anyio` 來自 plugin，非排除用） |

### 3.2 源碼 `@pytest.mark.integration` 錨點（恰 8 處）

| # | node ID | 標記行 |
|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `tests/test_domain.py:50` |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `tests/test_e2e_acceptance.py:244` |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `tests/test_gap.py:71` |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `tests/test_llm.py:66` |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `tests/test_pipeline.py:151` |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `tests/test_questions.py:62` |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_retrieve.py:102` |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `tests/test_twinkle.py:122` |

### 3.3 `--deselected-details` 原始原因（8/8 相同）

```
tests/test_domain.py::test_detect_domain_real_grok_returns_law | reason: deselected by -m 'not integration'
tests/test_e2e_acceptance.py::test_e2e_acceptance_real | reason: deselected by -m 'not integration'
tests/test_gap.py::test_detect_gaps_real_grok | reason: deselected by -m 'not integration'
tests/test_llm.py::test_grok_pong_integration | reason: deselected by -m 'not integration'
tests/test_pipeline.py::test_run_pipeline_real_grok | reason: deselected by -m 'not integration'
tests/test_questions.py::test_generate_questions_real_grok | reason: deselected by -m 'not integration'
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke | reason: deselected by -m 'not integration'
tests/test_twinkle.py::test_search_real_twinkle_hub | reason: deselected by -m 'not integration'
```

---

## 4. 潛在「隱藏篩選」檢查清單

| 檢查項 | 本輪結果 | 說明 |
|---|---|---|
| `pytest_collection_modifyitems` | **未使用** | `tests/` 內無此 hook |
| `pytest_ignore_collect` / `collect_ignore` | **未使用** | 無 |
| CLI `--deselect` | **未使用** | 預設閘與本輪命令皆無 |
| CLI `-k` | **未使用** | 無 keyword 篩選 |
| env `PYTEST_ADDOPTS` | **未設定** | 本輪 process 僅見 `PYTHONIOENCODING` / `PYTHONUTF8` |
| env `PYTEST_PLUGINS` / `PYTEST_DISABLE_PLUGIN_AUTOLOAD` | **未設定** | 無外掛注入 selector |
| `tests/conftest.py` hooks | **僅觀測** | `pytest_deselected` / `pytest_terminal_summary` 讀既成結果，不改 collection |
| 路徑縮篩（只跑子目錄） | **否** | 全 `tests/` |
| 第二個自訂 marker 參與預設排除 | **否** | markers 清單只有 `integration` |
| `skipif` / `pytest.skip` | **非 deselect** | 屬 **runtime**；預設閘下 8 項根本未進入執行，原因是 mark deselect |

### 4.1 deselect vs skip 邊界（避免文件誤讀）

- **Collection deselect（本任務焦點）**：item 帶 `integration` → 不滿足 `not integration` → 不進入 selected 集合。  
- **Runtime skip（若以 `-m integration` 選入後）**：grok `:8318`、`data/law_index.db`、`TWINKLE_HUB_TOKEN` 等條件才可能 skip。  
- 後者**不是** `pytest -m "not integration"` 的 8 個 deselected 原因；已於 allowlist 與既有規則報告中分開記載。

---

## 5. 既有文件化狀態 vs 本輪

| 文件／產物 | 是否涵蓋「唯一排除 = not integration」 | 與本輪差異 |
|---|---|---|
| `pyproject.toml` addopts + markers | 是（設定本體） | 無變更 |
| `tests/deselected_allowlist.json` | 是（8 node + 證據錨） | 與實跑全等 |
| `tests/test_deselection_guard.py` | 是（鎖定 145/137/8） | guard 通過 |
| `docs/testing-guide.md` | 是（模式表 137+8） | 總數敘述與本輪一致 |
| `docs/deselected-8-nodeids-rules-2026-07-19.md` | 是 | 文中曾記 143；**suite 已增至 145**，8-node 不變 |
| 較舊盤點（如 2026-07-18 的 109/117） | 規則正確、計數過時 | **非新規則**，屬歷史快照 |

**文件化缺口判定**：

1. **Collection 排除條件**：已在設定、allowlist、guard、testing-guide、多份 audit 中明確記載 → **無未文件化排除條件**。  
2. **新篩選規則**：本輪對設定、hooks、env、markers、集合等式的交叉比對 → **無新規則**。  
3. **唯一需注意的「文件陳舊」**：部分歷史 md 的 **collected 總數** 落後於現況（145）；這不改變 8 個 deselected 的成因與身份。本報告與 JSON 索引以 145/137/8 為準。

---

## 6. 判定摘要表（對任務問題的直接答覆）

| 問題 | 答覆 |
|---|---|
| 8 個 deselected 是誰？ | 上表 8 個 integration node（= allowlist） |
| 為何 deselected？ | 唯一：`-m 'not integration'`（addopts 與任務 CLI 等價） |
| markers 定義是否與行為對齊？ | 是：只宣告 `integration`；8 標記 = 8 deselected |
| 還有沒有沒寫清楚的排除條件？ | **沒有**（collection 層） |
| 有沒有新出現的篩選規則？ | **沒有** |
| 是否需要改 pytest 設定？ | **本任務否**（調查結論：現況正確且已文件化） |

---

## 7. 交付清單（可稽核）

| 路徑 | 角色 |
|---|---|
| `docs/deselect-exclusion-doc-gap-audit-2026-07-19.md` | 本報告（結論） |
| `docs/pytest-audit/deselect-doc-gap-index-2026-07-19.json` | 機器可讀索引（等式、node、判定） |
| `docs/pytest-audit/deselect-doc-gap-collect-A-2026-07-19.txt` | (A) 原始 collect 輸出 |
| `docs/pytest-audit/deselect-doc-gap-collect-B-full-2026-07-19.txt` | (B) 全量 collect |
| `docs/pytest-audit/deselect-doc-gap-collect-C-integration-2026-07-19.txt` | (C) integration 集合 |
| `docs/pytest-audit/deselect-doc-gap-collect-D-default-2026-07-19.txt` | (D) 預設 addopts |

**未改動**：`BACKLOG.md`、pytest 篩選邏輯、測試本體、allowlist 內容（因與實況一致，無需為「補文件缺口」而改規則）。
