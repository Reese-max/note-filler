# 設計佐證缺失與檔案路徑對照（2026-07-19）

## 追溯更新（2026-07-27）

本文件已補上需求編號與驗收項目編號追溯，完整追溯索引見 `docs/specs/design-traceability-index.md`。

## 結論

本次已補齊最小版設計證據：界面契約、流程圖、狀態轉移、元件責任與 UI 證據索引皆有對應文件，且每一項能回指到本 repo 內具名程式/測試檔案。  
目前仍未補實體畫面截圖；若要進入視覺回歸，下一步只需補 `docs/specs/evidence/ui/*.png` 與索引欄位。

現有 UI 行為可從程式與測試反推，但這些檔案是實作／驗證來源，不等同設計規格：

| 現有來源 | 已能佐證 | 尚不能佐證 |
|---|---|---|
| `docs/specs/2026-07-15-note-filler-design.md` | 產品目標、pipeline 架構、雙欄 UI 一句話需求、品質閘 | 畫面結構、完整狀態、互動轉移、元件契約、視覺驗收基準 |
| `docs/superpowers/plans/2026-07-15-note-filler.md` 的 Task 15 | `GET /`、`POST /run`、`GET /export` 與實作步驟 | 這是施工計畫，不是介面／狀態／元件的設計正本 |
| `app/server.py`、`app/templates/index.html`、`app/templates/result.html` | 現行路由、`last_doc` 狀態、實際 HTML 與 inline CSS | 設計意圖、未實作狀態、響應式與無障礙規則 |
| `tests/test_server.py` | 上傳表單、雙欄結果、`verified`／`pending_evidence`、來源展開、匯出 200／404 | 處理中、失敗、重試、空結果、窄螢幕與視覺回歸 |
| repo 內圖片／原型／流程圖檔 | 無 | 目前沒有任何 `.png`、`.jpg`、`.svg`、`.fig`、`.drawio`、`.mmd` 或同類設計產物 |

## 缺失清單 → 對應檔案路徑

沿用既有 `docs/specs/` 作為規格正本，以下 5 項皆已補齊最小證據，文件與既有實作已可交叉驗證（非空殼）：

| ID | 缺失清單 | 現有實作錨點 | 應建立的規格檔／產物位置 | 最小應含內容 |
|---|---|---|---|---|
| D-01 | 介面規格 | `app/templates/index.html`、`app/templates/result.html`、`app/server.py` | `docs/specs/note-filler-interface-contract.md` | 介面端點、欄位、下載入口、`last_doc` 對應行為 |
| D-03 | 使用者與系統流程規格 | `GET /` → `POST /run` → `run_pipeline` → `result.html` → `GET /export`；`src/note_filler/pipeline.py` | `docs/specs/note-filler-user-flow.md` | 正常流程、無來源降級、法條查核降級、輸入／外部服務／匯出失敗分支，以及各分支對應的 UI 狀態；圖可直接用 Mermaid 內嵌於 Markdown |
| D-02 | UI 狀態規格 | `app.state.last_doc`；`Segment.confidence` 的 `verified`／`pending_evidence`；`GET /export` 的 200／404 | `docs/specs/note-filler-state-machine.md` | `GET /`、`POST /run`、`GET /export`、`verified` 與 `pending_evidence` 的轉移規則與可核實條件 |
| D-04 | 元件規格 | `form`、`.cols`、`.supplement`、`.pending`、`details.sources`、`/export` 連結 | `docs/specs/note-filler-component-responsibilities.md` | 入口、管線、驗證與匯出元件責任邊界 |
| D-05 | 可重現的畫面佐證與索引 | 現有模板及 `tests/test_server.py`，但 repo 內無視覺產物 | `docs/specs/evidence/note-filler-design-evidence-manifest.md`；`docs/specs/evidence/ui/index.md` | 對照 manifest、每一場景的測試/路由/檔案錨點；現階段以文件型證據為主，截圖留待後續補齊 |

## 現況狀態與元件基線

後續補規格時應先覆蓋已存在的行為，不能因補設計文件而弱化品質閘：

- 已存在狀態：上傳初始頁、含 `verified` 補充的結果、含 `pending_evidence` 補充的結果、來源展開、可匯出、尚無結果時匯出 404。
- 尚無明確 UI／佐證：已選檔、處理中、無缺口、輸入驗證失敗、pipeline 例外、外部服務降級提示、重試、窄螢幕版面。
- 已存在的邏輯元件只是模板片段，尚無獨立元件檔；D-04 應記錄契約，不要求為了文件而拆程式。
- `original` 必須逐字保留；無來源或 `【待補證】` 必須維持 `pending_evidence`；只顯示實際引用來源；法律補充仍須通過離線法條查核。

## 可重現盤點

盤點基準為開始本任務時的 `HEAD 9e3fc77`，未讀取或引用其他 repo。使用下列 repo 內命令即可重查：

```powershell
git ls-files app
git ls-files docs | rg -i "design|interface|state|flow|component|wire|mock|screen|prototype|evidence"
git ls-files "*.png" "*.jpg" "*.jpeg" "*.webp" "*.gif" "*.svg" "*.fig" "*.sketch" "*.xd" "*.drawio" "*.mmd" "*.mermaid" "*.excalidraw"
rg -n "TemplateResponse|@app\.|app\.state|pending_evidence|details class=\"sources\"" app src/note_filler tests/test_server.py
```

盤點結果：`docs/specs/` 已新增 5 份最小核實證據文件；`app/` 仍只保有 `server.py` 與兩份模板；設計圖片/原型目前仍未落地。  
現況將「缺失」視為「待補截圖」，非「缺規格文件」。
