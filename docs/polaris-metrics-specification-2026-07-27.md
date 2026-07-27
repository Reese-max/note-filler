# 北極星筆記品質指標規格

日期：2026-07-27
基準 revision：`90229c30`
Schema 版本：`note_filler.polaris_metrics.v1`

公式版本：`1.2`

## 概述

本規格定義可機器讀取的北極星筆記品質指標，包含「功能缺口分數」與「使用者價值分數」等核心指標的明確公式、判定規則、資料來源與缺值處理方式。每則筆記可被一致計分與追蹤，並產出可序列化的指標物件與報告欄位。

本規格以「功能缺口分數」與「使用者價值分數」為兩項北極星品質指標；其餘三項為來源、角度與送達品質的配套指標，不得替代這兩項指標。兩項北極星指標只在資料完整且 `status = calculated` 時允許通過門檻，不可量測或部分可量測資料一律不得判為高品質。

## 核心指標

### 1. 功能缺口分數（Functional Gap Score）

#### 名稱

功能缺口分數（Functional Gap Score），序列化欄位為 `functional_gap_score`。

#### 目的

衡量單一筆記中的補充論點是否針對具體功能缺口，並同時具備可追溯來源、有效角度與一致的決策助益；避免只因 `functional_gap` 有文字就將筆記判為高品質。

#### 公式或判定規則

```
功能缺口分數 = 可追溯性 × 0.25 + 覆蓋廣度 × 0.25
               + 必要性明確度 × 0.25 + 決策助益 × 0.25
```

四個子分數均為符合條件的論點數除以總論點數：

- **可追溯性**：有實際來源，且來源與追溯識別碼完整對齊。
- **覆蓋廣度**：論點具有未被去重的有效角度，且包含 `necessity:functional_gap` facet。
- **必要性明確度**：`functional_gap` 非空且至少 10 字元。
- **決策助益**：關聯知識明示決策助益，且與功能缺口及使用者價值一致。

- **具體描述定義**：`functional_gap` 欄位非空且長度 >= 10 字元
- **分數範圍**：0.0 ~ 1.0
- **狀態**：`calculated`（成功計算）、`missing_data`（資料不足）、`error`（計算錯誤）

#### 計算週期

採事件制逐筆計算：每次單一筆記產出或更新 `binding_report`，並在訂正稿或最終 `delivery_manifest` 序列化前重算。若只更新送達狀態而 `binding_report` 未變，本指標重算結果應保持不變；本規格不定義跨筆記的排程彙總。

#### 資料來源

- `binding_report.arguments[].functional_gap`
- `binding_report.arguments[].source_ids`
- `binding_report.arguments[].checks.{at_least_one_source,source_traceable,no_omitted_traces,no_extra_traces,has_functional_gap,has_related_knowledge,related_knowledge_consistent}`
- `binding_report.arguments[].angle_coverage.{covered_facets,effective_angle_count}`

#### 適用範圍

- **適用筆記類型**：所有經由 note_filler 管線處理的法律、規範、制度類筆記
- **適用段落類型**：`type = supplement` 的補充段落，即系統偵測到功能缺口後主動補齊的內容
- **不適用情形**：
  - 原稿段落（`type = original`）：不計算此指標，因為原稿為逐字不可變的基準內容
  - 無補充論點的筆記：若 `binding_report.arguments` 為空，`status = missing_data`
  - 降級補齊且標記為 `pending_evidence` 的段落：追溯性子分數會反映此狀態，但不影響整體適用性判定
- **跨筆記行為**：本指標為單筆記粒度，不跨筆記彙總或平均；每則筆記獨立計算一個分數
- **責任歸屬**：適用於所有進入 `process_file()` 管線的筆記成品，無論送達狀態為 `delivered` 或 `failed`

#### 統計粒度

- 最小判定單位：單一 `argument_id`；四個子分數皆逐論點產生布林判定。
- 分母：同一份 `binding_report.arguments` 的論點總數，不排除失敗或缺欄位論點。
- 報告單位：每則筆記、每次成品產出一個分數；不跨筆記或跨時間窗平均。

