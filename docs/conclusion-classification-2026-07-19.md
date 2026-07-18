# 結論分類：非缺陷 vs 真實驗證缺口（2026-07-19）

> **任務**：逐項將既有驗證結論分類為「**非缺陷**」或「**真實驗證缺口**」；  
> 真實驗證缺口必須附 **可重現的失敗測試、預期行為、實際行為、修復後應納入的驗收命令**。  
> 僅對話輸出而無落盤／commit 視為失敗。未動 `BACKLOG.md`、未弱化品質閘。

## 0. 分類規則

| 標籤 | 定義 |
|------|------|
| **非缺陷** | 產品 correctness 路徑無法以失敗形式重現（`NOT-REPRODUCIBLE` 或 live PASS）；確定性契約已由非 integration 替代／failing-first 對照覆蓋；預設 deselect 屬可接受策略。殘餘僅外部模型語意品質或運維連通性者，**不得**冒充「真實驗證缺口」（因無法提供可重現失敗測試）。 |
| **真實驗證缺口** | 驗證設計／斷言本身可造成假綠或看不見；必須完整附：可重現失敗測試、預期行為、實際行為、修復後驗收命令。 |

機器可讀索引：[`docs/pytest-audit/conclusion-classification-2026-07-19.json`](pytest-audit/conclusion-classification-2026-07-19.json)  
分類守衛：[`tests/test_conclusion_classification.py`](../tests/test_conclusion_classification.py)

### 0.1 輸入結論來源（逐項對齊）

| 來源 | 角色 |
|------|------|
| `docs/verification-impact-conclusion-2026-07-18.md` | 8 項 integration 可接受未執行 |
| `docs/excluded-failing-controls-2026-07-19.md` | 8× failing-first + NOT-REPRODUCIBLE |
| `docs/exclusion-correctness-blind-spot-2026-07-19.md` | #7 vacuous smoke + 產品 Level A |
| `docs/deselected-8-individual-judge-2026-07-19.md` | 單獨實跑 8 pass |
| `tests/deselected_allowlist.json` | 8 node id 機器來源 |

## 1. 總表

| ID | node id | 維度 | 分類 | 產品缺陷可重現？ |
|----|---------|------|------|------------------|
| C1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | 產品＋排除策略 | **非缺陷** | 否 |
| C2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | 產品＋排除策略 | **非缺陷** | 否 |
| C3 | `tests/test_gap.py::test_detect_gaps_real_grok` | 產品＋排除策略 | **非缺陷** | 否 |
| C4 | `tests/test_llm.py::test_grok_pong_integration` | 產品＋排除策略 | **非缺陷** | 否 |
| C5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | 產品＋排除策略 | **非缺陷** | 否 |
| C6 | `tests/test_questions.py::test_generate_questions_real_grok` | 產品＋排除策略 | **非缺陷** | 否 |
| C7-product | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | 產品 correctness | **非缺陷** | 否 |
| C7-verification | 同上 | **驗證設計** | **真實驗證缺口** | （產品否；驗證層是） |
| C8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | 產品＋排除策略 | **非缺陷** | 否 |

**計數**：非缺陷 **8**／真實驗證缺口 **1**（C7 拆兩維；見 JSON `summary`）。

---

## 2. 非缺陷（C1–C6、C7-product、C8）

下列每一項：failing-first 對照 PASS、（本輪或歷史）live PASS 或 `NOT-REPRODUCIBLE`，確定性路徑有 substitute。殘餘「真模型品質／外部 I/O」**不**升級為真實驗證缺口（無法附可重現失敗測試證明產品已壞）。

### C1 domain — 非缺陷

| 欄位 | 內容 |
|------|------|
| 結論 | 排除不掩蓋產品標籤契約缺陷 |
| 理由 | `test_detect_domain_law` + `test_control_01_*` 鎖定 FakeLLM 契約；live 歷史 PASS |
| 殘餘 | 真 Grok borderline 語意（非閘門邏輯） |
| 證據 | `docs/excluded-failing-controls-2026-07-19.md` §3 #1 |

### C2 e2e — 非缺陷

| 欄位 | 內容 |
|------|------|
| 結論 | 四硬閘（原稿不可變、`pending_evidence`、只掛引用、法條離線查核）離線已鎖 |
| 理由 | `test_e2e_minimal_quality_gates_offline_regression`、`test_control_02_*` PASS；live e2e PASS |
| 殘餘 | 真 Grok+Twinkle 複合寫作品質 |
| 證據 | `minimal-quality-gates-regression`、`e2e-offline-quality-boundary`、failing-controls |

