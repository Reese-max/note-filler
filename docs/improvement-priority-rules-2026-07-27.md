# 依指標排序的改善優先級規則與驗收門檻

日期：2026-07-27
基準 revision：`90229c30`
公式版本：`1.3`

## 概述

本文件建立可追蹤的改善優先級規則，將北極星品質指標轉化為具體、可量測的改善清單。每項改善包含基準值、目標值、負責範圍、影響範圍評估、改善成本評估與驗收查詢方式，確保改善行動與品質指標直接對齊。

透過影響範圍與改善成本的量化評估，結合 ROI 計算，提供系統化的優先級排序機制，並定義機器可讀的待辦清單結構，實現改善項目的自動追蹤與管理。

## 優先級排序規則

### 排序原則

1. **指標影響度優先**：影響整體品質判定（overall_status）最大的指標優先
2. **門檻差距優先**：與合格門檻差距最大的指標優先
3. **關聯性整合**：改善項目間的依賴關係與整合效應
4. **資源效率**：以最小改動獲得最大品質提升
5. **影響範圍評估**：綜合評估改善項目對系統的影響廣度
6. **改善成本評估**：衡量實施改善項目所需的資源投入

### 機器可讀逐筆排序

`metrics_summary_*.json` 的 `improvement_priorities` 只列
`traceability_score.degraded = true` 的筆記，並依下列鍵穩定排序：

1. `score_penalty` 由高至低
2. `overall_score` 由低至高
3. `source_path`、`manifest_path` 字典序

每筆固定輸出 `rank`、來源路徑、目前總分、固定其他分項時回補追溯扣分後的總分、追溯分數、扣分、
`affected_argument_ids`、需修正來源欄位及 `acceptance`。後續修正完成的驗收條件為
`traceability_score = 1.0`、`score_penalty = 0.0` 且受影響論點清單為空；未降分筆記
不得混入排序清單。

### 影響範圍評估框架

#### 評估維度

影響範圍評估包含以下三個維度：

1. **模組影響度**：改善項目涉及的系統模組數量
   - **高影響**：涉及核心處理模組（如 `binding_report`、`metrics`）
   - **中影響**：涉及輔助模組（如 `angle_coverage`、`delivery_manifest`）
   - **低影響**：涉及單一功能或配置

2. **資料影響度**：改善項目對現有資料的影響程度
   - **高影響**：需要修改既有資料結構或遷移歷史資料
   - **中影響**：需要調整資料處理邏輯但不改變結構
   - **低影響**：僅影響新增資料或計算邏輯

3. **使用者影響度**：改善項目對最終使用者的影響範圍
   - **高影響**：影響所有使用者或關鍵使用場景
   - **中影響**：影響部分使用者或特定場景
   - **低影響**：僅影響內部流程或開發者體驗

#### 影響範圍評分標準

| 等級 | 分數 | 說明 |
|------|------|------|
| **高** | 3 | 涉及核心模組、需要資料遷移、影響所有使用者 |
| **中** | 2 | 涉及輔助模組、調整處理邏輯、影響部分使用者 |
| **低** | 1 | 涉及單一功能、僅影響新增資料、影響內部流程 |

#### 總影響範圍計算

```
總影響範圍 = (模組影響度 + 資料影響度 + 使用者影響度) / 3
```

### 改善成本評估框架

#### 評估維度

改善成本評估包含以下四個維度：

1. **開發時間**：實施改善項目所需的開發工時
   - **高成本**：超過 5 個工作日
   - **中成本**：2-5 個工作日
   - **低成本**：少於 2 個工作日

2. **測試成本**：驗證改善項目所需的測試工作
   - **高成本**：需要大量回歸測試或整合測試
   - **中成本**：需要單元測試與部分回歸測試
   - **低成本**：僅需簡單單元測試或驗證

3. **風險程度**：實施改善項目可能帶來的風險
   - **高風險**：可能影響核心功能或資料完整性
   - **中風險**：可能影響次要功能或效能
   - **低風險**：影響範圍有限且易於回滾

