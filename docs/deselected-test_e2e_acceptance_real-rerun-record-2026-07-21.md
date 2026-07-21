# Deselected 高風險測試獨立重跑記錄：test_e2e_acceptance_real

> **任務**：針對目前仍未能以最小條件重現的那個高風險 deselected node id，建立獨立的重跑記錄：只執行該 node id 的單測命令，完整保留 stdout/stderr、exit code、pytest 版本與環境變數快照，若仍無法重現就正式標註 `NOT-REPRODUCIBLE`。

---

## 目標測試

**Node ID**: `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`

**風險等級**: 高風險（最易形成驗證缺口）

**選定理由**: 此測試涵蓋「真 Grok + 真 TwinkleClient + 真 LawLookup」的完整 pipeline 執行，涉及 5 個 §12 硬不變式、_assert_supplement_quality（Level A 路由）、有界重跑（最多 6 次）取 Level A 路由穩定性。相較其他 7 項，此項同時依賴多個外部服務且斷言最嚴格，故最易因「無法在非-integration 環境重現」而形成驗證缺口。

---

## 執行環境快照

### Pytest 版本

```
pytest 9.1.1
```

### 關鍵環境變數

```json
{
  "PATH": "C:\\Program Files\\PowerShell\\7;C:\\Program Files\\OpenSSH\\;C:\\Windows\\System32;C:\\Windows;D:\\Users\\Administrator\\Desktop\\ffmpeg-n6.1-latest-win64-gpl-shared-6.1\\ffmpeg-n6.1-latest-win64-gpl-shared-6.1\\bin\\ffmpeg-n6.1-latest-win64-gpl-shared-6.1;C:\\ProgramData\\chocolatey\\bin;C:\\Program Files\\nodejs\\;C:\\Program Files (x86)\\NoteBook FanControl\\;C:\\Program Files\\Git\\cmd;C:\\Program Files\\PostgreSQL\\16\\bin;C:\\ProgramData\\mingw64\\mingw64\\bin;C:\\Program Files\\Go\\bin;C:\\Program Files\\GitHub CLI\\;C:\\WINDOWS\\System32\\OpenSSH;C:\\Program Files\\PowerShell\\7\\;C:\\Users\\Administrator\\AppData\\Local\\hermes\\bin;C:\\Users\\Administrator\\AppData\\Local\\hermes\\hermes-agent\\venv\\Scripts;C:\\Users\\Administrator\\bin;C:\\Users\\Administrator\\.cargo\\bin;D:\\Users\\Administrator\\Downloads\\flutter\\flutter\\bin;C:\\Users\\Administrator\\AppData\\Local\\Microsoft\\WindowsApps;C:\\Users\\Administrator\\AppData\\Local\\Programs\\Microsoft VS Code\\bin;C:\\Users\\Administrator\\AppData\\Local\\Programs\\Ollama;C:\\Users\\Administrator\\AppData\\Local\\Packages\\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\\LocalCache\\local-packages\\Python311\\Scripts;C:\\Users\\Administrator\\AppData\\Roaming\\npm;C:\\Users\\Administrator\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Starship.Starship_Microsoft.Winget.Source_8wekyb3d8bbwe;C:\\Users\\Administrator\\.bun\\bin;C:\\Users\\Administrator\\AppData\\Local\\Microsoft\\WinGet\\Links;C:\\Users\\Administrator\\.local\\bin;C:\\Users\\Administrator\\AppData\\Local\\Spectra;C:\\Users\\Administrator\\.multica\\bin;C:\\Users\\Administrator\\go\\bin;C:\\Program Files\\Tesseract-OCR;C:\\Users\\Administrator\\AppData\\Local\\Programs\\Kiro\\bin;C:\\Windows\\System32\\WindowsPowerShell\\v1.0;C:\\Users\\Administrator\\AppData\\Local\\cx\\bin;C:\\Program Files\\Git\\bin;C:\\Users\\Administrator\\AppData\\Local\\Programs\\Cua\\cua-driver\\bin;C:\\Users\\Administrator\\AppData\\Local\\Microsoft\\WinGet\\Packages\\BurntSushi.ripgrep.MSVC_Microsoft.Winget.Source_8wekyb3d8bbwe\\ripgrep-15.1.0-x86_64-pc-windows-msvc;C:\\Users\\Administrator\\AppData\\Local\\Microsoft\\WinGet\\Packages\\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\\node-v24.16.0-win-x64;C:\\Users\\Administrator\\AppData\\Local\\devin\\cli\\bin;C:\\Users\\Administrator\\AppData\\Local\\Programs\\Devin\\bin",
  "TWINKLE_HUB_AUTH": "Bearer sk-bpImUK47G5D-7PRi8ibTRg",
  "TWINKLE_HUB_TOKEN": "sk-bpImUK47G5D-7PRi8ibTRg"
}
```

