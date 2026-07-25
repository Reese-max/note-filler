# 角度有效性驗收規則

**日期**: 2026-07-26  
**任務**: 在驗收規則中新增角度有效性判定（單一角度／缺失／同義重複明確失敗，並指出缺少或被排除的角度欄位；來源綁定檢查不退化）

## 變更摘要

同一論點若：

1. **角度欄位缺失**（`angle_type`／`functional_gap`／`user_value`／`question`）
2. **角度彼此同義或精確重複**（被 `duplicate_exclusion` 排除）
3. **去重後僅剩單一有效角度**（未達 `required_effective_angle_count`）

則綁定報告必須：

- `binding_ok=False`、`binding_status=fail`
- 在 `angle_field_issues` 列出**缺少或被排除的角度欄位**
- `write_binding_report` 落盤後以 `RuntimeError: 角度有效性驗收失敗：…` 拒絕驗收，訊息含上述欄位定位

來源綁定 checks（`at_least_one_source`、`source_traceable`、`no_duplicate_sources`、`no_omitted_traces`、`no_extra_traces` 等）在角度失敗時**仍保留原判定**，不因角度閘而假性標壞。

## 核心 API

### `src/note_filler/angle_coverage.py`

| 符號 | 用途 |
|------|------|
| `list_missing_angle_fields(cov)` | 回傳 canonical 缺欄：`angle_type`／`functional_gap`／`user_value`／`question` |
| `validate_argument_angle(cov, *, argument_id)` | 面向完整性；回傳 `(ok, messages)` |
| `build_angle_field_issues(...)` | 組出可機器／人類共讀的 issue 清單（缺欄＋被排除＋單一有效角度） |

### `src/note_filler/binding_report.py`

- 每個 argument 新增固定欄位 **`angle_field_issues: list[str]`**（空 list＝通過）
- 納入 `REQUIRED_ARGUMENT_ANGLE_KEYS`；`parse_binding_report` 重算比對，有 issues 時不得標 pass
- `write_binding_report`：`coverage_ok` 未過、facet 不完整、或有 `angle_field_issues` 皆拒絕驗收，並在錯誤訊息中列出欄位

## 失敗訊息範例

| 情況 | `angle_field_issues`／錯誤片段 |
|------|--------------------------------|
| 缺 functional_gap | `argument:0: 缺少角度欄位 functional_gap` |
| 同義排除 | `argument:1: 被排除的角度欄位 angle_key=… (reason=synonym, kept_argument_index=0)` |
| 精確重複排除 | `… (reason=duplicate, …)` |
| 去重後僅一角 | `argument:0: 僅單一有效角度 (effective_angle_count=1/2)` |

## 測試覆蓋

- `tests/test_angle_coverage.py`：`list_missing_angle_fields`、`build_angle_field_issues`、既有 facet／重複／同義單元
- `tests/test_binding_report.py`：
  - `test_missing_angle_fields_fail_with_explicit_field_names`（來源 OK、缺欄明確失敗）
  - `test_excluded_synonym_angles_list_excluded_fields_and_keep_source_checks`（同義排除＋來源 checks 不退化）
  - 既有單一／重複／來源雙閘隔離負例（錯誤訊息改對齊「角度有效性驗收失敗」）
- 成功路徑 stub（CLI／delivery／note product）補齊必要性與相異角度，避免假成功路徑繞過閘

## 驗證證據

```
413 passed, 11 deselected
```

命令：

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -m "not integration" -q --tb=line
```

收集門檻：`_EXPECTED_COUNTS = (424, 413, 11)`（`tests/test_deselection_guard.py` 與 `docs/pytest-audit/requirements-test-coverage-2026-07-19.json`）

## 相關檔案

- `src/note_filler/angle_coverage.py`
- `src/note_filler/binding_report.py`
- `tests/test_angle_coverage.py`
- `tests/test_binding_report.py`
- `tests/test_cli.py`／`tests/test_delivery_receipt.py`／`tests/test_note_product_gate.py`（成功 stub）
- `tests/test_deselection_guard.py`
- `docs/pytest-audit/requirements-test-coverage-2026-07-19.json`
