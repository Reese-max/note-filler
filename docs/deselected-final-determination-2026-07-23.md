# Deselected 測試最終判定表

> 判定日期：2026-07-23
>
> 權威清單：`tests/deselected_allowlist.json`
>
> 本次實跑：163 collected、152 selected、11 deselected；35 個唯一替代測試逐一通過；完整預設套件 152 passed

## 判定標準

- **受控排除且有替代覆蓋**：node 在 allowlist，排除原因固定為 `deselected by -m 'not integration'`，確定性產品邏輯有可收集且本次逐一通過的非 integration 替代測試；真服務／真模型殘餘風險已有現存 integration node 與手動 job 可重跑，因此不需再新增測試。
- **受控排除但仍需補測**：排除雖經核准，但缺少替代測試、關鍵斷言或可執行的殘餘風險驗證路徑。

「有替代覆蓋」不等於預設 CI 已驗證真實外部服務。下表的殘餘風險仍須以 `C4` 手動 integration job 驗證。

## 最終判定

| # | Deselected node ID | 最終判定 | 已驗證的替代覆蓋 | 預設 CI 未覆蓋的殘餘風險 | 重跑 | 證據 |
|---:|---|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | **受控排除且有替代覆蓋** | law 標籤解析與契約控制 | 真 Grok 對法律文字的分類品質 | C1、C2、C3、C4 | E1、E2、E3、E4 |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | **受控排除且有替代覆蓋** | 結構不變式、補充品質邊界、C6、引用來源與法條查核路徑 | 真 Grok＋Twinkle＋law DB 的端到端品質 | C1、C2、C3、C4 | E1、E2、E3、E4 |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | **受控排除且有替代覆蓋** | partial／missing 過濾與未覆蓋問題浮現 | 真 Grok 的法律文本缺口判斷品質 | C1、C2、C3、C4 | E1、E2、E3、E4 |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | **受控排除且有替代覆蓋** | request body、endpoint 與回應解析契約 | `127.0.0.1:8318` TCP 連通及真 proxy 回應 | C1、C2、C3、C4 | E1、E2、E3、E4 |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | **受控排除且有替代覆蓋** | pipeline 不變式、malformed fallback、法條離線查核、無來源轉 `pending_evidence` | 真模型輸出下的 domain／questions／gaps 與 pipeline 穩定性 | C1、C2、C3、C4 | E1、E2、E3、E4 |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | **受控排除且有替代覆蓋** | 多行清理、空白移除、Markdown fence 與乾淨清單契約 | 真 Grok 的法律問題生成品質 | C1、C2、C3、C4 | E1、E2、E3、E4 |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | **受控排除且有替代覆蓋** | Level A／B 排序、法條來源、Twinkle 解析與錯誤降級；原 smoke 已要求非空且含 A、B | 真 Twinkle I/O 與真 Grok 關鍵字抽取 | C1、C2、C3、C4 | E1、E2、E3、E5 |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | **受控排除且有替代覆蓋** | Source 解析、session 重用、transport／MCP 錯誤降級；原 smoke 已要求非空 | 真 Hub 可用性、服務端 session 相容性與網路逾時 | C1、C2、C3、C4 | E1、E2、E3、E5 |
| 9 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | **受控排除且有替代覆蓋** | law／admin／exam／other 四類標籤解析 | 真模型四類代表文本的語意分類品質 | C1、C2、C3、C4 | E1、E2、E3、E4 |
| 10 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | **受控排除且有替代覆蓋** | covered 過濾與 partial／missing 結構 | 真模型對 covered／missing 的相反語意判斷 | C1、C2、C3、C4 | E1、E2、E3、E4 |
| 11 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | **受控排除且有替代覆蓋** | 實際引用來源 ID 映射與來源不足轉 `pending_evidence` | 真模型能否只依固定來源產生有效註腳補充 | C1、C2、C3、C4 | E1、E2、E3、E4 |

## 數量結論

