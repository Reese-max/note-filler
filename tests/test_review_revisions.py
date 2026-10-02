from dataclasses import replace
import json

import pytest

import app.server as server
from note_filler.export import to_markdown
from note_filler.review import ReviewLedger, ReviewState
from tests.review_forms import review_form
from tests.test_review_queue import _doc, _ledger, ORIGINAL_TEXT


@pytest.mark.anyio
@pytest.mark.parametrize("drift", ["claim", "evidence", "citation", "decision", "upload", "same_upload"])
async def test_old_browser_form_cannot_approve_a_new_revision(async_client, monkeypatch, tmp_path, drift):
    doc = _doc()
    ledger = _ledger(doc)
    monkeypatch.setattr(server.app.state, "last_doc", doc)
    monkeypatch.setattr(server.app.state, "review_ledger", ledger)
    monkeypatch.setattr(server, "LEDGER_PATH", tmp_path / "ledger.json")
    form = await review_form(async_client)
    assert {"document_revision", "document_instance", "claim_revision", "evidence_revision", "decision_revision"} <= form.keys()
    if drift == "claim":
        doc.segments[1].text = "新的主張版本。"
    elif drift == "evidence":
        doc.segments[1].sources[0].content += "新的來源內容。"
    elif drift == "citation":
        doc.segments[1].citation_spans[0]["span_end"] += 1
    elif drift == "decision":
        ledger.record(doc.segments[1], "rejected")
    else:
        replacement = replace(doc, segments=list(doc.segments))
        if drift == "upload":
            replacement.original = replace(doc.original, full_text="另一份上傳。")
        server.app.state.last_doc = replacement
    before = ledger.to_dict()
    response = await async_client.post("/review", data={**form, "decision": "accepted"})
    assert response.status_code == 409
    assert ledger.to_dict() == before


@pytest.mark.anyio
async def test_missing_revision_tokens_fail_closed(async_client, monkeypatch, tmp_path):
    doc = _doc()
    ledger = _ledger(doc)
    monkeypatch.setattr(server.app.state, "last_doc", doc)
    monkeypatch.setattr(server.app.state, "review_ledger", ledger)
    monkeypatch.setattr(server, "LEDGER_PATH", tmp_path / "ledger.json")
    response = await async_client.post("/review", data={
        "argument_id": "argument:0", "decision": "accepted",
    })
    assert response.status_code == 409
    assert ledger.records == []


@pytest.mark.anyio
async def test_manual_edit_survives_regeneration_and_process_state_reload(async_client, monkeypatch, tmp_path):
    original = _doc()
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(server, "run_pipeline", lambda *args: _doc())
    monkeypatch.setattr(server, "LEDGER_PATH", tmp_path / "ledger.json")
    monkeypatch.setattr(server.app.state, "last_doc", original)
    monkeypatch.setattr(server.app.state, "review_ledger", _ledger(original))
    for text in ("第一次人工修訂。", "第二次人工修訂。"):
        form = await review_form(async_client)
        response = await async_client.post("/review", data={
            **form, "decision": "accepted", "edited_text": text,
        })
        assert response.status_code == 200
    before_original = original.original.full_text
    server.app.state.last_doc = None
    server.app.state.review_ledger = None
    response = await async_client.post("/run", files={
        "file": ("note.txt", ORIGINAL_TEXT.encode(), "text/plain"),
    })
    assert response.status_code == 200
    assert "第二次人工修訂。" in response.text
    assert 'data-review-state="edited_accepted"' in response.text
    export = await async_client.get("/export?mode=accepted-only")
    assert "第二次人工修訂。" in export.text
    assert original.segments[1].text not in export.text
    assert server.app.state.last_doc.original.full_text == before_original


def edited_ledger(tmp_path):
    doc = _doc()
    ledger = _ledger(doc)
    candidate = replace(doc.segments[1], text="持久化的人工修訂。")
    ledger.record(candidate, "edited_accepted", base_segment=doc.segments[1])
    path = ledger.save(tmp_path / "ledger.json")
    return path, doc, candidate


def test_durable_overlay_is_replayed_in_direct_export(tmp_path):
    path, doc, edited = edited_ledger(tmp_path)
    ledger = ReviewLedger.load_for_document(path, doc)
    text = to_markdown(doc, export_mode="accepted-only", ledger=ledger)
    assert edited.text in text
    assert doc.segments[1].text not in text
    assert doc.segments[1].text == _doc().segments[1].text


@pytest.mark.parametrize("drift", ["claim", "evidence", "citation"])
def test_overlay_does_not_hide_new_generated_content_or_evidence(tmp_path, drift):
    path, doc, edited = edited_ledger(tmp_path)
    if drift == "claim":
        doc.segments[1].text = "重新產生的不同主張。"
    elif drift == "evidence":
        doc.segments[1].sources[0].content += "已變更。"
    else:
        doc.segments[1].citation_spans[0]["span_end"] += 1
    ledger = ReviewLedger.load_for_document(path, doc)
    replay = ledger.apply_overlays(doc)
    assert replay.segments[1].text == doc.segments[1].text
    assert ledger.state_of(replay.segments[1]) == ReviewState.STALE_REVIEW
    assert edited.text not in to_markdown(replay, export_mode="accepted-only", ledger=ledger)


def test_tampered_overlay_text_is_not_exported(tmp_path):
    path, doc, _ = edited_ledger(tmp_path)
    data = json.loads(path.read_text())
    data["records"][0]["revision_overlay"]["edited_text"] = "遭竄改的文字。"
    path.write_text(json.dumps(data))
    ledger = ReviewLedger.load_for_document(path, doc)
    assert "遭竄改" not in to_markdown(doc, export_mode="accepted-only", ledger=ledger)
    assert ledger.state_of(ledger.apply_overlays(doc).segments[1]) == ReviewState.STALE_REVIEW


def test_legacy_ledger_can_replay_unedited_decisions(tmp_path):
    doc = _doc()
    ledger = _ledger(doc)
    ledger.record(doc.segments[1], "accepted")
    data = ledger.to_dict()
    data["schema"] = "note_filler.review_ledger.v1"
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(data))
    loaded = ReviewLedger.load_for_document(path, doc)
    assert loaded.state_of(doc.segments[1]) == ReviewState.ACCEPTED
