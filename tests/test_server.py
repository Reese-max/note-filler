import asyncio
import logging
import re
from pathlib import Path

import httpx
import pytest
from starlette.datastructures import UploadFile

import app.server as server

from note_filler.parse import Document, Paragraph
from note_filler.correction import Segment, CorrectionDoc, build_related_knowledge
from note_filler.retrieve.models import Source


def _new_client() -> httpx.AsyncClient:
    """建立帶獨立 cookie jar 的第二個瀏覽器 client,模擬另一台/另一分頁使用者。"""
    transport = httpx.ASGITransport(app=server.app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


_EXPORT_LINK = re.compile(r'href="(/export/[^"]+)"')


def _export_path(html: str) -> str:
    match = _EXPORT_LINK.search(html)
    assert match, "result page must link to a per-result export URL"
    return match.group(1)


@pytest.mark.anyio
async def test_index_returns_upload_form(async_client):
    r = await async_client.get("/")
    assert r.status_code == 200
    body = r.text
    assert 'action="/run"' in body
    assert 'enctype="multipart/form-data"' in body
    assert 'type="file"' in body
    assert 'name="file"' in body


def _fixed_doc(marker_text: str = "行政處分之定義。") -> CorrectionDoc:
    para = Paragraph(idx=0, text=marker_text)
    doc = Document(
        source_path="/tmp/note.txt",
        paragraphs=(para,),
        full_text=marker_text,
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
        text=marker_text,
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


def _stub_pipeline(monkeypatch, mapping):
    """run_pipeline 依上傳內容回傳對應 marker 的 CorrectionDoc。"""
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))

    def fake_run_pipeline(path, llm, twinkle, law):
        text = Path(path).read_text(encoding="utf-8")
        return _fixed_doc(mapping[text])

    monkeypatch.setattr(server, "run_pipeline", fake_run_pipeline)


@pytest.mark.anyio
async def test_export_returns_markdown_attachment(async_client, monkeypatch):
    doc = _fixed_doc()
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(
        server, "run_pipeline", lambda path, llm, twinkle, law: doc
    )
    run_resp = await async_client.post(
        "/run", files={"file": ("note.txt", b"x", "text/plain")}
    )
    assert run_resp.status_code == 200
    # 結果頁必須給出本次結果專屬的匯出連結,不能是全域 /export。
    r = await async_client.get(_export_path(run_resp.text))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert "attachment" in r.headers["content-disposition"]
    assert "correction.md" in r.headers["content-disposition"]
    # markdown 內容來自 to_markdown(doc),應含原文段字樣
    assert "行政處分" in r.text


@pytest.mark.anyio
async def test_export_without_run_returns_404(async_client):
    r = await async_client.get("/export")
    assert r.status_code == 404
    r = await async_client.get("/export/no-such-result")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_two_clients_export_only_own_result(monkeypatch):
    """A 跑筆記 A、B 跑筆記 B:各自的匯出連結只能拿到自己的訂正稿。"""
    _stub_pipeline(monkeypatch, {"note-a": "甲客戶專用-A", "note-b": "乙客戶專用-B"})
    async with _new_client() as client_a, _new_client() as client_b:
        run_a = await client_a.post(
            "/run", files={"file": ("a.txt", b"note-a", "text/plain")}
        )
        run_b = await client_b.post(
            "/run", files={"file": ("b.txt", b"note-b", "text/plain")}
        )
        assert run_a.status_code == 200 and run_b.status_code == 200
        export_a = _export_path(run_a.text)
        export_b = _export_path(run_b.text)
        assert export_a != export_b

        resp_a = await client_a.get(export_a)
        assert resp_a.status_code == 200
        assert "甲客戶專用-A" in resp_a.text
        assert "乙客戶專用-B" not in resp_a.text

        resp_b = await client_b.get(export_b)
        assert resp_b.status_code == 200
        assert "乙客戶專用-B" in resp_b.text
        assert "甲客戶專用-A" not in resp_b.text

        # 交叉取用:就算拿到對方 result id,沒有對方 session 也拿不到。
        assert (await client_a.get(export_b)).status_code == 404
        assert (await client_b.get(export_a)).status_code == 404


