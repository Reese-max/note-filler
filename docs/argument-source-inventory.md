# 「論點」與「來源」資料流盤點報告

- 日期：2026-07-24
- 專案：note-filler (worktree 7ddaa0ef)
- 目的：盤點「論點（argument/claim）」與「來源（source）」在資料模型、序列化格式、輸出模板中的所有入口與出口；標示一對一／一對多綁定；列出最小缺口清單。

---

## 1. 核心資料模型定義

### 1.1 Source（`src/note_filler/retrieve/models.py`）

| 欄位 | 型別 | 綁定語意 | 說明 |
|---|---|---|---|
| `id` | `str` | 全域唯一識別碼 | 格式依來源層：`law:{pcode}:{article_no}`、`web:{sha1[:10]}`、twinkle 原生 ID |
| `title` | `str` | 標題 | 法條格式 `《法名》第N條` |
| `url` | `str \| None` | 連結 | law 恆有；twinkle/web 可能 None |
| `level` | `Literal["A","B","C","D"]` | 分級 | A=法規一手, B=立法院議案, C=官方一手, D=二手整理 |
| `content` | `str` | 全文 | 絕非摘要（G4 品質閘）；law 為法條全文, twinkle 為整筆展平, web 為 trafilatura 全文 |
| `fetched_date` | `str` | 擷取日 | ISO date, 恆有 |
| `doc_date` | `str \| None` | 文件日 | 取自原始記錄, 可能 None |
| `distance` | `float` | 排序權重 | 用於 C5 排序; 越小越優先 |

**綁定關係**：Source 被多處以 **多對多** 方式引用（見 §2）。

### 1.2 Gap（`src/note_filler/gap.py`）

| 欄位 | 型別 | 綁定語意 |
|---|---|---|
| `question` | `str` | 研究問題文字（作為全文 pipeline 中的隱式主鍵） |
| `status` | `Literal["covered","partial","missing"]` | 涵蓋狀態 |
| `reason` | `str` | 缺口理由 |

**綁定**：`question` 字串是 pipeline 中所有中間 dict 的 key（retrieved / written / validations），**但非結構化 ID**——依賴 LLM 輸出原文完全匹配。

### 1.3 WrittenSupplement（`src/note_filler/write.py`）

| 欄位 | 型別 | 綁定語意 |
|---|---|---|
| `text` | `str` | LLM 生成的補充段文字，含 `[^n]` 註腳標記 |
| `used_source_ids` | `list[str]` | 實際被引用的 Source.id 列表（依出現序去重） |

**綁定**：`used_source_ids` 對 `Source.id` 為 **多對多**（一個論點可引多個來源；一個來源可被多個論點引用）。`[^n]` 與 `sources[n-1]` 之映射為 **一對一位置綁定**（write.py:64-86）。

### 1.4 Validation（`src/note_filler/verify.py`）

| 欄位 | 型別 | 綁定語意 |
|---|---|---|
| `claim` | `str` | 被驗證的論點文字（= gap.question） |
| `sources` | `list` | 參與驗證的來源（= used sources） |
| `verified` | `bool` | 是否通過（>=1 A 或 >=1 C 或 >=2 異源） |
| `conflict` | `bool` | 是否有衝突 |
| `conflict_note` | `str \| None` | 衝突說明 |

**綁定**：`claim` → `Gap.question` 為 **一對一**；`sources` → `Source` 為 **多對多**（只含 used 來源子集）。

### 1.5 Segment（`src/note_filler/correction.py`）

| 欄位 | 型別 | 綁定語意 |
|---|---|---|
| `type` | `Literal["original","supplement"]` | 段落類型 |
| `text` | `str` | 原文或補充文字 |
| `anchor_idx` | `int \| None` | 對應原文段 idx（original 恆 = idx；supplement 取 best_anchor） |
| `sources` | `list` | 該段引用的 Source 物件列表 |
| `confidence` | `Literal["verified","pending_evidence"]` | 信心狀態 |
| `conflict_note` | `str \| None` | 衝突說明 |
| `traceability` | `list[dict]` | 追溯資訊（kind + id + 可選 paragraph_idx/question/outcome） |
| `source_id` | `str` | 聚合來源 ID 字串 |

**綁定**：
- `sources` → `Source` 為 **一對多**（一個 Segment 引用 0~N 個 Source）
- `anchor_idx` → `Paragraph.idx` 為 **多對一**（多個 supplement 可掛在同一個原文段）
- `source_id` 格式：
  - original: `input:{source_path}#p{idx}` — **一對一**綁定 Paragraph
  - supplement with sources: `sources:{id1},{id2}` — **一對多**聚合
  - supplement pending: `pending:gap:{idx}` — **一對一**綁定 gap index
