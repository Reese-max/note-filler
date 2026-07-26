# 筆記輸出資料流欄位盤點與北極星指標支援分析

日期：2026-07-27
基準 revision：`cad7bfc3`

## 結論

經盤點，目前筆記輸出資料流中已具備計算「功能缺口」與「使用者價值」相關指標的核心欄位。主要資料來源包括 `Segment` 資料模型、`binding_report.json` 機器可讀報告、以及 `delivery_manifest.json` 交付回執。所有任務指定的欄位（source_ids、functional_gap、user_value、angle_tags、delivery_status）均已存在且可直接量測。

## 資料流架構

### 1. 核心資料模型

#### Segment 資料模型
位置：`src/note_filler/correction.py:135-160`

```python
@dataclass
class Segment:
    type: Literal["original", "supplement"]
    text: str
    anchor_idx: int | None
    sources: list
    confidence: Literal["verified", "pending_evidence"]
    conflict_note: str | None = None
    traceability: list[dict] = field(default_factory=list)
    source_id: str = ""
    source_ids: list[str] = field(default_factory=list)
    functional_gap: str = ""
    user_value: str = ""
    summary: str | None = None
    related_knowledge: str | None = None
    argument_id: str = ""
    angle_type: str = ""
    angle_labels: list[str] = field(default_factory=list)
    angle_key: str = ""
    angle_tags: list[str] = field(default_factory=list)
    valid_angle_count: int = 0
    deduped_angle_count: int = 0
    duplicate_angles: list[str] = field(default_factory=list)
```

#### CorrectionDoc 資料模型
位置：`src/note_filler/correction.py:162-165`

```python
@dataclass
class CorrectionDoc:
    original: "Document"
    segments: list
```

### 2. 資料流處理流程

位置：`src/note_filler/pipeline.py:157-211`

```
parse_note → detect_domain → generate_questions → detect_gaps 
→ retrieve_for_gap → write_supplement → cross_validate 
→ assemble_correction → require_non_empty_note_product 
→ require_traceable_note_product
```

## 可直接量測的欄位盤點

### 1. source_ids（來源識別碼）

**存在狀態：✅ 已完整實作**

**資料來源：**
- `Segment.source_ids`：列表形式，儲存所有來源 ID
- `Segment.source_id`：字串形式，格式為 `sources:id1,id2` 或 `pending:gap:index`
- `Segment.sources`：Source 物件列表，含完整來源資訊

**輸出位置：**
- `binding_report.json`：每個 argument 的 `source_ids` 欄位
- `delivery_manifest.json`：透過 `segment_delivery_details` 逐段記錄
- 訂正稿 Markdown/JSON/DOCX：在「來源清單」區塊顯示

**量測能力：**
- 來源數量統計（one_to_one / one_to_many / none）
- 來源重複檢測
- 來源追溯完整性驗證

**計算北極星指標用途：**
- 來源綁定完整性 = (有來源的論點數) / (總論點數)
- 一手來源覆蓋率 = (Level A 來源數) / (總來源數)

### 2. functional_gap（功能缺口）

**存在狀態：✅ 已完整實作**

**資料來源：**
- `Segment.functional_gap`：字串，描述原稿缺失的功能
- 來源：`gap.reason`（從 `detect_gaps` 取得）

**輸出位置：**
- `binding_report.json`：每個 argument 的 `functional_gap` 欄位
- 訂正稿 Markdown/JSON/DOCX：在「功能缺口」區塊顯示
- 角度覆蓋：作為 `necessity:functional_gap` facet

**量測能力：**
- 功能缺口填補率 = (有 functional_gap 的論點數) / (總論點數)
- 功能缺口具體性檢測（非空且具體描述）

**計算北極星指標用途：**
- 功能缺口覆蓋率 = (已填補的功能缺口數) / (偵測到的總缺口數)
- 功能缺口品質 = (具體描述的缺口數) / (總缺口數)

### 3. user_value（使用者價值）

**存在狀態：✅ 已完整實作**

**資料來源：**
- `Segment.user_value`：字串，格式為「補齊讀者對「{問題}」所需的說明」
- 來源：`assemble_correction` 中依問題自動生成

