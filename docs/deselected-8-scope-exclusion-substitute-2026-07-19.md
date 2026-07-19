# 8 個 deselected 測試 node id 對照重整（2026-07-19）

> 任務：重新整理 8 個測試的「node id → 功能範圍 → 排除依據 → 替代覆蓋」對照，僅保留可由實際測試輸出和檔案內容直接證實的項目，將無法證實者標記為待補測。

## 證據範圍與判定規則

本報告只採用本 repo 內可直接檢查的兩類證據：

1. **實際 pytest 輸出**：本次重跑 collection，確認預設集合為 `137/145 tests collected (8 deselected)`，8 個 deselected node id 逐項回報 `reason: deselected by -m 'not integration'`；另以 `-m integration` 且覆寫 addopts 移除預設 mark 過濾後，確認選入的 8 個 node id 與下表相同。
2. **檔案內容**：逐項引用測試檔內 `@pytest.mark.integration`、runtime skip 條件、integration 測試本體斷言，以及 `tests/deselected_allowlist.json` / `docs/pytest-audit/deselected-individual-results-2026-07-19.json` 中可直接讀到的 substitute node id 與獨立實跑結果。

未納入舊報告中的模糊結論、風險推論或「替代覆蓋更廣」等無法由本次輸出與檔案內容逐字核對的說法。若替代測試只能證明 deterministic contract，但不能證明真 Grok / 真 Twinkle / 真網路服務行為，該部分在「待補測」欄明示。

## 本次實際 collection 輸出

### 預設 collection + deselected details

命令：

```powershell
call "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest --collect-only -q --deselected-details --color=no
```

關鍵輸出：

```text
============================= deselected details ==============================
tests/test_domain.py::test_detect_domain_real_grok_returns_law | reason: deselected by -m 'not integration'
tests/test_e2e_acceptance.py::test_e2e_acceptance_real | reason: deselected by -m 'not integration'
tests/test_gap.py::test_detect_gaps_real_grok | reason: deselected by -m 'not integration'
tests/test_llm.py::test_grok_pong_integration | reason: deselected by -m 'not integration'
tests/test_pipeline.py::test_run_pipeline_real_grok | reason: deselected by -m 'not integration'
tests/test_questions.py::test_generate_questions_real_grok | reason: deselected by -m 'not integration'
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke | reason: deselected by -m 'not integration'
tests/test_twinkle.py::test_search_real_twinkle_hub | reason: deselected by -m 'not integration'
137/145 tests collected (8 deselected) in 0.51s
```

### 僅 integration selector 的 collection

命令：

```powershell
call "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest -m integration --collect-only -q -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" --color=no
```

關鍵輸出：

```text
tests/test_domain.py::test_detect_domain_real_grok_returns_law
tests/test_e2e_acceptance.py::test_e2e_acceptance_real
tests/test_gap.py::test_detect_gaps_real_grok
tests/test_llm.py::test_grok_pong_integration
tests/test_pipeline.py::test_run_pipeline_real_grok
tests/test_questions.py::test_generate_questions_real_grok
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke
tests/test_twinkle.py::test_search_real_twinkle_hub

8/145 tests collected (137 deselected) in 0.74s
```

### 排除規則檔案證據

`pyproject.toml` `[tool.pytest.ini_options]` 直接設定：