- `traceability` 為 **多對多**：可含多筆 original_input / source / processing_record

### 1.6 CorrectionDoc（`src/note_filler/correction.py`）

| 欄位 | 型別 | 綁定語意 |
|---|---|---|
| `original` | `Document` | 原始輸入文件 |
| `segments` | `list[Segment]` | 所有段落（原文 + 補充） |

**綁定**：一對一持有 `Document`；一對多持有 `Segment`。

### 1.7 Document / Paragraph（`src/note_filler/parse.py`）

| 欄位 | 型別 | 綁定語意 |
|---|---|---|
| `Document.source_path` | `str` | 輸入檔路徑（全域唯一） |
| `Document.paragraphs` | `tuple[Paragraph, ...]` | 段落序列 |
| `Document.full_text` | `str` | 全文（`\n` 串接） |
| `Paragraph.idx` | `int` | 段落序號（0-based, frozen） |
| `Paragraph.text` | `str` | 段落原文（immutable） |

---

## 2. 資料流中「論點」與「來源」的所有入口與出口

### 2.1 入口（Entry Points）

| # | 入口 | 所在模組 | 論點形式 | 來源形式 | 綁定 |
|---|---|---|---|---|---|
| E1 | 使用者上傳筆記 | `parse.py` → `Document` | `Paragraph.text` = 原文論點 | 無（原始輸入不含來源） | — |
| E2 | LLM 生成研究問題 | `questions.py` → `list[str]` | `question` 字串 = 待驗證論點 | 無 | — |
| E3 | LLM Gap 偵測 | `gap.py` → `list[Gap]` | `Gap.question` = 確認缺口之論點 | 無 | — |
| E4 | 法條檢索 | `law_search.py` → `list[Source]` | — | `Source(id=law:..., level="A")` | 論點 gap → 多個 Source |
| E5 | Twinkle 檢索 | `twinkle.py` → `list[Source]` | — | `Source(id=原生, level="B")` | 論點 gap → 多個 Source |
| E6 | 開放網路檢索 | `web.py` → `list[Source]` | — | `Source(id=web:sha1, level="C/D")` | 論點 gap → 多個 Source |
| E7 | LLM 撰寫補充 | `write.py` → `WrittenSupplement` | `text` = 含 `[^n]` 的補充論點 | `used_source_ids` = 被引來源 ID 列表 | `[^n]` → `sources[n-1].id` 一對一 |
| E8 | 交叉驗證 | `verify.py` → `Validation` | `claim` = gap.question | `sources` = used sources | claim → sources 為多對多 |
| E9 | 法規引用查核 | `law_citation_check.py` → `list[dict]` | 正文中法條引用文字 | 離線法規 DB | law_name + article_no → DB 一對一 |
| E10 | 段落組裝 | `correction.py` → `Segment` | `text` = 原文或補充 | `sources` = used Sources 物件 | Segment → Source 為一對多 |

### 2.2 出口（Exit Points）

| # | 出口 | 所在模組 | 論點形式 | 來源形式 | 序列化 |
|---|---|---|---|---|---|
| X1 | JSON 輸出 | `export.py:to_json()` | `segment.text`, `segment.confidence` | `segment.sources` → `_source_to_dict()` | dict（含 sources 陣列） |
| X2 | Markdown 輸出 | `export.py:to_markdown()` | 原文 + `> 【補充】{text}[^n]` | `build_reference_lines()` → 註腳 | 純文字 |
| X3 | Docx 輸出 | `export.py:to_docx()` | 原文 + `【補充】{text}[^n]` | `build_reference_lines()` → 文末段落 | .docx |
| X4 | Web 雙欄 | `result.html` | `seg.text`（原文/補充） | `seg.sources` → Level/title/url/date | HTML |
| X5 | Markdown 下載 | `server.py:/export` | → to_markdown() | 同 X2 | HTTP response |
| X6 | 交付回執 | `__main__.py:write_delivery_receipt()` | — | — | JSON manifest |
| X7 | 稽核事件 | `audit_event()` | `data_id` = question/path | `missing_source_ids`, `source_ids` | JSON log line |
| X8 | 追溯資訊 | `export.py:_trace_text()` | — | `traceability[].kind + id` | 純文字字串 |

---

## 3. 綁定關係摘要（一對一 / 一對多 / 多對多）

### 3.1 一對一（1:1）