4. **依賴複雜度**：改善項目對其他系統或資源的依賴程度
   - **高複雜度**：涉及多個外部依賴或跨團隊協作
   - **中複雜度**：涉及少量外部依賴或單一協作
   - **低複雜度**：可獨立完成，無外部依賴

#### 改善成本評分標準

| 等級 | 分數 | 說明 |
|------|------|------|
| **高** | 3 | 開發時間長、測試成本高、風險高、依賴複雜 |
| **中** | 2 | 開發時間中等、測試成本中等、風險中等、依賴中等 |
| **低** | 1 | 開發時間短、測試成本低、風險低、依賴簡單 |

#### 總改善成本計算

```
總改善成本 = (開發時間 + 測試成本 + 風險程度 + 依賴複雜度) / 4
```

### 綜合優先級評分

#### ROI 計算

為了平衡影響範圍與改善成本，使用 ROI（投資回報率）概念：

```
ROI = (總影響範圍 × 指標權重) / 總改善成本
```

其中指標權重依據指標類型而定：
- P0 指標：權重 3.0
- P1 指標：權重 2.0
- P2 指標：權重 1.0
- P3 指標：權重 0.5

#### 最終排序規則

改善項目依以下順序排序：
1. ROI 由高至低
2. 指標優先級（P0 > P1 > P2 > P3）
3. 門檻差距由大至小
4. 總影響範圍由高至低
5. 總改善成本由低至高

### 優先級等級

| 等級 | 說明 | 處理時程 |
|------|------|---------|
| **P0** | 阻斷性問題，影響所有下游指標 | 立即處理 |
| **P1** | 核心指標未達門檻，影響整體品質判定 | 本週處理 |
| **P2** | 輔助指標未達門檻，影響品質完整性 | 下週處理 |
| **P3** | 優化項目，提升品質上限 | 月度處理 |

---

## 改善清單

### 0. 追溯性總分扣分（P0）

**指標**：`traceability_score`
**目標值**：`1.0`

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 影響範圍 | 改善成本 | 驗收查詢方式 |
|----|---------|--------|--------|---------|---------|---------|-------------|
| TRC-01 | 補齊排序列出的受影響論點 | 報表逐筆值 | `affected_argument_ids = []` | `claim_source_map`、`traceability_markers`、`citation_span_map` | 高 | 中 | `improvement_priorities[].affected_argument_ids` |
| TRC-02 | 消除北極星追溯扣分 | 報表逐筆值 | `score_penalty = 0.0` | `binding_report.arguments[].source_ids/checks` | 高 | 高 | `improvement_priorities` 不再含該筆記 |

#### 驗收標準

- `traceability_score.score = 1.0`
- `traceability_score.penalty = 0.0`
- `traceability_score.degraded = false`
- `traceability_score.affected_argument_ids = []`

### 1. 功能缺口分數改善（P1）

**指標**：`functional_gap_score`
**門檻**：>= 0.70
**基準值**：待量測（首次執行 metrics_pipeline 後取得）
**目標值**：>= 0.70

#### 改善項目

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 影響範圍 | 改善成本 | 驗收查詢方式 |
|----|---------|--------|--------|---------|---------|---------|-------------|
| FGS-01 | 提升可追溯性子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].source_ids` | 高 | 高 | `calculate_functional_gap_score(arguments).subscores["traceability"]["score"]` |
| FGS-02 | 提升覆蓋廣度子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].angle_coverage` | 中 | 中 | `calculate_functional_gap_score(arguments).subscores["coverage_breadth"]["score"]` |
| FGS-03 | 提升必要性明確度子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].functional_gap` | 中 | 低 | `calculate_functional_gap_score(arguments).subscores["necessity_clarity"]["score"]` |
| FGS-04 | 提升決策助益子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].related_knowledge` | 中 | 中 | `calculate_functional_gap_score(arguments).subscores["decision_support"]["score"]` |
| FGS-05 | 消除 missing_data 狀態 | 待量測 | 0 | `binding_report.arguments` 完整性 | 高 | 高 | `calculate_functional_gap_score(arguments).status != "missing_data"` |

#### 驗收標準

- 整體分數 >= 0.70
- 所有四個子分數皆 >= 0.70
- `status = "calculated"`
- `basis_mode = "binding_report"`
- 無論點缺少必要欄位

