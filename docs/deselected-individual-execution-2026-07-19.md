# Deselected 測試逐一單獨執行報告（2026-07-19）

> **任務**：在**不套用**目前選取條件（`addopts` 內 `-m 'not integration'`）下，**單獨**執行每個 deselected 測試，記錄 `pass` / `fail` / `skip` / `error`。
>
> **禁止推論**：不得以預設閘門的 `110 passed` 推論這 8 支的 correctness；本報告僅依各 node id 的獨立 pytest 實跑輸出判定。

## 0. 方法論

| 項目 | 值 |
|------|-----|
| 工作目錄 | 本 worktree 根目錄 |
| Python | `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8` |
| 目前選取條件（**本任務刻意不套用**） | `pyproject.toml` `addopts` 中的 `-m 'not integration'` |
| 覆寫方式 | 每次 `-o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning"`（**無** mark 過濾） |
| 執行粒度 | 8 次獨立 session，每次只傳 **1 個** node id |
| 狀態分類 | 依該次輸出中的 `1 passed` / `1 failed` / `1 skipped` / `1 error` + exit code |
| grok proxy | `http://127.0.0.1:8318/v1`（model `grok-4.3`）；實測 TCP `127.0.0.1:8318` 可達 |
| 環境快照 | `TWINKLE_HUB_TOKEN`=set；`GOV_AI_ENABLE_TWINKLE_MCP`=unset（None） |

### 0.1 預設 collection 對照（僅列出誰被 deselect，不用來判定 pass/fail）

```text
pytest --collect-only -q --deselected-details
→ 110/118 tests collected (8 deselected)
→ 8 支一律 reason: deselected by -m 'not integration'
```

完整原始 log / 機器可讀結果：

- [`docs/pytest-audit/deselected-individual-runs-2026-07-19.txt`](pytest-audit/deselected-individual-runs-2026-07-19.txt)
- [`docs/pytest-audit/deselected-individual-results-2026-07-19.json`](pytest-audit/deselected-individual-results-2026-07-19.json)

### 0.2 重現指令（PowerShell）

```powershell
$py = 'D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe'
$addopts = "-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning"
$t = 'tests/test_llm.py::test_grok_pong_integration'  # 替換為目標 node id
& $py -X utf8 -m pytest $t -o "addopts=$addopts" -v --tb=short
```

## 1. 總覽（8/8 實跑，非推論）

| # | node ID | 結果 | pytest 摘要 | wall（s） | exit |
|---|---------|------|-------------|-----------|------|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | **pass** | `1 passed in 4.16s` | 5.44 | 0 |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | **pass** | `1 passed in 117.59s` | 118.50 | 0 |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | **pass** | `1 passed in 4.90s` | 5.74 | 0 |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | **pass** | `1 passed in 1.10s` | 1.94 | 0 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | **pass** | `1 passed in 66.31s` | 67.30 | 0 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | **pass** | `1 passed in 5.81s` | 6.59 | 0 |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | **pass** | `1 passed in 6.53s` | 7.28 | 0 |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | **pass** | `1 passed in 3.85s` | 4.58 | 0 |

**計數（依獨立實跑分類，非 110 passed）**

| status | count |
|--------|------:|
| pass | 8 |
| fail | 0 |
| skip | 0 |
| error | 0 |
| **合計** | **8** |

## 2. 逐項詳情

### 2.1 `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 欄位 | 值 |
|------|-----|
| 結果 | **pass** |
| 預設為何 deselected | `-m 'not integration'`（collection） |
| 本次是否套用該條件 | **否**（addopts 覆寫，無 mark 過濾） |
| 實測輸出 | `PASSED` → `1 passed in 4.16s`；exit=0；wall=5.44s |
| 依賴 | 真實 grok proxy `:8318` |

### 2.2 `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 欄位 | 值 |
|------|-----|
| 結果 | **pass** |
| 預設為何 deselected | `-m 'not integration'` |
| 本次是否套用該條件 | **否** |
| 實測輸出 | `PASSED` → `1 passed in 117.59s (0:01:57)`；exit=0；wall=118.50s |
| 依賴 | grok + law db + Twinkle（本環境 token 已設） |

