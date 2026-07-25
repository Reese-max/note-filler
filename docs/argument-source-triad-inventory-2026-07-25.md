# argument → source 三元組盤點（argument text / source_id / source span）

- 日期：2026-07-25
- 工作目錄：`worktrees/90d9fa75`（僅本 repo）
- 任務：盤點最終成品與序列化層是否**同時**帶出 `argument text`、`source_id`、`source span(片段或位置)`；若缺則定位**唯一缺口**檔案與函式，並列出最小修改點。
- 驗證環境：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`，`PYTHONPATH=<repo>/src`
- 本任務為調查／盤點；**不改動程式碼**（僅產出本報告並 commit）。

---

## 0. 判定標準

| 欄位 | 可接受落點 | 不可算作 span 的近似物 |
|---|---|---|
| **argument text** | 成品 `Segment.text`；JSON `segments[].text`；MD/DOCX 正文；Web `result.html` 的 `seg.text` | — |
| **source_id** | 成品 `Segment.source_id` 與／或 `Source.id`／`traceability[].id`；序列化後仍可機器讀出 | 僅有 title／URL／Hash 而無 ID |
| **source span** | 來源內**支持該論點**的片段文字，或**位置**（如 `char_start`/`char_end`、段落偏移、可重定位的 quote locator） | ① 整份 `Source.content` 全文；② `Evidence: content[:100]` 固定前綴（與論點對齊無關）；③ 僅 `source_id` 而無片段／位置 |

三元組必須在**同一綁定層級**可對上（論點 ↔ 來源 ID ↔ 該來源內片段／位置），缺一即視為未同時帶出。

---

## 1. 資料流（argument → source）

```text
parse_note
  → detect_gaps (Gap.question)
  → retrieve_for_gap → list[Source]          # 全文 content，無 span 欄位
  → write_supplement → WrittenSupplement     # text + used_source_ids  ← 綁定首次形成
  → cross_validate(used sources)
  → assemble_correction → CorrectionDoc      # Segment 成品
  → require_traceable_note_product
  → export: to_json / to_markdown / to_docx  # 序列化層
  → Web: result.html
