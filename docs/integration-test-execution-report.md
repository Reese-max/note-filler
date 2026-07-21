# Integration 測試執行報告

執行日期：2026-07-21
執行方式：逐一以 `pytest -vv -m "integration" <node-id>` 執行

## 環境條件

| 項目 | 狀態 |
|---|---|
| grok proxy (:8318) | 埠通但缺少 xAI OAuth 憑證（`hermes auth reset xai-oauth` 後可修復） |
| TwinkleHub | 正常 |
| LAW_DB (data/law_index.db) | 存在 |
| TWINKLE_HUB_TOKEN | 已設定 |

## 逐項執行結果

| # | 測試節點 | 結果 | 失敗原因 |
|---|---|---|---|
| 1 | `test_domain.py::test_detect_domain_real_grok_returns_law` | **FAILED** | HTTP 401：grok proxy 無 xAI OAuth 憑證 |
| 2 | `test_e2e_acceptance.py::test_e2e_acceptance_real` | **FAILED** | HTTP 401：同上，pipeline 第一步 detect_domain 即炸 |
| 3 | `test_gap.py::test_detect_gaps_real_grok` | **FAILED** | HTTP 401：llm.complete 呼叫失敗 |
| 4 | `test_llm.py::test_grok_pong_integration` | **FAILED** | HTTP 401：最基本的 round-trip 驗證也失敗 |
| 5 | `test_pipeline.py::test_run_pipeline_real_grok` | **FAILED** | HTTP 401：pipeline entry detect_domain 即失敗 |
| 6 | `test_questions.py::test_generate_questions_real_grok` | **FAILED** | HTTP 401：llm.complete 呼叫失敗 |
| 7 | `test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | **FAILED** | HTTP 401：law_search 內 llm.complete 失敗（亦有 TWINKLE_HUB_TOKEN 需求，但 Token 存在） |
| 8 | `test_twinkle.py::test_search_real_twinkle_hub` | **PASSED** | 不需 grok，僅用 TwinkleHub |

## 總計

- **PASSED：1**（12.5%）
- **FAILED：7**（87.5%）
- **SKIPPED：0**
- **環境限制導致無法執行：0**

## 覆蓋分析

### 各測試對應的 correctness 路徑

| 測試 | 涵蓋路徑 | 通過？ |
|---|---|---|
| `test_domain.py::test_detect_domain_real_grok_returns_law` | 真實 LLM 輸出下的 domain 分類正確性 | ✗ |
| `test_llm.py::test_grok_pong_integration` | GrokClient round-trip 連通性 | ✗ |
| `test_questions.py::test_generate_questions_real_grok` | 真實 LLM 產出問題的品質 | ✗ |
| `test_gap.py::test_detect_gaps_real_grok` | 真實 LLM 產出 gap 分析的結構正確性 | ✗ |
| `test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | 真實 LLM + Twinkle + Law 三者整合的 retrieve 路徑 | ✗ |
| `test_pipeline.py::test_run_pipeline_real_grok` | 整條 pipeline（parse→domain→questions→gaps→retrieve→write）串接真實 LLM | ✗ |
| `test_e2e_acceptance.py::test_e2e_acceptance_real` | 完整 E2E 流程 + 品質邊界（Level A 檢索、補充段落引用） | ✗ |
| `test_twinkle.py::test_search_real_twinkle_hub` | TwinkleHub 真實檢索連通性 | ✓ |

### 未執行造成的覆蓋風險

1. **LLM 輸出正確性完全未驗證**：7 個依賴 grok 的測試全部失敗，代表任何對 LLM 輸出格式、內容正確性的假設都在真實模型上未經驗證。fake/mock 測試只能驗證程式邏輯不炸，無法保證模型實際輸出的品質。

2. **E2E 品質邊界全盲**：`test_e2e_acceptance_real` 原本設計為「以 temperature=0 定住寫作器，檢查至少補充段落掛 Level A 來源」，是唯一跨越所有模組的品質閘。該測試完全未執行，代表從 parse 到 write 的整條 pipeline 在真實 LLM 下是否正確無從得知。

3. **domain 分類的金標準遺失**：用 fake LLM 測試 `detect_domain` 只能驗證 routing 邏輯，無法確認真實 grok 對法律文本的回覆格式是否符合 `law|admin|exam|other` 規範。若 grok-4.3 的回覆格式偏移，整個 pipeline 會在不正確的 domain 下執行。

4. **低風險**：`test_twinkle.py::test_search_real_twinkle_hub` 通過，證明 TwinkleHub 檢索連通性正常。domain 非 law 時走 Web 檢索的路徑在 offline 測試已有覆蓋。

### `_grok_reachable()` 的 skipif 缺陷

所有 grok 依賴測試使用 `socket.create_connection` 做 TCP 埠檢查，但 grok proxy (:8318) 雖然 listening 卻未完成 xAI OAuth 認證（`upstream_auth_failed`）。這導致 `skipif` 條件不成立（埠通＝False），測試被收集但不應執行——它們應被正確判斷為「因環境條件無法執行」。

**建議修正**：`_grok_reachable()` 應改為實際發送一次簡單 API 呼叫（如 test_grok_pong_integration 的 round-trip）驗證 HTTP 200，而非僅檢查埠是否開放。

## 結論

| 面向 | 結果 |
|---|---|
| 真實 LLM 正確性驗證 | **完全未執行**（7/8 失敗） |
| TwinkleHub 連通性驗證 | **已驗證**（通過） |
| Skipif 保護失效 | 是——埠通不等於 API 可用 |
| 需修復環境後重新執行 | 是——需重跑 `hermes auth reset xai-oauth` |