### Python 執行路徑

```
D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe
```

---

## 執行命令

```powershell
& "D:/Users/Administrator/Desktop/筆記補齊/.venv/Scripts/python.exe" -X utf8 -m pytest tests/test_e2e_acceptance.py::test_e2e_acceptance_real -m integration -v --tb=short --color=no
```

---

## 完整執行輸出（stdout/stderr）

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- D:\Users\Administrator\Desktop\筆記補齊\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Users\Administrator\Desktop\autodev-ng\data\note-filler\worktrees\ed2e30e0
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 1 item

tests/test_e2e_acceptance.py::test_e2e_acceptance_real PASSED            [100%]

======================== 1 passed in 165.41s (0:02:45) ========================
```

---

## 執行結果摘要

| 項目 | 結果 |
|------|------|
| **測試狀態** | PASSED |
| **執行時間** | 165.41 秒（2 分 45 秒） |
| **Exit Code** | 0 |
| **收集數量** | 1 個測試 |
| **通過數量** | 1 個測試 |
| **失敗數量** | 0 個測試 |

---

## 重現性判斷

**判斷結果**: **可重現（REPRODUCIBLE）**

**判斷依據**:
1. 測試在 integration 標記下成功執行並通過
2. Exit code 為 0，表示無任何錯誤
3. 執行時間 165.41 秒在合理範圍內
4. 所有斷言通過，包括 5 個 §12 硬不變式與 _assert_supplement_quality
5. 外部服務（Grok proxy、Twinkle Hub）在執行期間均正常運作

**NOT-REPRODUCIBLE 標註**: 否（測試可重現）

---

## 最小條件驗證

根據 `docs/deselected-minimal-repro-2026-07-18.md` 的最小前置條件：

| 條件 | 狀態 | 驗證結果 |
|------|------|----------|
| `TWINKLE_HUB_TOKEN` 環境變數 | ✅ 已設定 | 有效 token 存在 |
| Grok proxy 於 `127.0.0.1:8318` 可達 | ✅ 可達 | 測試執行期間正常回應 |
| `data/law_index.db` 存在且可讀 | ✅ 存在 | LawLookup 正常運作 |

---

## 結論

`tests/test_e2e_acceptance.py::test_e2e_acceptance_real` 在當前環境條件下**可重現**，測試成功通過所有斷言。該測試雖然依賴多個外部服務（Grok proxy、Twinkle Hub、LawLookup），但在本次執行中所有依賴項均正常運作，因此無需標註為 `NOT-REPRODUCIBLE`。

**替代覆蓋有效性確認**: 由於該測試可重現且通過，現有的替代測試（`test_e2e_structural_invariants`、`test_run_pipeline_invariant` 等）雖然覆蓋了確定性契約，但無法完全替代真實外部服務的端到端驗證。建議在關鍵發布前定期執行此 integration 測試以確保外部服務相容性。

---

## 參考證據來源

| 證據文件 | 路徑 | 內容 |
|----------|------|------|
| 最小重現條件分析 | `docs/deselected-minimal-repro-2026-07-18.md` | 最易形成驗證缺口者之最小非-integration 重現條件 |
| Node id 映射對照 | `docs/deselected-nodeid-evidence-mapping-2026-07-21.md` | 排除依據與共享覆蓋證據 |
| 最終判讀 | `docs/deselected-final-judgment-2026-07-21.md` | 8 個 deselected 測試最終判讀 |

---

## 執行時間戳記

- **執行日期**: 2026-07-21
- **執行時間**: 165.41 秒
- **記錄建立時間**: 2026-07-21
