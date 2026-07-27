# 功能缺口與使用者價值指標規格

日期：2026-07-27
基準 revision：`21065f11`
Schema 版本：`note_filler.polaris_metrics.v1`
公式版本：`1.2`

## 概述

本規格文件專注於定義北極星筆記品質指標中的兩項核心指標：「功能缺口分數」與「使用者價值分數」。這兩項指標是衡量筆記品質的北極星指標，必須具備明確的計算公式、判定規則、資料來源、更新頻率、責任人及缺失資料處理方式。

---

## 1. 功能缺口分數（Functional Gap Score）

### 1.1 名稱
功能缺口分數（Functional Gap Score），序列化欄位為 `functional_gap_score`。

### 1.2 目的
衡量單一筆記中的補充論點是否針對具體功能缺口，並同時具備可追溯來源、有效角度與一致的決策助益；避免只因 `functional_gap` 有文字就將筆記判為高品質。

### 1.3 公式或判定規則

#### 計算公式
```
功能缺口分數 = 可追溯性 × 0.25 + 覆蓋廣度 × 0.25
               + 必要性明確度 × 0.25 + 決策助益 × 0.25
```

#### 子分數定義
四個子分數均為符合條件的論點數除以總論點數：

- **可追溯性**：有實際來源，且來源與追溯識別碼完整對齊。
  - 判定條件：`source_ids` 非空，且 `checks.at_least_one_source`、`checks.source_traceable`、`checks.no_omitted_traces`、`checks.no_extra_traces` 皆為 True

- **覆蓋廣度**：論點具有未被去重的有效角度，且包含 `necessity:functional_gap` facet。
  - 判定條件：`angle_coverage.effective_angle_count == 1` 且 `necessity:functional_gap` 在 `angle_coverage.covered_facets` 中

- **必要性明確度**：`functional_gap` 非空且至少 10 字元。
  - 判定條件：`functional_gap` 欄位非空且長度 >= 10 字元，且 `checks.has_functional_gap` 不為 False

- **決策助益**：關聯知識明示決策助益，且與功能缺口及使用者價值一致。
  - 判定條件：`checks.has_related_knowledge` 為 True 且 `checks.related_knowledge_consistent` 為 True

#### 分數範圍
- 0.0 ~ 1.0

#### 狀態定義
- `calculated`：成功計算
- `missing_data`：資料不足
- `error`：計算錯誤

#### 門檻值
- `status = calculated` 且分數 >= 0.70 才通過
- `missing_data` 或 `error` 即使保有診斷分數也必須令 `passes_threshold = false`

### 1.4 計算粒度

#### 最小判定單位
- 單一 `argument_id`；四個子分數皆逐論點產生布林判定

#### 分母定義
- 同一份 `binding_report.arguments` 的論點總數，不排除失敗或缺欄位論點

#### 報告單位
- 每則筆記、每次成品產出一個分數
- 不跨筆記或跨時間窗平均

### 1.5 資料來源

#### 主要欄位
- `binding_report.arguments[].functional_gap`
- `binding_report.arguments[].source_ids`
- `binding_report.arguments[].checks.{at_least_one_source,source_traceable,no_omitted_traces,no_extra_traces,has_functional_gap,has_related_knowledge,related_knowledge_consistent}`
- `binding_report.arguments[].angle_coverage.{covered_facets,effective_angle_count}`

#### 資料流路徑
- 原始來源：`gap.reason` → `Segment.functional_gap` → `binding_report.arguments[].functional_gap`
- 來源綁定：`WrittenSupplement.used_source_ids` → `Segment.source_ids` → `binding_report.arguments[].source_ids`
- 檢查結果：`binding_report._evaluate_argument()` → `binding_report.arguments[].checks`
- 角度覆蓋：`angle_coverage.build_angle_coverage()` → `binding_report.arguments[].angle_coverage`

### 1.6 適用範圍

#### 適用筆記類型
- 所有經由 note_filler 管線處理的法律、規範、制度類筆記

#### 適用段落類型
- `type = supplement` 的補充段落，即系統偵測到功能缺口後主動補齊的內容

