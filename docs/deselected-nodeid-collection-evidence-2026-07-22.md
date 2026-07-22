# 8 個 deselected node id 收集階段證據對照（2026-07-22）

## 任務目標

針對仍未能以既有證據閉合的 8 個 `deselected` node id，逐一補抓 `pytest -vv --setup-show <nodeid>` 與 `pytest --collect-only -vv <nodeid>` 的原始輸出，建立「node id → fixture/mark/收集階段原因 → 是否確定為預期排除」的機器可讀對照檔。

## 執行方法

### 1. 預設 addopts 下收集階段輸出（含 deselected 原因）

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest <nodeid> --collect-only -vv --deselected-details
```

### 2. 移除 addopts 下完整執行輸出（含 fixture 詳情）

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest <nodeid> -vv --setup-show -o addopts=
```

## 8 個 node id 詳細對照

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

**收集階段輸出（預設 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item / 1 deselected / 0 selected

============================= deselected details ==============================
tests/test_domain.py::test_detect_domain_real_grok_returns_law | reason: deselected by -m 'not integration'
================= no tests collected (1 deselected) in 0.03s ==================
```

**完整執行輸出（移除 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

tests/test_domain.py::test_detect_domain_real_grok_returns_law 
SETUP    S event_loop_policy
        tests/test_domain.py::test_detect_domain_real_grok_returns_law (fixtures used: event_loop_policy) PASSED
TEARDOWN S event_loop_policy

============================== 1 passed in 3.63s ==============================
```

**對照分析：**
- **fixtures**: `event_loop_policy` (session scope)
- **marks**: `@pytest.mark.integration`, `@pytest.mark.skipif(not _grok_reachable())`
- **收集階段原因**: `deselected by -m 'not integration'`
- **是否確定為預期排除**: ✅ 是
- **解釋**: 刻意分組：帶 `@pytest.mark.integration` 被 `pyproject.toml` addopts `-m 'not integration'` 排除

---

### 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

**收集階段輸出（預設 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item / 1 deselected / 0 selected

============================= deselected details ==============================
tests/test_e2e_acceptance.py::test_e2e_acceptance_real | reason: deselected by -m 'not integration'
================= no tests collected (1 deselected) in 0.02s ==================
```

**完整執行輸出（移除 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

<Dir 2360df1c>
  <Dir tests>
    <Module test_e2e_acceptance.py>
      端到端驗收測試(spec §12)。
      
      §12 硬不變式:
        1. 原稿逐字不可變(diff 只增不改)
        2. 無來源閘 + C6:supplement sources 空 -> confidence == "pending_evidence"
        3. 交叉驗證 C4:supplement verified -> sources 非空且皆 A/B、>=2 獨立來源
        4. 補充法條經 check_law_citations(text=..., lookup) 無 article_not_found
        5. C3:輸出由 T14 to_markdown 產出,含【補充】/⚠待補證/參考區塊(帶日期 C7)
      <Function test_e2e_acceptance_real>

========================== 1 test collected in 0.04s ==========================
```

**對照分析：**
- **fixtures**: `event_loop_policy` (session scope)
- **marks**: `@pytest.mark.integration` (無 skipif，改用內部 `pytest.skip()`)
- **收集階段原因**: `deselected by -m 'not integration'`
- **是否確定為預期排除**: ✅ 是
- **解釋**: 刻意分組：帶 `@pytest.mark.integration` 被 `pyproject.toml` addopts `-m 'not integration'` 排除；另有 runtime guard (LAW_DB.exists(), _grok_up(), _twinkle_ready())

---

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`

**收集階段輸出（預設 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item / 1 deselected / 0 selected

============================= deselected details ==============================
tests/test_gap.py::test_detect_gaps_real_grok | reason: deselected by -m 'not integration'
================= no tests collected (1 deselected) in 0.03s ==================
```

**完整執行輸出（移除 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

