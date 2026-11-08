"""Unknown persisted history stays intact; safe UNREVIEWED reads still work."""
import json

import pytest

import app.server as server
from note_filler.export import to_markdown
from note_filler.review import ReviewLedger, ReviewState
from tests.review_forms import review_form, seed_result
from tests.test_review_queue import _doc, ORIGINAL_TEXT


UNKNOWN_LEDGERS = [
    pytest.param(b'{not json: private previous decision', id='broken-json'),
    pytest.param(b'\xff\xfeprevious decision', id='invalid-utf8'),
    pytest.param(b'[]', id='wrong-root-shape'),
    pytest.param(b'{"schema":"future-ledger.v99","records":[]}', id='unknown-schema'),
    pytest.param(
        b'{"schema":"note_filler.review_ledger.v2","records":[null]}',
        id='invalid-known-schema-record',
    ),
]


@pytest.mark.parametrize('original_bytes', UNKNOWN_LEDGERS)
def test_fresh_unreviewed_read_does_not_authorize_overwriting_unknown_history(tmp_path, original_bytes):
    doc = _doc()
    path = tmp_path / 'ledger.json'
    path.write_bytes(original_bytes)
    ledger = ReviewLedger.load_for_document(path, doc)
    assert ledger.state_of(doc.segments[1]) == ReviewState.UNREVIEWED
    exported = to_markdown(doc, export_mode='accepted-only', ledger=ledger)
    assert ORIGINAL_TEXT in exported and doc.segments[1].text not in exported
    ledger.record(doc.segments[1], 'accepted')
    with pytest.raises(ValueError, match='無法辨識既有審查履歷'):
        ledger.save(path)
    assert path.read_bytes() == original_bytes
    assert not path.with_name(path.name + '.tmp').exists()


def test_missing_file_and_recognized_legacy_history_remain_writable(tmp_path):
    doc = _doc()
    path = tmp_path / 'ledger.json'
    ledger = ReviewLedger.for_document(doc)
    first = ledger.record(doc.segments[1], 'accepted')
    ledger.save(path)
    payload = json.loads(path.read_text('utf-8'))
    payload['schema'] = 'note_filler.review_ledger.v1'
    path.write_text(json.dumps(payload), encoding='utf-8')
    loaded = ReviewLedger.load_for_document(path, doc)
    second = loaded.record(doc.segments[1], 'rejected')
    loaded.save(path)
    saved = ReviewLedger.load_for_document(path, doc)
    assert [record.decision_id for record in saved.records] == [first.decision_id, second.decision_id]
    assert saved.state_of(doc.segments[1]) == ReviewState.REJECTED


@pytest.mark.anyio
@pytest.mark.parametrize('original_bytes', UNKNOWN_LEDGERS)
async def test_web_fresh_form_cannot_replace_unknown_history_or_publish_unsaved_edit(
    async_client, monkeypatch, tmp_path, original_bytes,
):
    doc = _doc()
    original_claim = doc.segments[1].text
    monkeypatch.setattr(server, 'LEDGER_PATH', tmp_path / 'ledger.json')
    result_id = seed_result(doc)
    path = server._ledger_path_for(doc, result_id)
    path.write_bytes(original_bytes)
    form = await review_form(async_client, result_id=result_id)
    assert server.app.state.results[result_id]['review_ledger'].records == []
    response = await async_client.post(f'/review/{result_id}', data={
        **form, 'decision': 'accepted', 'edited_text': '未持久化的候選修訂。',
    })
    assert response.status_code == 409
    assert '已保留原檔' in response.text and 'private previous decision' not in response.text
    assert response.headers['cache-control'] == 'no-store'
    assert path.read_bytes() == original_bytes
    assert not path.with_name(path.name + '.tmp').exists()
    entry = server.app.state.results[result_id]
    assert entry['review_ledger'].records == []
    assert entry['doc'].segments[1].text == original_claim
    assert entry['doc'].original.full_text == ORIGINAL_TEXT
    exported = await async_client.get(f'/export/{result_id}?mode=accepted-only')
    assert exported.status_code == 200
    assert '未持久化的候選修訂。' not in exported.text and original_claim not in exported.text


@pytest.mark.anyio
async def test_web_can_resume_only_after_unknown_history_is_explicitly_restored(
    async_client, monkeypatch, tmp_path,
):
    doc = _doc()
    monkeypatch.setattr(server, 'LEDGER_PATH', tmp_path / 'ledger.json')
    result_id = seed_result(doc)
    path = server._ledger_path_for(doc, result_id)
    path.write_bytes(b'{damaged history')
    form = await review_form(async_client, result_id=result_id)
    denied = await async_client.post(f'/review/{result_id}', data={**form, 'decision': 'accepted'})
    assert denied.status_code == 409 and path.read_bytes() == b'{damaged history'
    # Owned fixture simulates explicit recovery; the application never resets
    # or discards the unknown file on the user's behalf.
    path.write_text(json.dumps(ReviewLedger.for_document(doc).to_dict()), encoding='utf-8')
    form = await review_form(async_client, result_id=result_id)
    accepted = await async_client.post(f'/review/{result_id}', data={**form, 'decision': 'accepted'})
    assert accepted.status_code == 200
    loaded = ReviewLedger.load_for_document(path, doc)
    assert len(loaded.records) == 1 and loaded.state_of(doc.segments[1]) == ReviewState.ACCEPTED
