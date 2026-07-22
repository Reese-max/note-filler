# Deselected 測試數量差異分析報告：8 個到 11 個

> 分析日期：2026-07-23
> 任務：查明目標所稱 8 個與實際 11 個 deselected 的差異，逐項分類新增的 3 個測試是預期排除、目標過時或意外漏跑，並修正驗收基準或測試選擇設定

---

## 執行摘要

| 項目 | 數量 | 狀態 |
|---|---:|---|
| 舊文檔聲稱（2026-07-19） | 8 個 | 過時 |
| 新文檔聲稱（2026-07-22） | 11 個 | 正確 |
| 實際執行結果（2026-07-23） | 11 個 | 正確 |
| 差異數量 | +3 個 | 預期新增 |

**結論**：差異來自 2026-07-22 新增的 3 個 integration 測試，所有新增測試都是**預期排除**，排除機制一致且受控。驗收基準已同步更新為 11 個。

---

## 差異測試對照

### 新增的 3 個 deselected 測試（2026-07-22 新增）

| # | 測試 node ID | 新增位置 | 標記位置 | 排除原因 | 分類 |
|---|---|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_representative_domains` | 2026-07-22 | `test_domain.py:76` | `deselected by -m 'not integration'` | **預期排除** |
| 2 | `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix` | 2026-07-22 | `test_gap.py:106` | `deselected by -m 'not integration'` | **預期排除** |
| 3 | `tests/test_write.py::test_write_supplement_real_grok_grounded_output` | 2026-07-22 | `test_write.py:63` | `deselected by -m 'not integration'` | **預期排除** |

### 既有的 8 個 deselected 測試（2026-07-19 已存在）

| # | 測試 node ID | 標記位置 | 排除原因 |
|---|---|---|---|
| 1 | `tests/test_domain.py::test_detect_domain_real_grok_returns_law` | `test_domain.py:62` | `deselected by -m 'not integration'` |
| 2 | `tests/test_e2e_acceptance.py::test_e2e_acceptance_real` | `test_e2e_acceptance.py:244` | `deselected by -m 'not integration'` |
| 3 | `tests/test_gap.py::test_detect_gaps_real_grok` | `test_gap.py:83` | `deselected by -m 'not integration'` |
| 4 | `tests/test_llm.py::test_grok_pong_integration` | `test_llm.py:95` | `deselected by -m 'not integration'` |
| 5 | `tests/test_pipeline.py::test_run_pipeline_real_grok` | `test_pipeline.py:151` | `deselected by -m 'not integration'` |
| 6 | `tests/test_questions.py::test_generate_questions_real_grok` | `test_questions.py:74` | `deselected by -m 'not integration'` |
| 7 | `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | `test_retrieve.py:102` | `deselected by -m 'not integration'` |
| 8 | `tests/test_twinkle.py::test_search_real_twinkle_hub` | `test_twinkle.py:166` | `deselected by -m 'not integration'` |

---

## 分類判定

### 新增測試 1：test_detect_domain_real_grok_representative_domains

**判定**：預期排除

**理由**：
- 測試於 2026-07-22 新增，目的為驗證真 Grok 對四類代表文本（law/admin/exam/other）的語意分類品質
- 已正確標記 `@pytest.mark.integration`（test_domain.py:76）
- 已正確配置 `@pytest.mark.skipif` 條件式略過（test_domain.py:77）
- 已在 `tests/deselected_allowlist.json` 中建立完整記錄，包括：
  - 排除原因證據（pyproject.toml:32 的 `-m 'not integration'`）
  - 替代測試覆蓋（4 個 FakeLLM 測試）
  - 覆蓋缺口說明（真模型分類品質需 integration 執行）
  - 減緩措施證據（CI workflow_dispatch 觸發 test-integration job）

**非意外漏跑證據**：
- 排除機制與既有 8 個測試完全一致
- 沒有使用 `-k` 過濾、`--deselect` 或其他條件式收集機制
- CI 矩陣設定與排除政策一致

---

### 新增測試 2：test_detect_gaps_real_grok_semantic_matrix

**判定**：預期排除

**理由**：
- 測試於 2026-07-22 新增，目的為驗證真 Grok 對 covered/missing 問題的語意判斷
- 已正確標記 `@pytest.mark.integration`（test_gap.py:106）
- 已正確配置 `@pytest.mark.skipif` 條件式略過（test_gap.py:107）
- 已在 `tests/deselected_allowlist.json` 中建立完整記錄，包括：
  - 排除原因證據（pyproject.toml:32 的 `-m 'not integration'`）
  - 替代測試覆蓋（2 個 FakeLLM 測試）
  - 覆蓋缺口說明（真模型語意判斷需 integration 執行）
  - 減緩措施證據（CI workflow_dispatch 觸發 test-integration job）

**非意外漏跑證據**：
- 排除機制與既有 8 個測試完全一致
- 沒有使用 `-k` 過濾、`--deselect` 或其他條件式收集機制
- CI 矩陣設定與排除政策一致

---

### 新增測試 3：test_write_supplement_real_grok_grounded_output

**判定**：預期排除

**理由**：
- 測試於 2026-07-22 新增，目的為驗證真 Grok 在固定來源下的 grounded 寫作品質
- 已正確標記 `@pytest.mark.integration`（test_write.py:63）
- 已正確配置 `@pytest.mark.skipif` 條件式略過（test_write.py:64）
- 已在 `tests/deselected_allowlist.json` 中建立完整記錄，包括：
  - 排除原因證據（pyproject.toml:32 的 `-m 'not integration'`）
  - 替代測試覆蓋（2 個 FakeLLM 測試）
  - 覆蓋缺口說明（真模型 grounded 寫作品質需 integration 執行）
  - 減緩措施證據（CI workflow_dispatch 觸發 test-integration job）

