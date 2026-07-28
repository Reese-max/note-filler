# 延伸閱讀輸出格式規格

## 概述

本文檔定義延伸閱讀（extended_readings）的固定可解析格式規格，確保 pytest 能對最終成品做逐項驗證，避免只改顯示格式卻讓驗收無法比對。

## 規格版本

- **schema_id**: `note_filler.extended_readings_format_specification.v1`
- **version**: `1.0`
- **specification_date**: `2026-07-28`

## 論點區塊欄位順序

每個論點區塊（supplement segment）的延伸閱讀相關欄位必須按以下順序輸出：

1. `extended_readings` - 延伸閱讀來源列表
2. `extended_readings_status` - 延伸閱讀狀態
3. `pending_evidence_reason` - 待補證原因
4. `openable_links_count` - 可開啟連結數量
5. `openable_links_status` - 可開啟連結狀態
6. `openable_links_incomplete_reason` - 可開啟連結不足原因

## extended_readings 欄位契約

### 欄位定義

每筆延伸閱讀記錄必須包含以下欄位，按順序排列：

```python
{
    "source_id": str,      # 來源識別碼
    "title": str,          # 來源標題
    "url": str | None,     # 來源 URL（可為 None）
    "level": str,          # 來源層級（A/B/C/D）
    "distance": float,      # 相關性距離（0.0-1.0）
}
```

### 欄位型別約束

- `source_id`: 必須為非空字串
- `title`: 必須為非空字串
- `url`: 可為字串或 None，若為字串必須符合 URL 格式
- `level`: 必須為 "A", "B", "C", "D" 其中之一
- `distance`: 必須為數值（int 或 float），範圍 0.0-1.0

## 連結抽取規則

### 1. 優先級排序

延伸閱讀來源必須按以下優先級排序：

1. **Level 優先**: A > B > C > D
2. **距離次優先**: 同層級內按 distance 遞增排序

排序函數：
```python
def reading_priority_key(r):
    level_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    level_priority = level_order.get(r.get("level", "?"), 99)
    distance = r.get("distance", 1.0)
    return (level_priority, distance)
```

### 2. 來源收集規則

延伸閱讀只包含「檢索到但未被引用」的來源：

- `used_source_ids`: 實際引用的來源 ID 列表
- `omitted_source_ids`: 檢索到但未引用的來源 ID 列表
- `extended_readings = [source for source in retrieved if source.id in omitted_source_ids]`

### 3. 數量驗證規則

- 延伸閱讀數量必須等於 `omitted_source_ids` 中在 `retrieved` 存在的來源數
- 所有來源都被引用時，延伸閱讀為空列表
- 檢索結果為空時，延伸閱讀為空列表

## 狀態欄位規格

### extended_readings_status

**有效值**: `"none" | "available" | "pending_evidence"`

**判定邏輯**:
```python
if extended_readings:
    extended_readings_status = "available"
elif confidence == "pending_evidence":
    extended_readings_status = "pending_evidence"
else:
    extended_readings_status = "none"
```

### pending_evidence_reason

**格式**: 人類可讀的失敗訊息，說明為何此論點缺乏足夠來源

**生成規則**:
```python
if confidence == "pending_evidence":
    if not used_ids and not extended_readings:
        pending_evidence_reason = "檢索無可用來源"
    elif not used_ids and extended_readings:
        pending_evidence_reason = "有候選來源但未被引用"
    elif openable_links_count < MIN_OPENABLE_LINKS and has_any_candidates:
        pending_evidence_reason = (
            f"可開啟連結不足 {MIN_OPENABLE_LINKS} 條"
            f"（實際 {openable_links_count} 條），無法滿足論點區塊最低要求"
        )
    elif text.startswith("【待補證】"):
        pending_evidence_reason = "來源與問題完全無關或無從作答"
    else:
        pending_evidence_reason = "引用來源不足或未通過驗證"
else:
    pending_evidence_reason = ""
```

### openable_links_count

**定義**: 論點區塊中真實可開啟連結（http/https）的總數，含引用來源與延伸閱讀

**計算規則**:
```python
# 收集所有候選來源（引用 + 延伸），按優先級排序
all_candidate_ids = list(used_ids) + list(omitted_ids)
# 去重但保持優先級（used_ids 優先）
seen = set()
prioritized_candidates = []
for sid in all_candidate_ids:
    if sid in seen:
        continue
    seen.add(sid)
    if sid in by_id_full:
        prioritized_candidates.append(sid)

# 計算可開啟連結數
prioritized_openable_urls = [
    by_id_full[sid].url
    for sid in prioritized_candidates
    if sid in by_id_full and is_openable_url(by_id_full[sid].url)
]
openable_links_count = len(prioritized_openable_urls)
```

### openable_links_status

