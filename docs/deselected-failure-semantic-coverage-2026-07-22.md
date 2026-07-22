# Deselected 測試：失敗語義覆蓋對照表

> 產出日期：2026-07-22  
> 範圍：8 個被 `-m 'not integration'` 排除的 `@pytest.mark.integration` 測試  
> 方法論：逐一打開測試本體，萃取是否含有錯誤注入、錯誤碼、重試、fallback、例外傳遞斷言

---

## 背景

8 個整合測試皆為**無參數化(no parametrization)**的單一函式。參數化來源不存在，故「參數化來源萃取」欄位全部為 **N/A（不存在）**。

---

## 對照總表

| # | Node ID | 參數化來源 | 錯誤注入斷言 | 錯誤碼斷言 | 重試斷言 | Fallback 斷言 | 例外傳遞斷言 | 靜默失敗風險 |
|---|---------|-----------|:----------:|:--------:|:--------:|:------------:|:-----------:|:----------:|
| 1 | `test_domain.py::test_detect_domain_real_grok_returns_law` | N/A | ❌ | ❌ | ❌ | ❌ | ⚠️ 隱含 | **YES** |
| 2 | `test_e2e_acceptance.py::test_e2e_acceptance_real` | N/A | ❌ | ❌ | ✅ 重試迴圈×5 | ⚠️ 有條件跳過 | ⚠️ 隱含 | MODERATE |
| 3 | `test_gap.py::test_detect_gaps_real_grok` | N/A | ❌ | ❌ | ❌ | ❌ | ⚠️ 隱含 | **YES** |
| 4 | `test_llm.py::test_grok_pong_integration` | N/A | ❌ | ❌ | ❌ | ❌ | ⚠️ 隱含 | **YES** |
| 5 | `test_pipeline.py::test_run_pipeline_real_grok` | N/A | ❌ | ❌ | ❌ | ❌ | ⚠️ 隱含 | **YES** |
| 6 | `test_questions.py::test_generate_questions_real_grok` | N/A | ❌ | ❌ | ❌ | ❌ | ⚠️ 隱含 | MODERATE |
| 7 | `test_retrieve.py::test_retrieve_for_gap_real_twinkle_smoke` | N/A | ❌ | ❌ | ❌ | ❌ | ⚠️ 隱含 | MODERATE |
| 8 | `test_twinkle.py::test_search_real_twinkle_hub` | N/A | ❌ | ❌ | ❌ | ❌ | ⚠️ 隱含 | MODERATE |

---

## 逐項分析

### 1. `test_detect_domain_real_grok_returns_law`（`test_domain.py:52`）

```python
def test_detect_domain_real_grok_returns_law():
    llm = GrokClient()
    text = "刑法第271條..."
    assert detect_domain(text, llm) == "law"
```

- **錯誤注入斷言**：❌ 無。只驗 happy path（法律文字 → `"law"`）。
- **錯誤碼斷言**：❌ 無。未模擬任何 HTTP error / API error code。
- **重試斷言**：❌ 無。`GrokClient.complete` 無 retry 邏輯。
- **Fallback 斷言**：❌ 無。`detect_domain` 雖對雜訊標籤有 `"other"` fallback（由其他非整合測試驗證），此測試不觸發。
- **例外傳遞斷言**：⚠️ 隱含。`GrokClient.complete`（`llm.py:27-41`）**完全無 try/except**——任何 `urllib.error.URLError`（連線失敗）、`json.JSONDecodeError`（回應非 JSON）、`KeyError`（缺 choices）、`IndexError`（空陣列）**直接向上傳遞**，此測試未捕獲。
- **靜默失敗風險**：**YES**。assertion 只在 happy path 有意義；若 grok proxy 回應格式異常，測試以例外中止而非 assertion failure，無法區分「proxy 掛了」vs「模型答錯」。

### 2. `test_e2e_acceptance_real`（`test_e2e_acceptance.py:244`）

```python
def test_e2e_acceptance_real():
    # ... setup ...
    for _ in range(5):
        if _has_a(doc): break
        doc = run_pipeline(...)
    _assert_immutable_original(doc, note_text)
    _assert_no_source_gate(doc)
    _assert_law_citations_ok(doc, law)
    _assert_markdown_contract(doc)
    _assert_supplement_quality(doc)
    # 網路類斷言...
```

- **錯誤注入斷言**：❌ 無。全 happy path 驗證。
- **錯誤碼斷言**：❌ 無。
- **重試斷言**：✅ **有**。`test_e2e_acceptance.py:275-278` 對 Level A 來源的 flakiness 提供**最多 5 次重試**，但這是應用層 retry（為通過 quality check），非 LLM/Twinkle 的 transport retry。
- **Fallback 斷言**：⚠️ 有條件跳過。`pytest.skip` 在 grok 未上線或無 TWINKLE_HUB_TOKEN 時跳過（`:251-255`），但這是 skip 非斷言式 fallback。
- **例外傳遞斷言**：⚠️ 隱含——`GrokClient`、`TwinkleClient`、`LawLookup` 的例外皆未被捕獲。
- **靜默失敗風險**：**MODERATE**。重試迴圈降低了 Level A 路由的 flakiness；多層結構斷言（`_assert_*`）提供較高覆蓋。但若所有 run_pipeline 呼叫都因 Grok 異常而炸掉，測試以例外中止而非明確 assertion failure。