#### 不適用情形
- 原稿段落（`type = original`）：不計算此指標，因為原稿為逐字不可變的基準內容
- 無補充論點的筆記：若 `binding_report.arguments` 為空，`status = missing_data`
- 降級補齊且標記為 `pending_evidence` 的段落：追溯性子分數會反映此狀態，但不影響整體適用性判定

#### 跨筆記行為
- 本指標為單筆記粒度，不跨筆記彙總或平均；每則筆記獨立計算一個分數

#### 責任歸屬
- 適用於所有進入 `process_file()` 管線的筆記成品，無論送達狀態為 `delivered` 或 `failed`

### 1.6 更新頻率

#### 計算週期
- 採事件制逐筆計算：每次單一筆記產出或更新 `binding_report`，並在訂正稿或最終 `delivery_manifest` 序列化前重算

#### 觸發條件
- 筆記補充論點新增或修改時
- 來源綁定狀態變更時
- 角度覆蓋分析重新計算時
- 訂正稿或 delivery_manifest 序列化前

#### 不重算條件
- 若只更新送達狀態而 `binding_report` 未變，本指標重算結果應保持不變
- 本規格不定義跨筆記的排程彙總

### 1.7 責任人

#### 計算責任
- **計算模組**：`src/note_filler/metrics.py` 中的 `calculate_functional_gap_score()` 函數
- **調用位置**：`src/note_filler/metrics.py` 中的 `calculate_polaris_metrics()` 函數
- **整合點**：`src/note_filler/__main__.py` 中的 `process_file()` 函數

#### 資料供應責任
- **功能缺口資料**：`detect_gaps` 模組（`gap.reason` 生成）
- **來源綁定資料**：`binding_report` 模組（`source_ids` 與 `checks` 生成）
- **角度覆蓋資料**：`angle_coverage` 模組（`angle_coverage` 生成）

#### 驗證責任
- **單元測試**：`tests/test_metrics.py` 中的功能缺口分數測試
- **整合測試**：`tests/test_polaris_metrics_e2e.py` 中的端到端驗收測試
- **回歸測試**：確保公式變更時既有測試仍通過

### 1.8 缺失資料處理方式

#### 欄位層級處理
- `functional_gap` 為空字串：視為無具體描述，不計入分子
- 論點無 `functional_gap` 欄位：該論點的必要性明確度記為 0
- `source_ids` 為有效空清單代表無實際來源：可追溯性記為 0，並維持既有 `pending_evidence`／來源綁定失敗語義，不得視為缺值而排除該論點
- `source_ids`、`checks` 或 `angle_coverage` 缺少可重算的清單、布林或數值依據：`basis_mode = partial_binding_report` 或 `primary_field_fallback`、`status = missing_data`，不得通過門檻
- 總論點數為 0：`status = missing_data`

#### 狀態判定規則
- 所有論點的 `source_ids`、`checks` 與 `angle_coverage` 都具備可重算型別時才標為 `calculated`
- 欄位名稱雖齊全但值僅為敘述文字，或只有部分論點具備依據時，皆標為 `missing_data` 且整體品質降為 `poor`

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

## 2. 使用者價值分數（User Value Score）

### 2.1 名稱
使用者價值分數（User Value Score），序列化欄位為 `user_value_score`。

### 2.2 目的
衡量單一筆記中的補充論點是否清楚說明對讀者的理解或決策價值，並同時具備可追溯來源、有效角度與一致的決策助益；避免只以固定模板或非空文字充當使用者價值。

### 2.3 公式或判定規則

#### 計算公式
```
使用者價值分數 = 可追溯性 × 0.25 + 覆蓋廣度 × 0.25
                 + 必要性明確度 × 0.25 + 決策助益 × 0.25
```

#### 子分數定義
四個子分數均為符合條件的論點數除以總論點數：

- **可追溯性**：有實際來源，且來源與追溯識別碼完整對齊。
  - 判定條件：`source_ids` 非空，且 `checks.at_least_one_source`、`checks.source_traceable`、`checks.no_omitted_traces`、`checks.no_extra_traces` 皆為 True

- **覆蓋廣度**：論點具有未被去重的有效角度，且包含 `necessity:user_value` facet。
  - 判定條件：`angle_coverage.effective_angle_count == 1` 且 `necessity:user_value` 在 `angle_coverage.covered_facets` 中

