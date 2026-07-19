# 8 個排除測試：功能、關鍵路徑、安全風險與需求覆蓋對照

## 1. 判定規則

本報告的機器可讀來源是
[`docs/pytest-audit/requirements-test-coverage-2026-07-19.json`](pytest-audit/requirements-test-coverage-2026-07-19.json)，
由 [`tests/test_requirements_test_coverage.py`](../tests/test_requirements_test_coverage.py)
守衛。

「等價覆蓋」只計入不需外部服務、可重現，而且驗證相同產品契約或安全閘的
預設測試。真 Grok／真 Twinkle 的模型語意、TCP 連通性與服務可用性是外部風險，
不冒充程式路徑已覆蓋。

預設品質閘仍為 `-m 'not integration'`；新守衛沒有 integration marker，因此會
進入預設測試集。

## 2. 8 個測試分類

| ID | 被排除測試 | 功能 | 關鍵路徑 | 安全風險 | 預設等價覆蓋 | 殘餘風險 |
|---|---|---|---|---|---|---|
| T1 | `test_domain.py::test_detect_domain_real_grok_returns_law` | 領域路由 | P1：輸入→領域→問題→缺口 | 中：錯誤路由可能繞過法規檢索 | `test_detect_domain_law`；`control_01_domain_legal_label_contract` | 真 Grok 邊界語意分類 |
| T2 | `test_e2e_acceptance.py::test_e2e_acceptance_real` | 端到端品質閘 | P5：完整 pipeline | 高：原稿、證據、引用及法條閘可能同時失守 | structural、offline quality、minimal gates、pipeline／correction、`control_02` | 真模型＋真檢索複合品質 |
| T3 | `test_gap.py::test_detect_gaps_real_grok` | 缺口偵測 | P1 | 高：漏掉缺口會靜默漏補 | `test_detect_gaps_keeps_only_partial_and_missing`；`control_03_gap_uncovered_question_must_surface` | 真 Grok 缺口語意 |
| T4 | `test_llm.py::test_grok_pong_integration` | LLM 傳輸介面 | P3：LLM HTTP 信任邊界 | 高：Authorization、endpoint、model、回應解析 | `test_grokclient_builds_request_body`；`control_04_grok_client_parse_and_endpoint_contract` | proxy TCP／部署狀態 |
| T5 | `test_pipeline.py::test_run_pipeline_real_grok` | pipeline 編排 | P2：缺口→檢索→寫作→驗證→組裝 | 高：可能跳過 C6、引用過濾或法條查核 | pipeline invariant、malformed fallback、law citation、used-source、`control_05` | 真 Grok pipeline 穩定性 |
| T6 | `test_questions.py::test_generate_questions_real_grok` | 問題生成 | P1 | 中：畸形輸出會污染後續檢索範圍 | multiline、strip／blank、`control_06_questions_clean_list_contract` | 真 Grok 出題品質 |
| T7 | `test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | 法規／議案檢索 | P2 | 高：法規補充可能沒有 Level A 或檢索全滅假綠 | Level A 排序、law search、Twinkle parser／session／降級、law 非空 Level A、`control_07b` | 真 Twinkle／Grok keyword；另有 vacuous smoke 設計缺口 |
| T8 | `test_twinkle.py::test_search_real_twinkle_hub` | Twinkle MCP 來源解析 | P4：MCP→Source | 高：來源全文與 metadata 不可追溯或失敗時偽造來源 | full content、session、transport、`control_08` | 真 Hub 可用性與 session 相容性 |

P1～P5 的完整說明與每一筆 node ID、風險理由、替代測試在 JSON 索引內保存；
本表使用短名是為了可讀性。

## 3. 需求→測試覆蓋對照

| 需求 ID | 需求／安全閘 | 風險 | 預設測試證據 | 判定 |
|---|---|---|---|---|
| REQ-DOMAIN-CANONICAL | 只接受 canonical domain label；非法輸出 fallback `other` | 中 | `test_detect_domain_law`、`control_01...` | 已覆蓋 |
| REQ-ORIGINAL-IMMUTABLE | 原稿逐字保留，不改寫、不刪除 | 高 | `test_original_segments_verbatim_and_immutable`、e2e structural、`control_02...` | 已覆蓋 |
| REQ-NO-SOURCE-PENDING | 無來源／待補證不得標成 `verified` | 高 | pipeline invariant、malformed fallback、pending write、`control_05...` | 已覆蓋 |
| REQ-USED-SOURCES-ONLY | 正文只掛 writer 實際引用的來源 | 高 | write marker、`test_retrieved_five_but_only_two_cited`、minimal gates | 已覆蓋 |
| REQ-LAW-CITATION-OFFLINE | law 補充通過離線法條查核；找不到時保守降級 | 高 | pipeline law citation、e2e structural／minimal、real article check | 已覆蓋 |
| REQ-GAP-FILTER | 只保留 `partial`／`missing`，明顯未涵蓋題必須出現 | 高 | gap filter、`control_03...` | 已覆蓋 |
| REQ-GROK-BOUNDARY | 固定 POST、endpoint、model、Bearer、body、timeout、content parse | 高 | Grok request body、`control_04...` | 已覆蓋 |
| REQ-PIPELINE-ORCHESTRATION | 依序 retrieve／write／只驗 used／law citation | 高 | 3 個 pipeline test、used-source test | 已覆蓋 |
| REQ-QUESTION-CLEAN | 問題清單非空、逐行、strip、去空行、不殘留 JSON 結構符號 | 中 | 2 個 questions unit、`control_06...` | 已覆蓋 |
| REQ-LEVEL-A-PRIORITY | Level A 先於 B，同級依 distance 排序 | 高 | retrieve ordering、law search | 已覆蓋 |
| REQ-LEVEL-A-NONEMPTY | law＋離線 LawLookup 不得以空結果假綠，至少含 Level A | 高 | `test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`、`control_07b...` | 已補測並進預設集 |
| REQ-TWINKLE-SOURCE | MCP response 映射 Source，保留全文／metadata／session | 高 | full content、session、`control_08...` | 已覆蓋 |
| REQ-TWINKLE-SAFE-DEGRADE | 缺 token／transport failure 回空，不偽造來源 | 高 | no-token、transport failure | 已覆蓋 |

機器守衛會實際重新 collection 預設集合，逐筆確認上述 `covered_by` 與每個
`equivalent_default_tests` 都被收集，且沒有任何一筆落入 8 個 integration
node。需求缺口清單為空：**13／13 需求由預設測試覆蓋**。

## 4. 缺口與補測判定

### T7 的 vacuous smoke

原本 T7 的三個 `all()`／排序斷言在 `out == []` 時仍會通過；因此下列兩個測試
只能證明「驗證設計盲區存在」，不能列作等價覆蓋：

- `test_deselected_retrieve_smoke_vacuous_pass_on_empty_is_blind_spot`
- `test_control_07_retrieve_smoke_vacuous_empty_is_blind_spot`

真正補上的安全契約是同一條 law 離線路徑必須產生非空 Level A，且兩個測試都在
預設集合中：

- `test_law_domain_retrieve_must_yield_level_a_not_vacuous_empty`
- `test_control_07b_retrieve_law_level_a_not_vacuous`

所以產品 correctness 的等價覆蓋成立；vacuous smoke 本身仍被明確列為驗證設計
缺口，沒有把它誤報成產品通過。

### 其他 7 項

T1～T6、T8 的未覆蓋部分都需要真外部依賴（模型語意、proxy TCP 或 Twinkle
服務）；其 deterministic contract、安全降級與品質閘均已有預設替代測試，沒有
發現需要新增產品測試的需求缺口。

## 5. 實測證據

使用指定主專案 venv，所有命令工作目錄均為本 repo：

```text
pytest tests/test_requirements_test_coverage.py -vv --tb=short --color=no
2 passed in 1.86s

pytest tests/test_exclusion_correctness_blind_spot.py tests/test_excluded_failing_controls.py -q --tb=short --color=no
12 passed in 0.31s

pytest -m 'not integration' -q --tb=short --color=no
137 passed, 8 deselected in 40.65s

pytest tests/test_deselection_guard.py -q --tb=short --color=no
4 passed in 39.07s

pytest --collect-only -q --deselected-details --color=no
137/145 tests collected (8 deselected)
```

## 6. 本輪驗收產物

- [`docs/pytest-audit/requirements-test-coverage-2026-07-19.json`](pytest-audit/requirements-test-coverage-2026-07-19.json)：分類與需求→測試機器索引。
- [`tests/test_requirements_test_coverage.py`](../tests/test_requirements_test_coverage.py)：8 項分類、13 項需求、預設 collection 與非空 Level A 補測守衛。
- [`tests/deselection_allowlist.json`](../tests/deselection_allowlist.json)：8 個 integration node 的既有排除與替代測試來源。

本輪加入的守衛本身不需要外部服務，會進入預設集合；實測 collection 為
`145`、預設選取 `137`、deselected `8`。品質閘仍維持：原稿不可變、無來源→
`pending_evidence`、只掛實際引用來源、法條離線查核、integration 平時跳過。
