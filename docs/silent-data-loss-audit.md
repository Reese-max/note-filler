# 靜默資料遺失分支審計報告

**日期**: 2026-07-23
**範圍**: 核心資料處理路徑（pipeline → parse → domain → questions → gap → retrieve → write → verify → correction → export）
**目標**: 找出所有「吞例外、`continue`、`return None`、提前結束、條件跳過」的分支，評估靜默遺失風險，鎖定最危險的 1~3 個分支

---

## 一、路徑 → 可能丟資料方式 → 現有測試覆蓋 對照表

### 核心管線 (pipeline.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `pipeline.py:49` `if seg.type != "supplement": continue` | 跳過非 supplement 段不跑法規引用檢查 | 低（設計正確） | PARTIAL — 只驗證被呼叫，未驗證實際降級 |
| `pipeline.py:52-53` `_verify_law_citations` 降級至 `pending_evidence` | 當 `check_law_citations` 回傳 `article_not_found` 時，把 `seg.confidence` 改為 `pending_evidence`。若此路徑失效，引用錯誤法條的補充段會維持 `verified` | **高** | PARTIAL — mock 回傳空 list，未驗證降級路徑 |

### 解析 (parse.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `parse.py:28` `_split_txt` 過濾空白段 | 空白段被丟棄，不進入 paragraphs | 低（設計正確） | YES |
| `parse.py:36` `_read_docx` 過濾空白段 | docx 空白段被丟棄 | 低（設計正確） | YES |
| `parse.py:47` 不支援副檔名 → `raise ValueError` | 例外中斷流程 | 低（明確錯誤） | NO — 無測試驗證 `.md` 等副檔名 |

### 領域分類 (domain.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `domain.py:39-40` 無法辨識 → `return "other"` | LLM 回應無法解析時，回退至 "other"，影響後續檢索策略（law/admin/exam 走 twinkle，other 走 web） | 中 | YES |

### 問題生成 (questions.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `questions.py:47` markdown 圍欄剝離 | 內容可能被截斷 | 低 | YES |
| `questions.py:52` `return []` JSON 類回應 | LLM 回傳 JSON 格式時，整批問題被丟棄，後續 gap=0，全部補充跳過 | **高**（但設計合理：禁止 LLM 偽造結構化問題） | YES |
| `questions.py:55` 過濾空行 | 空行被丟棄 | 低（設計正確） | YES |

### 缺口偵測 (gap.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `gap.py:58-59` `if not questions: return []` | 無問題時無缺口，整個補充流程跳過 | 中（跟隨上游） | YES |
| `gap.py:71-73` JSON 解析失敗 → `_all_missing` | 保守把全部問題當 missing，觸發補充（安全降級） | 低（保守策略） | YES |
| `gap.py:77-78` `if not isinstance(item, dict): continue` | LLM 回傳非 dict 元素（如純字串、數字）時，該元素被靜默跳過，對應問題不會產生 gap | 中 | **NO** |
| `gap.py:80-81` `status not in ("partial", "missing"): continue` | covered 問題被過濾，不產生補充 | 低（設計正確） | YES |

### 撰寫補充 (write.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `write.py:47-48` `【待補證】` → `used_source_ids=[]` | 無可用來源時提前回傳，used_source_ids 為空 | 低（設計正確） | YES |
| `write.py:60` 越界 `[^n]` 標記移除 | LLM 引用不存在的來源時，該標記從文字中移除，不計入 used | 低（設計正確） | YES |

### 交叉驗證 (verify.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| （無靜默遺失模式） | 所有路徑都有明確輸出 | — | YES（全面覆蓋） |

### 訂正文件組裝 (correction.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `correction.py:90-91` `w = written.get(q)` / `text = w.text if w else ""` | 當 gap question 不在 written dict 時（例如 write 階段異常），補充段以空文字、空來源列表產生，靜默遺失該 gap 的所有補充內容 | **高** | **NO** — 所有測試都提供完整的 written dict |
| `correction.py:93-95` 過濾 `used_ids` 到 `by_id` 存在者 | 若 retrieved 與 used_source_ids 不一致，部分來源被靜默丟棄 | 低（設計正確） | YES |

### 檢索路由 (retrieve/__init__.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `__init__.py:37-41` domain 分支決定檢索來源 | law/admin/exam 走 law+twinkle；other 走 web。若 domain 錯誤，走錯檢索路徑 | 中（跟隨上游 domain 判定） | YES |

