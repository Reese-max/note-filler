# argument_id 到最終輸出的資料流：關聯知識落地

## 任務背景

補上「關聯知識」在機器可讀／人類可讀輸出的缺口，使每個論點同時輸出並綁定同一 `argument_id`：

1. **功能缺口**（`functional_gap`）
2. **使用者價值**（`user_value`）
3. **關聯知識**（`related_knowledge`）

關聯知識文字必須明確說明：

- **如何支撐決策品質**：對應功能缺口、提供可追溯依據，降低僅憑印象取捨的風險
- **如何補強使用者理解**：對應使用者價值

## 資料流

| 層級 | 檔案 | 行為 |
|------|------|------|
| 產生 | `src/note_filler/correction.py` | `argument_id = f"argument:{arg_idx}"`；`build_related_knowledge(...)` 寫入 `Segment.related_knowledge` |
| 機器報告 | `src/note_filler/binding_report.py` | `REQUIRED_ARGUMENT_KEYS` 含 `related_knowledge`；`checks.has_related_knowledge` 驗決策品質／使用者理解關鍵詞；缺則 `binding_ok=False`，`write_binding_report` 拒絕 |
| JSON | `src/note_filler/export.py:to_json` | segment 輸出 `related_knowledge` |
| Markdown / DOCX | `to_markdown` / `to_docx` | 獨立列 `**關聯知識**`；摘要可見列 `argument_id；functional_gap；user_value；related_knowledge` |
| Web | `app/templates/result.html` | `related_knowledge（關聯知識）` 與同一 `data-argument-id` 同卡 |

## 關鍵詞契約（可機器驗）

- `支撐決策品質`
- `補強使用者理解`

`related_knowledge_explains_value()` 兩者皆在且非空 → `has_related_knowledge=True`。

## 驗收測試錨點

- `tests/test_export.py::test_human_readable_exports_show_argument_aligned_visible_summaries`
- `tests/test_binding_report.py::test_empty_related_knowledge_fails_even_when_sources_traceable`
- `tests/test_binding_report.py::test_assembled_arguments_include_nonempty_necessity_views`
- `tests/test_source_binding_acceptance.py::test_final_output_each_argument_triad_coheres_with_same_source_and_argument`
- `tests/test_source_binding_acceptance.py::test_final_output_triad_missing_any_field_fails_explicitly`（含 `related_knowledge` 負例）
- `tests/test_server.py::test_run_renders_two_columns`

## 結論

關聯知識已自 `assemble_correction` 產生、經 binding report 守門，並落到 JSON／Markdown／DOCX／Web；每個論點的三欄與同一 `argument_id` 綁定，且文字明示決策品質與使用者理解。
