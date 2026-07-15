# 筆記補齊(Note-Filler)MVP 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:subagent-driven-development(建議)或 superpowers:executing-plans 逐 task 實作。步驟用 checkbox(- [ ])追蹤。

**Goal:** 輸入一份法律/行政/國考筆記,AI 自主找知識缺口、檢索台灣官方一手源、交叉驗證,產出「原文保留+標記補充+一手來源註腳」的訂正稿。

**Architecture:** 獨立 Python 專案,選擇性移植公文ai agent 的 twinkle client / 離線法規查核 / citation_formatter;自建 gap 偵測與訂正稿組裝兩塊。一條 pipeline 串接 parse→domain→questions→gap→retrieve→cross-validate→assemble→export,薄 FastAPI UI 呈現雙欄。

**Tech Stack:** Python 3.11+、grok(OpenAI 相容 :8318)、python-docx、stdlib urllib、pytest、FastAPI+Jinja2、SQLite(law_index.db)。

## Global Constraints

- Python 3.11+;專案名 note_filler;src layout(src/note_filler/...)。
- 研究層 LLM:grok,OpenAI 相容端點 http://127.0.0.1:8318/v1,model "grok-4.3",api_key 任意字串。已實測可用(回 PONG)。
- 可測性鐵律:所有會呼叫 LLM 的函式都必須把 llm: LLMClient 當參數注入(Protocol);單元測試傳 FakeLLM(canned responses),不打真網路;每個 LLM 模組另附一條真 grok 整合測試,標 @pytest.mark.integration。
- 原稿不可變:原筆記文字全程 immutable,絕不改動一字;補充一律 overlay(新增 segment)。
- 無來源閘(硬):sources 為空的補充不得進正文,confidence 標 "pending_evidence"(仍記錄但標記,不刪)。
- 來源分級只有 A/B(對齊既有程式碼實況):A=法規原文/官方一手;B=twinkle 立法院議案等。SourceLevel 型別保留 A/B/C/D 枚舉但 MVP 只產 A/B。
- 交叉驗證:一個 claim 要 >=2 個獨立 A/B 來源才算 verified;獨立 = 不同 url 且不同來源機關/文件。不足 2 → pending_evidence。
- 每個 Source 記 fetched_date(ISO 字串)+ doc_date(可 None)。
- commit 頻繁,conventional commit,訊息用繁體中文。
- MVP 領域只做 law/admin/exam;開放網路研究延後(第二階段接搜尋 backend)。
- 相依最小化:HTTP 用 stdlib urllib;.docx 解析用 python-docx;測試 pytest;薄 UI 用 fastapi + jinja2。

---

## 正本模組落點表

所有 task 的 import 與檔案路徑以此表為唯一正本。

| 符號 | import 模組 | 檔案路徑 |
|---|---|---|
| LLMClient, GrokClient, FakeLLM | note_filler.llm | src/note_filler/llm.py |
| Paragraph, Document, parse_note | note_filler.parse | src/note_filler/parse.py |
| Domain, detect_domain | note_filler.domain | src/note_filler/domain.py |
| generate_questions | note_filler.questions | src/note_filler/questions.py |
| Gap, detect_gaps | note_filler.gap | src/note_filler/gap.py |
| Source, SourceLevel | note_filler.retrieve.models | src/note_filler/retrieve/models.py |
| TwinkleClient | note_filler.retrieve.twinkle | src/note_filler/retrieve/twinkle.py |
| retrieve_for_gap | note_filler.retrieve | src/note_filler/retrieve/__init__.py |
| LawLookup | note_filler.knowledge.law_lookup | src/note_filler/knowledge/law_lookup.py |
| check_law_citations | note_filler.knowledge.law_citation_check | src/note_filler/knowledge/law_citation_check.py |
| Validation, cross_validate | note_filler.verify | src/note_filler/verify.py |
| build_reference_lines | note_filler.citation_formatter | src/note_filler/citation_formatter.py |
| Segment, CorrectionDoc, assemble_correction | note_filler.correction | src/note_filler/correction.py |
| run_pipeline | note_filler.pipeline | src/note_filler/pipeline.py |
| to_json, to_markdown | note_filler.export | src/note_filler/export.py |

---

### Task 1: 專案骨架 + grok LLM client(llm.py)

**Files:**
- Create: `pyproject.toml`
- Create: `src/note_filler/__init__.py`
- Create: `src/note_filler/llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: 無(全流程起點,不依賴任何早前 task)。
- Produces:
  - `LLMClient`(Protocol):`def complete(self, messages: list[dict], **kw) -> str`
  - `GrokClient(base_url="http://127.0.0.1:8318/v1", model="grok-4.3", api_key="x", timeout=60)`,實作 `LLMClient`
  - `FakeLLM(responses: list[str])`,實作 `LLMClient`,`complete` 依序 `pop(0)` 回傳 canned

---

- [ ] **Step 1: 建立 package 骨架(src layout)**

先把兩個空/最小檔案放好,讓 `note_filler` 能被 import。

`src/note_filler/__init__.py`:

```python
"""note_filler:法律/行政/考試筆記補齊工具(MVP)。"""

__version__ = "0.1.0"
```

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "note_filler"
version = "0.1.0"
description = "法律/行政/考試筆記自動補齊(研究層用 grok,原稿不可變,無來源不進正文)"
requires-python = ">=3.11"
dependencies = [
    "python-docx>=1.1.0",
    "fastapi>=0.110.0",
    "jinja2>=3.1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: 需要真實 grok(:8318)的整合測試;平時用 -m 'not integration' 跳過",
]
```

- [ ] **Step 2: Write the failing test — tests/test_llm.py**

三個測試:FakeLLM 依序回傳、GrokClient 用 monkeypatch 假 `urlopen` 驗 body/header 組對、整合測試真打 grok。

```python
import json
import urllib.request

import pytest

from note_filler.llm import FakeLLM, GrokClient


def test_fakellm_returns_canned_in_order():
    llm = FakeLLM(["first", "second"])
    assert llm.complete([{"role": "user", "content": "a"}]) == "first"
    assert llm.complete([{"role": "user", "content": "b"}]) == "second"


def test_grokclient_builds_request_body(monkeypatch):
    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "OK"}}]}
            ).encode("utf-8")

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["auth"] = req.get_header("Authorization")
        captured["content_type"] = req.get_header("Content-type")
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    client = GrokClient(api_key="secret", model="grok-4.3", timeout=42)
    out = client.complete([{"role": "user", "content": "hi"}], temperature=0.0)

    assert out == "OK"
    assert captured["url"] == "http://127.0.0.1:8318/v1/chat/completions"
    assert captured["method"] == "POST"
    assert captured["auth"] == "Bearer secret"
    assert captured["content_type"] == "application/json"
    assert captured["body"] == {
        "model": "grok-4.3",
        "messages": [{"role": "user", "content": "hi"}],
        "temperature": 0.0,
    }
    assert captured["timeout"] == 42


@pytest.mark.integration
def test_grok_pong_integration():
    client = GrokClient()
    out = client.complete(
        [{"role": "user", "content": "Reply with exactly one word: PONG"}]
    )
    assert "PONG" in out.upper()
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
cd D:/Users/Administrator/Desktop/筆記補齊
pip install -e ".[dev]"
python -m pytest tests/test_llm.py -m "not integration" -v
```

Expected: **FAIL** — `ModuleNotFoundError: No module named 'note_filler.llm'`(或 `ImportError: cannot import name 'FakeLLM'`),因為 `src/note_filler/llm.py` 尚未建立。

- [ ] **Step 4: Write minimal implementation — src/note_filler/llm.py**

`GrokClient.complete` 用 stdlib `urllib.request` POST 到 `{base_url}/chat/completions`,body 為 `{model, messages, **kw}`,header 帶 `Authorization: Bearer {api_key}` 與 `Content-Type: application/json`,解析 `choices[0].message.content`。`FakeLLM` 依序 `pop(0)`。

```python
from __future__ import annotations

import json
import urllib.request
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, messages: list[dict], **kw) -> str: ...


class GrokClient:
    """研究層 LLM:xAI grok,OpenAI 相容端點(本機 proxy :8318)。純 stdlib。"""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8318/v1",
        model: str = "grok-4.3",
        api_key: str = "x",
        timeout: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, messages: list[dict], **kw) -> str:
        body = {"model": self.model, "messages": messages, **kw}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]


class FakeLLM:
    """測試用:建構時給定 canned responses,每次 complete 依序 pop(0) 回傳。"""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], **kw) -> str:
        self.calls.append(messages)
        return self.responses.pop(0)
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
cd D:/Users/Administrator/Desktop/筆記補齊
python -m pytest tests/test_llm.py -m "not integration" -v
```

Expected: **PASS** — `test_fakellm_returns_canned_in_order` 與 `test_grokclient_builds_request_body` 均綠;`test_grok_pong_integration` 因 `-m "not integration"` 被 deselect(不打真網路)。

- [ ] **Step 6: (可選)驗整合測試真打 grok**

Run:
```bash
cd D:/Users/Administrator/Desktop/筆記補齊
python -m pytest tests/test_llm.py::test_grok_pong_integration -m integration -v
```

Expected: **PASS** — 真打 `:8318` 的 grok-4.3,回傳含 `PONG`(已實測端點可用)。若 :8318 未起,先執行 `hermes.exe proxy start --provider xai --port 8318` 再重跑;此步非 CI 必跑,失敗不阻塞單元測試綠燈。

- [ ] **Step 7: Commit**

```bash
cd D:/Users/Administrator/Desktop/筆記補齊
git add pyproject.toml src/note_filler/__init__.py src/note_filler/llm.py tests/test_llm.py
git commit -m "feat(llm): 建立 note_filler 專案骨架與 grok LLM client

- src layout + pyproject(deps: python-docx/fastapi/jinja2/pytest)
- LLMClient Protocol / GrokClient(stdlib urllib) / FakeLLM
- 單元測試以 FakeLLM 與 monkeypatch 假 urlopen 驗證,不打真網路
- 另附 @pytest.mark.integration 真 grok PONG 測試(可跳過)"
```

---

### Task 2: 筆記解析(parse.py)

**Files:**
- Create `src/note_filler/parse.py`
- Test `tests/test_parse.py`
- Create `tests/fixtures/sample.txt`

**Interfaces:**

Consumes：無（本 task 為 pipeline 最上游，不依賴任何其他 task 產物）。

Produces（本 task 定義的鎖定型別，後續 T13 `run_pipeline`、T12 `assemble_correction`、T14 `to_markdown` 消費）：
```python
@dataclass(frozen=True)
class Paragraph:
    idx: int
    text: str

@dataclass(frozen=True)
class Document:
    source_path: str
    paragraphs: tuple          # tuple[Paragraph, ...]，frozen 不可變
    full_text: str

def parse_note(path: str) -> Document: ...
```
- `.txt`：UTF-8 讀入，空行（一或多空白行）分段。
- `.docx`：python-docx 讀每個「非空」paragraph。
- `paragraphs` 為 frozen tuple、`idx` 從 0 起、`full_text` 以 `"\n"` join 各段。
- 原文 immutable：只做「段落邊界切分」，不改寫段內文字內容（不做同義替換／錯字修正／全形半形轉換）。

備註：本 task 無 LLM 呼叫，故不需 FakeLLM / grok 整合測試；改以「真 .docx round-trip 測試」落實 spec「Word 輸入」硬需求（★必修項）。

---

TDD steps：

- [ ] **Step 1（先寫 .txt 測試 + fixture，預期 FAIL）**

  建立 `tests/fixtures/sample.txt`（3 段、以空行分段；第 2 段刻意含連續空行測試多空白行切分）：
  ```text
  行政程序法第 92 條規定行政處分之定義，係指行政機關就公法上具體事件所為之決定。

  訴願法第 14 條：訴願之提起，應自行政處分達到之次日起三十日內為之。


  本筆記整理自上課講義，部分條號待查證。
  ```

  建立 `tests/test_parse.py`：
  ```python
  from pathlib import Path

  import pytest

  from note_filler.parse import Document, Paragraph, parse_note

  FIXTURE = Path(__file__).parent / "fixtures" / "sample.txt"


  def test_parse_txt_splits_on_blank_lines():
      doc = parse_note(str(FIXTURE))
      assert isinstance(doc, Document)
      assert doc.source_path == str(FIXTURE)
      # 三段：中間的連續空行不應產生空段
      assert len(doc.paragraphs) == 3
      assert isinstance(doc.paragraphs, tuple)
      assert [p.idx for p in doc.paragraphs] == [0, 1, 2]
      assert doc.paragraphs[0].text.startswith("行政程序法第 92 條")
      assert doc.paragraphs[1].text.startswith("訴願法第 14 條")
      assert doc.paragraphs[2].text.startswith("本筆記整理自上課講義")
      # full_text = 各段以換行 join
      assert doc.full_text == "\n".join(p.text for p in doc.paragraphs)


  def test_paragraph_and_document_are_frozen():
      p = Paragraph(idx=0, text="x")
      with pytest.raises(Exception):
          p.text = "y"  # frozen dataclass 不可指派
      doc = parse_note(str(FIXTURE))
      with pytest.raises(Exception):
          doc.full_text = "tampered"  # 原文 immutable
  ```

  Run：
  ```bash
  pytest tests/test_parse.py -v
  ```
  Expected（FAIL）：`ModuleNotFoundError: No module named 'note_filler.parse'`（尚未建立實作模組）。

- [ ] **Step 2（實作 parse.py 的型別與 .txt 分派，預期 .txt 測試 PASS）**

  建立 `src/note_filler/parse.py`：
  ```python
  from __future__ import annotations

  import re
  from dataclasses import dataclass
  from pathlib import Path


  @dataclass(frozen=True)
  class Paragraph:
      idx: int
      text: str


  @dataclass(frozen=True)
  class Document:
      source_path: str
      paragraphs: tuple  # tuple[Paragraph, ...]
      full_text: str


  # 空行分段：切在「一或多個只含空白的行」上；段內文字不改寫，僅去除段落
  # 首尾空白以確定邊界（原文內容 immutable，不做替換/正規化）。
  _BLANK_SEP = re.compile(r"(?:\r?\n)[ \t]*(?:\r?\n)+")


  def _split_txt(content: str) -> list[str]:
      blocks = _BLANK_SEP.split(content)
      return [b.strip() for b in blocks if b.strip()]


  def _read_docx(path: str) -> list[str]:
      # 延遲 import，讓 .txt 路徑不需安裝 python-docx
      from docx import Document as DocxDocument

      docx = DocxDocument(path)
      return [p.text for p in docx.paragraphs if p.text.strip()]


  def parse_note(path: str) -> Document:
      suffix = Path(path).suffix.lower()
      if suffix == ".txt":
          content = Path(path).read_text(encoding="utf-8")
          texts = _split_txt(content)
      elif suffix == ".docx":
          texts = _read_docx(path)
      else:
          raise ValueError(f"不支援的筆記副檔名：{suffix!r}（僅支援 .txt / .docx）")

      paragraphs = tuple(
          Paragraph(idx=i, text=t) for i, t in enumerate(texts)
      )
      full_text = "\n".join(p.text for p in paragraphs)
      return Document(source_path=path, paragraphs=paragraphs, full_text=full_text)
  ```

  Run：
  ```bash
  pytest tests/test_parse.py -v
  ```
  Expected（PASS）：`test_parse_txt_splits_on_blank_lines` 與 `test_paragraph_and_document_are_frozen` 兩項通過（`.docx` 尚未測）。

- [ ] **Step 3（★必修：加入「真 .docx round-trip」測試，預期 FAIL 直到驗證通過）**

  在 `tests/test_parse.py` 末端追加：
  ```python
  def test_parse_docx_roundtrip(tmp_path):
      # 用 python-docx 真的產生一份多段 .docx，再 parse_note 讀回，
      # 明確落實 spec「Word 輸入」需求。
      from docx import Document as DocxDocument

      paras = [
          "行政程序法第 92 條規定行政處分之定義。",
          "訴願法第 14 條：訴願應自處分達到次日起三十日內提起。",
          "第三段：交叉驗證需 >= 2 個獨立 A/B 來源。",
      ]
      src = DocxDocument()
      for t in paras:
          src.add_paragraph(t)
      src.add_paragraph("")     # 空段
      src.add_paragraph("   ")  # 只含空白 → 皆應被略過
      out = tmp_path / "note.docx"
      src.save(str(out))

      doc = parse_note(str(out))
      assert len(doc.paragraphs) == 3                     # 空段被過濾
      assert [p.text for p in doc.paragraphs] == paras     # 文字逐段正確且未改寫
      assert [p.idx for p in doc.paragraphs] == [0, 1, 2]  # idx 從 0 連續
      assert doc.full_text == "\n".join(paras)             # full_text 換行 join
  ```

  Run（先確認相依已裝：`pip install python-docx`）：
  ```bash
  pytest tests/test_parse.py::test_parse_docx_roundtrip -v
  ```
  Expected（FAIL）：若尚未安裝 `python-docx`，`_read_docx` 內 `from docx import ...` 觸發 `ModuleNotFoundError: No module named 'docx'`（即紅燈，證明 .docx 路徑尚未可用）。

- [ ] **Step 4（安裝相依，讓 .docx round-trip 綠燈；全測試 PASS）**

  將 `python-docx` 加入 `pyproject.toml` 相依（相依最小化：HTTP 用 stdlib、.docx 才引入 python-docx）：
  ```toml
  [project]
  dependencies = [
      "python-docx>=1.1.0",
  ]
  ```
  安裝並回跑全部：
  ```bash
  pip install -e .
  pytest tests/test_parse.py -v
  ```
  Expected（PASS）：三個測試全綠——
  ```
  tests/test_parse.py::test_parse_txt_splits_on_blank_lines PASSED
  tests/test_parse.py::test_paragraph_and_document_are_frozen PASSED
  tests/test_parse.py::test_parse_docx_roundtrip PASSED
  ```
  （`_read_docx` 程式碼於 Step 2 已寫好，Step 4 僅補齊執行期相依即轉綠，無需再改 `parse.py`。）

- [ ] **Step 5（Commit，conventional 繁中）**
  ```bash
  git add src/note_filler/parse.py tests/test_parse.py tests/fixtures/sample.txt pyproject.toml
  git commit -m "feat(parse): 實作筆記解析 parse_note 支援 .txt 空行分段與 .docx 段落讀取

  - 新增 frozen Paragraph/Document 型別，paragraphs 為 tuple、idx 從 0、full_text 換行 join
  - .txt 以空行分段；.docx 以 python-docx 讀非空段落，原文不清洗維持 immutable
  - 加入真 .docx round-trip 測試落實 Word 輸入需求"
  ```

---

### Task 3: 領域偵測(domain.py)

**Files:**
- Create: `src/note_filler/domain.py`
- Test: `tests/test_domain.py`

**Interfaces:**
- Consumes (T1, 照抄簽名):
  ```python
  # src/note_filler/llm.py
  class LLMClient(Protocol):
      def complete(self, messages: list[dict], **kw) -> str: ...
  class GrokClient:  # 實作 LLMClient, base_url="http://127.0.0.1:8318/v1", model="grok-4.3"
      def complete(self, messages: list[dict], **kw) -> str: ...
  class FakeLLM:
      def __init__(self, responses: list[str]): ...
      def complete(self, messages: list[dict], **kw) -> str: ...  # 依序 pop canned
  ```
- Produces (本 task 對外簽名):
  ```python
  # src/note_filler/domain.py
  from typing import Literal
  Domain = Literal["law", "admin", "exam", "other"]
  def detect_domain(text: str, llm: LLMClient) -> Domain: ...
  ```

---

