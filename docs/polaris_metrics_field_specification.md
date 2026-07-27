# 北極星品質指標欄位規格

**日期**: 2026-07-27  
**任務**: 盤點筆記成品輸出與資料流，定義北極星品質指標的欄位來源與規格  
**範圍**: `src/note_filler/` 資料流與輸出格式

---

## 1. 資料流概覽

### 1.1 主流程路徑

```
原始輸入 (.txt/.docx)
  └─ parse_note (T2)
      └─ detect_domain (T3)
          └─ generate_questions (T4)
              └─ detect_gaps (T5)
                  └─ for each gap:
                      ├─ retrieve_for_gap (T9)
                      ├─ write_supplement (Q3)
                      └─ cross_validate (T10)
                  └─ assemble_correction (T12)
                      └─ export (to_json/to_markdown/to_docx)
                          └─ delivery_manifest.json
```

### 1.2 關鍵資料結構轉換

| 階段 | 資料結構 | 關鍵欄位 |
|------|----------|----------|
| Gap Detection | `Gap` | `question`, `reason` |
| Supplement Writing | `WrittenSupplement` | `text`, `used_source_ids` |
| Correction Assembly | `Segment` | `functional_gap`, `user_value`, `source_ids`, `angle_tags`, `confidence` |
| Binding Report | `binding_report.json` | `arguments[].functional_gap`, `arguments[].user_value`, `arguments[].source_ids`, `arguments[].angle_tags` |
| Metrics Calculation | `PolarisMetrics` | 五項品質指標分數 |
| Final Output | `.json/.md/.docx` | `polaris_metrics`, `delivery_status` |

---

## 2. 北極星品質指標輸入欄位集合

### 2.1 核心輸入欄位

每則筆記計算北極星品質指標需要以下輸入欄位：

| 欄位名稱 | 資料類型 | 來源位置 | 說明 |
|----------|----------|----------|------|
| `functional_gap` | string | `Segment.functional_gap` / `binding_report.arguments[].functional_gap` | 功能缺口描述，來自 `gap.reason` |
| `user_value` | string | `Segment.user_value` / `binding_report.arguments[].user_value` | 使用者價值描述，從 `gap.question` 推導 |
| `source_ids` | list[string] | `Segment.source_ids` / `binding_report.arguments[].source_ids` | 實際引用的來源識別碼列表 |
| `angle_tags` | list[string] | `Segment.angle_tags` / `binding_report.arguments[].angle_tags` | 角度標籤列表，來自角度覆蓋分析 |
| `delivery_status` | dict | `delivery_manifest.delivery_status` | 送達狀態，包含多個布林欄位 |
| `binding_status` | string | `binding_report.arguments[].binding_status` | 綁定狀態：pass/fail/pending_evidence |
| `checks` | dict | `binding_report.arguments[].checks` | 來源對齊、必要性與關聯知識一致性的布林判定 |
| `angle_coverage` | dict | `binding_report.arguments[].angle_coverage` | 每個論點的有效角度與 covered facets |
| `angle_coverage_summary` | dict | `binding_report.angle_coverage_summary` | 角度覆蓋摘要，用於角度多樣性計算 |

### 2.2 欄位詳細定義

#### 2.2.1 functional_gap

- **資料來源**: `gap.reason` → `Segment.functional_gap`
- **生成位置**: `correction.py:assemble_correction()` 第 303 行
- **資料類型**: string
- **預設值**: `""` (空字串)
- **計算時機**: 在 `assemble_correction` 中從 `gap.reason` 直接賦值
- **缺值處理**: 
  - 空字串: 視為無具體描述，不計入功能缺口分數分子
  - 欄位缺失: 該論點的必要性明確度子分數記為 0

#### 2.2.2 user_value

- **資料來源**: 從 `gap.question` 推導 → `Segment.user_value`
- **生成位置**: `correction.py:assemble_correction()` 第 304 行
- **資料類型**: string
- **預設值**: `""` (空字串)
- **計算時機**: 在 `assemble_correction` 中以模板 `"補齊讀者對「{question}」所需的說明"` 生成
- **缺值處理**:
  - 空字串: 視為無明確價值，不計入使用者價值分數分子
  - 欄位缺失: 該論點的必要性明確度子分數記為 0

#### 2.2.3 source_ids

- **資料來源**: `WrittenSupplement.used_source_ids` → `Segment.source_ids`
- **生成位置**: `correction.py:assemble_correction()` 第 339 行
- **資料類型**: list[string]
- **預設值**: `[]` (空列表)
- **計算時機**: 在 `assemble_correction` 中從 `used_source_ids` 賦值，過濾掉無法在 retrieved 中找到的 ID
- **缺值處理**:
  - 空列表: 視為無來源，綁定狀態為 `pending_evidence` 或 `fail`
  - 欄位缺失: 視為缺值，指標狀態為 `missing_data`

