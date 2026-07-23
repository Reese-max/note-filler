# 11 個 Deselected 測試分析報告

日期：2026-07-24
執行環境：本機 grok proxy (:8318) + TWINKLE_HUB_TOKEN + data/law_index.db

---

## 一、排除機制總覽

- **篩選條件**：`pyproject.toml:32` 預設 `-m 'not integration'`
- **單一真實來源**：`tests/deselected_allowlist.json`（456 行，11 條目）
- **雙重防護**：`@pytest.mark.integration`（collection 階段排除） + `@pytest.mark.skipif`（runtime 跳過）
- **替代覆蓋**：`tests/test_deselection_guard.py` 逐項驗證 allowlist 穩定性 + 替代測試 collectable
- **CI 防漏跑**：`scripts/validate_deselection_ci.py`（數量、欄位、集合一致性、替代覆蓋可執行、安全風險、原因對齊）

## 二、11 個 Deselected 測試排除原因逐項說明

| # | 測試 | 檔案:行 | marker | 排除原因 |
|---|------|---------|--------|----------|
| 1 | `test_detect_domain_real_grok_returns_law` | `test_domain.py:62` | integration | 需真實 grok proxy (:8318)，proxy 不可達時 skipif 略過 |
| 2 | `test_detect_domain_real_grok_representative_domains` | `test_domain.py:76` | integration | 需真實 grok proxy，四類語意矩陣需真模型 |
| 3 | `test_e2e_acceptance_real` | `test_e2e_acceptance.py:244` | integration | 需 grok proxy + law_index.db + TWINKLE_HUB_TOKEN |
| 4 | `test_detect_gaps_real_grok` | `test_gap.py:83` | integration | 需真實 grok proxy |
| 5 | `test_detect_gaps_real_grok_semantic_matrix` | `test_gap.py:106` | integration | 需真實 grok proxy |
| 6 | `test_grok_pong_integration` | `test_llm.py:95` | integration | 需真實 grok proxy（基礎連通性） |
| 7 | `test_run_pipeline_real_grok` | `test_pipeline.py:190` | integration | 需真實 grok proxy |
| 8 | `test_generate_questions_real_grok` | `test_questions.py:74` | integration | 需真實 grok proxy |
| 9 | `test_retrieve_for_gap_real_twinkle_smoke` | `test_retrieve.py:102` | integration | 需 grok proxy + law_index.db + TWINKLE_HUB_TOKEN |
| 10 | `test_search_real_twinkle_hub` | `test_twinkle.py:185` | integration | 需 TWINKLE_HUB_TOKEN |
| 11 | `test_write_supplement_real_grok_grounded_output` | `test_write.py:63` | integration | 需真實 grok proxy |

**共同排除原因**：所有 11 個測試都依賴外部服務（grok proxy 或 Twinkle Hub），在 CI 預設不可用，故以 `@pytest.mark.integration` 標記後由 `-m 'not integration'` 在 collection 階段排除。

## 三、資料遺失／異常處理／跳過分支分類

### 3.1 涉及資料遺失驗證

| 測試 | 資料遺失斷言 | 說明 |
|------|-------------|------|
| `test_e2e_acceptance_real` | `_assert_immutable_original` (§12(1))、`_assert_no_source_gate` (§12(2))、`_assert_supplement_quality` | 驗證原稿逐字不可變、無來源補充不消失 |
| `test_run_pipeline_real_grok` | `doc.original is not None`、C6 pending_evidence 不變式 | 驗證 pipeline 不丟失原始內容、無來源補充不消失 |
| `test_write_supplement_real_grok_grounded_output` | `[^` in text、`used_source_ids` 非空且 ⊆ 提供來源 | 驗證 writer 輸出正確引用來源，不遺失來源映射 |

### 3.2 涉及異常處理

| 測試 | 異常處理路徑 | 說明 |
|------|-------------|------|
| `test_grok_pong_integration` | grok proxy 連線異常 → skipif | 驗證 proxy 連通性與回應格式 |
| `test_e2e_acceptance_real` | 缺 law_index.db → pytest.skip、grok/Twinkle 未就緒 → skip、模型幻覺 → law citation 檢查 | 多重依賴失敗時安全跳過；模型不正確輸出被法條查核攔截 |
| `test_run_pipeline_real_grok` | skipif grok 不可達 | pipeline 在真模型輸出下的穩定度 |
| `test_retrieve_for_gap_real_twinkle_smoke` | 缺 law_index.db → skipif、缺 grok → skipif、缺 token → runtime skip | 三層依賴檢查 |
| `test_search_real_twinkle_hub` | 缺 token → runtime skip | Twinkle Hub 連線驗證 |
| `test_write_supplement_real_grok_grounded_output` | skipif grok 不可達；temperature=0 定住寫作器 | 真模型 grounded 寫作穩定度 |