#### 門檻值

`status = calculated` 且分數 >= 0.70 才通過；`missing_data` 或 `error` 即使保有診斷分數也必須令 `passes_threshold = false`。

#### 缺失資料處理方式

- `functional_gap` 為空字串：視為無具體描述，不計入分子
- 論點無 `functional_gap` 欄位：該論點的必要性明確度記為 0
- `source_ids` 為有效空清單代表無實際來源：可追溯性記為 0，並維持既有 `pending_evidence`／來源綁定失敗語義，不得視為缺值而排除該論點
- `source_ids`、`checks` 或 `angle_coverage` 缺少可重算的清單、布林或數值依據：`basis_mode = partial_binding_report` 或 `primary_field_fallback`、`status = missing_data`，不得通過門檻
- 總論點數為 0：`status = missing_data`

#### 詳細統計欄位
```python
{
    "score": float,              # 0.0 ~ 1.0
    "total_score": float,        # 與 score 相同，明示加權總分
    "status": "calculated" | "missing_data" | "error",
    "threshold": 0.7,
    "passes_threshold": bool,
    "formula": "traceability*0.25 + ...",
    "subscores": {
        "traceability": {"score": float, "weight": 0.25, "numerator": int, "denominator": int, "rule": str},
        "coverage_breadth": { ... },
        "necessity_clarity": { ... },
        "decision_support": { ... },
    },
    "calculation_basis": list[dict],  # 每個 argument_id 的四項布林判定與實際 source_ids
    "basis_mode": "binding_report" | "partial_binding_report" | "primary_field_fallback" | "missing_data",
    "total_arguments": int,      # 總論點數
    "arguments_with_concrete_gap": int,   # 具體描述的功能缺口數
    "arguments_with_empty_gap": int,       # 空功能缺口數
    "arguments_missing_field": int,       # 缺失欄位的論點數
}
```

---

### 2. 使用者價值分數（User Value Score）

#### 名稱

使用者價值分數（User Value Score），序列化欄位為 `user_value_score`。

#### 目的

衡量單一筆記中的補充論點是否清楚說明對讀者的理解或決策價值，並同時具備可追溯來源、有效角度與一致的決策助益；避免只以固定模板或非空文字充當使用者價值。

#### 公式或判定規則

```
使用者價值分數 = 可追溯性 × 0.25 + 覆蓋廣度 × 0.25
                 + 必要性明確度 × 0.25 + 決策助益 × 0.25
```

四個子分數均為符合條件的論點數除以總論點數：

- **可追溯性**：有實際來源，且來源與追溯識別碼完整對齊。
- **覆蓋廣度**：論點具有未被去重的有效角度，且包含 `necessity:user_value` facet。
- **必要性明確度**：`user_value` 非空，且含「讀者」、「說明」、「理解」或對應英文語意。
- **決策助益**：關聯知識明示決策助益，且與功能缺口及使用者價值一致。

- **明確使用者價值定義**：`user_value` 欄位非空且包含關鍵詞「讀者」、「說明」、「理解」
- **分數範圍**：0.0 ~ 1.0
- **狀態**：`calculated`、`missing_data`、`error`

#### 計算週期

採事件制逐筆計算：每次單一筆記產出或更新 `binding_report`，並在訂正稿或最終 `delivery_manifest` 序列化前重算。若只更新送達狀態而 `binding_report` 未變，本指標重算結果應保持不變；本規格不定義跨筆記的排程彙總。

#### 資料來源

- `binding_report.arguments[].user_value`
- `binding_report.arguments[].source_ids`
- `binding_report.arguments[].checks.{at_least_one_source,source_traceable,no_omitted_traces,no_extra_traces,has_user_value,has_related_knowledge,related_knowledge_consistent}`
- `binding_report.arguments[].angle_coverage.{covered_facets,effective_angle_count}`

#### 適用範圍

