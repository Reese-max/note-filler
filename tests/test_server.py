import logging
import re
import threading
from pathlib import Path

import anyio
import httpx
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
async def test_export_b_cannot_receive_a_result(monkeypatch):
    """Issue #4 — A 跑完後,B 不得用全域 endpoint 拿到 A 的文件。"""
    doc_a = _fixed_doc()
    server.app.state.results.clear()
    transport_a = httpx.ASGITransport(app=server.app)
    transport_b = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport_a, base_url="http://client-a") as client_a, \
        httpx.AsyncClient(transport=transport_b, base_url="http://client-b") as client_b:
        result_a = await _run_note(client_a, monkeypatch, doc_a)
        # B 未跑任何 run;對裸 /export 與猜測的 ID 都只能是 404。
        assert (await client_b.get("/export")).status_code == 404
        assert (await client_b.get("/export/" + "x" * 22)).status_code == 404
        # A 持有自己的 capability,仍可匯出。
        r = await client_a.get(f"/export/{result_a}")
        assert r.status_code == 200
        assert "行政處分" in r.text


@pytest.mark.anyio
async def test_export_two_clients_each_receive_own_result(
    monkeypatch
):
    """A/B 各自 run;各自的 export capability 只回自己的文件。"""
    server.app.state.results.clear()
    doc_a = _fixed_doc()
    doc_b = _fixed_doc()
    doc_b.segments[1].text = "B 的訂正稿內容。[^1]"
    transport_a = httpx.ASGITransport(app=server.app)
    transport_b = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport_a, base_url="http://client-a") as client_a, \
        httpx.AsyncClient(transport=transport_b, base_url="http://client-b") as client_b:
        result_a = await _run_note(client_a, monkeypatch, doc_a)
        result_b = await _run_note(client_b, monkeypatch, doc_b)
        assert result_a != result_b

        ra = await client_a.get(f"/export/{result_a}")
        rb = await client_b.get(f"/export/{result_b}")
        assert ra.status_code == 200 and rb.status_code == 200
        assert "B 的訂正稿內容" not in ra.text
        assert "B 的訂正稿內容" in rb.text


@pytest.mark.anyio
async def test_export_interleaved_runs_no_last_writer_mixup(
    monkeypatch
):
    """兩個獨立 client 的 pipeline 真正重疊,匯出仍各自對應。"""
    server.app.state.results.clear()
    doc_a = _fixed_doc()
    doc_b = _fixed_doc()
    doc_b.segments[1].text = "B 的訂正稿內容。[^1]"
    barrier = threading.Barrier(2, timeout=10)
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))

    def pipeline(path, llm, twinkle, law):
        note = Path(path).read_bytes()
        barrier.wait()
        return doc_a if note == b"A" else doc_b

    monkeypatch.setattr(server, "run_pipeline", pipeline)
    responses = {}

    async def run_one(label, client):
        responses[label] = await client.post(
            "/run", files={"file": ("note.txt", label.encode(), "text/plain")}
        )

    transport_a = httpx.ASGITransport(app=server.app)
    transport_b = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport_a, base_url="http://client-a") as client_a, \
        httpx.AsyncClient(transport=transport_b, base_url="http://client-b") as client_b:
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(run_one, "A", client_a)
            tasks.start_soon(run_one, "B", client_b)
        assert responses["A"].status_code == 200
        assert responses["B"].status_code == 200
        result_a = _result_id_from(responses["A"].text)
        result_b = _result_id_from(responses["B"].text)
        assert result_a != result_b
        ra = await client_a.get(f"/export/{result_a}")
        rb = await client_b.get(f"/export/{result_b}")
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
async def test_export_after_restart_returns_404(async_client, monkeypatch):
    """程序重啟後的空記憶體不得回退到其他人的最新結果。"""
    server.app.state.results.clear()
    result_id = await _run_note(async_client, monkeypatch, _fixed_doc())
    assert (await async_client.get(f"/export/{result_id}")).status_code == 200
    old_results = server.app.state.results
    server.app.state.results = {}
    try:
        assert (await async_client.get(f"/export/{result_id}")).status_code == 404
        assert (await async_client.get("/export")).status_code == 404
    finally:
        old_results.clear()
        server.app.state.results = old_results


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("NOTE_FILLER_RESULT_TTL_SECONDS", "0"),
        ("NOTE_FILLER_RESULT_TTL_SECONDS", "-1"),
        ("NOTE_FILLER_RESULT_TTL_SECONDS", "nan"),
        ("NOTE_FILLER_RESULT_TTL_SECONDS", "inf"),
        ("NOTE_FILLER_RESULT_TTL_SECONDS", "invalid"),
        ("NOTE_FILLER_RESULT_MAX_ENTRIES", "0"),
        ("NOTE_FILLER_RESULT_MAX_ENTRIES", "-1"),
        ("NOTE_FILLER_RESULT_MAX_ENTRIES", "invalid"),
    ],
)
def test_invalid_result_retention_setting_fails_fast(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    setting = (
        server._positive_float_setting
        if name.endswith("SECONDS")
        else server._positive_int_setting
    )
    with pytest.raises(ValueError, match=name):
        setting(name, "1")


@pytest.mark.anyio
async def test_failed_run_does_not_log_uploaded_note_text(async_client, monkeypatch, caplog):
    sentinel = "PRIVATE_UPLOADED_NOTE_SENTINEL"
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))

    def boom(path, llm, twinkle, law):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(server, "run_pipeline", boom)
    with caplog.at_level(logging.ERROR, logger=server.logger.name):
        response = await async_client.post(
            "/run", files={"file": ("note.txt", sentinel.encode(), "text/plain")}
        )
    assert response.status_code == 500
    assert sentinel not in caplog.text
    assert sentinel not in response.text
    assert "/export/" not in response.text


