# Dependency Upgrade Verification

## 概述

此文件說明如何驗證最新相容版本的 fastapi、starlette、httpx 不會破壞現有測試套件，且不引入任何 deprecation warning。

## Deprecation 風險消除機制

### pyproject.toml 中的 addopts

```toml
addopts = "-p no:asyncio -W error::DeprecationWarning -W error::PendingDeprecationWarning"
```

- `-W error::DeprecationWarning`：任何 `DeprecationWarning` 直接導致測試失敗
- `-W error::PendingDeprecationWarning`：任何 `PendingDeprecationWarning` 直接導致測試失敗
- `-p no:asyncio`：停用 pytest-asyncio plugin（其自身會觸發 PytestDeprecationWarning）

此機制確保：**只要 102 個測試全數通過，就代表零 deprecation warning 被觸發。**

### 為什麼「102 passed」即可證明

pytest 的 `-W error::DeprecationWarning` 會將 warning 視為 exception。
若有任何 deprecated API 被呼叫，pytest 會立即報錯並導致對應測試 FAIL。
因此「102 passed, 0 failed」本身即為「零 deprecation warning」的直接證據。

## 佐證輸出（2026-07-17 再次實測）

### 環境

```
Python:      3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
pytest:      9.1.1
pluggy:      1.6.0
anyio:       4.14.2
```

### 已安裝依賴版本

```
Package       Version
------------- ---------
fastapi       0.139.2
starlette     1.3.1
httpx         0.28.1
httpcore      1.0.9
pydantic      2.13.4
pydantic-core 2.46.4
typing-extensions 4.16.0
typing-inspection 0.4.2
anyio         4.14.2
```

### 證據 A：`-W error` 模式下 102 測試全部通過

命令：`python -X utf8 -m pytest -m "not integration" -W error::DeprecationWarning -W error::PendingDeprecationWarning`

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.2
collected 110 items / 8 deselected / 102 selected

tests\test_citation_formatter.py .                                       [  0%]
tests\test_cli.py ...                                                    [  3%]
tests\test_correction.py .............                                   [ 16%]
tests\test_domain.py ......                                              [ 22%]
tests\test_e2e_acceptance.py .                                           [ 23%]
tests\test_export.py ...                                                 [ 26%]
tests\test_export_docx.py .                                              [ 27%]
tests\test_gap.py ......                                                 [ 33%]
tests\test_grading.py .......                                           [ 40%]
tests\test_law_check.py .......                                         [ 47%]
tests\test_law_lookup.py ..                                              [ 49%]
tests\test_law_search.py .......                                         [ 55%]
tests\test_llm.py ..                                                     [ 57%]
tests\test_parse.py ...                                                  [ 60%]
tests\test_pipeline.py ..                                                [ 62%]
tests\test_questions.py ....                                             [ 66%]
tests\test_retrieve.py ..                                                [ 68%]
tests\test_server.py ....                                                [ 72%]
tests\test_twinkle.py ...                                                [ 75%]
tests\test_verify.py .............                                       [ 88%]
tests\test_web.py .........                                              [ 97%]
tests\test_write.py ...                                                  [100%]

====================== 102 passed, 8 deselected in 0.98s ======================
```

結論：error 模式下零 fail → 零 deprecation warning。

### 證據 B：`-W all` 模式下無任何警告

命令：`python -X utf8 -m pytest -m "not integration" -W all -v`

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.14.2
collecting ... collected 110 items / 8 deselected / 102 selected

tests/test_citation_formatter.py::test_build_reference_lines_two_sources PASSED [  0%]
...（所有 102 項 PASSED）...
tests/test_write.py::test_out_of_range_marker_removed_and_not_used PASSED [100%]

====================== 102 passed, 8 deselected in 1.01s ======================
```

結論：`-W all` 顯示所有等級警告，輸出中 **零個 warnings summary** —— 實質上零警告。

## Constraints 檔案

```txt
# CI constraints: 以最新相容版本安裝 fastapi / starlette / httpx，
# 確保升級後測試仍通過。
# 日期：2026-07-17
fastapi==0.139.2
starlette==1.3.1
httpx==0.28.1
httpcore==1.0.9
```

## 驗證腳本

`scripts/dep_upgrade_check.py` 會在隔離臨時 venv 中：

1. 依 constraints-pinned.txt 安裝最新相容版本
2. 驗證安裝版本
3. 執行完整測試套件（跳過 integration）
4. 自動清理

```bash
python -X utf8 scripts/dep_upgrade_check.py
```

## CI 整合

GitHub Actions CI（`.github/workflows/ci.yml`）每次 push/PR 執行兩組驗證：

| Job | Python | Constraints | 用途 |
|---|---|---|---|
| `test-pinned` | 3.11, 3.12 | `constraints-pinned.txt` | 確保特定升級版本可通過 |
| `test-latest` | 3.11, 3.12, 3.13 | 無（pip 解析最新相容版） | 確保非鎖定環境仍可通過 |

`test-latest` 是防護「只在舊版鎖定依賴下通過」的核心：pyproject.toml 的 `>=` 範圍允許的最新版都必須通過。

## 更新 Constraints

1. 更新 `constraints-pinned.txt` 中的版本號
2. 執行 `python -X utf8 scripts/dep_upgrade_check.py` 驗證
3. 確認 102 passed + 零 warnings → 提交更新