### 3. `test_detect_gaps_real_grok`（`test_gap.py:73`）

```python
def test_detect_gaps_real_grok():
    llm = GrokClient()
    gaps = detect_gaps(questions, note, llm)
    assert isinstance(gaps, list)
    assert all(isinstance(g, Gap) for g in gaps)
    assert all(g.status in ("partial", "missing") for g in gaps)
    assert any("裁量基準" in g.question or "罰鍰" in g.question for g in gaps)
```

- **錯誤注入斷言**：❌ 無。
- **錯誤碼斷言**：❌ 無。
- **重試斷言**：❌ 無。
- **Fallback 斷言**：❌ 無。`detect_gaps` 內部對 JSON 解析失敗有 fallback（全標 missing），但此測試不觸發。
- **例外傳遞斷言**：⚠️ 隱含——GrokClient 例外直接傳遞。
- **靜默失敗風險**：**YES**。assertions 只檢查結構與存在性。若 Grok 回傳含 `"covered"` status 的 gap list，測試只驗證 `partial/missing` 會失敗，但無法區分「模型理解錯誤」與「根本沒偵測到缺口」。

### 4. `test_grok_pong_integration`（`test_llm.py:68`）

```python
def test_grok_pong_integration():
    client = GrokClient()
    out = client.complete([{"role": "user", "content": "Reply with exactly one word: PONG"}])
    assert "PONG" in out.upper()
```

- **錯誤注入斷言**：❌ 無。
- **錯誤碼斷言**：❌ 無。
- **重試斷言**：❌ 無。
- **Fallback 斷言**：❌ 無。
- **例外傳遞斷言**：⚠️ 隱含——GrokClient 例外直接傳遞。
- **靜默失敗風險**：**YES**。本質上是連通性驗證（smoke test），不具語義覆蓋。若 grok 回應不含 PONG（但格式正確），assertion 會明確失敗——但不代表 pipeline 正確。

### 5. `test_run_pipeline_real_grok`（`test_pipeline.py:153`）

```python
def test_run_pipeline_real_grok(note_path):
    llm = GrokClient()
    twinkle = FakeTwinkle([[], [], [], []])
    doc = run_pipeline(note_path, llm, twinkle, FakeLaw())
    assert doc.original is not None
    assert isinstance(doc.segments, list)
    for seg in doc.segments:
        if seg.type == "supplement" and not seg.sources:
            assert seg.confidence == "pending_evidence"
```

- **錯誤注入斷言**：❌ 無。
- **錯誤碼斷言**：❌ 無。
- **重試斷言**：❌ 無。
- **Fallback 斷言**：❌ 無（但 pipeline 內部有 malformed gap fallback，未被此測試斷言）。
- **例外傳遞斷言**：⚠️ 隱含——GrokClient 例外直接傳遞。
- **靜默失敗風險**：**YES**。FakeTwinkle 全部回空，所以所有 supplement 皆為 pending_evidence。C6 不變式在無 supplement 時 **vacuous pass**（`for` loop 遍歷空 list 時完全不執行 assertion body）。若 Grok 回傳導致 pipeline 不產生任何 supplement 段，此測試依然通過（假設 `doc.segments` 仍為 list）。這是典型的 vacuous truth 靜默失敗模式。

### 6. `test_generate_questions_real_grok`（`test_questions.py:64`）

```python
def test_generate_questions_real_grok():
    llm = GrokClient()
    result = generate_questions(note, "law", llm)
    assert isinstance(result, list)
    assert len(result) >= 1
    assert all(isinstance(q, str) and q.strip() for q in result)
    assert not any(q.strip().startswith(("[", "{")) for q in result)
```

- **錯誤注入斷言**：❌ 無。
- **錯誤碼斷言**：❌ 無。
- **重試斷言**：❌ 無。
- **Fallback 斷言**：❌ 無。
- **例外傳遞斷言**：⚠️ 隱含——GrokClient 例外直接傳遞。
- **靜默失敗風險**：**MODERATE**。檢查了結構、非空、無 JSON 殘留——比單純 smoke 強，但仍不驗證問題與筆記內容的語義相關性。任何符合格式的字串清單（即使不相關）都能 PASS。

### 7. `test_retrieve_for_gap_real_twinkle_smoke`（`test_retrieve.py:105`）