@pytest.mark.anyio
async def test_other_client_cannot_export_after_only_first_ran(monkeypatch):
    """只有 A 跑過時,B 呼叫匯出端點(無論裸路徑或猜中的 id)不得拿到 A 的文件。"""
    _stub_pipeline(monkeypatch, {"note-a": "甲客戶專用-A"})
    async with _new_client() as client_a, _new_client() as client_b:
        run_a = await client_a.post(
            "/run", files={"file": ("a.txt", b"note-a", "text/plain")}
        )
        assert run_a.status_code == 200
        export_a = _export_path(run_a.text)

        assert (await client_b.get("/export")).status_code == 404
        # B 從未 /run,沒有任何 session,也沒有 A 的 result id 以外的線索。
        resp_b = await client_b.get(export_a)
        assert resp_b.status_code == 404
        assert "甲客戶專用-A" not in resp_b.text


@pytest.mark.anyio
async def test_concurrent_runs_do_not_mix_results(monkeypatch):
    """兩 client 併發 /run:結果以各自的 result id 為準,無 last-writer-wins。"""
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))

    def slow_pipeline(path, llm, twinkle, law):
        import time

        time.sleep(0.05)
        text = Path(path).read_text(encoding="utf-8")
        return _fixed_doc(f"專屬-{text}")

    monkeypatch.setattr(server, "run_pipeline", slow_pipeline)
    async with _new_client() as client_a, _new_client() as client_b:
        run_a, run_b = await asyncio.gather(
            client_a.post("/run", files={"file": ("a.txt", b"note-a", "text/plain")}),
            client_b.post("/run", files={"file": ("b.txt", b"note-b", "text/plain")}),
        )
        assert run_a.status_code == 200 and run_b.status_code == 200
        export_a = _export_path(run_a.text)
        export_b = _export_path(run_b.text)
        assert export_a != export_b

        resp_a = await client_a.get(export_a)
        resp_b = await client_b.get(export_b)
        assert resp_a.status_code == 200 and resp_b.status_code == 200
        assert "專屬-note-a" in resp_a.text and "專屬-note-b" not in resp_a.text
        assert "專屬-note-b" in resp_b.text and "專屬-note-a" not in resp_b.text


