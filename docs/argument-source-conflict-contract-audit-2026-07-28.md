# 論點區塊來源衝突盤點與欄位契約（2026-07-28）

## 範圍與結論

本次只盤點既有程式與輸出，不改動功能。結論如下：

- **已被論點實際引用的來源衝突採並列保留**：`cross_validate()` 偵測到衝突後保留全部來源、不選邊；實測 `s:a`、`s:b` 皆留在 `Validation.sources` 與最終 `Segment.sources`。
- **未被 inline 引用的檢索來源會直接排除於驗證與成品之外**：`pipeline.run_pipeline()` 只把 `used_source_ids` 對應的來源傳給 `cross_validate()`；其餘來源只留下稽核事件，不會參與衝突判定或輸出。
- **相同 `Source.id` 是另一個覆蓋風險，不是衝突解決策略**：`assemble_correction()` 以 `{s.id: s}` 找回來源，同 ID 時後出現者會覆蓋先出現者。檢索層只在法條檢索內去重，跨來源供應者沒有統一的 ID 衝突防護。
- 目前衝突資料只有 `conflict: bool` 與自由文字 `conflict_note`；JSON、Markdown、DOCX 會帶出該文字，但沒有可逐筆解析的衝突來源、偏好理由、適用條件或可讀結論。Web 結果模板也沒有顯示 `conflict_note`。

因此，對「來源衝突」的主答案是：**實際引用來源採並列保留；未引用來源則在進入衝突判定前被直接排除；不會自動以單一來源覆蓋或選邊。**

## 現有資料模型與輸出鏈

| 階段 | 模型／格式 | 已有來源欄位 | 衝突資訊 | 行為 |
| --- | --- | --- | --- | --- |
| 檢索 | `Source` | `id`、`title`、`url`、`level`、`content`、日期、`distance` | 無 | 依 Level／distance 排序；候選仍是完整清單。 |
| 引用選取 | `WrittenSupplement` | `used_source_ids`、`citation_spans` | 無 | 從有效 `[^n]` 取用來源 ID，依首次出現順序去重。 |
| 交叉驗證 | `Validation` | `sources` | `conflict`、`conflict_note` | 關鍵詞啟發式只標記，保留全部傳入來源，`verified` 與衝突判定彼此獨立。 |
| 論點區塊 | `Segment(type="supplement")` | `sources`、`source_ids`、`source_id`、`traceability`、`citation_spans` | `conflict_note` | `sources` 只含實際引用來源；衝突降為單一文字。 |
| 機器可讀綁定報告 | `binding_report.json.arguments[]` | `source_ids`、`source_fragments`、`citation_spans`、`claim_source_map` | 無 | 嚴格 schema；目前無衝突欄位。 |
| JSON 訂正稿 | `to_json().segments[]` | `sources`、`source_ids`、`source_id`、`citation_spans` | `conflict_note` 字串 | 可看見告警文字，不能程式化知道哪幾個來源衝突。 |
| Markdown／DOCX | `to_markdown()`／`to_docx()` | 來源清單、註腳、追溯行 | 衝突告警文字 | 呈現文字告警，未呈現結構化條件或偏好。 |
| Web 結果頁 | `result.html` | 來源清單與引用範圍 | 無 | 直接讀取 `Segment`，但未渲染 `conflict_note`。 |

### 已驗證的實際路徑

1. `retrieve_for_gap()` 以 `extend()` 蒐集候選並排序。
2. `write_supplement()` 只從有效 inline 引用建立 `used_source_ids`。
3. `run_pipeline()` 以 `used = [s for s in sources if s.id in w.used_source_ids]` 執行交叉驗證；`omitted_ids` 僅記錄稽核事件。
4. `cross_validate()` 偵測「得／不得」等相反敘述時，回傳保留原清單的 `Validation` 與「不選邊」告警。
5. `assemble_correction()` 將告警文字放入 `Segment.conflict_note`；`to_json()`、`to_markdown()`、`to_docx()`各自轉送或渲染該文字。

以兩個實際引用來源的可執行探針驗證：`Validation.sources` 與最終 `Segment.sources` 都是 `['s:a', 's:b']`，`to_json()` 沒有 `source_conflicts`，但 Markdown 含既有 `conflict_note`。既有回歸測試也鎖定「衝突不選邊、不刪來源」與三種匯出會轉送告警文字。