- **必要性明確度**：`user_value` 非空，且含「讀者」、「說明」、「理解」或對應英文語意。
  - 判定條件：`user_value` 欄位非空且包含關鍵詞「讀者」、「說明」、「理解」、「reader」、「understand」、「explanation」，且 `checks.has_user_value` 不為 False

- **決策助益**：關聯知識明示決策助益，且與功能缺口及使用者價值一致。
  - 判定條件：`checks.has_related_knowledge` 為 True 且 `checks.related_knowledge_consistent` 為 True

#### 分數範圍
- 0.0 ~ 1.0

#### 狀態定義
- `calculated`：成功計算
- `missing_data`：資料不足
- `error`：計算錯誤

#### 門檻值
- `status = calculated` 且分數 >= 0.70 才通過
- `missing_data` 或 `error` 即使保有診斷分數也必須令 `passes_threshold = false`

### 2.4 計算粒度

#### 最小判定單位
- 單一 `argument_id`；四個子分數皆逐論點產生布林判定

#### 分母定義
- 同一份 `binding_report.arguments` 的論點總數，不排除失敗或缺欄位論點

#### 報告單位
- 每則筆記、每次成品產出一個分數
- 不跨筆記或跨時間窗平均

### 2.5 資料來源

#### 主要欄位
- `binding_report.arguments[].user_value`
- `binding_report.arguments[].source_ids`
- `binding_report.arguments[].checks.{at_least_one_source,source_traceable,no_omitted_traces,no_extra_traces,has_user_value,has_related_knowledge,related_knowledge_consistent}`
- `binding_report.arguments[].angle_coverage.{covered_facets,effective_angle_count}`

#### 資料流路徑
- 原始來源：從 `gap.question` 推導 → `Segment.user_value` → `binding_report.arguments[].user_value`
- 來源綁定：`WrittenSupplement.used_source_ids` → `Segment.source_ids` → `binding_report.arguments[].source_ids`
- 檢查結果：`binding_report._evaluate_argument()` → `binding_report.arguments[].checks`
- 角度覆蓋：`angle_coverage.build_angle_coverage()` → `binding_report.arguments[].angle_coverage`

### 2.6 適用範圍

#### 適用筆記類型
- 所有經由 note_filler 管線處理的法律、規範、制度類筆記

#### 適用段落類型
- `type = supplement` 的補充段落，即系統偵測到功能缺口後主動補齊的內容

#### 不適用情形
- 原稿段落（`type = original`）：不計算此指標，因為原稿為逐字不可變的基準內容
- 無補充論點的筆記：若 `binding_report.arguments` 為空，`status = missing_data`
- 降級補齊且標記為 `pending_evidence` 的段落：追溯性子分數會反映此狀態，但不影響整體適用性判定

#### 跨筆記行為
- 本指標為單筆記粒度，不跨筆記彙總或平均；每則筆記獨立計算一個分數

#### 責任歸屬
- 適用於所有進入 `process_file()` 管線的筆記成品，無論送達狀態為 `delivered` 或 `failed`

#### 關鍵詞檢查範圍
- 必要性明確度子分數要求 `user_value` 包含「讀者」、「說明」、「理解」或對應英文語意（`reader`、`understand`、`explanation`），以確保價值說明非模板化填充

### 2.6 更新頻率

#### 計算週期
- 採事件制逐筆計算：每次單一筆記產出或更新 `binding_report`，並在訂正稿或最終 `delivery_manifest` 序列化前重算

#### 觸發條件
- 筆記補充論點新增或修改時
- 來源綁定狀態變更時
- 角度覆蓋分析重新計算時
- 訂正稿或 delivery_manifest 序列化前

#### 不重算條件
- 若只更新送達狀態而 `binding_report` 未變，本指標重算結果應保持不變
- 本規格不定義跨筆記的排程彙總

### 2.7 責任人

#### 計算責任
- **計算模組**：`src/note_filler/metrics.py` 中的 `calculate_user_value_score()` 函數
- **調用位置**：`src/note_filler/metrics.py` 中的 `calculate_polaris_metrics()` 函數
- **整合點**：`src/note_filler/__main__.py` 中的 `process_file()` 函數

