# 被排除測試：逐項 failing-first 對照與 NOT-REPRODUCIBLE 判定

> **任務**：為每個被 `-m 'not integration'` 排除的測試建立或執行先失敗對照情境，證明其未執行是否可能掩蓋 correctness 缺陷；若無法以產品失敗形式重現 → 標記 **`NOT-REPRODUCIBLE`** 並記錄限制。
>
> **硬約束**：原稿逐字不可變、無來源/【待補證】→`pending_evidence`、只掛實際引用來源、法條引用須通過離線查核；integration 平時跳過。未動 `BACKLOG.md`、未弱化品質閘。

## 1. 方法

| 步驟 | 作法 |
|------|------|
| 鎖定集合 | `tests/deselected_allowlist.json` 8 個 node id（== 預設 deselected） |
| 對照設計 | 每個 node 至少 1 個 **failing-first 候選**（現況健康應 PASS；契約破壞應紅） |
| 驗證層盲區 | #7 額外鎖定 vacuous empty smoke（驗證設計缺陷，非產品回空） |
| Live 補證 | 環境就緒時分批重跑 8 個 integration 本體 |
| 判定規則 | 對照 PASS + live PASS/或 determinism 路徑健康 → 產品缺陷路徑 **`NOT-REPRODUCIBLE`** |