---

### 2. 使用者價值分數改善（P1）

**指標**：`user_value_score`
**門檻**：>= 0.70
**基準值**：待量測
**目標值**：>= 0.70

#### 改善項目

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 影響範圍 | 改善成本 | 驗收查詢方式 |
|----|---------|--------|--------|---------|---------|---------|-------------|
| UVS-01 | 提升可追溯性子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].source_ids` | 高 | 高 | `calculate_user_value_score(arguments).subscores["traceability"]["score"]` |
| UVS-02 | 提升覆蓋廣度子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].angle_coverage` | 中 | 中 | `calculate_user_value_score(arguments).subscores["coverage_breadth"]["score"]` |
| UVS-03 | 提升必要性明確度子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].user_value` | 中 | 低 | `calculate_user_value_score(arguments).subscores["necessity_clarity"]["score"]` |
| UVS-04 | 提升決策助益子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].related_knowledge` | 中 | 中 | `calculate_user_value_score(arguments).subscores["decision_support"]["score"]` |
| UVS-05 | 消除 missing_data 狀態 | 待量測 | 0 | `binding_report.arguments` 完整性 | 高 | 高 | `calculate_user_value_score(arguments).status != "missing_data"` |

#### 驗收標準

- 整體分數 >= 0.70
- 所有四個子分數皆 >= 0.70
- `status = "calculated"`
- `basis_mode = "binding_report"`
- 無論點缺少必要欄位

---

### 3. 來源綁定完整性改善（P1）

**指標**：`source_binding_integrity`
**門檻**：>= 0.80
**基準值**：待量測
**目標值**：>= 0.80

#### 改善項目

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 影響範圍 | 改善成本 | 驗收查詢方式 |
|----|---------|--------|--------|---------|---------|---------|-------------|
| SBI-01 | 提升 pass 論點比例 | 待量測 | >= 0.80 | `binding_report.arguments[].binding_status` | 高 | 高 | `calculate_source_binding_integrity(arguments).score` |
| SBI-02 | 消除 missing_data 狀態 | 待量測 | 0 | `binding_report.arguments` 完整性 | 高 | 高 | `calculate_source_binding_integrity(arguments).status != "missing_data"` |
| SBI-03 | 減少 fail 論點數 | 待量測 | <= 0.20 | `binding_report.arguments[].checks` | 中 | 中 | `calculate_source_binding_integrity(arguments).arguments_fail / total_arguments` |
| SBI-04 | 減少 pending_evidence 論點數 | 待量測 | <= 0.10 | 來源檢索流程 | 中 | 中 | `calculate_source_binding_integrity(arguments).arguments_pending / total_arguments` |

#### 驗收標準

- 整體分數 >= 0.80
- `status = "calculated"`
- `arguments_fail / total_arguments <= 0.20`
- `arguments_pending / total_arguments <= 0.10`

---

### 4. 角度多樣性指數改善（P2）

**指標**：`angle_diversity_index`
**門檻**：>= 0.60
**基準值**：待量測
**目標值**：>= 0.60

#### 改善項目

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 影響範圍 | 改善成本 | 驗收查詢方式 |
|----|---------|--------|--------|---------|---------|---------|-------------|
| ADI-01 | 提升唯一角度類型數 | 待量測 | >= 5 | `binding_report.angle_coverage_summary.unique_angle_types` | 中 | 中 | `calculate_angle_diversity_index(summary).unique_angle_types` |
| ADI-02 | 消除 missing_data 狀態 | 待量測 | 0 | `binding_report.angle_coverage_summary` 完整性 | 中 | 中 | `calculate_angle_diversity_index(summary).status != "missing_data"` |
| ADI-03 | 降低重複比率 | 待量測 | <= 0.30 | `binding_report.angle_coverage_summary.duplicate_ratio` | 低 | 低 | `calculate_angle_diversity_index(summary).duplicate_ratio` |
| ADI-04 | 提升有效角度數 | 待量測 | >= 4 | `binding_report.angle_coverage_summary.effective_angle_count` | 中 | 中 | `calculate_angle_diversity_index(summary).effective_angle_count` |

