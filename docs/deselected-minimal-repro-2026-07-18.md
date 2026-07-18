# Deselected 測試：最易形成驗證缺口者之最小非-integration 重現條件

> 任務：針對目前 8 個 `deselected` 中最可能形成驗證缺口的那一項，整理「若要在非 integration 情境下重現，必須滿足的最小前置條件」。

## 結論：最易形成驗證缺口者

**`tests/test_e2e_acceptance.py::test_e2e_acceptance_real`**

### 選定理由

此測試涵蓋「真 Grok + 真 TwinkleClient + 真 LawLookup」的完整 pipeline 執行，涉及：

1. **5 個 §12 硬不變式**（原稿逐字不可變、無來源→pending_evidence、verified 來源品質、補充法條查核、to_markdown 格式）
2. **_assert_supplement_quality**（Level A 路由、非原始記錄倒出、[^n] 註腳標引用）
3. **有界重跑（最多 6 次）** 取 Level A 路由穩定性

相較其他 7 項（多為單一函式或單一外部依賴的 smoke test），此項同時依賴多個外部服務且斷言最嚴格，故最易因「無法在非-integration 環境重現」而形成驗證缺口。

---

## 若要在非-integration 情境下重現，必須滿足的最小前置條件

### 1. 環境變數與外部服務

| 條件 | 說明 | 必要性 |
|------|------|--------|
| `TWINKLE_HUB_TOKEN` 環境變數 | 需為有效 token，否則 TwinkleClient 無法初始化 | 必要 |
| Grok proxy 於 `127.0.0.1:8318` 可達 | 使用 `socket.create_connection` 探測，需回應 HTTP | 必要 |
| `data/law_index.db` 存在且可讀 | LawLookup 離線查核法條引用 | 必要 |

### 2. Python 執行環境

```bash
"D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest \
  tests/test_e2e_acceptance.py::test_e2e_acceptance_real \
  -m integration -q --tb=short
```

### 3. 測試內部行為（需重現的邏輯）

- 使用 `_Grok0` 包裝 GrokClient，強制 `temperature=0`
- 執行 `run_pipeline(str(FIXTURE), llm, twinkle, law)`
- 若 5 次重跑後仍無 `level=="A"` 的來源，則判定 Level A 路由斷線
- 最終執行 5 個 §12 不變式 + `_assert_supplement_quality`

### 4. 替代保護（現況）

- `test_e2e_structural_invariants`：使用 `FakeLLM` + `_StubTwinkle` 驗證離線結構不變式
- `test_run_pipeline_invariant`、`test_run_pipeline_law_domain_runs_citation_check`、`test_retrieved_five_but_only_two_cited`：提供 pipeline 與 citation 的替代覆蓋

---

## 參考文件

- `tests/deselected_allowlist.json`（第 2 項）
- `docs/deselected-substitute-mapping.md`（第 2 項說明）
- `tests/test_e2e_acceptance.py`（完整測試與 fixture）