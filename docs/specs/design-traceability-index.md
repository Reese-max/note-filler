# 設計追溯索引（Design Traceability Index）

## 版本

- 日期：2026-07-27
- 目的：建立需求編號、設計編號與驗收項目編號之間的追溯對照，確保每一份設計稿都可回指需求來源與驗收結論。

## 1. 需求編號索引（Requirement Index）

從原始設計規格 `docs/specs/2026-07-15-note-filler-design.md` 提取之需求項目：

| 需求編號 | 需求標題 | 原始章節 | 說明 |
|----------|----------|----------|------|
| R-01 | 目標與一句話定義 | §1 | 輸入筆記→AI 找缺口→檢索一手源→交叉驗證→產出訂正稿 |
| R-02 | 範圍 - MVP | §2 | 領域、輸入、LLM、部署、產出之最小可行範圍 |
| R-03 | 復用策略 | §3 | 與公文ai agent 的模組復用決策 |
| R-04 | 系統架構 | §4 | 端到端資料流與處理流程 |
| R-05 | 自建模組 - Gap 偵測 | §5.1 | 研究問題 vs 筆記內容之缺口偵測 |
| R-06 | 自建模組 - 訂正稿資料結構 | §5.2 | 段落陣列結構與原文 immutable 設計 |
| R-07 | 品質閘 | §6 | 8 項程式硬閘門規則 |
| R-08 | LLM 接法 | §7 | grok proxy 連接與抽象介面 |
| R-09 | UI MVP | §8 | 最小 web 界面：上傳→雙欄→導出 |
| R-10 | 開發方式 | §9 | autodev-ng + codex-spark 驅動 |
| R-11 | MVP 不做清單 | §10 | YAGNI 排除項目 |
| R-12 | 驗收標準 | §12 | MVP done 的驗收定義 |

## 2. 設計編號索引（Design Claim Index）

設計規格文件之驗收主張：

| 設計編號 | 設計標題 | 規格檔 |
|----------|----------|--------|
| D-01 | 介面規格（路由／表單／匯出契約） | `docs/specs/note-filler-interface-contract.md` |
| D-02 | UI／資料狀態轉移（結果暫存 capability／confidence） | `docs/specs/note-filler-state-machine.md` |
| D-03 | 使用者與系統流程（上傳→pipeline→結果→匯出） | `docs/specs/note-filler-user-flow.md` |
| D-04 | 元件責任清單（入口／管線／匯出） | `docs/specs/note-filler-component-responsibilities.md` |
| D-05 | 可重現畫面佐證與索引 | `docs/specs/evidence/ui/index.md` |

## 3. 驗收項目編號索引（Acceptance Item Index）

從測試檔案提取之驗收項目：

| 驗收編號 | 測試項目 | 測試檔 | 驗證內容 |
|----------|----------|--------|----------|
| A-01 | test_index_returns_upload_form | tests/test_server.py | 上傳表單頁面正確渲染 |
| A-02 | test_run_renders_two_columns | tests/test_server.py | 雙欄結果頁正確渲染 |
| A-03 | test_export_returns_markdown_attachment | tests/test_server.py | 匯出 Markdown 附件 |
| A-04 | test_export_without_run_returns_404 | tests/test_server.py | 未執行時匯出回傳 404 |
| A-05 | test_run_pipeline_invariant | tests/test_pipeline.py | Pipeline C6 不變式（無源 pending） |
| A-06 | test_e2e_minimal_quality_gates_offline_regression | tests/test_e2e_acceptance.py | 品質閘離線回歸 |
| A-07 | test_e2e_structural_invariants | tests/test_e2e_acceptance.py | 結構性不變式 |
| A-08 | test_retrieved_five_but_only_two_cited | tests/test_correction.py | 來源數量與引用一致性 |

## 4. 追溯對照表（Traceability Matrix）

### 4.1 需求 → 設計對照

| 需求編號 | 對應設計編號 | 說明 |
|----------|--------------|------|
| R-01 | D-01, D-03 | 目標定義反映在介面與流程設計中 |
| R-02 | D-01, D-09 | MVP 範圍限定介面與 UI 設計 |
| R-03 | D-04 | 復用模組的責任邊界 |
| R-04 | D-03, D-04 | 系統架構對應流程與元件設計 |
| R-05 | D-03 | Gap 偵測在使用者流程中的位置 |
| R-06 | D-02, D-04 | 資料結構反映在狀態轉移與元件設計 |
| R-07 | D-02 | 品質閘規則決定狀態轉移條件 |
| R-08 | D-01 | LLM 接法影響介面設計 |
| R-09 | D-01, D-05 | UI 設計與畫面佐證 |
| R-10 | D-04 | 開發方式影響元件組織 |
| R-11 | - | 不做清單無對應設計 |
| R-12 | D-01~D-05 | 驗收標準涵蓋所有設計 |

### 4.2 設計 → 驗收對照

| 設計編號 | 對應驗收編號 | 說明 |
|----------|--------------|------|
| D-01 | A-01, A-02, A-03, A-04 | 介面規格由路由測試驗證 |
| D-02 | A-04, A-05, A-06 | 狀態轉移由匯出與 pipeline 測試驗證 |
| D-03 | A-02, A-03, A-05, A-07 | 使用者流程由多項測試驗證 |
| D-04 | A-01, A-05, A-06, A-08 | 元件責任由各模組測試驗證 |
| D-05 | A-01, A-02, A-03, A-04 | 畫面佐證由 UI 測試驗證 |

### 4.3 需求 → 驗收對照（完整追溯鏈）

| 需求編號 | 對應驗收編號 | 驗證方式 |
|----------|--------------|----------|
| R-01 | A-02, A-05, A-06 | 端到端流程驗證訂正稿產出 |
| R-02 | A-01, A-02, A-03 | MVP 介面功能驗證 |
| R-03 | A-08 | 復用模組的引用一致性 |
| R-04 | A-05, A-07 | 系統架構的結構性驗證 |
| R-05 | A-05 | Gap 偵測邏輯驗證 |
| R-06 | A-02, A-05 | 資料結構與狀態驗證 |
| R-07 | A-06 | 品質閘離線回歸驗證 |
| R-08 | - | LLM 連接由整合測試覆蓋（平時跳過） |
| R-09 | A-01, A-02 | UI 功能驗證 |
| R-10 | - | 開發方式無直接驗收 |
| R-11 | - | 不做清單無驗收 |
| R-12 | A-01~A-08 | 全面驗收 |

## 5. 設計稿追溯標註規範

每份設計稿（D-01~D-05）應包含以下追溯欄位：

```markdown
## 追溯資訊

- **設計編號**: D-XX
- **需求編號**: R-XX, R-XX
- **驗收編號**: A-XX, A-XX
- **追溯狀態**: 完整 / 部分完整 / 待補
```

## 6. 驗證命令

```powershell
# 驗證追溯索引存在
Test-Path docs/specs/design-traceability-index.md

# 驗證設計稿包含追溯標註
Select-String -Path "docs/specs/note-filler-*.md" -Pattern "追溯資訊"

# 驗證 JSON 包含追溯欄位
Get-Content docs/specs/evidence/design-acceptance-claims.json | ConvertFrom-Json | Select-Object -ExpandProperty claims
```

## 7. 結論

本索引建立三層追溯機制：
1. **需求層** (R-01~R-12)：從原始設計規格提取
2. **設計層** (D-01~D-05)：設計驗收主張
3. **驗收層** (A-01~A-08)：測試驗證項目

每一層都可互相追溯，確保設計內容、需求來源與驗收結論可逐項對照。