**輸出位置：**
- `binding_report.json`：每個 argument 的 `user_value` 欄位
- 訂正稿 Markdown/JSON/DOCX：在「使用者價值」區塊顯示
- 角度覆蓋：作為 `necessity:user_value` facet

**量測能力：**
- 使用者價值明確性檢測
- 使用者價值與功能缺口一致性驗證

**計算北極星指標用途：**
- 使用者價值覆蓋率 = (有 user_value 的論點數) / (總論點數)
- 使用者價值相關性 = (與功能缺口相關的 user_value 數) / (總 user_value 數)

### 4. angle_tags（角度標籤）

**存在狀態：✅ 已完整實作**

**資料來源：**
- `Segment.angle_tags`：列表，包含角度類型與必要性標籤
- `Segment.angle_type`：主角度類型（definition/limitation/requirement 等）
- `Segment.angle_labels`：完整角度標籤清單

**輸出位置：**
- `binding_report.json`：每個 argument 的 `angle_tags` 欄位
- 訂正稿 Markdown/JSON/DOCX：在「角度覆蓋」區塊顯示
- `angle_coverage_summary`：整體角度覆蓋統計

**量測能力：**
- 角度類型分佈統計
- 角度重複檢測（duplicate/synonym）
- 角度覆蓋完整性（四類必要 facet：angle_type、functional_gap、user_value、question）

**計算北極星指標用途：**
- 角度多樣性 = (唯一角度類型數) / (預期角度類型數)
- 角度覆蓋率 = (有效角度數) / (最低要求角度數)
- 重複角度比率 = (排除角度數) / (總角度數)

### 5. delivery_status（送達狀態）

**存在狀態：✅ 已完整實作**

**資料來源：**
- `_delivery_status()` 函式：`src/note_filler/__main__.py:36-56`
- `_build_segment_delivery_details()` 函式：`src/note_filler/__main__.py:59-86`

**輸出位置：**
- `delivery_manifest.json`：頂層 `delivery_status` 欄位
- `process_file()` 回傳值：包含 `delivery_status`

**欄位結構：**
```python
{
    "primary_note_ready": bool,           # 成品筆記就緒
    "user_channel_sent": bool,             # 使用者通道已送達
    "local_fallback_written": bool,        # 本機後援已寫入
    "segment_delivery_details": [         # 逐段送達詳情
        {
            "question": str,               # 問題或段落索引
            "confidence": str,             # verified/pending_evidence
            "has_sources": bool,           # 是否有來源
            "degraded": bool               # 是否降級補齊
        }
    ]
}
```

**量測能力：**
- 送達成功率 = (成功送達的檔案數) / (總處理檔案數)
- 降級補齊率 = (降級段數) / (總段數)
- 使用者通道送達率 = (user_channel_sent=True 的次數) / (總次數)

**計算北極星指標用途：**
- 端到端送達成功率 = delivery_status 中所有布林欄位皆為 True 的比例
- 降級容忍度 = 降級補齊但仍送達成功的比例

## 最終可讀輸出位置

### 1. 機器可讀報告

#### binding_report.json
位置：與訂正稿同目錄

**核心欄位：**
- `arguments[]`：每個論點的完整綁定資訊
- `source_usage`：來源使用反向索引
- `angle_coverage_summary`：角度覆蓋統計
- `summary`：整體綁定統計（pass/fail/pending_evidence 計數）

**適用指標計算：**
- 來源綁指標
- 功能缺口指標
- 使用者價值指標
- 角度覆蓋指標

#### delivery_manifest.json
位置：與訂正稿同目錄

**核心欄位：**
- `status`：delivered/failed
- `delivery_status`：送達狀態詳情
- `segment_delivery_details`：逐段送達詳情
- `content_hash`：內容雜湊值

**適用指標計算：**
- 送達成功率
- 降級補齊率
- 端到端完整性

### 2. 人類可讀輸出

#### Markdown 訂正稿
位置：`{輸入檔名}.訂正稿.md`

