# Dependency Upgrade Verification

## 概述

此文件說明如何使用 dependency-upgrade 驗證機制來確保最新相容版本的 fastapi、starlette、httpx 不會破壞現有測試套件。

## 驗證腳本

專案提供了一個可重複執行的檢查腳本 `scripts/dep_upgrade_check.py`，該腳本會：

1. 建立隔離的臨時虛擬環境
2. 使用 `constraints-ci.txt` 安裝最新相容版本的依賴套件
3. 執行完整的測試套件（跳過需要真實 grok 服務的 integration 測試）
4. 自動清理臨時虛擬環境

## 使用方式

### 基本使用

```bash
python -X utf8 scripts/dep_upgrade_check.py
```

### 使用指定的 Python

```bash
python -X utf8 scripts/dep_upgrade_check.py
```

## Constraints 檔案

依賴版本限制定義在 `constraints-ci.txt` 中：

```
# CI constraints: 以最新相容版本安裝 fastapi / starlette / httpx，
# 確保升級後測試仍通過。
# 日期：2026-07-17
fastapi==0.139.2
starlette==1.3.1
httpx==0.28.1
httpcore==1.0.9
```

## 實際通過輸出節錄

以下是執行腳本後的成功輸出節錄（2026-07-17）：

```
使用 constraints 檔案: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\ed9fa2be\constraints-ci.txt
專案根目錄: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\ed9fa2be

建立臨時 venv: C:\Users\ADMINI~1\AppData\Local\Temp\dep_upgrade_check_m0trfwut\venv
升級 pip
安裝專案依賴（使用 constraints-ci.txt）
...
Successfully installed MarkupSafe-3.0.3 annotated-doc-0.0.4 annotated-types-0.7.0 anyio-4.14.2 babel-2.18.0 brotli-1.2.0 certifi-2026.6.17 charset_normalizer-3.4.9 click-8.4.2 colorama-0.4.6 courlan-1.4.0 dateparser-1.4.1 ddgs-9.14.4 fake-useragent-2.2.0 fastapi-0.139.2 h11-0.16.0 h2-4.3.0 hpack-4.2.0 htmldate-1.10.0 httpcore-1.0.9 httpx-0.28.1 hyperframe-6.1.0 idna-3.18 iniconfig-2.3.0 jinja2-3.1.6 justext-3.0.2 lxml-6.1.1 lxml_html_clean-0.4.5 note_filler-0.1.0 packaging-26.2 pluggy-1.6.0 primp-1.3.1 pydantic-2.13.4 pydantic-core-2.46.4 pygments-2.20.0 pytest-9.1.1 python-dateutil-2.9.0.post0 python-docx-1.2.0 python-multipart-0.0.32 pytz-2026.2 regex-2026.7.10 six-1.17.0 socksio-1.0.0 starlette-1.3.1 tld-0.13.2 trafilatura-2.1.0 typing-inspection-0.4.2 typing_extensions-4.16.0 tzdata-2026.3 tzlocal-5.4.4 urllib3-2.7.0

驗證安裝的版本
Name: fastapi
Version: 0.139.2
---
Name: starlette
Version: 1.3.1
---
Name: httpx
Version: 0.28.1

執行測試套件（跳過 integration 測試）
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\ed9fa2be
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 110 items / 8 deselected / 102 selected

tests/test_citation_formatter.py::test_build_reference_lines_two_sources PASSED [  0%]
tests/test_cli.py::test_iter_inputs_expands_dir_filters_suffix_and_dedups PASSED [  1%]
...
====================== 102 passed, 8 deselected in 3.14s ======================

✅ 所有測試通過！

清理臨時 venv: C:\Users\ADMINI~1\AppData\Local\Temp\dep_upgrade_check_m0trfwut
```

## 測試結果摘要

- **總測試數**: 110 個測試
- **執行測試**: 102 個測試（跳過 8 個 integration 測試）
- **通過測試**: 102 個（100% 通過率）
- **執行時間**: 3.14 秒

## CI 整合

此驗證機制也整合在 GitHub Actions CI 中（`.github/workflows/ci.yml`），每次 push 或 pull request 時會自動執行相同的驗證流程。

## 更新 Constraints

當需要升級依賴版本時：

1. 更新 `constraints-ci.txt` 中的版本號
2. 執行 `python -X utf8 scripts/dep_upgrade_check.py` 驗證
3. 如果測試通過，提交更新
4. CI 會自動執行相同的驗證

## 注意事項

- 腳本會自動建立和清理臨時虛擬環境，不會影響開發環境
- 測試會自動跳過需要真實 grok 服務（`:8318`）的 integration 測試
- 執行時間可能因網路速度和系統效能而異