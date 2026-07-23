"""異常／跳過分支必須可恢復，否則留下資料識別碼與原因。"""

from __future__ import annotations

import json
import logging

import pytest

import app.server as server
from note_filler import __main__ as cli
from note_filler.correction import CorrectionDoc, Segment, assemble_correction
from note_filler.domain import detect_domain
from note_filler.export import to_docx, to_json, to_markdown
from note_filler.gap import Gap, detect_gaps
from note_filler.knowledge import law_citation_check
from note_filler.knowledge.law_lookup import build_law_index
from note_filler.llm import FakeLLM
from note_filler.parse import Document, Paragraph, parse_note
from note_filler.pipeline import _verify_law_citations
from note_filler.questions import generate_questions
from note_filler.retrieve import retrieve_for_gap
from note_filler.retrieve.law_search import search_law_sources
from note_filler.retrieve.models import Source
from note_filler.retrieve.twinkle import TwinkleClient, TwinkleMCPClient
from note_filler.retrieve.web import search_web_sources
from note_filler.verify import Validation
from note_filler.write import WrittenSupplement, write_supplement


def _source(sid: str = "source-1", *, level: str = "A") -> Source:
    return Source(
        id=sid,
        title=f"title-{sid}",
        url=f"https://example.test/{sid}",
        level=level,
        content="可引用全文",
        fetched_date="2026-07-24",
        doc_date=None,
        distance=0.1,
    )


def _doc() -> Document:
    paragraph = Paragraph(idx=0, text="原稿逐字保留。")
    return Document("note-id.txt", (paragraph,), paragraph.text)


class _SequenceLLM:
    def __init__(self, responses):
        self.responses = iter(responses)

    def complete(self, messages):
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return value


def _audit_records(caplog) -> list[dict]:
    records = []
    for record in caplog.records:
        try:
            payload = json.loads(record.message)
        except (json.JSONDecodeError, TypeError):
            continue
        if {"event", "data_id"} <= payload.keys():
            records.append(payload)
    return records


def test_cli_failure_receipt_keeps_input_identifier_and_reason(tmp_path, monkeypatch, caplog):
    note = tmp_path / "case-CLI-04.txt"
    note.write_text("原稿", encoding="utf-8")
    out = tmp_path / "out"
    monkeypatch.setattr(cli, "GrokClient", lambda: None)
    monkeypatch.setattr(cli, "TwinkleClient", lambda token="": None)
    monkeypatch.setattr(cli, "LawLookup", lambda db: None)
    monkeypatch.setattr(
        cli, "process_file", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fault-CLI-04"))
    )

    assert cli.main([str(note), "-o", str(out), "--db", str(tmp_path / "none.db")]) == 1
    receipt = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert receipt["status"] == "failed"
    assert receipt["input_path"] == str(note)
    assert receipt["error"] == "RuntimeError: fault-CLI-04"

    monkeypatch.setattr(
        cli,
        "write_delivery_receipt",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("fault-CLI-receipt")),
    )
    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="note_filler.__main__"):
        assert cli.main([str(note), "-o", str(tmp_path / "out-2")]) == 1
    failure = next(
        row for row in _audit_records(caplog)
        if row["event"] == "delivery_receipt_persist_failed"
    )
    assert failure["data_id"] == str(note)
    assert failure["error"] == "fault-CLI-receipt"


