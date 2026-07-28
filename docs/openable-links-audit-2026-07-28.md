# 論點區塊「至少 2 條真實可開啟連結」附加輸出規則（2026-07-28）

## 範圍

實作論點區塊的「至少 2 條真實可開啟連結」附加輸出規則：優先採用該論點實際引用來源的 URL，再補延伸閱讀的 URL；若合格來源不足，輸出【待補來源】並明確標示原因。

## 規則定義

- **MIN_OPENABLE_LINKS** = 2
- **可開啟連結**：`urlparse(url).scheme in ("http", "https")` 且 `netloc` 非空
- **優先序**：引用來源 URL → 延伸閱讀 URL
- **pure pending**（無任何候選來源）：不強制要求，狀態為 `sufficient`
- **禁止**：拼湊 URL、把待補來源與真實連結混排成可通過格式檢查的假結果

## 修改檔案

| 檔案 | 改動 |
|---|---|
| `src/note_filler/correction.py` | 新增 `is_openable_url()`、`MIN_OPENABLE_LINKS`；`Segment` 新增三欄；`assemble_correction()` 計算可開啟連結 |
| `src/note_filler/binding_report.py` | `REQUIRED_CHECK_KEYS` 新增 `at_least_two_openable_links`；`REQUIRED_ARGUMENT_KEYS` 新增三欄；`_evaluate_argument()` 計算檢查；`parse_binding_report()` 驗證一致性 |
| `src/note_filler/export.py` | `to_json()` 輸出三欄；`to_markdown()`/`to_docx()` 在 insufficient 時輸出【待補來源】標記 |
| `tests/test_openable_links.py` | 新增 41 個測試（14 URL 單元 + 6 assemble + 5 binding_report + 6 負例 + 5 export + 3 禁止拼湊 + 1 原稿不變 + 1 Segment） |
| `tests/test_binding_report.py` | 更新 `_source()` 預設 URL；更新 `all(checks.values())` 斷言排除附加規則 |
| `tests/test_source_binding_acceptance.py` | 更新 `all(checks.values())` 斷言排除附加規則 |
| `docs/polaris_field_specification.json` | 新增 `openable_links_count`、`openable_links_status`、`openable_links_incomplete_reason` 欄位定義 |

## 資料流

```
assemble_correction()
  → 計算 cited_urls（引用來源中有效 URL）
  → 計算 extended_urls（延伸閱讀中有效 URL）
  → 計算 openable_links_count = len(cited_urls + extended_urls)
  → 判定 openable_links_status（sufficient / insufficient）
  → 填入 Segment.openable_links_*

build_binding_report()
  → _evaluate_argument() 讀取 Segment 欄位
  → 輸出 checks.at_least_two_openable_links
  → 注意：此檢查為附加輸出規則，不影響 binding_ok/binding_status

export.to_json() / to_markdown() / to_docx()
  → JSON：輸出三欄
  → Markdown/DOCX：insufficient 時輸出「【待補來源】可開啟連結不足——{reason}」

parse_binding_report()
  → 驗證欄位型別、一致性、sufficient/insufficient 與 reason 對應
```

## 品質閘不變式

- **原稿逐字不變**：可開啟連結欄位只作為附加資訊，不修改原文
- **無虛構 URL**：`is_openable_url()` 嚴格驗證 http/https 協議
- **來源綁定不變**：`at_least_two_openable_links` 為附加檢查，不影響既有 `binding_ok` 邏輯
- **禁止混排**： insufficient 時明確標示原因，不偽裝為 sufficient

## 測試結果

```
762 passed, 1 skipped, 12 deselected
```

新增 41 個可開啟連結專屬測試全部通過：
- 14 個 `is_openable_url` 單元測試
- 1 個 Segment 欄位測試
- 6 個 assemble_correction 計算測試
- 5 個 binding_report 欄位/一致性測試
- 6 個負例（缺欄/非法值/不一致/sufficient+reason/insufficient-no-reason）
- 5 個 export 輸出測試（JSON/Markdown/DOCX）
- 3 個禁止拼湊 URL 測試
- 1 個原稿不可變性測試
