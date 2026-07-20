# 前 10 名最慢測試 ×3 基準量測（2026-07-20）

## 目的

延續 [`docs/per-test-timing-audit-2026-07-20.md`](per-test-timing-audit-2026-07-20.md) 的 Top 10 清單，對每一個最慢測試**再獨立跑 3 次**，記錄：

- 平均值（mean）
- 樣本標準差（stdev, n−1）
- 變異係數 CV = stdev / mean
- 是否受 **fixture / IO / 外部資源** 影響
- 判定：**可優化真瓶頸** vs **單次波動／邊際**

本任務**只做量測與判定**，不改測試邏輯、不改品質閘、不碰 `BACKLOG.md`。

## 可重現設定

| 項目 | 值 |
|---|---|
| Python | `D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8` |
| 基準來源 | [`docs/pytest-audit/per-test-durations-2026-07-20.json`](pytest-audit/per-test-durations-2026-07-20.json) 的 `top10` |
| 每測次數 | 3 |
| 量測主指標 | junit XML `testcase@time`（setup+call+teardown） |
| 次指標 | 外層 process wall（含 collect/import） |
| 篩選 | 單測 node id；`-o addopts=`；**未**跑 `integration` 標記套件 |
| 時段 (UTC) | 2026-07-20T07:22:24 → 07:26:55 |

