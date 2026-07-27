# 依指標排序的改善優先級規則與驗收門檻

日期：2026-07-27
基準 revision：`90229c30`
公式版本：`1.1`

## 概述

本文件建立可追蹤的改善優先級規則，將北極星品質指標轉化為具體、可量測的改善清單。每項改善包含基準值、目標值、負責範圍與驗收查詢方式，確保改善行動與品質指標直接對齊。

## 優先級排序規則

### 排序原則

1. **指標影響度優先**：影響整體品質判定（overall_status）最大的指標優先
2. **門檻差距優先**：與合格門檻差距最大的指標優先
3. **關聯性整合**：改善項目間的依賴關係與整合效應
4. **資源效率**：以最小改動獲得最大品質提升

### 優先級等級

| 等級 | 說明 | 處理時程 |
|------|------|---------|
| **P0** | 阻斷性問題，影響所有下游指標 | 立即處理 |
| **P1** | 核心指標未達門檻，影響整體品質判定 | 本週處理 |
| **P2** | 輔助指標未達門檻，影響品質完整性 | 下週處理 |
| **P3** | 優化項目，提升品質上限 | 月度處理 |

---

## 改善清單

### 1. 功能缺口分數改善（P1）

**指標**：`functional_gap_score`
**門檻**：>= 0.70
**基準值**：待量測（首次執行 metrics_pipeline 後取得）
**目標值**：>= 0.70

#### 改善項目

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 驗收查詢方式 |
|----|---------|--------|--------|---------|-------------|
| FGS-01 | 提升可追溯性子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].source_ids` | `calculate_functional_gap_score(arguments).subscores["traceability"]["score"]` |
| FGS-02 | 提升覆蓋廣度子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].angle_coverage` | `calculate_functional_gap_score(arguments).subscores["coverage_breadth"]["score"]` |
| FGS-03 | 提升必要性明確度子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].functional_gap` | `calculate_functional_gap_score(arguments).subscores["necessity_clarity"]["score"]` |
| FGS-04 | 提升決策助益子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].related_knowledge` | `calculate_functional_gap_score(arguments).subscores["decision_support"]["score"]` |
| FGS-05 | 消除 missing_data 狀態 | 待量測 | 0 | `binding_report.arguments` 完整性 | `calculate_functional_gap_score(arguments).status != "missing_data"` |

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

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 驗收查詢方式 |
|----|---------|--------|--------|---------|-------------|
| UVS-01 | 提升可追溯性子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].source_ids` | `calculate_user_value_score(arguments).subscores["traceability"]["score"]` |
| UVS-02 | 提升覆蓋廣度子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].angle_coverage` | `calculate_user_value_score(arguments).subscores["coverage_breadth"]["score"]` |
| UVS-03 | 提升必要性明確度子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].user_value` | `calculate_user_value_score(arguments).subscores["necessity_clarity"]["score"]` |
| UVS-04 | 提升決策助益子分數 | 待量測 | >= 0.70 | `binding_report.arguments[].related_knowledge` | `calculate_user_value_score(arguments).subscores["decision_support"]["score"]` |
| UVS-05 | 消除 missing_data 狀態 | 待量測 | 0 | `binding_report.arguments` 完整性 | `calculate_user_value_score(arguments).status != "missing_data"` |

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

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 驗收查詢方式 |
|----|---------|--------|--------|---------|-------------|
| SBI-01 | 提升 pass 論點比例 | 待量測 | >= 0.80 | `binding_report.arguments[].binding_status` | `calculate_source_binding_integrity(arguments).score` |
| SBI-02 | 消除 missing_data 狀態 | 待量測 | 0 | `binding_report.arguments` 完整性 | `calculate_source_binding_integrity(arguments).status != "missing_data"` |
| SBI-03 | 減少 fail 論點數 | 待量測 | <= 0.20 | `binding_report.arguments[].checks` | `calculate_source_binding_integrity(arguments).arguments_fail / total_arguments` |
| SBI-04 | 減少 pending_evidence 論點數 | 待量測 | <= 0.10 | 來源檢索流程 | `calculate_source_binding_integrity(arguments).arguments_pending / total_arguments` |

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

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 驗收查詢方式 |
|----|---------|--------|--------|---------|-------------|
| ADI-01 | 提升唯一角度類型數 | 待量測 | >= 5 | `binding_report.angle_coverage_summary.unique_angle_types` | `calculate_angle_diversity_index(summary).unique_angle_types` |
| ADI-02 | 消除 missing_data 狀態 | 待量測 | 0 | `binding_report.angle_coverage_summary` 完整性 | `calculate_angle_diversity_index(summary).status != "missing_data"` |
| ADI-03 | 降低重複比率 | 待量測 | <= 0.30 | `binding_report.angle_coverage_summary.duplicate_ratio` | `calculate_angle_diversity_index(summary).duplicate_ratio` |
| ADI-04 | 提升有效角度數 | 待量測 | >= 4 | `binding_report.angle_coverage_summary.effective_angle_count` | `calculate_angle_diversity_index(summary).effective_angle_count` |

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

| ID | 改善項目 | 基準值 | 目標值 | 負責範圍 | 驗收查詢方式 |
|----|---------|--------|--------|---------|-------------|
| DSR-01 | 提升成功送達比例 | 待量測 | >= 0.90 | `delivery_manifest.delivery_status` | `calculate_delivery_success_rate(status).score` |
| DSR-02 | 消除 missing_data 狀態 | 待量測 | 0 | `delivery_manifest` 完整性 | `calculate_delivery_success_rate(status).status != "missing_data"` |
| DSR-03 | 確保 primary_note_ready | 待量測 | 100% | `delivery_manifest.delivery_status.primary_note_ready` | `delivery_status["primary_note_ready"] is True` |
| DSR-04 | 確保 user_channel_sent | 待量測 | 100% | `delivery_manifest.delivery_status.user_channel_sent` | `delivery_status["user_channel_sent"] is True` |
| DSR-05 | 確保 local_fallback_written | 待量測 | 100% | `delivery_manifest.delivery_status.local_fallback_written` | `delivery_status["local_fallback_written"] is True` |

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

## 相關文件

- [北極星筆記品質指標規格](./polaris-metrics-specification-2026-07-27.md)
- [筆記輸出資料流欄位盤點與北極星指標支援分析](./note-output-dataflow-metrics-inventory-2026-07-27.md)
- [binding_report 結構說明](../src/note_filler/binding_report.py)
- [angle_coverage 詳細說明](../src/note_filler/angle_coverage.py)
- [metrics_pipeline 操作指南](../scripts/run_metrics_pipeline.py)

---

## 變更紀錄

- 2026-07-27：初始版本，建立依指標排序的改善優先級規則與驗收門檻