| 綁定 | 說明 |
|---|---|
| `WrittenSupplement` ↔ `Gap.question` | 每個 gap 產生一個 WrittenSupplement，以 question 字串為 key |
| `Validation` ↔ `Gap.question` | 每個 gap 有一個 Validation |
| `Segment.source_id` ↔ 原文段（original 型） | `input:{path}#p{idx}` 唯一綁定 Paragraph |
| `Segment.source_id` ↔ gap index（pending 型） | `pending:gap:{idx}` 唯一綁定 |
| `[^n]` 標記 ↔ `sources[n-1]` | 位置映射嚴格一對一 |
| `Segment` ↔ `CorrectionDoc.segments[i]` | 序列中唯一位置 |
| `Paragraph` ↔ `Document.paragraphs[i]` | 序列中唯一位置 |

### 3.2 一對多（1:N）

| 綁定 | 方向 | 說明 |
|---|---|---|
| `Gap` → `Source` | 1:N | 一個 gap 可檢索多個 sources（law + twinkle + web） |
| `Segment` → `Source` | 1:N | 一個 supplement segment 引用 0~N 個 sources |
| `CorrectionDoc` → `Segment` | 1:N | 一份訂正稿含多個 segments |
| `Document` → `Paragraph` | 1:N | 一份文件含多個段落 |
| `Validation` → `Source` | 1:N | 一份驗證含多個 sources |
| `Segment.traceability` → `trace entry` | 1:N | 一個 segment 含多筆追溯記錄 |

### 3.3 多對多（M:N）

| 綁定 | 說明 |
|---|---|
| `Source` ↔ `Segment` | 同一 Source 可被多個 Segment 引用；同一 Segment 可引用多個 Source |
| `Source` ↔ `Validation` | 同一 Source 可出現在多個 Validation 的 sources 列表 |
| `Gap.question` ↔ `Source` | 透過 `retrieved[question]` dict；同一 question 對多個 sources |

---

## 4. 來源識別碼完整追蹤

| 來源層 | ID 格式 | 產生位置 | 有 ID? | 有 level? | 有 url? | 有 doc_date? |
|---|---|---|---|---|---|---|
| Level A 法條 | `law:{pcode}:{article_no}` | law_search.py:108 | ✅ | ✅ A | ✅ moj.gov.tw | ❌ 恆 None |
| Level B 議案 | twinkle 原生 ID 或 URL 或 title | twinkle.py:245 | ✅ | ✅ B | ✅ 可能 None | ✅ 可能 None |
| Level C/D 網路 | `web:{sha1[:10]}` | web.py:201 | ✅ | ✅ C/D | ✅ | ✅ 可能 None |
| 原文輸入 | `input:{path}#p{idx}` | correction.py:101 | ✅ | — | — | — |
| 缺失/待補 | `pending:gap:{idx}` | correction.py:163 | ✅ | — | — | — |

**結論**：所有來源在模型層都有唯一識別碼（`Source.id`），且在 Segment 層有聚合識別碼（`source_id`）。追溯鏈完整。

---

## 5. 只存摘要或未帶來源識別碼的位置

### 5.1 `Gap.question` 作為 dict key（隱式依賴）

**位置**：`pipeline.py:144-163`

```python
retrieved[gap.question] = sources
written[gap.question] = w
validations[gap.question] = cross_validate(gap.question, used)
```

**問題**：`question` 是 LLM 產出的任意字串，沒有結構化 ID。若 LLM 對同一問題產出稍有差異的文字（如多了空白、改了標點），key 就會不匹配，導致 written/validations 找不到 retrieved。

**風險等級**：中。目前 pipeline 在同一次執行中 LLM 不會重複回答同一問題，但若重跑或合併多來源時可能出問題。

### 5.2 `Validation.claim` 只存文字副本

**位置**：`verify.py:88`

**問題**：`Validation.claim` 是 `gap.question` 的文字副本，沒有反向指向 `Gap` 的結構化 ID。若需從 Validation 追溯到 Gap，只能做字串比對。

**風險等級**：低。目前 pipeline 中 claim 與 question 在同一流程中匹配。

### 5.3 `Segment.sources` 為 untyped list

**位置**：`correction.py:29`

```python
sources: list  # list[Source]，但型別提示未收窄
```

**問題**：`sources` 欄位的型別標註為 `list`（未標 `list[Source]`）。在序列化（`to_json`）時透過 `asdict(s)` 正確展開，但在模板（`result.html`）中直接以 `s.level`、`s.title` 等屬性存取，若有人放入非 Source 物件將在執行期才爆炸。

**風險等級**：低。目前程式碼流程確保只放入 Source，但型別安全性不足。

### 5.4 `Segment.traceability` 為 `list[dict]`（非結構化）

**位置**：`correction.py:32`

**問題**：traceability 有三種 kind（`original_input` / `source` / `processing_record`），每種的 payload 結構不同，但共用同一 `list[dict]`，無 union type 或 sealed class。在 `result.html:66` 中以 `ref.kind` / `ref.id` / `ref.paragraph_idx` 存取，若 kind 與 payload 不匹配會静默產生空值。