### C3 gaps — 非缺陷

| 欄位 | 內容 |
|------|------|
| 結論 | 過濾／結構契約健康 |
| 理由 | `test_detect_gaps_keeps_only_partial_and_missing` + control #3 |
| 殘餘 | 真模型 partial/missing 語意 |

### C4 grok pong — 非缺陷

| 欄位 | 內容 |
|------|------|
| 結論 | 客戶端 parse/endpoint 契約健康 |
| 理由 | `test_grokclient_builds_request_body` + control #4 |
| 殘餘 | proxy TCP 運維 |

### C5 pipeline — 非缺陷

| 欄位 | 內容 |
|------|------|
| 結論 | C6／citation／引用過濾 determinism 健康 |
| 理由 | pipeline 不變式 + control #5 |
| 殘餘 | 真模型各階段輸出品質 |

### C6 questions — 非缺陷

| 欄位 | 內容 |
|------|------|
| 結論 | 清單淨空契約健康 |
| 理由 | questions 兩件套 + control #6 |
| 殘餘 | 真模型出題品質 |

### C7-product retrieve — 非缺陷（產品路徑）

| 欄位 | 內容 |
|------|------|
| 結論 | law + 真實 `LawLookup` + Twinkle 空 → 非空 Level A；**產品回空 NOT-REPRODUCIBLE** |
| 理由 | `test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`、`test_control_07b_*` PASS |
| 證據 | `docs/exclusion-correctness-blind-spot-2026-07-19.md` §3–§4 |

### C8 twinkle hub — 非缺陷

| 欄位 | 內容 |
|------|------|
| 結論 | MCP 解析契約健康；空 hit 綠燈屬 API「可無結果」語意 |
| 理由 | mock 三件套 + control #8；與 #7「law 合成路徑應有 Level A」不同 |
| 殘餘 | 真 Hub 可用性／session |

---

## 3. 真實驗證缺口（僅 C7-verification）

### C7-verification：`test_retrieve_for_gap_real_twinkle_smoke` 的 vacuous empty 斷言

#### 3.1 問題陳述

`tests/test_retrieve.py` 現況 smoke：

```python
assert all(isinstance(s, Source) for s in out)
assert all(s.level in ("A", "B") for s in out)
keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
assert keys == sorted(keys)
```

當 `out == []` 時三式皆 True → **檢索全滅仍綠**。  
預設 `addopts` 的 `-m 'not integration'` 更使此 smoke 日常不執行。

#### 3.2 預期行為

smoke（或等價驗收）在 `out == []` 時**必須失敗**，至少：

```python
assert out, "retrieve smoke 不得 vacuous empty"
```

使「檢索全滅」不可假綠。law 領域 Level A 非空另由離線回歸鎖定（已存在）。

#### 3.3 實際行為

| 觀測 | 結果 |
|------|------|
| 現行 smoke 套在 `[]` | **全綠（vacuous pass）** |
| 產品 law+LawLookup（Twinkle 空） | **非空 Level A（本輪健康）** |
| 預設 CI | smoke 被 deselect，連 vacuous 本身都不跑 |

#### 3.4 可重現的失敗測試（鎖定缺口）

| 測試 | 角色 | 現況期望 |
|------|------|----------|
| `tests/test_conclusion_classification.py::test_gap_c7_current_smoke_vacuous_pass_on_empty` | 重現**實際**行為：現行三斷言接受 empty | **PASSED**（缺口仍開） |
| `tests/test_conclusion_classification.py::test_gap_c7_strengthened_contract_fails_on_empty` | 重現**預期**修復契約：非空要求對 empty 必須 `AssertionError` | **PASSED**（證明修復後契約可攔截） |
| 既有 `test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot` | 同實際行為鎖定 | PASSED |
| 既有 `test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot` | 同 | PASSED |

重跑（可重現）：

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
& $py -X utf8 -m pytest `
  tests/test_conclusion_classification.py::test_gap_c7_current_smoke_vacuous_pass_on_empty `
  tests/test_conclusion_classification.py::test_gap_c7_strengthened_contract_fails_on_empty `
  -vv --tb=short --color=no
```

#### 3.5 修復後應納入的驗收命令