```python
def test_retrieve_for_gap_real_twinkle_smoke():
    gap = Gap(question="行政處分附款的容許界限為何?", status="missing", reason="")
    twinkle = TwinkleClient(token=token)
    law = LawLookup(str(LAW_DB))
    llm = GrokClient()
    out = retrieve_for_gap(gap, "law", twinkle, law, llm)
    assert all(isinstance(s, Source) for s in out)
    assert all(s.level in ("A", "B") for s in out)
    keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
    assert keys == sorted(keys)
```

- **錯誤注入斷言**：❌ 無。
- **錯誤碼斷言**：❌ 無。
- **重試斷言**：❌ 無。
- **Fallback 斷言**：❌ 無。
- **例外傳遞斷言**：⚠️ 隱含——GrokClient/TwinkleClient 例外直接傳遞。
- **靜默失敗風險**：**MODERATE**。排序不變式檢查（`keys == sorted(keys)`）是強 assertion。但若 Twinkle 回空（無結果）、或 Grok 關鍵詞抽取失敗導致法條查詢為空，test 將僅以 assertion failure 終止，不會有深度診斷資訊。

### 8. `test_search_real_twinkle_hub`（`test_twinkle.py:142`）

```python
def test_search_real_twinkle_hub():
    results = TwinkleClient(token=token).search("道路交通管理處罰條例", n=3)
    assert isinstance(results, list)
    for src in results:
        assert isinstance(src, Source)
        assert src.level in ("A", "B")
        assert src.content.strip()
        assert src.fetched_date == date.today().isoformat()
```

- **錯誤注入斷言**：❌ 無。
- **錯誤碼斷言**：❌ 無。
- **重試斷言**：❌ 無。
- **Fallback 斷言**：❌ 無。
- **例外傳遞斷言**：⚠️ 隱含——`TwinkleClient.search`（`twinkle.py`）在 transport 失敗時有內部 fallback（回傳空 list），但此測試不驗證該 fallback 是否觸發。
- **靜默失敗風險**：**MODERATE**。若 Twinkle hub 回傳合法 Source 物件但內容/日期異常，assertions 可發現。但若 Twinkle 回空 list，`isinstance(results, list)` 通過而 `for src in results` 不做任何檢查——又是一個 vacuous pass。

---

## 跨節點模式總結

| 維度 | 統計 | 說明 |
|------|------|------|
| 錯誤注入斷言 | 0/8（0%） | 無任何測試模擬 API 錯誤、timeout、或異常 payload |
| 錯誤碼斷言 | 0/8（0%） | 無任何測試驗證 HTTP status code 或 API error code 的處理 |
| 重試斷言 | 1/8（12.5%） | 僅 `test_e2e_acceptance_real` 有應用層重試（Level A flakiness） |
| Fallback 斷言 | 0/8（0%） | 無測試直接斷言 fallback 路徑是否觸發 |
| 例外傳遞斷言 | 0/8（0%） | 所有測試依賴 GrokClient/TwinkleClient 將例外**直接向上傳遞**，無 try/except 包裝 |
| 靜默失敗風險 | 8/8（100%） | 所有 8 個測試皆存在至少一種 vacuous pass 或例外傳遞的靜默失敗模式 |

### 高風險節點（直接標記 YES，非 MODERATE）

- **#1** `test_detect_domain_real_grok_returns_law`：唯一 assertion 不驗證任何錯誤路徑
- **#3** `test_detect_gaps_real_grok`：結構檢查不驗證 gap 偵測正確性
- **#4** `test_grok_pong_integration`：純連通性測試，無語義
- **#5** `test_run_pipeline_real_grok`：FakeTwinkle 空回 + C6 vacuous pass 風險

### GrokClient 原始碼風險（`llm.py:27-41`）

```python
def complete(self, messages, **kw):
    body = {"model": self.model, "messages": messages, **kw}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{self.base_url}/chat/completions", ...)
    with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # ← 無 try/except
        payload = json.loads(resp.read().decode("utf-8"))            # ← 無 try/except
    return payload["choices"][0]["message"]["content"]               # ← 無 try/except
```

三處可能拋例外處全部裸奔(no try/except)，這解釋了為何所有 8 個整合測試的「例外傳遞斷言」欄位皆為 ⚠️ 隱含——因為應用層**從不捕獲**，測試層也**不驗證**。

---

## 建議

1. **補 vacuous pass 防呆**：對可能回空的結果（`test_run_pipeline_real_grok` 的 segments、`test_search_real_twinkle_hub` 的 results），補 `len(result) >= 1` 或「非空」斷言。
2. **GrokClient 補例外包裹**：在 `llm.py` 對三者（urlopen、json.loads、索引存取）至少加 `try/except → raise GrokError`，讓測試層可針對 `GrokError` 寫 exception-propagation 斷言。
3. **至少一個錯誤注入測試**：針對 `detect_domain` / `detect_gaps` / `generate_questions` 任一函式，用 `monkeypatch` ＋ 異常 urlopen 模擬 transport 失敗，驗證該函式的錯誤處理行為（而非僅隱含例外傳遞）。
