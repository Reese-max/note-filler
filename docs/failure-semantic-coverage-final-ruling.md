# 失敗語義覆蓋最終判定

## 判定依據

- CI 配置：`.github/workflows/ci.yml`
- pytest 配置：`pyproject.toml`（`-m 'not integration'` 預設排除）
- 等價路徑審計：`docs/pytest-audit/deselected-correctness-path-equivalence-2026-07-21.json`
- 需求覆蓋矩陣：`docs/pytest-audit/requirements-test-coverage-2026-07-19.json`
- 排除對照：`tests/test_excluded_failing_controls.py`
- 盲區回歸：`tests/test_exclusion_correctness_blind_spot.py`
- 驗收守衛：`tests/test_deselection_guard.py`

---

## CI Jobs 總覽

| Job | Python | Dep 策略 | Marker | 觸發 | 測試數 |
|---|---|---|---|---|---|
| `test-pinned` | 3.11, 3.12 | `-c constraints-pinned.txt` | `not integration` | push/PR | 149 |
| `test-latest` | 3.11, 3.12, 3.13 | 最新相容 | `not integration` | push/PR | 149 |
| `test-integration` | 3.12 | 最新相容 | `integration` | `workflow_dispatch` | 8 |

**主線 Job**（test-pinned / test-latest）跑完全同一套 149 個非 integration 測試。
**替代 Job**（test-integration）只跑 8 個整合測試，且限定 manual trigger。

---

## 一、只在替代 Job 被覆蓋的失敗語義

以下 8 個 `@pytest.mark.integration` 測試的**「真實外部服務」部分**完全依賴
`test-integration` 手動 Job，主線 CI 永遠不執行。每個測試的確定性（parsing /
format / contract）部分已由 `tests/test_excluded_failing_controls.py` 替代覆蓋。

| # | Integration 測試 | 真實服務語義 | 確定性替代測試 |
|---|---|---|---|
| T1 | `test_domain.py::test_detect_domain_real_grok_returns_law` | Grok 對法律文字的領域分類正確性 | `test_detect_domain_law`, `control_01` |
| T2 | `test_e2e_acceptance.py::test_e2e_acceptance_real` | Grok+Twinkle+Law 完整 pipeline 實際產出 grounded supplement | `test_e2e_structural_invariants`, `control_02`, 等 8 個 |
| T3 | `test_gap.py::test_detect_gaps_real_grok` | Grok 語意判定 partial/missing | `test_detect_gaps_keeps_only_partial_and_missing`, `control_03` |
| T4 | `test_llm.py::test_grok_pong_integration` | 127.0.0.1:8318 TCP 連通性與 proxy 回應格式 | `test_grokclient_builds_request_body`, `control_04` |
| T5 | `test_pipeline.py::test_run_pipeline_real_grok` | Grok 在完整 pipeline 中的輸出穩定性 | `test_run_pipeline_invariant`, `control_05`, 等 4 個 |
| T6 | `test_questions.py::test_generate_questions_real_grok` | Grok 對法律文本的出題覆蓋品質 | `test_generate_questions_splits_multiline_string`, `control_06` |
| T7 | `test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | Twinkle Hub MCP I/O + Grok keyword 抽取組合 | `test_retrieve_law_domain_puts_level_A_before_B`, `control_07b`, 等 7 個 |
| T8 | `test_twinkle.py::test_search_real_twinkle_hub` | Twinkle Hub MCP 服務可用性與 session 相容性 | `test_search_parses_source_with_full_content`, `control_08` |

### 判定

這些語義的覆蓋依賴**替代 Job**（`test-integration`）。由於該 Job 僅 `workflow_dispatch`
不自動執行，實務上開發期間永遠看不到這些語義的失敗。
現有替代測試只覆蓋確定性解析層，不涵蓋真實 I/O。

---

## 二、完全沒有覆蓋的失敗語義（含替代 Job 在內）

路徑審計確認 **2 條 correctness path 零覆蓋點**——既無替代測試、連整合測試
本身的斷言對空結果也是 vacuous pass。

### 編號 T7-P3：Twinkle Level B 貢獻驗證

```
正確性路徑：組合 smoke 必須證明真 Twinkle 對結果有 Level B 貢獻
審計ID：T7-P3
coverage_points: []
status: not_covered
```

- 整合測試 `test_retrieve_for_gap_real_twinkle_smoke` 的三道斷言
  （`all(isinstance)`, `all(level in A/B)`, `sorted(keys)`）在 `out == []`
  時全部 vacuous true。
- 無任何測試斷言 `any(s.level == "B" for s in out)`。
- **必要補測**：在該整合測試中補上 `assert any(s.level == 'B' for s in out)`。

### 編號 T8-P3：真 Hub 非空結果驗證

```
正確性路徑：真 Hub 成功回傳至少一筆 Source，證明服務端協定仍相容
審計ID：T8-P3
coverage_points: []
status: not_covered
```

- 整合測試 `test_search_real_twinkle_hub` 只檢查 `isinstance(results, list)`，
  未對空結果設防——`results == []` 時 for 迴圈不執行，所有斷言 vacuous pass。
- **必要補測**：在該整合測試中 `isinstance(results, list)` 後立即加
  `assert results`。

---

## 三、回歸保護不足（僅 1 個覆蓋點，且該點在替代 Job 內）

以下 5 條路徑各只有 **1 個覆蓋點**，且該覆蓋點在 `@pytest.mark.integration`
測試內——主線 CI 執行時完全不可見。雖然不屬「全無覆蓋」，但保護強度等於零。

| 路徑 | 唯一覆蓋點 | 建議最小補測 |
|---|---|---|
| T1-P2：真 Grok 對刑法文字實際回 law | `test_detect_domain_real_grok_returns_law` | 參數化兄弟案例分測 law/admin/exam/other |
| T2-P6：真 Grok+真 Twinkle 產出 grounded supplement | `test_e2e_acceptance_real` | 隔離 retrieve 只真打 Grok writer |
| T3-P2：真 Grok 判定 partial/missing | `test_detect_gaps_real_grok` | 含 covered/missing 的有界參數化案例 |
| T5-P3：真 Grok 產生 gap 驅動下游 | `test_e2e_acceptance_real` | C6 迴圈前補 supplement 非空斷言 |
| T6-P2：JSON-shaped LLM 回應安全 | `test_generate_questions_real_grok` | FakeLLM 餵 JSON 證明安全解析 |

---

## 四、總結與必要補測清單

### 必要補測（零覆蓋，`test-integration` 也救不了）

| # | 位置 | 缺少的斷言／測試 | 優先級 |
|---|---|---|---|
| 1 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `out` 非空後 `any(s.level == 'B')` | 高 |
| 2 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `results` 非空斷言 | 高 |

### 可接受但需追蹤（僅替代 Job 覆蓋，有確定性替代）

8 項 `integration` 測試的「真實 I/O」語義已由 `deselected_allowlist.json`
文件化，並有對應的 `test_control_N` 涵蓋確定性路徑。殘餘外部風險在
allowlist 中標註為 `coverage_gap`，並指向 `test-integration` Job 或
本機手動執行作為緩解。不需追加補測。