**風險等級**：中。`pipeline.py:70-130` 的硬閘已驗證追溯完整性，但模板層無防禦。

### 5.5 `citation_formatter.py` 不存 Source.id 到輸出

**位置**：`citation_formatter.py:29-33`

**問題**：引用行格式為 `[^{i}]: [Level {level}] {title} | URL: {url} | Date: {date} | Hash: {hash} | Evidence: {evidence}`。**不含 Source.id**。若需從輸出的 Markdown 註腳反向追溯到 Source 物件，只能靠 title + url + hash 做模糊匹配，無精確 ID。

**風險等級**：高。若未來需要從匯出的 Markdown 自動化回溯到 Source（如自動化查核、跨文件去重），將缺乏精確錨點。

### 5.6 `_source_to_dict()` 展平所有 Source 欄位但無反向指標

**位置**：`export.py:10-12`

**問題**：`to_json()` 中每個 segment 的 sources 是 Source 的 dict 副本（含所有欄位），但 **不含 segment 自身的 ID**。若需從 JSON 的 sources 陣列反向找到「這些來源被哪個 segment 引用」，只能靠外層 segment 的 `source_id` 欄位做聚合，無法直接從 source dict 查到。

**風險等級**：低。JSON 結構已嵌套在 segment 內，外層可找到。

### 5.7 `to_markdown()` 的 footnote 編號非永久 ID

**位置**：`export.py:80-84`

**問題**：`[^n]` 的 n 是渲染時動態計數（`counter += 1`），非 Source.id。不同渲染（to_markdown vs to_docx）的編號可能不同。若有人拿 `[^3]` 去另一份輸出找，可能對到不同來源。

**風險等級**：低。這是 footnote 的標準行為，但需注意跨文件比較時的陷阱。

### 5.8 `audit_event()` 的 `data_id` 為自由字串

**位置**：`audit.py:12`

**問題**：稽核事件的 `data_id` 參數型別為 `object`（轉 `str`），各模組傳入的格式不一致：有時是 `gap.question`、有時是 `source.id`、有時是 `path`。若需從稽核 log 做結構化查詢，只能靠 regex 解析。

**風險等級**：低。稽核為輔助功能，非主資料流。

---

## 6. 最小缺口清單

| # | 缺口 | 嚴重度 | 說明 | 建議修補 |
|---|---|---|---|---|
| G1 | `Gap.question` 作為 dict key 無結構化 ID | 中 | pipeline 三個 dict 以 LLM 自由文字為 key，若文字微變將導致匹配失敗 | 為 Gap 加 `id: str` 欄位（如 `gap:{idx}`），所有 dict 改用 id 為 key |
| G2 | `citation_formatter` 輸出不含 Source.id | 高 | Markdown 註腳無精確來源 ID，無法從匯出檔自動化回溯 | 在引用行加入 Source.id（如 `[Level A] {title} (id: {id})`） |
| G3 | `Segment.sources` 型別標註為 untyped `list` | 低 | 型別安全性不足，IDE 無法推斷元素型別 | 改為 `list[Source]`（需 `TYPE_CHECKING` guard） |
| G4 | `Segment.traceability` 為 `list[dict]` 非結構化 | 中 | 三種 kind 的 payload 混在同一結構，無型別安全 | 定義 `TypedDict` 或 `dataclass` union（如 `OriginalTrace` / `SourceTrace` / `ProcessingTrace`） |
| G5 | `Validation.claim` 無反向 ID 指向 Gap | 低 | 需字串比對才能追溯 | 可加 `gap_id: str` 欄位（視未來需求決定） |
| G6 | `to_json()` 的 sources 無 segment 反向 ID | 低 | 嵌套結構已可追溯，但若需 flat 索引則不足 | 非必要，保持現狀 |
| G7 | `audit_event()` data_id 格式無統一規範 | 低 | 稽核 log 查詢需 regex | 可制定 `data_id` 格式規範（如 `{type}:{id}`） |

---

## 7. 結論

**現狀**：論點與來源在資料模型層的綁定完整度高。每個 Source 有唯一 ID，每個 Segment 有 `source_id` 聚合欄位與 `traceability` 追溯列表，pipeline 末端有硬閘（`require_traceable_note_product`）驗證追溯完整性。

**最大缺口**：G2（citation_formatter 輸出不含 Source.id）影響跨文件追溯能力；G1（Gap.question 無結構化 ID）影響 pipeline 健壯性。

**最小可行補修**：僅修 G1 + G2 即可覆蓋核心追溯需求。G3-G7 為型別安全 / 稽核品質改善，可擇期處理。