#### 資料供應責任
- **使用者價值資料**：`correction.py` 中的 `assemble_correction()` 函數（從 `gap.question` 推導）
- **來源綁定資料**：`binding_report` 模組（`source_ids` 與 `checks` 生成）
- **角度覆蓋資料**：`angle_coverage` 模組（`angle_coverage` 生成）

#### 驗證責任
- **單元測試**：`tests/test_metrics.py` 中的使用者價值分數測試
- **整合測試**：`tests/test_polaris_metrics_e2e.py` 中的端到端驗收測試
- **回歸測試**：確保公式變更時既有測試仍通過

### 2.8 缺失資料處理方式

#### 欄位層級處理
- `user_value` 為空字串：視為無明確價值，不計入分子
- 論點無 `user_value` 欄位：該論點的必要性明確度記為 0
- `source_ids` 為有效空清單代表無實際來源：可追溯性記為 0，並維持既有 `pending_evidence`／來源綁定失敗語義，不得視為缺值而排除該論點
- `source_ids`、`checks` 或 `angle_coverage` 缺少可重算的清單、布林或數值依據：`basis_mode = partial_binding_report` 或 `primary_field_fallback`、`status = missing_data`，不得通過門檻
- 總論點數為 0：`status = missing_data`

#### 狀態判定規則
- 所有論點的 `source_ids`、`checks` 與 `angle_coverage` 都具備可重算型別時才標為 `calculated`
- 欄位名稱雖齊全但值僅為敘述文字，或只有部分論點具備依據時，皆標為 `missing_data` 且整體品質降為 `poor`

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

## 3. 兩項指標的共同特性

### 3.1 共用計算架構
兩項指標採用相同的四面向量化公式與權重配置：
- 權重配置：可追溯性 0.25、覆蓋廣度 0.25、必要性明確度 0.25、決策助益 0.25
- 計算架構：共用 `_quality_score_breakdown()` 函數進行子分數計算
- 判定邏輯：皆要求 `basis_mode = "binding_report"` 才能標為 `calculated`

### 3.2 共用資料依賴
兩項指標都依賴以下資料結構：
- `source_ids`：來源綁定狀態
- `checks`：各項檢查結果
- `angle_coverage`：角度覆蓋分析

### 3.3 共用驗收標準
- 狀態必須為 `calculated` 且分數 >= 0.70 才通過門檻
- `missing_data` 或 `error` 狀態一律不得通過門檻
- 不可量測或部分可量測資料一律不得判為高品質

### 3.4 差異點對比

| 項目 | 功能缺口分數 | 使用者價值分數 |
|------|-------------|---------------|
| 主要欄位 | `functional_gap` | `user_value` |
| Facet 要求 | `necessity:functional_gap` | `necessity:user_value` |
| 必要性判定 | 長度 >= 10 字元 | 包含關鍵詞「讀者」、「說明」、「理解」 |
| 關鍵詞檢查 | 無 | 有（中英文關鍵詞） |
| 資料來源 | `gap.reason` | 從 `gap.question` 推導 |

---

## 4. 整合輸出位置

### 4.1 訂正稿 JSON
- 頂層欄位：`polaris_metrics.functional_gap_score`
- 頂層欄位：`polaris_metrics.user_value_score`

### 4.2 訂正稿 Markdown／DOCX
- 文末「北極星分數」區塊中顯示兩項分數

### 4.3 delivery_manifest.json
- 頂層欄位：`polaris_metrics.functional_gap_score`
- 頂層欄位：`polaris_metrics.user_value_score`

---

## 5. 相關文件

- [北極星筆記品質指標規格](./polaris-metrics-specification-2026-07-27.md) - 完整的五項指標定義
- [北極星品質指標欄位規格](./polaris_metrics_field_specification.md) - 欄位來源與資料流詳細定義
- [指標計算實作](../src/note_filler/metrics.py) - 實際計算邏輯

---

## 6. 變更紀錄

- 2026-07-27：為功能缺口分數與使用者價值分數新增「適用範圍」章節，明確界定適用筆記類型、段落類型、不適用情形、跨筆記行為、責任歸屬與關鍵詞檢查範圍
- 2026-07-27：初始版本，定義功能缺口與使用者價值兩項核心指標的完整規格，包含責任人資訊