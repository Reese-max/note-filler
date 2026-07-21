# 8 個 deselected 測試最終判讀（2026-07-21）

> **任務**：重新整理最終判讀，將 8 個 deselected 測試各自標記為「可接受未執行」或「需補測」，並要求每一項都能回指到具名測試檔、具名覆蓋案例與可重跑命令。
>
> **判讀基礎**：
> - 單獨執行結果：8/8 pass（來源：`docs/deselected-8-individual-judge-2026-07-19.md`）
> - 覆蓋映射：完整替代測試清單（來源：`docs/deselected-nodeid-evidence-mapping-2026-07-21.md`）
> - 排除機制：`@pytest.mark.integration` + `addopts -m 'not integration'`

---

## 判讀總表

| # | 判讀 | 測試檔案 | 具名覆蓋案例 | 可重跑命令 |
|---|------|----------|--------------|------------|
| 1 | **可接受未執行** | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `test_detect_domain_law`、`test_control_01_domain_legal_label_contract` | `pytest tests/test_domain.py::test_detect_domain_law -v` |
| 2 | **可接受未執行** | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `test_e2e_structural_invariants`、`test_e2e_offline_supplement_quality_boundary`、`test_run_pipeline_invariant`、`test_control_02` | `pytest tests/test_e2e_acceptance.py::test_e2e_structural_invariants -v` |
| 3 | **可接受未執行** | `tests/test_gap.py::test_detect_gaps_real_grok` | `test_detect_gaps_keeps_only_partial_and_missing`、`test_control_03_gap_uncovered_question_must_surface` | `pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing -v` |
| 4 | **可接受未執行** | `tests/test_llm.py::test_grok_pong_integration` | `test_grokclient_builds_request_body`、`test_control_04_grok_client_parse_and_endpoint_contract` | `pytest tests/test_llm.py::test_grokclient_builds_request_body -v` |
| 5 | **可接受未執行** | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `test_run_pipeline_invariant`、`test_run_pipeline_law_domain_runs_citation_check`、`test_run_pipeline_malformed_gap_output_falls_back_to_pending`、`test_control_05_pipeline_c6_pending_when_no_sources` | `pytest tests/test_pipeline.py::test_run_pipeline_invariant -v` |
| 6 | **可接受未執行** | `tests/test_questions.py::test_generate_questions_real_grok` | `test_generate_questions_splits_multiline_string`、`test_generate_questions_strips_and_drops_blank_lines`、`test_control_06_questions_clean_list_contract` | `pytest tests/test_questions.py::test_generate_questions_splits_multiline_string -v` |
| 7 | **可接受未執行** | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `test_retrieve_for_gap_law_domain_puts_level_A_before_B`、`test_search_law_sources_returns_level_A_law_articles`、`test_search_parses_source_with_full_content`、`test_search_reuses_mcp_session`、`test_search_transport_failure_returns_empty`、`test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot`、`test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`、`test_control_07`、`test_control_07b` | `pytest tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B -v` |
| 8 | **可接受未執行** | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `test_search_parses_source_with_full_content`、`test_search_reuses_mcp_session`、`test_search_transport_failure_returns_empty`、`test_control_08_twinkle_parsed_source_contract` | `pytest tests/test_twinkle.py::test_search_parses_source_with_full_content -v` |

**統計**：
- **可接受未執行**：8/8
- **需補測**：0/8

---

## 逐項詳細判讀

### 1. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

**判讀**：可接受未執行

**具名測試檔**：
- 主測試：`tests/test_domain.py::test_detect_domain_real_grok_returns_law`（L50-61）

**具名覆蓋案例**：
- `test_detect_domain_law`（L17-19）：以 FakeLLM 驗證 law 回傳契約
- `test_control_01_domain_legal_label_contract`：驗證法律標籤 + 雜訊 fallback

**可重跑命令**：
```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law -v --color=no
```

**判讀依據**：
- 單獨執行結果：pass（3.14s）
- 刻意分組：`@pytest.mark.integration` 被 `-m 'not integration'` 排除
- 重複覆蓋：有 2 個替代測試覆蓋確定性契約
- 殘留缺口：真 Grok 對法律文字的實際回應語意正確性（屬外部模型品質）

---

### 2. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

**判讀**：可接受未執行

**具名測試檔**：
- 主測試：`tests/test_e2e_acceptance.py::test_e2e_acceptance_real`（L244-299）

**具名覆蓋案例**：
- `test_e2e_structural_invariants`（L150-173）：涵蓋四項 §12 不變式
- `test_e2e_offline_supplement_quality_boundary`（L196-204）：離線補充品質邊界
- `test_e2e_minimal_quality_gates_offline_regression`（L211-240）：最小品質閘回歸
- `test_run_pipeline_invariant`：涵蓋 C6 不變式
- `test_control_02`：failing-first 對照

