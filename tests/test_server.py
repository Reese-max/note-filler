import pytest

import app.server as server

from note_filler.parse import Document, Paragraph
from note_filler.correction import Segment, CorrectionDoc
from note_filler.retrieve.models import Source


@pytest.mark.anyio
async def test_index_returns_upload_form(async_client):
    r = await async_client.get("/")
    assert r.status_code == 200
    body = r.text
    assert 'action="/run"' in body
    assert 'enctype="multipart/form-data"' in body
    assert 'type="file"' in body
    assert 'name="file"' in body


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


@pytest.mark.anyio
async def test_run_renders_two_columns(async_client, monkeypatch):
    doc = _fixed_doc()
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(
        server, "run_pipeline", lambda path, llm, twinkle, law: doc
    )
    r = await async_client.post(
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


@pytest.mark.anyio
async def test_export_returns_markdown_attachment(async_client, monkeypatch):
    doc = _fixed_doc()
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(
        server, "run_pipeline", lambda path, llm, twinkle, law: doc
    )
    # 先跑一次 /run 讓 last_doc 有值
    await async_client.post("/run", files={"file": ("note.txt", b"x", "text/plain")})
    r = await async_client.get("/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "attachment" in r.headers["content-disposition"]
    assert "correction.md" in r.headers["content-disposition"]
    # markdown 內容來自 to_markdown(doc),應含原文段字樣
    assert "行政處分" in r.text


@pytest.mark.anyio
async def test_export_without_run_returns_404(async_client):
    server.app.state.last_doc = None  # 重置狀態
    r = await async_client.get("/export")
    assert r.status_code == 404