| 分類 | 數量 |
|---|---:|
| 受控排除且有替代覆蓋 | 11 |
| 受控排除但仍需補測 | 0 |

先前 T7-P3／T8-P3 的空結果 vacuous-pass 缺口已落地補強；本判定不沿用補強前的「仍需補測」結論。`docs/deselected-error-branch-analysis-2026-07-23.md` 與 `docs/deselected-minimal-regression-test-draft-2026-07-23.md` 所稱「完整覆蓋」僅適用於離線確定性與錯誤分支，不代表真服務風險已由預設 CI 覆蓋。

## 可重跑命令

### C1：完整收集、selection 與逐項排除原因

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -q --deselected-details --color=no
```

### C2：allowlist 數量、完整集合與原因閘

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 scripts/validate_deselection_ci.py --report docs/pytest-audit/deselected-final-ci-gate-2026-07-23.md
```

### C3：逐一執行所有映射的非 integration 替代測試

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_deselection_guard.py::test_substitute_mapping_is_complete_and_collectable -vv --tb=short --color=no -s
```

### C4：手動重跑 11 個原始 integration node

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/ -m "integration" -v
```

C4 需依 node 備妥 grok proxy、`TWINKLE_HUB_TOKEN` 與 `data/law_index.db`；缺少前置條件時測試會 skip，不能把 skip 當成真服務通過。

### C5：完整預設品質閘

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest -q --color=no
```

### C6：最終表與 allowlist 一致性

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -c "import json,pathlib,re; a=json.loads(pathlib.Path('tests/deselected_allowlist.json').read_text(encoding='utf-8')); rows=[line for line in pathlib.Path('docs/deselected-final-determination-2026-07-23.md').read_text(encoding='utf-8').splitlines() if re.match(r'^\| \d+ \|',line)]; ids=[row.split('|')[2].strip().strip(chr(96)) for row in rows]; assert len(rows)==len(a)==11; assert set(ids)=={x['test_id'] for x in a}; assert all('受控排除且有替代覆蓋' in row for row in rows); print('FINAL_TABLE_CHECK=PASS rows=11 covered=11 needs_tests=0')"
```

## 對應證據檔案

- **E1** `docs/pytest-audit/deselected-final-collect-2026-07-23.txt`：本次完整 collection 輸出、11 個 node ID、逐項原因與 `152/163 tests collected (11 deselected)` 完成訊號。
- **E2** `docs/pytest-audit/deselected-final-ci-gate-2026-07-23.txt`、`docs/pytest-audit/deselected-final-ci-gate-2026-07-23.md`：allowlist 數量、集合、原因與 `PASS`。
- **E3** `docs/pytest-audit/deselected-final-substitute-runs-2026-07-23.txt`：11 項映射、35 個唯一替代 node 的逐一 `PASSED`、命令與 `TARGETED_VERIFICATION=PASS`。
- **E4** `tests/deselected_allowlist.json`：每項的替代測試、來源錨點、殘餘 coverage gap 與 integration 緩解路徑；`.github/workflows/ci.yml` 的 `test-integration` 為 `workflow_dispatch`。
- **E5** `docs/deselected-minimal-supplements-2026-07-22.md`、`tests/test_retrieve.py`、`tests/test_twinkle.py`：T7-P3／T8-P3 補強紀錄，以及目前 `assert out`、Level B、`assert results` 非空斷言。
- **E6** `docs/pytest-audit/deselected-final-default-suite-2026-07-23.txt`：本次完整預設品質閘 `152 passed, 11 deselected`。
- **E7** `docs/pytest-audit/deselected-final-table-check-2026-07-23.txt`：最終表 11 列與 allowlist 集合一致，且分類數為 11／0。

## 最終限制

本輪依任務規則維持 integration 平時跳過，未用 C4 重新真打外部服務；因此可判定「無新增補測缺口」，不可判定 2026-07-23 當下的 Grok／Twinkle 外部服務皆可用。
