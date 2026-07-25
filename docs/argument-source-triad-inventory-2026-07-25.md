# `argument -> source` 最終成品最後缺口盤點

- 日期：2026-07-25
- 範圍：目前 repo 的成功交付產物 `binding_report.json`
- 性質：唯讀盤點；未修改功能程式碼

## 落盤結果

以目前程式碼組出一筆有實際來源的 supplement，再讀取最終報告的
`arguments[0]`；實跑結果如下：

| 必備欄位 | 最終產物欄位 | 結果 |
|---|---|---|
| `argument text` | `argument_text` | 已落盤 |
| `source_id` | `source_ids`、`source_id_field` | 已落盤 |
| `source span/position` | 無 | **未落盤** |

實際 argument keys：

```text
argument_index, argument_text, binding_ok, binding_status, cardinality,
checks, confidence, segment_index, source_count, source_id_field,
source_ids, trace_source_ids
```

`argument_index` 與 `segment_index` 是成品內的位置，不是來源內容中的
span/position；`Source.content` 是整份來源全文，也不能代替支持該論點的片段或
可重定位位置。

來源標記第一次綁到論點時，目前只保留論點文字與來源 ID，沒有產生來源片段或
來源內位置；因此下游最終產物沒有可落盤的 span/position。這是三個必備欄位中
唯一仍缺的一個。

## 最後一個缺口

- 檔案：`src/note_filler/write.py`
- 函式：`write_supplement`
