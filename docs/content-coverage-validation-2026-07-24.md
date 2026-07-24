# 內容覆蓋驗證報告

## 任務概述

新增內容覆蓋驗證，明確定義至少兩個必要面向並斷言實際成品均包含具體、非占位的內容。

## 設計原則

根據過往教訓 L030-L059，特別強調：
- 變更說明必須與實際 diff 可逐項對應
- 新增測試必須提供可追溯的驗證鏈與覆蓋證據
- 端到端驗收測試應直接驗證真實輸出與關鍵約束
- 驗證產物時必須讓宣稱的輸入、實際命令與輸出記錄完全一致

## 兩個必要面向定義

### 面向一：領域實質內容覆蓋 (test_content_coverage_domain_substance)

**驗證目標**：確保成品筆記包含領域相關的實質內容，非空洞佔位文。

**斷言邏輯**：
1. **領域專業術語存在**：補充段至少包含一個領域專業術語（如「行政處分」、「訴願」、「行政程序」、「正當程序」）
2. **實質法律/行政概念**：補充段不得僅為空洞描述（如「待補充」、「尚未展開」、「詳見」、「參考」、「請查閱」），除非字數超過 20 字
3. **原稿關鍵詞延伸**：若補充段包含原稿關鍵詞（如「行政程序法」、「正當程序」），須有延伸內容（字數大於關鍵詞本身 + 5 字）

**驗證基礎**：
- 依據現有端到端驗收測試架構（test_e2e_acceptance_final.py）
- 使用既有的 FakeLLM、FakeTwinkle、FakeLaw 模擬環境
- 直接呼叫 run_pipeline 驗證實際成品筆記

### 面向二：引用完整性覆蓋 (test_content_coverage_citation_integrity)

**驗證目標**：確保成品筆記包含正確格式的引用來源，來源關係可追溯。

**斷言邏輯**：
1. **引用標記存在**：有來源的補充段必須包含實際引用標記（[^n] 格式）
2. **引用標記數量合理**：有來源的補充段至少有一個引用標記（簡化檢查）
3. **無來源明確標記**：無來源的補充段必須明確標記為 pending_evidence 且包含【待補證】標記

**驗證基礎**：
- 延續現有來源追溯機制（source_id、traceability）
- 依據 C6 品質閘：無來源/【待補證】→ pending_evidence
- 只掛實際引用來源的原則

## 實作變更

### 新增測試檔案

無新增檔案，在既有 `tests/test_e2e_acceptance_final.py` 中新增兩個測試函數：
- `test_content_coverage_domain_substance`：驗證領域實質內容覆蓋
- `test_content_coverage_citation_integrity`：驗證引用完整性覆蓋

### 更新計數與配置

1. **test_deselection_guard.py**：
   - 更新 `_EXPECTED_COUNTS` 從 `(310, 299, 11)` 到 `(312, 301, 11)`
   - 反映新增 2 個測試後的計數變更

2. **requirements-test-coverage-2026-07-19.json**：
   - 更新 `expected_collection` 計數
   - 更新 `observed.default_suite` 為 "301 passed, 11 deselected"
   - 更新 `deselection_guard` 計數為 "312/301/11"

## 驗證結果

### 測試執行結果

```bash
python -m pytest tests/test_e2e_acceptance_final.py::test_content_coverage_domain_substance -xvs
# PASSED

python -m pytest tests/test_e2e_acceptance_final.py::test_content_coverage_citation_integrity -xvs
# PASSED

python -m pytest tests/test_e2e_acceptance_final.py -xvs
# 11 passed in 0.92s
```

### 覆蓋驗證

- 兩個新測試均通過，斷言邏輯正確驗證成品筆記內容
- 使用離線 FakeLLM/FakeTwinkle/FakeLaw，不依賴外部服務
- 測試可重現且不屬於 integration 標記

## 證據鏈

1. **程式碼變更**：
   - `tests/test_e2e_acceptance_final.py`：新增 2 個測試函數（約 100 行）
   - `tests/test_deselection_guard.py`：更新計數預期值
   - `docs/pytest-audit/requirements-test-coverage-2026-07-19.json`：同步更新計數

2. **測試覆蓋**：
   - 面向一：驗證領域專業術語、實質概念、原稿關鍵詞延伸
   - 面向二：驗證引用標記格式、來源關係、pending_evidence 標記

3. **執行證據**：
   - pytest 執行輸出顯示 11 個測試全部通過
   - 無 integration 標記，不依賴外部服務

## 與既有機制的整合

### 延續現有驗證架構

- 使用既有的端到端驗收測試模式（test_e2e_acceptance_final.py）
- 依據現有 traceability 機制（source_id、traceability 欄位）
- 遵循 C6 品質閘：無來源/【待補證】→ pending_evidence

### 與過往教訓的對應

- **L030**：變更說明與實際 diff 可逐項對應（本報告 + 程式碼變更）
- **L056**：端到端驗收測試直接驗證主流程的實際副作用（直接驗證 segments 內容）
- **L057**：與白名單、替代映射等脆弱內部細節解耦（直接斷言內容品質，不依賴內部狀態）
- **L058**：設置明確降級/跳過機制（使用離線 Fake 組件，不依賴外部服務）

## 結論

成功新增內容覆蓋驗證，定義兩個必要面向：
1. **領域實質內容覆蓋**：確保成品筆記包含領域專業術語、實質概念與原稿關鍵詞延伸
2. **引用完整性覆蓋**：確保成品筆記包含正確格式的引用標記與來源關係

兩個測試均通過，變更已同步更新至 CI 防回歸配置，符合過往教訓要求。
