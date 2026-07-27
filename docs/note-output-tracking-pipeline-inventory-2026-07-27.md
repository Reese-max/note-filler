# 筆記產出與追蹤流程盤點報告

**日期**: 2026-07-27  
**任務**: 盤點現有筆記產出與追蹤流程，實作可持續計算北極星指標的資料蒐集、轉換與彙總管線  
**範圍**: `src/note_filler/` 資料流與輸出格式，以及新增的週期性指標計算管線

---

## 1. 現有筆記產出與追蹤流程盤點

### 1.1 主流程資料流

根據程式碼盤點，現有筆記產出流程如下：

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

| 階段 | 資料結構 | 關鍵欄位 | 位置 |
|------|----------|----------|------|
| Gap Detection | `Gap` | `question`, `reason` | `gap.py` |
| Supplement Writing | `WrittenSupplement` | `text`, `used_source_ids` | `write.py` |
| Correction Assembly | `Segment` | `functional_gap`, `user_value`, `source_ids`, `angle_tags` | `correction.py` |
| Binding Report | `binding_report.json` | `arguments[].functional_gap`, `arguments[].user_value`, `arguments[].source_ids` | `binding_report.py` |
| Metrics Calculation | `PolarisMetrics` | 五項品質指標分數 | `metrics.py` |
| Final Output | `.json/.md/.docx` | `polaris_metrics`, `delivery_status` | `export.py` |
| Delivery Receipt | `delivery_manifest.json` | `polaris_metrics`, `delivery_status` | `__main__.py` |

### 1.3 北極星指標計算整合點

北極星品質指標已在以下位置整合：

1. **訂正稿 JSON 輸出** (`export.to_json`)
   - 頂層欄位：`polaris_metrics`
   - 每次輸出時由 `CorrectionDoc` 與綁定報告自動計算

2. **訂正稿 Markdown／DOCX 輸出** (`export.to_markdown`, `export.to_docx`)
   - 文末 `北極星分數` 與 `北極星追蹤` 區塊
   - 同步帶出公式版本、五項公式、來源欄位、分數與判定

3. **delivery_manifest.json** (`__main__.write_delivery_receipt`)
   - 頂層欄位：`polaris_metrics`
   - 每次成功送達時自動計算並寫入

4. **binding_report.json**
   - 作為指標計算的主要資料來源
   - 提供論點層級的詳細資訊

### 1.4 計算時機

- **成功送達時**：在 `write_delivery_receipt` 前自動計算
- **user_channel_sent 更新時**：重新計算並更新 manifest
- **失敗時**：不計算指標（因為可能沒有完整的 binding_report）

---

## 2. 週期性指標計算管線設計與實作

### 2.1 設計目標

基於現有流程，新增週期性指標計算管線以實現：

1. **資料蒐集**：從 `delivery_manifest.json` 蒐集北極星指標資料
2. **轉換與彙總**：計算週期性統計（平均分數、品質分佈）
3. **可查詢結果**：儲存歷史記錄，支援查詢最新與歷史趨勢
4. **執行失敗告警**：監控指標低於門檻時發出告警

### 2.2 管線架構

新增模組 `src/note_filler/metrics_pipeline.py`，提供以下功能：

#### 核心類別

1. **MetricsCollectionConfig**
   - 配置掃描目錄、輸出目錄、告警門檻等參數

2. **MetricsRecord**
   - 單筆指標記錄，包含來源資訊與北極星指標

3. **MetricsSummary**
   - 指標彙總統計，包含平均分數、品質分佈、告警記錄

#### 主要函式

1. **collect_metrics_from_manifest**
   - 從單一 `delivery_manifest.json` 蒐集指標
   - 驗證 schema 版本與資料完整性

2. **scan_and_collect_metrics**
   - 掃描指定目錄（支援遞迴）並蒐集所有指標
   - 過濾無效或缺失指標的 manifest

3. **calculate_summary_statistics**
   - 計算平均分數、品質分佈
   - 檢查告警門檻並產生告警記錄

4. **save_metrics_summary**
   - 儲存彙總結果為 JSON 檔案
   - 檔名包含時間戳以便追蹤

5. **save_detailed_records**
   - 儲存詳細指標記錄為 JSON 檔案
   - 保留原始資料以便後續分析

6. **run_metrics_pipeline**
   - 執行完整管線：蒐集 → 彙總 → 儲存 → 告警

7. **query_metrics_history**
   - 查詢歷史彙總記錄
   - 支援限制回傳數量

8. **query_latest_summary**
   - 查詢最新的指標彙總

### 2.3 CLI 工具

新增 `scripts/run_metrics_pipeline.py`，提供以下指令：

1. **collect**
   - 執行指標蒐集與彙總
   - 輸出統計摘要與告警資訊

2. **query**
   - 查詢歷史記錄
   - 支援指定回傳數量

3. **latest**
   - 查詢最新彙總
   - 顯示當前指標狀態

### 2.4 告警機制

告警機制包含以下特性：

1. **可配置門檻**
   - 每項指標可獨立設定門檻
   - 預設門檻：
     - functional_gap_score: 0.5
     - user_value_score: 0.5
     - source_binding_integrity: 0.7
     - angle_diversity_index: 0.4
     - delivery_success_rate: 0.8

2. **嚴重性分級**
   - warning: 實際值 >= 門檻 * 0.8
   - critical: 實際值 < 門檻 * 0.8

3. **告警記錄**
   - 記錄指標名稱、門檻、實際值、時間戳、嚴重性
   - 包含在彙總結果中

### 2.5 輸出格式

#### 彙總結果格式

