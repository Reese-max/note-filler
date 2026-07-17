# 整合測試盤點報告

> 生成時間: 2026-07-17
> 命令: `pytest --collect-only -m "not integration" -q` → 102/110 通過、8 deselected
> 命令: `pytest --collect-only -m integration -q` → 8/110 collected

## 概覽

`-m "not integration"` 排除了恰好 **8** 個測試,全部掛有 `@pytest.mark.integration` marker。
pytest 定義於 `pyproject.toml:33-35`:

```
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

## 逐項清單

| # | 檔案 | 函式名 | 執行時額外 skip 條件 | 所需外部依賴 |
|---|------|--------|---------------------|-------------|
| 1 | `tests/test_domain.py:41` | `test_detect_domain_real_grok_returns_law` | 無(僅 marker) | grok proxy `127.0.0.1:8318` |
| 2 | `tests/test_e2e_acceptance.py:178` | `test_e2e_acceptance_real` | `if not LAW_DB.exists(): pytest.skip("缺 data/law_index.db")` + `if not (_grok_up() and _twinkle_ready()): pytest.skip("grok proxy 未上線或無 TWINKLE_HUB_TOKEN;...")` | grok proxy + `TWINKLE_HUB_TOKEN` env + `data/law_index.db` |
| 3 | `tests/test_gap.py:62` | `test_detect_gaps_real_grok` | 無(僅 marker) | grok proxy `127.0.0.1:8318` |
| 4 | `tests/test_llm.py:58` | `test_grok_pong_integration` | 無(僅 marker) | grok proxy `127.0.0.1:8318` |
| 5 | `tests/test_pipeline.py:118` | `test_run_pipeline_real_grok` | 無(僅 marker) | grok proxy `127.0.0.1:8318` |
| 6 | `tests/test_questions.py:53` | `test_generate_questions_real_grok` | 無(僅 marker) | grok proxy `127.0.0.1:8318` |
| 7 | `tests/test_retrieve.py:90` | `test_retrieve_for_gap_real_twinkle_smoke` | `if os.environ.get("GOV_AI_ENABLE_TWINKLE_MCP") != "1" or not token: pytest.skip("需 GOV_AI_ENABLE_TWINKLE_MCP=1 且設 TWINKLE_HUB_TOKEN")` | grok proxy + `TWINKLE_HUB_TOKEN` + `GOV_AI_ENABLE_TWINKLE_MCP=1` + `data/law_index.db` |
| 8 | `tests/test_twinkle.py:94` | `test_search_real_twinkle_hub` | `if not token: pytest.skip("未設定 TWINKLE_HUB_TOKEN,跳過 twinkle-hub 真打整合測試")` | `TWINKLE_HUB_TOKEN` env |

## 依賴分類

### 僅需 grok proxy (5 個)
- `test_detect_domain_real_grok_returns_law`
- `test_detect_gaps_real_grok`
- `test_grok_pong_integration`
- `test_run_pipeline_real_grok`
- `test_generate_questions_real_grok`

### 需 grok proxy + Twinkle + law DB (2 個)
- `test_e2e_acceptance_real` — 真端到端;grok + Twinkle + law DB 全串
- `test_retrieve_for_gap_real_twinkle_smoke` — Twinkle + law DB + grok 三件齊

### 僅需 Twinkle token (1 個)
- `test_search_real_twinkle_hub` — 真打 Twinkle Hub MCP

## Marker 機制說明

所有 8 個測試皆 **僅** 掛 `@pytest.mark.integration`，無其他額外 marker(如 `@pytest.mark.skip`、`@pytest.mark.skipif`)。
部分測試在函式體內以 `pytest.skip(...)` 做執行時條件跳過,但這些 skip 不依賴 `-m` 機制——即使以 `-m integration` 進入,若環境不滿足仍會 skip。

## 結論

- `pyproject.toml` 的 `markers` 定義與實際 `@pytest.mark.integration` 使用一致
- `-m "not integration"` 正好排除這 8 個;其餘 102 個為離線/FakeLLM 單元測試
- 排除機制運作正常,無需變更
