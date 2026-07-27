# 北極星品質指標標註驗證集評估報告

日期：2026-07-27

標註準則：`docs/polaris-annotation-guidelines.md`

驗收契約：`tests/fixtures/polaris_annotation/acceptance_contract.json`

## 結論

固定驗證集共 10 筆，5 筆高價值、5 筆形式完整但低效益；清單、類別、必要欄位、來源失敗語義與三種綁定基數均符合契約。Polaris baseline 可區分大部分案例，加入使用成效後可正確降級「形式分數高但零使用」案例，所有驗收門檻通過。

## 資料集完整性

| 檢查 | 結果 |
|---|---:|
| 高價值案例 | 5／5 |
| 低效益案例 | 5／5 |
| 契約 note_id 遺漏／重複／多餘 | 0／0／0 |
| 人工標註狀態 | 10／10 validated |
| 綁定基數覆蓋 | `none`、`one_to_one`、`one_to_many` |
| 無來源卻未標 pending_evidence | 0 |

低效益案例仍具備非空的 `functional_gap`、`user_value` 與 `related_knowledge`，因此不是靠空資料製造分數差異。`low_benefit_005` 的 Polaris 分數為 0.850，但使用成效為 0，專門驗證純形式指標的假陽性邊界。

## 區分能力

### Polaris baseline

決策：`polaris_overall_score >= 0.5` 判為高價值。

| | 預測高價值 | 預測低效益 |
|---|---:|---:|
| 實際高價值 | 5 | 0 |
| 實際低效益 | 1 | 4 |

| 指標 | 實測 | 門檻 | 結果 |
|---|---:|---:|---|
| F1 | 0.9091 | >= 0.80 | 通過 |
| Recall | 1.0000 | >= 0.80 | 通過 |
| Specificity | 0.8000 | >= 0.80 | 通過 |

### Composite 指標

決策：`0.5 * Polaris + 0.5 * Usage >= 0.5` 判為高價值。

| | 預測高價值 | 預測低效益 |
|---|---:|---:|
| 實際高價值 | 5 | 0 |
| 實際低效益 | 0 | 5 |

| 指標 | 實測 | 門檻 | 結果 |
|---|---:|---:|---|
| Precision | 1.0000 | >= 0.90 | 通過 |
| Recall | 1.0000 | >= 0.90 | 通過 |
| Specificity | 1.0000 | >= 0.90 | 通過 |
| Accuracy | 1.0000 | >= 0.90 | 通過 |
| F1 | 1.0000 | >= 0.90 | 通過 |
| 高低類別最低分數間隔 | 0.1688 | >= 0.10 | 通過 |
| 相較 baseline 的 F1 增益 | 0.0909 | >= 0.05 | 通過 |

## 逐筆結果

| note_id | Ground truth | Polaris | Usage | Composite | 預測 |
|---|---|---:|---:|---:|---|
| `high_value_001` | high_value | 0.8750 | 0.7533 | 0.8142 | high_value |
| `high_value_002` | high_value | 0.8750 | 0.6660 | 0.7705 | high_value |
| `high_value_003` | high_value | 0.8750 | 0.8690 | 0.8720 | high_value |
| `high_value_004` | high_value | 0.8750 | 0.6043 | 0.7397 | high_value |
| `high_value_005` | high_value | 0.8750 | 0.3127 | 0.5938 | high_value |
| `low_benefit_001` | low_benefit | 0.3500 | 0.0100 | 0.1800 | low_benefit |
| `low_benefit_002` | low_benefit | 0.3500 | 0.0050 | 0.1775 | low_benefit |
| `low_benefit_003` | low_benefit | 0.3500 | 0.0020 | 0.1760 | low_benefit |
| `low_benefit_004` | low_benefit | 0.3500 | 0.0440 | 0.1970 | low_benefit |
| `low_benefit_005` | low_benefit | 0.8500 | 0.0000 | 0.4250 | low_benefit |

最低高價值分數為 0.5938，最高低效益分數為 0.4250，未四捨五入間隔為 0.1688。

## 驗證指令

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_value_classifier.py tests/test_polaris_annotation_validation.py -q
```

結果：相關驗收 `44 passed`；完整非 integration 測試 `646 passed, 11 deselected`。這是固定合成驗收集的回歸證據，不外推為線上真實使用成效。