**非意外漏跑證據**：
- 排除機制與既有 8 個測試完全一致
- 沒有使用 `-k` 過濾、`--deselect` 或其他條件式收集機制
- CI 矩陣設定與排除政策一致

---

## 排除機制一致性驗證

### 統一排除規則

所有 11 個 deselected 測試皆透過以下統一機制排除：

#### 1. Marker 標記
每個測試都有 `@pytest.mark.integration` 標記：

```python
@pytest.mark.integration
@pytest.mark.skipif(not _grok_reachable(), reason="grok proxy(127.0.0.1:8318)未上線,條件式略過")
def test_xxx():
    ...
```

#### 2. Pytest 配置
`pyproject.toml` 中的統一排除設定：

```toml
[tool.pytest.ini_options]
addopts = "-p no:asyncio --strict-markers -m 'not integration' -W error::DeprecationWarning -W error::PendingDeprecationWarning"
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

#### 3. 排除原因
所有測試的排除原因皆為：`deselected by -m 'not integration'`

### 排除機制確認

| 機制 | 是否使用 | 說明 |
|---|---|---|
| `-m 'not integration'` (addopts) | **是** | 唯一 collection 排除機制 |
| `-k` keyword 過濾 | 否 | 未使用 |
| `--deselect` | 否 | 未使用 |
| 條件式收集 (pytest_collection_modifyitems) | 否 | 無此 hook |
| CI 矩陣設定 | 一致 | test-pinned/test-latest 跳過 integration，test-integration 專門跑 |

---

## 驗收基準修正

### 已修正的檔案

1. **`tests/deselected_allowlist.json`**
   - 已從 8 筆更新為 11 筆
   - 新增 3 筆完整記錄，包含排除原因、替代測試、覆蓋缺口、減緩措施

2. **`tests/test_deselection_guard.py`**
   - `_EXPECTED_COUNTS = (163, 152, 11)` 已更新為 11 個 deselected
   - `_NOT_REPRODUCIBLE_EVIDENCE` 已新增 3 筆測試的 NOT-REPRODUCIBLE 證據

3. **`docs/deselected-8-evidence-index.json`**
   - 已重命名為 `docs/deselected-11-evidence-index.json`
   - 已從 8 個節點更新為 11 個節點
   - 已新增 3 個測試的完整證據索引

### CI Gate 驗證

- `scripts/validate_deselection_ci.py` 可正常驗證 11 個 deselected 測試
- 守衛測試 `tests/test_deselection_guard.py` 可通過
- CI 矩陣設定與排除政策一致

---

## 可重現驗證命令

### 獲取實際 deselected 清單
```bash
python -X utf8 -m pytest tests/ -m "not integration" --collect-only -q --deselected-details
```

### 僅收集 integration 測試
```bash
python -X utf8 -m pytest tests/ -m integration --collect-only -q
```

### 執行 integration 測試（需 grok proxy）
```bash
python -X utf8 -m pytest tests/ -m integration -v
```

### 驗證 deselected 政策
```bash
python scripts/validate_deselection_ci.py
```

### 執行守衛測試
```bash
python -X utf8 -m pytest tests/test_deselection_guard.py -v
```

---

## 結論

1. **數量差異來源**：2026-07-22 新增了 3 個 integration 測試，從 8 個增加到 11 個
2. **分類判定**：新增的 3 個測試都是**預期排除**，非目標過時或意外漏跑
3. **排除機制一致性**：所有 11 個測試都使用統一的 `@pytest.mark.integration` 標記與 `-m 'not integration'` 排除機制
4. **無其他排除條件**：沒有使用 `-k` 過濾、`--deselect` 或目錄排除條件
5. **受控設計意圖**：所有 integration 測試都需要真實 grok proxy，預設 CI 跳過以避免依賴外部服務
6. **驗收基準已修正**：
   - `tests/deselected_allowlist.json` 已更新為 11 筆
   - `tests/test_deselection_guard.py` 已更新 `_EXPECTED_COUNTS = (163, 152, 11)`
   - `docs/deselected-8-evidence-index.json` 已重命名並更新為 `docs/deselected-11-evidence-index.json`
7. **CI Gate 驗證通過**：`scripts/validate_deselection_ci.py` 與 `tests/test_deselection_guard.py` 皆可通過

---

## 關聯文件

| 文件 | 用途 | 狀態 |
|---|---|---|
| `tests/deselected_allowlist.json` | 機器可讀的 11 筆 deselected 清單 | 已更新 |
| `tests/test_deselection_guard.py` | deselected 守衛測試 | 已更新 |
| `scripts/validate_deselection_ci.py` | CI deselected 政策驗證腳本 | 無需修改 |
| `docs/deselected-11-evidence-index.json` | 11 筆 deselected 證據索引 | 已更新 |
| `docs/deselected-11-nodeids-final-collect-2026-07-23.md` | 11 筆 deselected 最終收集報告 | 已存在 |
| `docs/deselected-count-discrepancy-investigation-2026-07-22.md` | 數量差異調查報告 | 已存在 |
| `docs/deselected-missing-not-reproducible-evidence-2026-07-22.md` | 新增 3 筆測試的 NOT-REPRODUCIBLE 證據 | 已存在 |