- **適用筆記類型**：所有經由 note_filler 管線處理的法律、規範、制度類筆記
- **適用段落類型**：`type = supplement` 的補充段落，即系統偵測到功能缺口後主動補齊的內容
- **不適用情形**：
  - 原稿段落（`type = original`）：不計算此指標，因為原稿為逐字不可變的基準內容
  - 無補充論點的筆記：若 `binding_report.arguments` 為空，`status = missing_data`
  - 降級補齊且標記為 `pending_evidence` 的段落：追溯性子分數會反映此狀態，但不影響整體適用性判定
- **跨筆記行為**：本指標為單筆記粒度，不跨筆記彙總或平均；每則筆記獨立計算一個分數
- **責任歸屬**：適用於所有進入 `process_file()` 管線的筆記成品，無論送達狀態為 `delivered` 或 `failed`
- **關鍵詞檢查範圍**：必要性明確度子分數要求 `user_value` 包含「讀者」、「說明」、「理解」或對應英文語意（`reader`、`understand`、`explanation`），以確保價值說明非模板化填充

#### 統計粒度

- 最小判定單位：單一 `argument_id`；四個子分數皆逐論點產生布林判定。
- 分母：同一份 `binding_report.arguments` 的論點總數，不排除失敗或缺欄位論點。
- 報告單位：每則筆記、每次成品產出一個分數；不跨筆記或跨時間窗平均。

#### 門檻值

`status = calculated` 且分數 >= 0.70 才通過；`missing_data` 或 `error` 即使保有診斷分數也必須令 `passes_threshold = false`。

#### 缺失資料處理方式

- `user_value` 為空字串：視為無明確價值，不計入分子
- 論點無 `user_value` 欄位：該論點的必要性明確度記為 0
- `source_ids` 為有效空清單代表無實際來源：可追溯性記為 0，並維持既有 `pending_evidence`／來源綁定失敗語義，不得視為缺值而排除該論點
- `source_ids`、`checks` 或 `angle_coverage` 缺少可重算的清單、布林或數值依據：`basis_mode = partial_binding_report` 或 `primary_field_fallback`、`status = missing_data`，不得通過門檻
- 總論點數為 0：`status = missing_data`

#### 詳細統計欄位
```python
{
    "score": float,
    "total_score": float,
    "status": "calculated" | "missing_data" | "error",
    "threshold": 0.7,
    "passes_threshold": bool,
    "formula": "traceability*0.25 + ...",
    "subscores": {
        "traceability": { ... },
        "coverage_breadth": { ... },
        "necessity_clarity": { ... },
        "decision_support": { ... },
    },
    "calculation_basis": list[dict],
    "basis_mode": "binding_report" | "partial_binding_report" | "primary_field_fallback" | "missing_data",
    "total_arguments": int,
    "arguments_with_clear_value": int,     # 明確使用者價值的論點數
    "arguments_with_empty_value": int,     # 空使用者價值數
    "arguments_missing_field": int,       # 缺失欄位的論點數
}
```

---

### 3. 來源綁定完整性（Source Binding Integrity）

#### 計算公式
```
來源綁定完整性 = (binding_status=pass 的論點數) / (總論點數)
```

#### 判定規則
- 只計算 `binding_status = "pass"` 的論點
- **分數範圍**：0.0 ~ 1.0
- **合格門檻**：>= 0.8 (80%)
- **狀態**：`calculated`、`missing_data`、`error`

#### 資料來源
- `binding_report.arguments[].binding_status`
- `binding_report.summary`

#### 缺值處理
- 論點無 `binding_status` 欄位：視為缺值，`status = missing_data`
- 總論點數為 0：`status = missing_data`

#### 詳細統計欄位
```python
{
    "score": float,
    "status": "calculated" | "missing_data" | "error",
    "threshold": 0.8,
    "passes_threshold": bool,
    "total_arguments": int,
    "arguments_pass": int,        # pass 狀態論點數
    "arguments_fail": int,        # fail 狀態論點數
    "arguments_pending": int,     # pending_evidence 狀態論點數
    "arguments_missing_status": int,  # 缺失 status 欄位的論點數
}
```

---

### 4. 角度多樣性指數（Angle Diversity Index）