### 1.1 Python / 命令前綴

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
```

## 2. 產物清單（主張 ↔ 檔案）

| 主張 | 檔案 |
|------|------|
| 8 項 failing-first 對照 + map 閘 | [`tests/test_excluded_failing_controls.py`](../tests/test_excluded_failing_controls.py) |
| allowlist 對照映射 | [`tests/deselected_allowlist.json`](../tests/deselected_allowlist.json) |
| guard 計數 + 8× NOT-REPRODUCIBLE | [`tests/test_deselection_guard.py`](../tests/test_deselection_guard.py) |
| audit script 同步 | [`scripts/refresh_pytest_audit.py`](../scripts/refresh_pytest_audit.py) |
| live batch1（domain/llm/gap/questions） | [`docs/pytest-audit/failing-controls-live-batch1-2026-07-19.txt`](pytest-audit/failing-controls-live-batch1-2026-07-19.txt) |
| live batch2（pipeline/twinkle/retrieve） | [`docs/pytest-audit/failing-controls-live-batch2-2026-07-19.txt`](pytest-audit/failing-controls-live-batch2-2026-07-19.txt) |
| live batch3（e2e） | [`docs/pytest-audit/failing-controls-live-batch3-e2e-2026-07-19.txt`](pytest-audit/failing-controls-live-batch3-e2e-2026-07-19.txt) |
| 本報告 | 本檔 |

## 3. 逐項對照結果

| # | 排除 node id | Failing-first 對照 | 對照結果 | Live integration | 產品缺陷路徑 | 限制 / 殘餘缺口 |
|---|--------------|-------------------|----------|------------------|--------------|-----------------|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `test_control_01_domain_legal_label_contract` | **PASSED** | **PASSED** | **`NOT-REPRODUCIBLE`** | 真模型對 borderline 文本的語意品質 |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `test_control_02_e2e_offline_quality_gates` | **PASSED** | **PASSED** (~146s) | **`NOT-REPRODUCIBLE`** | 真 Grok+Twinkle 複合品質／`[^n]` flaky 邊界 |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `test_control_03_gap_uncovered_question_must_surface` | **PASSED** | **PASSED** | **`NOT-REPRODUCIBLE`** | 真模型缺口判斷品質 |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `test_control_04_grok_client_parse_and_endpoint_contract` | **PASSED** | **PASSED** | **`NOT-REPRODUCIBLE`** | 純 TCP 連通屬運維；parse 契約已鎖 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `test_control_05_pipeline_c6_pending_when_no_sources` | **PASSED** | **PASSED** | **`NOT-REPRODUCIBLE`** | 真模型 domain/questions/gaps 輸出品質 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `test_control_06_questions_clean_list_contract` | **PASSED** | **PASSED** | **`NOT-REPRODUCIBLE`** | 真模型出題品質 |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `test_control_07_*` + `07b` | **PASSED** | **PASSED** | **`NOT-REPRODUCIBLE`**（產品）／驗證層 vacuous empty **已證實** | 真 Twinkle I/O + 真 keyword；smoke 本體仍弱 |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `test_control_08_twinkle_parsed_source_contract` | **PASSED** | **PASSED** | **`NOT-REPRODUCIBLE`** | 真 Hub 可用性／session 相容 |

### 3.1 #7 驗證層盲區（非產品 FAIL，但未執行會掩蓋）

| 對照 | 證明內容 |
|------|----------|
| `test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot` | `out=[]` 時 #7 的三道 `all()/sort` 仍 **vacuous PASS** → 檢索全滅不會被 smoke 攔截 |
| `test_control_07b_retrieve_law_level_a_not_vacuous` | law + 真實 `LawLookup` + empty Twinkle **必須非空 Level A**；本輪 PASS → 產品路徑健康 |

因此：

- 「產品 correctness 已壞、因排除而未被看見」→ **`NOT-REPRODUCIBLE`**
- 「未執行 + 弱 smoke 造成驗證盲區」→ **已證實**（由 07/07b 鎖定）

## 4. 執行證據

### 4.1 離線對照（10 tests）

```powershell
& $py -X utf8 -m pytest tests/test_excluded_failing_controls.py -vv --tb=short --color=no
```

```text
10 passed in 0.19s
EXIT=0
```

（含 `test_control_map_covers_all_eight_excluded` 確保 1:1 對齊 8 node id）

### 4.2 Live integration 分批

**Batch1（light）** — 4 passed / 17.09s

```text
test_detect_domain_real_grok_returns_law PASSED
test_grok_pong_integration PASSED
test_detect_gaps_real_grok PASSED
test_generate_questions_real_grok PASSED
```

**Batch2（medium）** — 3 passed / 85.45s

```text
test_run_pipeline_real_grok PASSED          (~65s)
test_search_real_twinkle_hub PASSED         (~7s)
test_retrieve_for_gap_real_twinkle_smoke PASSED (~13s)
```

**Batch3（e2e）** — 1 passed / 145.94s

```text
test_e2e_acceptance_real PASSED
```

### 4.3 預設非 integration 閘

```powershell
& $py -X utf8 -m pytest -m "not integration" -q --color=no
```

```text
123 passed, 8 deselected in 33.58s
EXITN=0
collected: 131; selected: 123; deselected: 8
```

### 4.4 Guard

```powershell
& $py -X utf8 -m pytest tests/test_deselection_guard.py -q --tb=short --color=no -s
```

```text
4 passed in 29.64s
EXITG=0
TARGETED_VERIFICATION=PASS
_EXPECTED_COUNTS = (131, 123, 8)
FAILED_OR_NOT_REPRODUCIBLE_INDEX: 8 nodes 皆含 NOT-REPRODUCIBLE 列
原始輸出：docs/pytest-audit/failing-controls-guard-2026-07-19.txt
```

## 5. NOT-REPRODUCIBLE 索引（8/8 產品缺陷路徑）

| # | status | 限制摘要 |
|---|--------|----------|
| 1–6, 8 | `NOT-REPRODUCIBLE` | determinism 契約對照 +（本輪）live PASS；殘餘僅外部模型/服務品質 |
| 7 | `NOT-REPRODUCIBLE`（產品）+ 驗證層盲區已鎖定 | 產品 law 非空；smoke vacuous empty 仍為驗證設計問題 |
| 2 附加 | 既有 e2e 離線品質閘／supplement 邊界文件 | 見 `minimal-quality-gates-regression` / `e2e-offline-quality-boundary` |

**無法重現的原因類型**（適用 1–8 產品路徑）：

1. 排除測獨有覆蓋多屬 **真 LLM 語意** 或 **外部 I/O**，離線 determinism 路徑本輪健康。
2. Live 在 grok `127.0.0.1:8318` + `TWINKLE_HUB_TOKEN` + `data/law_index.db` 就緒時 **通過**，無法展示「現行產品已壞」。
3. 未修改主程式；任務要求先失敗對照而非強行注入故障。

## 6. 品質閘未弱化

| 硬約束 | 狀態 |
|--------|------|
| 原稿逐字不可變 | control #2 + 既有 e2e 離線回歸 |
| 無來源 → `pending_evidence` | control #2 / #5 + pipeline C6 |
| 只掛實際引用來源 | 既有 correction + control #2 verified 路徑 |
| 法條離線查核 | 既有 e2e / law citation 路徑 |
| integration 平時跳過 | 維持 8 deselected |

## 7. 最終判決

| 維度 | 判決 |
|------|------|
| 8 項皆有 failing-first 對照 | **是**（`test_excluded_failing_controls.py`） |
| 產品 correctness 因排除而掩蓋 | **8/8 `NOT-REPRODUCIBLE`**（本輪對照 + live 健康） |
| 驗證層可掩蓋風險 | **#7 vacuous smoke 已證實並鎖定** |
| 預設品質閘 | **123 passed, 8 deselected**（見 §4.3 實跑） |
| 未動 BACKLOG / 未擴 scope | **是** |
