# 8 個 deselected 測試 correctness 路徑等價覆蓋審計

> 日期：2026-07-21
> 範圍：`tests/deselected_allowlist.json` 的 8 個 `integration` node ID
> 機器索引：`docs/pytest-audit/deselected-correctness-path-equivalence-2026-07-21.json`

## 結論

逐一比對測試本體、同檔兄弟案例、實際共用 fixture／helper、產品呼叫鏈與既有替代測試後，共拆出 **23 條可觀察 correctness 路徑**：

- **15 條已有等價覆蓋**。
- **6 條只剩一個有效覆蓋點，判定「回歸保護不足」**。
- **2 條沒有有效覆蓋點**：#7、#8 都可在真 Twinkle 回空時假綠。
- 只有 #4 `test_grok_pong_integration` 沒有 singleton 或未覆蓋路徑；其 HTTP 建構／解析有離線替代，真 proxy completion 另被 6 個 Grok integration 呼叫點重複觸發。

既有 `requirements-test-coverage-2026-07-19.json` 對 **deterministic 程式分支** 的 13 項結論仍成立；本報告採更嚴格的「斷言是否真的觀察結果」粒度，因此不把 fake 的乾淨 canned output 當成真模型語意等價，也不把空集合上的 `all()`／`for` 當成 coverage point。

## 判定規則

一個等價覆蓋點必須同時符合：

1. 抵達相同產品分支，而非只 import 或呼叫同名函式。
2. 斷言相同結果／安全閘，而非只證明「沒有拋例外」。
3. `all(...)`、排序或 `for` 若在空集合仍成功，不算非空／外部成功路徑的覆蓋。
4. 真模型語意、真 TCP、真 MCP 與離線 fake 分開；fake 可覆蓋 parser／mapping，不能冒充外部語意或服務相容性。
5. 全套測試只有一個有效觀察點時，使用使用者指定標籤 **「回歸保護不足」**；零點則標 **「未覆蓋」**。

## 逐項判定

| # | 目標測試 | 已有等價覆蓋 | singleton／零覆蓋路徑 | 判定與最小補測位置 |
|---|---|---|---|---|
| 1 | `test_detect_domain_real_grok_returns_law` | canonical label 解析、標點／大小寫、非法輸出 fallback | 真 Grok 對刑法文字判成 `law` 只有本測觀察 | **回歸保護不足**；在 `tests/test_domain.py` 增加 `test_detect_domain_real_grok_representative_domains`，參數化四類代表文本 |
| 2 | `test_e2e_acceptance_real` | 原稿不可變、pending gate、只掛實際引用、離線法條查核、輸出格式、deterministic Level A／註腳品質 | 真 Grok + 真 Twinkle + 真 LawLookup 產生 grounded supplement 只有本測觀察 | **回歸保護不足**；最小位置是 `tests/test_write.py`，用固定 Source 新增真 Grok writer integration，避免複製整個高成本 e2e |
| 3 | `test_detect_gaps_real_grok` | JSON 解析、`covered` 過濾、`partial/missing` 結構與問題傳遞 | 真 Grok 判定「罰鍰裁量基準」未涵蓋只有本測觀察 | **回歸保護不足**；在 `tests/test_gap.py` 增加有 covered/missing 對的真模型 semantic matrix |
| 4 | `test_grok_pong_integration` | POST／Bearer／model／messages／timeout／response parse；真 proxy completion 有 7 個 integration 呼叫點 | 無 | **已有等價覆蓋**；`PONG` 是健康探針 oracle，不另算產品分支 |
| 5 | `test_run_pipeline_real_grok` | 同一 `note_path` 的 DOCX orchestration、C6 pending 與 malformed fallback | 本測未斷言 `supplement` 非空；真 Grok 真的走到 retrieve/write 目前只由 #2 的 `assert supplements` 觀察 | **回歸保護不足**；在既有 `test_run_pipeline_real_grok` 的 C6 迴圈前加 supplement 非空斷言 |
| 6 | `test_generate_questions_real_grok` | 單次 completion、`splitlines()`、strip、空行移除 | JSON-shaped 不受信輸出不得流入下游只有本測對真回應觀察；`control_06` 餵乾淨 canned output，不等價 | **回歸保護不足**；在 `tests/test_questions.py` 加 `test_generate_questions_rejects_json_shaped_response` |
| 7 | `test_retrieve_for_gap_real_twinkle_smoke` | 真 LawLookup Level A 非空已有多個預設測試 | 混合 A/B 排序只由一個 fake 測試有效觀察；真 Twinkle 是否貢獻 Level B 則零覆蓋 | **回歸保護不足**（混合排序）且 **未覆蓋**（真 B）；在既有 smoke 加非空與同時含 A/B 的斷言 |
| 8 | `test_search_real_twinkle_hub` | MCP/session/SSE/Source mapping 與 transport safe-degrade 有離線兄弟案例 | 真 Hub 成功回至少一筆：`results == []` 時 `for src in results` 不執行，測試仍 PASS | **未覆蓋**；在 `isinstance(results, list)` 後立即加 `assert results` |

