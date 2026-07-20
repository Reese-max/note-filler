# 最慢 3 個測試降耗驗證（2026-07-21）

## 範圍

依 `docs/top10-slow-tests-3x-benchmark-2026-07-20.md` 的既有排名，檢查並局部重跑：

1. `tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable`
2. `tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_fails_when_deselected_allowlist_count_is_too_small`
3. `tests/test_deselected_ci_gate_acceptance.py::test_ci_gate_accepts_only_authorized_deselected_nodes_with_reasons`

未執行 integration 測試，未改 marker、allowlist、來源引用或既有品質斷言。

## setup / teardown、fixture 與資料流程

以 `pytest --fixtures-per-test` 檢查：

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest <上述三個 node ID> -o addopts= -p no:asyncio --strict-markers --fixtures-per-test -q
```

| 測試 | fixture | setup / teardown | 實際成本流程 |
|---|---|---|---|
| substitute mapping | 無 | after run 1 中各自皆 `<0.005s` | module import 讀 allowlist JSON，逐一核對來源證據並建立 28 個唯一替代 node ID；原流程另開 4 次 collect 行程，再為 28 個 node ID 各開一次 pytest 行程，最後建立逐 node 驗收 dict |
| allowlist 過少 | `tmp_path` → `tmp_path_factory` | setup `0.11s`，teardown `<0.005s` | 讀 allowlist、寫一份小型暫存 JSON；gate 原流程開 3 次 pytest collect，再建立 Markdown 報告 |
| allowlist 正常 | `tmp_path` → `tmp_path_factory` | setup `0.01s`，teardown `<0.005s` | 讀 allowlist；gate 原流程開 3 次 pytest collect，再讀小型暫存報告 |

`--durations=0` 顯示秒級時間都在 test call；fixture 與暫存資料建構不是瓶頸。共同根因是 nested pytest 的重複啟動與 collection。

## 最小改動

- `test_deselection_guard.py`：保留 28 個替代測試各自的 pytest 行程、單 node invocation 與逐 node 驗收，只用標準函式庫 `ThreadPoolExecutor(max_workers=4)` 同時處理最多 4 個獨立行程。測試隔離、個別狀態與失敗定位維持不變。
- `test_deselection_guard.py` 與 `validate_deselection_ci.py`：同一次 `--collect-only --deselected-details` 同時產生 selected node IDs 與 deselected 原因，刪除一次內容相同的 default collection。

未新增 fixture、快取、相依套件或設定層。

## 前後局部重跑

Python：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`

每個版本各跑 3 次，命令模板：

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest <上述三個 node ID> -o addopts= -p no:asyncio --strict-markers -q --tb=line --durations=3 --junitxml=docs/pytest-audit/slow-top3-<before|after>-run<N>.xml
```

為顯示各 phase，after run 1 使用等價的 `--durations=0`；JUnit 計時方式不變。

JUnit `testcase@time` 結果：

| 測試 | before 3 次（s） | before mean | after 3 次（s） | after mean | 節省 | 降幅 |
|---|---:|---:|---:|---:|---:|---:|
| substitute mapping | 29.959 / 29.937 / 26.310 | 28.735 | 11.237 / 14.088 / 11.327 | 12.217 | 16.518s | 57.5% |
| allowlist 過少 | 2.710 / 3.674 / 3.116 | 3.167 | 2.453 / 2.332 / 1.964 | 2.250 | 0.917s | 29.0% |
| allowlist 正常 | 2.576 / 3.135 / 2.926 | 2.879 | 1.912 / 2.025 / 2.307 | 2.081 | 0.798s | 27.7% |
| 三測 suite | 35.493 / 36.792 / 32.395 | 34.893 | 15.686 / 18.516 / 15.657 | 16.620 | 18.273s | 52.4% |

六份原始 JUnit：

- `docs/pytest-audit/slow-top3-before-run1.xml` ～ `slow-top3-before-run3.xml`
- `docs/pytest-audit/slow-top3-after-run1.xml` ～ `slow-top3-after-run3.xml`

## 回歸驗證

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_deselection_guard.py tests/test_deselected_ci_gate_acceptance.py -q --tb=line --durations=10
```

結果：`7 passed in 21.83s`。其中 substitute mapping 保留 28 個替代 node 的獨立行程與 invocation；三個 CI gate 正常與兩種失敗情境皆通過。

預設非 integration 回歸：

```text
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=line --durations=10
```

結果：`140 passed, 8 deselected in 25.87s`。

## 結論

setup / teardown 與 fixture 不需調整。平行處理彼此隔離的 pytest 行程並刪除重複 collection，讓前 3 測試的局部 suite 平均由 `34.893s` 降至 `16.620s`（`-52.4%`），且逐 node、排除原因與 allowlist 品質閘維持不變。