**可重跑命令**：
```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_structural_invariants -v --color=no
```

**判讀依據**：
- 單獨執行結果：pass（120.05s）
- 刻意分組：`@pytest.mark.integration` 被 `-m 'not integration'` 排除
- 重複覆蓋：8 個替代測試覆蓋所有不變式
- 殘留缺口：真 Grok + 真 Twinkle 組合下的端到端品質、Level A 路由穩定性

---

### 3. `tests/test_gap.py::test_detect_gaps_real_grok`

**判讀**：可接受未執行

**具名測試檔**：
- 主測試：`tests/test_gap.py::test_detect_gaps_real_grok`（L71-72）

**具名覆蓋案例**：
- `test_detect_gaps_keeps_only_partial_and_missing`（L17-29）：以 FakeLLM 驗證 covered 過濾
- `test_detect_gaps_calls_llm_exactly_once`（L32-36）：驗證 LLM 呼叫次數
- `test_detect_gaps_parse_failure_marks_all_missing`（L39-46）：解析失敗邊界
- `test_control_03_gap_uncovered_question_must_surface`：failing-first 對照

**可重跑命令**：
```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing -v --color=no
```

**判讀依據**：
- 單獨執行結果：pass（4.17s）
- 刻意分組：`@pytest.mark.integration` 被 `-m 'not integration'` 排除
- 重複覆蓋：2 個替代測試覆蓋解析/過濾/fallback
- 殘留缺口：真 Grok 對法律文本的缺口判斷品質

---

### 4. `tests/test_llm.py::test_grok_pong_integration`

**判讀**：可接受未執行

**具名測試檔**：
- 主測試：`tests/test_llm.py::test_grok_pong_integration`（L66-73）

**具名覆蓋案例**：
- `test_grokclient_builds_request_body`（L24-63）：monkeypatch 驗證 request body、Bearer、endpoint、timeout、response parse
- `test_control_04_grok_client_parse_and_endpoint_contract`：failing-first 對照

**可重跑命令**：
```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_llm.py::test_grokclient_builds_request_body -v --color=no
```

**判讀依據**：
- 單獨執行結果：pass（1.54s）
- 刻意分組：`@pytest.mark.integration` 被 `-m 'not integration'` 排除
- 重複覆蓋：2 個替代測試覆蓋請求構造與解析
- 殘留缺口：真實 TCP 連線與 proxy 實際回應格式

---

### 5. `tests/test_pipeline.py::test_run_pipeline_real_grok`

**判讀**：可接受未執行

**具名測試檔**：
- 主測試：`tests/test_pipeline.py::test_run_pipeline_real_grok`（L151-152）

**具名覆蓋案例**：
- `test_run_pipeline_invariant`（L56-95）：驗證 C6 不變式
- `test_run_pipeline_law_domain_runs_citation_check`（L98-123）：法規引用查核
- `test_run_pipeline_malformed_gap_output_falls_back_to_pending`（L126-148）：畸形輸出降級
- `test_control_05_pipeline_c6_pending_when_no_sources`：failing-first 對照

**可重跑命令**：
```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -v --color=no
```

**判讀依據**：
- 單獨執行結果：pass（80.14s）
- 刻意分組：`@pytest.mark.integration` 被 `-m 'not integration'` 排除
- 重複覆蓋：5 個替代測試覆蓋 C6、畸形輸出、法條查核、來源引用
- 殘留缺口：真 Grok 模型輸出下的 domain/questions/gaps 正確性

---

### 6. `tests/test_questions.py::test_generate_questions_real_grok`

**判讀**：可接受未執行

**具名測試檔**：
- 主測試：`tests/test_questions.py::test_generate_questions_real_grok`（L62-63）

**具名覆蓋案例**：
- `test_generate_questions_splits_multiline_string`（L17-29）：多行切割
- `test_generate_questions_strips_and_drops_blank_lines`（L32-38）：strip 與空行移除
- `test_generate_questions_empty_response_returns_empty_list`（L41-46）：空回應邊界
- `test_generate_questions_calls_llm_exactly_once`（L49-59）：呼叫次數
- `test_control_06_questions_clean_list_contract`：failing-first 對照

**可重跑命令**：
```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_questions.py::test_generate_questions_splits_multiline_string -v --color=no
```

**判讀依據**：
- 單獨執行結果：pass（7.85s）
- 刻意分組：`@pytest.mark.integration` 被 `-m 'not integration'` 排除
- 重複覆蓋：3 個替代測試覆蓋切割/淨空/邊界
- 殘留缺口：真 Grok 對法律文本的問題生成品質