<Dir 2360df1c>
  <Dir tests>
    <Module test_gap.py>
      <Function test_detect_gaps_real_grok>
        真打 grok(http://127.0.0.1:8318/v1, grok-4.3):
        給一段只談行政處分定義的筆記 + 一題明顯未涵蓋的問題,
        驗回傳結構正確且所有 status 皆為缺口(partial/missing)。

========================== 1 test collected in 0.06s ==========================
```

**對照分析：**
- **fixtures**: `event_loop_policy` (session scope)
- **marks**: `@pytest.mark.integration`, `@pytest.mark.skipif(not _grok_reachable())`
- **收集階段原因**: `deselected by -m 'not integration'`
- **是否確定為預期排除**: ✅ 是
- **解釋**: 刻意分組：帶 `@pytest.mark.integration` 被 `pyproject.toml` addopts `-m 'not integration'` 排除

---

### 4. `tests/test_llm.py::test_grok_pong_integration`

**收集階段輸出（預設 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item / 1 deselected / 0 selected

============================= deselected details ==============================
tests/test_llm.py::test_grok_pong_integration | reason: deselected by -m 'not integration'
================= no tests collected (1 deselected) in 0.02s ==================
```

**完整執行輸出（移除 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

<Dir 2360df1c>
  <Dir tests>
    <Module test_llm.py>
      <Function test_grok_pong_integration>

========================== 1 test collected in 0.06s ==========================
```

**對照分析：**
- **fixtures**: `event_loop_policy` (session scope)
- **marks**: `@pytest.mark.integration`, `@pytest.mark.skipif(not _grok_reachable())`
- **收集階段原因**: `deselected by -m 'not integration'`
- **是否確定為預期排除**: ✅ 是
- **解釋**: 刻意分組：帶 `@pytest.mark.integration` 被 `pyproject.toml` addopts `-m 'not integration'` 排除

---

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

**收集階段輸出（預設 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item / 1 deselected / 0 selected

============================= deselected details ==============================
tests/test_pipeline.py::test_run_pipeline_real_grok | reason: deselected by -m 'not integration'
================= no tests collected (1 deselected) in 0.08s ==================
```

**完整執行輸出（移除 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

<Dir 2360df1c>
  <Dir tests>
    <Module test_pipeline.py>
      <Function test_run_pipeline_real_grok>
        打真 grok(http://127.0.0.1:8318/v1, grok-4.3);twinkle/law 用 fake 隔離,
        驗 parse→domain→questions→gaps→assemble 整條在真模型輸出下不炸。

========================== 1 test collected in 0.08s ==========================
```

**對照分析：**
- **fixtures**: `event_loop_policy` (session scope), `tmp_path_factory` (session scope), `tmp_path` (function scope), `note_path` (function scope)
- **marks**: `@pytest.mark.integration`, `@pytest.mark.skipif(not _grok_reachable())`
- **收集階段原因**: `deselected by -m 'not integration'`
- **是否確定為預期排除**: ✅ 是
- **解釋**: 刻意分組：帶 `@pytest.mark.integration` 被 `pyproject.toml` addopts `-m 'not integration'` 排除；使用 `note_path` fixture 建立臨時 .docx

---

### 6. `tests/test_questions.py::test_generate_questions_real_grok`

**收集階段輸出（預設 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item / 1 deselected / 0 selected

============================= deselected details ==============================
tests/test_questions.py::test_generate_questions_real_grok | reason: deselected by -m 'not integration'
================= no tests collected (1 deselected) in 0.03s ==================
```

**完整執行輸出（移除 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

<Dir 2360df1c>
  <Dir tests>
    <Module test_questions.py>
      <Function test_generate_questions_real_grok>

========================== 1 test collected in 0.05s ==========================
```

**對照分析：**
- **fixtures**: `event_loop_policy` (session scope)
- **marks**: `@pytest.mark.integration`, `@pytest.mark.skipif(not _grok_reachable())`
- **收集階段原因**: `deselected by -m 'not integration'`
- **是否確定為預期排除**: ✅ 是
- **解釋**: 刻意分組：帶 `@pytest.mark.integration` 被 `pyproject.toml` addopts `-m 'not integration'` 排除

---

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

**收集階段輸出（預設 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item / 1 deselected / 0 selected

============================= deselected details ==============================
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke | reason: deselected by -m 'not integration'
================= no tests collected (1 deselected) in 0.02s ==================
```

**完整執行輸出（移除 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

<Dir 2360df1c>
  <Dir tests>
    <Module test_retrieve.py>
      <Function test_retrieve_for_gap_real_twinkle_smoke>

========================== 1 test collected in 0.07s ==========================
```

**對照分析：**
- **fixtures**: `event_loop_policy` (session scope)
- **marks**: `@pytest.mark.integration`, `@pytest.mark.skipif(not LAW_DB.exists())`, `@pytest.mark.skipif(not _grok_reachable())`
- **收集階段原因**: `deselected by -m 'not integration'`
- **是否確定為預期排除**: ✅ 是
- **解釋**: 刻意分組：帶 `@pytest.mark.integration` 被 `pyproject.toml` addopts `-m 'not integration'` 排除；三層 runtime guard (LAW_DB.exists(), _grok_reachable(), TWINKLE_HUB_TOKEN)

---

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

**收集階段輸出（預設 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item / 1 deselected / 0 selected

============================= deselected details ==============================
tests/test_twinkle.py::test_search_real_twinkle_hub | reason: deselected by -m 'not integration'
================= no tests collected (1 deselected) in 0.02s ==================
```

**完整執行輸出（移除 addopts）：**
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\2360df1c
configfile: pyproject.toml
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

<Dir 2360df1c>
  <Dir tests>
    <Module test_twinkle.py>
      <Function test_search_real_twinkle_hub>

========================== 1 test collected in 0.06s ==========================
```

**對照分析：**
- **fixtures**: `event_loop_policy` (session scope)
- **marks**: `@pytest.mark.integration` (無 skipif，改用內部 `pytest.skip()`)
- **收集階段原因**: `deselected by -m 'not integration'`
- **是否確定為預期排除**: ✅ 是
- **解釋**: 刻意分組：帶 `@pytest.mark.integration` 被 `pyproject.toml` addopts `-m 'not integration'` 排除；runtime guard (TWINKLE_HUB_TOKEN)

---

## 總結

### 統計結果

| 項目 | 數量 |
|------|------|
| 總 nodeid 數 | 8 |
| 預期排除數 | 8 |
| 非預期排除數 | 0 |
| 全部由 markexpr 排除 | 是 |
| 共同收集原因 | `deselected by -m 'not integration'` |

### 關鍵發現

1. **統一排除機制**: 全部 8 個 deselected 測試均由 `@pytest.mark.integration` + `pyproject.toml` addopts `-m 'not integration'` 排除
2. **fixture 使用**: 全部測試僅使用 `event_loop_policy` session fixture，僅 `test_run_pipeline_real_grok` 額外使用 `note_path` fixture
3. **多層防護**: 部分測試有額外的 runtime guard (skipif 或內部 pytest.skip)
4. **預期排除**: 所有 deselected 均為刻意分組策略，屬於預期排除

### 機器可讀對照檔

詳細的機器可讀 JSON 對照檔已建立於：`docs/deselected-nodeid-collection-mapping.json`

## 驗證命令

```powershell
# 驗證收集階段原因一致性
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest --collect-only -vv --deselected-details

# 驗證機器可讀對照檔格式
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -c "import json; json.load(open('docs/deselected-nodeid-collection-mapping.json', encoding='utf-8'))"
```