## 6 條「回歸保護不足」

| 路徑 ID | 唯一有效覆蓋點 | 為何替代案例不等價 | 最小補測位置 |
|---|---|---|---|
| `T1-P2` | `test_detect_domain_real_grok_returns_law` | `FakeLLM(["law"])` 只驗 parser，沒有驗模型看懂輸入 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` |
| `T2-P6` | `test_e2e_acceptance_real` | 離線 e2e 共用 canned writer，永遠預先給合法 `[^1][^2]` | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` |
| `T3-P2` | `test_detect_gaps_real_grok` | canned JSON 已直接宣告 missing，只驗傳遞與過濾 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` |
| `T5-P3` | `test_e2e_acceptance_real` | `test_run_pipeline_real_grok` 的 supplement loop 可在零 gap 時 vacuous pass | 直接補強 `tests/test_pipeline.py::test_run_pipeline_real_grok` |
| `T6-P2` | `test_generate_questions_real_grok` | 離線 siblings 都餵乾淨多行字串，沒有挑戰 JSON-shaped trust boundary | `tests/test_questions.py::test_generate_questions_rejects_json_shaped_response` |
| `T7-P1` | `test_retrieve_for_gap_law_domain_puts_level_A_before_B` | 真 smoke 沒有要求非空或同時含 A/B；`test_search_law_sources_returns_level_A_law_articles` 只驗 A，不能成為混合排序第二點 | 直接補強 `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` |

## 2 條未覆蓋路徑

### #7：組合 smoke 沒有證明 Twinkle 有貢獻

`test_retrieve_for_gap_real_twinkle_smoke` 只有：

```python
assert all(isinstance(s, Source) for s in out)
assert all(s.level in ("A", "B") for s in out)
assert keys == sorted(keys)
```

三者對 `out == []` 都成功；即使 `out` 只有 LawLookup 的 Level A，Twinkle 完全失效也成功。既有 Level A 非空 guards 只證明離線 law 路徑健康，不能證明真 Twinkle。

### #8：既有文件漏列的第二個 vacuous pass

`test_search_real_twinkle_hub` 先斷言 `results` 是 `list`，其餘斷言全在 `for src in results` 內。`TwinkleClient.search` 對任何 transport／協定錯誤都安全降級 `[]`，因此真 Hub 失效時此測仍可能 PASS。這修正 `docs/deselected-risk-pair-comparison-2026-07-21.md` 所寫「#8 無 vacuous pass」的舊判定。

關閉兩個盲區的最小順序是：先在 #8 加 `assert results`，再在 #7 加 `assert any(level == "B")`；前者證明 Hub 成功，後者證明組合路徑真的納入 Hub 結果。

## Fixture／替身關係

| 資源 | 使用範圍 | 對等價性的影響 |
|---|---|---|
| `tests/conftest.py::async_client` | 8 個目標皆未使用 | 不可列為共享覆蓋 |
| `tests/test_pipeline.py::note_path` | #5 與同檔 3 個離線 siblings | 同一臨時 DOCX，足以等價驗 parse 與 deterministic orchestration |
| `tests/fixtures/real_note.txt`、`data/law_index.db`、e2e `_assert_*` | #2 與 3 個 e2e siblings | 結構閘可直接等價；兩個 offline quality 測試共用 `_offline_structural_doc` 與 canned writer，屬相關覆蓋，不是第二個真寫作點 |
| `_grok_reachable()` | #1/#3/#4/#5/#6/#7 各自複製 | 只是 runtime skip guard，不是 correctness fixture |
| `TWINKLE_HUB_TOKEN` | #2/#7/#8 | 只是外部前置；token 存在不代表 Hub 回非空 |
| `FakeLLM`、fake Twinkle/Law | 多數替代測試 | 能精準覆蓋 parser、routing、排序與安全閘；不能替代模型語意與真服務相容性 |

## 可重現驗證

使用指定主專案 venv，且先 collection 再執行重測：

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest --collect-only -q -o "addopts=" -p no:asyncio --strict-markers -m integration tests/test_domain.py tests/test_e2e_acceptance.py tests/test_gap.py tests/test_llm.py tests/test_pipeline.py tests/test_questions.py tests/test_retrieve.py tests/test_twinkle.py --color=no
```

觀察：`8/40 tests collected (32 deselected)`，node ID 與 allowlist 8/8 相同。

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_requirements_test_coverage.py -q --color=no
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest -m "not integration" -q --color=no
```

本輪實跑結果：

- 機器索引與 collection 守衛：`2 passed in 3.89s`。
- 索引列出的 34 個去重 `equivalent_default_tests`：`34 passed in 0.78s`。
- 完整預設閘：`142 passed, 8 deselected in 61.76s`。

本輪不強制執行 integration：`pyproject.toml` 的正式預設就是 `-m 'not integration'`，而本任務是覆蓋等價性盤點；真服務結果不拿歷史紀錄冒充本輪 live 驗證。提交後再以 `git status` 與 commit 證明產物已落盤。
