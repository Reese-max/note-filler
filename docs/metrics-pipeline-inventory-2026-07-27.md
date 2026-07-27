# 筆記生產與分析流程盤點及指標欄位映射報告

日期：2026-07-27
基準 revision：`cd58d354`
任務：盤點現有筆記生產與分析流程，建立各指標所需欄位至既有資料來源的映射，並實作可重複執行的持續產出管線

## 執行摘要

經盤點，本專案已具備完整的筆記生產與分析流程，並實作了北極星品質指標計算系統。所有核心指標（功能缺口分數、使用者價值分數、來源綁定完整性、角度多樣性指數、端到端送達成功率）所需欄位均已完整實作，並建立了可重複執行的持續產出管線。

### 主要發現

✅ **筆記生產流程完整**：從解析輸入到產出訂正稿的完整管線已實作
✅ **指標計算系統完整**：北極星品質指標計算模組已建立並整合
✅ **資料來源映射完整**：所有指標所需欄位均有明確的資料來源映射
✅ **持續產出管線已實作**：具備週期性指標蒐集、彙總、查詢功能
✅ **時間戳與版本資訊完整**：指標輸出包含計算時間戳、公式版本、筆記識別碼

## 一、現有筆記生產與分析流程

### 1.1 核心生產管線

**位置**：`src/note_filler/pipeline.py:167-221`

**流程步驟**：
```
parse_note (T2) 
→ detect_domain (T3) 
→ generate_questions (T4) 
→ detect_gaps (T5) 
→ retrieve_for_gap (T9) [每個 gap 迴圈]
→ write_supplement (Q3) 
→ cross_validate (T10) 
→ assemble_correction (T12)
→ require_non_empty_note_product (品質閘)
→ require_traceable_note_product (追溯閘)
```

**輸入**：
- 原始筆記檔案（`.txt` 或 `.docx`）
- LLM 服務（Grok）
- Twinkle 來源服務
- 法條查詢服務

**輸出**：
- `CorrectionDoc` 物件（包含 original 與 segments）
- 訂正稿檔案（Markdown/JSON/DOCX）
- `binding_report.json`（機器可讀綁定報告）
- `delivery_manifest.json`（交付回執）

### 1.2 品質閘機制

**非空成品檢查**：`src/note_filler/pipeline.py:23-71`
- 硬性要求至少一份非空實際筆記內容
- 拒絕空白或僅稽核摘要的表面成功

**追溯性檢查**：`src/note_filler/pipeline.py:82-164`
- 逐段確認成品可回指原始輸入或實際來源
- 驗證 source_id 與 traceability 一致性
- 檢查來源片段完整性

**法條引用查核**：`src/note_filler/pipeline.py:224-249`
- law 領域對補充段執行離線法條查核
- 引用之法條在庫中找不到時降級為 pending_evidence
- 罰則金額不符時同樣降級

### 1.3 交付機制

**位置**：`src/note_filler/__main__.py:119-195`

**delivery_manifest.json 結構**：
```python
{
    "output_path": str,           # 輸出檔路徑
    "input_path": str,            # 輸入筆記路徑
    "status": "delivered" | "failed",
    "timestamp": str,             # ISO 8601 UTC
    "content_hash": str,          # sha256 前 16 碼
    "format": "md" | "json" | "docx",
    "supplements": int,           # 補充段數
    "verified": int,              # 已驗證段數
    "delivery_status": {
        "primary_note_ready": bool,
        "user_channel_sent": bool,
        "local_fallback_written": bool,
        "segment_delivery_details": list[dict]
    },
    "polaris_metrics": dict | None  # 北極星品質指標
}
```

## 二、指標欄位至資料來源映射

### 2.1 功能缺口分數（Functional Gap Score）

**計算公式**：
```
功能缺口分數 = 可追溯性×0.25 + 覆蓋廣度×0.25 + 必要性明確度×0.25 + 決策助益×0.25
```

**資料來源映射**：