#### 計算公式
```
角度多樣性 = (唯一角度類型數) / (預期角度類型數)
```

#### 判定規則
- **唯一角度類型數**：`angle_coverage_summary.unique_angle_types` 長度
- **預期角度類型數**：固定為 8（definition, limitation, requirement, effect, procedure, exception, comparison, application）
- **分數範圍**：0.0 ~ 1.0
- **合格門檻**：>= 0.6 (60%)
- **狀態**：`calculated`、`missing_data`、`error`

#### 資料來源
- `binding_report.angle_coverage_summary.unique_angle_types`
- `binding_report.angle_coverage_summary.effective_angle_count`

#### 缺值處理
- `angle_coverage_summary` 缺失：`status = missing_data`
- `unique_angle_types` 為空：分數為 0.0

#### 詳細統計欄位
```python
{
    "score": float,
    "status": "calculated" | "missing_data" | "error",
    "threshold": 0.6,
    "passes_threshold": bool,
    "unique_angle_types": int,           # 唯一角度類型數
    "expected_angle_types": int,         # 預期角度類型數（固定 8）
    "effective_angle_count": int,        # 有效角度數
    "duplicate_ratio": float,            # 重複比率
    "unique_angle_type_names": list[str], # 唯一角度類型名稱列表
}
```

---

### 5. 端到端送達成功率（End-to-End Delivery Success Rate）

#### 計算公式
```
送達成功率 = (delivery_status 所有布林欄位皆為 True 的次數) / (總處理次數)
```

#### 判定規則
- **所有布林欄位**：`primary_note_ready`、`user_channel_sent`、`local_fallback_written`
- **分數範圍**：0.0 ~ 1.0
- **合格門檻**：>= 0.9 (90%)
- **狀態**：`calculated`、`missing_data`、`error`

#### 資料來源
- `delivery_manifest.delivery_status`
- `delivery_manifest.status`

#### 缺值處理
- `delivery_status` 缺失：`status = missing_data`
- 總處理次數為 0：`status = missing_data`

#### 詳細統計欄位
```python
{
    "score": float,
    "status": "calculated" | "missing_data" | "error",
    "threshold": 0.9,
    "passes_threshold": bool,
    "total_attempts": int,         # 總處理次數
    "successful_deliveries": int,   # 成功送達次數
    "failed_deliveries": int,      # 失敗送達次數
}
```

---

## 整體品質評估

### 北極星數值總分與追溯扣分

令 `M1..M5` 依序為既有五項核心指標分數，`T` 為功能缺口與使用者價值共用、已由
`source_ids` 與四個來源對齊 checks 重算的 `traceability` 子分數。五項核心指標等權；
因 `T` 在前兩項各占 0.25，故它對總分的直接權重為 `0.25 × (0.2 + 0.2) = 0.1`：

```text
overall_score = (M1 + M2 + M3 + M4 + M5) / 5
traceability_penalty = (1 - T) * 0.1
score_if_traceability_complete = overall_score + traceability_penalty
```

`score_if_traceability_complete` 固定其他分項，只回補 `T` 在功能缺口與使用者價值中的
直接扣分；若修正也讓來源綁定完整性上升，實際重算總分可以更高。

`T < 1` 或追溯資料不可量測時，`traceability_score.degraded = true`；逐論點
`calculation_basis[].traceability != true` 的 `argument_id` 必須列入
`affected_argument_ids`。驗收必須同時達到 `T = 1`、`penalty = 0`、
`affected_argument_ids = []`。五項既有門檻與 `overall_status` 判定不變。

### PolarisMetrics 總覽

#### 整體品質判定規則
- **poor**：任一核心指標為 `missing_data`；即使其餘分項通過數達 3 項以上亦不得判為高品質
- **excellent**：所有 5 個核心指標皆通過門檻
- **good**：至少 3 個核心指標通過門檻
- **acceptable**：至少 2 個核心指標通過門檻
- **poor**：少於 2 個核心指標通過門檻
- **error**：任何指標計算發生錯誤