- [ ] **Step 1: Write the failing unit tests(FakeLLM,不打網路)**

  ```python
  # tests/test_domain.py
  import pytest

  from note_filler.domain import detect_domain
  from note_filler.llm import FakeLLM


  def test_detect_domain_law():
      llm = FakeLLM(["law"])
      assert detect_domain("行政程序法第92條所稱行政處分,係指行政機關就公法上具體事件所為之決定。", llm) == "law"


  def test_detect_domain_admin():
      llm = FakeLLM(["admin"])
      assert detect_domain("本府各單位公文簽核流程、用印規定與檔案歸檔作業要點。", llm) == "admin"


  def test_detect_domain_exam():
      llm = FakeLLM(["exam"])
      assert detect_domain("高普考行政法申論題作答架構與歷屆考古題重點整理。", llm) == "exam"


  def test_detect_domain_noise_falls_back_to_other():
      # LLM 回不可辨識的雜訊 → 必須 fallback 到 "other"
      llm = FakeLLM(["嗯...我不太確定這是什麼耶🤔"])
      assert detect_domain("今天天氣不錯,午餐吃了牛肉麵。", llm) == "other"


  def test_detect_domain_label_with_trailing_punctuation():
      # LLM 回帶標點/雜訊但含合法標籤 → 仍須抽出正確 Domain
      llm = FakeLLM(["law."])
      assert detect_domain("民法第184條規定侵權行為之損害賠償責任。", llm) == "law"


  def test_detect_domain_uppercase_and_whitespace():
      # 大小寫與前後空白皆須容忍
      llm = FakeLLM(["  ADMIN  "])
      assert detect_domain("機關內部差勤與請假作業規範。", llm) == "admin"
  ```

- [ ] **Step 2: Run tests to verify they fail**

  Run:
  ```bash
  pytest tests/test_domain.py -v
  ```
  Expected: FAIL —— `ModuleNotFoundError: No module named 'note_filler.domain'`(domain.py 尚未建立,`detect_domain` 無法 import)。

- [ ] **Step 3: Write minimal implementation**

  ```python
  # src/note_filler/domain.py
  from typing import Literal

  from note_filler.llm import LLMClient

  Domain = Literal["law", "admin", "exam", "other"]

  # 順序即抽取優先序:law > admin > exam > other
  _VALID: tuple[Domain, ...] = ("law", "admin", "exam", "other")

  _SYSTEM_PROMPT = (
      "你是文件領域分類器。閱讀使用者提供的筆記文字,"
      "只回一個標籤,不要任何解釋、標點、引號或多餘文字。\n"
      "可選標籤(四選一):\n"
      "law   = 法律、法規、法條、判決、釋字相關\n"
      "admin = 行政、公文、機關內部作業、簽核流程相關\n"
      "exam  = 考試、考古題、應試準備、申論作答相關\n"
      "other = 以上皆非\n"
      "只輸出 law、admin、exam、other 其中之一。"
  )


  def detect_domain(text: str, llm: LLMClient) -> Domain:
      messages = [
          {"role": "system", "content": _SYSTEM_PROMPT},
          {"role": "user", "content": text},
      ]
      raw = llm.complete(messages)
      token = raw.strip().lower()

      # 1) 乾淨回應直接命中
      if token in _VALID:
          return token  # type: ignore[return-value]

      # 2) 回應含雜訊/標點時,依優先序抽出第一個出現的合法標籤
      for label in _VALID:
          if label in token:
              return label

      # 3) 完全無法辨識 → 無來源閘精神:不硬猜,回 "other"
      return "other"
  ```

- [ ] **Step 4: Run tests to verify they pass**

  Run:
  ```bash
  pytest tests/test_domain.py -v
  ```
  Expected: PASS —— 6 個單元測試全綠(`test_detect_domain_law`、`_admin`、`_exam`、`_noise_falls_back_to_other`、`_label_with_trailing_punctuation`、`_uppercase_and_whitespace`)。

- [ ] **Step 5: Add one real-grok integration test(標記 integration,可跳過)**

  ```python
  # 追加到 tests/test_domain.py 末尾
  @pytest.mark.integration
  def test_detect_domain_real_grok_returns_law():
      # 真打 grok(http://127.0.0.1:8318/v1, grok-4.3);明顯法律文字須回 law
      from note_filler.llm import GrokClient

      llm = GrokClient()
      text = (
          "刑法第271條規定,殺人者處死刑、無期徒刑或十年以上有期徒刑;"
          "前項之未遂犯罰之。本條為普通殺人罪之構成要件與法定刑度。"
      )
      assert detect_domain(text, llm) == "law"
  ```

  Run(僅整合測試,需 grok proxy 在 8318):
  ```bash
  pytest tests/test_domain.py -v -m integration
  ```
  Expected: PASS —— 真 grok 對明顯刑法條文回 `law`。若 8318 未起(port 不通),此測試可用 `-m "not integration"` 跳過,不阻塞單元測試綠燈。

- [ ] **Step 6: Commit**

  ```bash
  git add src/note_filler/domain.py tests/test_domain.py
  git commit -m "feat(domain): 新增 detect_domain 領域偵測,FakeLLM 單元測試加一條真 grok 整合測試"
  ```

---

### Task 4: 研究問題生成(questions.py)

**Files:**
- Create `src/note_filler/questions.py`
- Test `tests/test_questions.py`

**Interfaces:**
- Consumes:
  - `class LLMClient(Protocol)` — `def complete(self, messages: list[dict], **kw) -> str` (T1)
  - `class FakeLLM` — `def __init__(self, responses: list[str])` / `complete` 依序 pop(T1,測試用)
  - `class GrokClient` — `def __init__(self, base_url="http://127.0.0.1:8318/v1", model="grok-4.3", api_key="x", timeout=60)`(T1,整合測試用)
  - `Domain = Literal["law","admin","exam","other"]`(T3)
- Produces:
  - `def generate_questions(full_text: str, domain: Domain, llm: LLMClient) -> list[str]`(T4)

**合約對齊(C1):** `generate_questions` 呼叫 `llm.complete`**恰一次**,prompt 明確要求「每行一題、不編號、不加前綴」;回應以 `splitlines()` + `strip()` 解析、去空行成 `list[str]`;**不解析 JSON**。

---

- [ ] **Step 1 (RED) — 先寫測試:多行字串必須被切成 list**

  ```python
  # tests/test_questions.py
  import pytest

  from note_filler.llm import FakeLLM
  from note_filler.questions import generate_questions


  def test_generate_questions_splits_multiline_string():
      canned = "本法的立法目的為何?\n適用範圍包含哪些對象?\n違反時的罰則規定為何?"
      llm = FakeLLM([canned])

      result = generate_questions("某段筆記內容", "law", llm)

      assert isinstance(result, list)
      assert all(isinstance(q, str) for q in result)
      assert result == [
          "本法的立法目的為何?",
          "適用範圍包含哪些對象?",
          "違反時的罰則規定為何?",
      ]
  ```

  **Run:**
  ```bash
  pytest tests/test_questions.py::test_generate_questions_splits_multiline_string -q
  ```
  **Expected (FAIL):** `ModuleNotFoundError: No module named 'note_filler.questions'`(模組尚未建立)。

- [ ] **Step 2 (GREEN) — 實作 generate_questions(單次呼叫 + splitlines 解析)**

  ```python
  # src/note_filler/questions.py
  """研究問題生成:依主題與領域,請 LLM 產出該主題應涵蓋的關鍵問題清單。"""
  from __future__ import annotations

  from note_filler.domain import Domain
  from note_filler.llm import LLMClient

  _DOMAIN_LABEL: dict[str, str] = {
      "law": "法律法規",
      "admin": "行政公文與行政法",
      "exam": "考試準備",
      "other": "一般主題",
  }


  def generate_questions(full_text: str, domain: Domain, llm: LLMClient) -> list[str]:
      """針對筆記主題,產生「該主題應涵蓋的關鍵研究問題」清單。

      合約(C1):呼叫 llm.complete 恰一次;要求「每行一題」;
      以 splitlines()+strip() 去空行解析成 list[str];不解析 JSON。
      """
      domain_label = _DOMAIN_LABEL.get(domain, "一般主題")
      prompt = (
          f"你是一位「{domain_label}」領域的研究助理。\n"
          "以下是一份筆記的完整內容。請針對這份筆記的主題,\n"
          "列出「該主題應該被涵蓋、但筆記可能缺漏的關鍵研究問題」。\n\n"
          "嚴格輸出格式:\n"
          "1. 每一行只寫一個問題。\n"
          "2. 不要編號、不要項目符號、不要任何前綴或縮排。\n"
          "3. 只輸出問題本身,不要開場白、標題或結語。\n"
          "4. 問題需具體且可查證,聚焦於法規/制度/事實層面的補充重點。\n\n"
          f"筆記內容:\n{full_text}"
      )
      messages = [{"role": "user", "content": prompt}]

      raw = llm.complete(messages)  # 恰一次呼叫

      lines = [line.strip() for line in raw.splitlines()]
      return [line for line in lines if line]
  ```

  **Run:**
  ```bash
  pytest tests/test_questions.py::test_generate_questions_splits_multiline_string -q
  ```
  **Expected (PASS):** `1 passed`。

- [ ] **Step 3 (RED) — 補測試:strip 去頭尾空白、丟棄空白行**

  ```python
  # tests/test_questions.py(續)
  def test_generate_questions_strips_and_drops_blank_lines():
      canned = "  第一題應涵蓋什麼?  \n\n   \n第二題的依據為何?\n"
      llm = FakeLLM([canned])

      result = generate_questions("內容", "admin", llm)

      assert result == ["第一題應涵蓋什麼?", "第二題的依據為何?"]


  def test_generate_questions_empty_response_returns_empty_list():
      llm = FakeLLM(["   \n\n  \n"])

      result = generate_questions("內容", "exam", llm)

      assert result == []
  ```

  **Run:**
  ```bash
  pytest tests/test_questions.py -k "strips_and_drops or empty_response" -q
  ```
  **Expected (PASS):** `2 passed`(Step 2 的 `strip()`+去空行邏輯已涵蓋,直接綠)。

- [ ] **Step 4 (RED) — 補測試:證明 llm.complete 恰被呼叫一次(非 per-question 多呼叫)**

  ```python
  # tests/test_questions.py(續)
  def test_generate_questions_calls_llm_exactly_once():
      # FakeLLM 依序 pop:只放一顆 canned。若函式呼叫超過一次,
      # 第二次 pop 會 IndexError;故「不炸」即證明恰一次呼叫。
      llm = FakeLLM(["唯一一題?"])

      result = generate_questions("內容", "law", llm)

      assert result == ["唯一一題?"]
      # 佇列已被唯一一次呼叫清空,再呼叫即 IndexError → 反證只呼叫過一次
      with pytest.raises(IndexError):
          llm.complete([{"role": "user", "content": "probe"}])
  ```

  **Run:**
  ```bash
  pytest tests/test_questions.py::test_generate_questions_calls_llm_exactly_once -q
  ```
  **Expected (PASS):** `1 passed`。

- [ ] **Step 5 (整合) — 真 grok 整合測試(標 @pytest.mark.integration,不隨單元測試跑)**

  ```python
  # tests/test_questions.py(續)
  @pytest.mark.integration
  def test_generate_questions_real_grok():
      from note_filler.llm import GrokClient

      llm = GrokClient()  # base_url=http://127.0.0.1:8318/v1, model="grok-4.3"
      note = (
          "個人資料保護法規範公務機關與非公務機關對個人資料之蒐集、處理及利用,"
          "並要求特定情形須告知當事人並取得同意。"
      )

      result = generate_questions(note, "law", llm)

      assert isinstance(result, list)
      assert len(result) >= 1
      assert all(isinstance(q, str) and q.strip() for q in result)
      # 合約:回傳為換行切割後的乾淨清單,不應殘留 JSON 括號等結構符號
      assert not any(q.strip().startswith(("[", "{")) for q in result)
  ```

  **Run:**
  ```bash
  pytest tests/test_questions.py -m integration -q
  ```
  **Expected (PASS):** `1 passed`(需本機 8318 proxy 可用;預設 `pytest`(未帶 `-m integration`)不會跑到此條)。

- [ ] **Step 6 — 全檔單元測試綠燈(排除整合)**

  **Run:**
  ```bash
  pytest tests/test_questions.py -m "not integration" -q
  ```
  **Expected (PASS):** `4 passed`(Step 1/3×2/4 共四條單元測試)。

- [ ] **Commit**

  ```bash
  git add src/note_filler/questions.py tests/test_questions.py
  git commit -m "feat(questions): 依領域生成研究問題清單,單次 LLM 呼叫換行解析(C1)"
  ```

---

### Task 5: 缺口偵測(gap.py,自建①)

**Files:**
- Create `src/note_filler/gap.py`
- Test `tests/test_gap.py`

**Interfaces:**
- Consumes(T1): `class LLMClient(Protocol): def complete(self, messages: list[dict], **kw) -> str: ...`;測試用 `FakeLLM(responses: list[str])`、整合測試用 `GrokClient`。
- Produces(T5):
  - `@dataclass\nclass Gap: question:str; status:Literal["covered","partial","missing"]; reason:str`
  - `def detect_gaps(questions: list[str], note_text: str, llm: LLMClient) -> list[Gap]: ...`

**硬合約對齊(C1):** `detect_gaps` 只呼叫 `llm.complete`「一次」,把「全部 questions 一起」丟給 LLM;prompt 要求回「JSON 陣列」每元素 `{question,status,reason}`;`json.loads` 後只保留 `status ∈ {partial, missing}`;JSON 解析失敗(非陣列/非法 JSON)時保守把「全部 questions」當 `missing`,reason 記解析失敗。禁止 per-question 多次呼叫。

---

- [ ] **Step 1｜寫失敗測試(RED):建立 `tests/test_gap.py`**

```python
import pytest

from note_filler.gap import Gap, detect_gaps
from note_filler.llm import FakeLLM


def test_detect_gaps_keeps_only_partial_and_missing():
    """LLM 回一個 JSON 陣列;covered 要被濾掉,只留 partial+missing。"""
    canned = """[
      {"question": "甲問題", "status": "covered", "reason": "已完整說明"},
      {"question": "乙問題", "status": "partial", "reason": "只提到一半"},
      {"question": "丙問題", "status": "missing", "reason": "完全沒提"}
    ]"""
    llm = FakeLLM([canned])
    gaps = detect_gaps(["甲問題", "乙問題", "丙問題"], "某段筆記文字", llm)
    assert [g.status for g in gaps] == ["partial", "missing"]
    assert [g.question for g in gaps] == ["乙問題", "丙問題"]
    assert all(isinstance(g, Gap) for g in gaps)
    assert all(g.reason for g in gaps)


def test_detect_gaps_calls_llm_exactly_once():
    """FakeLLM 只餵一個回應;若 detect_gaps 多次呼叫會把 responses pop 空 → IndexError。"""
    llm = FakeLLM(['[{"question":"q","status":"missing","reason":"r"}]'])
    gaps = detect_gaps(["q1", "q2", "q3"], "筆記", llm)
    assert len(gaps) == 1  # 一次呼叫、一個 JSON 陣列回應


def test_detect_gaps_parse_failure_marks_all_missing():
    """JSON 解析失敗 → 全部 questions 保守標 missing,reason 記解析失敗。"""
    llm = FakeLLM(["抱歉這不是 JSON"])
    qs = ["q1", "q2"]
    gaps = detect_gaps(qs, "筆記", llm)
    assert [g.status for g in gaps] == ["missing", "missing"]
    assert [g.question for g in gaps] == qs
    assert all("解析失敗" in g.reason for g in gaps)


def test_detect_gaps_non_array_json_also_fallbacks():
    """合法 JSON 但不是陣列(dict) → 同樣走保守 fallback。"""
    llm = FakeLLM(['{"status": "missing"}'])
    gaps = detect_gaps(["q1"], "筆記", llm)
    assert [g.status for g in gaps] == ["missing"]
    assert "解析失敗" in gaps[0].reason


def test_detect_gaps_strips_code_fence():
    """LLM 常包 ```json 圍欄,需能剝除後仍解析。"""
    canned = '```json\n[{"question":"q","status":"partial","reason":"半"}]\n```'
    llm = FakeLLM([canned])
    gaps = detect_gaps(["q"], "筆記", llm)
    assert len(gaps) == 1 and gaps[0].status == "partial"


def test_detect_gaps_empty_questions_short_circuits():
    """空問題清單直接回空,不呼叫 LLM。"""
    llm = FakeLLM([])  # 不應被 pop
    assert detect_gaps([], "筆記", llm) == []
```

Run:
```bash
python -m pytest tests/test_gap.py -q
```
Expected(FAIL):`ModuleNotFoundError: No module named 'note_filler.gap'`(gap.py 尚未建立)。

---

- [ ] **Step 2｜實作 `src/note_filler/gap.py`(GREEN)**

```python
"""缺口偵測:判定筆記是否涵蓋各問題,只回報 partial / missing 的缺口。

硬合約(C1):對「全部問題」一次性呼叫 llm.complete;要求回 JSON 陣列;
只保留 status ∈ {partial, missing};解析失敗則保守把全部問題當 missing。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from .llm import LLMClient


@dataclass
class Gap:
    question: str
    status: Literal["covered", "partial", "missing"]
    reason: str


_PROMPT_TEMPLATE = """你是筆記涵蓋度審查員。以下是一份筆記,以及一組問題。
請逐一判斷筆記是否已涵蓋每個問題,status 只能三選一:
- covered:筆記已完整回答此問題。
- partial:筆記有部分提及但不完整。
- missing:筆記完全沒有涉及。

只輸出 JSON 陣列,不要任何額外文字、說明或 markdown 圍欄。
每個元素格式:
{{"question": "<照抄原問題文字>", "status": "covered|partial|missing", "reason": "<簡短理由>"}}

=== 筆記全文 ===
{note_text}

=== 問題清單 ===
{questions_block}
"""


def _strip_fence(raw: str) -> str:
    """剝除 LLM 可能包上的 ```json ... ``` 圍欄,回傳純內容。"""
    s = raw.strip()
    if s.startswith("```"):
        # 去掉第一行圍欄(```或```json)
        s = s.split("\n", 1)[1] if "\n" in s else ""
        # 去掉結尾圍欄
        if s.rstrip().endswith("```"):
            s = s.rstrip()[: s.rstrip().rindex("```")]
    return s.strip()


def _all_missing(questions: list[str], reason: str) -> list[Gap]:
    return [Gap(question=q, status="missing", reason=reason) for q in questions]


def detect_gaps(questions: list[str], note_text: str, llm: LLMClient) -> list[Gap]:
    if not questions:
        return []

    questions_block = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    prompt = _PROMPT_TEMPLATE.format(note_text=note_text, questions_block=questions_block)

    # C1:對全部問題「一次」呼叫。
    raw = llm.complete([{"role": "user", "content": prompt}])

    try:
        data = json.loads(_strip_fence(raw))
        if not isinstance(data, list):
            raise ValueError("回應不是 JSON 陣列")
    except (json.JSONDecodeError, ValueError):
        # 保守 fallback:全部當 missing。
        return _all_missing(questions, reason="LLM 回應解析失敗,保守標為 missing")

    gaps: list[Gap] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        if status not in ("partial", "missing"):  # 只留缺口,covered 濾掉
            continue
        gaps.append(
            Gap(
                question=str(item.get("question", "")),
                status=status,
                reason=str(item.get("reason", "")),
            )
        )
    return gaps
```

Run:
```bash
python -m pytest tests/test_gap.py -q -m "not integration"
```
Expected(PASS):`6 passed`(6 條單元測試全綠;整合測試被 `-m "not integration"` 排除)。

---

- [ ] **Step 3｜真 grok 整合測試(標記 `@pytest.mark.integration`,附加到 `tests/test_gap.py` 尾端)**

```python
@pytest.mark.integration
def test_detect_gaps_real_grok():
    """真打 grok(http://127.0.0.1:8318/v1, grok-4.3):
    給一段只談行政處分定義的筆記 + 一題明顯未涵蓋的問題,
    驗回傳結構正確且所有 status 皆為缺口(partial/missing)。"""
    from note_filler.llm import GrokClient

    llm = GrokClient()  # base_url/model 用鎖定預設值
    note = "行政程序法第92條規定,行政處分係行政機關就公法上具體事件所為之對外直接發生法律效果之單方行政行為。"
    questions = [
        "行政處分的法定定義為何?",
        "行政罰鍰的裁量基準與上限為何?",  # 筆記完全沒提 → 應 missing
    ]
    gaps = detect_gaps(questions, note, llm)

    assert isinstance(gaps, list)
    assert all(isinstance(g, Gap) for g in gaps)
    assert all(g.status in ("partial", "missing") for g in gaps)  # 只回缺口
    # 第二題明顯未涵蓋,至少要出現在缺口清單
    assert any("裁量基準" in g.question or "罰鍰" in g.question for g in gaps)