**結構化區塊：**
- 功能缺口區塊
- 使用者價值區塊
- 來源清單區塊
- 角度覆蓋區塊
- 來源綁定摘要
- 角度覆蓋摘要

#### JSON 訂正稿
位置：`{輸入檔名}.訂正稿.json`

**結構：**
- 完整 Segment 資訊
- binding_summary（整合 binding_report 摘要）
- angle_coverage_summary

#### DOCX 訂正稿
位置：`{輸入檔名}.訂正稿.docx`

**結構：**
- 與 Markdown 對應的區塊結構
- 角度覆蓋摘要

## 北極星指標產出支援分析

### 已具備的基礎

✅ **資料完整性**
- 所有核心欄位均已實作且可機器讀取
- 資料流從輸入到輸出完整可追溯
- 機器可讀報告（binding_report.json）提供結構化資料

✅ **量測能力**
- 來源綁定完整性可量化
- 功能缺口覆蓋可統計
- 使用者價值明確性可檢測
- 角度多樣性可計算
- 送達成功率可追蹤

✅ **驗證機制**
- binding_report 提供嚴格的欄位契約驗證
- 角度有效性檢查確保四類必要 facet 齊備
- 必要性雙視角檢查確保 functional_gap 與 user_value 一致性

### 可能需要新增的項目

⚠️ **北極星指標定義**
- 目前 codebase 中未找到「北極星指標」的明確定義
- 需要明確指定北極星指標的計算公式與目標值
- 建議在 docs/ 中新增北極星指標定義文件

⚠️ **指標聚合層**
- 目前指標計算分散在各個報告中
- 若需要跨檔案、跨時間的指標聚合，需要新增：
  - 指標計算模組（`src/note_filler/metrics.py`）
  - 指標歷史記錄機制
  - 指標趨勢分析功能

⚠️ **指標閾值設定**
- 目前角度覆蓋有門檻設定（MIN_EFFECTIVE_ANGLE_COUNT、MAX_DUPLICATE_RATIO）
- 其他指標的閾值可能需要新增設定檔

### 建議的北極星指標計算公式

基於現有欄位，建議以下北極星指標：

#### 1. 功能缺口填補率
```python
功能缺口填補率 = (有 functional_gap 且非空的論點數) / (總論點數)
```
資料來源：`binding_report.arguments[].functional_gap`

#### 2. 使用者價值覆蓋率
```python
使用者價值覆蓋率 = (有 user_value 且非空的論點數) / (總論點數)
```
資料來源：`binding_report.arguments[].user_value`

#### 3. 來源綁定完整性
```python
來源綁定完整性 = (binding_status=pass 的論點數) / (總論點數)
```
資料來源：`binding_report.arguments[].binding_status`

#### 4. 角度多樣性指數
```python
角度多樣性 = (唯一角度類型數) / (預期角度類型數)
```
資料來源：`binding_report.angle_coverage_summary.unique_angle_types`

#### 5. 端到端送達成功率
```python
送達成功率 = (delivery_status 所有布林欄位皆為 True 的次數) / (總處理次數)
```
資料來源：`delivery_manifest.delivery_status`

## 結論與建議

### 現況評估
目前筆記輸出資料流已具備計算北極星指標所需的所有基礎欄位：
- ✅ source_ids：完整實作，可量測來源綁定
- ✅ functional_gap：完整實作，可量測功能缺口填補
- ✅ user_value：完整實作，可量測使用者價值覆蓋
- ✅ angle_tags：完整實作，可量測角度多樣性
- ✅ delivery_status：完整實作，可量測送達成功率

### 後續建議
1. **明確定義北極星指標**：在 docs/ 中新增指標定義文件，說明計算公式與目標值
2. **新增指標計算模組**：建立 `src/note_filler/metrics.py` 集中處理指標計算
3. **建立指標報告機制**：定期產生指標報告，追蹤趨勢變化
4. **設定指標閾值**：為各指標設定合理的閾值，作為品質閘

### 無需新增的欄位
所有任務指定的欄位均已存在且功能完整，無需新增資料結構即可支撐北極星指標產出。