```json
{
  "summary_time": "2026-07-27T12:00:00Z",
  "period_start": "2026-07-27T00:00:00Z",
  "period_end": "2026-07-27T23:59:59Z",
  "total_manifests": 10,
  "successful_collections": 10,
  "failed_collections": 0,
  "average_scores": {
    "functional_gap_score": 0.75,
    "user_value_score": 0.8,
    "source_binding_integrity": 0.85,
    "angle_diversity_index": 0.65,
    "delivery_success_rate": 0.95
  },
  "quality_distribution": {
    "excellent": 3,
    "good": 5,
    "acceptable": 2,
    "poor": 0,
    "error": 0
  },
  "alerts": [
    {
      "metric_name": "functional_gap_score",
      "threshold": 0.5,
      "actual_value": 0.45,
      "alert_time": "2026-07-27T12:00:00Z",
      "severity": "warning"
    }
  ],
  "records_count": 10
}
```

#### 詳細記錄格式

```json
[
  {
    "source_path": "/path/to/input.txt",
    "manifest_path": "/path/to/delivery_manifest.json",
    "collection_time": "2026-07-27T12:00:00Z",
    "polaris_metrics": { ... }
  }
]
```

---

## 3. 驗收測試

### 3.1 測試覆蓋

新增 `tests/test_metrics_pipeline.py`，包含以下測試類別：

1. **TestCollectMetricsFromManifest**
   - 測試從單一 manifest 蒐集指標
   - 驗證有效、無效、缺失指標的處理

2. **TestScanAndCollectMetrics**
   - 測試掃描目錄並蒐集指標
   - 驗證遞迴與非遞迴掃描

3. **TestCalculateSummaryStatistics**
   - 測試彙總統計計算
   - 驗證平均分數、品質分佈、告警門檻

4. **TestSaveMetricsSummary**
   - 測試儲存彙總結果
   - 驗證輸出格式與內容

5. **TestSaveDetailedRecords**
   - 測試儲存詳細記錄
   - 驗證資料完整性

6. **TestQueryMetricsHistory**
   - 測試查詢歷史記錄
   - 驗證數量限制與排序

7. **TestQueryLatestSummary**
   - 測試查詢最新彙總
   - 驗證無記錄時的處理

8. **TestRunMetricsPipeline**
   - 測試執行完整管線
   - 驗證端到端流程與告警觸發

### 3.2 測試執行

測試可透過以下指令執行：

```bash
python -m pytest tests/test_metrics_pipeline.py -v
```

整合測試可透過以下指令執行：

```bash
python -m pytest tests/test_metrics_pipeline.py -v -m integration
```

---

## 4. 使用範例

### 4.1 執行指標蒐集

```bash
python scripts/run_metrics_pipeline.py collect \
  --scan-dirs ./output \
  --output-dir ./metrics_output \
  --recursive
```

### 4.2 查詢歷史記錄

```bash
python scripts/run_metrics_pipeline.py query \
  --output-dir ./metrics_output \
  --limit 5
```

### 4.3 查詢最新彙總

```bash
python scripts/run_metrics_pipeline.py latest \
  --output-dir ./metrics_output
```

### 4.4 Python API 使用

```python
from note_filler.metrics_pipeline import (
    MetricsCollectionConfig,
    run_metrics_pipeline,
    query_latest_summary,
)

# 執行管線
config = MetricsCollectionConfig(
    scan_dirs=[Path("./output")],
    output_dir=Path("./metrics_output"),
)
summary = run_metrics_pipeline(config)

# 查詢最新
latest = query_latest_summary(config)
print(f"最新平均分數: {latest['average_scores']}")
```

---

## 5. 整合與部署建議

### 5.1 週期性執行

建議透過 cron 或 systemd timer 定期執行：

```cron
# 每小時執行一次
0 * * * * python /path/to/scripts/run_metrics_pipeline.py collect --scan-dirs /path/to/output
```

### 5.2 告警通知

目前告警僅記錄於日誌與彙總檔案，未來可擴展：

1. 整合 Email 通知
2. 整合 Slack/Teams Webhook
3. 整合監控系統（Prometheus/Grafana）

### 5.3 資料保留

建議設定資料保留策略：

1. 彙總檔案：保留最近 90 天
2. 詳細記錄：保留最近 30 天
3. 超過期限的檔案可自動清理

---

## 6. 結論

### 6.1 完成項目

1. ✅ 盤點現有筆記產出與追蹤流程
2. ✅ 設計資料蒐集、轉換與彙總管線架構
3. ✅ 實作週期性指標計算管線
4. ✅ 實作可查詢結果儲存與查詢介面
5. ✅ 實作執行失敗告警機制
6. ✅ 撰寫驗收測試
7. ✅ 撰寫盤點報告文檔

### 6.2 技術特點

1. **無侵入性**：基於現有 `delivery_manifest.json`，不需修改主流程
2. **可擴展性**：模組化設計，易於新增指標或調整告警規則
3. **可追溯性**：保留原始資料與計算過程，支援審計
4. **可用性**：提供 CLI 與 Python API，支援多種使用場景

### 6.3 未來擴展方向

1. **視覺化儀表板**：整合 Grafana 等工具建立監控儀表板
2. **趨勢分析**：新增時間序列分析，識別品質趨勢
3. **自動化修復**：整合自動化修復機制，處理常見問題
4. **多維度分析**：支援按來源、時間、主題等維度分析

---

## 7. 相關文件

- [北極星筆記品質指標規格](./polaris-metrics-specification-2026-07-27.md)
- [北極星品質指標欄位規格](./polaris_metrics_field_specification.md)
- [筆記輸出資料流欄位盤點與北極星指標支援分析](./note-output-dataflow-metrics-inventory-2026-07-27.md)