#### 驗收標準

- 整體分數 >= 0.60（即唯一角度類型數 >= 5）
- `status = "calculated"`
- `duplicate_ratio <= 0.30`
- `effective_angle_count >= 4`

---

### 5. 端到端送達成功率改善（P2）

**指標**：`delivery_success_rate`
**門檻**：>= 0.90
**基準值**：待量測
**目標值**：>= 0.90

#### 改善項目

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 影響範圍 | 改善成本 | 驗收查詢方式 |
|----|---------|--------|--------|---------|---------|---------|-------------|
| DSR-01 | 提升成功送達比例 | 待量測 | >= 0.90 | `delivery_manifest.delivery_status` | 高 | 高 | `calculate_delivery_success_rate(status).score` |
| DSR-02 | 消除 missing_data 狀態 | 待量測 | 0 | `delivery_manifest` 完整性 | 高 | 高 | `calculate_delivery_success_rate(status).status != "missing_data"` |
| DSR-03 | 確保 primary_note_ready | 待量測 | 100% | `delivery_manifest.delivery_status.primary_note_ready` | 高 | 中 | `delivery_status["primary_note_ready"] is True` |
| DSR-04 | 確保 user_channel_sent | 待量測 | 100% | `delivery_manifest.delivery_status.user_channel_sent` | 高 | 中 | `delivery_status["user_channel_sent"] is True` |
| DSR-05 | 確保 local_fallback_written | 待量測 | 100% | `delivery_manifest.delivery_status.local_fallback_written` | 中 | 低 | `delivery_status["local_fallback_written"] is True` |

#### 驗收標準

- 整體分數 >= 0.90
- `status = "calculated"`
- 所有三個布林欄位皆為 True

---

## 整體品質改善目標

### 目標等級

| 當前狀態 | 目標狀態 | 改善策略 |
|---------|---------|---------|
| poor | acceptable | 優先改善 P0/P1 指標，確保至少 2 項通過門檻 |
| acceptable | good | 繼續改善 P1/P2 指標，確保至少 3 項通過門檻 |
| good | excellent | 全面改善所有指標，確保全部 5 項通過門檻 |

### 整體驗收查詢

```python
# 從 delivery_manifest 取得指標
metrics = manifest["polaris_metrics"]

# 驗收條件
assert metrics["overall_status"] in ("excellent", "good")
assert metrics["core_metrics_pass_count"] >= 3
assert metrics["functional_gap_score"]["passes_threshold"] is True
assert metrics["user_value_score"]["passes_threshold"] is True
assert metrics["source_binding_integrity"]["passes_threshold"] is True
assert metrics["angle_diversity_index"]["passes_threshold"] is True
assert metrics["delivery_success_rate"]["passes_threshold"] is True
```

---

## 改善追蹤機制

### 追蹤頻率

| 指標類型 | 追蹤頻率 | 追蹤方式 |
|---------|---------|---------|
| P0 阻斷性 | 每次變更後 | 自動化測試 + 手動驗證 |
| P1 核心指標 | 每日 | metrics_pipeline 自動蒐集 |
| P2 輔助指標 | 每週 | metrics_pipeline 彙總報告 |
| P3 優化項目 | 每月 | 品質趨勢分析 |

### 追蹤報告

```bash
# 蒐集最新指標
python scripts/run_metrics_pipeline.py collect

# 查詢最新結果
python scripts/run_metrics_pipeline.py latest

# 查詢歷史趨勢
python scripts/run_metrics_pipeline.py query --metric functional_gap_score
```

### 驗證腳本

```python
# 單一筆記驗證
from note_filler.metrics import calculate_polaris_metrics

metrics = calculate_polaris_metrics(binding_report, delivery_status)
print(f"整體品質: {metrics.overall_status}")
print(f"通過門檻: {metrics.core_metrics_pass_count}/5")

# 批次驗證
# 使用 metrics_pipeline 收集多筆記錄並分析趨勢
```

---

## 與現有系統的整合

### 與 binding_report 的整合

改善項目直接對應 `binding_report` 的 18 項 checks：

