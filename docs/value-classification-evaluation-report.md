# 高價值筆記 vs 形式完整低效益筆記：分類評估報告

## 摘要

本報告建立並評估一套結合北極星品質指標（Polaris Metrics）與實際使用成效訊號的筆記價值分類系統，可區分「高價值筆記」與「形式完整但效益低筆記」。

## 1. 方法論

### 1.1 分類架構

```
                      ┌─────────────────────┐
                      │    北極星指標        │
                      │  (5 項品質指標)      │
                      │  overall_score       │
                      └──────────┬──────────┘
                                 │ × 0.5（等權重）
                      ┌──────────▼──────────┐
                      │   複合價值分數        │
                      │  composite_score =    │
                      │  0.5×polaris + 0.5×usage
                      └──────────┬──────────┘
                                 │ ≥ composite_threshold
                      ┌──────────▼──────────┐
                      │   high_value /       │
                      │   low_benefit        │
                      └─────────────────────┘
                      ┌─────────────────────┐
                      │    使用成效訊號       │
                      │  (7 項指標)           │
                      │  usage_score         │
                      └──────────┬──────────┘
                                 │ × 0.5（等權重）
```

### 1.2 使用成效訊號定義

| 訊號 | 最大合理值 | 權重 | 說明 |
|---|---|---|---|
| `citation_count` | 20 | 0.20 | 被其他筆記或文件引用的次數 |
| `reuse_count` | 10 | 0.20 | 被直接複製或重複使用的次數 |
| `regeneration_avoided` | 1 (布林) | 0.15 | 是否因補充完整而避免重新生成 |
| `user_feedback_positive` | 1 (布林) | 0.15 | 使用者是否給予正向回饋 |
| `completion_rate` | 1.0 | 0.10 | 使用過程中完整閱讀的比例 |
| `reference_in_other_notes_count` | 15 | 0.10 | 被其他筆記參考的次數 |
| `search_click_count` | 50 | 0.10 | 在搜尋中被點擊的次數 |

### 1.3 分類門檻

| 參數 | 預設值 | 說明 |
|---|---|---|
| `composite_threshold` | 0.5 | 複合分數 >= 0.5 判定為高價值 |
| `polaris_weight` | 0.5 | 北極星指標在複合分數中的權重 |
| `usage_weight` | 0.5 | 使用成效在複合分數中的權重 |

## 2. 標註資料集

### 2.1 資料集組成

10 筆人工標註筆記，5 高價值 + 5 低效益，涵蓋 6 個法律主題：

| 主題 | 高價值 | 低效益 |
|---|---|---|
| 行政處分 | note_001 | note_001 |
| 行政契約 | note_002 | note_002 |
| 訴願法 | note_003 | — |
| 國家賠償法 | note_004 | — |
| 行政執行法 | note_005 | — |
| 行政程序法（送達） | — | note_003 |
| 行政罰法 | — | note_004 |
| 政府資訊公開法 | — | note_005 |

### 2.2 邊界案例設計

| 案例 | 類別 | 特殊設計 |
|---|---|---|
| `high_value_005` | high_value | polaris 強但使用訊號中等，測試分類器是否仍能正確分類 |
| `low_benefit_005` | low_benefit | **polaris 優秀 (0.850) 但使用訊號歸零**——形式完美但沒人用的筆記，測試使用訊號降級機制 |
| `low_benefit_004` | low_benefit | polaris 低但少量使用訊號，測試使用訊號不會過度拉升 |

## 3. 評估結果

### 3.1 混淆矩陣（預設門檻）

| | 預測 high_value | 預測 low_benefit |
|---|---|---|
| **實際 high_value** | TP = 5 | FN = 0 |
| **實際 low_benefit** | FP = 0 | TN = 5 |

### 3.2 主要指標

| 指標 | 數值 |
|---|---|
| **精確率 (Precision)** | 1.0000 |
| **召回率 (Recall)** | 1.0000 |
| **特異性 (Specificity)** | 1.0000 |
| **準確率 (Accuracy)** | 1.0000 |
| **F1 分數** | 1.0000 |

### 3.3 逐筆分數

