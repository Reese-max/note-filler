"""主張級 Verify／Accept／Reject 審查佇列與決策履歷測試（issue #3）。

涵蓋驗收清單：
  - 每個 supplement/argument 有獨立 human review state，與系統 confidence 分開
  - ACCEPT / REJECT / NEEDS_MORE_EVIDENCE 決策附時間、reason、claim/evidence hash
  - 手動修改 claim → 舊 ACCEPTED 不得沿用（STALE_REVIEW / EDITED_ACCEPTED 新決策）
  - source content hash / citation span / claim hash 改變 → STALE_REVIEW（fail closed）
  - accepted-only export 不含 rejected / stale / needs-evidence / unreviewed supplement
  - 原稿在 review 操作後 byte-for-byte 不變
  - ledger 可序列化/載入並重播同一文件的審查狀態
  - 來源遺失時已核准 claim 不得保持「正常已核准」外觀
"""

import json

import pytest

import app.server as server
from note_filler.correction import CorrectionDoc, Segment
from note_filler.export import to_markdown
from note_filler.parse import Document, Paragraph
from note_filler.retrieve.models import Source

try:
    from note_filler import review as review_mod
except ImportError:  # 紅燈階段：模組尚不存在
    review_mod = None


ORIGINAL_TEXT = "原文第一段。"


def _source(
    sid,
    *,
    level="A",
    title="法規來源",
    content="本法所稱行政處分，係指行政機關就公法上具體事件所為之決定。",
    url="https://law.moj.gov.tw/x",
    doc_date="2005-12-28",
    fetched_date="2026-07-01",
    distance=0.1,
):
    return Source(
        id=sid,
        title=title,
        url=url,
        level=level,
        content=content,
        fetched_date=fetched_date,
        doc_date=doc_date,
        distance=distance,
    )


def _supplement(
    argument_id,
    text,
    sources,
    *,
    confidence="verified",
    conflict_note=None,
    citation_spans=None,
    extended_readings=None,
):
    source_ids = [s.id for s in sources]
    return Segment(
        type="supplement",
        text=text,
        anchor_idx=0,
        sources=list(sources),
        confidence=confidence,
        conflict_note=conflict_note,
        traceability=[{"kind": "source", "id": s.id} for s in sources],
        citation_spans=list(citation_spans or []),
        source_id=f"sources:{','.join(source_ids)}" if source_ids else f"pending:{argument_id}",
        source_ids=source_ids,
        argument_id=argument_id,
        extended_readings=list(extended_readings or []),
    )


def _doc():
    """original + 3 個 supplements：verified、pending、衝突來源。"""
    original = Document(
        source_path="/tmp/note.txt",
        paragraphs=(Paragraph(idx=0, text=ORIGINAL_TEXT),),
        full_text=ORIGINAL_TEXT,
    )
    verified = _supplement(
        "argument:0",
        "行政處分係指行政機關就公法上具體事件所為之決定。[^1]",
        [_source("s1")],
        confidence="verified",
        citation_spans=[
        {
            "source_id": "s1",
            "span_start": len("行政處分係指行政機關就公法上具體事件所為之決定。"),
            "span_end": len("行政處分係指行政機關就公法上具體事件所為之決定。") + 4,
            "marker_text": "[^1]",
        }
        ],
    )
    pending = _supplement(
        "argument:1",
        "【待補證】施行細節仍待查證。",
        [],
        confidence="pending_evidence",
    )
    conflict = _supplement(
        "argument:2",
        "沒收處分應以判決為準。",
        [
            _source("s3", content="沒收處分應以判決為準。", level="B", title="甲說"),
            _source("s4", content="沒收處分不應以判決為準。", level="B", title="乙說"),
        ],
        confidence="pending_evidence",
        conflict_note="來源對「應/不應」表述不一致,需人工判讀(不選邊)",
    )
    return CorrectionDoc(
        original=original, segments=[
            Segment(
                type="original",
                text=ORIGINAL_TEXT,
                anchor_idx=0,
                sources=[],
                confidence="verified",
                traceability=[
                    {"kind": "original_input", "id": "/tmp/note.txt", "paragraph_idx": 0}
                ],
            ),
            verified,
            pending,
            conflict,
        ]
    )