@pytest.mark.anyio
async def test_failed_run_discards_previous_result(async_client, monkeypatch):
    """失敗的新 run 不得把同 session 舊成功結果當成本次產物匯出。"""
    _stub_pipeline(monkeypatch, {"note-a": "甲客戶專用-A"})
    run_ok = await async_client.post(
        "/run", files={"file": ("a.txt", b"note-a", "text/plain")}
    )
    assert run_ok.status_code == 200
    export_a = _export_path(run_ok.text)

    monkeypatch.setattr(
        server,
        "run_pipeline",
        lambda *a: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    failed = await async_client.post(
        "/run", files={"file": ("boom.txt", b"x", "text/plain")}
    )
    assert failed.status_code == 500
    # 失敗頁本身不提供匯出連結;舊連結亦不得再回傳上一份成功稿。
    assert _EXPORT_LINK.search(failed.text) is None
    assert (await async_client.get(export_a)).status_code == 404


@pytest.mark.anyio
async def test_expired_result_returns_410(async_client, monkeypatch):
    _stub_pipeline(monkeypatch, {"note-a": "甲客戶專用-A"})
    run_resp = await async_client.post(
        "/run", files={"file": ("a.txt", b"note-a", "text/plain")}
    )
    assert run_resp.status_code == 200
    export_a = _export_path(run_resp.text)
    assert (await async_client.get(export_a)).status_code == 200

    result_id = export_a.rsplit("/", 1)[-1]
    entry = server.app.state.results._entries[result_id]
    entry.expires_at -= 10**9  # 直接老化,不等待真實 TTL

    r = await async_client.get(export_a)
    assert r.status_code == 410


@pytest.mark.anyio
async def test_restarted_result_store_returns_404(async_client, monkeypatch):
    """進程重啟 → in-memory 結果全失 → 確定性 404,不得落回任何文件。"""
    _stub_pipeline(monkeypatch, {"note-a": "甲客戶專用-A"})
    run_resp = await async_client.post(
        "/run", files={"file": ("a.txt", b"note-a", "text/plain")}
    )
    assert run_resp.status_code == 200
    export_a = _export_path(run_resp.text)

    server.app.state.results._entries.clear()  # 模擬重啟丟失 in-memory 狀態

    assert (await async_client.get(export_a)).status_code == 404


@pytest.mark.anyio
async def test_expired_foreign_result_does_not_leak_existence(monkeypatch):
    """過期結果對 owner 回 410,對其他 session 仍是 404:owner 檢查先於過期檢查。"""
    _stub_pipeline(monkeypatch, {"note-a": "甲客戶專用-A"})
    async with _new_client() as client_a, _new_client() as client_b:
        run_a = await client_a.post(
            "/run", files={"file": ("a.txt", b"note-a", "text/plain")}
        )
        export_a = _export_path(run_a.text)
        result_id = export_a.rsplit("/", 1)[-1]
        server.app.state.results._entries[result_id].expires_at -= 10**9

        # B(非 owner)在項目仍存在時也必須是 404,不得由 410 洩漏存在性。
        assert (await client_b.get(export_a)).status_code == 404
        assert (await client_a.get(export_a)).status_code == 410
        # owner 取得後項目被逐出;之後任何 client 一律 404。
        assert (await client_b.get(export_a)).status_code == 404


@pytest.mark.anyio
async def test_upload_read_failure_returns_traceable_500(async_client, monkeypatch):
    """上傳內容讀取失敗也走同一條 traceable 500 錯誤頁,不裸拋到框架。"""
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))

    async def boom_read(self):
        raise RuntimeError("upload-read-boom")

    monkeypatch.setattr(UploadFile, "read", boom_read)
    r = await async_client.post(
        "/run", files={"file": ("n.txt", b"x", "text/plain")}
    )
    assert r.status_code == 500
    assert "RuntimeError: upload-read-boom" in r.text


@pytest.mark.anyio
async def test_index_issues_session_cookie_and_run_reuses_it(async_client, monkeypatch):
    """GET / 即簽發 nf_session;之後 /run 沿用同一 session,不再換發。"""
    r = await async_client.get("/")
    assert r.status_code == 200
    session_cookie = async_client.cookies.get("nf_session")
    assert session_cookie, "index must issue the session cookie"

    _stub_pipeline(monkeypatch, {"note-a": "甲客戶專用-A"})
    run_resp = await async_client.post(
        "/run", files={"file": ("a.txt", b"note-a", "text/plain")}
    )
    assert run_resp.status_code == 200
    assert async_client.cookies.get("nf_session") == session_cookie
    assert (await async_client.get(_export_path(run_resp.text))).status_code == 200


@pytest.mark.anyio
async def test_uploaded_note_and_result_body_not_logged(async_client, monkeypatch, caplog):
    """上傳筆記內文與訂正稿內容不得進入預設日誌。"""
    secret_marker = "絕密個案編號-QZX-7788"
    _stub_pipeline(monkeypatch, {"note-a": secret_marker})
    with caplog.at_level(logging.INFO):
        run_resp = await async_client.post(
            "/run", files={"file": ("a.txt", b"note-a", "text/plain")}
        )
        assert run_resp.status_code == 200
        await async_client.get(_export_path(run_resp.text))
    for record in caplog.records:
        assert secret_marker not in record.getMessage()