| 改善項目 | 對應 checks |
|---------|------------|
| FGS-01 / UVS-01 / SBI-01 | `at_least_one_source`, `source_traceable`, `no_omitted_traces`, `no_extra_traces` |
| FGS-02 / UVS-02 / ADI-01 | `has_angle_coverage`, `meets_angle_coverage_threshold`, `angle_facet_complete` |
| FGS-03 / UVS-03 | `has_functional_gap`, `has_user_value` |
| FGS-04 / UVS-04 | `has_related_knowledge`, `related_knowledge_consistent` |

### 與 angle_coverage 的整合

角度多樣性指數直接使用 `angle_coverage` 模組的分類結果：

- 8 種角度類型：definition, limitation, requirement, effect, procedure, exception, comparison, application
- 同義判定：token Jaccard >= 0.5
- 重複比率：`MAX_DUPLICATE_RATIO = 0.5`

### 與 delivery_manifest 的整合

送達成功率直接使用 `delivery_manifest` 的送達狀態：

- `primary_note_ready`：主筆記是否就緒
- `user_channel_sent`：是否已傳送至使用者頻道
- `local_fallback_written`：是否已寫入本地備份

---

## 可追蹤的待辦清單結構

### 機器可讀清單格式

為了讓改善項目能被系統自動追蹤與排序，定義以下機器可讀的 JSON 結構：

```json
{
  "improvement_items": [
    {
      "id": "TRC-01",
      "title": "補齊排序列出的受影響論點",
      "priority_level": "P0",
      "metric_name": "traceability_score",
      "baseline_value": 0.85,
      "target_value": 1.0,
      "current_value": 0.85,
      "responsible_scope": ["claim_source_map", "traceability_markers", "citation_span_map"],
      "impact_assessment": {
        "module_impact": "高",
        "data_impact": "高",
        "user_impact": "高",
        "total_impact_score": 3.0,
        "impact_score": 3.0
      },
      "cost_assessment": {
        "dev_time": "中",
        "test_cost": "中",
        "risk_level": "中",
        "dependency_complexity": "低",
        "total_cost_score": 2.0,
        "cost_score": 2.0
      },
      "roi_score": 4.5,
      "gap_to_threshold": 0.15,
      "acceptance_query": "improvement_priorities[].affected_argument_ids",
      "status": "pending",
      "assigned_to": null,
      "created_at": "2026-07-27T00:00:00Z",
      "updated_at": "2026-07-27T00:00:00Z",
      "completed_at": null,
      "notes": []
    }
  ],
  "summary": {
    "total_items": 20,
    "by_priority": {
      "P0": 2,
      "P1": 8,
      "P2": 6,
      "P3": 4
    },
    "by_status": {
      "pending": 15,
      "in_progress": 3,
      "completed": 2,
      "blocked": 0
    },
    "by_metric": {
      "traceability_score": 2,
      "functional_gap_score": 5,
      "user_value_score": 5,
      "source_binding_integrity": 4,
      "angle_diversity_index": 2,
      "delivery_success_rate": 2
    }
  },
  "generated_at": "2026-07-27T00:00:00Z",
  "formula_version": "1.2"
}
```

### 欄位說明

#### 改善項目欄位

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `id` | string | 是 | 改善項目唯一識別碼（如 TRC-01） |
| `title` | string | 是 | 改善項目標題 |
| `priority_level` | string | 是 | 優先級等級（P0/P1/P2/P3） |
| `metric_name` | string | 是 | 對應的指標名稱 |
| `baseline_value` | float | 是 | 基準值 |
| `target_value` | float | 是 | 目標值 |
| `current_value` | float | 否 | 當前值（可從 metrics_pipeline 取得） |
| `responsible_scope` | list[string] | 是 | 負責範圍（涉及的模組或欄位） |
| `impact_assessment` | object | 是 | 影響範圍評估 |
| `cost_assessment` | object | 是 | 改善成本評估 |
| `roi_score` | float | 是 | 投資回報率分數 |
| `gap_to_threshold` | float | 是 | 與門檻的差距 |
| `acceptance_query` | string | 是 | 驗收查詢方式 |
| `status` | string | 是 | 狀態（pending/in_progress/completed/blocked） |
| `assigned_to` | string | 否 | 負責人 |
| `created_at` | string | 是 | 建立時間（ISO 8601） |
| `updated_at` | string | 是 | 更新時間（ISO 8601） |
| `completed_at` | string | 否 | 完成時間（ISO 8601） |
| `notes` | list[string] | 否 | 備註事項 |

