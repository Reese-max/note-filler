# 北極星品質指標人工標註準則

日期：2026-07-27
機器可讀契約：`tests/fixtures/polaris_annotation/acceptance_contract.json`

## 目的與邊界

本資料集是固定的離線回歸驗收集，用來驗證指標能否區分「高價值筆記」與「形式完整但效益低筆記」。所有案例都必須先依本準則完成人工標註，再執行指標，禁止以模型分數反推標籤。

目前共 10 筆合成案例，每類各 5 筆。這能證明既定案例的回歸區分能力，不代表真實使用者母體的泛化成效；來源鍵也只驗證綁定語義，正式法條引用仍須通過既有離線查核。

## 共通形式完整性

兩類筆記都必須具備以下非空欄位，避免用「缺欄位」假裝低效益：

- 筆記層：`note_id`、`category`、`ground_truth`、`topic`、`original_note`、`arguments`、`usage_signals`、`annotation_metadata`。
- 論點層：`argument_text`、`functional_gap`、`user_value`、`related_knowledge`、`sources`、`binding_status`、`cardinality`、`angle_coverage`、`checks`。
- `annotation_metadata.annotator` 必須為 `human`，`validation_status` 必須為 `validated`。
- 無來源的論點必須是 `pending_evidence`；`binding_status = pass` 時必須有來源且 `source_traceable = true`。

## 價值標註準則

### 高價值筆記（`high_value`）

每個論點都必須同時符合：

- 功能缺口具體：`functional_gap` 至少 10 字元，明確指出缺漏資訊。
- 使用者助益明確：`user_value` 至少包含「讀者」、「說明」或「理解」之一，且描述可理解或可決策的助益。
- 來源可追溯：至少一個實際使用的來源鍵、`binding_status = pass`、`source_traceable = true`。
- 使用成效不只靠單一訊號：七項 `usage_signals` 中至少四項為正值。

### 形式完整但效益低筆記（`low_benefit`）

形式欄位仍須齊全，但必須符合：

- 七項 `usage_signals` 中至多三項為正值；且
- 實質內容或來源追溯未達高價值準則，或全部使用成效訊號為零。

這個「或」刻意保留兩種負例：

- `low_benefit_001` 至 `004`：欄位都有值，但描述空泛、來源缺失或追溯失敗。
- `low_benefit_005`：內容與來源形式分數高，但使用訊號全為零，避免純 Polaris 形式分數被誤當成實際價值。

## 固定資料清單與覆蓋

| 類別 | 必須存在的 note_id |
|---|---|
| 高價值 | `high_value_001`、`high_value_002`、`high_value_003`、`high_value_004`、`high_value_005` |
| 低效益 | `low_benefit_001`、`low_benefit_002`、`low_benefit_003`、`low_benefit_004`、`low_benefit_005` |

資料集必須恰好符合契約清單，不得重複、遺漏或放入錯誤類別目錄，且整體需覆蓋 `none`、`one_to_one`、`one_to_many` 三種來源綁定基數。

## 指標與決策規則

### Polaris 單項既有門檻

| 指標 | 通過門檻 |
|---|---:|
| 功能缺口分數 | 0.70 |
| 使用者價值分數 | 0.70 |
| 來源綁定完整性 | 0.80 |
| 角度多樣性 | 0.60 |
| 送達成功率 | 0.90 |

不可量測或部分可量測資料維持既有 fail-closed 規則：`status != calculated` 時不得通過門檻。

### 分類決策

```text
Polaris baseline = high_value if polaris_overall_score >= 0.5
composite_score = 0.5 * polaris_overall_score + 0.5 * usage_effectiveness_score
composite label = high_value if composite_score >= 0.5
```

## 可驗收門檻

| 範圍 | 門檻 |
|---|---:|
| 每類最少案例 | 5 |
| Polaris baseline F1／Recall／Specificity | 各 >= 0.80 |
| Composite Precision／Recall／Specificity／Accuracy／F1 | 各 >= 0.90 |
| 最低類別分數間隔 | >= 0.10 |
| Composite 相較 Polaris baseline 的最低 F1 增益 | >= 0.05 |

最低類別分數間隔定義為：`min(高價值 composite_score) - max(低效益 composite_score)`。任何完整清單、標註準則或門檻未通過，整體驗收即失敗。

## 重跑方式

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_value_classifier.py tests/test_polaris_annotation_validation.py -q
```

驗收實作位於 `tests/test_value_classifier.py::TestDatasetEvaluation` 與 `TestThresholdOptimization`；評估數值記錄於 `docs/polaris-annotation-evaluation-report.md`。