修復方向（**本任務不修改主程式／integration 斷言**，僅分類與鎖定；修復屬後續）：  
在 `test_retrieve_for_gap_real_twinkle_smoke` 於既有三斷言**之前**加入非空契約，並同步調整 characterization 測（vacuous 測應改為期望 raise 或移除）。

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"

# A. 盲區關閉訊號：現行 vacuous characterization 應改為 FAILED 或被替換
& $py -X utf8 -m pytest `
  tests/test_conclusion_classification.py::test_gap_c7_current_smoke_vacuous_pass_on_empty `
  -vv --tb=short --color=no
# 修復後期望：FAILED（表示現行 smoke 已不再接受 empty）

# B. 強化契約 + 產品 Level A 離線路徑
& $py -X utf8 -m pytest `
  tests/test_conclusion_classification.py::test_gap_c7_strengthened_contract_fails_on_empty `
  tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty `
  tests/test_excluded_failing_controls.py::test_control_07b_retrieve_law_level_a_not_vacuous `
  -vv --tb=short --color=no
# 修復後期望：皆 PASSED

# C. 日常非 integration 閘（不得弱化四硬閘）
& $py -X utf8 -m pytest -m "not integration" -q --color=no
# 修復後期望：全綠；collected/selected 計數依當時測試數更新

# D. （可選）環境就緒時 integration smoke 本體
& $py -X utf8 -m pytest tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke `
  -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" `
  -vv --tb=short --color=no
```

#### 3.6 為何不算「產品缺陷」卻算「真實驗證缺口」

- 產品 law 路徑本輪**不回空** → 無法主張 correctness 已壞。  
- 但驗證層**允許 empty 綠燈** + 預設 deselect → 若未來 law 路徑回歸為空，日常 CI **看不見**。  
- 此為驗證設計缺口，符合「真實驗證缺口」定義，且已附完整四要件。

---

## 4. 刻意不列為真實驗證缺口的殘餘風險

| 殘餘 | 涉及 | 為何不是「真實驗證缺口」 |
|------|------|--------------------------|
| 真 Grok 語意品質 | C1 C2 C3 C5 C6 | live 通過或無法以失敗測試鎖定「已壞」；屬條件式 integration 範圍 |
| 真 Twinkle I/O | C2 C7 C8 | 同上；空 hit 對 #8 可為合法 API 語意 |
| Proxy TCP | C4 | 運維探測，非邏輯回歸 |

---

## 5. 品質閘未弱化

| 硬約束 | 狀態 |
|--------|------|
| 原稿逐字不可變 | 離線 e2e／control #2 |
| 無來源 → `pending_evidence` | pipeline C6／control #2/#5 |
| 只掛實際引用來源 | correction／control #2 |
| 法條引用離線查核 | e2e／law citation |
| integration 平時跳過 | 維持 8 deselected |

---

## 6. 本輪實跑驗收

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
& $py -X utf8 -m pytest tests/test_conclusion_classification.py -vv --tb=short --color=no
# 8 passed in 0.03s  EXIT=0

& $py -X utf8 -m pytest -m "not integration" -q --color=no
# 131 passed, 8 deselected in 31.06s  EXITN=0

& $py -X utf8 -m pytest --collect-only -q -o addopts=
# 139 tests collected

& $py -X utf8 -m pytest --collect-only -m "not integration" -q
# 131/139 tests collected (8 deselected)

& $py -X utf8 -m pytest tests/test_deselection_guard.py -q --tb=line --color=no
# 4 passed in 30.14s  EXITG=0
# _EXPECTED_COUNTS = (139, 131, 8)
```

### 6.1 產物清單（主張 ↔ 檔案）

| 主張 | 檔案 |
|------|------|
| 逐項分類報告 | `docs/conclusion-classification-2026-07-19.md`（本檔） |
| 機器可讀索引 | `docs/pytest-audit/conclusion-classification-2026-07-19.json` |
| 分類守衛 + 缺口四要件測試 | `tests/test_conclusion_classification.py` |
| 未動 BACKLOG | commit 不含 BACKLOG* 任務改寫 |

## 7. 最終判決

1. **8 項產品／排除策略結論**：皆 **非缺陷**（C1–C6、C7-product、C8）。  
2. **1 項驗證設計結論**：C7-verification **真實驗證缺口**，已附可重現測試、預期／實際行為、修復後驗收命令。  
3. 外部模型／服務殘餘風險維持 integration 條件式補跑，**不**降級品質閘，也**不**偽造成「真實驗證缺口」包裝。
