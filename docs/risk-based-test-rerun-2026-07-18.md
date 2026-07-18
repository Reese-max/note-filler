# 依風險分析決定補跑清單與執行紀錄

> 日期：2026-07-18  
> 工作目錄：`D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\8eba824b`  
> 基線 HEAD（報告產出前）：`db9aaa2c3d51617a96b2a483ce0ba5bd46952c68`（branch `adng/8eba824b`）  
> Python：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`  
> grok proxy：`http://127.0.0.1:8318/v1`（model `grok-4.3`）  
> 指令覆寫：`-o addopts=`（取消預設 `-m 'not integration'`）後以 node ID / `-m integration` 明確選取

## 1. 任務範圍

依既有逐項風險／覆蓋等價分析（`docs/coverage-equivalence-audit-2026-07-18.md`、`docs/deselected-final-judgment-2026-07-18.md`、`tests/deselected_allowlist.json`）決定 **哪些 deselected integration 測試必須補跑**；對可補跑者實際執行並記錄命令、環境、退出碼與結果；對無法補跑者記錄阻礙原因。

本任務：

- **不修改** 生產碼／測試碼／`pyproject.toml` 預設閘
- **不弱化** 品質閘（原稿逐字不可變、無來源／【待補證】→`pending_evidence`、只掛實際引用來源、法條離線查核）
- **不改動** `BACKLOG.md`／`BACKLOG-adng.md`
- 平時預設仍維持 `-m 'not integration'`；本紀錄為條件具備時的 **風險導向補跑**

---

## 2. 輕量前置檢查（L004／L005）

來源落盤：[`docs/pytest-audit/risk-based-rerun-preflight-2026-07-18.json`](pytest-audit/risk-based-rerun-preflight-2026-07-18.json)

| 檢查項 | 結果 | 影響測試 |
|---|---|---|
| `grok_proxy_tcp_8318` | **True** | #1–#7 |
| `law_index_db_exists` | **True** | #2, #7 |
| `twinkle_token_present` | **True**（僅布林，不輸出 token 值） | #2, #7, #8 |
| `real_note_exists` | **True** | #2 |
| `twinkle_flag_is_1`（`GOV_AI_ENABLE_TWINKLE_MCP=1`） | **False** | 現行 8 項測試碼 **不讀** 此 flag；**不構成阻礙** |

Collect 對照（完整輸出：[`docs/pytest-audit/risk-based-rerun-collect-2026-07-18.txt`](pytest-audit/risk-based-rerun-collect-2026-07-18.txt)）：

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest --collect-only -q -o addopts= -m integration
```

```text
tests/test_domain.py::test_detect_domain_real_grok_returns_law
tests/test_e2e_acceptance.py::test_e2e_acceptance_real
tests/test_gap.py::test_detect_gaps_real_grok
tests/test_llm.py::test_grok_pong_integration
tests/test_pipeline.py::test_run_pipeline_real_grok
tests/test_questions.py::test_generate_questions_real_grok
tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke
tests/test_twinkle.py::test_search_real_twinkle_hub

