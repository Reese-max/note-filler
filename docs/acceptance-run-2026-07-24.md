# 最小驗收命令重跑報告 2026-07-24

## 驗收目標

重跑與主流程直接相關的最小驗收命令，確認修正後在既有路徑下能穩定產出至少一份可驗證的實際筆記，且輸出中可明確對應到來源與內容覆蓋面。

## 執行命令

```
python -X utf8 -m pytest tests/test_pipeline.py tests/test_note_product_gate.py \
  tests/test_e2e_acceptance.py::test_e2e_structural_invariants \
  tests/test_e2e_acceptance.py::test_e2e_offline_supplement_quality_boundary \
  tests/test_e2e_acceptance.py::test_e2e_minimal_quality_gates_offline_regression \
  -v --tb=short
```

加上全量非整合測試：

```
python -X utf8 -m pytest -v --tb=short
```

## 結果摘要

| 測試集 | 通過 | 跳過(integration) | 失敗 |
|---|---|---|---|
| 主流程最小驗收（5 檔） | 16 | 1 | 0 |
| 全量非整合（286 collected） | 275 | 11 | 0 |

## 主流程覆蓋對照

### test_pipeline.py（核心管線）
- `test_run_pipeline_invariant`：FakeLLM + FakeTwinkle → 2 gap、gap1 無源→pending_evidence、gap2 兩獨立 A/B 源→verified，補充段非空 ✅
- `test_run_pipeline_law_domain_runs_citation_check`：law 領域每補充段觸發 check_law_citations(text=...) ✅
- `test_run_pipeline_malformed_gap_output_falls_back_to_pending`：JSON 解析失敗→fallback pending_evidence ✅
- `test_original_text_immutable_in_output`：原文段逐字不變、anchor_idx 正確 ✅

### test_note_product_gate.py（非空筆記產出閘）
- `test_require_non_empty_rejects_blank_product_with_reason`：空白成品→RuntimeError ✅
- `test_require_non_empty_rejects_whitespace_or_audit_only_with_reason`：僅空白段→RuntimeError ✅
- `test_require_non_empty_accepts_original_or_supplement`：有原文或補充即通過 ✅
- `test_require_non_empty_emits_audit_event`：空白成品觸發 note_product_empty 稽核事件 ✅
- `test_run_pipeline_produces_non_empty_traceable_notes`：主流程產出非空原文+補充段 ✅
- `test_main_flow_actual_note_has_traceable_source_and_extension`：產出含可追溯來源（sources 非空）+ 延伸論點（非【待補證】占位）+ markdown 含 [^n] ✅
- `test_run_pipeline_empty_input_and_no_gaps_fails_product_gate`：空輸入→不得表面成功 ✅
- `test_process_file_rejects_empty_product_stub_with_reason`：CLI 交付層拒絕空白成品 ✅
- `test_process_file_success_requires_non_empty_body`：CLI 交付層要求非空正文 ✅

### test_e2e_acceptance.py（離線結構不變式）
- `test_e2e_structural_invariants`：原稿逐字不變 + 無來源→pending_evidence + 法條離線查核 + markdown 格式鎖定 + 參考區塊含日期 + to_json 可序列化 ✅
- `test_e2e_offline_supplement_quality_boundary`：離線路徑觸發 _assert_supplement_quality（Level A 路由 / 非原始記錄倒出 / [^n] 註腳）✅
- `test_e2e_minimal_quality_gates_offline_regression`：四項硬閘（原稿不變 / pending_evidence / 法條離線查核 / 只掛實際引用）離線最小前置下穩定通過 ✅

## 驗證結論

1. **穩定產出非空筆記**：主流程在 FakeLLM+FakeTwinkle 離線前置下，每次都產出非空 original 段 + 補充段，require_non_empty_note_product 閘通過。
2. **可追溯來源**：補充段掛有 id/title/url/level 皆完整的 Source 物件，markdown 匯出含 [^n] 註腳與參考區塊（含日期），來源可追溯。
3. **內容覆蓋面**：C6 不變式（無源→pending_evidence）、C4 交叉驗證（>=2 獨立 A/B→verified）、C2 法條引用檢查（check_law_citations）、C3 markdown 格式鎖定（to_markdown）全部覆蓋且通過。
4. **原稿逐字不變**：parse_note 契約（full_text = 各段以換行 join）在所有路徑下成立。
5. **全量回歸無失敗**：275 個非整合測試全數通過，無回歸。