#### 2.2.4 angle_tags

- **資料來源**: `angle_coverage.build_angle_coverage()` → `Segment.angle_tags`
- **生成位置**: `correction.py:assemble_correction()` 第 312-317 行，後續在第 354-362 行更新
- **資料類型**: list[string]
- **預設值**: `[]` (空列表)
- **計算時機**: 在 `assemble_correction` 中先計算基本角度覆蓋，然後在跨論點分析後更新完整角度欄位
- **缺值處理**:
  - 空列表: 視為無角度標籤，角度多樣性分數為 0.0
  - 欄位缺失: 視為缺值，指標狀態為 `missing_data`

#### 2.2.5 delivery_status

- **資料來源**: `__main__._delivery_status()` → `delivery_manifest.json`
- **生成位置**: `__main__.py:process_file()` 第 256-259 行
- **資料類型**: dict
- **子欄位**:
  - `primary_note_ready`: bool - 成品筆記是否就緒
  - `user_channel_sent`: bool - 是否已送達使用者通道
  - `local_fallback_written`: bool - 本機後援是否已寫入
  - `segment_delivery_details`: list[dict] - 逐段送達詳細資訊
- **預設值**: 所有欄位預設為 `False`
- **計算時機**: 在 `process_file` 中根據實際輸出狀態設定
- **缺值處理**:
  - 欄位缺失: 視為缺值，指標狀態為 `missing_data`
  - 部分欄位缺失: 僅根據現有欄位計算，可能在日誌中警告

#### 2.2.6 binding_status

- **資料來源**: `binding_report._evaluate_argument()` → `binding_report.arguments[].binding_status`
- **生成位置**: `binding_report.py:_evaluate_argument()` 第 390-402 行
- **資料類型**: string (enum: "pass", "fail", "pending_evidence")
- **預設值**: 無預設值，必須明確計算
- **計算時機**: 在 `build_binding_report` 中對每個論點評估
- **判定規則**:
  - `pass`: 有來源且所有檢查項通過
  - `fail`: 有來源但部分檢查項失敗，或無來源但不符合 pending 條件
  - `pending_evidence`: 無來源但符合 pending 條件（confidence="pending_evidence" 且可追溯）
- **缺值處理**:
  - 欄位缺失: 視為缺值，指標狀態為 `missing_data`

#### 2.2.7 angle_coverage_summary

- **資料來源**: `angle_coverage.summarize_angle_coverage()` → `binding_report.angle_coverage_summary`
- **生成位置**: `binding_report.py:build_binding_report()` 第 457 行
- **資料類型**: dict
- **子欄位**:
  - `unique_angle_types`: list[string] - 唯一角度類型列表
  - `effective_angle_count`: int - 有效角度數量
  - `duplicate_ratio`: float - 重複率
  - `coverage_ok`: bool - 覆蓋是否合格
- **預設值**: 見 `angle_coverage.py` 中的預設值
- **計算時機**: 在 `build_binding_report` 中跨論點分析後計算
- **缺值處理**:
  - 欄位缺失: 視為缺值，指標狀態為 `missing_data`
  - 子欄位缺失: 僅根據現有子欄位計算，可能在日誌中警告

### 2.3 功能缺口與使用者價值的量化公式

兩項分數皆採四子分數等權加總：

```text
總分 = traceability*0.25 + coverage_breadth*0.25
       + necessity_clarity*0.25 + decision_support*0.25
```

每個子分數皆為「符合條件論點數 / 總論點數」。可追溯性要求有實際 `source_ids` 且來源追溯完整對齊；覆蓋廣度要求有效角度含對應的 `necessity:functional_gap` 或 `necessity:user_value` facet；必要性明確度依功能缺口字數或使用者理解語意判斷；決策助益要求關聯知識存在且跨欄位一致。輸出保留各子分數的 numerator、denominator、rule、weight，以及逐 `argument_id` 的 `calculation_basis`。

---

## 3. 缺值處理規則

### 3.1 指標層級缺值處理