**有效值**: `"none" | "insufficient" | "sufficient"`

**判定邏輯**:
```python
MIN_OPENABLE_LINKS = 2

if not has_any_candidates:
    openable_links_status = "sufficient"
elif directly_related_openable_count >= MIN_OPENABLE_LINKS:
    openable_links_status = "sufficient"
else:
    openable_links_status = "insufficient"
```

### openable_links_incomplete_reason

**格式**: 機器可解析的失敗訊息，指出缺失的欄位與原因

**生成規則**:
```python
if openable_links_status == "sufficient":
    openable_links_incomplete_reason = ""
else:
    related_cited_count = sum(sid in used_ids for sid in directly_related_openable_ids)
    missing_binding = (
        f"{argument_id}.extended_readings"
        if related_cited_count
        else f"{argument_id}.source_ids"
    )
    if openable_links_count == 0:
        openable_links_incomplete_reason = (
            f"{missing_binding} 缺失：無可開啟連結"
            "（引用來源與延伸閱讀均無有效 URL）"
        )
    elif openable_links_count < MIN_OPENABLE_LINKS:
        openable_links_incomplete_reason = (
            f"{missing_binding} 缺失：僅有 {openable_links_count} 條可開啟連結"
            f"（引用來源 {len(cited_urls)} 條、延伸閱讀 {len(extended_urls)} 條），"
            f"不足 {MIN_OPENABLE_LINKS} 條"
        )
    else:
        openable_links_incomplete_reason = (
            f"{missing_binding} 缺失：雖有 {openable_links_count} 條可開啟連結，"
            f"但與論點直接相關僅 {directly_related_openable_count} 條，"
            f"不足 {MIN_OPENABLE_LINKS} 條"
        )
```

## 跨格式一致性

### JSON 格式

```json
{
  "extended_readings": [
    {
      "source_id": "s1",
      "title": "來源標題",
      "url": "https://example.com",
      "level": "A",
      "distance": 0.3
    }
  ],
  "extended_readings_status": "available",
  "pending_evidence_reason": "",
  "openable_links_count": 3,
  "openable_links_status": "sufficient",
  "openable_links_incomplete_reason": ""
}
```

### Markdown 格式

```markdown
> **延伸閱讀**：
> - [s1] Level A 來源標題 (相關性: 0.30)
> **待補證原因**：原因說明
```

**正則式解析**:
```python
MD_EXTENDED_READING_RE = re.compile(r"> - \[(\S+?)\] Level (\S+) (.+)")
```

### DOCX 格式

- 延伸閱讀必須為獨立段落
- 必須在 supplement 段落之後
- 格式與 Markdown 類似

## 機械驗證規則

### pytest 驗證項目

1. **欄位契約穩定性**
   - 每筆 extended_reading 含所有必要欄位
   - 欄位型別符合契約
   - 狀態欄位只含有效值

2. **可抽取性**
   - 可從 binding_report / JSON / Markdown / DOCX 四種格式抽取
   - 跨格式內容一致

3. **數量正確性**
   - 延伸閱讀數 = omitted_source_ids 中在 retrieved 存在者
   - 跨格式數量一致

4. **分離性**
   - original segment 的 extended_readings 永遠為空
   - 延伸閱讀不在 supplement text 內文裡
   - 原稿逐字不變

5. **排序正確性**
   - 按 Level A > B > C > D 排序
   - 同層級按 distance 遞增排序

## 失敗訊息標準

### 訊息格式

所有失敗訊息必須遵循以下格式：

```
{argument_id}.{field_name} 缺失：{原因}
```

### 標準訊息模板

1. **無可開啟連結**:
   ```
   {argument_id}.source_ids 缺失：無可開啟連結（引用來源與延伸閱讀均無有效 URL）
   ```

2. **數量不足**:
   ```
   {argument_id}.extended_readings 缺失：僅有 {count} 條可開啟連結（引用來源 {cited} 條、延伸閱讀 {extended} 條），不足 {MIN_OPENABLE_LINKS} 條
   ```

3. **直接相關性不足**:
   ```
   {argument_id}.extended_readings 缺失：雖有 {total} 條可開啟連結，但與論點直接相關僅 {related} 條，不足 {MIN_OPENABLE_LINKS} 條
   ```

## 品質閘約束

延伸閱讀輸出必須遵守以下品質閘：

1. **原稿逐字不可變**: 延伸閱讀不得影響原稿內容
2. **無來源/【待補證】→ pending_evidence**: 缺乏來源時必須正確設定狀態
3. **只掛實際引用來源**: 延伸閱讀只含未引用的檢索來源
4. **至少 2 條真實可開啟連結**: 論點區塊需滿足最低連結要求

## 變更歷史

- **2026-07-28**: 初始版本，定義延伸閱讀格式規格
