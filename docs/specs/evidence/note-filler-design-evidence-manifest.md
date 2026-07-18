# 設計證據與對照檔清單（可核實）

## 日期

- 2026-07-19

## 目的

把「對照表」落地為可查、可回朔的證據檔清單，讓每一條設計證據都對到 repo 內具名檔案（程式、範本、測試）。

## E-01~E-05 規格落點

| 設計項目 | 證據檔 | 回指原檔 |
|---|---|---|
| 介面契約 | `docs/specs/note-filler-interface-contract.md` | `app/server.py`, `app/templates/index.html`, `app/templates/result.html`, `tests/test_server.py` |
| 狀態轉移表 | `docs/specs/note-filler-state-machine.md` | `app/server.py`, `src/note_filler/correction.py`, `src/note_filler/pipeline.py` |
| 使用者流程 | `docs/specs/note-filler-user-flow.md` | `app/server.py`, `src/note_filler/pipeline.py`, `app/templates/result.html` |
| 元件責任清單 | `docs/specs/note-filler-component-responsibilities.md` | `app/server.py`, `src/note_filler/*.py`, `tests/*` |
| 畫面可重現索引 | `docs/specs/evidence/ui/index.md` | `app/templates/index.html`, `app/templates/result.html`, `tests/test_server.py`, `tests/test_e2e_acceptance.py` |

## 畫面佐證（目前補齊狀態）

- 目前完成到「命名檔 + 對照檔」，尚未新增截圖檔（`.png/.jpg/...`）。  
- 若後續要加可視化回歸，建議新增 `docs/specs/evidence/ui/upload-idle.png`、`result-basic.png`、`result-pending.png`，並在 `index.md` 補上 `git status` 命令與捕捉命令。

## 采證條件（最小）

- 每個「設計項目」至少要同時具備：
  1. 對應的證據檔存在（本文件清單）；
  2. 應答到一個以上程式/測試錨點；
  3. 與既有對照表任務可串接（例如缺漏對照、失效排除清單）。

## 下一步（非本輪）

- 將 `docs/specs/evidence/ui/index.md` 轉為「含截圖與路徑」的實體回歸素材索引，這將把「流程可看見」補足成「畫面可重現」。