| 指標名稱 | 必需欄位 | 缺值處理策略 | 指標狀態 |
|----------|----------|--------------|----------|
| FunctionalGapScore | `functional_gap`、`source_ids`、`checks`、`angle_coverage` | 個別欄位缺失時對應子分數記 0；總論點數為 0 | `calculated`／`missing_data` |
| UserValueScore | `user_value`、`source_ids`、`checks`、`angle_coverage` | 個別欄位缺失時對應子分數記 0；總論點數為 0 | `calculated`／`missing_data` |
| SourceBindingIntegrity | `binding_status` | 欄位缺失或總論點數為 0 | `missing_data` |
| AngleDiversityIndex | `angle_coverage_summary` | 欄位缺失 | `missing_data` |
| DeliverySuccessRate | `delivery_status` | 欄位缺失 | `missing_data` |

### 3.2 欄位層級缺值處理

#### 3.2.1 functional_gap

- **空字串處理**: 視為無具體描述，不計入分子但計入分母
- **欄位缺失**: 視為缺值，整個指標狀態為 `missing_data`
- **類型錯誤**: 嘗試轉為字串，失敗則視為空字串

#### 3.2.2 user_value

- **空字串處理**: 視為無明確價值，不計入分子但計入分母
- **欄位缺失**: 視為缺值，整個指標狀態為 `missing_data`
- **類型錯誤**: 嘗試轉為字串，失敗則視為空字串

#### 3.2.3 source_ids

- **空列表處理**: 視為無來源，綁定狀態為 `pending_evidence` 或 `fail`
- **欄位缺失**: 視為缺值，整個指標狀態為 `missing_data`
- **類型錯誤**: 嘗試轉為列表，失敗則視為空列表

#### 3.2.4 angle_tags

- **空列表處理**: 視為無角度標籤，角度多樣性分數為 0.0
- **欄位缺失**: 視為缺值，整個指標狀態為 `missing_data`
- **類型錯誤**: 嘗試轉為列表，失敗則視為空列表

#### 3.2.5 delivery_status

- **欄位缺失**: 視為缺值，整個指標狀態為 `missing_data`
- **部分子欄位缺失**: 僅根據現有子欄位計算，記錄警告
- **類型錯誤**: 嘗試轉為 dict，失敗則視為缺值

#### 3.2.6 binding_status

- **欄位缺失**: 視為缺值，整個指標狀態為 `missing_data`
- **無效值**: 不在 {"pass", "fail", "pending_evidence"} 中，視為缺值
- **類型錯誤**: 嘗試轉為字串，失敗則視為缺值

#### 3.2.7 angle_coverage_summary

- **欄位缺失**: 視為缺值，整個指標狀態為 `missing_data`
- **部分子欄位缺失**: 僅根據現有子欄位計算，記錄警告
- **類型錯誤**: 嘗試轉為 dict，失敗則視為缺值

---

## 4. 最終輸出位置

### 4.1 JSON 格式輸出

- **檔案位置**: `{input_path}.訂正稿.json`
- **輸出函數**: `export.to_json()`
- **北極星指標位置**: `polaris_metrics` 欄位 (頂層)
- **結構**:
```json
{
  "schema": "note_filler.binding_report.v1",
  "source_path": "...",
  "binding_summary": {...},
  "angle_coverage_summary": {...},
  "polaris_metrics": {
    "schema": "note_filler.polaris_metrics.v1",
    "overall_status": "excellent|good|acceptable|poor|error",
    "core_metrics_pass_count": 5,
    "core_metrics_total_count": 5,
    "calculated_at": "2026-07-27T...",
    "functional_gap_score": {...},
    "user_value_score": {...},
    "source_binding_integrity": {...},
    "angle_diversity_index": {...},
    "delivery_success_rate": {...}
  },
  "segments": [...]
}
```

### 4.2 Markdown 格式輸出

- **檔案位置**: `{input_path}.訂正稿.md`
- **輸出函數**: `export.to_markdown()`
- **北極星指標位置**: 文末摘要區塊
- **結構**:
```markdown
... (筆記內容)

---

> **來源綁定**：...
> **角度覆蓋摘要**：...
> **北極星分數**：overall=excellent（pass 5/5）；functional_gap=0.95（✓）；user_value=0.90（✓）；source_binding=0.85（✓）；angle_diversity=0.75（✓）；delivery=1.00（✓）
```

### 4.3 DOCX 格式輸出

- **檔案位置**: `{input_path}.訂正稿.docx`
- **輸出函數**: `export.to_docx()`
- **北極星指標位置**: 文末段落
- **結構**: 與 Markdown 類似，以段落形式呈現

### 4.4 Delivery Manifest