| 指標欄位 | 資料來源 | 位置 | 輸出位置 |
|---------|---------|------|---------|
| functional_gap | Segment.functional_gap | correction.py:29 | binding_report.arguments[].functional_gap |
| source_ids | Segment.source_ids | correction.py:28 | binding_report.arguments[].source_ids |
| checks.at_least_one_source | 來源綁定檢查 | binding_report.py | binding_report.arguments[].checks.at_least_one_source |
| checks.source_traceable | 追溯性檢查 | binding_report.py | binding_report.arguments[].checks.source_traceable |
| checks.no_omitted_traces | 遺漏檢查 | binding_report.py | binding_report.arguments[].checks.no_omitted_traces |
| checks.no_extra_traces | 額外檢查 | binding_report.py | binding_report.arguments[].checks.no_extra_traces |
| checks.has_functional_gap | 功能缺口檢查 | binding_report.py | binding_report.arguments[].checks.has_functional_gap |
| angle_coverage.covered_facets | 角度覆蓋 | correction.py:37 | binding_report.arguments[].angle_coverage.covered_facets |
| angle_coverage.effective_angle_count | 有效角度數 | correction.py:38 | binding_report.arguments[].angle_coverage.effective_angle_count |

**判定規則**：
- 具體描述：functional_gap 欄位非空且長度 >= 10 字元
- 分數範圍：0.0 ~ 1.0
- 合格門檻：>= 0.7

### 2.2 使用者價值分數（User Value Score）

**計算公式**：
```
使用者價值分數 = 可追溯性×0.25 + 覆蓋廣度×0.25 + 必要性明確度×0.25 + 決策助益×0.25
```

**資料來源映射**：

| 指標欄位 | 資料來源 | 位置 | 輸出位置 |
|---------|---------|------|---------|
| user_value | Segment.user_value | correction.py:30 | binding_report.arguments[].user_value |
| source_ids | Segment.source_ids | correction.py:28 | binding_report.arguments[].source_ids |
| checks.at_least_one_source | 來源綁定檢查 | binding_report.py | binding_report.arguments[].checks.at_least_one_source |
| checks.source_traceable | 追溯性檢查 | binding_report.py | binding_report.arguments[].checks.source_traceable |
| checks.no_omitted_traces | 遺漏檢查 | binding_report.py | binding_report.arguments[].checks.no_omitted_traces |
| checks.no_extra_traces | 額外檢查 | binding_report.py | binding_report.arguments[].checks.no_extra_traces |
| checks.has_user_value | 使用者價值檢查 | binding_report.py | binding_report.arguments[].checks.has_user_value |
| angle_coverage.covered_facets | 角度覆蓋 | correction.py:37 | binding_report.arguments[].angle_coverage.covered_facets |
| angle_coverage.effective_angle_count | 有效角度數 | correction.py:38 | binding_report.arguments[].angle_coverage.effective_angle_count |

**判定規則**：
- 明確使用者價值：user_value 欄位非空且包含關鍵詞「讀者」、「說明」、「理解」
- 分數範圍：0.0 ~ 1.0
- 合格門檻：>= 0.7

### 2.3 來源綁定完整性（Source Binding Integrity）

**計算公式**：
```
來源綁定完整性 = (binding_status=pass 的論點數) / (總論點數)
```

**資料來源映射**：

| 指標欄位 | 資料來源 | 位置 | 輸出位置 |
|---------|---------|------|---------|
| binding_status | Segment.confidence + 來源檢查 | correction.py:24 | binding_report.arguments[].binding_status |

**判定規則**：
- 只計算 binding_status = "pass" 的論點
- 分數範圍：0.0 ~ 1.0
- 合格門檻：>= 0.8

### 2.4 角度多樣性指數（Angle Diversity Index）

**計算公式**：
```
角度多樣性 = (唯一角度類型數) / (預期角度類型數)
```

**資料來源映射**：

| 指標欄位 | 資料來源 | 位置 | 輸出位置 |
|---------|---------|------|---------|
| unique_angle_types | 角度覆蓋統計 | binding_report.py | binding_report.angle_coverage_summary.unique_angle_types |
| effective_angle_count | 有效角度數 | correction.py:38 | binding_report.angle_coverage_summary.effective_angle_count |

**判定規則**：
- 預期角度類型數：固定為 8
- 分數範圍：0.0 ~ 1.0
- 合格門檻：>= 0.6

### 2.5 端到端送達成功率（Delivery Success Rate）

**計算公式**：
```
送達成功率 = (delivery_status 所有布林欄位皆為 True 的次數) / (總處理次數)
```

**資料來源映射**：

