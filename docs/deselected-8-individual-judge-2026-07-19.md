# 8 個 deselected 測試：單獨執行判定報告（2026-07-19）

> **任務**：在**不套用**目前 deselection 條件（`addopts` 內 `-m 'not integration'`）的情況下，**單獨**執行 8 個測試；保存命令、環境、逐項結果與失敗輸出；判定為 **刻意不執行** / **條件性跳過** / **測試收斂**。
>
> **禁止推論**：不得以預設閘門 `113 passed, 8 deselected` 推論這 8 支的 correctness；本報告僅依各 node id 的獨立 pytest 實跑輸出判定。

## 0. 方法論與環境

| 項目 | 值 |
|------|-----|
| 工作目錄 | `D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\9f1d227e` |
| Python | `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8` |
| Python 版本 | 3.11.9 |
| 平台 | Windows-10-10.0.26200-SP0 |
| 目前 deselection 條件（**本任務刻意不套用**） | `pyproject.toml` `addopts` 中的 `-m 'not integration'` |
| 覆寫 addopts | `-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning`（**無** mark 過濾） |
| 執行粒度 | 8 次獨立 pytest session，每次只傳 1 個 node id |
| 時間戳 | `2026-07-19T02:06:49+08:00` |
| grok proxy | `http://127.0.0.1:8318/v1`（model `grok-4.3`） |
| grok proxy TCP | **可達**（`127.0.0.1:8318`） |
| `TWINKLE_HUB_TOKEN` | **已設定** |
| `GOV_AI_ENABLE_TWINKLE_MCP` | unset（`null`） |
| `data/law_index.db` | **存在**（24,129,536 bytes） |

### 0.1 預設 collection 對照（僅說明誰被 deselect，不用來判定 pass/fail）

```text
pytest --collect-only -q --deselected-details --color=no
→ 113/121 tests collected (8 deselected)
→ 8 支一律 reason: deselected by -m 'not integration'
```

integration 集合（覆寫 addopts 後 `-m integration`）：

```text
8/121 tests collected (113 deselected)
# node id 清單與 allowlist / 下方 §1 八支完全一致
```

### 0.2 重現指令（PowerShell）

```powershell
$py = 'D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe'
$addopts = '-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning'
$t = 'tests/test_llm.py::test_grok_pong_integration'  # 替換為目標 node id
& $py -X utf8 -m pytest $t -o "addopts=$addopts" -v --tb=long --color=no
```

### 0.3 可稽核原始產物

| 檔案 | 內容 |
|------|------|
| [`docs/pytest-audit/deselected-8-individual-judge-2026-07-19.txt`](pytest-audit/deselected-8-individual-judge-2026-07-19.txt) | 完整命令 + 環境 probe + 8 次 stdout + exit/wall |
| [`docs/pytest-audit/deselected-8-individual-judge-2026-07-19.json`](pytest-audit/deselected-8-individual-judge-2026-07-19.json) | 機器可讀逐項狀態與判定欄位 |
| 本檔 | 人類可讀判定報告 |

## 1. 單獨實跑總覽（8/8，非推論）

| # | node ID | 結果 | pytest 摘要 | wall（s） | exit | 失敗輸出 |
|---|---------|------|-------------|-----------|------|----------|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | **pass** | `1 passed in 3.14s` | 3.94 | 0 | （無） |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | **pass** | `1 passed in 120.05s (0:02:00)` | 120.87 | 0 | （無） |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | **pass** | `1 passed in 4.17s` | 5.15 | 0 | （無） |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | **pass** | `1 passed in 1.54s` | 2.33 | 0 | （無） |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | **pass** | `1 passed in 80.14s (0:01:20)` | 80.92 | 0 | （無） |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | **pass** | `1 passed in 7.85s` | 8.52 | 0 | （無） |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | **pass** | `1 passed in 8.46s` | 9.19 | 0 | （無） |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | **pass** | `1 passed in 2.74s` | 3.69 | 0 | （無） |

**計數（依獨立實跑分類）**

| status | count |
|--------|------:|
| pass | 8 |
| fail | 0 |
| skip | 0 |
| error | 0 |
| **合計** | **8** |