8/117 tests collected (109 deselected) in 0.29s
```

8 個 node ID 與 `tests/deselected_allowlist.json` **完全一致**。

預設閘計數：

```text
109/117 tests collected (8 deselected)  # -m "not integration"
```

---

## 3. 逐項風險分析 → 是否必須補跑

### 3.1 判定原則

| 代號 | 定義 |
|---|---|
| **MUST** | 殘餘風險屬模型語意品質／外部服務 I/O／真實 TCP 連通，且 **離線 substitute 無法證明**；環境就緒時 **必須補跑** 才能關閉該殘餘風險 |
| **OPTIONAL** | 殘餘風險已由離線等價覆蓋，或僅屬歷史對照；本次無此分類 |
| **BLOCKED** | 必須補跑但環境／依賴不足，無法執行；需記錄阻礙 |

補充：

- allowlist 的 `decision: acceptable_unexecuted` 指 **日常 CI 可接受不跑**（確定性路徑已由 substitute 覆蓋），**不等於**「殘餘風險不需在條件具備時驗證」。
- 本任務「補跑」= 在環境就緒時執行既有 integration 測試；**不是**新增 non-integration 測試（該決策見 `docs/deselected-final-judgment-2026-07-18.md`，8/8 無需補測）。

### 3.2 決策總表

| # | 測試 node ID | 殘餘風險（substitute 未覆蓋） | 風險等級 | 補跑決策 | 本次可否執行 | 理由 |
|---:|---|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | 真 grok-4.3 對法律文字 domain 分類品質 | 中（路由偏差） | **MUST** | 可（TCP 8318） | 誤標 admin/exam/other 會污染後續 questions/retrieve |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | 真 Grok+真 Twinkle+真 LawLookup 複合品質與 Level A 路由 | **高**（§12 MVP） | **MUST** | 可（db+token+grok+fixture） | 唯一真正端到端；品質閘在 live 路徑的 smoke |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | 真 grok gap 語意（partial/missing） | 中 | **MUST** | 可 | 漏判缺口 → 檢索範圍錯誤 |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | 真實 TCP／proxy 回應 schema 連通 | 高（基礎設施）／成本低 | **MUST** | 可 | 全 LLM 路徑前置 smoke；失敗則其餘 grok 測試無意義 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | 真模型各階段輸出下 pipeline 穩定性 | 中高 | **MUST** | 可 | 驗證 domain→questions→gaps→assemble 在 live 輸出下不炸且 C6 仍守 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | 真 grok 問題語意／相關性 | 中 | **MUST** | 可 | 無關問題污染 gap/retrieve |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | 真 keyword + 真 LawLookup + 真 Twinkle I/O | 中高 | **MUST** | 可（db+token+grok） | A/B 排序與 live 檢索路徑 |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | 真 Twinkle Hub MCP session／網路 | 中 | **MUST** | 可（token） | 服務可用性與協議相容性 |

**決策結論：8/8 = MUST 補跑；本次環境 8/8 均可執行；0 BLOCKED。**

---

## 4. 執行策略（避免逾時，L003／L010）

先輕後重、分三批，不把關鍵修正綁死在單一長尾指令：

| 批次 | 範圍 | 風險優先序 | 原始輸出 |
|---|---|---|---|
| batch1 light | #4 llm, #1 domain, #3 gap, #6 questions | 先驗證連通 + 單階段語意 | [`risk-based-rerun-batch1-light-2026-07-18.txt`](pytest-audit/risk-based-rerun-batch1-light-2026-07-18.txt) |
| batch2 medium | #5 pipeline, #8 twinkle, #7 retrieve | 中成本 live pipeline／外部 I/O | [`risk-based-rerun-batch2-medium-2026-07-18.txt`](pytest-audit/risk-based-rerun-batch2-medium-2026-07-18.txt) |
| batch3 e2e | #2 e2e acceptance | 最高殘餘風險複合 smoke | [`risk-based-rerun-batch3-e2e-2026-07-18.txt`](pytest-audit/risk-based-rerun-batch3-e2e-2026-07-18.txt) |

另執行日常閘與 guard，證明未弱化預設品質閘：

| 檢查 | 原始輸出 |
|---|---|
| `pytest -m "not integration" -q` | [`risk-based-rerun-default-gate-2026-07-18.txt`](pytest-audit/risk-based-rerun-default-gate-2026-07-18.txt) |
| `tests/test_deselection_guard.py` | [`risk-based-rerun-guard-2026-07-18.txt`](pytest-audit/risk-based-rerun-guard-2026-07-18.txt) |

---

## 5. 環境摘要

| 項目 | 值 |
|---|---|
| cwd | `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\8eba824b` |
| worktree_id | `8eba824b` |
| Python | `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe` |
| flags | `-X utf8` |
| pytest | 9.1.1（venv） |
| platform | win32 / Python 3.11.9 |
| grok | `127.0.0.1:8318` TCP **可達**；model `grok-4.3` |
| law_index | `data/law_index.db` **存在** |
| TWINKLE_HUB_TOKEN | **已設定**（值不記錄） |
| GOV_AI_ENABLE_TWINKLE_MCP | 非 `1`（測試碼不依賴） |
| real_note | `tests/fixtures/real_note.txt` **存在** |
| preflight 時間 | `2026-07-18T20:36:39` |

---

## 6. 執行結果總覽

| # | 測試 | 決策 | 批次 | 結果 | call 耗時 | 退出碼（批次） | 阻礙 |
|---:|---|---|---|---|---:|---:|---|
| 4 | `test_grok_pong_integration` | MUST | batch1 | **PASSED** | 1.11s | **0** | 無 |
| 1 | `test_detect_domain_real_grok_returns_law` | MUST | batch1 | **PASSED** | 2.45s | **0** | 無 |
| 3 | `test_detect_gaps_real_grok` | MUST | batch1 | **PASSED** | 4.11s | **0** | 無 |
| 6 | `test_generate_questions_real_grok` | MUST | batch1 | **PASSED** | 6.50s | **0** | 無 |
| 5 | `test_run_pipeline_real_grok` | MUST | batch2 | **PASSED** | 51.72s | **0** | 無 |
| 8 | `test_search_real_twinkle_hub` | MUST | batch2 | **PASSED** | 6.83s | **0** | 無 |
| 7 | `test_retrieve_for_gap_real_twinkle_smoke` | MUST | batch2 | **PASSED** | 6.69s | **0** | 無 |
| 2 | `test_e2e_acceptance_real` | MUST | batch3 | **PASSED** | 102.91s | **0** | 無 |

**Integration 補跑：8/8 PASSED，0 SKIPPED，0 FAILED，0 BLOCKED**

| 附加檢查 | 結果 | 退出碼 | 耗時 |
|---|---|---:|---|
| 預設閘 `-m "not integration"` | **109 passed, 8 deselected** | **0** | 5.05s |
| deselection guard（3 tests） | **3 passed** | **0** | 4.16s |

Session 耗時合計（integration 三批）：14.26s + 65.36s + 102.92s ≈ **182.54s（約 3 分 3 秒）**。

---

## 7. 逐項詳情

### 7.1 #4 `tests/test_llm.py::test_grok_pong_integration`

- **決策**：MUST（基礎設施連通；低成本前置）
- **結果**：PASSED（1.11s call）
- **命令**（屬 batch1，見 §8）
- **環境**：TCP 8318 可達
- **阻礙**：無

### 7.2 #1 `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