#### 核心指標清單
1. 功能缺口分數
2. 使用者價值分數
3. 來源綁定完整性
4. 角度多樣性指數
5. 端到端送達成功率

#### 序列化結構
```python
{
    "schema": "note_filler.polaris_metrics.v1",
    "formula_version": "1.2",            # 公式、門檻與來源欄位契約版本
    "overall_status": "excellent" | "good" | "acceptable" | "poor" | "error",
    "decision": "excellent" | "good" | "acceptable" | "poor" | "error",
    "decision_rule": str,
    "core_metrics_pass_count": int,      # 通過門檻的核心指標數
    "core_metrics_total_count": int,     # 核心指標總數（固定 5）
    "overall_score": float,              # 五項核心指標等權，前兩項明確含追溯性
    "overall_score_formula": str,
    "score_if_traceability_complete": float,
    "overall_score_components": dict,
    "traceability_score": {
        "score": float,
        "status": "calculated" | "missing_data" | "error",
        "weight": 0.1,
        "penalty": float,
        "degraded": bool,
        "affected_argument_ids": list[str],
        "acceptance": {
            "target_score": 1.0,
            "target_penalty": 0.0,
            "affected_argument_ids": [],
        },
    },
    "calculated_at": str,                # ISO 8601 UTC 時間戳
    "functional_gap_score": { ... },     # 功能缺口分數詳情
    "user_value_score": { ... },          # 使用者價值分數詳情
    "source_binding_integrity": { ... },  # 來源綁定完整性詳情
    "angle_diversity_index": { ... },     # 角度多樣性指數詳情
    "delivery_success_rate": { ... },    # 端到端送達成功率詳情
    "traceability_markers": list[dict],   # 論點層級來源／待補證追溯標記
    "claim_source_map": dict[str, list[str]],  # argument_id → 實際引用來源
    "citation_span_map": list[dict],      # 引用標記在補充文字中的精確範圍
}
```

五項指標物件都固定帶出 `formula_version`、`formula`、`source_fields`、
`score`、`status`、`threshold`、`passes_threshold` 與 `decision`。其中
`source_fields` 只列計分實際讀取的 `binding_report` 或
`delivery_manifest.delivery_status` 欄位；`decision` 在可計算時為 `pass`／`fail`，
缺值或錯誤時則分別為 `missing_data`／`error`。公式、門檻或來源欄位語意改變時，
必須同步升級 `formula_version`。

---

## 可追溯性標記欄位定義

### 必填輸出契約

每則筆記的 `polaris_metrics` 必須輸出 `traceability_markers`、
`claim_source_map` 與 `citation_span_map` 三個機器可讀欄位。三個欄位皆不得省略或為
`null`；沒有補充論點時分別輸出 `[]`、`{}`、`[]`。這些欄位是原稿以外的旁路
metadata，不得改寫 `full_text` 或任何 `original` segment。Markdown／DOCX 的
「北極星追蹤」文字只供人閱讀，不能取代這三個 JSON 欄位。

以下公式使用：

- `A`：依 `argument_index` 排序的 `binding_report.arguments`。
- `S(a)`：論點 `a` 的 `source_ids` 原始順序清單；只含實際引用且已傳遞到成品的
  來源，不含 retrieved 候選來源，且驗收時要求不得重複。
- `T(a)`：論點 `a` 的 `trace_source_ids`。
- `C(a)`：撰寫階段解析出的有效 inline 引用標記出現紀錄；同一來源重複引用可有多筆。

### 1. `traceability_markers`

#### 欄位結構

```python
list[{
    "argument_id": str,
    "kind": "source" | "processing_record",
    "id": str,  # source ID 或 pending 的 processing record ID
    "binding_status": "pass" | "fail" | "pending_evidence",
}]
```

#### 公式

```text
traceability_markers = concat(
  每個 a ∈ A 的 Segment.traceability 紀錄
  投影為 (argument_id, kind, id, binding_status)
)
```

輸出保留論點順序及原始追溯紀錄順序，不在序列化時偷偷去重。有來源論點每個實際
來源輸出一筆 `kind = source`；無來源且明確待補證的論點輸出一筆
`kind = processing_record`。

