# 北極星筆記品質指標規格

日期：2026-07-27
基準 revision：`90229c30`
Schema 版本：`note_filler.polaris_metrics.v1`

## 概述

本規格定義可機器讀取的北極星筆記品質指標，包含「功能缺口分數」與「使用者價值分數」等核心指標的明確公式、判定規則、資料來源與缺值處理方式。每則筆記可被一致計分與追蹤，並產出可序列化的指標物件與報告欄位。

## 核心指標

### 1. 功能缺口分數（Functional Gap Score）

#### 計算公式
```
功能缺口分數 = (具體描述的功能缺口數) / (總論點數)
```

#### 判定規則
- **具體描述定義**：`functional_gap` 欄位非空且長度 >= 10 字元
- **分數範圍**：0.0 ~ 1.0
- **合格門檻**：>= 0.7 (70%)
- **狀態**：`calculated`（成功計算）、`missing_data`（資料不足）、`error`（計算錯誤）

#### 資料來源
- `binding_report.arguments[].functional_gap`
- `binding_report.arguments[].binding_status`

#### 缺值處理
- `functional_gap` 為空字串：視為無具體描述，不計入分子
- 論點無 `functional_gap` 欄位：視為缺值，`status = missing_data`
- 總論點數為 0：`status = missing_data`

#### 詳細統計欄位
```python
{
    "score": float,              # 0.0 ~ 1.0
    "status": "calculated" | "missing_data" | "error",
    "threshold": 0.7,
    "passes_threshold": bool,
    "total_arguments": int,      # 總論點數
    "arguments_with_concrete_gap": int,   # 具體描述的功能缺口數
    "arguments_with_empty_gap": int,       # 空功能缺口數
    "arguments_missing_field": int,       # 缺失欄位的論點數
}
```

---

### 2. 使用者價值分數（User Value Score）

#### 計算公式
```
使用者價值分數 = (明確使用者價值的論點數) / (總論點數)
```

#### 判定規則
- **明確使用者價值定義**：`user_value` 欄位非空且包含關鍵詞「讀者」、「說明」、「理解」
- **分數範圍**：0.0 ~ 1.0
- **合格門檻**：>= 0.7 (70%)
- **狀態**：`calculated`、`missing_data`、`error`

#### 資料來源
- `binding_report.arguments[].user_value`
- `binding_report.arguments[].binding_status`

#### 缺值處理
- `user_value` 為空字串：視為無明確價值，不計入分子
- 論點無 `user_value` 欄位：視為缺值，`status = missing_data`
- 總論點數為 0：`status = missing_data`

#### 詳細統計欄位
```python
{
    "score": float,
    "status": "calculated" | "missing_data" | "error",
    "threshold": 0.7,
    "passes_threshold": bool,
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

### PolarisMetrics 總覽

#### 整體品質判定規則
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
    "overall_status": "excellent" | "good" | "acceptable" | "poor" | "error",
    "core_metrics_pass_count": int,      # 通過門檻的核心指標數
    "core_metrics_total_count": int,     # 核心指標總數（固定 5）
    "calculated_at": str,                # ISO 8601 UTC 時間戳
    "functional_gap_score": { ... },     # 功能缺口分數詳情
    "user_value_score": { ... },          # 使用者價值分數詳情
    "source_binding_integrity": { ... },  # 來源綁定完整性詳情
    "angle_diversity_index": { ... },     # 角度多樣性指數詳情
    "delivery_success_rate": { ... },    # 端到端送達成功率詳情
}
```

---

## 資料流整合

### 輸出位置

北極星指標會自動整合到以下輸出：

1. **delivery_manifest.json**
   - 頂層欄位：`polaris_metrics`
   - 每次成功送達時自動計算並寫入

2. **binding_report.json**
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
- 2026-07-27：初始版本，定義 5 個核心指標與整體評估機制