### 2.3 `tests/test_gap.py::test_detect_gaps_real_grok`

| 欄位 | 值 |
|------|-----|
| 結果 | **pass** |
| 預設為何 deselected | `-m 'not integration'` |
| 本次是否套用該條件 | **否** |
| 實測輸出 | `PASSED` → `1 passed in 4.90s`；exit=0；wall=5.74s |

### 2.4 `tests/test_llm.py::test_grok_pong_integration`

| 欄位 | 值 |
|------|-----|
| 結果 | **pass** |
| 預設為何 deselected | `-m 'not integration'` |
| 本次是否套用該條件 | **否** |
| 實測輸出 | `PASSED` → `1 passed in 1.10s`；exit=0；wall=1.94s |

### 2.5 `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 欄位 | 值 |
|------|-----|
| 結果 | **pass** |
| 預設為何 deselected | `-m 'not integration'` |
| 本次是否套用該條件 | **否** |
| 實測輸出 | `PASSED` → `1 passed in 66.31s (0:01:06)`；exit=0；wall=67.30s |

### 2.6 `tests/test_questions.py::test_generate_questions_real_grok`

| 欄位 | 值 |
|------|-----|
| 結果 | **pass** |
| 預設為何 deselected | `-m 'not integration'` |
| 本次是否套用該條件 | **否** |
| 實測輸出 | `PASSED` → `1 passed in 5.81s`；exit=0；wall=6.59s |

### 2.7 `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 欄位 | 值 |
|------|-----|
| 結果 | **pass** |
| 預設為何 deselected | `-m 'not integration'` |
| 本次是否套用該條件 | **否** |
| 實測輸出 | `PASSED` → `1 passed in 6.53s`；exit=0；wall=7.28s |
| 備註 | 歷史報告（2026-07-18）曾因缺 token / MCP flag 為 **skip**；本次獨立實跑為 **pass**，不得沿用舊結論 |

### 2.8 `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 欄位 | 值 |
|------|-----|
| 結果 | **pass** |
| 預設為何 deselected | `-m 'not integration'` |
| 本次是否套用該條件 | **否** |
| 實測輸出 | `PASSED` → `1 passed in 3.85s`；exit=0；wall=4.58s |

## 3. 與「110 passed」的邊界說明

| 主張 | 是否由本任務證據支持 |
|------|----------------------|
| 預設閘門 `pytest` 選取 110 支、deselect 8 支 | 是（collection 輸出）；**不**等於 8 支 correct |
| 8 支 deselected 在**不套用** `-m 'not integration'` 下單獨執行之結果 | **是**——本報告 §1–§2 與 audit 原始 log/json |
| 以 `110 passed` 推論 8 支 integration 正確 | **否**——任務明文禁止；亦未採用此推論 |

## 4. 結論

1. 預設 deselected 清單仍為 **8** 支 `@pytest.mark.integration` 測試，排除機制為 `addopts` 的 `-m 'not integration'`。
2. 在**覆寫 addopts、不套用該 mark 過濾**的前提下，對 8 個 node id **各開一次獨立 pytest session** 實跑。
3. 分類結果：**8 pass / 0 fail / 0 skip / 0 error**（依每次 session 的 `1 passed` + exit=0，非由預設 110 推論）。
4. 可稽核產物已落盤：本 md + `docs/pytest-audit/deselected-individual-runs-2026-07-19.txt` + `docs/pytest-audit/deselected-individual-results-2026-07-19.json`。
5. 本任務**未**修改測試篩選、品質閘或產品碼；僅調查執行與報告落盤。

## 5. 提交時檔案清單（預期）

- `docs/deselected-individual-execution-2026-07-19.md`（本報告）
- `docs/pytest-audit/deselected-individual-runs-2026-07-19.txt`（完整 stdout）
- `docs/pytest-audit/deselected-individual-results-2026-07-19.json`（機器可讀逐項狀態）