### 單測命令模板

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest <node_id> -o addopts= -q --tb=line --junitxml=docs/pytest-audit/top10-rerun3x-junit-2026-07-20/rankXX-runY.xml
```

### 落盤產物

| 檔案 | 說明 |
|---|---|
| [`docs/pytest-audit/top10-rerun3x-benchmark-2026-07-20.json`](pytest-audit/top10-rerun3x-benchmark-2026-07-20.json) | 機器可讀：三次樣本、mean/stdev/CV、影響因子、判定 |
| [`docs/pytest-audit/top10-rerun3x-raw-2026-07-20.txt`](pytest-audit/top10-rerun3x-raw-2026-07-20.txt) | 每次 run 的 raw 摘要列 |
| [`docs/pytest-audit/top10-rerun3x-junit-2026-07-20/`](pytest-audit/top10-rerun3x-junit-2026-07-20/) | 30 份 junit XML（10 測 × 3 次） |
| 本報告 | 人類可讀結論 |

## 判定規則（事先固定）

| 標籤 | 條件 | 意義 |
|---|---|---|
| `true_bottleneck` | mean ≥ 1.0s 且 CV ≤ 0.25 | 結構性慢點，可優化真瓶頸 |
| `true_bottleneck_with_variance` | mean ≥ 1.0s 且 CV > 0.25 | 仍是長尾，但有負載/快取波動；仍值得優化 |
| `secondary_stable` | 0.5s ≤ mean < 1.0s 且 CV ≤ 0.25 | 次級穩定慢點 |
| `marginal` | mean < 0.5s 且 CV ≤ 0.35 | 絕對時間小，非套件瓶頸優先項 |
| `noise_or_marginal` | mean < 0.5s 且 CV > 0.35 | 單次波動易主導，優化邊際低 |

## 三次基準結果總表

| 排名 | mean_s | stdev_s | CV | min | max | 基線_s | mean相對基線 | 判定 | fixture | IO | 外部 | subprocess pytest | node id |
|---:|---:|---:|---:|---:|---:|---:|---:|---|:---:|:---:|:---:|:---:|---|
| 1 | 37.923 | 3.291 | 0.087 | 34.159 | 40.256 | 36.883 | +2.8% | **真瓶頸** | 否 | 是 | 否 | **是** | `tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable` |
| 2 | 4.649 | 0.567 | 0.122 | 4.004 | 5.066 | 4.686 | −0.8% | **真瓶頸** | 是(tmp_path) | 是 | 否 | **是** | `tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_fails_when_deselected_allowlist_count_is_too_small` |
| 3 | 5.050 | 0.724 | 0.143 | 4.608 | 5.885 | 3.997 | +26.3% | **真瓶頸** | 是(tmp_path) | 是 | 否 | **是** | `tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_accepts_only_authorized_deselected_nodes_with_reasons` |
| 4 | 4.364 | 0.125 | 0.029 | 4.234 | 4.484 | 2.914 | +49.8% | **真瓶頸** | 是(tmp_path) | 是 | 否 | **是** | `tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_fails_when_deselected_allowlist_contains_non_deselected_node` |
| 5 | 2.873 | 0.292 | 0.102 | 2.703 | 3.210 | 2.578 | +11.4% | **真瓶頸** | 否 | 是 | 否 | **是** | `tests/test_deselection_guard.py::test_integration_allowlist_is_stable` |
| 6 | 1.747 | 0.598 | 0.342 | 1.227 | 2.400 | 1.186 | +47.3% | **真瓶頸+波動** | 否 | 是 | 否 | **是** | `tests/test_deselection_guard.py::test_deselected_details_lists_node_ids_and_reasons` |
| 7 | 1.824 | 0.416 | 0.228 | 1.449 | 2.271 | 0.898 | +103.2% | **真瓶頸** | 否 | 是 | 否 | **是** | `tests/test_requirements_test_coverage.py::test_default_gate_collects_every_equivalent_and_safety_regression` |
| 8 | 0.090 | 0.054 | 0.603 | 0.051 | 0.152 | 0.443 | −79.7% | **波動/邊際** | 是(module lookup) | 是(SQLite) | 否 | 否 | `tests/test_law_check.py::test_search_articles_keyword_only` |
| 9 | 0.111 | 0.014 | 0.122 | 0.097 | 0.124 | 0.261 | −57.5% | **邊際** | 是(tmp_path) | 是(docx) | 否 | 否 | `tests/test_excluded_failing_controls.py::test_control_05_pipeline_c6_pending_when_no_sources` |
| 10 | 0.202 | 0.020 | 0.099 | 0.181 | 0.221 | 0.251 | −19.6% | **邊際** | 是(tmp_path) | 是(docx) | 否 | 否 | `tests/test_export_docx.py::test_to_docx_roundtrip_preserves_original_and_marks_supplement` |

- Top10 mean 加總：**58.833 s**（基線加總 54.097 s；量測窗約 +8.8%）
- **30/30 runs 全部 passed**（returncode=0）
- **無任何測試依賴外部網路 / grok proxy / 真實 Twinkle**（rank 9 使用 stub）

## 逐測影響分析與判定

### Rank 1 — `test_substitute_mapping_is_complete_and_collectable` → **可優化真瓶頸**

| 三次 junit (s) | mean | stdev | CV |
|---|---:|---:|---:|
| 34.159 / 39.354 / 40.256 | 37.923 | 3.291 | 0.087 |

- **fixture**：無 pytest fixture 依賴
- **IO**：讀 allowlist / JSON 證據檔
- **外部資源**：無
- **主成本**：多次 `subprocess` 再 spawn `pytest --collect-only`，並對 mapped 替代測**逐一** `_run_one_test`（nested pytest 執行）
- **判定**：CV 僅 0.087，與基線 36.9s 差 +2.8% → **結構穩定長尾**，不是單次波動。全套件優化第一優先。

### Rank 2–4 — 三個 `test_ci_gate_*` → **可優化真瓶頸**

| 測 | 三次 | mean | stdev | CV |
|---|---|---:|---:|---:|
| allowlist 過少 | 4.878 / 4.004 / 5.066 | 4.649 | 0.567 | 0.122 |
| 授權 accept | 4.608 / 5.885 / 4.657 | 5.050 | 0.724 | 0.143 |
| allowlist 多餘 node | 4.373 / 4.234 / 4.484 | 4.364 | 0.125 | 0.029 |

- **fixture**：`tmp_path` 寫臨時 allowlist / 報告
- **IO**：讀寫 JSON/md；`scripts/validate_deselection_ci.py` 內部再 `pytest --collect-only`
- **外部**：無
- **主成本**：每次 gate 至少一次 nested collect（~2–5s 級）
- **判定**：三者 CV ≤ 0.15，mean 皆 > 4s。Rank 4 相對基線 +50% 仍落在「秒級 nested collect」結構帶，**不是把假陽當瓶頸**。三者可合併優化（共用 collect 結果快取、或 mock collect 輸出）。

### Rank 5 — `test_integration_allowlist_is_stable` → **可優化真瓶頸**

| 三次 | mean | stdev | CV |
|---|---:|---:|---:|
| 3.210 / 2.706 / 2.703 | 2.873 | 0.292 | 0.102 |

- 兩次 full collect（全量 vs default）
- 穩定秒級；與 rank 1 同類 **nested collect** 成本

### Rank 6 — `test_deselected_details_lists_node_ids_and_reasons` → **真瓶頸（含波動）**

| 三次 | mean | stdev | CV |
|---|---:|---:|---:|
| 1.615 / 1.227 / 2.400 | 1.747 | 0.598 | 0.342 |

- 單次 collect + `--deselected-details`
- mean 仍 ≥ 1s → 可優化；CV 0.34 顯示機器負載會讓單次落在 1.2–2.4s，**不應只看最慢那次下結論**

### Rank 7 — `test_default_gate_collects_every_equivalent_and_safety_regression` → **可優化真瓶頸**

| 三次 | mean | stdev | CV |
|---|---:|---:|---:|
| 2.271 / 1.753 / 1.449 | 1.824 | 0.416 | 0.228 |

- 讀 coverage matrix JSON + default collect
- 獨立量測 mean（1.82s）高於套件基線（0.90s）：隔離執行時 nested collect 更易受系統負載影響，但三次皆 ≥ 1.4s → **仍是真瓶頸**，非「只慢一次」

### Rank 8 — `test_search_articles_keyword_only` → **波動／邊際（非優化優先）**

| 三次 | mean | stdev | CV |
|---|---:|---:|---:|
| 0.152 / 0.051 / 0.067 | 0.090 | 0.054 | 0.603 |

- **fixture**：module-scoped `lookup`（開 `data/law_index.db`）
- **IO**：本地 SQLite
- **外部**：無
- 基線 0.443s 在**全套件**中含 module fixture 攤提差異；獨立三次 junit 僅 0.05–0.15s
- **判定**：CV 高、絕對時間小 → **單次/套件上下文波動**，不是可回收的套件級瓶頸

### Rank 9 — `test_control_05_pipeline_c6_pending_when_no_sources` → **邊際**

| 三次 junit | mean | stdev | CV |
|---|---:|---:|---:|
| 0.097 / 0.112 / 0.124 | 0.111 | 0.014 | 0.122 |

- **fixture**：`tmp_path`；stub LLM/Twinkle
- **IO**：建 docx / pipeline 離線
- **外部**：無真實 API
- **注意**：第 1 次 process wall = **47.2s**（pytest 摘要 45.06s），但 junit testcase 僅 0.097s → 時間在 **session/import 冷啟動**（可能受前序大量 nested pytest 進程影響），**不是 test body 瓶頸**
- **判定**：body 穩定 ~0.11s → 邊際；勿把冷啟動 process wall 誤判為可優化測試本體

### Rank 10 — `test_to_docx_roundtrip_preserves_original_and_marks_supplement` → **邊際**

| 三次 | mean | stdev | CV |
|---|---:|---:|---:|
| 0.203 / 0.181 / 0.221 | 0.202 | 0.020 | 0.099 |

- `tmp_path` + python-docx I/O
- 穩定但 < 0.25s → 優化 ROI 極低

## 總結：真瓶頸 vs 波動

### 可優化真瓶頸（7）

皆屬 **nested pytest collect / gate subprocess** 同一成本族：

1. `test_substitute_mapping_is_complete_and_collectable`（~38s，獨占長尾）
2. 三個 `test_ci_gate_*`（各 ~4.4–5.1s）
3. `test_integration_allowlist_is_stable`（~2.9s）
4. `test_deselected_details_lists_node_ids_and_reasons`（~1.7s，波動較大但 mean 仍 ≥ 1s）
5. `test_default_gate_collects_every_equivalent_and_safety_regression`（~1.8s）

這 7 個 mean 加總 ≈ **58.4 s**，占 Top10 mean 加總的 **99.3%**。

### 非瓶頸／波動（3）

| 測 | 理由 |
|---|---|
| `test_search_articles_keyword_only` | mean 0.09s、CV 0.60；SQLite fixture 在全套件與單測計時差大 |
| `test_control_05_...` | junit ~0.11s 穩定；第 1 次 process 47s 是 import 冷啟動噪音 |
| `test_to_docx_roundtrip_...` | ~0.20s 穩定 docx I/O，邊際 |

### 外部資源

**本 Top10 無「外部服務真依賴」**。慢點來自：

1. **subprocess 再啟動 pytest collect**（主導）
2. 本地 **檔案/SQLite/docx I/O**（次要、僅 rank 8–10）
3. **fixture**（tmp_path / module DB）— 非秒級主因

## 優化方向（僅建議，本任務未實作）

1. **最高 ROI**：`test_substitute_mapping_is_complete_and_collectable` — 減少重複 collect；對替代測用 in-process API 或快取 collect 結果，避免 N 次 nested pytest。
2. **次高**：CI gate 三測共用一次 collect 快照（fixture session 級或 parametrize 前先算）。
3. **不要**優先優化 rank 8–10（合計 mean < 0.5s，且含波動）。

## 驗收對照（任務要求 ↔ 產物）

| 要求 | 證據 |
|---|---|
| 前 10 名各再跑 3 次 | 30 份 junit + JSON `runs[]` |
| 平均值、標準差 | JSON `mean_s` / `stdev_s`；本表 |
| fixture/IO/外部影響 | JSON `influence` + 本節逐測 |
| 真瓶頸 vs 單次波動 | JSON `classification` + 總結 |
| 報告落盤並 commit | 本檔 + pytest-audit 產物 |
| 不弱化品質閘 / 不跑 integration 常規套件 | 單測 node id；30/30 pass；無 integration suite |
| 不改 BACKLOG | 未修改 |

## 限制

- 樣本 n=3：標準差對極端值敏感（rank 6/8 尤然），但足以區分「秒級結構慢」與「亞秒波動」。
- 獨立執行會讓 **process wall** 含 import；分析以 **junit testcase time** 為準。
- 與全套件基線的百分比差（尤其 rank 4/7）反映負載與是否共用 parent process，**不推翻** nested-collect 結構結論。
