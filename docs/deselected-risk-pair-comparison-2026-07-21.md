# Deselected 最高風險對：#7 vs #8 共用路徑對照表

> **日期**：2026-07-21
>
> **鎖定對象**：8 個 deselected 測試中風險最高的兩筆
>
> **判定依據**：`docs/deselected_tests_report.md`、`tests/deselected_allowlist.json`

---

## 為何 #7 + #8 是最高風險對

| 指標 | #7 `test_retrieve_for_gap_real_twinkle_smoke` | #8 `test_search_real_twinkle_hub` |
|------|-----------------------------------------------|-------------------------------------|
| 風險等級 | **Medium**（已紀錄驗證盲區） | Medium（與 #7 共享 same correctness concern） |
| 驗證盲區類型 | smoke 斷言 vacuous pass on empty | 無 vacuous pass，但為 #7 的底層服務 |
| 是否有產品缺陷 | NOT-REPRODUCIBLE（law Level A 路徑健康） | NOT-REPRODUCIBLE（Twinkle 正常回傳） |

**選擇理由**：#7 被標記為「true verification gap」（vacuous pass），#8 是 #7 依賴的底層 Twinkle Hub 服務。兩者共享相同的 correctness concern（real Twinkle Hub I/O），且 #8 的替代覆蓋只有 4 個（最少），殘留缺口含「真實 Twinkle Hub 服務可用性 + session 相容性 + 網路逾時」。

---

## 測試本體對照

| 維度 | #7 `test_retrieve_for_gap_real_twinkle_smoke` | #8 `test_search_real_twinkle_hub` |
|------|-----------------------------------------------|-------------------------------------|
| **檔案位置** | `tests/test_retrieve.py:102-125` | `tests/test_twinkle.py:141-154` |
| **覆蓋函式** | `note_filler.retrieve.retrieve_for_gap` | `note_filler.retrieve.twinkle.TwinkleClient.search` |
| **呼叫鏈** | `retrieve_for_gap` → `TwinkleClient.search` + `LawLookup.search_articles` + `GrokClient.complete` | `TwinkleClient.search` only |
| **測試目的** | 證明 law 領域 retrieve 的 **完整組合路徑** 產出合法排序結果 | 證明 Twinkle Hub MCP 的 **底層搜尋** 能解析合法 Source |
| **前提條件數** | 4（law_index.db + grok + twinkle token + integration marker） | 1（twinkle token + integration marker） |
| **Skip guard** | 4 層（collection + 3 runtime skipif） | 2 層（collection + runtime skip） |

---

## 斷言對照（關鍵差異）

| #7 斷言 | #8 斷言 | 是否重疊 |
|---------|---------|---------|
| `all(isinstance(s, Source) for s in out)` | `isinstance(src, Source)` per item | **同質**：都驗證 Source 類型 |
| `all(s.level in ("A", "B") for s in out)` | `src.level in ("A", "B")` per item | **同質**：都驗證 level 範圍 |
| `keys == sorted(keys)` 排序不變式 | （無排序斷言） | **#7 獨有**：驗證 (rank, distance) 升序 |
| （無全量斷言） | `src.content.strip()` 全文非空 | **#8 獨有**：驗證 content 非空 |
| （無日期斷言） | `src.fetched_date == date.today()` | **#8 獨有**：驗證 fetched_date 當日 |

**結論**：#7 的斷言是 #8 的超集的一半（#7 驗排序，#8 驗 content/date），但 **#7 的三道斷言全為 vacuous pass on empty**，這正是已紀錄的驗證盲區。

---

## 參數化資料對照

| 維度 | #7 | #8 |
|------|----|----|
| **搜尋問題** | `"行政處分附款的容許界限為何?"` | `"道路交通管理處罰條例"` |
| **搜尋限制 n** | 3（預設） | 3（明確指定） |
| **Domain** | `"law"` | N/A（直接呼叫 TwinkleClient） |
| **LLM 參與** | 有（GrokClient 抽 keyword） | 無 |
| **LawLookup 參與** | 有（真 LawLookup + law_index.db） | 無 |
| **TwinkleClient** | 真實（TwinkleClient(token)） | 真實（TwinkleClient(token)） |

**結論**：兩者使用 **相同的 TwinkleClient(token)** 實例化方式，但 #7 還額外依賴 GrokClient + LawLookup。搜尋問題不同但都屬法制領域。