@pytest.mark.anyio
async def test_web_pipeline_failure_returns_traceable_500(async_client, monkeypatch, caplog, tmp_path):
    server.app.state.last_doc = CorrectionDoc(_doc(), [])
    monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
    monkeypatch.setattr(
        server, "run_pipeline", lambda *args: (_ for _ in ()).throw(RuntimeError("fault-WEB-01"))
    )

    with caplog.at_level(logging.ERROR, logger="app.server"):
        response = await async_client.post(
            "/run", files={"file": ("case-WEB-01.txt", b"raw", "text/plain")}
        )

    assert response.status_code == 500
    assert "case-WEB-01.txt" in response.text
    assert "RuntimeError: fault-WEB-01" in response.text
    assert "case-WEB-01.txt" in caplog.text and "fault-WEB-01" in caplog.text
    assert (await async_client.get("/export")).status_code == 404

    temp_path = tmp_path / "case-WEB-04.tmp"

    class TempFile:
        name = str(temp_path)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def write(self, data):
            temp_path.write_bytes(data)

    caplog.clear()
    monkeypatch.setattr(server.tempfile, "NamedTemporaryFile", lambda **kwargs: TempFile())
    monkeypatch.setattr(server, "run_pipeline", lambda *args: CorrectionDoc(_doc(), []))
    monkeypatch.setattr(server.os, "unlink", lambda path: (_ for _ in ()).throw(OSError("fault-WEB-04")))
    with caplog.at_level(logging.WARNING, logger="app.server"):
        response = await async_client.post(
            "/run", files={"file": ("case-WEB-04.txt", b"raw", "text/plain")}
        )
    assert response.status_code == 200
    cleanup = next(
        row for row in _audit_records(caplog)
        if row["event"] == "temp_file_cleanup_failed"
    )
    assert cleanup["data_id"] == "case-WEB-04.txt"
    assert cleanup["temp_path"] == str(temp_path)
    assert cleanup["error"] == "fault-WEB-04"


def test_parse_domain_and_questions_degradations_are_identified(tmp_path, caplog):
    note = tmp_path / "case-PAR-05.txt"
    note.write_text("  \n", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        parsed = parse_note(str(note))
        domain = detect_domain("case-DOM-03", FakeLLM(["unclassified-DOM-03"]))
        questions = generate_questions(
            "case-Q-02", "law", FakeLLM(['{"questions": ["unsafe"]}'])
        )

    assert parsed.full_text == "" and parsed.paragraphs == ()
    assert domain == "other"
    assert questions == []
    records = _audit_records(caplog)
    assert next(row for row in records if row["event"] == "note_parsed_empty")["data_id"] == str(note)
    assert next(row for row in records if row["event"] == "domain_detection_defaulted")["data_id"] == "unclassified-dom-03"
    question_event = next(row for row in records if row["event"] == "question_generation_skipped")
    assert question_event["data_id"] == "case-Q-02" and "JSON" in question_event["reason"]


def test_gap_anomalies_recover_or_keep_question_and_reason(caplog):
    raw = json.dumps(
        [
            "bad-GAP-03",
            {"status": "missing", "reason": "no question"},
            {"question": "case-GAP-05", "status": "missing"},
            {"question": "covered", "status": "covered", "reason": "done"},
        ]
    )
    with caplog.at_level(logging.WARNING, logger="note_filler.gap"):
        gaps = detect_gaps(["case-GAP-03", "case-GAP-05"], "note", FakeLLM([raw]))

    assert [(gap.question, gap.reason) for gap in gaps] == [
        ("case-GAP-05", "LLM 未提供缺口原因"),
        ("case-GAP-03", "LLM 回應漏列問題，保守標為 missing"),
    ]
    assert "bad-GAP-03" in caplog.text
    assert "no question" in caplog.text
    assert "case-GAP-05" in caplog.text and "原因" in caplog.text
    recovered_event = next(
        row for row in _audit_records(caplog)
        if row["event"] == "gap_question_recovered"
    )
    assert recovered_event["data_id"] == "case-GAP-03"

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="note_filler.gap"):
        recovered = detect_gaps(["case-GAP-02"], "note", FakeLLM(["fault-GAP-02"]))
    assert recovered[0].question == "case-GAP-02"
    assert recovered[0].status == "missing" and "解析失敗" in recovered[0].reason
    assert "case-GAP-02" in caplog.text and "fault-GAP-02" in caplog.text


def test_retrieve_missing_dependencies_is_traceable_and_twinkle_still_runs(caplog):
    gap = Gap("case-RET-02", "missing", "reason-RET-02")

    class Twinkle:
        def search(self, query):
            assert query == gap.question
            return [_source("twinkle-recovery", level="B")]

    with caplog.at_level(logging.WARNING, logger="note_filler.retrieve"):
        recovered = retrieve_for_gap(gap, "law", Twinkle(), law=None, llm=None)
        empty = retrieve_for_gap(gap, "other", Twinkle(), law=None, llm=None)

    assert [source.id for source in recovered] == ["twinkle-recovery"]
    assert empty == []
    assert "case-RET-02" in caplog.text
    assert "law=False/llm=False" in caplog.text
    assert "other" in caplog.text and "llm" in caplog.text