## 新增機器可讀欄位契約

以下四欄應置於每個 supplement 論點的同一層級；原文段不新增論點判定。欄位只描述已實際引用的來源，不得把未引用的檢索候選補進成品。

```json
{
  "source_conflicts": [
    {
      "kind": "semantic_contradiction",
      "status": "unresolved",
      "source_ids": ["s:a", "s:b"],
      "detector": "keyword_heuristic",
      "rule": "得/不得",
      "message": "來源對得／不得表述不一致"
    }
  ],
  "source_preference_reason": {
    "status": "not_selected",
    "preferred_source_id": null,
    "reason_code": "unresolved_conflict",
    "detail": "目前偵測到矛盾，尚未取得可判定優先來源的依據。"
  },
  "applicable_conditions": {
    "status": "not_assessed",
    "items": []
  },
  "readable_conclusion": "兩個已引用來源對得／不得表述不一致；尚未選定優先來源，需人工判讀適用條件。"
}
```

| 欄位 | 型別與固定值 | 空值規則與約束 |
| --- | --- | --- |
| `source_conflicts` | `list[object]`；每筆含 `kind`、`status`、`source_ids`、`detector`、`rule`、`message`。`kind` 目前固定 `semantic_contradiction`；`status` 為 `unresolved`、`resolved_by_conditions` 或 `preferred`。 | 無衝突必為 `[]`，不得省略。每筆 `source_ids` 至少兩個、去重、保持 `source_ids` 原順序，且必為本論點實際引用來源的子集。 |
| `source_preference_reason` | 固定 object：`status`（`not_applicable`／`not_selected`／`selected`）、`preferred_source_id`（`string` 或 `null`）、`reason_code`、`detail`。 | 目前衝突一律 `not_selected`，`preferred_source_id=null`；不得因 Level 排序而自動選邊。只有 `status=selected` 時才可填入本論點 `source_ids` 內的 ID 與非空理由。 |
| `applicable_conditions` | 固定 object：`status`（`not_assessed`／`assessed`）及 `items`。每個 item 為 `kind`（時間／地域／主體／程序／例外）、`value`、`source_ids`。 | 現行啟發式沒有擷取條件，衝突時必為 `{"status":"not_assessed","items":[]}`，不可假造條件。已解析條件時，每個 item 的來源 ID 仍須是實際引用來源子集。 |
| `readable_conclusion` | 非空 `string`，供 Markdown、DOCX、Web 與人工閱讀。 | 僅能由前三欄與既有論點文字／實際來源標題生成；須說出是否有衝突、是否已選邊及條件判定狀態，不得加入來源外事實。 |

### 品質閘不變式

- 原稿 `Segment.text` 維持逐字不變；上述欄位只加在 supplement 論點的中繼資料與輸出投影。
- 無來源或以 `【待補證】` 開頭的補充仍必為 `pending_evidence`；此時 `source_conflicts=[]`、偏好狀態為 `not_applicable`、條件狀態為 `not_assessed`，且結論須明示待補證。
- 衝突欄位不得把未引用候選來源、推測來源或空白 ID 寫入；`source_conflicts[].source_ids` 必須能逐一回指既有引用範圍與來源片段。
- 法條引用仍須經既有離線查核；衝突欄位不得用「已偏好」或文字結論繞過查核，也不得因衝突自動把未查核法條升為 `verified`。
- 衝突的存在不等同自動選邊。若未能判定適用條件，必須保留 `unresolved`，而不是用來源等級、距離或輸入順序推斷結論。

## 唯一列出的末端修改目標

依本次限制，僅列出最末端的機器可讀序列化目標：

- `src/note_filler/binding_report.py`：`_evaluate_argument()`

理由：此函式建立 `binding_report.json.arguments[]` 的逐論點 dict，而該報告已有嚴格欄位契約與解析驗收；四個欄位應在此成為可驗證的最終投影，而非只停留在 `conflict_note` 的自由文字中。

## 本次驗證

```text
可執行探針：衝突來源 s:a／s:b 均保留；JSON 缺少 source_conflicts；Markdown 含 conflict_note
既有對應測試：test_verify.py::test_conflict_detected_and_no_side_taken
既有對應測試：test_exception_skip_traceability.py::test_validation_conflict_reaches_all_exports
```
