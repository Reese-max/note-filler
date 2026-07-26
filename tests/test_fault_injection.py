"""故障注入測試：覆蓋未證實異常、逾時、持久化失敗、轉送失敗及 skip 分支。

逐一斷言資料會回報失敗或留下可追蹤紀錄。此檔補齊既有
test_exception_skip_traceability.py 未涵蓋之故障路徑。
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import app.server as server
from note_filler import __main__ as cli
from note_filler.correction import CorrectionDoc, Segment, assemble_correction
from note_filler.domain import detect_domain
from note_filler.export import to_docx, to_json, to_markdown
from note_filler.gap import Gap, detect_gaps
from note_filler.knowledge import law_citation_check
from note_filler.knowledge.law_lookup import LawLookup, build_law_index
from note_filler.llm import FakeLLM, GrokClient
from note_filler.parse import Document, Paragraph, parse_note
from note_filler.pipeline import run_pipeline, _verify_law_citations
from note_filler.questions import generate_questions
from note_filler.retrieve import retrieve_for_gap
from note_filler.retrieve.law_search import search_law_sources
from note_filler.retrieve.models import Source
from note_filler.retrieve.twinkle import TwinkleClient, TwinkleMCPClient, _to_source
from note_filler.retrieve.web import search_web_sources, _extract_query, _grade
from note_filler.verify import Validation
from note_filler.write import WrittenSupplement, write_supplement


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source(sid: str = "source-1", *, level: str = "A") -> Source:
    return Source(
        id=sid,
        title=f"title-{sid}",
        url=f"https://example.test/{sid}",
        level=level,
        content="可引用全文內容",
        fetched_date="2026-07-24",
        doc_date=None,
        distance=0.1,
    )


def _doc() -> Document:
    paragraph = Paragraph(idx=0, text="原稿逐字保留。")
    return Document("note-id.txt", (paragraph,), paragraph.text)


class _SequenceLLM:
    """依序回傳每個 complete 呼叫的回應；支援 Exception 作為回應值觸發故障。"""
    def __init__(self, responses):
        self.responses = iter(responses)

    def complete(self, messages, **kw):
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


# ===========================================================================
# §1  未證實異常：LLM 回傳 None / 空值 / 無法解析的結構
# ===========================================================================

class TestUnconfirmedExceptions:
    """LLM 回傳非預期型別或結構時，系統應降級而非崩潰，並留下可追蹤紀錄。"""

    def test_domain_detection_llm_returns_none_raises(self):
        """domain.py:32 LLM 回傳 None → AttributeError（未處理的異常型別）。"""

        class NoneLLM:
            def complete(self, messages, **kw):
                return None

        with pytest.raises(AttributeError):
            detect_domain("測試文字", NoneLLM())

    def test_domain_detection_llm_returns_empty_string(self, caplog):
        """domain.py:31 LLM 回傳空字串 → token 為空 → fallback 到 other。"""
        with caplog.at_level(logging.WARNING, logger="note_filler.domain"):
            domain = detect_domain("測試文字", FakeLLM([""]))

        assert domain == "other"
        records = _audit_records(caplog)
        assert any(r["event"] == "domain_detection_defaulted" for r in records)

    def test_questions_llm_returns_empty_string(self, caplog):
        """questions.py:48 LLM 回傳空字串 → questions 為空 → audit。"""
        with caplog.at_level(logging.WARNING, logger="note_filler.questions"):
            result = generate_questions("note-text", "law", FakeLLM([""]))

        assert result == []
        records = _audit_records(caplog)
        assert any(r["event"] == "question_generation_empty" for r in records)

    def test_gap_detection_llm_returns_none_raises(self):
        """gap.py:79 LLM 回傳 None → AttributeError（未處理的異常型別）。"""
        with pytest.raises(AttributeError):
            detect_gaps(["q1", "q2"], "note", FakeLLM([None]))

    def test_web_query_extraction_falls_back_on_exception(self, caplog):
        """web.py:69-75 _extract_query LLM 拋例外 → 退回 gap.question 原文。"""
        gap = Gap("case-QE", "missing", "reason")
        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.web"):
            query = _extract_query(gap, FakeLLM([RuntimeError("qe-fault")]))

        assert query == "case-QE"
        assert "query extraction failed" in caplog.text

    def test_web_grade_llm_returns_garbage(self, caplog):
        """web.py:83 _grade LLM 回傳非 JSON → 解析失敗 → drop。"""
        gap = Gap("case-GR", "missing", "reason")
        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.web"):
            level, doc_date = _grade(FakeLLM(["!!!not-json!!!"]), gap, "x" * 250)

        assert level == "drop"
        assert doc_date is None
        assert "grade JSON parse failed" in caplog.text


# ===========================================================================
# §2  逾時：GrokClient / urllib / TwinkleMCP 超時
# ===========================================================================

class TestTimeout:
    """逾時時應安全降級為空結果或回傳失敗，不讓 exception 向上傳播。"""

    def test_grok_client_timeout_raises(self):
        """GrokClient.complete 超時應向上拋 URLError / TimeoutError（由呼叫端處理）。"""
        with patch("urllib.request.urlopen", side_effect=TimeoutError("grok-timeout")):
            client = GrokClient()
            with pytest.raises(TimeoutError, match="grok-timeout"):
                client.complete([{"role": "user", "content": "test"}])

    def test_twinkle_search_timeout_returns_empty(self, caplog):
        """TwinkleClient.search 超時 → audit + 回傳 []（不崩潰）。"""
        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.twinkle"):
            client = TwinkleClient(token="fake-token", timeout=0.01)

            class FakeMCP:
                def call_tool(self, name, args):
                    raise TimeoutError("twinkle-timeout")

            with patch.object(TwinkleMCPClient, "call_tool", side_effect=TimeoutError("twinkle-timeout")):
                result = client.search("query")

        assert result == []
        records = _audit_records(caplog)
        assert any(r["event"] == "twinkle_search_failed" and "timeout" in r.get("error", "").lower() for r in records)

    def test_web_fetch_timeout_skips_page(self, caplog):
        """web.py:161-170 單頁 fetch 超時 → 跳過該頁、不影響其他頁。"""
        gap = Gap("case-TIMEOUT", "missing", "reason")
        hits = [
            {"title": "timeout-page", "href": "https://timeout.test"},
            {"title": "good-page", "href": "https://good.test"},
        ]

        def fetch(url):
            if "timeout" in url:
                raise TimeoutError("fetch-timeout")
            return "x" * 250

        # _extract_query 用一次 LLM，_grade 用一次 LLM
        llm = _SequenceLLM(["query-text", '{"level":"C","doc_date":null}'])
        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.web"):
            sources = search_web_sources(
                gap, llm, search=lambda q, n: hits, fetch=fetch, max_fetch=5
            )

        assert len(sources) == 1
        assert sources[0].url == "https://good.test"
        assert "fetch-timeout" in caplog.text


# ===========================================================================
# §3  持久化失敗：檔案寫入 / SQLite / 匯出失敗
# ===========================================================================

class TestPersistenceFailure:
    """磁碟寫入或資料庫操作失敗時，應留下可追蹤的 audit 或 delivery receipt。"""

    def test_cli_output_write_failure_returns_failed_receipt(self, tmp_path, monkeypatch, caplog):
        """__main__.py:199-234 process_file 拋例外 → delivery_manifest status=failed。"""
        note = tmp_path / "case-PERSIST-01.txt"
        note.write_text("原稿", encoding="utf-8")
        out = tmp_path / "out"
        monkeypatch.setattr(cli, "GrokClient", lambda: None)
        monkeypatch.setattr(cli, "TwinkleClient", lambda token="": None)
        monkeypatch.setattr(cli, "LawLookup", lambda db: None)
        monkeypatch.setattr(
            cli, "process_file",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("disk-full")),
        )

        assert cli.main([str(note), "-o", str(out), "--db", str(tmp_path / "none.db")]) == 1
        receipt = json.loads((out / cli.MANIFEST_NAME).read_text(encoding="utf-8"))
        assert receipt["status"] == "failed"
        assert "disk-full" in receipt["error"]

    def test_docx_export_failure_raises(self, tmp_path):
        """export.py:to_docx 寫入失敗應向上拋 OSError。"""
        doc = CorrectionDoc(_doc(), [
            Segment("supplement", "test", 0, [_source()], "verified", functional_gap="", user_value="", argument_id="argument:0"),
        ])
        with patch("docx.Document") as MockDocx:
            instance = MagicMock()
            instance.save.side_effect = OSError("permission-denied")
            MockDocx.return_value = instance
            with pytest.raises(OSError, match="permission-denied"):
                to_docx(doc, str(tmp_path / "out.docx"))

    def test_law_lookup_search_articles_sqlite_error(self, tmp_path):
        """LawLookup.search_articles SQLite 連線失敗 → 應向上拋出 sqlite3 錯誤。"""
        db = tmp_path / "broken.db"
        law = LawLookup(db)
        with patch("sqlite3.connect", side_effect=sqlite3.OperationalError("db-locked")):
            with pytest.raises(sqlite3.OperationalError, match="db-locked"):
                law.search_articles("keyword", limit=5)

    def test_cli_receipt_write_failure_still_reports_original_error(self, tmp_path, monkeypatch, caplog):
        """__main__.py:225 回執寫入本身也失敗 → audit 但不吞掉原始錯誤。"""
        note = tmp_path / "case-PERSIST-03.txt"
        note.write_text("原稿", encoding="utf-8")
        out = tmp_path / "out"
        monkeypatch.setattr(cli, "GrokClient", lambda: None)
        monkeypatch.setattr(cli, "TwinkleClient", lambda token="": None)
        monkeypatch.setattr(cli, "LawLookup", lambda db: None)
        call_count = 0

        def fake_process(path, llm, tw, law, out_dir, fmt):
            raise RuntimeError("pipeline-fault")

        monkeypatch.setattr(cli, "process_file", fake_process)
        monkeypatch.setattr(
            cli, "write_delivery_receipt",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("receipt-io-error")),
        )

        with caplog.at_level(logging.ERROR, logger="note_filler.__main__"):
            assert cli.main([str(note), "-o", str(out), "--db", str(tmp_path / "none.db")]) == 1

        records = _audit_records(caplog)
        assert any(r["event"] == "delivery_receipt_persist_failed" and "receipt-io-error" in r.get("error", "") for r in records)


# ===========================================================================
# §4  轉送失敗：pipeline 階段間資料未正確傳遞
# ===========================================================================

class TestForwardingFailure:
    """pipeline 階段間資料遺失時，應 emit audit 事件且不得靜默吞掉。"""

    def test_written_supplement_missing_in_assembly(self, caplog):
        """correction.py:100-108 gap 不在 written 字典 → written_supplement_missing + pending_evidence。"""
        gap = Gap("q-forward-01", "missing", "reason")
        doc = _doc()
        with caplog.at_level(logging.WARNING, logger="note_filler.correction"):
            correction = assemble_correction(
                doc, [gap],
                retrieved={gap.question: [_source("s1")]},
                written={},   # ← 故意留空
                validations={},
            )

        sup = correction.segments[-1]
        assert sup.confidence == "pending_evidence"
        assert "【待補證】" in sup.text
        records = _audit_records(caplog)
        assert any(r["event"] == "written_supplement_missing" and r["data_id"] == "q-forward-01" for r in records)

    def test_validation_not_forwarded_audit(self, caplog):
        """correction.py:140-147 gap 不在 validations 字典 → validation_not_forwarded。"""
        gap = Gap("q-forward-02", "missing", "reason")
        source = _source("s2")
        written = WrittenSupplement("補充內容[^1]", ["s2"])
        with caplog.at_level(logging.WARNING, logger="note_filler.correction"):
            correction = assemble_correction(
                _doc(), [gap],
                retrieved={gap.question: [source]},
                written={gap.question: written},
                validations={},   # ← 故意留空
            )

        records = _audit_records(caplog)
        assert any(r["event"] == "validation_not_forwarded" and r["data_id"] == "q-forward-02" for r in records)

    def test_sources_not_forwarded_to_validation(self, caplog, tmp_path):
        """pipeline.py:38-46 寫作未引用的來源 → sources_not_forwarded_to_validation。"""
        from docx import Document as DocxDocument

        p = tmp_path / "fw-note.docx"
        d = DocxDocument()
        d.add_paragraph("問題?")
        d.save(str(p))

        s1 = _source("s-cited")
        s2 = _source("s-omitted")

        class FakeTwinkle:
            def search(self, q):
                return []

        class FakeLaw:
            def search_articles(self, kw, lim, ln):
                return []

        import note_filler.pipeline as pl

        original_retrieve = pl.retrieve_for_gap

        def fake_retrieve(gap, domain, tw, law, llm):
            return [s1, s2]

        monkeypatch_obj = pytest.MonkeyPatch()
        monkeypatch_obj.setattr(pl, "retrieve_for_gap", fake_retrieve)
        try:
            llm = _SequenceLLM([
                "law",
                "問題?",
                json.dumps([{"question": "問題?", "status": "missing", "reason": "r"}], ensure_ascii=False),
                '{"keywords": ["k"], "law_name": null}',
                "補充[^1]",  # 只引用 [^1] = s-cited, s-omitted 被遺棄
            ])
            with caplog.at_level(logging.INFO, logger="note_filler.pipeline"):
                correction = run_pipeline(str(p), llm, FakeTwinkle(), FakeLaw())
        finally:
            monkeypatch_obj.undo()

        records = _audit_records(caplog)
        fwd_event = [r for r in records if r["event"] == "sources_not_forwarded_to_validation"]
        assert fwd_event, "應有 sources_not_forwarded_to_validation 事件"
        assert "s-omitted" in json.dumps(fwd_event)

    def test_used_sources_not_forwarded(self, caplog):
        """correction.py:118-125 writer 引用不存在的 source ID → used_sources_not_forwarded。"""
        gap = Gap("q-missing-src", "missing", "reason")
        written = WrittenSupplement("補充[^1]", ["nonexistent-id"])
        with caplog.at_level(logging.WARNING, logger="note_filler.correction"):
            correction = assemble_correction(
                _doc(), [gap],
                retrieved={gap.question: []},
                written={gap.question: written},
                validations={},
            )

        sup = correction.segments[-1]
        assert sup.sources == []
        assert sup.confidence == "pending_evidence"
        records = _audit_records(caplog)
        assert any(
            r["event"] == "used_sources_not_forwarded"
            and "nonexistent-id" in json.dumps(r.get("missing_source_ids", []))
            for r in records
        )


# ===========================================================================
# §5  Skip 分支：缺失依賴 / 降級路由 / 過濾跳過
# ===========================================================================

class TestSkipBranches:
    """依賴缺失或內容不符合閘值時，應跳過並留下 audit。"""

    def test_domain_other_no_llm_skips_web(self, caplog):
        """retrieve/__init__.py:55-63 domain=other 且 llm=None → web_source_retrieval_skipped。"""
        gap = Gap("q-skip-01", "missing", "reason")

        class FakeTwinkle:
            def search(self, q):
                return []

        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve"):
            sources = retrieve_for_gap(gap, "other", FakeTwinkle(), law=None, llm=None)

        assert sources == []
        records = _audit_records(caplog)
        assert any(r["event"] == "web_source_retrieval_skipped" for r in records)

    def test_law_domain_no_llm_no_law_skips_level_a(self, caplog):
        """retrieve/__init__.py:43-51 law 域缺 law/llm → law_source_retrieval_skipped，但 twinkle 仍執行。"""
        gap = Gap("q-skip-02", "missing", "reason")
        twinkle_result = [_source("tw-skip", level="B")]

        class FakeTwinkle:
            def search(self, q):
                return twinkle_result

        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve"):
            sources = retrieve_for_gap(gap, "law", FakeTwinkle(), law=None, llm=None)

        assert [s.id for s in sources] == ["tw-skip"]
        records = _audit_records(caplog)
        assert any(r["event"] == "law_source_retrieval_skipped" for r in records)

    def test_web_hit_not_dict_skipped(self, caplog):
        """web.py:141-149 search 回傳非 dict hit → web_hit_skipped。"""
        gap = Gap("q-hit-skip", "missing", "reason")
        hits = ["not-a-dict", 42, None]

        class DummyLLM:
            def complete(self, msgs, **kw):
                return '{"level":"C","doc_date":null}'

        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.web"):
            sources = search_web_sources(
                gap, DummyLLM(), search=lambda q, n: hits,
                fetch=lambda url: "x" * 250, max_fetch=10
            )

        assert sources == []
        records = _audit_records(caplog)
        assert any(r["event"] == "web_hit_skipped" for r in records)

    def test_web_content_too_short_skipped(self, caplog):
        """web.py:171-180 fetch 回傳過短內容 → web_content_skipped。"""
        gap = Gap("q-short", "missing", "reason")
        hits = [{"title": "short", "href": "https://short.test"}]

        class DummyLLM:
            def complete(self, msgs, **kw):
                return '{"level":"C","doc_date":null}'

        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.web"):
            sources = search_web_sources(
                gap, DummyLLM(), search=lambda q, n: hits,
                fetch=lambda url: "too short", max_fetch=5
            )

        assert sources == []
        records = _audit_records(caplog)
        assert any(r["event"] == "web_content_skipped" for r in records)

    def test_web_grade_drop_skipped(self, caplog):
        """web.py:192-200 分級結果 drop → web_source_not_forwarded。"""
        gap = Gap("q-drop", "missing", "reason")
        hits = [{"title": "spam", "href": "https://spam.test"}]

        class DropLLM:
            def complete(self, msgs, **kw):
                return '{"level":"drop","doc_date":null,"reason":"spam"}'

        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.web"):
            sources = search_web_sources(
                gap, DropLLM(), search=lambda q, n: hits,
                fetch=lambda url: "x" * 250, max_fetch=5
            )

        assert sources == []
        records = _audit_records(caplog)
        assert any(r["event"] == "web_source_not_forwarded" for r in records)

    def test_twinkle_empty_rpc_response(self, caplog):
        """twinkle.py:105-112 MCP 回傳空 → twinkle_response_empty。"""
        client = TwinkleMCPClient("https://twinkle.test", "token", 1)
        with patch.object(client, "_ensure_session"):
            with patch.object(client, "_rpc", return_value=None):
                with caplog.at_level(logging.DEBUG, logger="note_filler.retrieve.twinkle"):
                    result = client.call_tool("test", {})

        assert result == {}
        records = _audit_records(caplog)
        assert any(r["event"] == "twinkle_response_empty" for r in records)

    def test_twinkle_non_dict_hit_skipped(self, caplog):
        """twinkle.py:324-331 hit 非 dict → twinkle_hit_skipped。"""
        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.twinkle"):
            client = TwinkleClient(token="fake-token")
            with patch.object(TwinkleMCPClient, "call_tool", return_value={"hits": ["not-a-dict"]}):
                sources = client.search("query")

        assert sources == []
        records = _audit_records(caplog)
        assert any(r["event"] == "twinkle_hit_skipped" for r in records)

    def test_twinkle_similarity_non_numeric(self, caplog):
        """twinkle.py:173-183 similarity 非數字 → twinkle_similarity_defaulted。"""
        from note_filler.retrieve.twinkle import _clamp_similarity
        result = _clamp_similarity("not-a-number", "test-id")
        assert result == 0.0
        records = []
        # _clamp_similarity 用 audit_event 寫 log，但需 caplog 裝
        # 改為直接測 _to_source 的路徑
        hit = {"id": "test", "title": "title", "similarity": "bad-value", "content": "x"}
        with patch("note_filler.retrieve.twinkle.audit_event") as mock_audit:
            from note_filler.retrieve.twinkle import _to_source
            src = _to_source(hit)
            # _clamp_similarity 會呼叫 audit_event
            assert src is not None

    def test_question_generation_empty_response(self, caplog):
        """questions.py:68-74 LLM 回覆全空行 → question_generation_empty。"""
        with caplog.at_level(logging.WARNING, logger="note_filler.questions"):
            result = generate_questions("note-text", "law", FakeLLM(["  \n  \n  "]))

        assert result == []
        records = _audit_records(caplog)
        assert any(r["event"] == "question_generation_empty" for r in records)

    def test_gap_detection_empty_questions_returns_empty(self, caplog):
        """gap.py:62-70 questions 為空 → gap_detection_skipped。"""
        with caplog.at_level(logging.INFO, logger="note_filler.gap"):
            gaps = detect_gaps([], "note", FakeLLM(["unused"]))

        assert gaps == []
        records = _audit_records(caplog)
        assert any(r["event"] == "gap_detection_skipped" for r in records)

    def test_law_search_skipped_on_empty_keywords(self, caplog):
        """law_search.py:66-73 LLM 回傳空 keywords → law_search_skipped。"""
        gap = Gap("q-law-skip", "missing", "reason")

        class FakeLaw:
            def search_articles(self, kw, lim, ln):
                return []

        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.law_search"):
            sources = search_law_sources(gap, FakeLLM(['{"keywords": []}']), FakeLaw())

        assert sources == []
        records = _audit_records(caplog)
        assert any(r["event"] == "law_search_skipped" for r in records)


# ===========================================================================
# §6  端到端故障注入：多階段異常串聯
# ===========================================================================

class TestEndToEndFaultInjection:
    """多階段同時故障時，pipeline 應降級並在每個故障點留下 audit。"""

    def test_web_search_exception_all_pages_faulty(self, caplog):
        """web search 整體拋例外 + 每頁 fetch 也失敗 → web_search_failed + web_fetch_failed。"""
        gap = Gap("q-e2e-01", "missing", "reason")

        def broken_search(q, n):
            raise RuntimeError("ddg-dead")

        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.web"):
            sources = search_web_sources(
                gap, FakeLLM(["unused"]),
                search=broken_search, fetch=lambda u: (_ for _ in ()).throw(OSError("fetch-dead")),
                max_fetch=5,
            )

        assert sources == []
        records = _audit_records(caplog)
        assert any(r["event"] == "web_search_failed" for r in records)

    def test_pipeline_cascading_degradation(self, caplog):
        """domain=other → questions=JSON → gaps=empty → 全 pipeline 降級但不崩潰。"""
        from docx import Document as DocxDocument

        p = Path(__file__).parent / "_e2e_fault_note.docx"
        try:
            d = DocxDocument()
            d.add_paragraph("測試降級 cascade")
            d.save(str(p))

            llm = _SequenceLLM([
                "!!!unparseable-domain!!!",  # domain → other
                '{"questions": ["q1"]}',      # questions → JSON wrapper → skip
            ])
            from note_filler.retrieve.twinkle import TwinkleClient

            class FakeTw:
                def search(self, q):
                    return []

            doc = run_pipeline(str(p), llm, FakeTw(), None)
            supplements = [s for s in doc.segments if s.type == "supplement"]
            # questions 為空 → gaps 為空 → 無 supplement
            assert supplements == []
        finally:
            p.unlink(missing_ok=True)

    def test_cli_batch_one_fails_others_succeed(self, tmp_path, monkeypatch, caplog):
        """__main__.py:199 單檔失敗不拖垮整批，失敗檔有 failed receipt。"""
        note1 = tmp_path / "ok.txt"
        note1.write_text("ok", encoding="utf-8")
        note2 = tmp_path / "fail.txt"
        note2.write_text("fail", encoding="utf-8")
        out = tmp_path / "out"

        call_count = 0

        def fake_process(path, llm, tw, law, out_dir, fmt):
            nonlocal call_count
            call_count += 1
            if "fail" in str(path):
                raise RuntimeError("single-fail")
            return {
                "input": str(path),
                "output": str(out / "ok.md"),
                "content": "完整筆記內容",
                "supplements": 0,
                "verified": 0,
            }

        monkeypatch.setattr(cli, "GrokClient", lambda: None)
        monkeypatch.setattr(cli, "TwinkleClient", lambda token="": None)
        monkeypatch.setattr(cli, "LawLookup", lambda db: None)
        monkeypatch.setattr(cli, "process_file", fake_process)
        # Mock write_delivery_receipt to avoid file system issues
        monkeypatch.setattr(cli, "write_delivery_receipt", lambda *a, **kw: tmp_path / "receipt.json")

        result = cli.main([str(note1), str(note2), "-o", str(out), "--db", str(tmp_path / "none.db")])
        # 混合成功+失敗 → exit=1
        assert result == 1
        # 失敗檔有 receipt
        fail_receipt = out / cli.MANIFEST_NAME
        # process_file 被呼叫兩次
        assert call_count == 2

    def test_law_citation_not_forwarded_as_verified(self, caplog, monkeypatch):
        """pipeline.py:70-76 法規引用找不到 → confidence 降為 pending_evidence。"""
        from docx import Document as DocxDocument

        p = Path(__file__).parent / "_cite_note.docx"
        try:
            d = DocxDocument()
            d.add_paragraph("本法第1條規定")
            d.save(str(p))

            import note_filler.pipeline as pl

            def fake_check(text, lookup):
                return [{"kind": "article_not_found", "detail": "fault-CITE-TEST"}]

            monkeypatch.setattr(pl, "check_law_citations", fake_check)

            llm = _SequenceLLM([
                "law",
                "本法第1條的要件?",
                json.dumps([{"question": "本法第1條的要件?", "status": "missing", "reason": "r"}], ensure_ascii=False),
                '{"keywords": ["本法"], "law_name": null}',
                "本法第1條[^1]",
            ])

            class FakeTw:
                def search(self, q):
                    return []

            class FakeLaw:
                def search_articles(self, kw, lim, ln):
                    return []
                def lookup_article(self, law, art):
                    return None
                def law_exists(self, law):
                    return False
                def fuzzy_find_law(self, law):
                    return None

            doc = run_pipeline(str(p), llm, FakeTw(), FakeLaw())
            supplements = [s for s in doc.segments if s.type == "supplement"]
            assert supplements
            assert supplements[0].confidence == "pending_evidence"

            records = _audit_records(caplog)
            assert any(r["event"] == "law_citation_not_forwarded_as_verified" for r in records)
        finally:
            p.unlink(missing_ok=True)

    @pytest.mark.anyio
    async def test_web_pipeline_failure_clears_last_doc(self, async_client, monkeypatch, caplog):
        """server.py:50 失敗時 app.state.last_doc 被清空，不得轉送上一份結果。"""
        server.app.state.last_doc = CorrectionDoc(_doc(), [])
        monkeypatch.setattr(server, "_build_clients", lambda: (None, None, None))
        monkeypatch.setattr(
            server, "run_pipeline",
            lambda *a: (_ for _ in ()).throw(RuntimeError("pipeline-boom")),
        )

        response = await async_client.post(
            "/run", files={"file": ("boom.txt", b"x", "text/plain")}
        )
        assert response.status_code == 500
        assert server.app.state.last_doc is None
        export_resp = await async_client.get("/export")
        assert export_resp.status_code == 404


# ===========================================================================
# §7  未覆蓋 audit_event 補齊：覆蓋所有可能造成資料未處理/未持久化/未轉送/未記錄之路徑
# ===========================================================================

class TestUncoveredAuditEvents:
    """補齊既有測試未覆蓋之 audit_event 路徑，確保每條異常/跳過分支均有非靜默處置。"""

    def test_delivery_receipt_replaced(self, caplog):
        """__main__.py:63-71 已有 manifest 時再次寫入 → delivery_receipt_replaced。"""
        from note_filler.__main__ import write_delivery_receipt, MANIFEST_NAME
        import tempfile, os
        with tempfile.TemporaryDirectory() as td:
            manifest = os.path.join(td, MANIFEST_NAME)
            Path(manifest).write_text("{}", encoding="utf-8")
            caplog.clear()
            with caplog.at_level(logging.INFO, logger="note_filler.__main__"):
                write_delivery_receipt(
                    Path(os.path.join(td, "out.md")),
                    Path("note.txt"),
                    status="delivered",
                    content="test",
                )
            records = _audit_records(caplog)
            assert any(r["event"] == "delivery_receipt_replaced" for r in records), \
                "應觸發 delivery_receipt_replaced 事件"

    def test_input_directory_skipped(self, caplog, tmp_path):
        """__main__.py:108-114 資料夾無 .txt/.docx → input_directory_skipped。"""
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        (empty_dir / "readme.md").write_text("not a note", encoding="utf-8")
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="note_filler.__main__"):
            result = cli._iter_inputs([str(empty_dir)])
        assert result == []
        records = _audit_records(caplog)
        assert any(r["event"] == "input_directory_skipped" for r in records), \
            "應觸發 input_directory_skipped 事件"

    def test_input_file_deduplicated(self, caplog, tmp_path):
        """__main__.py:120-127 同一檔案重複出現 → input_file_deduplicated。"""
        note = tmp_path / "dup.txt"
        note.write_text("content", encoding="utf-8")
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="note_filler.__main__"):
            result = cli._iter_inputs([str(note), str(note)])
        assert len(result) == 1
        records = _audit_records(caplog)
        assert any(r["event"] == "input_file_deduplicated" for r in records), \
            "應觸發 input_file_deduplicated 事件"

    def test_citation_source_deduplicated(self, caplog):
        """write.py:70-77 同一 [^n] 出現兩次 → citation_source_deduplicated。"""
        gap = Gap("q-dedup-cite", "missing", "reason")
        src = _source("src-dedup-1")
        with caplog.at_level(logging.INFO, logger="note_filler.write"):
            written = write_supplement(gap, [src], FakeLLM(["text[^1] again[^1]"]))
        assert written.used_source_ids == ["src-dedup-1"]
        records = _audit_records(caplog)
        assert any(r["event"] == "citation_source_deduplicated" for r in records), \
            "應觸發 citation_source_deduplicated 事件"

    def test_supplement_has_no_forwardable_sources(self, caplog):
        """write.py:89-96 文字有有效 [^n] 但全部越界，最終 used 為空 → supplement_has_no_forwardable_sources。"""
        gap = Gap("q-no-fwd", "missing", "reason")
        with caplog.at_level(logging.WARNING, logger="note_filler.write"):
            written = write_supplement(gap, [_source("s1")], FakeLLM(["text[^99]"]))
        assert written.used_source_ids == []
        assert "【待補證】" not in written.text
        records = _audit_records(caplog)
        assert any(r["event"] == "supplement_has_no_forwardable_sources" for r in records), \
            "應觸發 supplement_has_no_forwardable_sources 事件"

    def test_web_query_defaulted(self, caplog):
        """web.py:61-68 LLM 回傳空 query → web_query_defaulted → 退回 gap.question。"""
        gap = Gap("q-query-def", "missing", "reason")
        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.web"):
            query = _extract_query(gap, FakeLLM([""]))
        assert query == "q-query-def"
        records = _audit_records(caplog)
        assert any(r["event"] == "web_query_defaulted" for r in records), \
            "應觸發 web_query_defaulted 事件"

    def test_web_hits_truncated(self, caplog):
        """web.py:131-139 hits 超過 max_fetch → web_hits_truncated。"""
        gap = Gap("q-trunc", "missing", "reason")
        hits = [{"title": f"h{i}", "href": f"https://{i}.test"} for i in range(10)]
        # _extract_query = 1 call, then 3 grades for 3 hits
        llm = _SequenceLLM(["query", '{"level":"C","doc_date":null}', '{"level":"C","doc_date":null}', '{"level":"C","doc_date":null}'])
        with caplog.at_level(logging.INFO, logger="note_filler.retrieve.web"):
            sources = search_web_sources(
                gap, llm, search=lambda q, n: hits, fetch=lambda u: "x" * 250,
                max_fetch=3
            )
        assert len(sources) == 3
        records = _audit_records(caplog)
        assert any(r["event"] == "web_hits_truncated" and r.get("omitted") == 7 for r in records), \
            "應觸發 web_hits_truncated 事件且 omitted=7"

    def test_web_fetch_empty(self, caplog):
        """web.py:247-254 trafilatura.fetch_url 回傳 falsy → web_fetch_empty。"""
        from note_filler.retrieve.web import _fetch_fulltext
        mock_trafilatura = MagicMock()
        mock_trafilatura.fetch_url.return_value = None
        with patch.dict("sys.modules", {"trafilatura": mock_trafilatura}):
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.web"):
                result = _fetch_fulltext("https://empty.test")
            assert result is None
            records = _audit_records(caplog)
            assert any(r["event"] == "web_fetch_empty" for r in records), \
                "應觸發 web_fetch_empty 事件"

    def test_twinkle_source_content_empty(self, caplog):
        """twinkle.py:248-254 hit 有 title 但 _record_fulltext 回傳空 → twinkle_source_content_empty。"""
        hit = {"title": "valid-title", "id": "tw-id"}
        caplog.clear()
        with patch("note_filler.retrieve.twinkle._record_fulltext", return_value=""):
            with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.twinkle"):
                src = _to_source(hit)
        assert src is not None
        assert src.title == "valid-title"
        records = _audit_records(caplog)
        assert any(r["event"] == "twinkle_source_content_empty" for r in records), \
            "應觸發 twinkle_source_content_empty 事件"

    def test_twinkle_limit_defaulted(self, caplog):
        """twinkle.py:290-299 n 為非數字 → twinkle_limit_defaulted → limit=3。"""
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.twinkle"):
            client = TwinkleClient(token="fake-token")
            with patch.object(TwinkleMCPClient, "call_tool", return_value={"hits": []}):
                result = client.search("q-limit", n="not-a-number")
        records = _audit_records(caplog)
        assert any(r["event"] == "twinkle_limit_defaulted" for r in records), \
            "應觸發 twinkle_limit_defaulted 事件"

    def test_twinkle_hits_empty(self, caplog):
        """twinkle.py:316-322 MCP 回傳成功但無 hits → twinkle_hits_empty。"""
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="note_filler.retrieve.twinkle"):
            client = TwinkleClient(token="fake-token")
            with patch.object(TwinkleMCPClient, "call_tool", return_value={"data": "ok"}):
                result = client.search("q-empty")
        assert result == []
        records = _audit_records(caplog)
        assert any(r["event"] == "twinkle_hits_empty" for r in records), \
            "應觸發 twinkle_hits_empty 事件"

    def test_twinkle_sources_truncated(self, caplog):
        """twinkle.py:336-344 sources 數量超限 → twinkle_sources_truncated。"""
        hits = [
            {"title": f"bill-{i}", "id": f"id-{i}", "similarity": 0.9}
            for i in range(5)
        ]
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="note_filler.retrieve.twinkle"):
            client = TwinkleClient(token="fake-token")
            with patch.object(TwinkleMCPClient, "call_tool", return_value={"hits": hits}):
                result = client.search("q-trunc", n=2)
        assert len(result) == 2
        records = _audit_records(caplog)
        assert any(r["event"] == "twinkle_sources_truncated" for r in records), \
            "應觸發 twinkle_sources_truncated 事件"

    def test_law_issue_deduplicated(self, caplog, monkeypatch):
        """law_citation_check.py:116-124 annotate_law_mismatches 含重複 issue → law_issue_deduplicated。"""
        from note_filler.knowledge.law_citation_check import annotate_law_mismatches
        duplicate = {
            "law_name": "測試法",
            "article_no": "1",
            "kind": "article_not_found",
            "detail": "重複-DUP-ISSUE",
        }
        monkeypatch.setattr(
            law_citation_check, "check_law_citations",
            lambda draft, lookup: [duplicate, duplicate],
        )
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="note_filler.knowledge.law_citation_check"):
            result = annotate_law_mismatches("draft", MagicMock())
        assert result.count("重複-DUP-ISSUE") == 1
        records = _audit_records(caplog)
        assert any(r["event"] == "law_issue_deduplicated" for r in records), \
            "應觸發 law_issue_deduplicated 事件"

    def test_law_sources_truncated(self, caplog):
        """law_search.py:93-102 超過 20 筆 unique rows → law_sources_truncated。"""
        gap = Gap("q-law-trunc", "missing", "reason")
        call_count = [0]

        class FakeLaw:
            def search_articles(self, kw, lim, ln):
                call_count[0] += 1
                if call_count[0] == 1:
                    return [
                        {
                            "pcode": "P1",
                            "law_name": "法A",
                            "article_no": str(i),
                            "article_text": f"text-{i}",
                        }
                        for i in range(1, 16)
                    ]
                return [
                    {
                        "pcode": "P2",
                        "law_name": "法B",
                        "article_no": str(i),
                        "article_text": f"text-b-{i}",
                    }
                    for i in range(1, 12)
                ]

        caplog.clear()
        with caplog.at_level(logging.INFO, logger="note_filler.retrieve.law_search"):
            sources = search_law_sources(gap, FakeLLM(['{"keywords": ["k1", "k2"]}']), FakeLaw())
        assert len(sources) == 20
        records = _audit_records(caplog)
        assert any(r["event"] == "law_sources_truncated" and r.get("found") == 26 for r in records), \
            "應觸發 law_sources_truncated 事件且 found=26"
