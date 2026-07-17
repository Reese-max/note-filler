# Integration Marker 排除一致性審計

**日期**：2026-07-17

## 審查範圍

| 檔案 | 狀態 |
|---|---|
| `pyproject.toml` | 有 marker 定義，`addopts` 修正 |
| `tests/conftest.py` | 無預設過濾邏輯（正確，靠 addopts） |
| CI workflows | 不存在（無 `.github/workflows/`） |
| `tox.ini` / `pytest.ini` | 不存在 |

## 發現

### 問題：`addopts` 未排除 `integration` 測試

- `pyproject.toml:34` 定義了 `integration` marker，註解寫「平時用 `-m 'not integration'` 跳過」
- 但 `pyproject.toml:32` 的 `addopts` 只有 `-p no:asyncio` 與 deprecation warning flags，**缺少 `-m 'not integration'`**
- 本地跑 `pytest` 會把 8 個需要真實 grok proxy 的整合測試全部拉進來

### 受影響的測試（8 個）

全部在 `tests/` 下，分佈在 8 個檔案：
- `test_domain.py::test_evaluate_domain_real_grok`
- `test_e2e_acceptance.py::test_e2e_full_pipeline_real_grok`
- `test_gap.py::test_identify_gaps_real_grok`
- `test_llm.py::test_call_grok_real`
- `test_pipeline.py::test_full_pipeline_real_grok`
- `test_questions.py::test_generate_questions_real_grok`
- `test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`
- `test_twinkle.py::test_search_real_twinkle_hub`

## 修正

在 `addopts` 加入 `-m 'not integration'`：

```toml
addopts = "-p no:asyncio -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
```

## 驗證結果

| 指令 | 預期 | 實際 |
|---|---|---|
| `pytest --co -q` | 收集 102 個、跳過 8 個 | ✅ 102/110 collected, 8 deselected |
| `pytest -m integration --co -q` | 只收集 8 個 integration | ✅ 8/110 collected, 102 deselected |

**結論**：本地與 CI（若未來加入）現在都預設排除 integration 測試；需要時可用 `pytest -m integration` 顯式執行。