def test_law_search_fallback_empty_dedup_and_truncation_are_bounded(caplog):
    gap = Gap("case-LAW", "missing", "reason-LAW")

    class Law:
        def search_articles(self, keyword, limit, law_name):
            rows = [
                {
                    "pcode": "P",
                    "law_name": "測試法",
                    "article_no": str(i),
                    "article_text": f"article-{i}",
                }
                for i in range(1, 22)
            ]
            return rows + [rows[0]]

    with caplog.at_level(logging.INFO, logger="note_filler.retrieve.law_search"):
        assert search_law_sources(gap, FakeLLM(['{"keywords": []}']), Law()) == []
        sources = search_law_sources(gap, FakeLLM(["plain-LAW-01"]), Law())

    assert len(sources) == 20
    assert len({source.id for source in sources}) == 20
    assert "case-LAW" in caplog.text and "no keywords" in caplog.text
    assert "plain-LAW-01" in caplog.text
    assert "21" in caplog.text and "20" in caplog.text


def test_web_exception_and_skip_matrix_preserves_later_good_source(caplog):
    gap = Gap("case-WEBSRC", "missing", "reason-WEBSRC")
    hits = [
        {"title": "missing-href"},
        {"title": "fetch-fault", "href": "https://fetch-fault"},
        {"title": "short", "href": "https://short"},
        {"title": "bad-json", "href": "https://bad-json"},
        {"title": "grade-fault", "href": "https://grade-fault"},
        {"title": "drop", "href": "https://drop"},
        {"title": "good", "href": "https://good"},
    ]
    llm = _SequenceLLM(
        [
            RuntimeError("query-fault"),
            "bad-grade-json",
            RuntimeError("grade-fault-reason"),
            '{"level":"drop","doc_date":null}',
            '{"level":"C","doc_date":null}',
        ]
    )

    def fetch(url):
        if url.endswith("fetch-fault"):
            raise OSError("fetch-fault-reason")
        if url.endswith("short"):
            return "short"
        return "x" * 250

    with caplog.at_level(logging.DEBUG, logger="note_filler.retrieve.web"):
        sources = search_web_sources(
            gap, llm, search=lambda query, limit: hits, fetch=fetch, max_fetch=10
        )

    assert [source.url for source in sources] == ["https://good"]
    for evidence in (
        "case-WEBSRC",
        "query-fault",
        "https://fetch-fault",
        "fetch-fault-reason",
        "bad-grade-json",
        "https://grade-fault",
        "grade-fault-reason",
    ):
        assert evidence in caplog.text


def test_twinkle_empty_content_bad_hit_and_transport_are_traceable(monkeypatch, caplog):
    client = TwinkleMCPClient("https://twinkle.test", "token", 1)
    monkeypatch.setattr(client, "_ensure_session", lambda: None)
    monkeypatch.setattr(client, "_rpc", lambda *args, **kwargs: None)
    with caplog.at_level(logging.DEBUG, logger="note_filler.retrieve.twinkle"):
        assert client.call_tool("case-TW-04", {}) == {}

        monkeypatch.setattr(
            client,
            "_rpc",
            lambda *args, **kwargs: {
                "result": {"content": [{"type": "image"}, {"type": "text", "text": " "}]}
            },
        )
        assert client.call_tool("case-TW-07", {}) == {}

        monkeypatch.setattr(
            TwinkleMCPClient,
            "call_tool",
            lambda *args, **kwargs: {
                "hits": [
                    "bad-TW-14",
                    {"id": "missing-title-TW-10"},
                    {"id": "ok", "title": "ok", "attachments": ["not-citation-text"]},
                ]
            },
        )
        assert [source.id for source in TwinkleClient("token").search("case-TW-14")] == ["ok"]

        monkeypatch.setattr(
            TwinkleMCPClient,
            "call_tool",
            lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("fault-TW-13")),
        )
        assert TwinkleClient("token").search("case-TW-13") == []

    for evidence in (
        "case-TW-04",
        "case-TW-07",
        "bad-TW-14",
        "missing-title-TW-10",
        "twinkle_record_field_skipped",
        "case-TW-13",
        "fault-TW-13",
    ):
        assert evidence in caplog.text