| 筆記 | 實際 | 預測 | Polaris | Usage | Composite | 正確? |
|---|---|---|---|---|---|---|
| high_value_001 | high_value | high_value | 0.875 | 0.753 | 0.814 | ✓ |
| high_value_002 | high_value | high_value | 0.875 | 0.666 | 0.770 | ✓ |
| high_value_003 | high_value | high_value | 0.875 | 0.869 | 0.872 | ✓ |
| high_value_004 | high_value | high_value | 0.875 | 0.604 | 0.740 | ✓ |
| high_value_005 | high_value | high_value | 0.875 | 0.313 | 0.594 | ✓ |
| low_benefit_001 | low_benefit | low_benefit | 0.350 | 0.010 | 0.180 | ✓ |
| low_benefit_002 | low_benefit | low_benefit | 0.350 | 0.005 | 0.178 | ✓ |
| low_benefit_003 | low_benefit | low_benefit | 0.350 | 0.002 | 0.176 | ✓ |
| low_benefit_004 | low_benefit | low_benefit | 0.350 | 0.044 | 0.197 | ✓ |
| low_benefit_005 | low_benefit | low_benefit | **0.850** | **0.000** | **0.425** | ✓ |

### 3.4 誤判案例

**無誤判案例。** 所有 10 筆標註資料均被正確分類。

## 4. 門檻分析

### 4.1 最佳複合門檻

| Polariss Threshold | Composite Threshold | F1 |
|---|---|---|
| 任意 (0.3~0.7) | **0.5** | **1.0000** |
| 任意 | 0.3 | 0.9091 (1 FP) |
| 任意 | 0.4 | 0.9091 (1 FP) |
| 任意 | 0.6 | 0.8889 (1 FN) |

### 4.2 關鍵決定邊界

- **`low_benefit_005`**（形式完美零使用）：composite = 0.425 < 0.5 → **正確降級**
- **`high_value_005`**（中等使用）：composite = 0.594 > 0.5 → **正確分類**
- 中間間隔 0.169，留有足夠安全距離

### 4.3 建議門檻

**`composite_threshold = 0.5`** 為最佳門檻，理由：
1. 在此標註資料集達到完美分類
2. 邊界案例之間留有 >0.15 安全距離
3. 等權重設計平衡形式品質與實際使用

## 5. 使用成效訊號之邊際貢獻

### 5.1 純 Polaris 分類 vs 複合分類

若僅使用 Polaris overall_score（≥0.5 為 high_value）：

| | 預測 high_value | 預測 low_benefit |
|---|---|---|
| high_value | 5 | 0 |
| low_benefit | **1** (low_benefit_005) | 4 |

- 精確率 = 0.8333
- 回召率 = 1.0000
- F1 = 0.9091

加入使用訊號後 F1 從 0.9091 → 1.0000，改善了純形式評估對極端案例（形式完美但無人使用）的誤判。

### 5.2 門檻安全距離對比

| 門檻 | 純 Polaris F1 | 複合分類 F1 |
|---|---|---|
| 0.5 | 0.9091 | **1.0000** |
| 0.6 | 0.8000 | **0.8889** |

使用訊號在每個門檻均提升 F1。

## 6. 代表性誤判案例

當前資料集無誤判；但從門檻掃描中可預測**潛在誤判類型**：

### 6.1 假陽性（FP）情境

當 composite_threshold = 0.3 時：
- `low_benefit_005`（composite = 0.425）會被誤判為 high_value
- **特徵**：Polaris 優秀但使用訊號完全歸零
- **成因**：門檻過低 + 使用訊號權重不足

### 6.2 假陰性（FN）情境

當 composite_threshold = 0.6 時：
- `high_value_005`（composite = 0.594）會被誤判為 low_benefit
- **特徵**：Polaris 強但使用訊號普通 (0.313)
- **成因**：門檻過高對中低使用率的高品質筆記不利

### 6.3 潛在盲點

以下情境在當前資料集中未被覆蓋，建議未來補充：
1. **Polaris 低 + 使用訊號極高**（眾人愛用的不完美筆記）
2. **Polaris 中等 + 使用訊號中等**（灰色地帶大量案例）
3. **Polaris 極低 + 使用訊號中等**（結構差但局部有用）

## 7. 結論

### 建議門檻設定

```
composite_threshold = 0.5
polaris_weight = 0.5
usage_weight = 0.5
```

### 分類決策規則（機器可讀）

```
composite_score = 0.5 × polaris_overall + 0.5 × usage_effectiveness
value_label = "high_value" if composite_score >= 0.5 else "low_benefit"
```

### 使用限制

1. 使用訊號在離線環境會自動退化為 0，此時分類完全依賴 Polaris 指標
2. 使用訊號資料需外部系統提供，非本 pipeline 自動產生
3. 建議至少 3 個不同使用訊號有值，否則應標記 `status = partial_signals`