- **決策**：MUST（模型語意 → domain 路由）
- **結果**：PASSED（2.45s call）
- **環境**：真 GrokClient → `127.0.0.1:8318/v1` / `grok-4.3`
- **阻礙**：無

### 7.3 #3 `tests/test_gap.py::test_detect_gaps_real_grok`

- **決策**：MUST（gap 語意）
- **結果**：PASSED（4.11s call）
- **阻礙**：無

### 7.4 #6 `tests/test_questions.py::test_generate_questions_real_grok`

- **決策**：MUST（問題語意）
- **結果**：PASSED（6.50s call）
- **阻礙**：無

### 7.5 #5 `tests/test_pipeline.py::test_run_pipeline_real_grok`

- **決策**：MUST（live pipeline 穩定性 + C6）
- **結果**：PASSED（51.72s call）
- **依賴**：真 Grok；Twinkle／Law 為 Fake（測試設計）
- **阻礙**：無

### 7.6 #8 `tests/test_twinkle.py::test_search_real_twinkle_hub`

- **決策**：MUST（真 Twinkle MCP）
- **結果**：PASSED（6.83s call）
- **環境**：`TWINKLE_HUB_TOKEN` 已設定
- **阻礙**：無

### 7.7 #7 `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

- **決策**：MUST（真 keyword + LawLookup + Twinkle）
- **結果**：PASSED（6.69s call）
- **環境**：`data/law_index.db` + grok + token
- **阻礙**：無

### 7.8 #2 `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