本輪**無任何失敗輸出**可保存（0 fail / 0 error）；skip 亦為 0。

## 2. 判定分類定義

| 類別 | 定義 | 層級 |
|------|------|------|
| **刻意不執行** | 設定／策略在 **collection** 即 deselect，日常預設閘門不跑 | L1 collection |
| **條件性跳過** | 選入後因環境前置不足而 `skipif` / `pytest.skip` | L2 runtime |
| **測試收斂** | 離線 substitute 已覆蓋確定性契約，integration 僅驗證外部 I/O／模型品質；解釋「為何可接受平時不跑」，**不是** collection 排除的直接機制 | L3 策略／覆蓋 |

## 3. 逐項判定

### 3.1 `tests/test_domain.py::test_detect_domain_real_grok_returns_law`

| 欄位 | 值 |
|------|-----|
| 單獨實跑 | **pass**（`1 passed in 3.14s`，exit=0，wall=3.94s） |
| 失敗輸出 | 無 |
| 預設未執行直接原因 | **刻意不執行**：`@pytest.mark.integration` + `addopts -m 'not integration'` |
| 選入後第二層 | **條件性跳過**：`@pytest.mark.skipif(not _grok_reachable(), ...)`（本輪 proxy 可達，**未觸發**） |
| 測試收斂 | 有 substitute `test_detect_domain_law`（FakeLLM）；解釋可接受 deselect，非本次未跑機制 |
| **綜合判定** | 日常未跑＝**刻意不執行**；本輪單獨執行＝pass（非 skip/fail） |

### 3.2 `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

| 欄位 | 值 |
|------|-----|
| 單獨實跑 | **pass**（`1 passed in 120.05s`，exit=0，wall=120.87s） |
| 失敗輸出 | 無 |
| 預設未執行直接原因 | **刻意不執行** |
| 選入後第二層 | **條件性跳過**：缺 `law_index.db` / grok / Twinkle token 時函式內 skip（本輪齊備，**未觸發**） |
| 測試收斂 | 離線 e2e 結構不變式、品質閘、pipeline 不變式等 substitute |
| **綜合判定** | 日常未跑＝**刻意不執行**；本輪＝pass |

### 3.3 `tests/test_gap.py::test_detect_gaps_real_grok`

| 欄位 | 值 |
|------|-----|
| 單獨實跑 | **pass**（`1 passed in 4.17s`，exit=0，wall=5.15s） |
| 失敗輸出 | 無 |
| 預設未執行直接原因 | **刻意不執行** |
| 選入後第二層 | **條件性跳過**（grok skipif；本輪未觸發） |
| 測試收斂 | `test_detect_gaps_keeps_only_partial_and_missing` |
| **綜合判定** | 日常未跑＝**刻意不執行**；本輪＝pass |

### 3.4 `tests/test_llm.py::test_grok_pong_integration`

| 欄位 | 值 |
|------|-----|
| 單獨實跑 | **pass**（`1 passed in 1.54s`，exit=0，wall=2.33s） |
| 失敗輸出 | 無 |
| 預設未執行直接原因 | **刻意不執行** |
| 選入後第二層 | **條件性跳過**（grok skipif；本輪未觸發） |
| 測試收斂 | `test_grokclient_builds_request_body` |
| **綜合判定** | 日常未跑＝**刻意不執行**；本輪＝pass |

### 3.5 `tests/test_pipeline.py::test_run_pipeline_real_grok`

| 欄位 | 值 |
|------|-----|
| 單獨實跑 | **pass**（`1 passed in 80.14s`，exit=0，wall=80.92s） |
| 失敗輸出 | 無 |
| 預設未執行直接原因 | **刻意不執行** |
| 選入後第二層 | **條件性跳過**（grok skipif；本輪未觸發） |
| 測試收斂 | pipeline 不變式 / malformed fallback / citation check / 只掛引用來源 |
| **綜合判定** | 日常未跑＝**刻意不執行**；本輪＝pass |

### 3.6 `tests/test_questions.py::test_generate_questions_real_grok`

