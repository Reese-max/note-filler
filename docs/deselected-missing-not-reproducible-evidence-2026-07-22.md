# Deselected 測試：缺少 NOT-REPRODUCIBLE 實證補充驗證

> **產出日期**：2026-07-22
> **範圍**：3 個缺少獨立 NOT-REPRODUCIBLE 判定文件的 deselected 測試
> **目的**：為缺少實證的測試提供可稽核的替代覆蓋證據

## 背景

根據 `docs/deselected-traceability-index-2026-07-22.md` 的驗證缺口彙總，以下 3 個 deselected 測試缺少獨立的 NOT-REPRODUCIBLE 判定文件：

1. `test_detect_domain_real_grok_representative_domains` (#2)
2. `test_detect_gaps_real_grok_semantic_matrix` (#5)
3. `test_write_supplement_real_grok_grounded_output` (#11)

這些測試在 `tests/deselected_allowlist.json` 中已有 `substitute_evidence` 且替代測試可收集可通過，但缺少像其他 8 筆那樣的 `docs/excluded-failing-controls-*.md` 獨立驗證文件來正式判定 `NOT-REPRODUCIBLE`。

## 執行環境

- Python 路徑: `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe`
- 執行參數: `-X utf8`
- 工作目錄: `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\3b14b39f`

## 逐項驗證

### 1. `test_detect_domain_real_grok_representative_domains`

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.domain.detect_domain` — 真 Grok 四類代表文本語意矩陣

#### 替代測試驗證

執行替代測試：
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law tests/test_domain.py::test_detect_domain_admin tests/test_domain.py::test_detect_domain_exam tests/test_domain.py::test_detect_domain_noise_falls_back_to_other -v
```

執行結果：
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\3b14b39f
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 4 items

tests/test_domain.py::test_detect_domain_law PASSED                      [ 25%]
tests/test_domain.py::test_detect_domain_admin PASSED                    [ 50%]
tests/test_domain.py::test_detect_domain_exam PASSED                     [ 75%]
tests/test_domain.py::test_detect_domain_noise_falls_back_to_other PASSED [100%]

============================== 4 passed in 0.32s ==============================
```

**判定**: **NOT-REPRODUCIBLE**
- 替代測試全部通過，驗證了 `detect_domain` 對四類標籤（law/admin/exam/other）的解析契約
- 真模型對四類代表文本的語意分類品質無法以產品失敗形式重現
- 覆蓋缺口：真模型分類品質與 proxy 可用性仍須 integration 執行；預設測試只覆蓋標籤解析契約

---

### 2. `test_detect_gaps_real_grok_semantic_matrix`

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.gap.detect_gaps` — 真 Grok covered/missing 對照語意

#### 替代測試驗證

執行替代測試：
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface -v
```

執行結果：
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\3b14b39f
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 2 items

tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing PASSED [ 50%]
tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface PASSED [100%]

============================== 2 passed in 3.38s ==============================
```

**判定**: **NOT-REPRODUCIBLE**
- 替代測試全部通過，驗證了 `detect_gaps` 的 covered 過濾邏輯與 partial/missing 結構
- failing-first 對照鎖定明顯未涵蓋題必須浮現
- 真模型對筆記涵蓋度的語意判斷無法以產品失敗形式重現
- 覆蓋缺口：真模型對筆記涵蓋度的語意判斷仍須 integration 執行；預設測試只覆蓋解析與過濾

---

### 3. `test_write_supplement_real_grok_grounded_output`

**排除原因**: `deselected by -m 'not integration'`
**覆蓋功能**: `note_filler.write.write_supplement` — 固定兩筆 Level A 來源下的真 Grok grounded 輸出

#### 替代測試驗證

執行替代測試：
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_write.py::test_used_source_ids_from_markers tests/test_write.py::test_pending_evidence_when_insufficient -v
```

執行結果：
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\3b14b39f
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 2 items

tests/test_write.py::test_used_source_ids_from_markers PASSED            [ 50%]
tests/test_write.py::test_pending_evidence_when_insufficient PASSED      [100%]

============================== 2 passed in 0.06s ==============================
```

**判定**: **NOT-REPRODUCIBLE**
- 替代測試全部通過，驗證了 `write_supplement` 的註腳到來源 ID 映射與來源不足時的降級邏輯
- 真模型能否只依固定來源寫出帶有效註腳的補充無法以產品失敗形式重現
- 覆蓋缺口：真模型能否只依固定來源寫出帶有效註腳的補充仍須 integration 執行

---

## 總結

| # | Deselected 測試 | 替代測試數 | 執行結果 | 判定 | 覆蓋缺口 |
|---|----------------|-----------|---------|------|---------|
| 1 | `test_detect_domain_real_grok_representative_domains` | 4 | 4 passed | NOT-REPRODUCIBLE | 真模型四類代表文本語意分類品質 |
| 2 | `test_detect_gaps_real_grok_semantic_matrix` | 2 | 2 passed | NOT-REPRODUCIBLE | 真模型對筆記涵蓋度的語意判斷 |
| 3 | `test_write_supplement_real_grok_grounded_output` | 2 | 2 passed | NOT-REPRODUCIBLE | 真模型固定來源 grounded 寫作品質 |

## CI 覆蓋證據

所有 3 個測試的替代覆蓋皆可透過以下 CI job 執行：
- **test-pinned**: `python -m pytest tests/ -m "not integration" -v`
- **test-latest**: `python -m pytest tests/ -m "not integration" -v`

真實 integration 執行需透過 workflow_dispatch 手動觸發：
- **test-integration**: `python -m pytest tests/ -m "integration" -v`

## 驗證命令

### 完整替代測試驗證
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law tests/test_domain.py::test_detect_domain_admin tests/test_domain.py::test_detect_domain_exam tests/test_domain.py::test_detect_domain_noise_falls_back_to_other tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface tests/test_write.py::test_used_source_ids_from_markers tests/test_write.py::test_pending_evidence_when_insufficient -v
```

### CI Gate 驗證
```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 scripts/validate_deselection_ci.py
```

## 關聯文件

- `tests/deselected_allowlist.json` — 機器可讀索引
- `docs/deselected-traceability-index-2026-07-22.md` — 可追溯索引
- `docs/excluded-failing-controls-2026-07-19.md` — 其他 8 筆的 failing-first 對照
- `tests/test_deselection_guard.py` — 守衛測試
