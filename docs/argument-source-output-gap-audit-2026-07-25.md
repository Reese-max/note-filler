# Argument→Source 最終成品輸出路徑缺口盤點 (2026-07-25)

## 範圍

盤點 `argument → source` 最終成品的三層輸出路徑，確認是否各層在**同層級**都
具備 `argument_text`、`source_id`、`source_span/position` 三個欄位。

## 逐層盤點

### 1. 序列化層 — `export.py:to_json()` (line 34–70)

每個 segment dict 欄位：
```
type, text, anchor_idx, confidence, conflict_note,
source_id, traceability, sources
```

| 需求欄位 | 狀態 | 說明 |
|---|---|---|
| `argument_text` | △ | 內容存在但欄位名為 `text`，非 `argument_text` |
| `source_id` | ✅ | `source_id` 欄位存在 |
| `source_span/position` | ❌ | 完全不存在 |

### 2. 檔案層 — `binding_report.py:_evaluate_argument()` (line 134–214)

每個 argument dict 欄位（`REQUIRED_ARGUMENT_KEYS` line 36–51）：
```
argument_index, segment_index, argument_text, confidence,
cardinality, source_count, source_ids, trace_source_ids,
source_id_field, checks, binding_status, binding_ok
```

| 需求欄位 | 狀態 | 說明 |
|---|---|---|
| `argument_text` | ✅ | 欄位名 `argument_text` 存在 |
| `source_id` | ✅ | 以 `source_ids` + `trace_source_ids` + `source_id_field` 三欄位存在 |
| `source_span/position` | ❌ | 完全不存在 |

### 3. 回傳層 — `server.py:run()` (line 45–60) + `result.html` (line 44–75)

每個 segment 可存取欄位（由 `correction.py:24` `Segment` dataclass 提供）：
```
type, text, anchor_idx, sources, confidence,
conflict_note, traceability, source_id
```

| 需求欄位 | 狀態 | 說明 |
|---|---|---|
| `argument_text` | △ | 內容存在但以 `seg.text` 存取，非 `argument_text` 欄位名 |
| `source_id` | ✅ | `seg.source_id` 存在 |
| `source_span/position` | ❌ | 完全不存在 |

## 結論

**三層都缺的欄位：`source_span/position`。**  
`argument_text` 與 `source_id` 的內容在三層都有，唯獨來源內的精確位置
（span／段落／頁碼等）完全沒有在任何層級的同一層出現。

## 最後一個缺口

**檔案：** `binding_report.py`  
**函式：** `_evaluate_argument()` (line 134)  

理由：binding_report 是三層中最結構化的機器可讀產出，擁有最嚴格的欄位契約
（`REQUIRED_ARGUMENT_KEYS`），是「argument → source」最終成品的核心。
若此處補上 `source_span/position`，其他兩層即可比照跟進；反之，若資料模型
（`correction.py` `Segment`）未定義此欄位，三層皆無法輸出。

因此最關鍵的單一缺口位置為 `binding_report.py:134` `_evaluate_argument()` ——
該函式在建立每個 argument dict 時未納入 `source_span/position`。