| 指標欄位 | 資料來源 | 位置 | 輸出位置 |
|---------|---------|------|---------|
| primary_note_ready | 交付狀態 | __main__.py:39 | delivery_manifest.delivery_status.primary_note_ready |
| user_channel_sent | 使用者通道 | __main__.py:40 | delivery_manifest.delivery_status.user_channel_sent |
| local_fallback_written | 本機後援 | __main__.py:41 | delivery_manifest.delivery_status.local_fallback_written |

**判定規則**：
- 所有布林欄位皆為 True 才算成功送達
- 分數範圍：0.0 ~ 1.0
- 合格門檻：>= 0.9

## 三、持續產出管線實作

### 3.1 管線架構

**核心模組**：`src/note_filler/metrics_pipeline.py`

**主要元件**：

1. **MetricsCollectionConfig** - 蒐集配置
   - scan_dirs: 掃描目錄列表
   - output_dir: 輸出目錄
   - recursive: 是否遞迴掃描
   - file_pattern: 檔案模式（預設 delivery_manifest.json）
   - alert_thresholds: 告警門檻

2. **MetricsRecord** - 單筆指標記錄
   - source_path: 來源路徑
   - manifest_path: manifest 路徑
   - collection_time: 蒐集時間戳
   - polaris_metrics: 北極星指標資料
   - delivery_manifest: 原始 manifest 資料

3. **MetricsSummary** - 指標彙總統計
   - summary_time: 彙總時間戳
   - period_start/period_end: 統計期間
   - total_manifests: 總處理數
   - successful_collections: 成功蒐集數
   - failed_collections: 失敗數
   - average_scores: 平均分數
   - quality_distribution: 品質分佈
   - alerts: 告警記錄
   - improvement_priorities: 改善優先級

### 3.2 管線功能

**蒐集功能**：
- `collect_metrics_from_manifest()` - 從單一 manifest 蒐集指標
- `scan_and_collect_metrics()` - 掃描目錄並蒐集所有指標

**計算功能**：
- `calculate_summary_statistics()` - 計算彙總統計
- `_traceability_improvement_priorities()` - 依追溯扣分排序改善優先級

**儲存功能**：
- `save_metrics_summary()` - 儲存指標彙總（含時間戳）
- `save_detailed_records()` - 儲存詳細記錄（含時間戳）

**查詢功能**：
- `query_metrics_history()` - 查詢歷史指標彙總
- `query_latest_summary()` - 查詢最新指標彙總

### 3.3 時間戳與版本資訊

**時間戳保存**：
- collection_time: 每筆記錄的蒐集時間（ISO 8601 UTC）
- summary_time: 彙總計算時間（ISO 8601 UTC）
- period_start/period_end: 統計期間（ISO 8601 UTC）
- calculated_at: 指標計算時間（ISO 8601 UTC）

**版本資訊保存**：
- formula_version: 公式版本（目前 1.2）
- schema: 資料結構版本（note_filler.polaris_metrics.v1）

**筆記識別碼保存**：
- source_path: 來源檔案路徑
- manifest_path: manifest 檔案路徑
- input_path: 原始輸入路徑
- output_path: 輸出檔案路徑

### 3.4 持續產出機制

**事件制計算**：
- 每次單一筆記產出或更新 binding_report 時重算
- 在 write_delivery_receipt 前自動計算
- user_channel_sent 更新時重新計算並更新 manifest

**週期性蒐集**：
- 透過 scan_and_collect_metrics 掃描目錄
- 支援遞迴掃描子目錄
- 可配置檔案模式過濾

**歷史追蹤**：
- 每次執行產生時間戳記錄檔案
- 支援查詢最近 N 筆歷史記錄
- 保留原始 delivery_manifest 資料

### 3.5 改善優先級排序

**追溯性改善排序**：
- 依追溯扣分（score_penalty）降序排列
- 扣分相同時以總分（overall_score）排序
- 再以路徑（source_path, manifest_path）穩定排序
- 每筆記錄包含 rank、affected_argument_ids、repair_fields

**告警機制**：
- 可配置各指標的告警門檻
- 依嚴重性分級（warning/critical）
- 記錄告警時間與實際值

## 四、整合點與輸出位置

### 4.1 指標計算整合點

**主要整合點**：`src/note_filler/__main__.py:275-292`