---

### 7. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

**判讀**：可接受未執行

**具名測試檔**：
- 主測試：`tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`（L102-125）

**具名覆蓋案例**：
- `test_retrieve_for_gap_law_domain_puts_level_A_before_B`（L62-77）：排序契約
- `test_search_law_sources_returns_level_A_law_articles`：離線 law source
- `test_search_parses_source_with_full_content`：Twinkle 解析
- `test_search_reuses_mcp_session`：session 重用
- `test_search_transport_failure_returns_empty`：transport 安全降級
- `test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot`：vacuous pass 盲區
- `test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`：Level A 非空驗證
- `test_control_07`、`test_control_07b`：failing-first 對照

**可重跑命令**：
```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B -v --color=no
```

**判讀依據**：
- 單獨執行結果：pass（8.46s）
- 刻意分組：`@pytest.mark.integration` 被 `-m 'not integration'` 排除
- 重複覆蓋：9 個替代測試覆蓋排序/離線/解析/session/transport/盲區
- 殘留缺口：真實 Twinkle Hub I/O 與真 Grok 關鍵字抽取品質

---

### 8. `tests/test_twinkle.py::test_search_real_twinkle_hub`

**判讀**：可接受未執行

**具名測試檔**：
- 主測試：`tests/test_twinkle.py::test_search_real_twinkle_hub`（L122-135）

**具名覆蓋案例**：
- `test_search_parses_source_with_full_content`（L61-80）：全文 Source 解析
- `test_search_returns_empty_without_token`（L83-85）：無 token 邊界
- `test_search_reuses_mcp_session`（L88-105）：session 重用
- `test_search_transport_failure_returns_empty`（L108-114）：transport 安全降級
- `test_default_timeout_is_60`（L117-119）：timeout 預設值
- `test_control_08_twinkle_parsed_source_contract`：failing-first 對照

**可重跑命令**：
```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_twinkle.py::test_search_parses_source_with_full_content -v --color=no
```

**判讀依據**：
- 單獨執行結果：pass（2.74s）
- 刻意分組：`@pytest.mark.integration` 被 `-m 'not integration'` 排除
- 重複覆蓋：4 個替代測試覆蓋協議解析/session/transport
- 殘留缺口：真實 Twinkle Hub 服務可用性、session 相容性與網路逾時行為

---

## 統計摘要

| 判讀類別 | 數量 | 比例 |
|----------|------|------|
| 可接受未執行 | 8 | 100% |
| 需補測 | 0 | 0% |
| **合計** | **8** | **100%** |

---

## 驗證命令

```powershell
# 驗證 deselected 集合與 allowlist 一致
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest --collect-only -q --deselected-details --color=no

# 驗證替代測試可執行
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_domain.py::test_detect_domain_law -v --color=no
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_structural_invariants -v --color=no
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing -v --color=no
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_llm.py::test_grokclient_builds_request_body -v --color=no
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_pipeline.py::test_run_pipeline_invariant -v --color=no
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_questions.py::test_generate_questions_splits_multiline_string -v --color=no
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B -v --color=no
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_twinkle.py::test_search_parses_source_with_full_content -v --color=no

# 驗證 guard 測試通過
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_deselection_guard.py -v --color=no
```

---

## 參考證據來源

| 證據文件 | 路徑 | 內容 |
|----------|------|------|
| 單獨執行判定報告 | `docs/deselected-8-individual-judge-2026-07-19.md` | 8/8 pass 執行結果 |
| node id 映射對照 | `docs/deselected-nodeid-evidence-mapping-2026-07-21.md` | 排除依據與共享覆蓋證據 |
| 原最終判讀 | `docs/deselected-final-judgment-2026-07-18.md` | 三欄判定基礎 |
| allowlist | `tests/deselected_allowlist.json` | 機器可讀設定 |
| guard 測試 | `tests/test_deselection_guard.py` | 驗證機制 |

---

## 結論

全部 8 個 deselected 測試均標記為**可接受未執行**，理由如下：

1. **單獨執行通過**：8/8 測試在移除 deselection 條件後單獨執行全部 pass
2. **完整替代覆蓋**：每個測試都有對應的非 integration 替代測試，覆蓋確定性契約
3. **刻意分組排除**：排除機制為 `@pytest.mark.integration` + `addopts -m 'not integration'`，屬於策略性分組
4. **殘留缺口可控**：未覆蓋部分僅為外部服務（Grok/Twinkle）的實際 I/O 行為，屬 integration 邊界
5. **品質閘已守底線**：原稿逐字不可變、pending_evidence、只掛引用、法條離線查核等硬約束已由替代測試覆蓋

因此，無需補測任何非 integration 測試。