- **檔案位置**: `{output_dir}/delivery_manifest.json`
- **輸出函數**: `__main__.write_delivery_receipt()`
- **北極星指標位置**: `polaris_metrics` 欄位
- **結構**:
```json
{
  "output_path": "...",
  "input_path": "...",
  "status": "delivered|failed",
  "timestamp": "2026-07-27T...",
  "content_hash": "...",
  "format": "md|json|docx",
  "supplements": 3,
  "verified": 2,
  "delivery_status": {
    "primary_note_ready": true,
    "user_channel_sent": true,
    "local_fallback_written": true,
    "segment_delivery_details": [...]
  },
  "polaris_metrics": {
    "schema": "note_filler.polaris_metrics.v1",
    "overall_status": "excellent",
    ...
  }
}
```

---

## 5. 機器可讀取指標規格結構

### 5.1 規格結構定義

```json
{
  "schema": "note_filler.polaris_field_specification.v1",
  "version": "1.0",
  "specification_date": "2026-07-27",
  "field_definitions": {
    "functional_gap": {
      "data_type": "string",
      "source_location": "Segment.functional_gap",
      "binding_report_path": "arguments[].functional_gap",
      "generation_stage": "assemble_correction",
      "default_value": "",
      "required_for_metrics": ["FunctionalGapScore"],
      "missing_data_handling": "status=missing_data",
      "empty_value_handling": "not_counted_in_numerator"
    },
    "user_value": {
      "data_type": "string",
      "source_location": "Segment.user_value",
      "binding_report_path": "arguments[].user_value",
      "generation_stage": "assemble_correction",
      "default_value": "",
      "required_for_metrics": ["UserValueScore"],
      "missing_data_handling": "status=missing_data",
      "empty_value_handling": "not_counted_in_numerator"
    },
    "source_ids": {
      "data_type": "list[string]",
      "source_location": "Segment.source_ids",
      "binding_report_path": "arguments[].source_ids",
      "generation_stage": "assemble_correction",
      "default_value": "[]",
      "required_for_metrics": ["SourceBindingIntegrity"],
      "missing_data_handling": "status=missing_data",
      "empty_value_handling": "binding_status=pending_evidence_or_fail"
    },
    "angle_tags": {
      "data_type": "list[string]",
      "source_location": "Segment.angle_tags",
      "binding_report_path": "arguments[].angle_tags",
      "generation_stage": "assemble_correction",
      "default_value": "[]",
      "required_for_metrics": ["AngleDiversityIndex"],
      "missing_data_handling": "status=missing_data",
      "empty_value_handling": "score=0.0"
    },
    "delivery_status": {
      "data_type": "dict",
      "source_location": "delivery_manifest.delivery_status",
      "binding_report_path": null,
      "generation_stage": "process_file",
      "default_value": "{\"primary_note_ready\":false,\"user_channel_sent\":false,\"local_fallback_written\":false}",
      "required_for_metrics": ["DeliverySuccessRate"],
      "missing_data_handling": "status=missing_data",
      "sub_fields": {
        "primary_note_ready": {"type": "bool", "default": false},
        "user_channel_sent": {"type": "bool", "default": false},
        "local_fallback_written": {"type": "bool", "default": false},
        "segment_delivery_details": {"type": "list[dict]", "default": "[]"}
      }
    },
    "binding_status": {
      "data_type": "string",
      "source_location": "binding_report.arguments[].binding_status",
      "binding_report_path": "arguments[].binding_status",
      "generation_stage": "build_binding_report",
      "default_value": null,
      "required_for_metrics": ["SourceBindingIntegrity"],
      "missing_data_handling": "status=missing_data",
      "valid_values": ["pass", "fail", "pending_evidence"]
    },
    "checks": {
      "data_type": "dict",
      "source_location": "binding_report.arguments[].checks",
      "binding_report_path": "arguments[].checks",
      "generation_stage": "build_binding_report",
      "default_value": null,
      "required_for_metrics": ["FunctionalGapScore", "UserValueScore"],
      "missing_data_handling": "affected_subscores=0"
    },
    "angle_coverage": {
      "data_type": "dict",
      "source_location": "binding_report.arguments[].angle_coverage",
      "binding_report_path": "arguments[].angle_coverage",
      "generation_stage": "build_binding_report",
      "default_value": null,
      "required_for_metrics": ["FunctionalGapScore", "UserValueScore"],
      "missing_data_handling": "coverage_breadth=0"
    },
    "angle_coverage_summary": {
      "data_type": "dict",
      "source_location": "binding_report.angle_coverage_summary",
      "binding_report_path": "angle_coverage_summary",
      "generation_stage": "build_binding_report",
      "default_value": null,
      "required_for_metrics": ["AngleDiversityIndex"],
      "missing_data_handling": "status=missing_data",
      "sub_fields": {
        "unique_angle_types": {"type": "list[string]", "default": "[]"},
        "effective_angle_count": {"type": "int", "default": 0},
        "duplicate_ratio": {"type": "float", "default": 0.0},
        "coverage_ok": {"type": "bool", "default": false}
      }
    }
  },
  "metric_definitions": {
    "FunctionalGapScore": {
      "required_fields": ["functional_gap", "source_ids", "checks", "angle_coverage"],
      "calculation_formula": "traceability*0.25 + coverage_breadth*0.25 + necessity_clarity*0.25 + decision_support*0.25",
      "threshold": 0.7,
      "subscore_weights": {
        "traceability": 0.25,
        "coverage_breadth": 0.25,
        "necessity_clarity": 0.25,
        "decision_support": 0.25
      },
      "subscore_rules": {
        "traceability": "actual source_ids and aligned source trace checks / total_arguments",
        "coverage_breadth": "effective angles with necessity:functional_gap facet / total_arguments",
        "necessity_clarity": "functional_gap length >= 10 / total_arguments",
        "decision_support": "related knowledge present and cross-field consistent / total_arguments"
      }
    },
    "UserValueScore": {
      "required_fields": ["user_value", "source_ids", "checks", "angle_coverage"],
      "calculation_formula": "traceability*0.25 + coverage_breadth*0.25 + necessity_clarity*0.25 + decision_support*0.25",
      "threshold": 0.7,
      "clear_value_keywords": ["讀者", "說明", "理解", "reader", "understand", "explanation"],
      "subscore_weights": {
        "traceability": 0.25,
        "coverage_breadth": 0.25,
        "necessity_clarity": 0.25,
        "decision_support": 0.25
      },
      "subscore_rules": {
        "traceability": "actual source_ids and aligned source trace checks / total_arguments",
        "coverage_breadth": "effective angles with necessity:user_value facet / total_arguments",
        "necessity_clarity": "user_value with explicit reader understanding semantics / total_arguments",
        "decision_support": "related knowledge present and cross-field consistent / total_arguments"
      }
    },
    "SourceBindingIntegrity": {
      "required_fields": ["binding_status"],
      "calculation_formula": "arguments_pass / total_arguments",
      "threshold": 0.8,
      "pass_condition": "binding_status == 'pass'"
    },
    "AngleDiversityIndex": {
      "required_fields": ["angle_coverage_summary"],
      "calculation_formula": "unique_angle_types / expected_angle_types",
      "threshold": 0.6,
      "expected_angle_types": 8
    },
    "DeliverySuccessRate": {
      "required_fields": ["delivery_status"],
      "calculation_formula": "successful_deliveries / total_attempts",
      "threshold": 0.9,
      "success_condition": "all boolean fields are true"
    }
  },
  "output_locations": {
    "json": {
      "file_extension": ".json",
      "output_function": "export.to_json",
      "metrics_location": "polaris_metrics"
    },
    "markdown": {
      "file_extension": ".md",
      "output_function": "export.to_markdown",
      "metrics_location": "end_summary_block"
    },
    "docx": {
      "file_extension": ".docx",
      "output_function": "export.to_docx",
      "metrics_location": "end_paragraph"
    },
    "delivery_manifest": {
      "file_name": "delivery_manifest.json",
      "output_function": "__main__.write_delivery_receipt",
      "metrics_location": "polaris_metrics"
    }
  }
}
```