#### 判定規則

- 有來源論點的 `kind = source` ID 清單必須與 `S(a)`、`T(a)` 完全相等，不得遺漏、
  額外加入或重複。
- `kind = processing_record` 只允許用於 `S(a) = []`、文字以 `【待補證】` 開頭且
  `binding_status = pending_evidence` 的論點；不得與同論點的 `kind = source` 並存。
- `binding_status = pass` 只允許實際來源、追溯標記、`claim_source_map` 與
  `citation_span_map` 全部對齊。法條來源另須先通過既有離線法條查核。
- 有來源但任一對齊條件不成立時必須為 `fail`；`pending_evidence` 不得算作通過。

#### 資料來源

- `CorrectionDoc.segments[type=supplement].{argument_id,traceability,confidence}`
- `binding_report.arguments[].{argument_id,trace_source_ids,binding_status}`
- `Segment.traceability` 中的 `source` 或 `processing_record` 紀錄

#### 缺值處理

- 欄位省略、為 `null`、非 list，或 item 缺少必填鍵：輸出契約驗收失敗，不得以空
  清單回退後宣稱成功。
- 有補充論點但完全沒有對應 marker：視為部分資料遺失，該論點綁定失敗；不得從
  `source_ids` 反向虛構 marker。
- 無來源論點保留 `processing_record` 並標為 `pending_evidence`；不得補入假來源。
- `A = []` 時 `[]` 是有效結構，但五項指標仍依既有「總論點數為 0」規則判為
  `missing_data`。

### 2. `claim_source_map`

#### 欄位結構

```python
dict[str, list[str]]  # 每個 argument_id 對應 0..n 個實際引用 source ID
```

#### 公式

```text
claim_source_map = {a.argument_id: S(a) for a in A}
```

#### 判定規則

- key 集合必須與 `A` 的 `argument_id` 集合完全相等；每個論點恰有一個 key。
- value 依實際引用順序排列且不得有重複或空字串：一個 ID 為 `one_to_one`，兩個以上
  為 `one_to_many`。
- value 只能來自 `WrittenSupplement.used_source_ids` 且確實存在於該 Segment 的
  `sources`；僅被檢索但未引用的來源不得列入。
- `claim_source_map[a]` 必須與該論點所有 `kind = source` marker 的 ID 集合一致，並
  由 `citation_span_map` 至少覆蓋每個 source ID 一次。
- 法條 source ID 只有在既有離線法條引用查核通過後才可列入。

#### 資料來源

- `WrittenSupplement.used_source_ids`
- `CorrectionDoc.segments[type=supplement].{argument_id,source_ids,sources}`
- `binding_report.arguments[].{argument_id,source_ids,cardinality}`

#### 缺值處理

- 欄位省略、為 `null`、非 object，或缺少任一 `argument_id`：輸出契約驗收失敗，且
  來源綁定不得通過。
- `A = []` 時輸出 `{}`。
- 明確 `pending_evidence` 論點輸出空清單 `[]`；這是已知無來源，不是可忽略的缺值，
  且不得計入來源綁定分子。
- 非 `pending_evidence` 論點為空清單、含未知來源或與 marker 不一致：該論點
  `binding_status = fail`，不得由 retrieved 候選來源自動補值。

### 3. `citation_span_map`

#### 欄位結構

```python
list[{
    "segment_index": int,
    "argument_id": str,
    "source_id": str,
    "span_start": int,  # 以 Unicode code point 計數，0-based，含頭
    "span_end": int,    # 以 Unicode code point 計數，0-based，不含尾
    "marker_text": str, # 例如 "[^1]"
}]
```

範圍一律相對於訂正稿 JSON 的 `segments[segment_index].text`，採半開區間
`[span_start, span_end)`；不得改以 Markdown／DOCX 經排版後的位移計算。

#### 公式

```text
citation_span_map = sort(
  {(segment_index(a), a.argument_id, source_id(c),
    start(c), end(c), text[start(c):end(c)])
   | a ∈ A, c ∈ C(a)},
  by=(segment_index, span_start, span_end, source_id)
)
```