```

Run:
```bash
python -m pytest tests/test_gap.py -q -m integration
```
Expected(PASS):`1 passed`(需 grok proxy 於 8318 在線;不在線則 port 不通,依環境事實手動拉起 Hermes 後重跑)。

---

- [ ] **Step 4｜全檔回歸驗證**

Run:
```bash
python -m pytest tests/test_gap.py -q
```
Expected(PASS):`7 passed`(6 單元 + 1 整合)。

---

- [ ] **Step 5｜Commit(conventional 繁中)**

```bash
git add src/note_filler/gap.py tests/test_gap.py
git commit -m "feat(gap): 新增缺口偵測 detect_gaps,一次性呼叫 LLM 只回 partial/missing 缺口

- Gap dataclass(question/status/reason);status 三態 covered/partial/missing
- detect_gaps 依 C1 對全部問題單次 llm.complete,要求回 JSON 陣列
- json.loads 後只留 partial/missing;解析失敗保守把全部問題標 missing
- 剝除 code fence;空問題清單短路不呼叫 LLM
- 單元測試用 FakeLLM 驗濾除與 fallback;另附 @pytest.mark.integration 真 grok 測試"
```

---

### Task 6: 來源模型 + 分級 + 新鮮度(retrieve/models.py, retrieve/grading.py)

**Files:**
- Create `src/note_filler/retrieve/__init__.py`(暫空,T9 補 `retrieve_for_gap()`)
- Create `src/note_filler/retrieve/models.py`
- Create `src/note_filler/retrieve/grading.py`
- Test `tests/test_grading.py`

**Interfaces:**
- Consumes: 無(純函式,不依賴任何早前 task 產出;不呼叫 LLM)
- Produces:
  - `SourceLevel = Literal["A","B","C","D"]`(models.py)
  - `@dataclass class Source`(欄位:`id:str, title:str, url:str|None, level:SourceLevel, content:str, fetched_date:str, doc_date:str|None, distance:float`)(models.py)
  - `def grade_law() -> SourceLevel`(回 `"A"`;law_lookup 命中的法規原文=一手)(grading.py)
  - `def grade_twinkle() -> SourceLevel`(回 `"B"`;twinkle 議案等二手)(grading.py)
  - `def is_stale(fetched_date: str, max_age_days: int) -> bool`(grading.py;`today - fetched_date > max_age_days` 才算 stale)

---

- [ ] **Step 1: 建立 retrieve package 目錄與空 `__init__.py`**

先讓 package 可被 import(內容留空,T9 才填 `retrieve_for_gap`)。

```python
# src/note_filler/retrieve/__init__.py
# retrieve package。retrieve_for_gap() 於 Task 9 補上,此處先留空以成立 package。
```

Run:
```
python -c "import note_filler.retrieve; print('ok')"
```
Expected: 印出 `ok`,無 ImportError。

---

- [ ] **Step 2: Write the failing test — Source dataclass 可用全欄位建構**

```python
# tests/test_grading.py
from dataclasses import fields
from note_filler.retrieve.models import Source


def test_source_dataclass_has_locked_fields():
    s = Source(
        id="law-民法-184",
        title="民法第184條",
        url=None,
        level="A",
        content="因故意或過失,不法侵害他人之權利者,負損害賠償責任。",
        fetched_date="2026-07-15",
        doc_date=None,
        distance=0.0,
    )
    assert s.id == "law-民法-184"
    assert s.level == "A"
    assert s.url is None
    assert s.doc_date is None
    assert s.fetched_date == "2026-07-15"
    assert s.distance == 0.0
    # 鎖定型別:欄位名稱與順序不得改
    names = [f.name for f in fields(Source)]
    assert names == [
        "id", "title", "url", "level", "content",
        "fetched_date", "doc_date", "distance",
    ]
```

Run:
```
pytest tests/test_grading.py::test_source_dataclass_has_locked_fields -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'note_filler.retrieve.models'`(models.py 尚未建立)。

---

- [ ] **Step 3: Write minimal implementation — models.py**

```python
# src/note_filler/retrieve/models.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SourceLevel = Literal["A", "B", "C", "D"]


@dataclass
class Source:
    id: str
    title: str
    url: str | None
    level: SourceLevel
    content: str
    fetched_date: str        # ISO date,例如 "2026-07-15"
    doc_date: str | None     # 文件本身日期,未知則 None
    distance: float
```

Run:
```
pytest tests/test_grading.py::test_source_dataclass_has_locked_fields -v
```
Expected: PASS。

---

- [ ] **Step 4: Write the failing test — grade_law / grade_twinkle 回正確等級**

```python
# tests/test_grading.py(append)
from note_filler.retrieve.grading import grade_law, grade_twinkle


def test_grade_law_returns_A():
    # law_lookup 命中的法規原文 = 官方一手 = A
    assert grade_law() == "A"


def test_grade_twinkle_returns_B():
    # twinkle 立法院議案等 = 二手 = B
    assert grade_twinkle() == "B"
```

Run:
```
pytest tests/test_grading.py::test_grade_law_returns_A tests/test_grading.py::test_grade_twinkle_returns_B -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'note_filler.retrieve.grading'`。

---

- [ ] **Step 5: Write minimal implementation — grading.py 的兩個分級函式**

對齊 MIGRATION 實況:分級為固定映射(law=A、twinkle=B),非查表。

```python
# src/note_filler/retrieve/grading.py
from __future__ import annotations

from datetime import date

from note_filler.retrieve.models import SourceLevel


def grade_law() -> SourceLevel:
    """law_lookup 命中的本地法規原文 = 官方一手 → A。"""
    return "A"


def grade_twinkle() -> SourceLevel:
    """twinkle(立法院議案等)= 二手 → B。"""
    return "B"
```

Run:
```
pytest tests/test_grading.py::test_grade_law_returns_A tests/test_grading.py::test_grade_twinkle_returns_B -v
```
Expected: PASS(兩項)。

---

- [ ] **Step 6: Write the failing test — is_stale 邊界(剛好 / 超過 / 未達)**

用相對今天的日期算出 fetched_date,邊界才可決定性驗證。判定規則:`(today - fetched).days > max_age_days` 才算 stale;剛好等於 max_age_days 不算過期。

```python
# tests/test_grading.py(append)
from datetime import date, timedelta

from note_filler.retrieve.grading import is_stale


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def test_is_stale_exactly_max_age_is_not_stale():
    # 剛好 max_age_days 天前抓的:未超過 → 不算 stale
    assert is_stale(_days_ago(30), max_age_days=30) is False


def test_is_stale_over_max_age_is_stale():
    # 超過一天:算 stale
    assert is_stale(_days_ago(31), max_age_days=30) is True


def test_is_stale_under_max_age_is_not_stale():
    # 未達門檻:不算 stale
    assert is_stale(_days_ago(29), max_age_days=30) is False


def test_is_stale_today_is_not_stale():
    # 今天剛抓:一定不 stale
    assert is_stale(date.today().isoformat(), max_age_days=0) is False
```

Run:
```
pytest tests/test_grading.py -k is_stale -v
```
Expected: FAIL — `ImportError: cannot import name 'is_stale' from 'note_filler.retrieve.grading'`(函式尚未實作)。

---

- [ ] **Step 7: Write minimal implementation — is_stale**

```python
# src/note_filler/retrieve/grading.py(append)
def is_stale(fetched_date: str, max_age_days: int) -> bool:
    """fetched_date(ISO)距今天數 > max_age_days 即視為過期。

    MVP 不追文件本身 doc_date,以抓取當下 fetched_date 為準。
    邊界:剛好等於 max_age_days 不算 stale(用嚴格大於)。
    """
    fetched = date.fromisoformat(fetched_date)
    age_days = (date.today() - fetched).days
    return age_days > max_age_days
```

Run:
```
pytest tests/test_grading.py -k is_stale -v
```
Expected: PASS(4 項)。

---

- [ ] **Step 8: 全 task 測試綠燈**

Run:
```
pytest tests/test_grading.py -v
```
Expected: PASS —— 共 7 項(Source 建構 1、grade 2、is_stale 4)全過,無 warning、無 skip。

---

- [ ] **Step 9: Commit**

```bash
git add src/note_filler/retrieve/__init__.py \
        src/note_filler/retrieve/models.py \
        src/note_filler/retrieve/grading.py \
        tests/test_grading.py
git commit -m "feat(retrieve): 新增 Source 模型與來源分級/新鮮度純函式

- models.py 定義 Source dataclass 與 SourceLevel(A/B/C/D)
- grading.py:grade_law()->A、grade_twinkle()->B(對齊 MIGRATION 固定映射)
- is_stale() 以 fetched_date 距今天數比對 max_age_days(嚴格大於才過期)
- retrieve/__init__.py 先留空,retrieve_for_gap() 於 Task 9 補上"
```
Expected: commit 成功,`git log --oneline -1` 顯示本則訊息。

---

### Task 7: twinkle-hub client(retrieve/twinkle.py,複製+校準)

**Files:**
- Copy `D:/Users/Administrator/Desktop/公文ai agent/src/knowledge/mcp_law_source.py` → `src/note_filler/retrieve/twinkle.py`
- Modify:回傳型別由 `list[dict]` 改為 `list[Source]`;移除 `GOV_AI_ENABLE_TWINKLE_MCP` opt-in 閘;`content` 改存「該筆記錄全文」(非 `title+案由+說明` 截斷);補 `fetched_date`/`doc_date`/`level`。
- Test:`tests/test_twinkle.py`

**Interfaces:**
- Consumes(T6):
  ```python
  SourceLevel = Literal["A","B","C","D"]
  @dataclass
  class Source:
      id:str; title:str; url:str|None; level:SourceLevel; content:str
      fetched_date:str; doc_date:str|None; distance:float
  ```
- Produces(T7):
  ```python
  class TwinkleClient:
      def __init__(self, token:str, url="https://api.twinkleai.tw/mcp/", timeout=30): ...
      def search(self, query:str, n:int=3) -> list[Source]: ...
  ```

---

#### TDD steps

- [ ] **Step 1 — cp 上游檔到目標路徑(先原封不動落地)**

  ```bash
  mkdir -p src/note_filler/retrieve
  test -f src/note_filler/retrieve/__init__.py || : > src/note_filler/retrieve/__init__.py
  cp "D:/Users/Administrator/Desktop/公文ai agent/src/knowledge/mcp_law_source.py" \
     src/note_filler/retrieve/twinkle.py
  ```

  Run:
  ```bash
  python -c "import ast,sys; ast.parse(open(r'src/note_filler/retrieve/twinkle.py',encoding='utf-8').read()); print('parse-ok')"
  ```
  Expected(PASS):`parse-ok`(上游檔純 stdlib、語法可解析,但此時 **還沒有** `Source`、簽名不符合約,尚未可用)。

- [ ] **Step 2 — 具體改寫(校準為回傳 `Source`,落實★必修項)**

  具體 edit 清單(對 cp 下來的檔做真 edit,不是重寫整檔):

  1. **改模組 docstring / import**:加 `from datetime import date`、`from note_filler.retrieve.models import Source`;移除不再用的 `math`(timeout 夾值改常數)。
  2. **保留** `TwinkleMCPClient`(`initialize`/`tools/call` 的 Streamable HTTP JSON-RPC)、`_decode_streamable_http`、`_first_text`、`_clamp_similarity`、`_extract_hits` —— 這些是零依賴傳輸層,原封搬。
  3. **刪除** `search_legislative_bills_via_mcp` 的 `GOV_AI_ENABLE_TWINKLE_MCP` opt-in 閘與 `_env_enabled`(改由「有無 token」決定連外)。
  4. **改寫** `_format_hit` → `_to_source`:回傳 `Source`;`content` 改用 `_record_fulltext(hit)` 存**全量**(metadata + 所有非空純量欄位),不再 `title+案由+說明` 截斷(落實 C5/G4);`level = metadata.source_level or "B"`;`fetched_date = date.today().isoformat()`;`doc_date` 取記錄日期欄位否則 `None`;`distance = 0.6 + 0.4*(1-sim)` 魔數保留並加 TODO 校準註。
  5. **新增** `TwinkleClient(token, url, timeout)`,`search(query, n=3) -> list[Source]`:token 為空(含 env 後援)即回 `[]`;呼叫 `search_ly_bills`;逐筆轉 `Source`;任何外部錯誤降級為 `[]`。

  校準後的 `src/note_filler/retrieve/twinkle.py` 關鍵段(傳輸層沿用上游,僅示差異段):

  ```python
  """twinkle-hub 立法院議案即時查詢,回傳 note_filler 的 Source(Level B)。

  移植自上游 公文ai agent/src/knowledge/mcp_law_source.py(純 stdlib urllib
  JSON-RPC Streamable HTTP)。校準:回傳型別改 note_filler.retrieve.models.Source;
  content 存「該筆記錄全文」以滿足無搜尋摘要閘(G4);移除 opt-in env 閘。
  """
  from __future__ import annotations

  import json
  import logging
  import os
  import urllib.request
  from datetime import date
  from typing import Any

  from note_filler.retrieve.models import Source

  logger = logging.getLogger(__name__)

  DEFAULT_MCP_URL = "https://api.twinkleai.tw/mcp/"
  _PROTOCOL_VERSION = "2025-03-26"
  _MAX_RESULTS = 100


  class MCPProtocolError(RuntimeError):
      """MCP 回應不符合預期協定。"""


  # ---- 傳輸層:沿用上游(_decode_streamable_http / TwinkleMCPClient) ----
  def _decode_streamable_http(raw: str) -> dict[str, Any] | None:
      """解析 MCP Streamable HTTP 的 JSON 或 SSE 最後一個 data payload。"""
      payloads = [
          line[5:].strip()
          for line in raw.splitlines()
          if line.startswith("data:") and line[5:].strip()
      ]
      text = payloads[-1] if payloads else raw.strip()
      if not text:
          return None
      decoded = json.loads(text)
      if not isinstance(decoded, dict):
          raise MCPProtocolError("MCP JSON-RPC 回應不是物件")
      if decoded.get("error"):
          raise MCPProtocolError(f"MCP JSON-RPC 錯誤: {decoded['error']}")
      return decoded


  class TwinkleMCPClient:
      """只實作 initialize 與 tools/call 的最小 Streamable HTTP client(沿用上游)。"""

      def __init__(self, url: str, key: str, timeout: float) -> None:
          self.url = url
          self.key = key
          self.timeout = timeout
          self._session: str | None = None
          self._request_id = 0

      def _next_id(self) -> int:
          self._request_id += 1
          return self._request_id

      def _rpc(self, method: str, params: dict[str, Any], *, notify: bool = False):
          if not self.key:
              raise MCPProtocolError("缺少 twinkle-hub 存取權杖")
          headers = {
              "Authorization": f"Bearer {self.key}",
              "Content-Type": "application/json",
              "Accept": "application/json, text/event-stream",
          }
          if self._session:
              headers["Mcp-Session-Id"] = self._session
          payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params}
          if not notify:
              payload["id"] = self._next_id()
          request = urllib.request.Request(
              self.url,
              data=json.dumps(payload).encode("utf-8"),
              headers=headers,
              method="POST",
          )
          with urllib.request.urlopen(request, timeout=self.timeout) as response:
              session_id = response.headers.get("Mcp-Session-Id")
              if session_id:
                  self._session = session_id
              raw = response.read().decode("utf-8")
          return _decode_streamable_http(raw)

      def _ensure_session(self) -> None:
          if self._session:
              return
          self._rpc(
              "initialize",
              {
                  "protocolVersion": _PROTOCOL_VERSION,
                  "capabilities": {},
                  "clientInfo": {"name": "note-filler", "version": "0.1.0"},
              },
          )
          self._rpc("notifications/initialized", {}, notify=True)

      def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
          self._ensure_session()
          response = self._rpc("tools/call", {"name": name, "arguments": arguments})
          if not response:
              return {}
          result = response.get("result")
          if not isinstance(result, dict):
              raise MCPProtocolError("MCP tools/call 缺少 result")
          if result.get("isError"):
              raise MCPProtocolError(f"MCP 工具回報失敗: {result.get('content', '')}")
          structured = result.get("structuredContent")
          if isinstance(structured, dict):
              return structured
          content = result.get("content")
          if not isinstance(content, list):
              raise MCPProtocolError("MCP tools/call 缺少 content")
          for item in content:
              if not isinstance(item, dict) or item.get("type") not in (None, "text"):
                  continue
              text = item.get("text")
              if not isinstance(text, str) or not text.strip():
                  continue
              decoded = json.loads(text)
              if isinstance(decoded, dict):
                  return decoded
          return {}


  # ---- 轉 Source(★必修項:全文 content / level / 日期 / distance 魔數) ----
  def _first_text(hit: dict[str, Any], *names: str) -> str:
      for name in names:
          value = hit.get(name)
          if value is not None and str(value).strip():
              return str(value).strip()
      return ""


  def _clamp_similarity(value: Any) -> float:
      try:
          similarity = float(value or 0.0)
      except (TypeError, ValueError):
          return 0.0
      return min(max(similarity, 0.0), 1.0)


  def _extract_hits(data: dict[str, Any]) -> list[Any]:
      for key in ("hits", "results", "data"):
          hits = data.get(key)
          if isinstance(hits, list):
              return hits
      return []


  def _record_fulltext(hit: dict[str, Any]) -> str:
      """★C5/G4:把整筆記錄(含 metadata)攤平成全文,絕不截斷成搜尋摘要。"""
      lines: list[str] = []
      for key, value in hit.items():
          if key in ("similarity", "distance"):
              continue
          if isinstance(value, (str, int, float)) and str(value).strip():
              lines.append(f"{key}: {str(value).strip()}")
          elif isinstance(value, dict):
              for sub_key, sub_value in value.items():
                  if isinstance(sub_value, (str, int, float)) and str(sub_value).strip():
                      lines.append(f"{key}.{sub_key}: {str(sub_value).strip()}")
      return "\n".join(lines)


  def _to_source(hit: dict[str, Any]) -> Source | None:
      title = _first_text(hit, "title", "議案名稱", "name")
      if not title:
          return None
      meta = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
      url = (
          _first_text(hit, "url", "source_url", "網址")
          or _first_text(meta, "source_url", "url")
          or None
      )
      level = str(meta.get("source_level") or "B")  # ★ metadata.source_level 否則 "B"
      doc_date = _first_text(hit, "date", "提案日期", "最新進度日期", "doc_date") or None
      source_id = _first_text(hit, "id", "bill_id", "議案編號") or url or title
      similarity = _clamp_similarity(hit.get("similarity"))
      return Source(
          id=source_id,
          title=title,
          url=url,
          level=level,  # type: ignore[arg-type]  # MVP 只產 A/B,此源恆 B
          content=_record_fulltext(hit),          # ★ 全文,非截斷摘要
          fetched_date=date.today().isoformat(),  # ★ 今天 ISO
          doc_date=doc_date,                        # ★ 記錄有日期則帶,否則 None
          # TODO(校準): 0.6 魔數綁定上游 KB 快照分布(1-similarity 落 0.05-0.2,
          # 需壓入 [0.6,1.0] 頻帶避免系統性壓過本地 Level A 全文)。若日後接入
          # note_filler 自有向量檢索,須以 MCP OFF 對 3+ 典型 query 重量測 distance 分布
          # 後重設下界,勿沿用 0.6。
          distance=0.6 + 0.4 * (1.0 - similarity),
      )


  class TwinkleClient:
      """twinkle-hub 立法院議案查詢;回傳 Level B 的 Source(無 token → 空結果)。"""

      def __init__(self, token: str, url: str = DEFAULT_MCP_URL, timeout: float = 30):
          self.token = token or os.environ.get("TWINKLE_HUB_TOKEN", "")  # env 後援
          self.url = url
          self.timeout = timeout

      def search(self, query: str, n: int = 3) -> list[Source]:
          if not self.token or not isinstance(query, str) or not query.strip():
              return []
          try:
              limit = min(max(int(n), 1), _MAX_RESULTS)
          except (TypeError, ValueError):
              limit = 3
          try:
              data = TwinkleMCPClient(self.url, self.token, self.timeout).call_tool(
                  "search_ly_bills",
                  {"query": query.strip(), "limit": limit},
              )
          except Exception as exc:  # noqa: BLE001 - 外部服務不得中斷主流程
              logger.warning("twinkle-hub 查詢失敗,降級為空結果: %s", exc)
              return []
          sources: list[Source] = []
          for raw_hit in _extract_hits(data):
              if not isinstance(raw_hit, dict):
                  continue
              source = _to_source(raw_hit)
              if source:
                  sources.append(source)
          return sources[:limit]
  ```

- [ ] **Step 3 — 先寫失敗 smoke test(monkeypatch 假 urlopen,驗解析出含全文的 Source)**

  `tests/test_twinkle.py`:

  ```python
  import json
  from datetime import date

  import pytest

  from note_filler.retrieve.models import Source
  from note_filler.retrieve import twinkle
  from note_filler.retrieve.twinkle import TwinkleClient

  _BILL = {
      "id": "1120001",
      "title": "道路交通管理處罰條例部分條文修正草案",
      "議案類別": "法律案",
      "議案狀態": "交付審查",
      "提案人": "王小明委員等 17 人",
      "提案日期": "2024-03-15",
      "案由": "為提高酒後駕車罰則、遏止累犯,爰擬具本修正草案。",
      "說明": "一、現行條文對累犯之處罰不足。二、修正理由:參酌日本立法例,提高吊銷年限。",
      "url": "https://ly.gov.tw/bill/1120001",
      "similarity": 0.82,
  }


  class _FakeResponse:
      def __init__(self, body: str, session: str | None = "sess-1"):
          self._body = body.encode("utf-8")
          self.headers = {"Mcp-Session-Id": session}

      def read(self):
          return self._body

      def __enter__(self):
          return self

      def __exit__(self, *exc):
          return False


  def _make_fake_urlopen(hits: list[dict]):
      """依 JSON-RPC method 回不同 payload:tools/call 回 SSE 包住的議案清單。"""
      def fake_urlopen(request, timeout=None):
          body = json.loads(request.data.decode("utf-8"))
          if body.get("method") == "tools/call":
              inner = json.dumps({"hits": hits}, ensure_ascii=False)
              envelope = json.dumps(
                  {
                      "jsonrpc": "2.0",
                      "id": body.get("id"),
                      "result": {"content": [{"type": "text", "text": inner}]},
                  },
                  ensure_ascii=False,
              )
              return _FakeResponse(f"data: {envelope}\n\n")  # 驗 SSE 解析路徑
          # initialize / notifications/initialized
          plain = json.dumps({"jsonrpc": "2.0", "id": body.get("id"), "result": {}})
          return _FakeResponse(plain)

      return fake_urlopen


  def test_search_parses_source_with_full_content(monkeypatch):
      monkeypatch.setattr(
          twinkle.urllib.request, "urlopen", _make_fake_urlopen([_BILL])
      )
      client = TwinkleClient(token="fake-token")
      results = client.search("酒駕 罰則", n=3)

      assert len(results) == 1
      src = results[0]
      assert isinstance(src, Source)
      assert src.title == _BILL["title"]
      assert src.url == "https://ly.gov.tw/bill/1120001"
      assert src.level == "B"                     # metadata 無 source_level → 預設 B
      assert src.doc_date == "2024-03-15"
      assert src.fetched_date == date.today().isoformat()
      # ★ 全文 content:案由 + 說明全文都在,非截斷摘要(G4)
      assert "現行條文對累犯之處罰不足" in src.content
      assert "參酌日本立法例" in src.content
      assert "王小明委員等 17 人" in src.content
      assert abs(src.distance - (0.6 + 0.4 * (1 - 0.82))) < 1e-9


  def test_search_returns_empty_without_token(monkeypatch):
      monkeypatch.delenv("TWINKLE_HUB_TOKEN", raising=False)
      assert TwinkleClient(token="").search("酒駕") == []


  @pytest.mark.integration
  def test_search_real_twinkle_hub():
      import os

      token = os.environ.get("TWINKLE_HUB_TOKEN", "")
      if not token:
          pytest.skip("未設定 TWINKLE_HUB_TOKEN,跳過 twinkle-hub 真打整合測試")
      results = TwinkleClient(token=token).search("道路交通管理處罰條例", n=3)
      assert isinstance(results, list)
      for src in results:
          assert isinstance(src, Source)
          assert src.level in ("A", "B")
          assert src.content.strip()               # 全文非空
          assert src.fetched_date == date.today().isoformat()
  ```

  Run:
  ```bash
  pytest tests/test_twinkle.py -m "not integration" -q
  ```
  Expected(FAIL):此步在 **Step 2 尚未完成**(檔案仍是 cp 下來的上游原檔、無 `TwinkleClient`/不回 `Source`)時執行 → `AttributeError: module 'note_filler.retrieve.twinkle' has no attribute 'TwinkleClient'` / `ImportError`,測試紅燈。

- [ ] **Step 4 — 套用 Step 2 校準後,smoke test 轉綠**

  Run:
  ```bash
  pytest tests/test_twinkle.py -m "not integration" -q
  ```
  Expected(PASS):`2 passed`(`test_search_parses_source_with_full_content`、`test_search_returns_empty_without_token`;`integration` 標記被排除)。

  Run(整合,無 token 應 skip 而非 fail):
  ```bash
  pytest tests/test_twinkle.py -m integration -q
  ```
  Expected(PASS):未設 `TWINKLE_HUB_TOKEN` 時 `1 skipped`;有 token 且服務可達時 `1 passed`。

- [ ] **Step 5 — Commit(conventional 繁中)**

  ```bash
  git add src/note_filler/retrieve/__init__.py \
          src/note_filler/retrieve/twinkle.py \
          tests/test_twinkle.py
  git commit -m "feat(retrieve): 移植 twinkle-hub client 並校準回傳 Source

  - 自上游 mcp_law_source.py 移植純 stdlib urllib JSON-RPC Streamable HTTP 傳輸層
  - 回傳型別改為 note_filler Source(Level B),content 存記錄全文以滿足無搜尋摘要閘(G4)
  - 移除 GOV_AI_ENABLE_TWINKLE_MCP opt-in 閘,改由 token 決定連外
  - fetched_date 取今日 ISO、doc_date 取記錄日期、distance 保留 0.6 頻帶魔數並附校準 TODO
  - smoke test 以 monkeypatch 假 urlopen 驗 SSE 解析出含全文 Source;另附 @pytest.mark.integration 真打(無 token skip)"
  ```

---

### Task 8: 離線法規查核(law_lookup.py + law_citation_check.py,複製+db)

**Files:**
- `src/note_filler/knowledge/law_lookup.py`(複製自上游 `src/knowledge/law_lookup.py`)
- `src/note_filler/knowledge/law_citation_check.py`(複製自上游 `src/knowledge/law_citation_check.py`,改 import + rename 參數)
- `data/law_index.db`(複製自上游 `kb_data/law_index.db`,24M,二進位)
- `tests/test_law_check.py`(新增,真 DB smoke test)

**Interfaces:**

Consumes(本 task):
- 無(純移植,零內部上游依賴)

Produces(本 task,供 T9 `check_law_citations` 與下游組裝使用;exact 簽名):
```python
class LawLookup:
    def __init__(self, db_path: str): ...
    def lookup_article(self, law_name: str, article_no: str) -> str | None: ...
    def law_exists(self, name: str) -> bool: ...
    def fuzzy_find_law(self, name: str) -> str | None: ...