def _ledger(doc):
    assert review_mod is not None, "note_filler.review 模組不存在"
    return review_mod.ReviewLedger.for_document(doc)


# ---- 基本狀態與決策紀錄 --------------------------------------------------


def test_supplements_start_unreviewed_separate_from_confidence():
    doc = _doc()
    ledger = _ledger(doc)
    states = [ledger.state_of(seg) for seg in doc.segments]
    # original 段不進審查佇列；supplement 一律 UNREVIEWED（即便系統 verified）
    assert states[0] == review_mod.ReviewState.UNREVIEWED
    assert doc.segments[1].confidence == "verified"
    assert states[1] == review_mod.ReviewState.UNREVIEWED
    assert states[2] == review_mod.ReviewState.UNREVIEWED
    assert states[3] == review_mod.ReviewState.UNREVIEWED


def test_accept_reject_needs_evidence_decisions():
    doc = _doc()
    ledger = _ledger(doc)
    seg_ok, seg_pending, seg_conflict = doc.segments[1:]

    r1 = ledger.record(seg_ok, "accepted", reason_code="", note="核可", reviewer="op")
    r2 = ledger.record(seg_pending, "needs_more_evidence",
                       reason_code="needs_primary_source", note="缺一手來源")
    r3 = ledger.record(seg_conflict, "rejected", reason_code="source_not_supporting")

    assert ledger.state_of(seg_ok) == review_mod.ReviewState.ACCEPTED
    assert ledger.state_of(seg_pending) == review_mod.ReviewState.NEEDS_MORE_EVIDENCE
    assert ledger.state_of(seg_conflict) == review_mod.ReviewState.REJECTED

    for rec in (r1, r2, r3):
        assert rec.argument_id
        assert rec.reviewed_at
        assert rec.reviewer
        assert rec.claim_hash and rec.evidence_hash
        assert rec.decision_id
    assert r1.reviewer == "op"
    assert r1.previous_decision_id is None
    # 重審時指回前一筆決策
    r4 = ledger.record(seg_ok, "rejected", reason_code="out_of_scope")
    assert r4.previous_decision_id == r1.decision_id
    assert ledger.state_of(seg_ok) == review_mod.ReviewState.REJECTED
    assert [r.decision_id for r in ledger.records_for("argument:0")] == [
        r1.decision_id, r4.decision_id
    ]


def test_verified_confidence_does_not_equal_accepted():
    """系統 verified ≠ 人類 ACCEPTED：未審的 verified supplement 不得進正式稿。"""
    doc = _doc()
    ledger = _ledger(doc)
    md = to_markdown(doc, export_mode="accepted-only", ledger=ledger)
    assert "行政處分係指" not in md  # verified 但未審 → 排除


def test_illegal_decision_and_reason_rejected():
    doc = _doc()
    ledger = _ledger(doc)
    seg = doc.segments[1]
    with pytest.raises(ValueError):
        ledger.record(seg, "stale_review")  # STALE_REVIEW 為衍生態，不可手動記錄
    with pytest.raises(ValueError):
        ledger.record(seg, "unreviewed")
    with pytest.raises(ValueError):
        ledger.record(seg, "accepted", reason_code="not_a_real_code")
    with pytest.raises(ValueError):
        ledger.record(doc.segments[0], "accepted")  # original 段不可審


# ---- 失效與 re-review -----------------------------------------------------


def test_claim_edit_invalidates_previous_accept():
    doc = _doc()
    ledger = _ledger(doc)
    seg = doc.segments[1]
    ledger.record(seg, "accepted", note="初審通過")

    seg.text = "行政處分係指行政機關就公法上具體事件所為之決定（已手動改寫）。[^1]"
    detail = ledger.state_detail(seg)
    assert detail["state"] == review_mod.ReviewState.STALE_REVIEW
    assert detail["stale_reason"] == "claim_changed"

    rec = ledger.record(seg, "edited_accepted", note="手動修訂後核准")
    assert rec.reason_code == "manual_edit"  # 預設快捷碼
    assert ledger.state_of(seg) == review_mod.ReviewState.EDITED_ACCEPTED