@pytest.mark.anyio
async def test_web_pipeline_diagnostics_redact_note_and_result_text(
    async_client, monkeypatch, caplog
):
    sentinel = "PRIVATE_NOTE_AND_RESULT_SENTINEL"
    doc = _fixed_doc()
    doc.segments[1].text = sentinel
    pipeline_logger = logging.getLogger("note_filler.pipeline")
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))

    def pipeline(path, llm, twinkle, law):
        pipeline_logger.warning("uploaded note: %s", sentinel)
        try:
            raise RuntimeError(sentinel)
        except RuntimeError:
            pipeline_logger.exception("processing result: %s", sentinel)
        return doc

    monkeypatch.setattr(server, "run_pipeline", pipeline)
    with caplog.at_level(logging.WARNING, logger=pipeline_logger.name):
        response = await async_client.post(
            "/run", files={"file": ("note.txt", sentinel.encode(), "text/plain")}
        )
    assert response.status_code == 200
    assert sentinel in response.text
    assert sentinel not in caplog.text
    pipeline_records = [
        record for record in caplog.records if record.name == pipeline_logger.name
    ]
    assert len(pipeline_records) == 2
    assert all(
        record.msg == "web_content_diagnostic_redacted"
        and record.exc_info is None
        for record in pipeline_records
    )
    pipeline_logger.warning("normal logging resumed")
    assert caplog.records[-1].msg == "normal logging resumed"


@pytest.mark.anyio
async def test_export_formatting_does_not_log_result_text(
    async_client, monkeypatch, caplog
):
    sentinel = "PRIVATE_EXPORTED_RESULT_SENTINEL"
    result_id = await _run_note(async_client, monkeypatch, _fixed_doc())
    export_logger = logging.getLogger("note_filler.export")

    def markdown(doc, **kwargs):
        export_logger.warning("result body: %s", sentinel)
        return sentinel

    monkeypatch.setattr(server, "to_markdown", markdown)
    with caplog.at_level(logging.WARNING, logger=export_logger.name):
        response = await async_client.get(f"/export/{result_id}")
    assert response.status_code == 200
    assert response.text == sentinel
    assert sentinel not in caplog.text
    assert any(
        record.msg == "web_content_diagnostic_redacted"
        for record in caplog.records
        if record.name == export_logger.name
    )


@pytest.mark.anyio
async def test_export_formatting_failure_keeps_note_out_of_error_log(
    async_client, monkeypatch, caplog
):
    sentinel = "PRIVATE_EXPORT_EXCEPTION_SENTINEL"
    result_id = await _run_note(async_client, monkeypatch, _fixed_doc())

    def fail_export(doc, **kwargs):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(server, "to_markdown", fail_export)
    with caplog.at_level(logging.ERROR, logger=server.logger.name):
        response = await async_client.get(f"/export/{result_id}")
    assert response.status_code == 500
    assert sentinel not in response.text
    assert sentinel not in caplog.text
    assert result_id in server.app.state.results
    monkeypatch.setattr(server, "to_markdown", lambda doc, **kwargs: "retry works")
    assert (await async_client.get(f"/export/{result_id}")).text == "retry works"


@pytest.mark.anyio
async def test_result_render_failure_removes_new_capability(
    async_client, monkeypatch
):
    server.app.state.results.clear()
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(server, "run_pipeline", lambda *args: _fixed_doc())
    render = server.TEMPLATES.TemplateResponse
    calls = 0

    def fail_first_render(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("render failed")
        return render(*args, **kwargs)

    monkeypatch.setattr(server.TEMPLATES, "TemplateResponse", fail_first_render)
    response = await async_client.post(
        "/run", files={"file": ("note.txt", b"x", "text/plain")}
    )
    assert response.status_code == 500
    assert "/export/" not in response.text
    assert server.app.state.results == {}


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