- **決策**：MUST（§12 最高殘餘風險）
- **結果**：PASSED（102.91s call；session 102.92s）
- **品質閘（測試內斷言）**：原稿 immutable、無來源閘、法條引用、Markdown 契約、Level A 路由等
- **阻礙**：無

### 7.9 無法補跑項目

**無。** 本次 8 項 MUST 皆環境就緒且實際執行通過。

若未來環境不足，預期阻礙對照：

| 缺失條件 | 受影響 MUST 項 | 預期行為 |
|---|---|---|
| TCP 8318 不可達 | #1–#7 | `skipif` 或 batch 無法通過前置 |
| 缺 `TWINKLE_HUB_TOKEN` | #2, #7, #8 | runtime `pytest.skip` |
| 缺 `data/law_index.db` | #2, #7 | runtime skip |
| 缺 `tests/fixtures/real_note.txt` | #2 | 測試失敗／skip（視測試碼） |

---

## 8. 可重現命令

```text
# 前置（不輸出 token 值）— 見 risk-based-rerun-preflight-2026-07-18.json

# collect
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest --collect-only -q -o addopts= -m integration

# batch1 light  （exit=0, 4 passed in 14.26s）
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -o addopts= -m integration -v --tb=short --durations=0 ^
  tests/test_llm.py::test_grok_pong_integration ^
  tests/test_domain.py::test_detect_domain_real_grok_returns_law ^
  tests/test_gap.py::test_detect_gaps_real_grok ^
  tests/test_questions.py::test_generate_questions_real_grok

# batch2 medium  （exit=0, 3 passed in 65.36s）
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -o addopts= -m integration -v --tb=short --durations=0 ^
  tests/test_pipeline.py::test_run_pipeline_real_grok ^
  tests/test_twinkle.py::test_search_real_twinkle_hub ^
  tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke

# batch3 e2e  （exit=0, 1 passed in 102.92s）
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -o addopts= -m integration -v --tb=short --durations=0 ^
  tests/test_e2e_acceptance.py::test_e2e_acceptance_real

# 預設閘未弱化  （exit=0, 109 passed, 8 deselected in 5.05s）
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -m "not integration" -q --tb=line

# allowlist / substitute guard  （exit=0, 3 passed in 4.16s）
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_deselection_guard.py -v --tb=short
```

---

## 9. 產物清單（本提交可稽核）

| 檔案 | 用途 |
|---|---|
| `docs/risk-based-test-rerun-2026-07-18.md` | 本報告：風險決策 + 命令／環境／退出碼／結果 |
| `docs/pytest-audit/risk-based-rerun-preflight-2026-07-18.json` | 前置環境布林探測 + HEAD |
| `docs/pytest-audit/risk-based-rerun-collect-2026-07-18.txt` | integration collect 原始輸出 |
| `docs/pytest-audit/risk-based-rerun-batch1-light-2026-07-18.txt` | batch1 原始 pytest 輸出 |
| `docs/pytest-audit/risk-based-rerun-batch2-medium-2026-07-18.txt` | batch2 原始 pytest 輸出 |
| `docs/pytest-audit/risk-based-rerun-batch3-e2e-2026-07-18.txt` | batch3 原始 pytest 輸出 |
| `docs/pytest-audit/risk-based-rerun-default-gate-2026-07-18.txt` | 預設 109 非 integration 閘 |
| `docs/pytest-audit/risk-based-rerun-guard-2026-07-18.txt` | deselection guard 3 passed |

---

## 10. 最終判讀

1. **風險決策**：8 個 deselected integration 測試之殘餘風險皆無法由離線 substitute 證明 → **8/8 MUST 補跑**。
2. **執行結果**：本 worktree 環境就緒，**8/8 實跑 PASSED**（exit 0），無 SKIP／FAIL／BLOCKED。
3. **品質閘未弱化**：預設 `-m "not integration"` 仍為 **109 passed, 8 deselected**；guard 3/3 PASSED；未改測試碼或 allowlist。
4. **與「acceptable_unexecuted」並存**：日常 CI 可持續排除 integration；本紀錄證明在 grok／Twinkle／law_db 就緒時，殘餘風險路徑可實際通過。
