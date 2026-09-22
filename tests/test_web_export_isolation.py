"""Issue #4: /export 必須以 result capability 隔離，不得跨 client 轉送上一份結果。"""

from __future__ import annotations

import pytest

import app.server as server
from note_filler.correction import CorrectionDoc, Segment
from note_filler.parse import Document, Paragraph


def _doc(text: str = "原稿逐字保留。") -> Document:
    paragraph = Paragraph(idx=0, text=text)
    return Document("note-id.txt", (paragraph,), text)


def _correction(marker: str) -> CorrectionDoc:
    return CorrectionDoc(
        _doc(marker),
        [Segment(type="original", text=marker, anchor_idx=0, sources=[], confidence="verified")],
    )


def _patch_pipeline(monkeypatch, doc):
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(server, "run_pipeline", lambda *args: doc)


@pytest.mark.anyio
async def test_export_requires_result_id_and_isolates_clients(async_client, monkeypatch):
    server.app.state.results.clear()
    server.app.state.last_doc = None

    # 沒有 id → 404，即便 process 內曾有成功結果
    assert (await async_client.get("/export")).status_code == 404
    assert (await async_client.get("/export", params={"id": "forged"})).status_code == 404

    # client A 跑一次
    _patch_pipeline(monkeypatch, _correction("甲的原稿。"))
    r_a = await async_client.post("/run", files={"file": ("a.txt", b"raw-a", "text/plain")})
    assert r_a.status_code == 200
    id_a = next(iter(server.app.state.results.keys()))

    # client B 跑一次 → 產生不同 capability
    _patch_pipeline(monkeypatch, _correction("乙的原稿。"))
    r_b = await async_client.post("/run", files={"file": ("b.txt", b"raw-b", "text/plain")})
    assert r_b.status_code == 200
    ids = list(server.app.state.results.keys())
    assert len(ids) == 2 and ids[0] != ids[1]
    id_b = ids[1]

    # 各自只能取回自己的結果
    exp_a = await async_client.get("/export", params={"id": id_a})
    exp_b = await async_client.get("/export", params={"id": id_b})
    assert exp_a.status_code == 200 and "甲的原稿" in exp_a.text
    assert exp_b.status_code == 200 and "乙的原稿" in exp_b.text

    # 結果頁帶上 capability 連結
    assert f"/export?id={id_b}" in r_b.text


@pytest.mark.anyio
async def test_failed_run_creates_no_exportable_result(async_client, monkeypatch):
    server.app.state.results.clear()
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(
        server,
        "run_pipeline",
        lambda *args: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    r = await async_client.post("/run", files={"file": ("x.txt", b"raw", "text/plain")})
    assert r.status_code == 500
    assert len(server.app.state.results) == 0
