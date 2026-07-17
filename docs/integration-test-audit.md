# 整合測試排除清單審查報告

日期: 2026-07-16
審查範圍: `pyproject.toml` addopts `-m 'not integration'` 排除的 8 個測試

## 審查結論

| # | 測試 | 判定 | 變更 |
|---|------|------|------|
| 1 | `test_domain.py::test_detect_domain_real_grok_returns_law` | **改為條件式執行** | `@pytest.mark.integration` → `@pytest.mark.skipif(not _grok_reachable())` |
| 2 | `test_gap.py::test_detect_gaps_real_grok` | **改為條件式執行** | 同上 |
| 3 | `test_e2e_acceptance.py::test_e2e_acceptance_real` | **維持 integration** | 無變更 |
| 4 | `test_twinkle.py::test_search_real_twinkle_hub` | **改為條件式執行** | 移除 `@pytest.mark.integration`,保留函式內 runtime skip |
| 5 | `test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | **維持 integration** | 無變更 |
| 6 | `test_pipeline.py::test_run_pipeline_real_grok` | **維持 integration** | 無變更 |
| 7 | `test_llm.py::test_grok_pong_integration` | **改為條件式執行** | `@pytest.mark.integration` → `@pytest.mark.skipif(not _grok_reachable())` |
| 8 | `test_questions.py::test_generate_questions_real_grok` | **改為條件式執行** | 同上 |

## 變更為條件式執行(5 檔)

### 共同機制

新增 `_grok_reachable()` 模組層級輔助函式,用 `socket.create_connection` 探測 `127.0.0.1:8318`(grok proxy)。

grok proxy 為本機 24/7 常駐基礎設施(CLIProxyAWG/Hermes),並非外部 SaaS。
這 5 個測試各自的依賴分析:

| 測試 | 依賴 | 實測耗時 | 已有 Fake 覆蓋 | 適合條件式? |
|------|------|----------|----------------|-----------|
| test_detect_domain_real_grok_returns_law | GrokClient only | ~3.6s | FakeLLM 6 case | ✅ |
| test_detect_gaps_real_grok | GrokClient only | ~4.9s | FakeLLM 5 case | ✅ |
| test_grok_pong_integration | GrokClient only | ~2.1s | 有 monkeypatch 版 | ✅ |
| test_generate_questions_real_grok | GrokClient only | ~5.9s | FakeLLM 4 case | ✅ |
| test_search_real_twinkle_hub | TwinkleClient only | ~7.0s | monkeypatch 版 3 case | ✅(已有 runtime skip) |

### test_twinkle.py 特例

原稿同時有 `@pytest.mark.integration` + 函式內 `pytest.skip()`,雙重門檻。
本次僅移除 `@pytest.mark.integration`,函式內的 `if not token: pytest.skip(...)` 保留作為 fallback。
效果:有 TWINKLE_HUB_TOKEN 時自動執行;無 token 時 clean skip(不進 marker 機制)。

## 維持 integration(3 檔)

| 測試 | 維持理由 | 實測 |
|------|---------|------|
| test_e2e_acceptance_real | 完整 pipeline:GrokClient + TwinkleClient + law_index.db;三服務依賴;實測 >120s timeout | TIMEOUT |
| test_run_pipeline_real_grok | GrokClient + FakeTwinkle;但 pipeline 多步 grok 呼叫實測 >60s | TIMEOUT |
| test_retrieve_for_gap_real_twinkle_smoke | 需同時設定 TWINKLE_HUB_TOKEN + GOV_AI_ENABLE_TWINKLE_MCP;雙 env 閘 | SKIP |

## 驗證結果

### 變更前

```
non-integration: 102 passed, 8 deselected
integration(-m): 2 passed, 1 skipped, 2 timeout
```

### 變更後

```
non-integration(-m 'not integration'): 107 passed, 3 deselected
integration(-m): 3 remaining (e2e, pipeline, retrieve)
```

5 個測試從「永遠排除」改為「grok/twinkle 可用時自動執行」,正常開發流程不再需要手動 `-m integration` 才跑得到 grok smoke test。