```

| 階段 | 檔案:函式 | argument text | source_id | source span |
|---|---|---|---|---|
| 檢索 | `retrieve/models.py` `Source` | — | `Source.id` | ❌ 無欄位（僅有 `content` 全文） |
| 撰寫綁定 | `write.py` `write_supplement` | `WrittenSupplement.text` | `used_source_ids: list[str]` | ❌ 只解析 `[^n]` → id，不記片段／位置 |
| 成品組裝 | `correction.py` `assemble_correction` | `Segment.text` | `Segment.source_id` + `sources[].id` + `traceability` | ❌ `Segment` 無 span 欄位；`traceability` 僅 `{kind,id}` |
| 追溯閘 | `pipeline.py` `require_traceable_note_product` | 檢查 text 非空 | 檢查 source_id／sources／traceability 對齊 | ❌ 不檢查 span |
| JSON | `export.py` `to_json` | `text` | `source_id` + `sources[].id` + `traceability` | ❌ 鍵集合無 span／offset／locator／excerpt |
| MD/DOCX | `export.py` + `citation_formatter.build_reference_lines` | 正文 `seg.text` | 追溯列「來源ID …」；註腳**不含** `Source.id` | ❌ `Evidence: content[:100]` 固定前綴，非論點對齊 span |
| Web | `app/templates/result.html` | `seg.text` | `traceability` 的 id；來源列表**無** `source_id`／span | ❌ 來源列僅 level/title/url/日期 |

**靜態掃描證據（本 repo `src/**/*.py`）**：`source_span` / `char_start` / `char_end` / `span_start` / `span_end` / `quote_span` / `locator` / `excerpt` / `fragment` 字樣 **0 命中**。  
唯一接近「片段」的輸出是 `citation_formatter.py` 的 `content[:100]`（見 §3）。

---

## 2. 成品層欄位證據

### 2.1 模型欄位（`dataclasses.fields`，2026-07-25 實跑）

| 型別 | 欄位 |
|---|---|
| `Source` | `id, title, url, level, content, fetched_date, doc_date, distance` |
| `WrittenSupplement` | `text, used_source_ids` |
| `Segment` | `type, text, anchor_idx, sources, confidence, conflict_note, traceability, source_id` |

→ 三型別皆**無** source span 欄位。

### 2.2 組裝邏輯（唯一把 used id 掛到成品的地方）

[`src/note_filler/correction.py`](../src/note_filler/correction.py) `assemble_correction`：

- `Segment.text = w.text`（argument text ✅）
- `source_id = sources:{id1,id2}` 或 `pending:gap:{idx}`（source_id ✅）
- `sources = used_sources`（完整 `Source` 物件，含全文 `content`，**無** span）
- `traceability = [{"kind":"source","id": source.id}, ...]`（僅 id，**無** span）

關鍵片段（約 159–185 行）：只組 `source_id` 與 `{"kind","id"}`，從不寫入片段或偏移。

### 2.3 綁定首次形成處

[`src/note_filler/write.py`](../src/note_filler/write.py) `write_supplement`（約 64–97 行）：

- 以 regex `\[\^(\d+)\]` 對映 `sources[n-1].id`
- 產出僅 `WrittenSupplement(text=..., used_source_ids=used)`
- **不**記錄：論點子句邊界、來源內 `char_start/char_end`、引用 quote 文字

此處是 argument↔source **ID 綁定**的起點，也是 **span 從未進入資料流** 的起點。

---

## 3. 序列化層證據

### 3.1 JSON（`export.to_json`）

supplement 段鍵（實跑）：

```text
['anchor_idx', 'confidence', 'conflict_note', 'source_id', 'sources', 'text', 'traceability', 'type']
```

source 鍵：

```text
['content', 'distance', 'doc_date', 'fetched_date', 'id', 'level', 'title', 'url']
```

對 `span/offset/char_start/char_end/locator/quote/excerpt/fragment/position/source_span` 掃描：**皆 False**。

| 三元組 | JSON | 判定 |
|---|---|---|
| argument text | `segments[].text` | ✅ |
| source_id | `segments[].source_id` + `sources[].id` + `traceability` | ✅ |
| source span | 無鍵；`content` 為全文非 span | ❌ |

### 3.2 Markdown / DOCX

- 正文：`seg.text` ✅
- 追溯列（`export._trace_text`）：含 `來源ID {source_id}` 與 `來源識別碼 {id}` ✅（產品層 source_id 有落到 MD）
- 文末註腳（`citation_formatter.build_reference_lines`）：

```text
[^{i}]: [Level {level}] {title} | URL: … | Date: … | Hash: … | Evidence: {content[:100]}
```

| 項目 | 判定 |
|---|---|
| 註腳含 Source.id | ❌（舊 G2；但段級 `來源ID` 已另列，**不**構成本任務唯一缺口） |
| `Evidence` 是否為 source span | ❌ 固定 `content[:100]`，與該論點在來源中的支持位置無對齊、無 start/end |

### 3.3 Web（`result.html`）

- 顯示 `seg.text` ✅
- `traceability` 的 kind/id（original 另有 paragraph_idx）— 有 id，**無** 段級 `source_id` 字串、**無** span
- 來源 `<details>`：level/title/url/日期 — **無** `s.id`、**無** 片段

---

## 4. 三元組總表（最終輸出）

| 輸出通道 | argument text | source_id | source span | 同時帶出？ |
|---|---|---|---|---|
| 成品 `CorrectionDoc` / `Segment` | ✅ `text` | ✅ `source_id` + sources/traceability | ❌ | **否** |
| JSON | ✅ | ✅ | ❌ | **否** |
| Markdown | ✅ | ✅（追溯列） | ❌（Evidence≠span） | **否** |
| DOCX | ✅ | ✅（追溯列） | ❌ | **否** |
| Web result | ✅ | 部分（trace id，非完整 source_id 欄） | ❌ | **否** |

**結論：最終輸出尚未同時帶出三元組；唯一實質缺口為 `source span`（全鏈從未建模／產生／序列化）。**  
`argument text` 與 `source_id` 已在成品與 JSON／MD 追溯列落地。

---

## 5. 唯一缺口定位

| 項目 | 內容 |
|---|---|
| **缺口欄位** | `source span`（來源內支持論點的片段或位置） |
| **唯一缺口檔案** | [`src/note_filler/write.py`](../src/note_filler/write.py) |
| **唯一缺口函式** | `write_supplement`（含其回傳型別 `WrittenSupplement`） |
| **理由** | argument→source 綁定**第一次**在此形成，卻只產出 `text` + `used_source_ids`；下游 `assemble_correction`／`to_json`／`build_reference_lines` 皆無 span 可轉送。缺口在**產生點**，非僅序列化遺漏。 |
| **為何不是 export 單獨問題** | 成品 `Segment` 本身無 span 欄位；即使改序列化也無資料可寫。 |
| **為何不是 Source 模型單獨問題** | `Source.content` 是整份來源全文；span 是「論點對來源的切片」，屬**綁定**屬性，應掛在 citation／segment 綁定上，而非取代 Source 全文。 |
| **近似物排除** | `Evidence: content[:100]`（`citation_formatter.py:26`）= 全文固定前綴，**不算** source span。`anchor_idx` / `paragraph_idx` = 對**輸入原文**的錨點，非對檢索來源的 span。 |

---

## 6. 最小修改點（僅定位，本任務不實作）

依資料流順序的最小閉環（改完才會「成品 + 序列化」同時有三元組）：

| # | 檔案 | 函式／位置 | 最小改動 |
|---|---|---|---|
| M1 | `src/note_filler/write.py` | `WrittenSupplement` | 新增綁定結構，例如 `citations: list[Citation]`，每筆至少 `{source_id, argument_span?, source_span}`；`source_span` 建議 `{start:int,end:int,quote:str}` 或等價 locator。 |
| M2 | `src/note_filler/write.py` | `write_supplement` / `_sub` | 在解析 `[^n]` 時寫入 citation；span 產生策略二選一（實作時再定）：(a) 以論點子句對 `Source.content` 做離線對齊取最大重疊片段；(b) 要求 LLM 同步輸出 quote 再驗證為 content 子字串。缺 span → 可比照無來源走 `pending_evidence` 或明確失敗（見品質閘精神 L071）。 |
| M3 | `src/note_filler/correction.py` | `Segment` + `assemble_correction` | 成品增加可序列化欄位（如 `source_spans: list[dict]` 或擴充 `traceability` 的 source 項：`start/end/quote`）；從 `WrittenSupplement.citations` 轉送，**不可靜默丟棄**。 |
| M4 | `src/note_filler/export.py` | `to_json` | 每段輸出 span 欄位；確保與 `text`、`source_id` 同層可讀。 |
| M5 | `src/note_filler/citation_formatter.py` | `build_reference_lines` | `Evidence` 改為**實際 source span quote**（可截斷），勿再用無對齊的 `content[:100]`；建議同時附 `Source.id`（舊 G2）。 |
| M6 | `src/note_filler/pipeline.py` | `require_traceable_note_product`（可選但建議） | 對有 sources 的 supplement：要求每筆 used source 具備非空 span／quote，否則硬失敗。 |
| M7 | 測試 | `tests/test_write.py`、`test_traceability.py`、`test_export.py`、`test_source_binding_acceptance.py` | 正例：三元組齊全；負例：有 text+id 無 span → 失敗或 pending（L071/L074）。 |

**最小必改集合**：M1–M4（無 M1 則下游無資料；無 M3/M4 則成品／JSON 仍缺）。M5–M7 為人讀輸出與品質閘對齊。

**非缺口／勿擴 scope**：`BACKLOG.md` 不動；不在此任務實作 M1–M7；不改白名單／deselected 治理（除非後續實作任務明確要求）。

---

## 7. 可重現驗證命令與輸出摘要

```powershell
$env:PYTHONPATH = "<repo>/src"
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -c "<組裝最小 CorrectionDoc 後 to_json / to_markdown>"
```

實跑摘要（2026-07-25）：

- `Segment`／`Source`／`WrittenSupplement` 欄位見 §2.1
- JSON supplement 含 `text` + `source_id=sources:law:92:14` + `sources[0].id`；**無**任何 span 鍵
- MD 含 `來源ID sources:law:92:14` 與 `Evidence: <content 前綴>`；Evidence ≠ 對齊 span
- `src` 內 span 相關識別字 **0 命中**

---

## 8. 與既有文件關係

| 文件 | 關係 |
|---|---|
| `docs/argument-source-inventory.md`（2026-07-24） | 盤點論點／來源入口出口與 G1–G7；**未**以三元組（含 source span）為硬性驗收軸 |
| 本文件 | 專責三元組是否同時落在成品／序列化；結論：**span 為唯一缺口**，根因在 `write_supplement` |

---

## 9. 一句話結論

**argument text 與 source_id 已在成品與主要序列化通道落地；source span 在 `write_supplement` 起點即未產生，故最終輸出無法同時帶出三元組。** 唯一缺口：[`src/note_filler/write.py`](../src/note_filler/write.py) 的 `write_supplement`／`WrittenSupplement`；最小修改從該處新增 citation+span，經 `assemble_correction` 進成品，再由 `to_json`／`build_reference_lines` 輸出。