| 欄位 | 值 |
|------|-----|
| 單獨實跑 | **pass**（`1 passed in 7.85s`，exit=0，wall=8.52s） |
| 失敗輸出 | 無 |
| 預設未執行直接原因 | **刻意不執行** |
| 選入後第二層 | **條件性跳過**（grok skipif；本輪未觸發） |
| 測試收斂 | multiline / strip blank 等 FakeLLM 測試 |
| **綜合判定** | 日常未跑＝**刻意不執行**；本輪＝pass |

### 3.7 `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`

| 欄位 | 值 |
|------|-----|
| 單獨實跑 | **pass**（`1 passed in 8.46s`，exit=0，wall=9.19s） |
| 失敗輸出 | 無 |
| 預設未執行直接原因 | **刻意不執行** |
| 選入後第二層 | **條件性跳過**（law_db skipif + grok skipif + 缺 token 時 skip；本輪未觸發） |
| 測試收斂 | Level A 排序 + mock Twinkle + exclusion_correctness_blind_spot |
| **綜合判定** | 日常未跑＝**刻意不執行**；本輪＝pass |

### 3.8 `tests/test_twinkle.py::test_search_real_twinkle_hub`

| 欄位 | 值 |
|------|-----|
| 單獨實跑 | **pass**（`1 passed in 2.74s`，exit=0，wall=3.69s） |
| 失敗輸出 | 無 |
| 預設未執行直接原因 | **刻意不執行** |
| 選入後第二層 | **條件性跳過**（函式內缺 `TWINKLE_HUB_TOKEN` → `pytest.skip`；本輪 token 已設，**未觸發**） |
| 測試收斂 | parse / session reuse / transport failure mock 測試 |
| **綜合判定** | 日常未跑＝**刻意不執行**；本輪＝pass |

## 4. 總判定表

| # | node ID | 日常未跑主因 | 本輪單獨結果 | 本輪是否觸發條件性跳過 | 測試收斂（策略層） |
|---|---------|--------------|--------------|------------------------|-------------------|
| 1–8 全部 | 見 §1 / §3 | **刻意不執行** | **pass** × 8 | **否** × 8 | 有（allowlist substitute） |

### 4.1 一句結論

1. **預設品質閘為何不跑這 8 支**：全部是 **刻意不執行**（collection deselect：`addopts` 的 `-m 'not integration'`），**不是** session 中的 skipped，也**不是**測試收斂「自動省略」。
2. **拿掉 deselection 後單獨實跑**：本環境（grok proxy 可達、token 已設、law db 存在）下 **8 pass / 0 fail / 0 skip / 0 error**；失敗輸出欄為空。
3. **條件性跳過**：是選入後的 **第二層** runtime 防護；本輪**未觸發**（0 skip）。若 proxy/token/db 缺失，同一批測試會變成 skip 而非 pass——與 collection deselect 屬不同層級。
4. **測試收斂**：解釋 allowlist `acceptable_unexecuted` 與離線 substitute 為何足夠支撐日常閘門；**不**是 collection 排除的直接原因。
5. 本任務**未**修改 `addopts`、marker、品質閘或產品碼；僅調查執行與報告落盤。

## 5. 與「113 passed, 8 deselected」的邊界

| 主張 | 是否由本任務證據支持 |
|------|----------------------|
| 預設閘門 deselect 8 支 integration | 是（`--deselected-details`） |
| 8 支在不套用 deselection 下單獨結果 | **是**——§1 與 audit txt/json |
| 以 `113 passed` 推論 8 支 integration 正確 | **否**——禁止；本報告以獨立 session 實跑判定 |
| 8 支未跑是因為「條件性跳過」 | **否**（日常層）；條件性跳過僅為選入後第二層 |
| 8 支未跑是因為「測試收斂導致 pytest 漏收」 | **否**；pytest 有 collect 後 deselect，node id 完整可見 |

## 6. 提交檔案清單（預期）

- `docs/deselected-8-individual-judge-2026-07-19.md`（本報告）
- `docs/pytest-audit/deselected-8-individual-judge-2026-07-19.txt`（完整 stdout）
- `docs/pytest-audit/deselected-8-individual-judge-2026-07-19.json`（機器可讀）