---

## 共享 Fixture 對照

| Fixture / Dependency | #7 | #8 | 共享？ |
|----------------------|----|----|--------|
| `TWINKLE_HUB_TOKEN` env var | 讀取 | 讀取 | **是** |
| `data/law_index.db` | 讀取（LawLookup） | 不使用 | 否 |
| `127.0.0.1:8318` grok proxy | 讀取（GrokClient） | 不使用 | 否 |
| `@pytest.mark.integration` | 有 | 有 | **是** |
| `Source` model import | 有 | 有 | **是** |
| `TwinkleClient` class | 有 | 有 | **是** |

---

## 確認：是否為同一 correctness 問題

| 判斷標準 | 結果 |
|----------|------|
| 是否覆蓋同一底層函式？ | **是** — `TwinkleClient.search` |
| 是否共享相同的外部服務依賴？ | **是** — Twinkle Hub MCP |
| 是否測試相同的 correctness concern？ | **是** — real Twinkle Hub 是否能產出合法 Source |
| 是否有不同的驗證缺口？ | **是** — #7 有 vacuous pass 盲區（已紀錄）；#8 有 session 相容性缺口 |
| 替代覆蓋是否互補？ | **是** — #7 的 9 個替代含 vacuous pass 證明；#8 的 4 個替代含 session/transport |

**判定**：兩者 **為同一 correctness 問題**（real Twinkle Hub 的 Source 產出正確性），差異在於：
- #7 是 **組合路徑**（retrieve_for_gap = law + twinkle + llm），驗證盲區為 vacuous pass on empty
- #8 是 **底層路徑**（TwinkleClient.search），驗證缺口為真實服務可用性

---

## 最小對照表（機器可讀）

| 屬性 | #7 `test_retrieve_for_gap_real_twinkle_smoke` | #8 `test_search_real_twinkle_hub` |
|------|-----------------------------------------------|-------------------------------------|
| `test_id` | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `tests/test_twinkle.py::test_search_real_twinkle_hub` |
| `source_file` | `tests/test_retrieve.py:102-125` | `tests/test_twinkle.py:141-154` |
| `covered_fn` | `note_filler.retrieve.retrieve_for_gap` | `note_filler.retrieve.twinkle.TwinkleClient.search` |
| `shared_fn` | `TwinkleClient.search` (indirect) | `TwinkleClient.search` (direct) |
| `external_dep` | `TWINKLE_HUB_TOKEN` + `127.0.0.1:8318` + `data/law_index.db` | `TWINKLE_HUB_TOKEN` |
| `shared_dep` | `TWINKLE_HUB_TOKEN` (Twinkle Hub MCP) | `TWINKLE_HUB_TOKEN` (Twinkle Hub MCP) |
| `correctness_concern` | real Twinkle Hub Source 產出正確性 | real Twinkle Hub Source 產出正確性 |
| `design_gap` | vacuous pass on empty (C7-verification) | 无 vacuous pass |
| `substitute_count` | 9 | 4 |
| `risk_level` | Medium (verification gap) | Medium (shared concern) |
| `is_same_correctness_issue` | **True** | **True** |

---

## 驗證命令

```powershell
# 驗證 #7 替代測試（排序契約）
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B -v --color=no

# 驗證 #8 替代測試（Source 解析）
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_twinkle.py::test_search_parses_source_with_full_content -v --color=no

# 驗證 vacuous pass 盲區（#7 特有）
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_exclusion_correctness_blind_spot.py -v --color=no

# 驗證 Level A 非空路徑（#7 產品路徑）
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract -v --color=no
```

---

## 參考來源

| 來源 | 路徑 |
|------|------|
| deselected allowlist | `tests/deselected_allowlist.json` |
| final judgment | `docs/deselected-final-judgment-2026-07-21.md` |
| blind spot test | `tests/test_exclusion_correctness_blind_spot.py` |
| failing controls | `tests/test_excluded_failing_controls.py:300-410` |
| source: retrieve_for_gap | `src/note_filler/retrieve/__init__.py` |
| source: TwinkleClient | `src/note_filler/retrieve/twinkle.py` |
| source: search_law_sources | `src/note_filler/retrieve/law_search.py` |