### 3.3 涉及跳過分支

| 測試 | 跳過條件數 | 跳過類型 |
|------|-----------|---------|
| `test_e2e_acceptance_real` | 3 | runtime pytest.skip (law_db, grok, twinkle) |
| `test_retrieve_for_gap_real_twinkle_smoke` | 3 | 2×@skipif + runtime pytest.skip |
| `test_search_real_twinkle_hub` | 1 | runtime pytest.skip (twinkle token) |
| 其餘 8 個 | 1 | @pytest.mark.skipif (grok proxy) |

## 四、執行結果

### 4.1 執行命令

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest <測試節點> -m "integration" -o "addopts=" -v
```

### 4.2 逐項結果

| # | 測試 | 結果 | 耗時 | 備註 |
|---|------|------|------|------|
| 1 | test_detect_domain_real_grok_returns_law | ✅ PASSED | 40.23s (批次) | grok 正確回 law |
| 2 | test_detect_domain_real_grok_representative_domains | ✅ PASSED | 同上 | 四類語意矩陣全部正確 |
| 3 | test_e2e_acceptance_real | ❌ FAILED | 198.65s | grok 幻覺「訴願法第22等條」 |
| 4 | test_detect_gaps_real_grok | ✅ PASSED | 40.23s (批次) | covered/missing 正確過濾 |
| 5 | test_detect_gaps_real_grok_semantic_matrix | ✅ PASSED | 36.92s (批次) | covered 排除、missing 保留 |
| 6 | test_grok_pong_integration | ✅ PASSED | 40.23s (批次) | PONG 契約成立 |
| 7 | test_run_pipeline_real_grok | ✅ PASSED | 108.28s | pipeline 不炸、C6 不變式成立 |
| 8 | test_generate_questions_real_grok | ✅ PASSED | 40.23s (批次) | 問題清單格式正確 |
| 9 | test_retrieve_for_gap_real_twinkle_smoke | ✅ PASSED | 36.92s (批次) | Level A/B 路由正常、排序正確 |
| 10 | test_search_real_twinkle_hub | ✅ PASSED | 36.92s (批次) | Twinkle Hub 連線正常、Source 解析正確 |
| 11 | test_write_supplement_real_grok_grounded_output | ✅ PASSED | 36.92s (批次) | grounded 輸出含 [^ 註腳 |

**合計：10 passed, 1 failed**

### 4.3 失敗分析：test_e2e_acceptance_real

**失敗斷言**：`_assert_law_citations_ok`（第 283 行）

```
AssertionError: 補充出現不存在法條: [{'law_name': '訴願法', 'article_no': '22等',
  'kind': 'article_not_found',
  'detail': '《訴願法》查無第 22等 條（疑似條號幻覺）'}]
```

**根本原因**：Grok-4.3 模型產生幻覺，在補充文本中引用「訴願法第22等條」（「等」字為人為添加、非正式法條編號）。`check_law_citations` 正確攔截此不存在的條號。

**涉及面向**：
- 資料完整性：模型幻覺可能將不存在引用寫入輸出 → 被法條查核攔截
- 異常處理：`check_law_citations` 正確識別 `article_not_found` 並回報
- 跳過分支：測試在 law_db/grok/twinkle 任一段缺時會安全跳過

**現況判定**：此為模型幻覺造成的真實測試失敗，非 CI 回歸。法條查核機制正常運作。

## 五、額外發現

1. `test_e2e_acceptance_real` 有內建 flakiness 補償：因 grok reasoning model 不完全吃 temperature，Level A 路由斷言約 50% flaky，設計了最多 6 次重跑（第 268-278 行）。
2. `test_retrieve_for_gap_real_twinkle_smoke` 的 `_assert_supplement_quality` 盲區已被 `test_exclusion_correctness_blind_spot.py` 離線覆蓋（vacuous pass on empty 情境）。
3. 所有 11 個整合測試的替代離線覆蓋在 `test_excluded_failing_controls.py`（8 個 control 測試）及各自替代測試中完備。
