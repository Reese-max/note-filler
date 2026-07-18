# 最終驗證報告：8 項 integration 判定與整體結論（更新）

> 日期：2026-07-18
> Python：`D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe -X utf8`
> 日常策略：`pyproject.toml` 以 `-m 'not integration'` 排除需要 Grok／Twinkle 的測試；本報告不變更該策略。

## 1. 證據與計數校正

原先的 108 項通過快照仍有效，但不是目前的測試總數：提交 `32a3d65` 只新增
`test_deselected_details_lists_node_ids_and_reasons` 這一項稽核測試，並將計數從
`116 / 108 / 8` 更新為 `117 / 109 / 8`；沒有改動任何 production 路徑、8 項
integration node ID 或 16 個替代測試映射。

| 證據 | 結果 | 對本判定的意義 |
|---|---:|---|
| 歷史非 integration 基準 | 108 passed、8 deselected | 108 項已覆蓋全部 16 個替代測試的確定性契約。 |
| 本次全量 collection | 117 collected | 8 項 integration node ID 仍在完整集合內。 |
| 本次日常回歸 | 109 passed、8 deselected | 108 項基準加上新增的排除詳情 guard；沒有失敗或意外排除。 |
| 本次 mapping guard | 3 passed；`DESELECTED_AUDIT=8 MAPPED_TESTS=16` | allowlist、程式碼 anchor、16 個替代測試及其實際執行結果一致。 |
| 已提交的 live 補跑證據（`30db593`） | 8/8 PASSED、0 skipped、0 failed | 同一測試碼已分批完成真 Grok／Twinkle 補跑；本提交不變更測試碼，故不重複耗時 live 呼叫。 |

「108」與「109」不是相互矛盾：前者是題目所指的基準回歸，後者是現行集合，僅多出一項驗證 deselection 詳情的 guard。下列重疊判定以該 108 項基準為主，並由本次 109 項回歸再次確認。

## 2. 判定規則

只有下列任一情形才判為「必須補測」：

1. integration 測試的確定性程式契約沒有落在 108 項已通過集合，或其替代測試失敗；
2. 該測試失敗可繞過原稿不可變、無來源／`【待補證】` → `pending_evidence`、只掛實際引用來源、法條離線查核等品質閘。

真模型語意、proxy 連通與 Twinkle 服務可用性不會因單元測試而變成確定性行為；它們保留為 integration 邊界。因此，在替代契約已通過且失敗會安全降級時，日常未執行可接受，但發版、Grok proxy／模型更換、Twinkle 協定或 token 設定變更時必須補跑 integration。

## 3. 逐項覆蓋、失敗影響與判定