```toml
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

## 對照表

| # | node id | 功能範圍（僅依測試本體與檔案內容） | 排除依據 | 替代覆蓋（僅列 allowlist 具名 node id） | 待補測 / 未由替代覆蓋直接證實 |
|---:|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | 真 Grok `GrokClient()` 對明顯刑法文字呼叫 `detect_domain`，斷言回傳 `law`（`tests/test_domain.py`）。 | 預設輸出：`reason: deselected by -m 'not integration'`；檔案：`pyproject.toml` addopts 含 `-m 'not integration'`，測試有 `@pytest.mark.integration`；另有 `skipif(not _grok_reachable())`。 | `tests/test_domain.py::test_detect_domain_law`；`tests/test_excluded_failing_controls.py::test_control_01_domain_legal_label_contract`。 | 待補測：替代測試不真打 Grok；「真 Grok 對法律文字穩定回 `law`」仍待 integration 補測。 |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | 真 Grok + 真 Twinkle token + `LawLookup` 的端到端流程；測試本體讀 fixture、檢查 `LAW_DB`、`_grok_up()`、`_twinkle_ready()`，並建 `_Grok0` 與 `TwinkleClient`。 | 預設輸出：同上；檔案：`@pytest.mark.integration`；函式內缺 `data/law_index.db`、grok 或 token 時 `pytest.skip`。 | `tests/test_e2e_acceptance.py::test_e2e_structural_invariants`；`tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary`；`tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression`；`tests/test_pipeline.py::test_run_pipeline_invariant`；`tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`；`tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`；`tests/test_correction.py::test_retrieved_five_but_only_two_cited`；`tests/test_excluded_failing_controls.py::test_control_02_e2e_offline_quality_gates`。 | 待補測：替代測試以離線/fake 前置覆蓋品質閘；真 Grok + 真 Twinkle 組合、端到端外部服務品質仍待 integration 補測。 |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | 真 Grok 對「行政處分定義筆記 + 未涵蓋罰鍰裁量問題」呼叫 `detect_gaps`，斷言輸出為 `Gap` 清單、狀態皆為 `partial`/`missing`，且明顯未涵蓋問題出現在缺口清單。 | 預設輸出：同上；檔案：`@pytest.mark.integration` 與 `skipif(not _grok_reachable())`。 | `tests/test_gap.py::test_detect_gaps_keeps_only_partial_and_missing`；`tests/test_excluded_failing_controls.py::test_control_03_gap_uncovered_question_must_surface`。 | 待補測：替代測試使用 `FakeLLM`；真 Grok 對法律文本缺口判斷品質仍待 integration 補測。 |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | 真 `GrokClient()` 發送 `Reply with exactly one word: PONG`，斷言回應含 `PONG`。 | 預設輸出：同上；檔案：`@pytest.mark.integration` 與 `skipif(not _grok_reachable())`。 | `tests/test_llm.py::test_grokclient_builds_request_body`；`tests/test_excluded_failing_controls.py::test_control_04_grok_client_parse_and_endpoint_contract`。 | 待補測：替代測試 monkeypatch HTTP；真 proxy TCP 連線與 proxy 實際回應仍待 integration 補測。 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | 真 Grok + `FakeTwinkle` + `FakeLaw` 執行 `run_pipeline`；斷言 `doc.original` 存在、`segments` 是 list，且無來源 supplement 必為 `pending_evidence`。 | 預設輸出：同上；檔案：`@pytest.mark.integration` 與 `skipif(not _grok_reachable())`。 | `tests/test_pipeline.py::test_run_pipeline_invariant`；`tests/test_pipeline.py::test_run_pipeline_malformed_gap_output_falls_back_to_pending`；`tests/test_pipeline.py::test_run_pipeline_law_domain_runs_citation_check`；`tests/test_correction.py::test_retrieved_five_but_only_two_cited`；`tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources`。 | 待補測：替代測試不使用真 Grok；真模型輸出下完整 pipeline 穩定性仍待 integration 補測。 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | 真 Grok 對個資法筆記呼叫 `generate_questions`；斷言回傳非空字串清單，且問題不以 `[` 或 `{` 開頭。 | 預設輸出：同上；檔案：`@pytest.mark.integration` 與 `skipif(not _grok_reachable())`。 | `tests/test_questions.py::test_generate_questions_splits_multiline_string`；`tests/test_questions.py::test_generate_questions_strips_and_drops_blank_lines`；`tests/test_excluded_failing_controls.py::test_control_06_questions_clean_list_contract`。 | 待補測：替代測試使用 `FakeLLM`；真 Grok 問題生成品質與非空穩定性仍待 integration 補測。 |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | 真 `TwinkleClient` + `LawLookup` + 真 Grok keyword，對 law gap 呼叫 `retrieve_for_gap`；斷言每筆為 `Source`、level 為 `A`/`B`，且排序 keys 已升序。 | 預設輸出：同上；檔案：`@pytest.mark.integration`、`skipif(not LAW_DB.exists())`、`skipif(not _grok_reachable())`，函式內缺 `TWINKLE_HUB_TOKEN` 時 `pytest.skip`。 | `tests/test_retrieve.py::test_retrieve_for_gap_law_domain_puts_level_A_before_B`；`tests/test_law_search.py::test_search_law_sources_returns_level_A_law_articles`；`tests/test_twinkle.py::test_search_parses_source_with_full_content`；`tests/test_twinkle.py::test_search_reuses_mcp_session`；`tests/test_twinkle.py::test_search_transport_failure_returns_empty`；`tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot`；`tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`；`tests/test_excluded_failing_controls.py::test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot`；`tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous`。 | 待補測：替代測試可覆蓋排序、離線 law source、Twinkle 解析與 vacuous empty 盲區；真 Twinkle Hub I/O 與真 Grok keyword 抽取仍待 integration 補測。 |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | 真 `TwinkleClient(token=...)` 搜尋「道路交通管理處罰條例」；斷言回傳 list，且每筆 `Source` 的 level 為 `A`/`B`、content 非空、`fetched_date` 為今日。 | 預設輸出：同上；檔案：`@pytest.mark.integration`，函式內缺 `TWINKLE_HUB_TOKEN` 時 `pytest.skip`。 | `tests/test_twinkle.py::test_search_parses_source_with_full_content`；`tests/test_twinkle.py::test_search_reuses_mcp_session`；`tests/test_twinkle.py::test_search_transport_failure_returns_empty`；`tests/test_excluded_failing_controls.py::test_control_08_twinkle_parsed_source_contract`。 | 待補測：替代測試 mock MCP / timeout；真 Twinkle Hub 服務可用性、session 相容性與實際搜尋結果仍待 integration 補測。 |

## 獨立實跑結果（既有落盤證據）

`docs/pytest-audit/deselected-individual-results-2026-07-19.json` 目前記錄 8 個 node id 在移除預設 deselection 後的獨立結果皆為 `status: "pass"`、`exit_code: 0`，且 `skip_reason: null`、`fail_hint: null`。本報告只引用其「已實跑且 pass」的事實；不把它延伸解讀為替代測試已覆蓋外部服務風險。

| node id | 既有獨立結果 |
|---|---|
| `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `pass`, exit `0` |
| `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `pass`, exit `0` |
| `tests/test_gap.py::test_detect_gaps_real_grok` | `pass`, exit `0` |
| `tests/test_llm.py::test_grok_pong_integration` | `pass`, exit `0` |
| `tests/test_pipeline.py::test_run_pipeline_real_grok` | `pass`, exit `0` |
| `tests/test_questions.py::test_generate_questions_real_grok` | `pass`, exit `0` |
| `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `pass`, exit `0` |
| `tests/test_twinkle.py::test_search_real_twinkle_hub` | `pass`, exit `0` |

## 結論

1. 目前可由實際 collection 輸出直接證實：預設 pytest 會 deselect 的 8 個 node id 正是上表 8 項，且排除理由逐項都是 `-m 'not integration'`。
2. 可由檔案內容直接證實：8 項皆標記 `@pytest.mark.integration`；`pyproject.toml` 預設 addopts 含 `-m 'not integration'`；部分測試另有 runtime skip，但那不是本次預設 collection deselect 的直接原因。
3. 替代覆蓋僅列 `tests/deselected_allowlist.json` 具名的 substitute node id；其是否可收集與執行由既有 `tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable` 守住。
4. 無法由替代測試直接證實的外部行為已逐項標記為待補測，尤其是真 Grok 語意品質、真 Twinkle Hub I/O、proxy TCP 連線與真端到端外部服務組合。
