<!--
  adng backlog 檔案格式說明(autodev-ng 接線;本檔由 configs/note-filler.json 的
  backlogFile 指向):

  - 每個任務一行,格式固定為: - [ ] 任務文字
  - 任務完成後系統會自動改成 `- [x]` 並在行尾加上一段 done 註記(含 commit hash)。
  - 任務被判定 blocked 時系統會自動保持 `- [ ]` 並在行尾加上一段 blocked 註記(含原因)。
  - 系統只會「改既有任務行的勾選狀態並在行尾加註記」,絕不會自己新增/刪除/改寫任務文字
    (鐵律 #1:永不自生任務)。
  - 只有使用者可以在本檔新增任務行;新增時請照上面的格式,一行一個任務,
    以 `- [ ] ` 開頭。可在任務文字開頭加 [engine:devin] 等 tag 指定引擎。

  目前尚無任務——perpetual 模式會自主發現問題並立案;要指定工作請在下面加任務行。
-->
- [ ] [engine:devin] 建立 dependency-upgrade 驗證機制：新增一個可重複執行的檢查腳本（例如 scripts/dep_upgrade_check.py 或同等 make/tox 任務），在隔離的臨時 venv 安裝最新相容版本的 fastapi、starlette、httpx 後執行完整測試套件，並把使用方式與一次實際通過輸出的節錄記錄在 docs/ 下的說明檔，一起 commit。 <!-- adng:autopilot goal:8a0d round:0 (人工改寫重派:原任務連敗 3 次肇因於已修復的 worktree 環境缺陷,見 autodev-ng 047f26a) -->
- [x] 以 `pytest -W error::DeprecationWarning -W error::PendingDeprecationWarning` 執行測試，修正所有由 fastapi.testclient、starlette.testclient、httpx 觸發的 deprecation warning，確保驗收輸出中可證明不再存在該風險。 <!-- adng:autopilot goal:8a0d round:0 --> <!-- adng:done 938a672 (人工標記:2026-07-16 事故中引擎繞道 main 直接完成於 58df3e8+938a672,已人工實跑驗證 102 passed 無 deprecation warning) -->
- [x] 掃描測試程式碼中所有 `fastapi.testclient`、`starlette.testclient`、`httpx.Client(app=...)`、`httpx.AsyncClient(app=...)` 等即將失效或高風險用法，改為目前支援的 `ASGITransport`/相容測試客戶端初始化方式。 <!-- adng:autopilot goal:8a0d round:0 --> <!-- adng:done 58df3e8 (人工標記:同上,test_server.py 已全面改用 httpx.AsyncClient+ASGITransport) -->
- [x] 提交實際修改過的測試檔、依賴鎖定檔或 CI 設定檔作為佐證；目前僅有「102 passed」不足以證明已移除目標指定的相依 API 風險。 <!-- adng:autopilot goal:8a0d round:0 --> <!-- adng:done 938a672 (人工標記:佐證即 58df3e8+938a672 兩筆已合入 main 的測試檔改動) -->
- [ ] 全域搜尋測試碼中所有 `fastapi.testclient.TestClient`、`starlette.testclient.TestClient` 與直接依賴 `httpx.Client`／`httpx.AsyncClient` 建立測試請求的用法，列出所有受影響檔案與目前用法型態。 <!-- adng:autopilot goal:8a0d round:1 --> <!-- adng:blocked reason="連敗 3 次，人工介入" -->
- [x] 將使用 `TestClient` 的測試改寫為明確的 `httpx.ASGITransport` 搭配 `httpx.AsyncClient`（或等效的非 deprecated 寫法），並同步調整測試為 `async`/`pytest.mark.anyio` 風格以維持行為一致。 <!-- adng:autopilot goal:8a0d round:1 --> <!-- adng:done ceb2d310dc68ae3985324fb67daff17848cfbab3 -->
- [x] 若有共用測試工具、fixture 或 helper 建立了 `app` 測試客戶端，集中改成新版封裝，避免個別測試仍直接呼叫已不穩定 API。 <!-- adng:autopilot goal:8a0d round:1 --> <!-- adng:done fc6c3a16f49a9caacdfe778cab80bceb530dbe70 -->
- [ ] 執行 `pytest -m "not integration" -q`，針對因 client 改寫導致失敗的測試逐一修正斷言、事件迴圈或生命週期處理，直到在最新相容版本下通過。 <!-- adng:autopilot goal:8a0d round:1 --> <!-- adng:blocked reason="連敗 3 次，人工介入" -->
- [x] 檢查測試依賴與鎖定版本設定，確認不再需要依賴會觸發 deprecation 的組合，必要時更新或補充最小相容版本說明。 <!-- adng:autopilot goal:8a0d round:1 --> <!-- adng:done ce9a2498a6505c843cd3793b28c6a6c0a52f29fe -->
- [x] 在 CI/本地驗收中加入以最新相容版本安裝 `fastapi`、`starlette`、`httpx` 的測試環境，並提交對應 lock/constraints 或 CI job，證明升級後測試仍通過。 <!-- adng:autopilot goal:8a0d round:0 --> <!-- adng:done 467c62157e14caecdbdd4914ebe926c269618a9f -->
- [x] 新增或調整測試指令為 `pytest -W error::DeprecationWarning -W error::PendingDeprecationWarning`，確保 `fastapi.testclient`／`starlette.testclient`／`httpx` 相關棄用警告會使驗收失敗。 <!-- adng:autopilot goal:8a0d round:0 --> <!-- adng:done 10e97c80510db48580117291b56ee839842063ee -->
- [ ] 掃描並移除測試碼中對即將失效 API 的直接使用，例如 `httpx.Client(app=...)` 或已棄用的 TestClient 初始化方式，改為目前支援的 `ASGITransport`／相容寫法。 <!-- adng:autopilot goal:8a0d round:0 --> <!-- adng:blocked reason="連敗 3 次，人工介入" -->
- [ ] 提交實際修改檔案與佐證輸出，包含相依版本、測試指令、完整 warnings 結果；目前只有 `102 passed` 無法證明已消除 deprecation 風險。 <!-- adng:autopilot goal:8a0d round:0 -->
- [ ] 盤點並移除/改寫測試中所有直接或間接依賴即將失效 API 的用法，特別是 `fastapi.testclient.TestClient`、`starlette.testclient.TestClient` 與受影響的 `httpx` client 初始化參數；提交對應程式碼變更。 <!-- adng:autopilot goal:8a0d round:0 -->
- [ ] 在最新相容版本組合下重新安裝並執行測試，例如升級 `fastapi`、`starlette`、`httpx` 至專案允許範圍內最新版，並提供 `pip freeze`/lockfile 與測試輸出佐證。 <!-- adng:autopilot goal:8a0d round:0 -->
- [ ] 以 warning 視為失敗執行測試，例如 `pytest -W error::DeprecationWarning -W error::PendingDeprecationWarning`，確認不再出現相關 deprecation 風險並提交輸出。 <!-- adng:autopilot goal:8a0d round:0 -->
- [ ] 新增或更新 CI 驗證步驟，使其在相容的最新版依賴環境中執行測試，避免只在舊版鎖定依賴下通過。 <!-- adng:autopilot goal:8a0d round:0 -->