`source_id(c)` 必須在撰寫階段依當時的來源序號解析並保留，不得在輸出階段只看
`[^n]` 字面值猜測來源。

#### 判定規則

- `segments[segment_index].text[span_start:span_end]` 必須逐字等於 `marker_text`，且
  `marker_text` 必須是已通過解析的有效 inline 引用標記。
- `argument_id` 必須指向同一 segment，`source_id` 必須存在於
  `claim_source_map[argument_id]`。
- `claim_source_map` 中每個 source ID 至少要有一筆 span；span 不得引用 map 以外的
  來源。重複引用同一來源可保留多筆不同 span，但 span 不得重疊或越界。
- `pending_evidence` 論點不得有 citation span；越界或無法對應來源的標記不得進入
  map，也不得據此掛來源。

#### 資料來源

- `write_supplement` 解析 `WrittenSupplement.text` 時的 inline marker 與來源序號對應
- `CorrectionDoc.segments[].{text,argument_id,source_ids,sources}`
- `binding_report.arguments[].{argument_id,segment_index,source_ids}`

#### 缺值處理

- 欄位省略、為 `null`、非 list，或 span item 型別／必填鍵錯誤：輸出契約驗收失敗，
  不得略過壞資料後繼續判為通過。
- 沒有有來源論點時輸出 `[]`；包含有來源論點卻為空，視為追溯資料遺失，相關論點
  綁定失敗。
- span 越界、對不到原文 marker、缺 source ID 或指向未知 source ID：該論點
  `binding_status = fail`，不得推測或補造範圍。

### 三欄一致性總判定

令 `source_pairs` 為 `claim_source_map` 的所有 `(argument_id, source_id)`，
`marker_pairs` 為 `traceability_markers` 中 `kind = source` 的相同 pair，
`span_pairs` 為 `citation_span_map` 的相同 pair 去重集合。每則有補充論點的筆記必須
同時滿足：

```text
keys(claim_source_map) = {a.argument_id | a ∈ A}
source_pairs = marker_pairs = span_pairs
```

等式成立且每筆 span 的字面、範圍與 segment 關聯皆有效，才可令既有
`checks.source_traceable`、`checks.no_omitted_traces` 與 `checks.no_extra_traces` 通過。
任一欄位結構缺失時 fail-closed，該筆記不得判為高品質或成功送達；欄位完整但集合
不一致時，逐論點標為 `fail`。這三欄是既有追溯資料的可驗收投影；五項分數公式
維持不變，但新增的北極星數值總分納入獨立追溯分量，因此 `formula_version` 升為
`1.2`。

---

## 資料流整合

### 輸出位置

北極星指標會自動整合到以下輸出：

1. **訂正稿 JSON**
   - 頂層欄位：`polaris_metrics`
   - `polaris_metrics` 固定含 `traceability_markers`、`claim_source_map`、
     `citation_span_map`
   - 每次輸出時由 `CorrectionDoc` 與綁定報告自動計算

2. **訂正稿 Markdown／DOCX**
   - 文末 `北極星分數` 與 `北極星追蹤` 區塊
   - 同步帶出公式版本、五項公式、來源欄位、分數與判定

3. **delivery_manifest.json**
   - 頂層欄位：`polaris_metrics`
   - 沿用訂正稿 JSON 的三個可追溯性欄位，不得重新推測或省略
   - 每次成功送達時自動計算並寫入

4. **binding_report.json**
   - 作為指標計算的主要資料來源
   - 提供論點層級的詳細資訊

### 計算時機

- **成功送達時**：在 `write_delivery_receipt` 前自動計算
- **user_channel_sent 更新時**：重新計算並更新 manifest
- **失敗時**：不計算指標（因為可能沒有完整的 binding_report）

---

## 實作模組

### 核心模組位置
- **指標計算**：`src/note_filler/metrics.py`
- **整合點**：`src/note_filler/__main__.py`