---

## 6. 驗證與測試對應

### 6.1 現有測試覆蓋

- `tests/test_polaris_metrics_e2e.py`: 端到端驗收測試，驗證指標計算正確性
- `tests/test_metrics.py`: 單元測試，驗證各指標計算函數
- `tests/test_binding_report.py`: 驗證 binding_report 欄位完整性
- `tests/test_e2e_acceptance.py`: 端到端驗收，驗證輸出格式正確性

### 6.2 欄位追溯驗證

每個欄位都可透過以下路徑追溯：
1. 原始資料來源 (gap/question/written)
2. 中間資料結構 (Segment/CorrectionDoc)
3. 綁定報告 (binding_report.json)
4. 最終輸出 (json/md/docx + delivery_manifest)

---

## 7. 結論

1. **欄位來源明確**: 所有北極星指標所需的欄位都有明確的資料來源與生成位置
2. **缺值處理完整**: 每個欄位都有定義清晰的缺值處理策略
3. **輸出位置一致**: 北極星指標在所有輸出格式中都有對應位置
4. **機器可讀取**: 提供了 JSON 格式的規格結構，可自動化解析與驗證
5. **測試覆蓋完整**: 現有測試已覆蓋指標計算與輸出格式驗證

此規格可作為北極星品質指標的欄位契約，確保資料流的一致性與可追溯性。
