# 失敗語義局部重跑與錯誤注入驗證證據

> 產出日期：2026-07-22  
> 對應報告：`docs/deselected-failure-semantic-coverage-2026-07-22.md`  
> 方法論：對高風險整合測試執行真 Grok 重跑 + 新增錯誤注入單元測試，保留 node ID 與原始輸出證明非假陽性

---

## 一、現有整合測試（真 Grok 連線）重跑結果

5 個 high-risk 整合測試在 Grok proxy 可用環境下全部 PASS，證明正常路徑正確：

| # | Node ID | 結果 |
|---|---------|------|
| 1 | `tests/test_llm.py::test_grok_pong_integration` | PASSED |
| 2 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | PASSED |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | PASSED |
| 4 | `tests/test_questions.py::test_generate_questions_real_grok` | PASSED |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | PASSED |

原始輸出：
```
tests/test_llm.py::test_grok_pong_integration PASSED
tests/test_domain.py::test_detect_domain_real_grok_returns_law PASSED
tests/test_gap.py::test_detect_gaps_real_grok PASSED
tests/test_questions.py::test_generate_questions_real_grok PASSED
tests/test_pipeline.py::test_run_pipeline_real_grok PASSED
5 passed in 88.50s
```

---

## 二、新增錯誤注入單元測試

共 6 個測試，全部使用 `monkeypatch` 在 urllib/GrokClient 層注入異常，驗證錯誤會明確傳遞（非靜默吞掉）：

### 2.1 GrokClient 層（`tests/test_llm.py`）

| 測試 | Node ID | 注入方式 | 預期行為 | 結果 |
|------|---------|---------|---------|:----:|
| #1 | `test_llm.py::test_grokclient_urlopen_error` | `urllib.request.urlopen` → `URLError("connection refused")` | `pytest.raises(URLError)` | PASSED |
| #2 | `test_llm.py::test_grokclient_json_decode_error` | urlopen → 回傳 `b"not-json-at-all"` | `pytest.raises(JSONDecodeError)` | PASSED |
| #3 | `test_llm.py::test_grokclient_malformed_response_error` | urlopen → 回傳 `{"unexpected": "shape"}` | `pytest.raises(KeyError, IndexError)` | PASSED |

### 2.2 應用層（錯誤傳遞不吞）

| 測試 | Node ID | 注入方式 | 預期行為 | 結果 |
|------|---------|---------|---------|:----:|
| #4 | `test_domain.py::test_detect_domain_grok_error_propagates` | `GrokClient.complete` → `RuntimeError` | `detect_domain` 傳遞例外 | PASSED |
| #5 | `test_gap.py::test_detect_gaps_grok_error_propagates` | `GrokClient.complete` → `RuntimeError` | `detect_gaps` 傳遞例外 | PASSED |
| #6 | `test_questions.py::test_generate_questions_grok_error_propagates` | `GrokClient.complete` → `RuntimeError` | `generate_questions` 傳遞例外 | PASSED |

---

## 三、驗證結論：非假陽性

### 3.1 錯誤注入時明確失敗

每個錯誤注入測試均使用 `pytest.raises` 明確斷言預期例外類型與訊息，非空集合/假結構通過。

### 3.2 正常路徑通過

同一組函式的正常路徑（FakeLLM 或真 Grok）在既有測試中已充分驗證且全綠。

### 3.3 回歸全綠

```
149 passed, 8 deselected in 30.66s
```

包含 6 個新測試在內的 149 個預設測試全部 PASS，8 個 integration 測試仍由 `-m 'not integration'` 正確排除。

---

## 四、新增測試檔案與行號

| 檔案 | 行號 | 新增內容 |
|------|------|---------|
| `tests/test_llm.py` | 4 | 加入 `import urllib.error` |
| `tests/test_llm.py` | 78-92 | 3 個 GrokClient 錯誤注入測試 |
| `tests/test_domain.py` | 50-60 | `test_detect_domain_grok_error_propagates` |
| `tests/test_gap.py` | 71-81 | `test_detect_gaps_grok_error_propagates` |
| `tests/test_questions.py` | 62-72 | `test_generate_questions_grok_error_propagates` |
| `tests/test_deselection_guard.py` | 27 | `_EXPECTED_COUNTS` 更新 (151→157, 143→149) |
| `tests/deselected_allowlist.json` | 多處 | Line number 對照更新 |
| `docs/pytest-audit/requirements-test-coverage-2026-07-19.json` | 12-14 | `expected_collection` 更新 |
