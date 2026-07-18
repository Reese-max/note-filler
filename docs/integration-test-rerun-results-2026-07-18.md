# 8 個未執行整合測試補跑結果

> 日期：2026-07-18  
> 工作目錄：`D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\098f866a`  
> Python：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`  
> 指令覆寫：`-o addopts=`（取消預設 `-m 'not integration'`）+ 明確 node ID / `-m integration`  
> grok proxy：`http://127.0.0.1:8318/v1`（model `grok-4.3`）

## 1. 任務與範圍

針對預設被 `pyproject.toml` 的 `-m 'not integration'` 排除、且已登錄於 `tests/deselected_allowlist.json` 的 **8 個 integration 測試**，在具備標記／依賴／環境條件時補跑，並逐項記錄結果或阻礙。

本任務**不修改**測試碼、**不弱化**品質閘（原稿逐字不可變、無來源／【待補證】→`pending_evidence`、只掛實際引用來源、法條離線查核），也**不改動** `BACKLOG.md`。

## 2. 前置檢查（輕量）

來源：`docs/pytest-audit/integration-preflight-2026-07-18.json`（timestamp_local=`2026-07-18T20:10:05`）

| 檢查項 | 結果 | 影響的測試 |
|---|---|---|
| `grok_proxy_tcp_8318` | **True** | #1, #2, #3, #4, #5, #6, #7 |
| `law_index_db_exists` | **True** | #2, #7 |
| `twinkle_token_present` | **True**（僅布林，不輸出 token 值） | #2, #7, #8 |
| `real_note_exists` | **True** | #2 |
| `twinkle_flag_is_1`（`GOV_AI_ENABLE_TWINKLE_MCP=1`） | **False** | **現行 8 項測試碼未讀取此 flag**（見 `tests/test_retrieve.py:106-108` 僅查 `TWINKLE_HUB_TOKEN`） |

Collect 對照：

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest --collect-only -q -o addopts= -m integration
```

輸出（完整落盤：`docs/pytest-audit/integration-collect-2026-07-18.txt`）：

```text
tests/test_domain.py::test_detect_domain_real_grok_returns_law
tests/test_e2e_acceptance.py::test_e2e_acceptance_real
tests/test_gap.py::test_detect_gaps_real_grok
tests/test_llm.py::test_grok_pong_integration
tests/test_pipeline.py::test_run_pipeline_real_grok
tests/test_questions.py::test_generate_questions_real_grok
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke
tests/test_twinkle.py::test_search_real_twinkle_hub

8/117 tests collected (109 deselected) in 0.32s
```

8 個 node ID 與 `tests/deselected_allowlist.json` **完全一致**。

## 3. 執行策略（避免逾時）

依 L003 / L004 / L005 / L010，採三段式分批，先輕後重：

| 批次 | 範圍 | 原始輸出檔 |
|---|---|---|
| batch1 light | #4 llm, #1 domain, #3 gap, #6 questions | `docs/pytest-audit/integration-batch1-light-2026-07-18.txt` |
| batch2 medium | #5 pipeline, #8 twinkle, #7 retrieve | `docs/pytest-audit/integration-batch2-medium-2026-07-18.txt` |
| batch3 e2e | #2 e2e acceptance | `docs/pytest-audit/integration-batch3-e2e-2026-07-18.txt` |

## 4. 總覽結果

| # | 測試 node ID | 結果 | call 耗時 | 阻礙 |
|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | **PASSED** | 2.36s | 無 |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | **PASSED** | 130.22s | 無 |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | **PASSED** | 4.09s | 無 |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | **PASSED** | 1.22s | 無 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | **PASSED** | 63.30s | 無 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | **PASSED** | 7.03s | 無 |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | **PASSED** | 10.44s | 無 |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | **PASSED** | 2.92s | 無 |

**結論：8/8 PASSED，0 SKIPPED，0 FAILED，0 阻礙**

總 session 耗時合計約：14.84s + 76.83s + 130.24s ≈ **221.91s（約 3 分 42 秒）**。

## 5. 逐項詳情

### 5.1 `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

- **結果**：PASSED（2.36s call）
- **前置條件**：`@pytest.mark.integration` + `@pytest.mark.skipif(not _grok_reachable())`；本次 TCP 8318 可達
- **依賴**：真 GrokClient → `127.0.0.1:8318/v1` / `grok-4.3`
- **批次**：batch1
- **阻礙**：無

### 5.2 `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

- **結果**：PASSED（130.22s call；session 130.24s）
- **前置條件**：integration marker；runtime 需 `data/law_index.db`、grok proxy、`TWINKLE_HUB_TOKEN`；本次三者皆就緒
- **依賴**：真 Grok + 真 Twinkle Hub + 真 LawLookup + `tests/fixtures/real_note.txt`
- **品質閘（測試內斷言）**：原稿 immutable、無來源閘、法條引用、Markdown 格式、Level A 路由等
- **批次**：batch3
- **阻礙**：無