#### 影響範圍評估欄位

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `module_impact` | string | 是 | 模組影響度（高/中/低） |
| `data_impact` | string | 是 | 資料影響度（高/中/低） |
| `user_impact` | string | 是 | 使用者影響度（高/中/低） |
| `total_impact_score` | float | 是 | 總影響範圍分數（1-3） |
| `impact_score` | float | 是 | 影響範圍數值（高=3, 中=2, 低=1） |

#### 改善成本評估欄位

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `dev_time` | string | 是 | 開發時間（高/中/低） |
| `test_cost` | string | 是 | 測試成本（高/中/低） |
| `risk_level` | string | 是 | 風險程度（高/中/低） |
| `dependency_complexity` | string | 是 | 依賴複雜度（高/中/低） |
| `total_cost_score` | float | 是 | 總改善成本分數（1-3） |
| `cost_score` | float | 是 | 改善成本數值（高=3, 中=2, 低=1） |

### 狀態轉換規則

```
pending → in_progress → completed
  ↓         ↓
blocked  blocked
```

- **pending**：待處理，尚未開始
- **in_progress**：進行中，正在實施
- **completed**：已完成，通過驗收
- **blocked**：已阻塞，等待依賴或外部資源

### 自動排序邏輯

系統應依以下規則自動排序改善項目：

1. **ROI 分數降序**：roi_score 由高至低
2. **優先級等級**：P0 > P1 > P2 > P3
3. **門檻差距降序**：gap_to_threshold 由大至小
4. **影響範圍降序**：total_impact_score 由高至低
5. **改善成本升序**：total_cost_score 由低至高

### 待辦清單生成範例

```python
from note_filler.improvement_tracker import generate_improvement_todo_list

# 從 metrics_summary 生成待辦清單
metrics_summary = load_metrics_summary("output/metrics_summary_latest.json")
todo_list = generate_improvement_todo_list(metrics_summary)

# 依優先級排序
sorted_items = sort_improvement_items(todo_list["improvement_items"])

# 輸出為 JSON
import json
with open("output/improvement_todo_list.json", "w", encoding="utf-8") as f:
    json.dump(todo_list, f, indent=2, ensure_ascii=False)
```

### 追蹤報告範例

```json
{
  "tracking_report": {
    "period": "2026-07-20 to 2026-07-27",
    "completed_items": 3,
    "in_progress_items": 2,
    "blocked_items": 0,
    "new_items": 1,
    "metrics_improvement": {
      "traceability_score": {
        "before": 0.85,
        "after": 0.92,
        "improvement": 0.07
      },
      "functional_gap_score": {
        "before": 0.65,
        "after": 0.72,
        "improvement": 0.07
      }
    },
    "roi_summary": {
      "total_invested_cost": 8.0,
      "total_impact_achieved": 12.0,
      "overall_roi": 1.5
    }
  }
}
```

---

## 相關文件

- [北極星筆記品質指標規格](./polaris-metrics-specification-2026-07-27.md)
- [筆記輸出資料流欄位盤點與北極星指標支援分析](./note-output-dataflow-metrics-inventory-2026-07-27.md)
- [binding_report 結構說明](../src/note_filler/binding_report.py)
- [angle_coverage 詳細說明](../src/note_filler/angle_coverage.py)
- [metrics_pipeline 操作指南](../scripts/run_metrics_pipeline.py)

---

## 變更紀錄

- 2026-07-27：新增影響範圍評估框架與改善成本評估框架，整合為綜合優先級評分系統
- 2026-07-27：新增可追蹤的待辦清單結構，包含機器可讀 JSON 格式與自動排序邏輯
- 2026-07-27：初始版本，建立依指標排序的改善優先級規則與驗收門檻