| # | integration 測試與獨有範圍 | 與已通過 108 項的重疊 | 失敗影響 | 本次判定 |
|---:|---|---|---|---|
| 1 | `test_detect_domain_real_grok_returns_law`：真 Grok 對法律文字的領域判定。 | `test_detect_domain_law` 鎖定同一 `detect_domain` 入口與 `law` 回傳契約。 | 領域誤判會使後續檢索路由偏移，但不會直接略過來源或法條品質閘。 | **可接受未執行**；模型／proxy 變更或發版時補跑。 |
| 2 | `test_e2e_acceptance_real`：真 Grok + 真 Twinkle + LawLookup 的全流程與補充品質。 | 6 項替代測試覆蓋原稿逐字不可變、無來源 → `pending_evidence`、只掛實際引用、法條離線查核、Level A 路由與 Markdown 契約。 | 高：若外部服務或模型語意異常，使用者可見的補充品質會下降；四項硬品質閘仍由日常集合保護。 | **可接受未執行**；已由 `30db593` live 補跑通過，發版／外部依賴變更時必跑。 |
| 3 | `test_detect_gaps_real_grok`：真模型判斷 partial／missing。 | `test_detect_gaps_keeps_only_partial_and_missing` 與同檔解析、fence、fallback 邊界測試覆蓋 JSON 與過濾契約。 | 缺口語意誤判會影響補充範圍，不會改寫原稿或放寬來源閘。 | **可接受未執行**；模型提示或模型版本變更時補跑。 |
| 4 | `test_grok_pong_integration`：真 HTTP proxy 的 PONG 與回應相容性。 | `test_grokclient_builds_request_body` 覆蓋 URL、POST、Bearer、payload、timeout 與 response parse。 | proxy 不可用會使 LLM 路徑不可用，屬可用性問題；不是確定性請求構造回歸。 | **可接受未執行**；proxy／模型設定變更時補跑。 |
| 5 | `test_run_pipeline_real_grok`：真模型輸出下的 parse → domain → questions → gaps → assemble。 | `test_run_pipeline_invariant`、畸形 gap fallback、law citation check 與 cited-source 測試覆蓋 C6、法條查核及引用選取。 | 高：模型輸出變形可能降低流程品質；無來源仍會降為 `pending_evidence`，法條仍走離線查核。 | **可接受未執行**；發版／Grok 變更時補跑。 |
| 6 | `test_generate_questions_real_grok`：真模型產生可用問題清單。 | 兩項替代測試覆蓋多行切割、strip、空行移除，另有空回應與呼叫次數邊界。 | 問題相關性下降會降低後續檢索品質，但不會破壞來源或原稿不變式。 | **可接受未執行**；模型／prompt 變更時補跑。 |
| 7 | `test_retrieve_for_gap_real_twinkle_smoke`：真 Grok keyword、LawLookup 與 Twinkle 的 A/B 排序。 | A 優先排序、離線 law index、MCP/SSE 解析、session 傳遞與 transport failure 安全降級均已在 5 項替代測試通過。 | 高：外部檢索失敗會減少可用來源；空結果會走無來源／`pending_evidence`，不會把無證內容升為 verified。 | **可接受未執行**；Twinkle／law DB／Grok 變更時補跑。live smoke 的 `all(...)` 對空清單為真，不能把其 PASS 解讀成「一定取得結果」。 |
| 8 | `test_search_real_twinkle_hub`：真 Twinkle Hub MCP 搜尋與 `Source` 映射。 | mock 測試覆蓋全文解析、三段 RPC session header 與 timeout 回空結果。 | 外部服務中斷只影響檢索可用性；呼叫端會維持安全的無來源路徑。 | **可接受未執行**；Twinkle 協定／token／發版時補跑。測試對空 `results` 不失敗，故 PASS 不是非空服務健康證明。 |

## 4. 整體驗證結論

1. **本次沒有必須新增或日常強制執行的補測：0/8。** 8 項的確定性範圍都與 108 項通過集合重疊，且 16 個映射替代測試已由 guard 實跑確認。
2. **四項品質閘沒有被弱化。** #2、#5 的離線替代測試與目前 109 項日常回歸仍強制驗證原稿不可變、無來源降級為 `pending_evidence`、僅保留實際引用來源，以及法條離線查核。
3. **外部依賴已另有 live 證據，但不是日常健康承諾。** `30db593` 的 8/8 PASSED 證明當時同一測試碼可與 Grok／Twinkle 協作；模型語意與服務可用性仍必須在上述變更觸發時重跑。
4. **#7、#8 的限制已保留。** 它們目前允許空清單通過，所以不能用此次 PASS 宣稱 Twinkle 一定回傳非空資料；若未來需求是服務健康保證，才應另行定義穩定查詢與非空結果契約，不應把不穩定外部服務塞進日常 CI。

結論：**預設驗證通過**（現行 109 passed、8 個有邊界的 integration deselected）；**整體品質閘通過**；外部 integration 維持條件式補跑，而非降低或移除測試。

## 5. 本次可重現指令與實測摘要

```powershell
& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest --collect-only -q -o addopts=
# 117 tests collected

& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest -q --deselected-details
# 109 passed, 8 deselected

& 'D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_deselection_guard.py -q -s
# 3 passed; DESELECTED_AUDIT=8 MAPPED_TESTS=16; TARGETED_VERIFICATION=PASS
```

完整 8/8 live 補跑輸出見 [`integration-test-rerun-results-2026-07-18.md`](integration-test-rerun-results-2026-07-18.md) 與同目錄的 `pytest-audit/integration-batch*.txt`。