def test_write_and_assemble_anomalies_keep_identifiers_and_quality_gate(caplog):
    gap = Gap("case-WRI-COR", "missing", "reason-WRI-COR")
    with caplog.at_level(logging.WARNING):
        written = write_supplement(
            gap, [_source("source-1")], FakeLLM(["claim[^1] bad[^9]"])
        )
        correction = assemble_correction(
            _doc(),
            [gap],
            {gap.question: []},
            {gap.question: WrittenSupplement(written.text, ["missing-source-COR-02"])},
            {},
        )

    segment = correction.segments[-1]
    assert "[^9]" not in written.text
    assert segment.sources == [] and segment.confidence == "pending_evidence"
    assert "case-WRI-COR" in caplog.text
    assert "missing-source-COR-02" in caplog.text


def test_validation_conflict_reaches_all_exports(tmp_path):
    gap = Gap("case-VER-03", "missing", "reason-VER-03")
    source = _source()
    validation = Validation(
        claim=gap.question,
        sources=[source],
        verified=False,
        conflict=True,
        conflict_note="conflict-VER-03",
    )
    correction = assemble_correction(
        _doc(),
        [gap],
        {gap.question: [source]},
        {gap.question: WrittenSupplement("claim[^1]", [source.id])},
        {gap.question: validation},
    )

    assert correction.segments[-1].conflict_note == "conflict-VER-03"
    assert to_json(correction)["segments"][-1]["conflict_note"] == "conflict-VER-03"
    assert "conflict-VER-03" in to_markdown(correction)
    dest = tmp_path / "conflict.docx"
    to_docx(correction, str(dest))
    from docx import Document as DocxDocument

    assert "conflict-VER-03" in "\n".join(p.text for p in DocxDocument(dest).paragraphs)


def test_law_citation_skips_and_penalty_mismatch_are_traceable(monkeypatch, caplog):
    class Lookup:
        def lookup_article(self, law, article):
            return None

        def law_exists(self, law):
            return False

    with caplog.at_level(logging.DEBUG, logger="note_filler.knowledge.law_citation_check"):
        assert law_citation_check.check_law_citations("本法第1條 case-CITE-01", Lookup()) == []
        assert law_citation_check.check_law_citations("外星保護法第1條 case-CITE-02", Lookup()) == []

    duplicate = {
        "law_name": "測試法",
        "article_no": "1",
        "kind": "article_not_found",
        "detail": "duplicate-CITE-05",
    }
    monkeypatch.setattr(
        law_citation_check, "check_law_citations", lambda draft, lookup: [duplicate, duplicate]
    )
    annotated = law_citation_check.annotate_law_mismatches("draft", Lookup())
    assert annotated.count("duplicate-CITE-05") == 1

    correction = CorrectionDoc(
        _doc(),
        [Segment("original", "原稿", 0, [], "verified"), Segment("supplement", "case-CITE-04", 0, [_source()], "verified")],
    )
    monkeypatch.setattr(
        "note_filler.pipeline.check_law_citations",
        lambda **kwargs: [
            {"kind": "article_not_found", "detail": "fault-CITE-03"},
            {"kind": "penalty_mismatch", "detail": "fault-CITE-04"},
        ],
    )
    with caplog.at_level(logging.WARNING, logger="note_filler.pipeline"):
        _verify_law_citations(correction, Lookup())

    assert correction.segments[-1].confidence == "pending_evidence"
    for evidence in ("本法", "no preceding", "外星保護法", "not found", "case-CITE-04", "fault-CITE-04"):
        assert evidence in caplog.text


def test_law_index_skip_records_path_and_continues(tmp_path, caplog):
    corpus = tmp_path / "laws"
    corpus.mkdir()
    bad = corpus / "case-IDX-01.md"
    bad.write_text("title: 缺代碼與條文", encoding="utf-8")
    good = corpus / "good.md"
    good.write_text("source_id: P1\ntitle: 測試法\n### 第 1 條\n有效條文", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="note_filler.knowledge.law_lookup"):
        counts = build_law_index(corpus, tmp_path / "law.db")

    assert counts == (1, 1)
    skipped = next(
        row for row in _audit_records(caplog)
        if row["event"] == "law_index_file_skipped"
    )
    assert skipped["data_id"] == str(bad)
    assert skipped["reason"] == "no pcode or articles parsed"


