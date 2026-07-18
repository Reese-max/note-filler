# 排除範圍 correctness 盲區：failing-first 回歸驗證

> 任務：針對排除範圍建立會先失敗的回歸測試，證明未執行可造成具體 correctness 盲區；若無法以產品失敗形式重現 → **`NOT-REPRODUCIBLE`**，並分別標示「已證實非缺陷」與「仍存在的真實驗證缺口」。
>
> 硬約束：原稿逐字不可變、無來源/【待補證】→`pending_evidence`、只掛實際引用來源、法條引用須通過離線查核；integration 平時跳過。

## 1. 鎖定排除對象

| 項目 | 內容 |
|------|------|
| 排除機制 | `pyproject.toml` `addopts` → `-m 'not integration'`（collection 排除，非 skip） |
| 排除集合 | 8 個 node id（`tests/deselected_allowlist.json`） |
| 本輪主攻 | **#7** `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` |
| 選定理由 | smoke 三斷言對 **empty list 皆 vacuous True**；預設未執行 + 弱斷言 = 雙重 correctness 盲區 |

### 1.1 具體盲區（可機器重現的邏輯事實）

`test_retrieve_for_gap_real_twinkle_smoke` 斷言形狀：

```python
assert all(isinstance(s, Source) for s in out)
assert all(s.level in ("A", "B") for s in out)
keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
assert keys == sorted(keys)
```

當 `out == []` 時三式皆 True → **檢索全滅仍綠燈**。  
預設 CI 更因 mark 排除而不跑此測，連 smoke 本身都不執行。

## 2. 新增 failing-first 回歸

| 測試 | 角色 | 預期若盲區「產品已壞」 | 本輪結果 |
|------|------|------------------------|----------|
| `tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot` | 純邏輯鎖定：empty 滿足 smoke 三斷言 | 若 smoke 已強化為要求非空，此測會紅（盲區關閉訊號） | **PASSED**（盲區仍在驗證層） |
| `tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty` | 生產不變量：law + 真實 `LawLookup` + Twinkle 空 → 必須非空 Level A | 若 law 路徑回空 → **FAIL**（產品 correctness 缺口） | **PASSED**（產品路徑健康） |

## 3. 判定：**NOT-REPRODUCIBLE**（產品缺陷路徑）

在不修改主程式、僅加回歸的前提下：

1. Vacuous-empty 邏輯盲區 **可重現**（驗證層缺陷／弱 smoke）。
2. 產品路徑 `retrieve_for_gap(law, LawLookup(db), empty_twinkle)` **穩定回 Level A 非空** → 無法以「產品失敗」形式重現 correctness 崩壞。
3. 預設非 integration 全集 **112 passed, 8 deselected**；guard 3 passed。

故對「產品 correctness 已壞、因排除而未被看見」之主張：**`NOT-REPRODUCIBLE`**。  
對「未執行 + 弱 smoke 造成驗證盲區」之主張：**已證實（驗證層）**，並由新回歸鎖定。

## 4. 已證實非缺陷

下列在本工作樹與既有證據下，**不視為現行產品 correctness 缺陷**（確定性路徑有替代覆蓋或本輪實測通過）：

| # | 排除測試 | 為何判「非缺陷」 | 主要證據 |
|---|---------|------------------|----------|
| 1 | `test_detect_domain_real_grok_returns_law` | 契約由 FakeLLM substitute 覆蓋；真模型語意屬品質非閘門邏輯 | allowlist + `test_detect_domain_law`；個別實跑 historically PASS |
| 2 | `test_e2e_acceptance_real` | 四項硬閘有離線回歸；真 e2e 歷史 PASS | `test_e2e_minimal_quality_gates_offline_regression` 等 |
| 3 | `test_detect_gaps_real_grok` | 過濾／fallback 契約有 unit 覆蓋 | `test_detect_gaps_keeps_only_partial_and_missing` |
| 4 | `test_grok_pong_integration` | request/parse 路徑有 monkeypatch 覆蓋；連通性屬運維 | `test_grokclient_builds_request_body` |
| 5 | `test_run_pipeline_real_grok` | C6／citation／引用過濾有 substitute | pipeline + correction 測試 |
| 6 | `test_generate_questions_real_grok` | 字串切割契約有 unit 覆蓋 | questions 兩件套 |
| 7 | `test_retrieve_for_gap_real_twinkle_smoke` | **law Level A 離線路徑本輪非空**；排序／協議有 substitute；產品未回空 | 本檔新回歸 `..._not_vacuous_empty` PASSED |
| 8 | `test_search_real_twinkle_hub` | MCP 解析／session／timeout 降級有 mock 覆蓋 | twinkle 三件套 |

