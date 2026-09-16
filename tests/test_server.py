import re

import pytest

import app.server as server

from note_filler.parse import Document, Paragraph
from note_filler.correction import Segment, CorrectionDoc, build_related_knowledge
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
        anchor_idx=0,
        sources=[],
        confidence="verified",
        traceability=[
            {"kind": "original_input", "id": "/tmp/note.txt", "paragraph_idx": 0}
        ],
        functional_gap="",
        user_value="",
        argument_id="",
    )
    seg_supp_ok = Segment(
        type="supplement",
        text="行政處分係指行政機關就公法上具體事件所為之單方決定。[^1]",
        anchor_idx=0,
        sources=[src],
        confidence="verified",
        traceability=[{"kind": "source", "id": "s1"}],
        citation_spans=[{
            "source_id": "s1",
            "span_start": len("行政處分係指行政機關就公法上具體事件所為之單方決定。"),
            "span_end": len("行政處分係指行政機關就公法上具體事件所為之單方決定。") + 4,
            "marker_text": "[^1]",
        }],
        functional_gap="原稿未定義行政處分",
        user_value="讓讀者辨識行政處分的適用範圍",
        related_knowledge=build_related_knowledge(
            knowledge_body="行政處分係指行政機關就公法上具體事件所為之單方決定。",
            functional_gap="原稿未定義行政處分",
            user_value="讓讀者辨識行政處分的適用範圍",
        ),
        argument_id="argument:0",
        angle_type="definition",
        angle_labels=["definition", "functional_gap", "user_value"],
        angle_key="definition:行政處分之定義",
    )
    seg_supp_pending = Segment(
        type="supplement",
        text="另有學說補充,惟目前無獨立來源。",
        anchor_idx=0,
        sources=[],
        confidence="pending_evidence",
        traceability=[
            {
                "kind": "processing_record",
                "id": "gap:1",
                "question": "另有學說補充？",
                "outcome": "pending_evidence",
            }
        ],
        functional_gap="",
        user_value="",
        argument_id="argument:1",
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
    assert "論點：" in body
    # 有來源時可展開,且標 Level
    assert "[Level A]" in body
    assert "行政程序法第92條" in body
    # 無來源 supplement 標 pending 警示
    assert 'class="pending"' in body
    assert "待補依據" in body
    # 每個主要內容顯示可追溯識別碼
    assert 'class="traceability"' in body
    assert "/tmp/note.txt" in body
    assert "source s1" in body
    assert "processing_record gap:1" in body
    # 每筆可讀卡片同時呈現來源、必要性雙視角與角度清單。
    assert "functional_gap（功能缺口）" in body
    assert "原稿未定義行政處分" in body
    assert "user_value（使用者價值）" in body
    assert "讓讀者辨識行政處分的適用範圍" in body
    assert "角度清單" in body
    assert "definition" in body
    assert "來源：pending（無來源）" in body
    assert "claim_fragment（主張片段）" in body
    assert "citation_spans（引用範圍）" in body
    assert "s1@" in body and "=[^1]" in body
    assert "來源片段：本法所稱行政處分" in body
    # 關聯知識、必要性雙視角與 ID 必須同卡顯示，不能只留在內部報告。
    assert "摘要可見" in body
    assert 'data-argument-id="argument:0"' in body
    assert "argument_id" in body
    assert "related_knowledge（關聯知識）" in body
    summary_block = body.split('data-argument-id="argument:0"', 1)[1].split(
        "</section>", 1
    )[0]
    assert "行政處分係指行政機關就公法上具體事件所為之單方決定。" in summary_block
    assert "原稿未定義行政處分" in summary_block
    assert "讓讀者辨識行政處分的適用範圍" in summary_block
    assert "支撐決策品質" in summary_block
    assert "補強使用者理解" in summary_block
    assert "另有學說補充" not in summary_block


def _result_id_from(body: str) -> str:
    match = re.search(r'/export/([A-Za-z0-9_\-]+)', body)
    assert match, "result page should link the opaque result export"
    return match.group(1)


async def _run_note(async_client, monkeypatch, doc) -> str:
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(
        server, "run_pipeline", lambda path, llm, twinkle, law: doc
    )
    r = await async_client.post(
        "/run", files={"file": ("note.txt", b"x", "text/plain")}
    )
    assert r.status_code == 200
    return _result_id_from(r.text)


@pytest.mark.anyio
async def test_export_returns_markdown_attachment(async_client, monkeypatch):
    doc = _fixed_doc()
    result_id = await _run_note(async_client, monkeypatch, doc)
    r = await async_client.get(f"/export/{result_id}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "attachment" in r.headers["content-disposition"]
    assert "correction.md" in r.headers["content-disposition"]
    # markdown 內容來自 to_markdown(doc),應含原文段字樣
    assert "行政處分" in r.text


@pytest.mark.anyio
async def test_export_without_run_returns_404(async_client):
    server.app.state.results.clear()
    r = await async_client.get("/export")
    assert r.status_code == 404
    r = await async_client.get("/export/no-such-result")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_export_b_cannot_receive_a_result(async_client, monkeypatch):
    """Issue #4 — A 跑完後,B 不得用全域 endpoint 拿到 A 的文件。"""
    doc_a = _fixed_doc()
    server.app.state.results.clear()
    result_a = await _run_note(async_client, monkeypatch, doc_a)
    # B 未跑任何 run;對裸 /export 與猜測的 ID 都只能是 404。
    r = await async_client.get("/export")
    assert r.status_code == 404
    r = await async_client.get("/export/" + "x" * 22)
    assert r.status_code == 404
    # 而 A 自己的 capability 仍可用。
    r = await async_client.get(f"/export/{result_a}")
    assert r.status_code == 200
    assert "行政處分" in r.text


@pytest.mark.anyio
async def test_export_two_clients_each_receive_own_result(
    async_client, monkeypatch
):
    """A/B 各自 run;各自的 export capability 只回自己的文件。"""
    server.app.state.results.clear()
    doc_a = _fixed_doc()
    doc_b = _fixed_doc()
    doc_b.segments[1].text = "B 的訂正稿內容。[^1]"
    result_a = await _run_note(async_client, monkeypatch, doc_a)
    result_b = await _run_note(async_client, monkeypatch, doc_b)
    assert result_a != result_b

    ra = await async_client.get(f"/export/{result_a}")
    rb = await async_client.get(f"/export/{result_b}")
    assert ra.status_code == 200 and rb.status_code == 200
    assert "B 的訂正稿內容" not in ra.text
    assert "B 的訂正稿內容" in rb.text


@pytest.mark.anyio
async def test_export_interleaved_runs_no_last_writer_mixup(
    async_client, monkeypatch
):
    """並發交錯:A run → B run → A export 仍拿到 A 的文件,非 last-writer-wins。"""
    server.app.state.results.clear()
    doc_a = _fixed_doc()
    doc_b = _fixed_doc()
    doc_b.segments[1].text = "B 的訂正稿內容。[^1]"
    result_a = await _run_note(async_client, monkeypatch, doc_a)
    result_b = await _run_note(async_client, monkeypatch, doc_b)

    ra = await async_client.get(f"/export/{result_a}")
    rb = await async_client.get(f"/export/{result_b}")
    assert "B 的訂正稿內容" not in ra.text
    assert "B 的訂正稿內容" in rb.text


@pytest.mark.anyio
async def test_export_expired_result_returns_404(async_client, monkeypatch):
    """TTL 過期後,result capability 回確定性 404,不落回最新文件。"""
    server.app.state.results.clear()
    doc_a = _fixed_doc()
    result_a = await _run_note(async_client, monkeypatch, doc_a)
    assert (await async_client.get(f"/export/{result_a}")).status_code == 200
    # 直接把 created_at 推到 TTL 之前,模擬過期。
    server.app.state.results[result_a]["created_at"] -= (
        server.RESULT_TTL_SECONDS + 1
    )
    r = await async_client.get(f"/export/{result_a}")
    assert r.status_code == 404
    # 過期條目真的被移除,後續查詢仍 404。
    assert result_a not in server.app.state.results


@pytest.mark.anyio
async def test_failed_run_creates_no_export_capability(
    async_client, monkeypatch
):
    """失敗的 run 不產生新 capability;舊 capability 不因此外洩。"""
    server.app.state.results.clear()
    doc_a = _fixed_doc()
    result_a = await _run_note(async_client, monkeypatch, doc_a)

    def boom(path, llm, twinkle, law):
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr(server, "run_pipeline", boom)
    r = await async_client.post(
        "/run", files={"file": ("note.txt", b"y", "text/plain")}
    )
    assert r.status_code == 500
    assert "/export/" not in r.text
    # 失敗 run 沒有新增任何結果。
    assert list(server.app.state.results) == [result_a]