def test_citation_span_change_invalidates():
    doc = _doc()
    ledger = _ledger(doc)
    seg = doc.segments[1]
    ledger.record(seg, "accepted")
    seg.citation_spans[0]["span_end"] += 1
    assert ledger.state_of(seg) == review_mod.ReviewState.STALE_REVIEW


def test_source_content_drift_marks_stale():
    doc = _doc()
    ledger = _ledger(doc)
    seg = doc.segments[1]
    ledger.record(seg, "accepted")
    seg.sources[0].content = "來源內容已被改版。"
    detail = ledger.state_detail(seg)
    assert detail["state"] == review_mod.ReviewState.STALE_REVIEW
    assert detail["stale_reason"] == "evidence_changed"


def test_missing_source_marks_evidence_unavailable():
    """引用的來源被刪/找不到時，已核准 claim 必須顯示 evidence unavailable。"""
    doc = _doc()
    ledger = _ledger(doc)
    seg = doc.segments[1]
    ledger.record(seg, "accepted")
    seg.sources.clear()  # source_ids 仍在但來源物件消失
    detail = ledger.state_detail(seg)
    assert detail["state"] == review_mod.ReviewState.STALE_REVIEW
    assert detail["stale_reason"] == "evidence_unavailable"


def test_validation_contract_change_marks_stale():
    doc = _doc()
    ledger = _ledger(doc)
    seg = doc.segments[1]
    ledger.record(seg, "accepted")
    seg.confidence = "pending_evidence"  # 驗證契約降級（如法條查無）
    assert ledger.state_of(seg) == review_mod.ReviewState.STALE_REVIEW


# ---- 來源立場（deterministic,非 LLM 自評） ---------------------------------


def test_source_stances_support_conflict_context_unresolved():
    doc = _doc()
    seg_ok, _, seg_conflict = doc.segments[1:]

    stances = {s["source_id"]: s["stance"] for s in review_mod.source_stances(seg_ok)}
    assert stances["s1"] == "supports"

    conflict_stances = {
        s["source_id"]: s["stance"] for s in review_mod.source_stances(seg_conflict)
    }
    assert conflict_stances["s3"] == "supports"     # 正面詞來源
    assert conflict_stances["s4"] == "conflicts"    # 反面詞來源

    seg_ok.extended_readings = [
        {"source_id": "s9", "title": "延伸", "url": "https://x", "level": "C", "distance": 0.9}
    ]
    stances = {s["source_id"]: s["stance"] for s in review_mod.source_stances(seg_ok)}
    assert stances["s9"] == "context_only"          # 檢索到但未引用

    unrelated = _supplement(
        "argument:9", "完全無關的論點文字。",
        [_source("s8", content="qqq zzz", title="無關文件")],
    )
    stances = {s["source_id"]: s["stance"] for s in review_mod.source_stances(unrelated)}
    assert stances["s8"] == "unresolved"            # 引用但語彙無重疊


# ---- 匯出閘 ---------------------------------------------------------------


def test_accepted_only_export_excludes_non_accepted():
    doc = _doc()
    ledger = _ledger(doc)
    seg_ok, seg_pending, seg_conflict = doc.segments[1:]
    ledger.record(seg_ok, "accepted", note="ok")
    ledger.record(seg_pending, "needs_more_evidence", reason_code="needs_primary_source")
    ledger.record(seg_conflict, "rejected", reason_code="source_not_supporting")

    md = to_markdown(doc, export_mode="accepted-only", ledger=ledger)
    assert ORIGINAL_TEXT in md                    # 原稿永遠保留
    assert "行政處分係指" in md                     # accepted 收錄
    assert "施行細節仍待查證" not in md               # needs_more_evidence 排除
    assert "沒收處分應以判決為準" not in md           # rejected 排除
    assert "export_mode=accepted-only" in md