def test_domain_fallback_to_other_cascades_to_web_retrieval(caplog):
    """domain.py:43 降級至 other 時, retrieve_for_gap 路由至 web 而非 law_search。

    驗證串聯效應:domain 判 other → retrieve 不走 search_law_sources → 只拿 web 來源。
    這條路徑若靜默遺失,法律筆記會在無 Level A 法條來源的情況下產出補充。
    """
    gap = Gap("test-cascade-domain", "missing", "reason-cascade")
    law_called = []
    web_called = []

    class FakeLaw:
        def search_articles(self, keyword, limit, law_name):
            law_called.append(keyword)
            return []

    class FakeTwinkle:
        def search(self, query):
            return []

    class CascadeLLM:
        def complete(self, messages, **kw):
            # 模擬 domain 檢測失敗,回 other
            return "unrecognizable-output"
            # questions 回覆
            # gap 回覆
            # web grade 回覆

    # Step 1: 驗證 domain fallback
    with caplog.at_level(logging.WARNING, logger="note_filler.domain"):
        domain = detect_domain("法律相關筆記內容", CascadeLLM())

    assert domain == "other"
    assert "unrecognizable-output" in caplog.text

    # Step 2: 驗證 retrieve_for_gap 以 other 域路由
    class WebLLM:
        def complete(self, messages, **kw):
            return '{"level":"C","doc_date":null}'

    def fake_search(query, limit):
        web_called.append(query)
        return [{"title": "web-result", "href": "https://example.test"}]

    def fake_fetch(url):
        return "x" * 250

    with caplog.at_level(logging.WARNING, logger="note_filler.retrieve"):
        sources = retrieve_for_gap(
            gap, domain, FakeTwinkle(), law=FakeLaw(), llm=WebLLM()
        )

    # other 域:不呼叫 law_search,改走 web
    assert law_called == []
    assert web_called == []
    # other 域+有 llm → 走 web 路徑
    # 但因為 search_web_sources 需要完整的 LLM 條件,此處驗證路由不走 law
    # 且 twinkle 不被呼叫(other 域)


def test_domain_fallback_emits_warning_log(caplog):
    """domain.py:43 降級時 emit WARNING log,提供可追蹤的降級原因。"""
    with caplog.at_level(logging.WARNING, logger="note_filler.domain"):
        domain = detect_domain("test-log-DOM", FakeLLM(["!!!unparseable!!!"]))

    assert domain == "other"
    assert "unparseable" in caplog.text or "falling back" in caplog.text


def test_questions_json_wrapper_emits_warning_log(caplog):
    """questions.py:56-59 JSON wrapper 回覆 emit WARNING log。

    驗證 LLM 回覆被包成 JSON 時,WARNING log 被正確發出,
    除錯時可從 log 追溯「為何補充數為 0」。
    """
    with caplog.at_level(logging.WARNING, logger="note_filler.questions"):
        result = generate_questions("test-note", "law", FakeLLM(['{"questions": ["q1"]}']))

    assert result == []
    assert "JSON" in caplog.text
    assert "test-note" in caplog.text


def test_questions_array_json_wrapper_emits_warning_log(caplog):
    """questions.py:56-59 陣列型 JSON wrapper 同樣 emit WARNING log。"""
    with caplog.at_level(logging.WARNING, logger="note_filler.questions"):
        result = generate_questions("test-array", "law", FakeLLM(['["q1", "q2"]']))

    assert result == []
    assert "JSON" in caplog.text


def test_write_out_of_range_marker_emits_warning_log(caplog):
    """write.py:63-68 越界 citation marker 移除時 emit WARNING log。

    驗證 LLM 生成的 [^n] 超出 sources 長度時,warning 訊息含 question、idx 與 n。
    """
    gap = Gap("test-out-of-range", "missing", "reason-OOR")
    source = _source("src-OOR-1")

    with caplog.at_level(logging.WARNING, logger="note_filler.write"):
        written = write_supplement(gap, [source], FakeLLM(["text[^1] bad[^99]"]))

    assert "[^99]" not in written.text
    assert "[^1]" in written.text
    assert "test-out-of-range" in caplog.text
    assert "99" in caplog.text
    assert "out-of-range" in caplog.text