### 主要函式
```python
# 計算單一指標
calculate_functional_gap_score(arguments: list[dict]) -> FunctionalGapScore
calculate_user_value_score(arguments: list[dict]) -> UserValueScore
calculate_source_binding_integrity(arguments: list[dict]) -> SourceBindingIntegrity
calculate_angle_diversity_index(angle_coverage_summary: dict) -> AngleDiversityIndex
calculate_delivery_success_rate(delivery_status: dict) -> DeliverySuccessRate

# 計算所有指標
calculate_polaris_metrics(
    binding_report: dict,
    delivery_status: dict | None = None
) -> PolarisMetrics
```

### Dataclass 結構
所有指標物件皆為 dataclass，具備：
- 明確的型別標註
- `to_dict()` 方法用於序列化
- 詳細的統計欄位
- 狀態追蹤（`calculated`、`missing_data`、`error`）

---

## 閾值設定

### 預設門檻
```python
FUNCTIONAL_GAP_THRESHOLD = 0.7      # 70%
USER_VALUE_THRESHOLD = 0.7          # 70%
SOURCE_BINDING_THRESHOLD = 0.8      # 80%
ANGLE_DIVERSITY_THRESHOLD = 0.6     # 60%
DELIVERY_SUCCESS_THRESHOLD = 0.9     # 90%
```

### 閾值調整原則
- 閾值應根據實際品質需求調整
- 調整時需同步更新測試斷言
- 建議在配置檔中集中管理（未來擴展）

---

## 驗證與測試

### 測試覆蓋要求
1. **正向測試**：驗證指標計算正確性
2. **負例測試**：驗證缺值處理與錯誤處理
3. **邊界測試**：驗證門檻判定邏輯
4. **序列化測試**：驗證 `to_dict()` 輸出格式
5. **整合測試**：驗證與 delivery_manifest 的整合

### 測試檔案位置
- 測試檔案：`tests/test_metrics.py`（新增）
- 整合測試：`tests/test_e2e_acceptance.py`（更新）

---

## 使用範例

### Python API 使用
```python
from note_filler.metrics import calculate_polaris_metrics
from note_filler.binding_report import build_binding_report

# 假設已有 correction doc
binding_report = build_binding_report(correction)
delivery_status = {
    "primary_note_ready": True,
    "user_channel_sent": True,
    "local_fallback_written": True,
}

metrics = calculate_polaris_metrics(
    binding_report=binding_report,
    delivery_status=delivery_status,
)

# 序列化為 JSON
metrics_dict = metrics.to_dict()
import json
print(json.dumps(metrics_dict, indent=2, ensure_ascii=False))
```

### 從 delivery_manifest 讀取
```python
import json
from pathlib import Path

manifest_path = Path("output/delivery_manifest.json")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

polaris_metrics = manifest.get("polaris_metrics")
if polaris_metrics:
    print(f"整體品質: {polaris_metrics['overall_status']}")
    print(f"通過門檻指標數: {polaris_metrics['core_metrics_pass_count']}/5")
```

---

## 未來擴展方向

### 短期擴展
1. **指標歷史記錄**：追蹤指標趨勢變化
2. **閾值配置檔**：支援外部配置門檻值
3. **指標匯總報告**：跨檔案的指標聚合

### 長期擴展
1. **自適應門檻**：根據歷史資料動態調整門檻
2. **異常檢測**：識別指標異常波動
3. **品質預測**：基於指標預測最終品質

---

## 相關文件
- [筆記輸出資料流欄位盤點與北極星指標支援分析](./note-output-dataflow-metrics-inventory-2026-07-27.md)
- [binding_report 結構說明](../src/note_filler/binding_report.py)
- [angle_coverage 詳細說明](../src/note_filler/angle_coverage.py)

---

## 變更紀錄
- 2026-07-27：為功能缺口分數與使用者價值分數新增「適用範圍」章節，明確界定適用筆記類型、段落類型、不適用情形、跨筆記行為與責任歸屬
- 2026-07-27：新增每則筆記必填的可追溯性標記欄位、構造公式、判定規則、資料來源與缺值處理
- 2026-07-27：初始版本，定義 5 個核心指標與整體評估機制