def test_accepted_only_export_excludes_stale_and_pending_confidence():
    doc = _doc()
    ledger = _ledger(doc)
    seg_ok = doc.segments[1]
    ledger.record(seg_ok, "accepted")
    seg_ok.sources[0].content = "改版後的來源內容"  # → STALE_REVIEW
    md = to_markdown(doc, export_mode="accepted-only", ledger=ledger)
    assert "行政處分係指" not in md  # stale 不得混入正式稿

    # 人類核准也不能放行 pending_evidence（無來源不進正文）
    doc2 = _doc()
    ledger2 = _ledger(doc2)
    ledger2.record(doc2.segments[2], "accepted")
    md2 = to_markdown(doc2, export_mode="accepted-only", ledger=ledger2)
    assert "施行細節仍待查證" not in md2


def test_accepted_only_without_ledger_is_fail_closed():
    md = to_markdown(_doc(), export_mode="accepted-only", ledger=None)
    assert ORIGINAL_TEXT in md
    assert "行政處分係指" not in md


def test_review_draft_export_marks_review_state():
    doc = _doc()
    ledger = _ledger(doc)
    ledger.record(doc.segments[1], "accepted", note="ok", reviewer="op1")
    md = to_markdown(doc, export_mode="review-draft", ledger=ledger)
    assert "review_state=accepted" in md
    assert "reviewer=op1" in md
    assert "review_state=unreviewed" in md  # 未審段在草稿中仍標示
    assert "施行細節仍待查證" in md          # 草稿保留 pending 供審查


def test_default_export_mode_unchanged():
    """既有呼叫 to_markdown(doc) 行為不變（review-draft 相容）。"""
    md = to_markdown(_doc())
    assert "行政處分係指" in md
    assert "施行細節仍待查證" in md


# ---- 序列化 / 重播 ---------------------------------------------------------


def test_ledger_roundtrip_replays_same_states(tmp_path):
    doc = _doc()
    ledger = _ledger(doc)
    r1 = ledger.record(doc.segments[1], "accepted", note="ok")
    ledger.record(doc.segments[2], "needs_more_evidence",
                  reason_code="needs_primary_source")
    ledger.record(doc.segments[3], "rejected", reason_code="source_not_supporting")

    path = tmp_path / "ledger.json"
    ledger.save(path)
    loaded = review_mod.ReviewLedger.load_for_document(path, doc)

    assert loaded is not None
    assert [r.decision_id for r in loaded.records] == [
        r.decision_id for r in ledger.records
    ]
    assert loaded.records_for("argument:0")[0].decision_id == r1.decision_id
    assert loaded.state_of(doc.segments[1]) == review_mod.ReviewState.ACCEPTED
    assert loaded.state_of(doc.segments[2]) == review_mod.ReviewState.NEEDS_MORE_EVIDENCE
    assert loaded.state_of(doc.segments[3]) == review_mod.ReviewState.REJECTED
    # 序列化結果可被獨立解析
    json.loads(path.read_text(encoding="utf-8"))


def test_ledger_not_replayed_for_different_document(tmp_path):
    doc = _doc()
    ledger = _ledger(doc)
    ledger.record(doc.segments[1], "accepted")
    path = tmp_path / "ledger.json"
    ledger.save(path)

    other = _doc()
    # Document 為 frozen dataclass,以另一份原始文件重建 CorrectionDoc
    other = CorrectionDoc(
        original=Document(
            source_path="/tmp/other.txt",
            paragraphs=(Paragraph(idx=0, text="另一份筆記。"),),
            full_text="另一份筆記。",
        ),
        segments=list(other.segments),
    )
    loaded = review_mod.ReviewLedger.load_for_document(path, other)
    assert loaded.state_of(other.segments[1]) == review_mod.ReviewState.UNREVIEWED


def test_ledger_load_missing_or_corrupt_is_fresh(tmp_path):
    doc = _doc()
    missing = review_mod.ReviewLedger.load_for_document(tmp_path / "none.json", doc)
    assert missing.state_of(doc.segments[1]) == review_mod.ReviewState.UNREVIEWED

    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    fresh = review_mod.ReviewLedger.load_for_document(bad, doc)
    assert fresh.state_of(doc.segments[1]) == review_mod.ReviewState.UNREVIEWED


# ---- 原稿不可變 ------------------------------------------------------------