```python
# 計算北極星品質指標
binding_report = build_binding_report(doc)
polaris_metrics = calculate_polaris_metrics(
    binding_report=binding_report,
    delivery_status=delivery_status,
).to_dict()

# 寫入 delivery receipt
write_delivery_receipt(
    dest, path,
    status="delivered",
    content=body if fmt != "docx" else None,
    fmt=fmt,
    supplements=len(supp),
    verified=ver,
    delivery_status=delivery_status,
    polaris_metrics=polaris_metrics,
)
```

### 4.2 輸出位置

**delivery_manifest.json**：
- 位置：與訂正稿同目錄
- 欄位：polaris_metrics（頂層）
- 時間戳：timestamp、calculated_at

**訂正稿 JSON**：
- 位置：{輸入檔名}.訂正稿.json
- 欄位：polaris_metrics（頂層）
- 時間戳：calculated_at

**訂正稿 Markdown/DOCX**：
- 位置：{輸入檔名}.訂正稿.{md,docx}
- 區塊：文末「北極星分數」與「北極星追蹤」
- 時間戳：calculated_at

**指標輸出目錄**：
- 位置：metrics_output/
- 檔案：metrics_summary_{timestamp}.json
- 檔案：metrics_records_{timestamp}.json

## 五、驗證與測試

### 5.1 測試覆蓋

**單元測試**：`tests/test_metrics.py`
- 功能缺口分數測試
- 使用者價值分數測試
- 來源綁定完整性測試
- 角度多樣性指數測試
- 送達成功率測試
- 北極星指標總覽測試

**管線測試**：`tests/test_metrics_pipeline.py`
- 單一 manifest 蒐集測試
- 目錄掃描測試
- 彙總統計測試
- 儲存功能測試
- 查詢功能測試
- 完整管線測試
- 追溯性改善排序測試

### 5.2 品質閘驗證

**資料完整性驗證**：
- schema 版本檢查
- 必填欄位檢查
- 時間戳格式檢查

**指標一致性驗證**：
- 公式版本一致性
- 來源欄位映射一致性
- 計算結果與閾值一致性

**追溯性驗證**：
- traceability_markers 完整性
- claim_source_map 一致性
- citation_span_map 正確性

## 六、結論

### 6.1 完成度評估

✅ **筆記生產流程**：100% 完成
- 完整的解析→偵測→補齊→驗證管線
- 嚴格的品質閘機制
- 完整的交付回執系統

✅ **指標欄位映射**：100% 完成
- 五項核心指標欄位完整映射
- 資料來源明確標註
- 輸出位置清楚定義

✅ **持續產出管線**：100% 完成
- 週期性蒐集功能
- 彙總統計功能
- 歷史查詢功能
- 改善優先級排序

✅ **時間戳與版本**：100% 完成
- 所有層級的時間戳保存
- 公式版本管理
- 筆記識別碼保存

### 6.2 可重複執行性

**管線可重複性**：
- 相同輸入產生相同輸出（ deterministic ）
- 時間戳記錄允許歷史追蹤
- 版本資訊支援公式變更管理

**資料可追溯性**：
- 每筆指標可追溯到原始 delivery_manifest
- 保留完整的原始資料
- 支援重新計算與驗證

### 6.3 後續建議

**短期**：
- 增加更多實際 delivery_manifest 範例進行測試
- 建立定期執行排程（如 cron job）
- 建立指標趨勢監控儀表板

**中期**：
- 增加跨時間窗的指標趨勢分析
- 建立指標異常檢測機制
- 整合外部監控系統

**長期**：
- 建立機器學習模型預測指標趨勢
- 建立自動化改善建議系統
- 整合多專案指標比較

## 附錄：關鍵檔案清單

### 核心實作檔案
- `src/note_filler/metrics.py` - 指標計算核心
- `src/note_filler/metrics_pipeline.py` - 持續產出管線
- `src/note_filler/pipeline.py` - 筆記生產管線
- `src/note_filler/__main__.py` - CLI 與交付整合
- `src/note_filler/binding_report.py` - 綁定報告生成

### 測試檔案
- `tests/test_metrics.py` - 指標計算測試
- `tests/test_metrics_pipeline.py` - 管線測試

### 文件檔案
- `docs/polaris-metrics-specification-2026-07-27.md` - 北極星指標規格
- `docs/note-output-dataflow-metrics-inventory-2026-07-27.md` - 資料流盤點

### 腳本檔案
- `scripts/run_metrics_pipeline.py` - 管線 CLI 工具