def check_law_citations(text: str, lookup: LawLookup) -> list[dict]: ...
# 回傳每筆 dict 欄位固定:{law_name, article_no, kind, detail}
# kind ∈ {"article_not_found", "penalty_mismatch"}
```

> 合約對齊:本 task 落實 **C2**——`check_law_citations` 第一參數名一律 `text`(上游為 `draft`,移植時 rename)。`LawLookup` 公開方法名沿用鎖定型別(`lookup_article`/`law_exists`/`fuzzy_find_law`)。

---

TDD steps:

- [ ] **Step 0(必修:移植前先實跑上游,確認合約)**
  改動前先對上游函式 + 真 DB 跑一次,鎖定 `law_articles` schema 與 `check_law_citations` 回傳 dict 欄位符合預期(`law_name/article_no/kind/detail`)。**若實況與下方 Expected 不符,以實況為準調整測試斷言,不硬套。**

  Run:
  ```bash
  cd "D:/Users/Administrator/Desktop/公文ai agent"
  PYTHONIOENCODING=utf-8 python -X utf8 -c "
  import sqlite3
  from src.knowledge.law_lookup import LawLookup
  from src.knowledge.law_citation_check import check_law_citations
  c = sqlite3.connect('kb_data/law_index.db')
  print('SCHEMA_COLS', [r[1] for r in c.execute('PRAGMA table_info(law_articles)')])
  lk = LawLookup('kb_data/law_index.db')
  print('EXISTS', lk.law_exists('行政程序法'))
  print('ART1_OK', lk.lookup_article('行政程序法','1') is not None)
  print('ART_FAKE', lk.lookup_article('行政程序法','9999'))
  issues = check_law_citations('依行政程序法第9999條規定辦理。', lk)
  print('KIND', issues[0]['kind'])
  print('KEYS', sorted(issues[0]))
  "
  ```
  Expected(PASS,作為合約基準線):
  ```
  SCHEMA_COLS ['pcode', 'law_name', 'article_no', 'article_text']
  EXISTS True
  ART1_OK True
  ART_FAKE None
  KIND article_not_found
  KEYS ['article_no', 'detail', 'kind', 'law_name']
  ```

- [ ] **Step 1(先寫測試,看它 FAIL)** 建立 `tests/test_law_check.py`:
  ```python
  # tests/test_law_check.py
  # -*- coding: utf-8 -*-
  from pathlib import Path

  import pytest

  from note_filler.knowledge.law_lookup import LawLookup
  from note_filler.knowledge.law_citation_check import check_law_citations

  DB = str(Path(__file__).resolve().parents[1] / "data" / "law_index.db")


  @pytest.fixture(scope="module")
  def lookup() -> LawLookup:
      db = Path(DB)
      assert db.exists(), f"法規索引 DB 未就緒:{db}"
      return LawLookup(DB)


  def test_real_law_article_exists(lookup):
      # 真法規、真條號 → 存在且有內容
      assert lookup.law_exists("行政程序法") is True
      art = lookup.lookup_article("行政程序法", "1")
      assert art is not None and len(art) > 0


  def test_fake_article_no_flagged_not_found(lookup):
      # 真法規、假條號 → article_not_found,且 dict 欄位齊全
      issues = check_law_citations("依行政程序法第9999條規定辦理。", lookup)
      hits = [i for i in issues if i["kind"] == "article_not_found"]
      assert hits, f"預期 article_not_found,實得 {issues}"
      hit = hits[0]
      assert set(hit) >= {"law_name", "article_no", "kind", "detail"}
      assert hit["law_name"] == "行政程序法"
      assert hit["article_no"] == "9999"


  def test_unknown_law_not_false_reported(lookup):
      # 法規名不在庫(未收錄)→ 不誤報
      issues = check_law_citations("依外星生物保護法第1條規定辦理。", lookup)
      assert issues == []


  def test_check_law_citations_first_param_is_text():
      # C2:第一參數名一律 text(防回歸成 draft)
      import inspect
      params = list(inspect.signature(check_law_citations).parameters)
      assert params[0] == "text", f"第一參數應為 text,實得 {params[0]}"
  ```
  Run:
  ```bash
  cd <note_filler repo root>
  python -m pytest tests/test_law_check.py -q
  ```
  Expected(FAIL):
  ```
  E   ModuleNotFoundError: No module named 'note_filler.knowledge.law_lookup'
  (檔案尚未移植;collection error)
  ```

- [ ] **Step 2(cp 上游兩檔 + db)** 直接複製,先不改內容:
  ```bash
  cd <note_filler repo root>
  UP="D:/Users/Administrator/Desktop/公文ai agent"
  mkdir -p src/note_filler/knowledge data
  cp "$UP/src/knowledge/law_lookup.py"        src/note_filler/knowledge/law_lookup.py
  cp "$UP/src/knowledge/law_citation_check.py" src/note_filler/knowledge/law_citation_check.py
  cp "$UP/kb_data/law_index.db"                data/law_index.db
  test -f src/note_filler/knowledge/__init__.py || : > src/note_filler/knowledge/__init__.py
  ls -l data/law_index.db
  ```
  Run(複製後再跑一次,仍會 FAIL——因為 `law_citation_check.py` 的 import 還指向 `src.knowledge`):
  ```bash
  python -m pytest tests/test_law_check.py -q
  ```
  Expected(FAIL):
  ```
  E   ModuleNotFoundError: No module named 'src'
  (law_citation_check.py 第 9 行 import 未改)
  ```

- [ ] **Step 3(移植後具體改寫:改 import + rename `draft`→`text`)** 只動 `law_citation_check.py`,共 3 處真 edit(`law_lookup.py` 零內部依賴,複製後不需改):

  改寫 1 — import 路徑(同時引入 `LawLookup` 供型別標註):
  ```python
  # before(上游第 9 行)
  from src.knowledge.law_lookup import _normalize_article_no
  # after
  from note_filler.knowledge.law_lookup import LawLookup, _normalize_article_no
  ```

  改寫 2 — `check_law_citations` 簽名對齊 C2 鎖定型別:
  ```python
  # before
  def check_law_citations(draft: str, lookup) -> list[dict]:
  # after
  def check_law_citations(text: str, lookup: LawLookup) -> list[dict]:
  ```

  改寫 3 — 函式體內兩處 `draft` 引用同步改為 `text`:
  ```python
  # before
      for cite in extract_law_citations(draft):
      ...
          window = draft[cite["end"] : cite["end"] + 70]
  # after
      for cite in extract_law_citations(text):
      ...
          window = text[cite["end"] : cite["end"] + 70]
  ```

  > 注意:`extract_law_citations(draft: str)` 與 `annotate_law_mismatches(draft: str, lookup)` 非鎖定型別介面、也非本 task Produces 契約,參數名維持 `draft` 不動;`annotate_law_mismatches` 內以位置參數呼叫 `check_law_citations(draft, lookup)`,rename 後仍相容,不需改。只有 C2 指名的 `check_law_citations` 第一參數必為 `text`。

- [ ] **Step 4(smoke test 通過)** Run:
  ```bash
  cd <note_filler repo root>
  python -m pytest tests/test_law_check.py -q
  ```
  Expected(PASS):
  ```
  ....                                                                     [100%]
  4 passed in 0.4s
  ```

- [ ] **Step 5(Commit,conventional 繁中)**
  ```bash
  git add src/note_filler/knowledge/law_lookup.py \
          src/note_filler/knowledge/law_citation_check.py \
          src/note_filler/knowledge/__init__.py \
          data/law_index.db \
          tests/test_law_check.py
  git diff --cached --name-only   # 硬規則10:嚴格比對預期清單,不符即 reset 中止
  git commit -m "feat(knowledge): 移植離線法規查核(law_lookup + citation_check + 24M 索引 db)

- 複製上游 law_lookup.py / law_citation_check.py 至 src/note_filler/knowledge
- 複製 kb_data/law_index.db -> data/law_index.db(law_articles 47037 條)
- 改 import 路徑 src.knowledge -> note_filler.knowledge
- 依 C2 將 check_law_citations 第一參數 draft rename 為 text
- 新增 tests/test_law_check.py:真 DB 驗真條存在、假條號回 article_not_found、未收錄法規不誤報"
  ```

> 備註(不阻斷本 task,交下一輪決策):`data/law_index.db` 為 24M 二進位,直接入 git 會膨脹 repo。此處依規格「直接複製到 data/law_index.db」先納入版控;若後續 repo 體積成問題,再評估改走 Git LFS 或 `.gitignore` + 建置期產生,屬獨立議題不在本 task 動它。

---

### Task 9: 依缺口檢索(retrieve/__init__.py)

**Files:**
- Modify `src/note_filler/retrieve/__init__.py`
- Test `tests/test_retrieve.py`

**Interfaces:**

Consumes:
- `Gap`(T5) — `@dataclass class Gap: question:str; status:Literal["covered","partial","missing"]; reason:str`
- `Domain`(T3) — `Domain = Literal["law","admin","exam","other"]`
- `Source`(T6) — `@dataclass class Source: id:str; title:str; url:str|None; level:SourceLevel; content:str; fetched_date:str; doc_date:str|None; distance:float`
- `TwinkleClient`(T7) — `class TwinkleClient: def search(self, query:str, n:int=3) -> list[Source]`

Produces:
- `def retrieve_for_gap(gap: Gap, domain: Domain, twinkle: TwinkleClient) -> list[Source]`(T9)

本 task 非複製類(TwinkleClient 已於 T7 移植落地,這裡只消費它),走一般 RED→GREEN;`domain` 參數落實「MVP 只在 law/admin/exam 檢索」,★必修項落實 C5 排序(Level A 先於 B、再 distance 小先)。

---

- [ ] **Step 1 (RED):寫失敗測試** — `tests/test_retrieve.py`。用 `FakeTwinkle` 回混合 A/B 的 `Source`,斷言排序後 A 全在 B 前、同級內 distance 小者先、且 `twinkle.search` 收到的 query 恰為 `gap.question`;另驗 `domain="other"` 不檢索回空。

```python
# tests/test_retrieve.py
import pytest
from note_filler.gap import Gap
from note_filler.retrieve.models import Source
from note_filler.retrieve import retrieve_for_gap


class FakeTwinkle:
    """模擬 TwinkleClient.search;記錄呼叫參數,回傳 canned Source。"""
    def __init__(self, responses: list[Source]):
        self.responses = responses
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, n: int = 3) -> list[Source]:
        self.calls.append((query, n))
        return list(self.responses)  # 回副本,避免被排序就地改動


def _src(sid: str, level: str, distance: float) -> Source:
    return Source(
        id=sid, title=f"title-{sid}", url=f"https://twinkle/{sid}",
        level=level, content=f"官方一手記錄全文 {sid}",
        fetched_date="2026-07-15", doc_date=None, distance=distance,
    )


def test_retrieve_for_gap_sorts_A_before_B_then_distance():
    gap = Gap(question="勞動基準法第84條之1責任制範圍為何?", status="missing", reason="原稿未涵蓋")
    # 刻意亂序;注意 b2 distance=0.1 比所有 A 都小,用來證明「級別壓過 distance」
    twinkle = FakeTwinkle([
        _src("b1", "B", 0.3),
        _src("a1", "A", 0.7),
        _src("a2", "A", 0.2),
        _src("b2", "B", 0.1),
    ])

    out = retrieve_for_gap(gap, "law", twinkle)

    # A 先(級內 distance 升序):a2(0.2)→a1(0.7);再 B:b2(0.1)→b1(0.3)
    assert [s.id for s in out] == ["a2", "a1", "b2", "b1"]
    # query 必須用 gap.question
    assert twinkle.calls[0][0] == gap.question


def test_retrieve_for_gap_skips_non_mvp_domain():
    gap = Gap(question="這題超綱", status="missing", reason="")
    twinkle = FakeTwinkle([_src("a1", "A", 0.1)])

    out = retrieve_for_gap(gap, "other", twinkle)

    assert out == []
    assert twinkle.calls == []  # 非 MVP 領域完全不打 twinkle