def test_original_paragraphs_immutable_across_review_ops(tmp_path):
    doc = _doc()
    before = [p.text for p in doc.original.paragraphs]
    ledger = _ledger(doc)
    ledger.record(doc.segments[1], "accepted")
    doc.segments[1].text = "手動改寫後的補充文字。"
    ledger.record(doc.segments[1], "edited_accepted", note="edited")
    ledger.save(tmp_path / "l.json")
    to_markdown(doc, export_mode="accepted-only", ledger=ledger)
    to_markdown(doc, export_mode="review-draft", ledger=ledger)
    assert [p.text for p in doc.original.paragraphs] == before
    assert doc.original.full_text == ORIGINAL_TEXT
    assert doc.segments[0].text == ORIGINAL_TEXT


# ---- 審查佇列 --------------------------------------------------------------


def test_queue_items_and_summary_counts():
    doc = _doc()
    ledger = _ledger(doc)
    ledger.record(doc.segments[1], "accepted")
    ledger.record(doc.segments[2], "needs_more_evidence")

    items = {item["argument_id"]: item for item in ledger.queue_items(doc)}
    assert set(items) == {"argument:0", "argument:1", "argument:2"}
    card = items["argument:2"]
    assert card["state"] == review_mod.ReviewState.UNREVIEWED
    assert card["confidence"] == "pending_evidence"
    assert card["conflict_note"]
    assert {s["source_id"] for s in card["source_stances"]} == {"s3", "s4"}
    assert card["citation_spans"] == []
    assert card["sources"][0]["url"]

    summary = ledger.summary(doc)
    assert summary["accepted"] == 1
    assert summary["needs_more_evidence"] == 1
    # 待審 = unreviewed + stale + needs_more_evidence
    assert summary["pending"] == 2
    assert summary["total"] == 3
    assert summary["next_pending_argument_id"] == "argument:1"


# ---- Web 介面 ---------------------------------------------------------------


def _fixed_doc_for_server():
    return _doc()


@pytest.mark.anyio
async def test_review_endpoint_records_and_export_gate(async_client, monkeypatch, tmp_path):
    doc = _fixed_doc_for_server()
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(server, "run_pipeline", lambda path, llm, twinkle, law: doc)
    monkeypatch.setattr(server, "LEDGER_PATH", tmp_path / "review_ledger.json")
    server.app.state.review_ledger = None
    server.app.state.last_doc = None

    r = await async_client.post(
        "/run", files={"file": ("note.txt", ORIGINAL_TEXT.encode(), "text/plain")}
    )
    assert r.status_code == 200
    assert "待審" in r.text
    assert 'data-review-state="unreviewed"' in r.text
    assert 'action="/review"' in r.text

    r = await async_client.post(
        "/review",
        data={
            "argument_id": "argument:0",
            "decision": "accepted",
            "reason_code": "",
            "note": "看過來源",
            "reviewer": "op",
        },
    )
    assert r.status_code == 200
    assert 'data-review-state="accepted"' in r.text
    # 決策已落盤（不只存在瀏覽器/記憶體）;每份文件一個履歷檔（指紋命名）
    saved_files = list(tmp_path.glob("review_ledger.*.json"))
    assert len(saved_files) == 1
    saved = json.loads(saved_files[0].read_text(encoding="utf-8"))
    assert saved["records"][0]["decision"] == "accepted"

    r = await async_client.get("/export", params={"mode": "accepted-only"})
    assert r.status_code == 200
    assert "行政處分係指" in r.text
    assert "施行細節仍待查證" not in r.text
    assert "沒收處分應以判決為準" not in r.text


@pytest.mark.anyio
async def test_review_endpoint_rejects_unknown_argument(async_client, monkeypatch, tmp_path):
    doc = _fixed_doc_for_server()
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(server, "run_pipeline", lambda path, llm, twinkle, law: doc)
    monkeypatch.setattr(server, "LEDGER_PATH", tmp_path / "l.json")
    server.app.state.review_ledger = None
    await async_client.post(
        "/run", files={"file": ("note.txt", ORIGINAL_TEXT.encode(), "text/plain")}
    )
    r = await async_client.post(
        "/review", data={"argument_id": "argument:99", "decision": "accepted"}
    )
    assert r.status_code == 404
    r = await async_client.post(
        "/review", data={"argument_id": "argument:0", "decision": "bogus"}
    )
    assert r.status_code == 400