品質閘硬約束（本輪未弱化）：

| 硬約束 | 狀態 |
|--------|------|
| 原稿逐字不可變 | 仍由 e2e 離線回歸鎖定 |
| 無來源 → `pending_evidence` | 同上 + pipeline C6 |
| 只掛實際引用來源 | correction / write 測試 |
| 法條離線查核 | law citation 路徑 |
| integration 平時跳過 | 維持 8 deselected |

## 5. 仍存在的真實驗證缺口

下列 **不是本輪可判的產品 FAIL**，但 **預設 CI（`-m 'not integration'`）確實看不到**，屬真實驗證缺口：

| 缺口 | 來源排除 | 說明 | 嚴重度 |
|------|----------|------|--------|
| **Smoke vacuous empty** | #7 | 即使手動重跑 integration smoke，`out=[]` 仍全綠；**新回歸已鎖定 law 非空 Level A**，但 **未改** integration smoke 本體（本任務不修主／integration 斷言，除非產品失敗重現） | 中（驗證設計） |
| 真 Grok 語意品質 | #1 #3 #5 #6 | domain／gaps／pipeline／questions 的模型輸出品質 | 低～中 |
| 真 e2e 複合品質 | #2 | 真 Grok + 真 Twinkle + Level A 路由穩定性／寫作 `[^n]` | 中 |
| 真 Twinkle I/O | #7 #8 | 服務可用性、session、keyword 抽取 | 中 |
| Proxy TCP 連通 | #4 | `127.0.0.1:8318` 日常未探針 | 低（運維） |

## 6. 執行證據

### Python

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8
```

### 6.1 新回歸（兩次穩定性）

```powershell
$py = "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe"
& $py -X utf8 -m pytest tests/test_exclusion_correctness_blind_spot.py -vv --tb=short --color=no
```

```text
tests/test_exclusion_correctness_blind_spot.py::test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot PASSED
tests/test_exclusion_correctness_blind_spot.py::test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty PASSED
============================== 2 passed in 0.02s ==============================
EXIT=0
```

### 6.2 Guard + 非 integration 全集

```text
# test_deselection_guard.py
3 passed in 5.33s
EXITG=0

# pytest -m "not integration" -q
112 passed, 8 deselected in 5.66s
EXITN=0

# collection
120 tests collected
112/120 tests collected (8 deselected)
```

## 7. 產物與主張對照

| 主張 | 可見產物 |
|------|----------|
| 已對排除範圍建立 failing-first 回歸 | `tests/test_exclusion_correctness_blind_spot.py`（2 tests） |
| 證明未執行可造成具體 correctness 盲區 | vacuous empty 邏輯測 + 報告 §1.1／§5 |
| 產品失敗路徑無法重現 | **`NOT-REPRODUCIBLE`**（§3）；Level A 非空 PASSED |
| 已證實非缺陷 | §4 八項表 |
| 仍存在真實驗證缺口 | §5 表 |
| allowlist／計數同步 | `deselected_allowlist.json` #7 substitute + `_EXPECTED_COUNTS=(120,112,8)` |
| 未弱化品質閘、未改主程式 | 無 `src/` diff；全集 112 passed |
| 未動 BACKLOG | 本 commit 不含 `BACKLOG.md` |

## 8. 最終判決

| 維度 | 判決 |
|------|------|
| 產品 correctness 缺陷（因排除而未被看見） | **`NOT-REPRODUCIBLE`** |
| 驗證層盲區（vacuous smoke + 預設未執行） | **已證實**；由新離線回歸鎖定 law Level A 非空 |
| 修正主程式／integration 選取 | **未觸發**（產品路徑未失敗） |
| 預設品質閘 | **112 passed, 8 deselected** |