```

Run:
```bash
cd note_filler && python -m pytest tests/test_retrieve.py -q
```
Expected (FAIL):
```
E   ModuleNotFoundError: No module named 'note_filler.retrieve'
(或 ImportError: cannot import name 'retrieve_for_gap')
```

---

- [ ] **Step 2 (GREEN):實作 `retrieve_for_gap`** — 依 `domain` 決定是否檢索(僅 law/admin/exam),以 `gap.question` 打 `twinkle.search`,回傳前依 C5 排序:`(Level rank, distance)`,A=0、B=1(C/D 保留但 MVP 不產),同級 distance 升序。用 `sorted` 產新 list,不就地改動來源。

```python
# src/note_filler/retrieve/__init__.py
"""依缺口檢索:對單一 Gap 打 twinkle 取回一手來源,並依 C5 排序(A 先於 B、distance 小先)。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import Gap, Source

if TYPE_CHECKING:  # 僅型別檢查用,避免執行期循環匯入
    from ..models import Domain
    from ..twinkle import TwinkleClient

# SourceLevel 枚舉 A/B/C/D 排序權重;MVP 只會出現 A/B,未知級別排最後
_LEVEL_RANK: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3}
# MVP 領域閘:只在 law/admin/exam 檢索(開放網路/其他領域延後)
_RETRIEVABLE: frozenset[str] = frozenset({"law", "admin", "exam"})


def retrieve_for_gap(gap: Gap, domain: "Domain", twinkle: "TwinkleClient") -> list[Source]:
    """對缺口 gap 檢索一手來源。

    - domain 非 MVP(law/admin/exam)→ 不檢索,回 [](不浪費網路)。
    - 以 gap.question 為 query 打 twinkle.search。
    - 回傳前依 C5 排序:Level A 先於 B,同級 distance 小者先,落實 G2 優先一手源。
    """
    if domain not in _RETRIEVABLE:
        return []
    sources = twinkle.search(gap.question)
    return sorted(sources, key=lambda s: (_LEVEL_RANK.get(s.level, 99), s.distance))
```

Run:
```bash
cd note_filler && python -m pytest tests/test_retrieve.py -q
```
Expected (PASS):
```
..                                                               [100%]
2 passed in 0.0Xs
```

---

- [ ] **Step 3:真 twinkle 整合冒煙測試(選配,標 integration)** — 消費 T7 移植的真 `TwinkleClient`,實打 twinkle-hub 一筆,驗回傳皆為 `Source`、級別只有 A/B,且排序不變式成立(相鄰兩筆前者 `(rank, distance)` 不劣於後者)。需 `GOV_AI_ENABLE_TWINKLE_MCP=1` 與 `TWINKLE_HUB_TOKEN`,缺則 skip,不打真網路。

```python
# tests/test_retrieve.py(續)
import os
from note_filler.retrieve import _LEVEL_RANK  # 排序權重,重用以驗不變式


@pytest.mark.integration
def test_retrieve_for_gap_real_twinkle_smoke():
    token = os.environ.get("TWINKLE_HUB_TOKEN")
    if os.environ.get("GOV_AI_ENABLE_TWINKLE_MCP") != "1" or not token:
        pytest.skip("需 GOV_AI_ENABLE_TWINKLE_MCP=1 且設 TWINKLE_HUB_TOKEN")

    from note_filler.retrieve.twinkle import TwinkleClient

    gap = Gap(question="勞動基準法 責任制 工時", status="missing", reason="")
    twinkle = TwinkleClient(token=token)

    out = retrieve_for_gap(gap, "law", twinkle)

    assert all(isinstance(s, Source) for s in out)
    assert all(s.level in ("A", "B") for s in out)  # MVP 只產 A/B
    # 排序不變式:整串 (rank, distance) 已升序
    keys = [(_LEVEL_RANK[s.level], s.distance) for s in out]
    assert keys == sorted(keys)
```

Run(僅整合層,平時 CI 用 `-m "not integration"` 略過):
```bash
cd note_filler && GOV_AI_ENABLE_TWINKLE_MCP=1 TWINKLE_HUB_TOKEN=*** python -m pytest tests/test_retrieve.py -m integration -q
```
Expected (PASS 或 skip):
```
1 passed in 1.XXs
(或未設 env 時:1 skipped)
```

---

- [ ] **Commit**
```bash
git add src/note_filler/retrieve/__init__.py tests/test_retrieve.py
git commit -m "feat(retrieve): 依缺口打 twinkle 檢索並依 A 先於 B、distance 小先排序

- retrieve_for_gap 以 gap.question 為 query,落實 C5/G2 優先一手源
- 非 MVP 領域(other)不檢索,直接回空
- 補 FakeTwinkle 單元測試(排序+query)與 twinkle 整合冒煙測試"
```

---

### Task 10: 交叉驗證(verify.py)

純函式模組,不呼叫 LLM。核心是 C4 硬合約:`cross_validate` 內部對「獨立 A/B 來源」做**顯式計數**,count>=2 才 `verified=True`。衝突偵測用關鍵詞啟發式,只標記不自動選邊(原實作要點)。來源排序遵守 C5:Level A 先於 B、distance 小者先。

**Files:**
- Create `src/note_filler/verify.py`
- Test `tests/test_verify.py`

**Interfaces:**
- Consumes:
  - `Source(id, title, url, level, content, fetched_date, doc_date, distance)` — T6(`note_filler.retrieve.models`);`level: SourceLevel = Literal["A","B","C","D"]`。
- Produces:
  - `@dataclass class Validation: claim:str; sources:list; verified:bool; conflict:bool; conflict_note:str|None` — 本 task(T10)
  - `def cross_validate(claim: str, sources: list) -> Validation` — 本 task(T10)
  - (內部輔助,非對外簽名)`_independent_ab(sources) -> list[Source]`、`_is_independent(a, b) -> bool`、`_detect_conflict(sources) -> tuple[bool, str|None]`

---

#### TDD Steps

- [ ] **Step 1 — 寫 verified 計數測試(FAIL)**

  先寫 C4 四個核心案例:2 獨立 A/B→verified、2 同 url→not verified、只有 1 個→not verified、含 C/D 不計入。

  ```python
  # tests/test_verify.py
  from note_filler.retrieve.models import Source
  from note_filler.verify import Validation, cross_validate


  def mk(id: str, title: str, url: str | None, level: str,
         content: str = "", distance: float = 0.5) -> Source:
      """測試用 Source 工廠;固定 fetched_date、doc_date=None。"""
      return Source(
          id=id, title=title, url=url, level=level, content=content,
          fetched_date="2026-07-15", doc_date=None, distance=distance,
      )


  def test_two_independent_ab_sources_verified():
      # 不同 url 且 不同 title/機關,level 皆 A/B → verified
      sources = [
          mk("s1", "行政程序法第92條", "https://law.moj.gov.tw/a", "A",
             content="行政處分應以書面為之。"),
          mk("s2", "立法院議案關係文書 第10屆", "https://ly.gov.tw/b", "B",
             content="行政處分應以書面為之。"),
      ]
      v = cross_validate("行政處分應以書面為之", sources)
      assert isinstance(v, Validation)
      assert v.verified is True
      assert v.claim == "行政處分應以書面為之"
      assert v.sources == sources  # 原始來源保留不刪


  def test_same_url_not_verified():
      # 兩筆 url 相同 → 非獨立 → 只算 1 → not verified
      sources = [
          mk("s1", "來源甲", "https://same.example/x", "A", content="X 成立。"),
          mk("s2", "來源乙", "https://same.example/x", "A", content="X 成立。"),
      ]
      v = cross_validate("X 成立", sources)
      assert v.verified is False


  def test_single_source_not_verified():
      sources = [mk("s1", "唯一來源", "https://only.example/z", "A", content="Z。")]
      v = cross_validate("Z", sources)
      assert v.verified is False


  def test_cd_level_not_counted():
      # 1 個 A + 1 個 C + 1 個 D:C/D 不計入 → 獨立 A/B 僅 1 → not verified
      sources = [
          mk("s1", "官方一手", "https://gov.example/a", "A", content="主張成立。"),
          mk("s2", "部落格摘要", "https://blog.example/c", "C", content="主張成立。"),
          mk("s3", "論壇貼文", "https://forum.example/d", "D", content="主張成立。"),
      ]
      v = cross_validate("主張成立", sources)
      assert v.verified is False
  ```

  **Run:** `pytest tests/test_verify.py -q`
  **Expected (FAIL):** `ModuleNotFoundError: No module named 'note_filler.verify'`(尚未建檔)。

- [ ] **Step 2 — 實作 verify.py 使計數測試通過(PASS)**

  建 `Validation` 與 `cross_validate`,`_independent_ab` 對來源先依 C5 排序(A 先、distance 小先),再貪婪挑出彼此獨立的 A/B 子集,**顯式計數** `len >= 2` 才 verified。

  ```python
  # src/note_filler/verify.py
  from __future__ import annotations

  from dataclasses import dataclass

  from note_filler.retrieve.models import Source


  @dataclass
  class Validation:
      claim: str
      sources: list
      verified: bool
      conflict: bool
      conflict_note: str | None


  def _is_independent(a: Source, b: Source) -> bool:
      """獨立 = url 不同 且 title(機關/文件) 不同。
      任一 url 為 None 時無法證明「不同 url」,保守視為不獨立。
      """
      diff_url = a.url is not None and b.url is not None and a.url != b.url
      diff_title = a.title != b.title
      return diff_url and diff_title


  def _independent_ab(sources: list[Source]) -> list[Source]:
      """回傳彼此獨立的 A/B 來源子集(僅計 level A/B)。
      C5 排序:Level A 先於 B、distance 小者先;再貪婪挑選互相獨立者。
      """
      ab = [s for s in sources if s.level in ("A", "B")]
      ab.sort(key=lambda s: (0 if s.level == "A" else 1, s.distance))
      kept: list[Source] = []
      for s in ab:
          if all(_is_independent(s, k) for k in kept):
              kept.append(s)
      return kept


  def cross_validate(claim: str, sources: list) -> Validation:
      """C4:顯式計數獨立 A/B 來源,count>=2 才 verified。
      衝突僅標記不選邊(見 _detect_conflict)。
      """
      independent = _independent_ab(sources)
      verified = len(independent) >= 2  # 顯式計數 >=2
      conflict, note = _detect_conflict(sources)
      return Validation(
          claim=claim,
          sources=sources,      # 原始來源保留,不因衝突刪除
          verified=verified,
          conflict=conflict,
          conflict_note=note,
      )


  # 衝突偵測用的正/反關鍵詞對;命中僅標記,絕不自動選邊
  _CONFLICT_PAIRS: list[tuple[str, str]] = [
      ("應", "不應"),
      ("得", "不得"),
      ("有效", "失效"),
      ("有效", "廢止"),
      ("合法", "違法"),
      ("成立", "不成立"),
  ]


  def _detect_conflict(sources: list[Source]) -> tuple[bool, str | None]:
      """關鍵詞啟發式:若某來源含正面詞、另一來源含其反面詞 → 標記衝突。
      不判斷孰是孰非(不選邊)。
      """
      texts = [s.content or "" for s in sources]
      for pos, neg in _CONFLICT_PAIRS:
          # 反面詞常含正面詞為子字串(如「不應」含「應」),故正面命中須排除含反面詞者
          has_pos = any(pos in t and neg not in t for t in texts)
          has_neg = any(neg in t for t in texts)
          if has_pos and has_neg:
              note = f"來源對「{pos}/{neg}」表述不一致,需人工判讀(未自動選邊)"
              return True, note
      return False, None
  ```

  **Run:** `pytest tests/test_verify.py -q`
  **Expected (PASS):** 4 passed。

- [ ] **Step 3 — 寫衝突啟發式測試(FAIL)**

  追加測試:反面詞命中 → `conflict=True` 且 `conflict_note` 非空;同時驗「不選邊」(sources 全數保留、verified 仍由計數決定)。

  ```python
  # tests/test_verify.py (append)
  def test_conflict_detected_and_no_side_taken():
      # 一源「得」、一源「不得」→ 標記衝突,但不刪來源、不選邊
      sources = [
          mk("s1", "來源甲", "https://a.example/1", "A", content="納稅義務人得申請延期。"),
          mk("s2", "來源乙", "https://b.example/2", "B", content="納稅義務人不得申請延期。"),
      ]
      v = cross_validate("納稅義務人得否申請延期", sources)
      assert v.conflict is True
      assert v.conflict_note is not None and "不選邊" in v.conflict_note
      assert v.sources == sources          # 未選邊、未刪除任何來源
      assert v.verified is True            # 2 獨立 A/B,verified 與 conflict 各自獨立


  def test_no_conflict_when_consistent():
      sources = [
          mk("s1", "來源甲", "https://a.example/1", "A", content="行政處分應以書面為之。"),
          mk("s2", "來源乙", "https://b.example/2", "B", content="行政處分應以書面為之。"),
      ]
      v = cross_validate("行政處分應以書面為之", sources)
      assert v.conflict is False
      assert v.conflict_note is None
  ```

  **Run:** `pytest tests/test_verify.py -q -k conflict`
  **Expected (FAIL 或全綠?):** 若 Step 2 已含 `_detect_conflict`,此步應直接 PASS;若你採「先寫測試後補實作」節奏,先在 Step 2 略去 `_detect_conflict` 主體(回傳 `(False, None)`),此步即出現 `AssertionError: assert False is True`。

- [ ] **Step 4 — 補實作使衝突測試通過(PASS)**

  (若 Step 2 已完整實作 `_detect_conflict` 則本步為確認回歸。)確認正/反子字串排除邏輯正確:反面詞 `不應` 不得誤觸發 `應` 的正面命中。

  ```python
  # tests/test_verify.py (append) — 子字串誤判防護
  def test_negation_substring_not_false_positive():
      # 兩源皆為反面「不應」,不應被判為「應 vs 不應」衝突
      sources = [
          mk("s1", "來源甲", "https://a.example/1", "A", content="機關不應逕行處分。"),
          mk("s2", "來源乙", "https://b.example/2", "B", content="機關不應逕行處分。"),
      ]
      v = cross_validate("機關不應逕行處分", sources)
      assert v.conflict is False
  ```

  **Run:** `pytest tests/test_verify.py -q`
  **Expected (PASS):** all passed(含衝突與子字串防護)。

- [ ] **Step 5 — C5 排序/優先 A 回歸測試(PASS)**

  驗證 `_independent_ab` 依 C5 排序:Level A 優先、distance 小者先,且獨立計數不受重複來源膨脹。

  ```python
  # tests/test_verify.py (append)
  from note_filler.verify import _independent_ab


  def test_independent_ab_orders_A_before_B_and_by_distance():
      sources = [
          mk("b_far", "B 遠", "https://b.example/far", "B", distance=0.9),
          mk("a_near", "A 近", "https://a.example/near", "A", distance=0.2),
          mk("a_far", "A 遠", "https://a.example/far", "A", distance=0.7),
      ]
      kept = _independent_ab(sources)
      # 三者兩兩獨立(url、title 皆異)→ 全留;順序:A 近、A 遠、B 遠
      assert [s.id for s in kept] == ["a_near", "a_far", "b_far"]


  def test_duplicate_title_collapses_to_one():
      # 同 title(同機關/文件)不同 url → 非獨立,計數仍為 1 → not verified
      sources = [
          mk("s1", "行政程序法第92條", "https://law.example/v1", "A", content="X。"),
          mk("s2", "行政程序法第92條", "https://law.example/v2", "A", content="X。"),
      ]
      v = cross_validate("X", sources)
      assert v.verified is False
      assert len(_independent_ab(sources)) == 1
  ```

  **Run:** `pytest tests/test_verify.py -q`
  **Expected (PASS):** all passed。

- [ ] **Commit**

  ```
  feat(verify): 交叉驗證顯式計數獨立 A/B 來源並偵測衝突不選邊

  - cross_validate 依 C4 顯式計數獨立 A/B 來源,count>=2 才 verified
  - 獨立判定:url 不同且 title/機關 不同;C/D 級不計入
  - _independent_ab 依 C5 排序(A 先、distance 小先)後貪婪挑選
  - _detect_conflict 用正/反關鍵詞啟發式僅標記衝突,保留全部來源不選邊
  - 補齊 test_verify.py:verified 計數四案、衝突、子字串防護、排序回歸
  ```

---

### Task 11: 引用格式(citation_formatter.py,複製)

**Files:**
- Copy: `D:/Users/Administrator/Desktop/公文ai agent/src/document/citation_formatter.py` -> `src/note_filler/citation_formatter.py`
- Modify: `src/note_filler/citation_formatter.py`(輸入從 `list[dict]` 改為 `list[Source]`,`CitationFormatter` classmethod 收斂為單一純函式 `build_reference_lines`)
- Test: `tests/test_citation_formatter.py`

**Interfaces:**
- Consumes: `Source`(Task 6,`src/note_filler/retrieve/models.py`):
  ```python
  @dataclass
  class Source:
      id: str
      title: str
      url: str | None
      level: SourceLevel      # Literal["A","B","C","D"]
      content: str
      fetched_date: str
      doc_date: str | None
      distance: float
  ```
- Produces: `build_reference_lines(sources: list) -> str`(`src/note_filler/citation_formatter.py`);純函式,每行格式 `[^{i}]: [Level {level}] {title} | URL: {url} | Date: {doc_date or fetched_date} | Hash: {sha1(content)[:8]} | Evidence: {content[:100]}`,多行以 `\n` 串接。

---

- [ ] **Step 1: Write the failing test** — 建立 `tests/test_citation_formatter.py`,驗證兩個 `Source` 產出兩行,且序號、Level、URL、Hash、Evidence 前 100 字皆正確。

  ```python
  # tests/test_citation_formatter.py
  import hashlib

  from note_filler.retrieve.models import Source
  from note_filler.citation_formatter import build_reference_lines


  def _make_source(id: str, title: str, url: str | None, level: str, content: str) -> Source:
      return Source(
          id=id,
          title=title,
          url=url,
          level=level,
          content=content,
          fetched_date="2026-07-15",
          doc_date=None,
          distance=0.0,
      )


  def test_build_reference_lines_two_sources():
      long_content = "本法所稱行政處分,係指行政機關就公法上具體事件所為之決定而對外直接發生法律效果之單方行政行為。" * 5
      sources = [
          _make_source(
              "s1",
              "行政程序法",
              "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0030055",
              "A",
              "行政程序法第九十二條:本法所稱行政處分,係指行政機關就公法上具體事件所為之決定。",
          ),
          _make_source(
              "s2",
              "立法院議案關係文書",
              "https://ppg.ly.gov.tw/ppg/bills/12345",
              "B",
              long_content,
          ),
      ]

      result = build_reference_lines(sources)
      lines = result.split("\n")

      # 兩個 Source -> 兩行
      assert len(lines) == 2

      # 序號:依序 [^1] [^2]
      assert lines[0].startswith("[^1]: ")
      assert lines[1].startswith("[^2]: ")

      # Level 正確
      assert "[Level A]" in lines[0]
      assert "[Level B]" in lines[1]

      # 標題
      assert "行政程序法" in lines[0]
      assert "立法院議案關係文書" in lines[1]

      # URL 正確
      assert "URL: https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0030055" in lines[0]
      assert "URL: https://ppg.ly.gov.tw/ppg/bills/12345" in lines[1]

      # Date:doc_date 優先,否則 fetched_date(此處兩筆 doc_date 皆 None → 用 fetched_date)
      assert "Date: 2026-07-15" in lines[0]
      assert "Date: 2026-07-15" in lines[1]

      # Hash = sha1(content)[:8]
      expected_hash = hashlib.sha1(sources[0].content.encode("utf-8")).hexdigest()[:8]
      assert f"Hash: {expected_hash}" in lines[0]

      # Evidence 取 content 前 100 字(長內容需被截斷)
      assert f"Evidence: {sources[1].content[:100]}" in lines[1]
      assert len(sources[1].content) > 100  # 確認確實有截斷發生
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run:
  ```bash
  pytest tests/test_citation_formatter.py::test_build_reference_lines_two_sources -v
  ```
  Expected: **FAIL** — `ImportError` / `ModuleNotFoundError`,因為 `src/note_filler/citation_formatter.py` 尚未存在(或匯入不到 `build_reference_lines`)。

- [ ] **Step 3: 複製上游檔到目的路徑**

  Run:
  ```bash
  cp "D:/Users/Administrator/Desktop/公文ai agent/src/document/citation_formatter.py" "src/note_filler/citation_formatter.py"
  ```
  Expected: `src/note_filler/citation_formatter.py` 出現,內容為上游 `CitationFormatter`(以 `list[dict]` 為輸入、含 `_normalize_title_for_context` 公文專用邏輯)。此時測試仍 FAIL(對外介面不符:上游是 classmethod 且簽名為 `build_reference_lines(draft, sources_list, *, preserve_all_sources)`)。

- [ ] **Step 4: 改寫成接受 Source list 的純函式** — 去掉公文專用的 `draft`/會議情境正規化/`preserve_all_sources` 參數,輸入改吃 `Source` dataclass,並自行計算 `sha1(content)[:8]`。以下 code 整檔取代 Step 3 複製進來的內容:

  ```python
  # src/note_filler/citation_formatter.py
  from __future__ import annotations

  import hashlib

  REFERENCE_SECTION_HEADING = "### 參考來源 (AI 引用追蹤)"


  def build_reference_lines(sources: list) -> str:
      """把 Source 清單轉成引用行字串(純函式,無副作用)。

      每行格式:
          [^{i}]: [Level {level}] {title} | URL: {url} | Date: {doc_date or fetched_date} | Hash: {sha1(content)[:8]} | Evidence: {content[:100]}

      - i 依 sources 順序從 1 起算
      - url 為 None 時省略 " | URL: ..." 區段
      - Date 取 doc_date,否則 fetched_date(必存在,url 為 None 時仍保留)
      - Hash 為 content 的 sha1 前 8 碼(utf-8 編碼)
      - Evidence 取 content 前 100 字,換行壓成空白後 strip
      多行以 "\\n" 串接;空清單回傳空字串。
      """
      lines: list[str] = []
      for i, src in enumerate(sources, start=1):
          content = src.content or ""
          content_hash = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
          evidence = content[:100].replace("\n", " ").strip()
          url_part = f" | URL: {src.url}" if src.url else ""
          date = src.doc_date or src.fetched_date
          lines.append(
              f"[^{i}]: [Level {src.level}] {src.title}"
              f"{url_part} | Date: {date} | Hash: {content_hash} | Evidence: {evidence}"
          )
      return "\n".join(lines)


  def build_reference_block(sources: list) -> str:
      """在引用行前加上參考來源標題;無來源時回傳空字串。"""
      lines = build_reference_lines(sources)
      if not lines:
          return ""
      return REFERENCE_SECTION_HEADING + "\n" + lines
  ```

  改寫要點(對照上游):移除 `draft` 參數與 `_normalize_title_for_context`(會議情境改標題屬公文專用,筆記補齊不需要);移除 `re` 掃 `[^n]` 引用計數與 `preserve_all_sources`(筆記補齊固定輸出所有 Source);來源欄位由 dict 的 `source_level`/`source_url`/`content_hash`/`content` 改為 `Source.level`/`Source.url`/自算 hash/`Source.content`。

- [ ] **Step 5: Run test to verify it passes**

  Run:
  ```bash
  pytest tests/test_citation_formatter.py::test_build_reference_lines_two_sources -v
  ```
  Expected: **PASS** — 兩行輸出,序號 `[^1]`/`[^2]`、`[Level A]`/`[Level B]`、兩個 URL、`sha1` 前 8 碼 Hash、以及第二筆 Evidence 為 `content[:100]` 全部 assert 通過。

- [ ] **Step 6: Commit**

  Run:
  ```bash
  git add src/note_filler/citation_formatter.py tests/test_citation_formatter.py
  git commit -m "feat(citation): 移植引用格式產生器,輸入改為 Source 並自算 sha1 hash"
  ```

---

### Task 12: 訂正稿組裝 + 無來源閘(correction.py,自建②)

**Files:**
- Create `src/note_filler/correction.py`
- Test `tests/test_correction.py`

**Interfaces:**

Consumes(唯讀,只讀屬性不改任何一字):
- `Document`(T2) — `@dataclass(frozen=True) Document: source_path:str; paragraphs:tuple; full_text:str`;`Paragraph: idx:int; text:str`
- `Gap`(T5) — `@dataclass Gap: question:str; status:Literal["covered","partial","missing"]; reason:str`
- `Source`(T6) — `@dataclass Source: id:str; title:str; url:str|None; level:SourceLevel; content:str; fetched_date:str; doc_date:str|None; distance:float`
- `Validation`(T10) — `@dataclass Validation: claim:str; sources:list; verified:bool; conflict:bool; conflict_note:str|None`

Produces(本 task 定義,下游 T13/T14/T16 import 不重寫):
- `@dataclass Segment: type:Literal["original","supplement"]; text:str; anchor_idx:int|None; sources:list; confidence:Literal["verified","pending_evidence"]`
- `@dataclass CorrectionDoc: original:Document; segments:list`
- `def assemble_correction(doc:Document, gaps:list, retrieved:dict, validations:dict) -> CorrectionDoc: ...`
  - `retrieved`:`dict[gap.question -> list[Source]]`(T11 產)
  - `validations`:`dict[gap.question -> Validation]`(T10 產)

本 task 無 LLM 呼叫(純組裝),故不需 FakeLLM / 不加 `@pytest.mark.integration`。

★必修項落實對照:
- **C6 pending_evidence 不變式**:supplement 段 `sources` 空 **或** `validations[gap.question].verified` 為 False → `confidence="pending_evidence"`(該段保留不刪);兩者皆滿足(有源 **且** verified True)才 `"verified"`。
- **原稿 immutable**:原文段 `text` 逐字等於 `Paragraph.text`,不做任何 strip/normalize/覆寫。
- **overlay 不刪原文**:先鋪全部 original 段,再逐 gap append supplement 段,原文段數與順序恆等於 `doc.paragraphs`。

---

#### TDD Steps

- [ ] **Step 1 — 寫失敗測試(先 RED)**

```python
# tests/test_correction.py
import pytest

from note_filler.correction import assemble_correction, Segment, CorrectionDoc
from note_filler.parse import Document, Paragraph      # T2
from note_filler.gap import Gap                         # T5
from note_filler.retrieve.models import Source                 # T6
from note_filler.verify import Validation              # T10


def _doc(texts):
    paras = tuple(Paragraph(idx=i, text=t) for i, t in enumerate(texts))
    return Document(source_path="x.docx", paragraphs=paras, full_text="\n".join(texts))


def _src(sid, title, url, level="A"):
    return Source(
        id=sid, title=title, url=url, level=level,
        content=f"{title} 記錄全文", fetched_date="2026-07-15",
        doc_date=None, distance=0.4,
    )


def test_original_segments_verbatim_and_immutable():
    """原文段逐字全等輸入,順序/段數不變,confidence=verified。"""
    texts = ["行政程序法第92條規定行政處分之定義。", "第二段原始筆記內容,一字不改。"]
    doc = _doc(texts)
    cd = assemble_correction(doc, gaps=[], retrieved={}, validations={})
    originals = [s for s in cd.segments if s.type == "original"]
    assert [s.text for s in originals] == texts          # 逐字全等(immutable)
    assert [s.anchor_idx for s in originals] == [0, 1]   # anchor = 原段 idx
    assert all(s.confidence == "verified" for s in originals)
    assert all(s.sources == [] for s in originals)
    assert cd.original is doc                             # 原 Document 原封帶回


def test_no_source_gap_is_pending_and_still_present():
    """無源 gap:confidence=pending_evidence,且該 supplement 段仍在 segments(不刪)。"""
    doc = _doc(["行政處分之定義。"])
    gap = Gap(question="訴願期間多久?", status="missing", reason="原文未提及")
    cd = assemble_correction(doc, gaps=[gap], retrieved={}, validations={})
    sups = [s for s in cd.segments if s.type == "supplement"]
    assert len(sups) == 1                                 # 保留該段
    assert sups[0].sources == []
    assert sups[0].confidence == "pending_evidence"       # C6:無源 → pending


def test_two_independent_ab_sources_verified():
    """有 2 個獨立 A/B 源且 Validation.verified=True → confidence=verified。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="missing", reason="原文未提及")
    s1 = _src("1", "訴願法第14條", "https://law.moj.gov.tw/a", level="A")
    s2 = _src("2", "立法院議案關係文書", "https://ly.gov.tw/b", level="B")
    retrieved = {q: [s1, s2]}
    validations = {q: Validation(claim=q, sources=[s1, s2], verified=True,
                                 conflict=False, conflict_note=None)}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved, validations=validations)
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "verified"
    assert len(sup.sources) == 2