### 5.3 `tests/test_gap.py::test_detect_gaps_real_grok`

- **結果**：PASSED（4.09s call）
- **前置條件**：integration + grok skipif；本次可達
- **依賴**：真 Grok 缺口判定
- **批次**：batch1
- **阻礙**：無

### 5.4 `tests/test_llm.py::test_grok_pong_integration`

- **結果**：PASSED（1.22s call）
- **前置條件**：integration + grok skipif；本次可達
- **依賴**：真 HTTP chat completion 連通性（PONG）
- **批次**：batch1
- **阻礙**：無

### 5.5 `tests/test_pipeline.py::test_run_pipeline_real_grok`

- **結果**：PASSED（63.30s call）
- **前置條件**：integration + grok skipif；本次可達
- **依賴**：真 Grok；Twinkle／Law 為 Fake
- **批次**：batch2
- **阻礙**：無

### 5.6 `tests/test_questions.py::test_generate_questions_real_grok`

- **結果**：PASSED（7.03s call）
- **前置條件**：integration + grok skipif；本次可達
- **依賴**：真 Grok 問題生成
- **批次**：batch1
- **阻礙**：無

### 5.7 `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

- **結果**：PASSED（10.44s call）
- **前置條件**：integration；skipif 缺 `data/law_index.db` 或 grok 不可達；函式內缺 `TWINKLE_HUB_TOKEN` 則 skip。本次皆就緒
- **依賴**：真 Grok keyword + 真 LawLookup + 真 Twinkle Hub
- **與歷史差異**：先前報告 `docs/integration-test-individual-results-2026-07-18.md` 曾因缺 token／舊 flag 敘述而 **SKIPPED**；本次 token 已存在且測試碼僅要求 `TWINKLE_HUB_TOKEN`，故成功執行並 **PASSED**
- **批次**：batch2
- **阻礙**：無

### 5.8 `tests/test_twinkle.py::test_search_real_twinkle_hub`

- **結果**：PASSED（2.92s call）
- **前置條件**：integration；缺 `TWINKLE_HUB_TOKEN` 則 skip；本次 token 存在
- **依賴**：真 Twinkle Hub MCP 搜尋
- **批次**：batch2
- **阻礙**：無

## 6. 可重現指令

```text
# 前置（不輸出 token 值）
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -c "..."  # 見 preflight JSON

# collect
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest --collect-only -q -o addopts= -m integration

# batch1 light
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -o addopts= -m integration -v --tb=short --durations=0 ^
  tests/test_llm.py::test_grok_pong_integration ^
  tests/test_domain.py::test_detect_domain_real_grok_returns_law ^
  tests/test_gap.py::test_detect_gaps_real_grok ^
  tests/test_questions.py::test_generate_questions_real_grok

# batch2 medium
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -o addopts= -m integration -v --tb=short --durations=0 ^
  tests/test_pipeline.py::test_run_pipeline_real_grok ^
  tests/test_twinkle.py::test_search_real_twinkle_hub ^
  tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke

# batch3 e2e
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -o addopts= -m integration -v --tb=short --durations=0 ^
  tests/test_e2e_acceptance.py::test_e2e_acceptance_real
```

## 7. 產物清單（本提交可稽核）

| 檔案 | 用途 |
|---|---|
| `docs/integration-test-rerun-results-2026-07-18.md` | 本報告（逐項結果與阻礙） |
| `docs/pytest-audit/integration-preflight-2026-07-18.json` | 前置環境布林探測 |
| `docs/pytest-audit/integration-collect-2026-07-18.txt` | collect 8 項原始輸出 |
| `docs/pytest-audit/integration-batch1-light-2026-07-18.txt` | batch1 原始 pytest 輸出 |
| `docs/pytest-audit/integration-batch2-medium-2026-07-18.txt` | batch2 原始 pytest 輸出 |
| `docs/pytest-audit/integration-batch3-e2e-2026-07-18.txt` | batch3 原始 pytest 輸出 |

## 8. 最終判讀

1. **8 個未執行測試在本次環境下均可執行，且全部 PASSED**。
2. 無「缺標記／缺依賴／環境不足」導致的跳過或阻礙；`GOV_AI_ENABLE_TWINKLE_MCP` 雖非 `1`，但現行測試碼不讀此 flag，不構成阻礙。
3. 預設日常回歸仍維持 `-m 'not integration'`（平時跳過）；本任務為條件具備時的補跑驗證，未變更預設選取策略。
4. 與同日較早的 `docs/integration-test-individual-results-2026-07-18.md`（7 passed / 1 skipped）相比，#7 在 token 就緒後已由 SKIPPED 轉為 PASSED。
