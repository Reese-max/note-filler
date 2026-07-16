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
- [ ] 在 CI/測試設定中新增或更新一個 dependency-upgrade 測試工作，明確安裝最新相容版本的 fastapi、starlette、httpx 後執行完整測試，並保存該 job 的通過輸出作為佐證。 <!-- adng:autopilot goal:8a0d round:0 --> <!-- adng:blocked reason="連敗 3 次，人工介入" -->
- [x] 以 `pytest -W error::DeprecationWarning -W error::PendingDeprecationWarning` 執行測試，修正所有由 fastapi.testclient、starlette.testclient、httpx 觸發的 deprecation warning，確保驗收輸出中可證明不再存在該風險。 <!-- adng:autopilot goal:8a0d round:0 --> <!-- adng:done 938a672 (人工標記:2026-07-16 事故中引擎繞道 main 直接完成於 58df3e8+938a672,已人工實跑驗證 102 passed 無 deprecation warning) -->
- [x] 掃描測試程式碼中所有 `fastapi.testclient`、`starlette.testclient`、`httpx.Client(app=...)`、`httpx.AsyncClient(app=...)` 等即將失效或高風險用法，改為目前支援的 `ASGITransport`/相容測試客戶端初始化方式。 <!-- adng:autopilot goal:8a0d round:0 --> <!-- adng:done 58df3e8 (人工標記:同上,test_server.py 已全面改用 httpx.AsyncClient+ASGITransport) -->
- [x] 提交實際修改過的測試檔、依賴鎖定檔或 CI 設定檔作為佐證；目前僅有「102 passed」不足以證明已移除目標指定的相依 API 風險。 <!-- adng:autopilot goal:8a0d round:0 --> <!-- adng:done 938a672 (人工標記:佐證即 58df3e8+938a672 兩筆已合入 main 的測試檔改動) -->