### 法條搜尋 (retrieve/law_search.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `law_search.py:61-62` `if not keywords: return []` | LLM 無法抽取關鍵詞時，整批 law 來源為空 | 中（設計合理） | YES |
| `law_search.py:71` `if key in seen: continue` | 去重，重複條文被跳過 | 低（設計正確） | YES |

### Twinkle Hub (retrieve/twinkle.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `twinkle.py:208-209` token/query 檢查 → `return []` | 無 token 或空查詢時返回空結果 | 低（設計正確） | YES |
| `twinkle.py:219-221` **`except Exception: return []`** | Twinkle 服務任何例外（網路、逾時、協議錯誤）都被吞掉，返回空結果，Level B 來源靜默消失 | **中**（設計上的 resilience 策略，但可能 mask 真實故障） | YES（但只測了 TimeoutError，未覆蓋連線錯誤、協議錯誤等） |
| `twinkle.py:224-225` `if not isinstance(raw_hit, dict): continue` | 非 dict 的 hit 被跳過 | 中 | **NO** |
| `twinkle.py:226-227` `if source: sources.append(source)` | `_to_source` 回傳 None 時被跳過 | 低（title 為空的 hit 被合理跳過） | PARTIAL |

### 開放網路搜尋 (retrieve/web.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `web.py:60-61` query 提取失敗 → 退回原問題 | LLM 失敗時用原始問題搜尋，搜尋品質可能下降 | 低 | YES |
| `web.py:95-97` **`except Exception: return []`** | 網路搜尋任何例外都被吞掉，整批 web 來源為空 | **中**（resilience 策略） | YES |
| `web.py:103-104` `if not href: continue` | 無 URL 的搜尋結果被跳過 | 低 | **NO** |
| `web.py:107-108` fetch 失敗 → `continue` | 單頁抓取失敗跳過該頁 | 低（設計正確） | YES |
| `web.py:109-110` 全文過短 → `continue` | 導覽頁/短文被跳過 | 低（設計正確） | YES |
| `web.py:113-114` 分級例外 → `continue` | LLM 分級失敗跳過該頁 | 低 | **NO**（只測了 JSON 解析失敗，未測 _grade 本身拋例外） |
| `web.py:115-116` level not in (C,D) → `continue` | drop 級別被跳過 | 低（設計正確） | YES |

### 法規查索 (knowledge/law_lookup.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `law_lookup.py:119-120` `if not pcode or not articles: continue` | build_law_index 時，無 pcode 或無條文的 markdown 檔被靜默跳過，該法規不會進入索引 | **中** | **NO** |
| `law_lookup.py:156` `lookup_article` 查無 → `None` | 明確回傳 None，由呼叫端決定 | 低 | YES |

### 法規引用核對 (knowledge/law_citation_check.py)

| 路徑 (檔案:行) | 丟資料方式 | 風險 | 測試覆蓋 |
|---|---|---|---|
| `law_citation_check.py:52-53` `if not last_full: continue` | 指代詞（同法/本法）前無完整法規名時，該引用被跳過不核對 | 中 | **NO** |
| `law_citation_check.py:71` `continue` 法規名不在 DB | 簡稱/未收錄法規的引用被跳過不核對（不誤報） | 低（設計正確） | YES |

---

## 二、鎖定最可能造成靜默遺失的 Top 3 分支

### 🔴 #1：`correction.py:90-91` — gap question 不在 written dict 時產生空補充段

```python
w = written.get(q)
text = w.text if w else ""
```

**觸發條件**：pipeline 在 `write_supplement` 階段拋出未預期例外（如 LLM timeout、網路中斷），導致該 gap 的 written 結果未寫入 dict。或者 written dict 因任何原因缺少某個 gap question 的 key。

**丟資料方式**：補充段以空文字 `""` 和空來源列表 `[]` 產生。用戶看到的訂正稿中，該 gap 的補充段是空的，但不會有任何錯誤提示或警告。

**風險評估**：**高** — 這是核心管線中的「黑洞」，一旦觸發，gap 對應的補充完全消失，且無 log、無例外、無 fallback。

**測試覆蓋**：**無** — 所有 `test_correction.py` 的測試都提供完整的 `written` dict，從未測試 `written.get(q)` 返回 None 的路徑。

---

### 🔴 #2：`pipeline.py:44-53` + `law_citation_check.py:41-85` — 法規引用核對的降級路徑

```python
# pipeline.py
if any(f.get("kind") == "article_not_found" for f in findings):
    seg.confidence = "pending_evidence"
```