def test_sources_but_unverified_stays_pending():
    """C6 第二 clause:有源但 verified=False,仍必須 pending_evidence。"""
    doc = _doc(["行政處分之定義。"])
    q = "訴願期間多久?"
    gap = Gap(question=q, status="partial", reason="僅片段")
    s1 = _src("1", "訴願法第14條", "https://law.moj.gov.tw/a", level="A")
    retrieved = {q: [s1]}
    validations = {q: Validation(claim=q, sources=[s1], verified=False,
                                 conflict=False, conflict_note=None)}
    cd = assemble_correction(doc, gaps=[gap], retrieved=retrieved, validations=validations)
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.confidence == "pending_evidence"


def test_anchor_picks_keyword_overlap():
    doc = _doc(["訴願程序相關規定。", "完全無關的天氣內容。"])
    gap = Gap(question="訴願期間多久?", status="missing", reason="")
    cd = assemble_correction(doc, gaps=[gap], retrieved={}, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.anchor_idx == 0        # 與「訴願」重疊之段


def test_anchor_none_when_no_overlap():
    doc = _doc(["天氣晴朗適合出遊。"])
    gap = Gap(question="ABC XYZ?", status="missing", reason="")
    cd = assemble_correction(doc, gaps=[gap], retrieved={}, validations={})
    sup = next(s for s in cd.segments if s.type == "supplement")
    assert sup.anchor_idx is None
```

  **Run:** `pytest -q tests/test_correction.py`
  **Expected (FAIL):** collection error —
  `ModuleNotFoundError: No module named 'note_filler.correction'`(correction.py 尚未建立)。

- [ ] **Step 2 — 實作 correction.py 讓測試轉綠(GREEN)**

```python
# src/note_filler/correction.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:                      # 僅型別提示,執行期零硬耦合(結構化 attr 讀取)
    from note_filler.parse import Document
    from note_filler.gap import Gap
    from note_filler.retrieve.models import Source
    from note_filler.verify import Validation


@dataclass
class Segment:
    type: Literal["original", "supplement"]
    text: str
    anchor_idx: int | None
    sources: list
    confidence: Literal["verified", "pending_evidence"]


@dataclass
class CorrectionDoc:
    original: "Document"
    segments: list


# CJK 逐字 + 英數字詞:粗略關鍵詞集合,供 anchor 重疊比對
_TOKEN = re.compile(r"[A-Za-z0-9]+|[一-鿿]")


def _tokens(s: str) -> set[str]:
    return set(_TOKEN.findall(s))


def _best_anchor(question: str, paragraphs) -> int | None:
    """挑與 question 關鍵詞重疊最多的原文段 idx;全為 0 → None;平手取最小 idx。"""
    q = _tokens(question)
    if not q:
        return None
    best_idx: int | None = None
    best_overlap = 0
    for p in paragraphs:               # paragraphs 已按 idx 遞增
        overlap = len(q & _tokens(p.text))
        if overlap > best_overlap:     # 嚴格大於 → 平手保留先出現(較小 idx)
            best_overlap = overlap
            best_idx = p.idx
    return best_idx


def _supplement_text(gap, sources) -> str:
    """組 supplement 段本文;無源時退回 gap.reason/question(段仍保留待補)。"""
    if sources:
        body = "；".join(s.content for s in sources)
    else:
        body = gap.reason or gap.question
    return f"針對「{gap.question}」補充:{body}"


def assemble_correction(doc, gaps, retrieved, validations) -> CorrectionDoc:
    segments: list[Segment] = []

    # 1) 原文段:逐字保留(immutable),絕不改一字;overlay 不刪原文
    for p in doc.paragraphs:
        segments.append(
            Segment(
                type="original",
                text=p.text,           # 逐字等於原 Paragraph.text
                anchor_idx=p.idx,
                sources=[],
                confidence="verified",
            )
        )

    # 2) 每個 gap 一個 supplement 段(overlay 疊加)
    for gap in gaps:
        sources = list(retrieved.get(gap.question, []))
        val = validations.get(gap.question)
        verified = bool(val and val.verified)
        # C6 不變式:無源 或 未 verified → pending_evidence(保留該段不刪)
        confidence = "verified" if (sources and verified) else "pending_evidence"
        segments.append(
            Segment(
                type="supplement",
                text=_supplement_text(gap, sources),
                anchor_idx=_best_anchor(gap.question, doc.paragraphs),
                sources=sources,
                confidence=confidence,
            )
        )

    return CorrectionDoc(original=doc, segments=segments)
```

  **Run:** `pytest -q tests/test_correction.py`
  **Expected (PASS):** `7 passed`(originals 逐字全等、無源 gap pending 且保留、2 獨立 A/B 源 verified、有源未驗仍 pending、anchor 命中與 None 各就位)。

- [ ] **Step 3 — smoke test(整合面 sanity,真 code 跑一遍組裝路徑)**

```python
# 於 REPL 或臨時 scripts/smoke_correction.py 執行
from note_filler.parse import Document, Paragraph
from note_filler.gap import Gap
from note_filler.retrieve.models import Source
from note_filler.verify import Validation
from note_filler.correction import assemble_correction

doc = Document(
    source_path="demo.docx",
    paragraphs=(Paragraph(0, "訴願程序之相關規定。"),),
    full_text="訴願程序之相關規定。",
)
q = "訴願期間多久?"
s1 = Source("1", "訴願法第14條", "https://law.moj.gov.tw/a", "A",
            "訴願應於行政處分達到次日起30日內提起。", "2026-07-15", None, 0.4)
s2 = Source("2", "立法院議案關係文書", "https://ly.gov.tw/b", "B",
            "訴願期間相關立法說明。", "2026-07-15", None, 0.5)
cd = assemble_correction(
    doc,
    gaps=[Gap(q, "missing", "原文未載期間")],
    retrieved={q: [s1, s2]},
    validations={q: Validation(q, [s1, s2], True, False, None)},
)
orig = [s for s in cd.segments if s.type == "original"]
sup = [s for s in cd.segments if s.type == "supplement"]
assert orig[0].text == "訴願程序之相關規定。"        # immutable
assert sup[0].confidence == "verified"              # 2 獨立 A/B 源
assert sup[0].anchor_idx == 0                        # 錨到「訴願」段
print("smoke ok:", [(s.type, s.confidence, s.anchor_idx) for s in cd.segments])
```

  **Run:** `python scripts/smoke_correction.py`
  **Expected (PASS):**
  `smoke ok: [('original', 'verified', 0), ('supplement', 'verified', 0)]`
  (無 AssertionError;原文逐字保留、supplement 驗證通過並正確錨定)。

- [ ] **Commit(conventional 繁中)**

```
feat(correction): 訂正稿組裝與無來源閘(自建②)

- 新增 Segment / CorrectionDoc / assemble_correction
- 原文段逐字 overlay 保留,immutable 不改動原稿
- 落實 C6 不變式:supplement 無源或未 verified → pending_evidence 且保留該段
- 2 個獨立 A/B 源且 Validation.verified 才標 verified
- anchor_idx 以關鍵詞重疊挑最相關原文段,無重疊回 None
- 補 tests/test_correction.py 全綠
```

---

### Task 13: Pipeline 串接(pipeline.py)

**Files:**
- Create `src/note_filler/pipeline.py`
- Test `tests/test_pipeline.py`

**Interfaces:**

Consumes(exact 簽名 + 正確 task 歸屬):
- `parse_note(path: str) -> Document`(T2)
- `detect_domain(text: str, llm: LLMClient) -> Domain`(T3)
- `generate_questions(full_text: str, domain: Domain, llm: LLMClient) -> list[str]`(T4)
- `detect_gaps(questions: list[str], note_text: str, llm: LLMClient) -> list[Gap]`(T5)
- `retrieve_for_gap(gap: Gap, domain: Domain, twinkle: TwinkleClient) -> list[Source]`(T9)
- `cross_validate(claim: str, sources: list) -> Validation`(T10)
- `check_law_citations(text: str, lookup: LawLookup) -> list[dict]`(T8)
- `assemble_correction(doc: Document, gaps: list, retrieved: dict, validations: dict) -> CorrectionDoc`(T12)
- `LawLookup`(T8)、`TwinkleClient`(T7)、`LLMClient`(型別鎖定)

Produces:
- `run_pipeline(path: str, llm: LLMClient, twinkle: TwinkleClient, law: LawLookup) -> CorrectionDoc`

> 匯入路徑一律以文件開頭「正本模組落點表」為唯一正本(`note_filler.parse` / `domain` / `questions` / `gap` / `retrieve` / `retrieve.models` / `retrieve.twinkle` / `verify` / `knowledge.law_citation_check` / `correction` / `llm`);函式邏輯不動。

---

- [ ] **Step 1 — 先寫失敗單元測試(C1 恰餵 3 canned + C6 不變式)**

  `tests/test_pipeline.py`:
  ```python
  import json
  import pytest
  from docx import Document as DocxDocument

  from note_filler.llm import FakeLLM
  from note_filler.retrieve.models import Source          # Source 定義處(T6/型別鎖定)
  from note_filler.pipeline import run_pipeline


  @pytest.fixture
  def note_path(tmp_path):
      """用 python-docx 現造一份真 .docx,避免依賴外部檔。"""
      p = tmp_path / "note.docx"
      d = DocxDocument()
      d.add_paragraph("行政程序法要求行政行為應遵守正當程序。")
      d.add_paragraph("本筆記僅記錄部分重點,尚未展開。")
      d.save(str(p))
      return str(p)


  class FakeTwinkle:
      """依序回傳每個 gap 的來源批次;不打真網路。"""
      def __init__(self, batches):
          self.batches = list(batches)
          self.queries = []

      def search(self, query, n=3):
          self.queries.append(query)
          return self.batches.pop(0) if self.batches else []


  class FakeLaw:
      def lookup_article(self, law_name, article_no): return None
      def law_exists(self, name): return True
      def fuzzy_find_law(self, name): return None


  def _src(sid, title, url, level):
      return Source(
          id=sid, title=title, url=url, level=level,
          content=f"{title} 官方結構化記錄全文……",
          fetched_date="2026-07-15", doc_date="2026-01-01", distance=0.6,
      )


  def test_run_pipeline_invariant(note_path):
      # C1:FakeLLM 恰餵 3 個 canned,依序=domain 標籤字串、換行問題字串、gaps JSON 陣列字串
      llm = FakeLLM([
          "admin",                                              # detect_domain 取單一標籤
          "正當程序的要件為何?\n聽證程序如何進行?",              # generate_questions 逐行解析
          json.dumps([                                          # detect_gaps 一次回陣列
              {"question": "正當程序的要件為何?", "status": "missing", "reason": "筆記未展開"},
              {"question": "聽證程序如何進行?", "status": "missing", "reason": "筆記未提及"},
          ], ensure_ascii=False),
      ])
      twinkle = FakeTwinkle([
          [],                                                   # gap1 無來源 → pending_evidence
          [_src("s1", "行政院公報", "https://a", "A"),
           _src("s2", "立法院議案", "https://b", "B")],          # gap2 兩獨立 A/B → verified
      ])

      doc = run_pipeline(note_path, llm, twinkle, FakeLaw())

      supplements = [s for s in doc.segments if s.type == "supplement"]
      assert supplements, "應至少有一個補充段"

      # C6 不變式:斷言「每個無源 supplement 的 confidence==pending_evidence」,
      # 不斷言「pending 一定存在」;有 >=2 獨立 A/B 源則為 verified。
      for seg in supplements:
          if not seg.sources:
              assert seg.confidence == "pending_evidence"
          elif len(seg.sources) >= 2:
              assert seg.confidence == "verified"

      # 每個 gap 恰觸發一次 retrieve;若 LLM 被呼叫第 4 次,FakeLLM 會 IndexError 使測試自然失敗
      assert len(twinkle.queries) == 2
  ```

  `src/note_filler/pipeline.py`(先放骨架讓測試紅):
  ```python
  from __future__ import annotations


  def run_pipeline(path, llm, twinkle, law):
      raise NotImplementedError
  ```

  **Run:** `pytest tests/test_pipeline.py::test_run_pipeline_invariant -q`
  **Expected(FAIL):** `NotImplementedError`(run_pipeline 尚未實作)

---

- [ ] **Step 2 — 實作 run_pipeline 核心串接,使測試轉綠**

  `src/note_filler/pipeline.py`:
  ```python
  from __future__ import annotations

  from .parse import parse_note                 # T2
  from .domain import detect_domain              # T3
  from .questions import generate_questions      # T4
  from .gap import detect_gaps                   # T5
  from .retrieve import retrieve_for_gap          # T9
  from .verify import cross_validate            # T10
  from .knowledge.law_citation_check import check_law_citations   # T8
  from .correction import assemble_correction       # T12


  def run_pipeline(path, llm, twinkle, law):
      """串 parse→domain→questions→gaps→(每 gap)retrieve→cross_validate→assemble。
      law 領域對補充段再跑 check_law_citations(C2 簽名 text=)。
      回傳 CorrectionDoc。
      """
      doc = parse_note(path)                                  # T2
      domain = detect_domain(doc.full_text, llm)             # T3(1 次 llm.complete)
      questions = generate_questions(doc.full_text, domain, llm)  # T4(1 次 llm.complete)
      gaps = detect_gaps(questions, doc.full_text, llm)      # T5(1 次 llm.complete)

      retrieved: dict[str, list] = {}
      validations: dict = {}
      for gap in gaps:                                       # 只對 partial/missing gap(T5 已過濾)
          sources = retrieve_for_gap(gap, domain, twinkle)   # T9
          retrieved[gap.question] = sources
          validations[gap.question] = cross_validate(gap.question, sources)  # T10

      correction = assemble_correction(doc, gaps, retrieved, validations)    # T12

      if domain == "law":
          _verify_law_citations(correction, law)

      return correction


  def _verify_law_citations(correction, law):
      """law 領域:對每個補充段跑法規引用檢查;引用之法條在離線庫找不到時,
      保守把該段降為 pending_evidence(C6:只降級、保留不刪,絕不升級)。
      """
      for seg in correction.segments:
          if seg.type != "supplement":
              continue
          findings = check_law_citations(text=seg.text, lookup=law)  # C2:第一參數用 text 名
          if any(f.get("kind") == "article_not_found" for f in findings):
              seg.confidence = "pending_evidence"
  ```

  **Run:** `pytest tests/test_pipeline.py::test_run_pipeline_invariant -q`
  **Expected(PASS):** `1 passed`

---

- [ ] **Step 3 — law 領域確實跑過 check_law_citations(C2 驗證)**

  追加測試至 `tests/test_pipeline.py`:
  ```python
  def test_run_pipeline_law_domain_runs_citation_check(note_path, monkeypatch):
      import note_filler.pipeline as pl

      calls = []
      def fake_check(text, lookup):        # 對齊 C2:關鍵字 text=... 會綁到此參數
          calls.append(text)
          return []                        # 無問題引用 → 不降級
      monkeypatch.setattr(pl, "check_law_citations", fake_check)

      llm = FakeLLM([
          "law",                                                   # domain 標籤
          "民法第184條的構成要件為何?",                             # 換行問題(單行)
          json.dumps([{"question": "民法第184條的構成要件為何?",
                       "status": "missing", "reason": "缺"}], ensure_ascii=False),
      ])
      twinkle = FakeTwinkle([[_src("s1", "法規原文A", "https://a", "A"),
                             _src("s2", "立法院議案B", "https://b", "B")]])

      doc = run_pipeline(note_path, llm, twinkle, FakeLaw())

      supplements = [s for s in doc.segments if s.type == "supplement"]
      # law 領域:每個補充段都經過 check_law_citations(text=...)
      assert len(calls) == len(supplements)
      assert calls, "law 領域至少應跑一次法規引用檢查"
  ```

  **Run:** `pytest tests/test_pipeline.py -q`
  **Expected(PASS):** `2 passed`

---

- [ ] **Step 4 — 真 grok 整合測試(隔離 twinkle,只驗 LLM 串接)**

  追加至 `tests/test_pipeline.py`:
  ```python
  @pytest.mark.integration
  def test_run_pipeline_real_grok(note_path):
      """打真 grok(http://127.0.0.1:8318/v1, grok-4.3);twinkle/law 用 fake 隔離,
      驗 parse→domain→questions→gaps→assemble 整條在真模型輸出下不炸。
      """
      from note_filler.llm import GrokClient

      llm = GrokClient()                        # base_url/model 依鎖定預設
      twinkle = FakeTwinkle([[], [], [], []])   # 每個 gap 都回空,補充段一律 pending_evidence
      doc = run_pipeline(note_path, llm, twinkle, FakeLaw())

      assert doc.original is not None
      assert isinstance(doc.segments, list)
      # 真模型下無源補充仍須守 C6 不變式
      for seg in doc.segments:
          if seg.type == "supplement" and not seg.sources:
              assert seg.confidence == "pending_evidence"
  ```

  **Run(單元,預設跳過 integration):** `pytest tests/test_pipeline.py -q -m "not integration"`
  **Expected(PASS):** `2 passed`(整合測試被 deselect)
  **Run(整合,需 8318 在):** `pytest tests/test_pipeline.py -q -m integration`
  **Expected(PASS):** `1 passed`

---

- [ ] **Commit**
  ```
  feat(pipeline): 串接 parse→domain→questions→gaps→retrieve→驗證→assemble 主流程

  - run_pipeline 依 C1 對 llm.complete 恰三次呼叫(domain/questions/gaps)
  - check_law_citations 以 text= 傳入(C2);law 領域對補充段跑引用檢查
  - 單元測試以 FakeLLM 三 canned + FakeTwinkle 覆蓋 C6 不變式,另附真 grok 整合測試
  ```

---

### Task 14: 匯出(export.py)

**Files:**
- Create `src/note_filler/export.py`
- Test `tests/test_export.py`

**Interfaces:**
- Consumes:
  - `Document(source_path:str, paragraphs:tuple, full_text:str)`（T2）
  - `Source(id, title, url, level, content, fetched_date, doc_date, distance)`（T6）
  - `Segment(type, text, anchor_idx, sources, confidence)`、`CorrectionDoc(original, segments)`（T12）
  - `def build_reference_lines(sources: list) -> str`（T11；已含 C7 之 Date，每筆 `doc_date` 優先否則 `fetched_date`，行首格式 `"[^{i}]: [Level {level}] ..."`）
- Produces:
  - `def to_json(doc: CorrectionDoc) -> dict`
  - `def to_markdown(doc: CorrectionDoc) -> str`

> 說明：本模組不呼叫 LLM，故無 `LLMClient` 注入、無 `@pytest.mark.integration` 真 grok 測試。footnote 編號在 body 與 `build_reference_lines(cited)` 之間以「被引用順序」對齊：每個 supplement 依序把自己的 sources 逐一計數 `[^n]`，並蒐集到 `cited`，最後把 `cited`（同順序）交給 T11 的 `build_reference_lines` 重新列 `[^1..n]`，兩邊編號一致。C6 不變式下 sources 空的 supplement 必為 `pending_evidence`，該段不產生任何 footnote。

---

- [ ] **Step 1 (RED)：先寫 `to_json` 測試**

  建立 `tests/test_export.py`（含共用 fixture）：

  ```python
  import json

  import pytest

  from note_filler.parse import Document, Paragraph
  from note_filler.correction import CorrectionDoc, Segment
  from note_filler.retrieve.models import Source
  from note_filler.export import to_json, to_markdown


  def _sample_doc() -> CorrectionDoc:
      original = Document(
          source_path="/tmp/note.docx",
          paragraphs=(Paragraph(idx=0, text="原文第一段。"),),
          full_text="原文第一段。",
      )
      src_a = Source(
          id="s1",
          title="行政程序法第92條",
          url="https://law.moj.gov.tw/LawClass/LawSingle.aspx?a=92",
          level="A",
          content="行政程序法第92條：本法所稱行政處分，係指……全文。",
          fetched_date="2026-07-01",
          doc_date="2005-12-28",
          distance=0.10,
      )
      src_b = Source(
          id="s2",
          title="立法院第11屆第1會期議案關係文書",
          url="https://ppg.ly.gov.tw/ppg/bills/1101/text",
          level="B",
          content="議案關係文書全文……",
          fetched_date="2026-07-02",
          doc_date=None,
          distance=0.30,
      )
      segments = [
          Segment(
              type="original",
              text="原文第一段。",
              anchor_idx=0,
              sources=[],
              confidence="verified",
          ),
          Segment(
              type="supplement",
              text="依行政程序法第92條，行政處分係指行政機關就公法上具體事件所為之決定。",
              anchor_idx=0,
              sources=[src_a, src_b],
              confidence="verified",
          ),
          Segment(
              type="supplement",
              text="關於施行細節仍待查證。",
              anchor_idx=0,
              sources=[],
              confidence="pending_evidence",
          ),
      ]
      return CorrectionDoc(original=original, segments=segments)


  def test_to_json_serializes_segments() -> None:
      data = to_json(_sample_doc())

      assert data["source_path"] == "/tmp/note.docx"
      segs = data["segments"]
      assert len(segs) == 3

      # 原文段
      assert segs[0]["type"] == "original"
      assert segs[0]["text"] == "原文第一段。"
      assert segs[0]["sources"] == []

      # verified supplement，帶兩個來源，Level 保留
      assert segs[1]["type"] == "supplement"
      assert segs[1]["confidence"] == "verified"
      assert [s["level"] for s in segs[1]["sources"]] == ["A", "B"]
      assert segs[1]["sources"][0]["fetched_date"] == "2026-07-01"

      # pending_evidence supplement，sources 空(C6 不變式)
      assert segs[2]["confidence"] == "pending_evidence"
      assert segs[2]["sources"] == []

      # 整份可被 json 序列化(不丟例外)
      json.dumps(data, ensure_ascii=False)
  ```

  **Run:** `pytest tests/test_export.py -q`
  **Expected (FAIL):** `ModuleNotFoundError: No module named 'note_filler.export'`（`export.py` 尚未建立）。

---

- [ ] **Step 2 (GREEN)：實作 `to_json`**

  建立 `src/note_filler/export.py`：

  ```python
  from __future__ import annotations

  from dataclasses import asdict

  from note_filler.citation_formatter import build_reference_lines
  from note_filler.correction import CorrectionDoc
  from note_filler.retrieve.models import Source


  def _source_to_dict(src: Source) -> dict:
      """Source dataclass → 純 dict(含 fetched_date/doc_date/level/distance)。"""
      return asdict(src)


  def to_json(doc: CorrectionDoc) -> dict:
      """序列化整份 CorrectionDoc；原文 immutable，僅讀不改。"""
      return {
          "source_path": doc.original.source_path,
          "full_text": doc.original.full_text,
          "segments": [
              {
                  "type": seg.type,
                  "text": seg.text,
                  "anchor_idx": seg.anchor_idx,
                  "confidence": seg.confidence,
                  "sources": [_source_to_dict(s) for s in seg.sources],
              }
              for seg in doc.segments
          ],
      }
  ```

  **Run:** `pytest tests/test_export.py::test_to_json_serializes_segments -q`
  **Expected (PASS):** `1 passed`。

---

- [ ] **Step 3 (RED)：再寫 `to_markdown` 格式鎖定測試（對齊 C3/C7）**

  在 `tests/test_export.py` 追加：

  ```python
  def test_to_markdown_format_locked() -> None:
      md = to_markdown(_sample_doc())

      # 原文段原樣輸出
      assert "原文第一段。" in md

      # C3：supplement 段 "> 【補充】{text}" 後接 [^n]
      assert "> 【補充】依行政程序法第92條" in md
      assert (
          "> 【補充】依行政程序法第92條，行政處分係指行政機關就公法上具體事件所為之決定。[^1][^2]"
          in md
      )

      # C3：pending_evidence 段【補充】後加 ⚠待補證
      assert "> 【補充】⚠待補證 關於施行細節仍待查證。" in md
      assert "⚠待補證" in md

      # 文末參考區塊(來自 T11 build_reference_lines)：帶 Level 與 Date
      assert "[^1]: [Level A]" in md          # 第一筆為 Level A
      assert "2005-12-28" in md               # C7：src_a doc_date 優先
      assert "2026-07-02" in md               # C7：src_b doc_date=None → fetched_date fallback


  def test_to_markdown_pending_segment_has_no_footnote() -> None:
      md = to_markdown(_sample_doc())
      pending_lines = [ln for ln in md.splitlines() if "待補證" in ln]
      assert len(pending_lines) == 1
      # sources 空 → 該段不產生任何 [^n] 標記
      assert "[^" not in pending_lines[0]
  ```

  **Run:** `pytest tests/test_export.py -q`
  **Expected (FAIL):** `AttributeError: module 'note_filler.export' has no attribute 'to_markdown'`（或 import 失敗）。

---

- [ ] **Step 4 (GREEN)：實作 `to_markdown`（鎖定 C3 格式、footnote 與參考區塊對齊）**

  在 `src/note_filler/export.py` 追加：

  ```python
  def to_markdown(doc: CorrectionDoc) -> str:
      """
      C3 鎖定格式：
        - original 段：原樣輸出(原文 immutable)。
        - supplement 段：'> 【補充】{text}' 後接 [^n] 註腳(每個來源一個)。
        - pending_evidence 段：【補充】後加 '⚠待補證 '(sources 空則無 footnote)。
      文末以 build_reference_lines(所有被引用 sources) 產參考區塊(C7 內含 Date)。
      footnote 編號與 cited 順序一致，交給 T11 重新列 [^1..n]。
      """
      body: list[str] = []
      cited: list[Source] = []
      counter = 0

      for seg in doc.segments:
          if seg.type == "original":
              body.append(seg.text)
              continue

          # supplement：依序為每個來源配一個 footnote，並蒐集到 cited
          marks = ""
          for src in seg.sources:
              counter += 1
              cited.append(src)
              marks += f"[^{counter}]"

          prefix = "> 【補充】"
          if seg.confidence == "pending_evidence":
              prefix += "⚠待補證 "
          body.append(f"{prefix}{seg.text}{marks}")

      md = "\n\n".join(body)

      # 文末參考區塊：只放實際被引用(有進 body 的)sources，順序即 footnote 順序
      ref_block = build_reference_lines(cited)
      if ref_block:
          md = f"{md}\n\n{ref_block}"

      return md
  ```

  **Run:** `pytest tests/test_export.py -q`
  **Expected (PASS):** `3 passed`（`to_json` + 兩條 `to_markdown` 測試全綠）。

  > 前置依賴檢查：本步依賴 T11 `note_filler.citation_formatter.build_reference_lines(sources)` 已完成且每行格式為 `"[^{i}]: [Level {level}] {title} | URL: {url} | Date: {doc_date or fetched_date}"`。若 T11 尚未產出 `[^1]: [Level A]` / Date 欄位，先回補 T11，不得在 T14 自訂參考區塊格式（C3 規定 T16 端到端只 import 本 `to_markdown`，故格式正本在此）。

---

- [ ] **Step 5：Commit（conventional，繁中）**

  ```bash
  git add src/note_filler/export.py tests/test_export.py
  git commit -m "feat(export): 實作 to_json/to_markdown 匯出，鎖定補充段與參考區塊格式"
  ```

  提交前先 `git diff --cached --name-only` 核對僅含上述兩檔（硬規則 10）。

---

### Task 15: 薄 Web UI(app/server.py)

**Files:**
- Create: `app/__init__.py`(空檔,讓 `import app.server` 可用)
- Create: `app/server.py`
- Create: `app/templates/index.html`
- Create: `app/templates/result.html`
- Modify: `pyproject.toml`(新增 `fastapi`、`jinja2`、`python-multipart`,dev 加 `httpx`)
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes(前置 task 的 exact 簽名):
  - `run_pipeline(path: str, llm: LLMClient, twinkle: TwinkleClient, law: LawLookup) -> CorrectionDoc`(T13)
  - `to_markdown(doc: CorrectionDoc) -> str`(T14)
  - `to_json(doc: CorrectionDoc) -> dict`(T14)
  - `GrokClient()`(T1)、`TwinkleClient(token, ...)`(T7)、`LawLookup(db_path)`(T8)
  - 型別:`CorrectionDoc(original: Document, segments: list[Segment])`、`Segment(type, text, anchor_idx, sources, confidence)`、`Document(source_path, paragraphs, full_text)`、`Paragraph(idx, text)`、`Source(id, title, url, level, content, fetched_date, doc_date, distance)`
- Produces(本 task 對外):
  - `app: fastapi.FastAPI`(模組級單例)
  - `GET /` → 200 HTML 上傳表單
  - `POST /run`(multipart `file`)→ HTML 雙欄訂正稿(supplement 高亮、pending 警示、sources 可展開)
  - `GET /export` → `text/markdown` 附件下載(依 `app.state.last_doc`)
  - `_build_clients() -> tuple[GrokClient, TwinkleClient, LawLookup]`(可被測試 monkeypatch)

---

- [ ] **Step 1: 建立 app 套件骨架與相依**

先讓 `app` 成為可 import 的套件並登記相依。建立空的 `app/__init__.py`:

```python
# app/__init__.py
```

在 `pyproject.toml` 的 `[project].dependencies` 加入 UI 相依(檔案上傳需要 `python-multipart`):

```toml
dependencies = [
    "python-docx>=1.1",
    "fastapi>=0.110",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "httpx>=0.27",
]
```

Run:
```
python -m pip install -e ".[dev]"
```
Expected: 安裝成功,`python -c "import fastapi, jinja2, httpx, multipart"` 無 ImportError。

---

- [ ] **Step 2: Write the failing test — GET / 回上傳表單**

```python
# tests/test_server.py
from fastapi.testclient import TestClient

import app.server as server


def test_index_returns_upload_form():
    client = TestClient(server.app)
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    assert 'action="/run"' in body
    assert 'enctype="multipart/form-data"' in body
    assert 'type="file"' in body
    assert 'name="file"' in body
```

---

- [ ] **Step 3: Run test to verify it fails**

Run:
```
pytest tests/test_server.py::test_index_returns_upload_form -v
```
Expected: FAIL —— `ModuleNotFoundError: No module named 'app.server'`(server.py 尚未建立)。

---

- [ ] **Step 4: Write minimal implementation — server.py(只做 GET /)+ index.html**

```python
# app/server.py
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from note_filler.export import to_markdown
from note_filler.llm import GrokClient
from note_filler.pipeline import run_pipeline
from note_filler.knowledge.law_lookup import LawLookup
from note_filler.retrieve.twinkle import TwinkleClient

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
DB_PATH = os.environ.get(
    "NOTE_FILLER_DB", str(BASE_DIR.parent / "data" / "law_index.db")
)

app = FastAPI(title="筆記補齊")
app.state.last_doc = None


def _build_clients() -> tuple[GrokClient, TwinkleClient, LawLookup]:
    """建立三個注入用 client;測試會 monkeypatch 掉以避免真連線/開 DB。"""
    llm = GrokClient()
    twinkle = TwinkleClient(token=os.environ.get("TWINKLE_HUB_TOKEN", ""))
    law = LawLookup(DB_PATH)
    return llm, twinkle, law


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse("index.html", {"request": request})
```

```html
<!-- app/templates/index.html -->
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>筆記補齊</title>
</head>
<body>
  <h1>筆記補齊</h1>
  <p>上傳筆記(.txt 或 .docx),系統將保留原稿、以差異方式補齊。</p>
  <form action="/run" method="post" enctype="multipart/form-data">
    <input type="file" name="file" accept=".txt,.docx" required>
    <button type="submit">開始補齊</button>
  </form>
</body>
</html>
```

---

- [ ] **Step 5: Run test to verify it passes**

Run:
```
pytest tests/test_server.py::test_index_returns_upload_form -v
```
Expected: PASS。

---

- [ ] **Step 6: Write the failing test — POST /run 回雙欄訂正稿(高亮 + pending + 來源)**

```python
# tests/test_server.py(追加)
from note_filler.parse import Document, Paragraph
from note_filler.correction import Segment, CorrectionDoc
from note_filler.retrieve.models import Source


def _fixed_doc() -> CorrectionDoc:
    para = Paragraph(idx=0, text="行政處分之定義。")
    doc = Document(
        source_path="/tmp/note.txt",
        paragraphs=(para,),
        full_text="行政處分之定義。",
    )
    src = Source(
        id="s1",
        title="行政程序法第92條",
        url="https://law.moj.gov.tw/LawClass/LawSingle.aspx?a=92",
        level="A",
        content="本法所稱行政處分,係指行政機關就公法上具體事件所為之決定...",
        fetched_date="2026-07-15",
        doc_date=None,
        distance=0.12,
    )
    seg_original = Segment(
        type="original",
        text="行政處分之定義。",
        anchor_idx=None,
        sources=[],
        confidence="verified",
    )
    seg_supp_ok = Segment(
        type="supplement",
        text="行政處分係指行政機關就公法上具體事件所為之單方決定。",
        anchor_idx=0,
        sources=[src],
        confidence="verified",
    )
    seg_supp_pending = Segment(
        type="supplement",
        text="另有學說補充,惟目前無獨立來源。",
        anchor_idx=0,
        sources=[],
        confidence="pending_evidence",
    )
    return CorrectionDoc(
        original=doc,
        segments=[seg_original, seg_supp_ok, seg_supp_pending],
    )


def test_run_renders_two_columns(monkeypatch):
    doc = _fixed_doc()
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(
        server, "run_pipeline", lambda path, llm, twinkle, law: doc
    )
    client = TestClient(server.app)
    r = client.post(
        "/run",
        files={"file": ("note.txt", b"hello world", "text/plain")},
    )
    assert r.status_code == 200
    body = r.text
    # 左欄原稿
    assert "行政處分之定義。" in body
    # 右欄 supplement 高亮
    assert 'class="supplement"' in body
    assert "行政處分係指行政機關就公法上具體事件所為之單方決定。" in body
    # 有來源時可展開,且標 Level
    assert "[Level A]" in body
    assert "行政程序法第92條" in body
    # 無來源 supplement 標 pending 警示
    assert 'class="pending"' in body
    assert "待補依據" in body
```

---

- [ ] **Step 7: Run test to verify it fails**

Run:
```
pytest tests/test_server.py::test_run_renders_two_columns -v
```
Expected: FAIL —— `405 Method Not Allowed`(尚無 `POST /run` 路由,或 `result.html` 不存在導致 TemplateNotFound)。

---

- [ ] **Step 8: Write minimal implementation — /run 路由 + result.html**

在 `app/server.py` 的 `index` 函式後追加 `/run`:

```python
# app/server.py(追加於 index 之後)
@app.post("/run", response_class=HTMLResponse)
async def run(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    suffix = Path(file.filename or "note.txt").suffix or ".txt"
    data = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    llm, twinkle, law = _build_clients()
    doc = run_pipeline(tmp_path, llm, twinkle, law)
    app.state.last_doc = doc  # 供 /export 使用
    return TEMPLATES.TemplateResponse(
        "result.html", {"request": request, "doc": doc}
    )
```

```html
<!-- app/templates/result.html -->
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>訂正稿</title>
  <style>
    body { font-family: system-ui, "Microsoft JhengHei", sans-serif; }
    .cols { display: flex; gap: 1rem; align-items: flex-start; }
    .col { flex: 1; border: 1px solid #ccc; padding: 1rem; border-radius: 6px; }
    .col h2 { margin-top: 0; }
    .seg { white-space: pre-wrap; margin: .4rem 0; }
    .supplement {
      background: #fff7d6;
      border-left: 4px solid #e0a800;
      padding: .5rem .75rem;
      margin: .5rem 0;
      border-radius: 4px;
    }
    .pending {
      color: #b00020;
      font-weight: bold;
      margin-left: .5rem;
    }
    details.sources { margin-top: .35rem; font-size: .9em; }
    details.sources ul { margin: .3rem 0 0; padding-left: 1.2rem; }
  </style>
</head>
<body>
  <h1>訂正結果</h1>
  <p><a href="/export">下載 Markdown 訂正稿</a></p>
  <div class="cols">
    <div class="col" id="original">
      <h2>原稿(不可變)</h2>
      {% for p in doc.original.paragraphs %}
      <p class="seg">{{ p.text }}</p>
      {% endfor %}
    </div>
    <div class="col" id="correction">
      <h2>訂正稿</h2>
      {% for seg in doc.segments %}
        {% if seg.type == "supplement" %}
        <div class="supplement">
          <span class="seg">{{ seg.text }}</span>
          {% if seg.confidence == "pending_evidence" %}
          <span class="pending">[待補依據]</span>
          {% endif %}
          {% if seg.sources %}
          <details class="sources">
            <summary>來源({{ seg.sources|length }})</summary>
            <ul>
            {% for s in seg.sources %}
              <li>
                [Level {{ s.level }}] {{ s.title }}
                {% if s.url %} — <a href="{{ s.url }}" target="_blank" rel="noopener">{{ s.url }}</a>{% endif %}
                <br><small>擷取日:{{ s.fetched_date }}{% if s.doc_date %} / 文件日:{{ s.doc_date }}{% endif %}</small>
              </li>
            {% endfor %}
            </ul>
          </details>
          {% endif %}
        </div>
        {% else %}
        <p class="seg">{{ seg.text }}</p>
        {% endif %}
      {% endfor %}
    </div>
  </div>
</body>
</html>
```

---

- [ ] **Step 9: Run test to verify it passes**

Run:
```
pytest tests/test_server.py::test_run_renders_two_columns -v
```
Expected: PASS。

---

- [ ] **Step 10: Write the failing test — GET /export 回 markdown 附件**

```python
# tests/test_server.py(追加)
def test_export_returns_markdown_attachment(monkeypatch):
    doc = _fixed_doc()
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(
        server, "run_pipeline", lambda path, llm, twinkle, law: doc
    )
    client = TestClient(server.app)
    # 先跑一次 /run 讓 last_doc 有值
    client.post("/run", files={"file": ("note.txt", b"x", "text/plain")})
    r = client.get("/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "attachment" in r.headers["content-disposition"]
    assert "correction.md" in r.headers["content-disposition"]
    # markdown 內容來自 to_markdown(doc),應含原文段字樣
    assert "行政處分" in r.text


def test_export_without_run_returns_404():
    server.app.state.last_doc = None  # 重置狀態
    client = TestClient(server.app)
    r = client.get("/export")
    assert r.status_code == 404
```

---

- [ ] **Step 11: Run test to verify it fails**

Run:
```
pytest tests/test_server.py::test_export_returns_markdown_attachment tests/test_server.py::test_export_without_run_returns_404 -v
```
Expected: FAIL —— `404`/`405`(尚無 `GET /export` 路由;`test_export_returns_markdown_attachment` 因無路由取不到 markdown 而失敗)。

---

- [ ] **Step 12: Write minimal implementation — /export 路由**

在 `app/server.py` 的 `run` 函式後追加:

```python
# app/server.py(追加於 run 之後)
@app.get("/export")
def export() -> PlainTextResponse:
    doc = app.state.last_doc
    if doc is None:
        return PlainTextResponse("尚無可匯出的訂正稿,請先上傳筆記。", status_code=404)
    md = to_markdown(doc)
    headers = {"Content-Disposition": 'attachment; filename="correction.md"'}
    return PlainTextResponse(
        md, media_type="text/markdown; charset=utf-8", headers=headers
    )
```

---

- [ ] **Step 13: Run test to verify it passes**

Run:
```
pytest tests/test_server.py -v
```
Expected: PASS(全部 4 個測試通過:index / run / export / export-404)。

---

- [ ] **Step 14: Commit**

```
git add app/__init__.py app/server.py app/templates/index.html app/templates/result.html tests/test_server.py pyproject.toml
git commit -m "feat(ui): 新增 FastAPI 薄 Web UI(上傳/雙欄訂正/Markdown 匯出)

- GET / 上傳表單、POST /run 跑 run_pipeline 產雙欄訂正稿
- supplement 高亮、pending_evidence 標警示、來源可展開
- GET /export 依 last_doc 回 to_markdown 附件下載
- 測試以 TestClient + monkeypatch run_pipeline/_build_clients 驗證,不打真網路"
```

---

### Task 16: 端到端驗收測試(§12)

**Files:**
- Create `tests/test_e2e_acceptance.py`
- Create `tests/fixtures/real_note.txt`

**Interfaces:**

Consumes（exact 簽名、task 編號歸屬）:
- `run_pipeline(path:str, llm:LLMClient, twinkle:TwinkleClient, law:LawLookup) -> CorrectionDoc` — **T13**
- `to_markdown(doc:CorrectionDoc) -> str` — **T14**（依 C3 只 import 呼叫，絕不自訂格式）
- `to_json(doc:CorrectionDoc) -> dict` — **T14**
- `check_law_citations(text: str, lookup: LawLookup) -> list[dict]` — **T8**（C2:第一參數一律 `text`）
- `parse_note(path:str) -> Document`、`Document`、`Paragraph` — **T2**（由 `run_pipeline` 間接使用）
- `class GrokClient(LLMClient)`、`LLMClient`(Protocol)、`FakeLLM` — **T1**
- `class TwinkleClient` — **T7**；`@dataclass Source`（鎖定型別，隨 T7）
- `class LawLookup` — **T8**
- `@dataclass Gap`(T3/T4)、`@dataclass Segment` / `@dataclass CorrectionDoc`(T12/T13) — 唯讀消費，不重建

Produces:
- 涵蓋 spec **§12** 的端到端驗收測試（原稿不可變 / 無來源閘 / 交叉驗證 / 法條存在 / to_markdown 契約），含真實筆記 fixture。分兩層:
  - `test_e2e_structural_invariants`:離線（`FakeLLM` canned + stub twinkle），**永遠跑**，驗結構不變式。
  - `test_e2e_acceptance_real`:`@pytest.mark.integration`,真 grok(127.0.0.1:8318)+真 twinkle(需 `TWINKLE_HUB_TOKEN`+`GOV_AI_ENABLE_TWINKLE_MCP=1`)+真 `LawLookup`,無 token/grok 未上線則 **skip 網路類斷言**,結構類斷言由離線測試照跑。

---

TDD steps:

- [ ] **Step 1（FAIL 步）:寫 `tests/test_e2e_acceptance.py`（fixture 尚未建立）**

```python
"""端到端驗收測試(spec §12)。

§12 硬不變式:
  1. 原稿逐字不可變(diff 只增不改)
  2. 無來源閘 + C6:supplement sources 空 -> confidence == "pending_evidence"
  3. 交叉驗證 C4:supplement verified -> sources 非空且皆 A/B、>=2 獨立來源
  4. 補充法條經 check_law_citations(text=..., lookup) 無 article_not_found
  5. C3:輸出由 T14 to_markdown 產出,含【補充】/⚠待補證/參考區塊(帶日期 C7)
"""
from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import pytest

from note_filler.knowledge.law_citation_check import check_law_citations   # T8
from note_filler.knowledge.law_lookup import LawLookup                     # T8
from note_filler.llm import FakeLLM, GrokClient                  # T1
from note_filler.retrieve.models import Source                             # 鎖定型別(隨 T7)
from note_filler.pipeline import run_pipeline                    # T13
from note_filler.export import to_json, to_markdown             # T14
from note_filler.retrieve.twinkle import TwinkleClient                    # T7

FIXTURE = Path(__file__).parent / "fixtures" / "real_note.txt"
LAW_DB = Path(__file__).resolve().parents[1] / "data" / "law_index.db"


# ---- 環境探測(網路類斷言的 skip 閘) --------------------------------------
def _grok_up(host: str = "127.0.0.1", port: int = 8318) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def _twinkle_ready() -> bool:
    return bool(os.environ.get("TWINKLE_HUB_TOKEN")) and \
        os.environ.get("GOV_AI_ENABLE_TWINKLE_MCP") == "1"


# ---- 共用不變式(結構類,離線與真跑都套用) --------------------------------
def _assert_immutable_original(doc, note_text: str) -> None:
    """§12(1) 原稿逐字不可變:全文與各段皆不得被竄改,只增不改。"""
    assert doc.original.full_text == note_text, "原稿 full_text 被改動"
    for para in doc.original.paragraphs:
        assert para.text in note_text, f"原稿段落被竄改: {para.text!r}"
    for seg in doc.segments:
        if seg.type == "original":
            assert seg.text in note_text, f"original segment 非逐字原文: {seg.text!r}"


def _assert_no_source_gate(doc) -> None:
    """§12(2) 無來源閘 + C6 pending_evidence 不變式(斷言不變式,非「一定存在」)。"""
    for seg in doc.segments:
        if seg.type != "supplement":
            continue
        if not seg.sources:
            assert seg.confidence == "pending_evidence", \
                "sources 空的 supplement 必須 pending_evidence(不得刪除)"
        if seg.confidence == "verified":
            assert seg.sources, "verified supplement 不得無來源"
            assert all(s.level in ("A", "B") for s in seg.sources), \
                "verified 來源必須皆為 A/B 級"


def _assert_law_citations_ok(doc, law: LawLookup) -> None:
    """§12(4) 補充內法條必須真實存在(C2:text 第一參數)。"""
    for seg in doc.segments:
        if seg.type != "supplement":
            continue
        issues = check_law_citations(text=seg.text, lookup=law)
        bad = [i for i in issues if i.get("kind") == "article_not_found"]
        assert not bad, f"補充出現不存在法條: {bad}"


def _assert_markdown_contract(doc) -> None:
    """§12(5)/C3:呼叫 T14 to_markdown,驗鎖定格式標記,不自訂另一套格式。"""
    md = to_markdown(doc)               # C3:直接 import 呼叫 T14
    assert isinstance(md, str) and md
    for seg in doc.segments:
        if seg.type == "original":
            assert seg.text in md, "原文段未原樣輸出"
        else:  # supplement
            assert "> 【補充】" in md, "supplement 未依 C3 格式輸出"
            if seg.confidence == "pending_evidence":
                assert "⚠待補證" in md, "pending_evidence 未標 ⚠待補證"
    # C7:被引用來源的參考區塊須帶日期(doc_date 優先否則 fetched_date)
    cited = [s for seg in doc.segments for s in (seg.sources or [])]
    if cited:
        assert any((s.doc_date or s.fetched_date) in md for s in cited), \
            "參考區塊應含來源日期(doc_date 優先否則 fetched_date)"
    # to_json 亦須可序列化
    assert isinstance(to_json(doc), dict)


# ---- 離線替身:回兩個「獨立 A/B」來源,使 supplement 可被判 verified ----------
class _StubTwinkle:
    """符合 TwinkleClient.search(query, n=3) -> list[Source]。"""

    def __init__(self) -> None:
        today = "2026-07-15"
        self._sources = [
            Source(id="s1", title="行政程序法(全國法規資料庫)",
                   url="https://law.moj.gov.tw/LawClass/A0030055",
                   level="A", content="行政程序法第92條:本法所稱行政處分,係指行政機關就公法上具體事件所為之決定或其他公權力措施。",
                   fetched_date=today, doc_date="2021-01-20", distance=0.62),
            Source(id="s2", title="立法院議案關係文書",
                   url="https://ppg.ly.gov.tw/ppg/bills/2",
                   level="B", content="行政程序法第92條修正說明:釐清行政處分之對外效力。",
                   fetched_date=today, doc_date=None, distance=0.71),
        ]

    def search(self, query: str, n: int = 3):
        return list(self._sources[:n])


# ---- 結構類:永遠跑(不打真網路) -------------------------------------------
@pytest.mark.skipif(not LAW_DB.exists(), reason="缺 data/law_index.db,無法驗離線結構不變式")
def test_e2e_structural_invariants():
    note_text = FIXTURE.read_text(encoding="utf-8")
    law = LawLookup(str(LAW_DB))
    # C1:FakeLLM 恰 3 canned,依序 domain 標籤字串 / 換行問題字串 / gaps JSON 陣列字串
    fake = FakeLLM([
        "law",
        "什麼是行政處分?\n行政程序法第92條的定義為何?\n訴願前置程序為何?",
        json.dumps(
            [{"question": "行政程序法第92條的定義為何?",
              "status": "missing", "reason": "筆記未展開條文定義"}],
            ensure_ascii=False,
        ),
    ])
    doc = run_pipeline(str(FIXTURE), fake, _StubTwinkle(), law)

    _assert_immutable_original(doc, note_text)
    _assert_no_source_gate(doc)
    _assert_law_citations_ok(doc, law)
    _assert_markdown_contract(doc)


# ---- 網路類:真 grok+真 twinkle+真 law;無 token/未上線則 skip --------------
@pytest.mark.integration
def test_e2e_acceptance_real():
    note_text = FIXTURE.read_text(encoding="utf-8")
    if not LAW_DB.exists():
        pytest.skip("缺 data/law_index.db")
    law = LawLookup(str(LAW_DB))

    if not (_grok_up() and _twinkle_ready()):
        pytest.skip(
            "grok proxy 未上線或無 TWINKLE_HUB_TOKEN/GOV_AI_ENABLE_TWINKLE_MCP;"
            "網路類斷言略過(結構不變式見 test_e2e_structural_invariants)"
        )

    llm = GrokClient()                                    # 127.0.0.1:8318 grok-4.3
    twinkle = TwinkleClient(token=os.environ["TWINKLE_HUB_TOKEN"])
    doc = run_pipeline(str(FIXTURE), llm, twinkle, law)

    # 結構不變式:真跑亦須成立
    _assert_immutable_original(doc, note_text)
    _assert_no_source_gate(doc)
    _assert_law_citations_ok(doc, law)
    _assert_markdown_contract(doc)

    # 網路類斷言:真跑應偵測 gap 產生補充;verified 者須 >=2 獨立 A/B(C4)
    supplements = [s for s in doc.segments if s.type == "supplement"]
    assert supplements, "真跑應偵測到 gap 並產生補充段"
    for seg in supplements:
        if seg.confidence == "verified":
            urls = {s.url for s in seg.sources}
            titles = {s.title for s in seg.sources}  # 機關/文件標題
            assert len(urls) >= 2 and len(titles) >= 2, \
                "verified 需 >=2 個 url 不同且 title(機關)不同的獨立 A/B 來源"
            assert all(s.level in ("A", "B") for s in seg.sources)
```

Run:
```bash
python -m pytest tests/test_e2e_acceptance.py -q
```
Expected(FAIL):
```
FileNotFoundError: ...tests/fixtures/real_note.txt
========================= 2 errors in 0.xx s =========================
```
（fixture 尚未建立,`FIXTURE.read_text` 於 collection/setup 即拋錯。）

- [ ] **Step 2（PASS 步）:建 `tests/fixtures/real_note.txt`（真實法科筆記,含真實存在法條）**

```text
行政法重點筆記 — 行政處分

一、行政處分之定義
行政程序法第92條規定,行政處分係指行政機關就公法上具體事件所為之決定或其他公權力措施,而對外直接發生法律效果之單方行政行為。

二、行政處分之種類
依相對人是否特定,可分為一般處分與個別處分;一般處分之相對人雖非特定,惟依一般性特徵可得確定。

三、救濟途徑
人民對違法或不當之行政處分,得依訴願法提起訴願;對訴願決定不服者,得依法提起行政訴訟。
```

Run（無 token / grok 未上線,驗結構類照跑、網路類 skip）:
```bash
python -m pytest tests/test_e2e_acceptance.py -q
```
Expected(PASS):
```
tests/test_e2e_acceptance.py::test_e2e_structural_invariants PASSED
tests/test_e2e_acceptance.py::test_e2e_acceptance_real SKIPPED (grok proxy 未上線或無 TWINKLE_HUB_TOKEN...)
==================== 1 passed, 1 skipped in 0.xx s ====================
```

- [ ] **Step 3（整合 PASS 步）:真 grok + 真 twinkle 全鏈跑真實筆記**

Run（先確認 8318 在線;設 twinkle env,只跑 integration 標記）:
```bash
GOV_AI_ENABLE_TWINKLE_MCP=1 TWINKLE_HUB_TOKEN="<你的 token>" \
  python -m pytest tests/test_e2e_acceptance.py -q -m integration
```
Expected(PASS):
```
tests/test_e2e_acceptance.py::test_e2e_acceptance_real PASSED
========================= 1 passed in X.xx s =========================
```
（驗:原稿逐字不變、無來源閘→pending_evidence 不變式成立、verified 段皆 >=2 獨立 A/B、補充法條無 article_not_found、輸出由 T14 to_markdown 產出並帶日期。）

- [ ] **Commit**

```bash
git add tests/test_e2e_acceptance.py tests/fixtures/real_note.txt
git commit -m "test(e2e): 新增 §12 端到端驗收測試與真實筆記 fixture

離線結構不變式(FakeLLM+stub twinkle)永遠跑,整合真 grok+真 twinkle 標 integration;
斷言原稿不可變、無來源閘 pending_evidence、交叉驗證 >=2 獨立 A/B、
補充法條無 article_not_found,輸出契約由 T14 to_markdown 提供。"
```
