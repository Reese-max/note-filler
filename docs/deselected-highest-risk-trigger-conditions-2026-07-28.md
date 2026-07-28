# 最高風險 deselected 情境最小觸發條件

> 檢視日期：2026-07-28
> 目標：`tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

## 結論

原始 8 項基準中，最高風險且目前 HEAD 尚無直接真跑證據的是
`test_e2e_acceptance_real`。它同時經過 parse、domain、questions、gaps、
retrieve、write、verify、assemble 與 export，並檢查原稿不可變、無來源降級、
實際引用、法條離線查核及輸出格式；其失守影響大於單一 Grok 或 Twinkle smoke。

目前預設收集實際為 `701/712 tests collected (11 deselected)`。任務所稱 8 項是
`docs/pytest-audit/requirements-test-coverage-2026-07-19.json` 固定的原始集合；
2026-07-22 後另增 3 項 integration 測試，本次沒有把它們混入候選比較。

`acceptable_unexecuted` 目前只是 allowlist 決策，不能當成目前 HEAD 的執行證據：

- 最近一次保存的真跑是提交 `12d1945` 所記錄的 2026-07-24 結果，該項為
  `PASSED`（169.094 秒）。
- 本次檢視起點 HEAD 為 `bc028ab`；該證據之後，`src/note_filler/pipeline.py`、
  `src/note_filler/write.py`、`src/note_filler/correction.py` 已加入非空成品、
  逐段追溯、寫作失敗降級、引用範圍與論點綁定等實質路徑。
- 本輪離線四硬閘回歸通過，但依專案「integration 平時跳過」規則，沒有對外呼叫
  Grok／Twinkle；因此不能把離線 PASS 說成目前 HEAD 的真服務 e2e PASS。

## 本體、fixture、marker 與前置條件

| 層級 | 現行行為 | 最小必要條件 |
|---|---|---|
| 測試本體 | 讀取 `tests/fixtures/real_note.txt`，建立 `LawLookup`、`GrokClient`、`TwinkleClient`，最多跑 pipeline 6 次，再套用完整不變式 | 目標 node 必須被 pytest 收集並實際選取 |
| fixture | 固定 UTF-8 文字，內容含行政處分定義、種類與救濟；測試沒有注入 pytest fixture | 檔案必須存在且可讀；它在任何 runtime skip 判斷前就會被讀取 |
| marker | 僅有 `@pytest.mark.integration`，沒有 decorator 型 `skipif` | 必須覆寫 `pyproject.toml` 的預設 `-m 'not integration'` |
| 法規索引 | 函式內先檢查 `data/law_index.db` 是否存在 | 避免 skip 只需檔案存在；跑完整路徑則還要 SQLite 可讀、含 `law_articles` schema 與可召回的 Level A 條文 |
| Grok 前置 | `_grok_up()` 只做 `127.0.0.1:8318` TCP connect | 避免 skip 只需 TCP 成功；跑完整路徑還需 `/v1/chat/completions` 可用、`grok-4.3` 回傳 `choices[0].message.content` |
| Twinkle 前置 | `_twinkle_ready()` 只檢查 `TWINKLE_HUB_TOKEN` 是否為非空字串 | 避免 skip 只需非空；要驗真 Twinkle，token 必須有效、MCP 端點可達且查詢至少回一筆 Level B |

### 選入測試的最小命令

以下只移除預設 marker 排除，仍保留 strict marker 與 warning 品質閘：

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest `
  "tests/test_e2e_acceptance.py::test_e2e_acceptance_real" `
  -m integration `
  -o "addopts=-p no:asyncio --strict-markers -W error::DeprecationWarning -W error::PendingDeprecationWarning" `
  -vv --tb=short --color=no
```

此命令會對外呼叫服務；本輪僅以同參數加 `--collect-only` 驗證選取結果為
`1 test collected`，沒有執行付費或外部整合流量。

## 真正觸發斷言情境的最小資料流

通過 collection 與 runtime guard 只代表測試開始執行。要讓此 fixture 真的走到
被檢視的高風險情境，至少還要同時成立：

1. Grok 將 fixture 判為 `law`，使法制檢索與 pipeline 法條查核路徑啟用。
2. 問題生成至少回一個非空問題，gap 判定至少保留一個 `partial` 或 `missing`；
   fixture 本身沒有硬編碼缺口，故「讀到檔案」不保證會產生 supplement。
3. 關鍵詞抽取回有效 JSON，且法規索引以該詞召回至少一筆 Level A `Source`。
4. writer 在補充文字中輸出有效 `[^n]`，且該 marker 指向 Level A 來源；只有實際
   被引用的來源才會保留到成品。若前次沒有 Level A，測試最多再跑 5 次。
5. 最終至少有一個 supplement，並依序通過原稿逐字、無來源
   `pending_evidence`、法條存在、Markdown／JSON、Level A 與 verified grounding
   斷言。

## 「可進入／可通過」不等於「已驗真 Twinkle」

這是本次重檢最重要的邊界：

- `TwinkleClient.search()` 遇到 token、網路或 MCP 錯誤會回 `[]`，不會中止
  pipeline。
- e2e 的品質斷言要求至少一個 Level A，但沒有要求 Level B；verified 也允許
  單一 Level A 來源。
- 因此任意非空但無效的 token 足以越過 skip，且只要法規 Level A 路徑成功，
  此 e2e 仍可能 PASS。這個 PASS 不能單獨證明 Twinkle token、session 或查詢結果
  正常。

若要證明測試註解聲稱的「真 Grok＋真 Twinkle＋真 law」完整情境，除上述條件外，
還必須觀察至少一筆實際 Level B；現行 e2e 本體沒有這個斷言。已有
`test_retrieve_for_gap_real_twinkle_smoke` 與 `test_search_real_twinkle_hub` 分別要求
Level B／非空結果，但它們同樣是預設 deselected，不能拿預設測試 PASS 代替。

## 本輪可重現證據

| 驗證 | 結果 |
|---|---|
| 預設 `pytest --collect-only -q --deselected-details` | `701/712` collected，`11 deselected` |
| 目標 node 覆寫 marker 後 collect-only | `1 test collected in 0.04s` |
| `test_e2e_minimal_quality_gates_offline_regression` | `1 passed in 0.05s` |
| Twinkle transport 降級＋單一 Level A verified 契約 | `2 passed in 0.11s` |
| 現場前置探測 | fixture 存在；law DB `24,129,536` bytes；token 非空；TCP `8318` 可達 |
| 真 Grok／Twinkle e2e | **本輪未執行**；HTTP、token 有效性、MCP 回傳與目前 HEAD 真跑結果仍未知 |

以上只整理觸發條件，未修改 marker、fixture、測試本體、allowlist 或既有品質閘。
