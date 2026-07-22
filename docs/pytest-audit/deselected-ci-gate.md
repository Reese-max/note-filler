## CI Deselected 測試稽核（防漏跑）
- 產生時間: 2026-07-23 03:51:21+0800
- 工具: validate_deselection_ci.py

- 全量 collected: 171
- 預設 selected: 160
- 預設 deselected: 11
- allowlist/預期數量: 11

### 本次 deselected 清單（含原因）
1. `tests/test_domain.py::test_detect_domain_real_grok_representative_domains`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 未在 requirements matrix 中
   - 憑證: 預設 -m 'not integration' 排除；四類代表文本需真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
   - 替代覆蓋數: 4

2. `tests/test_domain.py::test_detect_domain_real_grok_returns_law`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 中
   - 憑證: 預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
   - 替代覆蓋數: 2

3. `tests/test_e2e_acceptance.py::test_e2e_acceptance_real`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 高
   - 憑證: 預設 -m 'not integration' 在 collection 階段排除；真跑需要 data/law_index.db、grok proxy 與 TWINKLE_HUB_TOKEN，任一前置條件不足即 skip
   - 替代覆蓋數: 8

4. `tests/test_gap.py::test_detect_gaps_real_grok`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 高
   - 憑證: 預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
   - 替代覆蓋數: 2

5. `tests/test_gap.py::test_detect_gaps_real_grok_semantic_matrix`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 未在 requirements matrix 中
   - 憑證: 預設 -m 'not integration' 排除；covered/missing 語意矩陣需真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
   - 替代覆蓋數: 2

6. `tests/test_llm.py::test_grok_pong_integration`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 高
   - 憑證: 預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
   - 替代覆蓋數: 2

7. `tests/test_pipeline.py::test_run_pipeline_real_grok`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 高
   - 憑證: 預設 -m 'not integration' 在 collection 階段排除；只要真實 grok proxy 才能執行，Twinkle 與 law 雖以 fake 隔離仍保留 integration 邊界
   - 替代覆蓋數: 5

8. `tests/test_questions.py::test_generate_questions_real_grok`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 中
   - 憑證: 預設 -m 'not integration' 在 collection 階段排除；需要真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
   - 替代覆蓋數: 4

9. `tests/test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 高
   - 憑證: 預設 -m 'not integration' 在 collection 階段排除；真跑需要 data/law_index.db、grok proxy 與 TWINKLE_HUB_TOKEN
   - 替代覆蓋數: 9

10. `tests/test_twinkle.py::test_search_real_twinkle_hub`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 高
   - 憑證: 預設 -m 'not integration' 在 collection 階段排除；真跑需要 TWINKLE_HUB_TOKEN，缺 token 時由函式內 pytest.skip 略過
   - 替代覆蓋數: 5

11. `tests/test_write.py::test_write_supplement_real_grok_grounded_output`
   - 採集原因: deselected by -m 'not integration'
   - 核准決策: acceptable_unexecuted
   - 安全風險: 未在 requirements matrix 中
   - 憑證: 預設 -m 'not integration' 排除；固定來源的 grounded writer 語意需真實 grok proxy (127.0.0.1:8318)，proxy 不可達時由 skipif 略過
   - 替代覆蓋數: 2

### 失敗原因
- （無）