```python
# law_citation_check.py — 多個跳過路徑
if law in _ANAPHORA:
    if not last_full:
        continue          # 指代詞無法解析 → 跳過
    law = last_full
# ...
if not lookup.law_exists(law):
    continue              # 法規名不在 DB → 跳過
```

**觸發條件**：
1. 指代詞（同法/本法）前無完整法規名 → 引用被跳過不核對
2. 法規名簡稱或未收錄 → 引用被跳過不核對
3. 罰則金額比對（`_MONEY_RE`）無測試覆蓋 → 不一致可能被漏掉

**丟資料方式**：
- 情境 1：含「同法第94條」的引用，若前文沒有完整法規名，該引用完全不被核對，錯誤法條不會被降級為 `pending_evidence`，維持 `verified` 狀態
- 情境 2：法規名在 DB 中不存在（簡稱/新法），引用不被核對，可能含有幻覺法條
- 情境 3：罰則金額不一致但 `_MONEY_RE` 未觸發比對，錯誤金額被視為正確

**風險評估**：**高** — 法規引用核對是防止法規幻覺的最後一道防線。此路徑的未覆蓋分支意味著幻覺法條可能以 `verified` 狀態出現在最終文件中。

**測試覆蓋**：
- 降級路徑（`article_not_found` → `pending_evidence`）：**PARTIAL** — mock 回傳空 list
- 指代詞解析：**無**
- 罰則比對：**無**
- `annotate_law_mismatches` 去重：**無**

---

### 🟡 #3：`twinkle.py:219-221` + `web.py:95-97` — 外部服務例外的廣泛吞沒

```python
# twinkle.py:219
except Exception as exc:  # noqa: BLE001
    logger.warning("twinkle-hub 查詢失敗,降級為空結果: %s", exc)
    return []

# web.py:95
except Exception as exc:  # noqa: BLE001
    logger.warning("開放網路搜尋失敗,降級為空結果: %s", exc)
    return []
```

**觸發條件**：外部服務（Twinkle Hub / DuckDuckGo / trafilatura）出現任何例外，包括：網路中斷、逾時、DNS 失敗、SSL 錯誤、服務端 500、協議不相容、記憶體不足等。

**丟資料方式**：
- Twinkle 例外 → Level B 來源全部為空，gap 只有 Level A（法條）或無來源
- Web 例外 → Level C/D 來源全部為空，other 領域的 gap 完全無來源
- 補充文字可能變成「【待補證】...」，但用戶未必注意到

**風險評估**：**中** — 這是 resilience 設計（不因外部服務中斷而中斷主流程），但缺乏：
1. 區分「暫時性故障」vs「永久性故障」的機制
2. 在最終文件中標記「部分來源因服務不可用而缺失」的機制
3. 多次連續失敗的告警/熔斷

**測試覆蓋**：
- Twinkle：YES（但只測 TimeoutError，未覆蓋連線拒絕、SSL 錯誤、協議不相容）
- Web：YES（但只測 RuntimeError，未覆蓋 DNS 失敗、逾時等）

---

## 三、其他值得注意的未覆蓋分支

| 模式 | 檔案:行 | 風險 | 建議 |
|---|---|---|---|
| `gap.py:77-78` 非 dict 元素被跳過 | gap.py | 中 | 補測試：JSON 陣列含字串/數字元素 |
| `twinkle.py:224-225` 非 dict hit 被跳過 | twinkle.py | 中 | 補測試：hits 含非 dict 元素 |
| `web.py:103-104` 無 href 被跳過 | web.py | 低 | 補測試：hit 缺少 href |
| `web.py:113-114` 分級例外被跳過 | web.py | 低 | 補測試：_grade 拋例外 |
| `law_lookup.py:119-120` build_law_index 跳過無 pcode 檔 | law_lookup.py | 中 | 補測試：語料含無 pcode 檔 |
| `parse.py:47` 不支援副檔名 | parse.py | 低 | 補測試：`.md` 副檔名 |

---

## 四、建議優先序

1. **補 `correction.py` 的 `written.get(q)` 為 None 路徑測試** — 最高風險、零覆蓋，且可能隱藏真實 bug
2. **補 `law_citation_check.py` 的指代詞解析 + 罰則比對測試** — 防止法規幻覺的最後防線有缺口
3. **強化外部服務例外的測試深度** — 確認各種網路故障模式都被正確降級
4. **補 `gap.py` / `twinkle.py` 的非 dict 元素跳過測試** — 防禦 LLM 或外部 API 回傳非預期格式
