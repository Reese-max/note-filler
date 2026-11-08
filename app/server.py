from __future__ import annotations

import hashlib
import logging
import re
import math
import os
import secrets
import tempfile
import time
from contextvars import ContextVar
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from note_filler.export import EXPORT_MODES, to_markdown
from note_filler.audit import audit_event
from note_filler.llm import GrokClient
from note_filler.pipeline import run_pipeline
from note_filler.knowledge.law_lookup import LawLookup
from note_filler.review import (
    REASON_CODES, REVIEWABLE_DECISIONS, ReviewLedger,
    ReviewLedgerWriteConflict, doc_fingerprint,
)
from note_filler.retrieve.twinkle import TwinkleClient

logger = logging.getLogger(__name__)

# The pipeline can log note-derived questions and exception text.  Keep its
# ordinary diagnostics out of web upload logs, including inside AnyIO's worker
# thread; ContextVar is copied into run_in_threadpool without affecting CLI
# executions or other concurrent requests.
_redact_web_pipeline_logs: ContextVar[bool] = ContextVar(
    "note_filler_redact_web_pipeline_logs", default=False
)


def _install_web_log_redaction() -> None:
    current_factory = logging.getLogRecordFactory()
    if getattr(current_factory, "_note_filler_web_redaction", False):
        return

    def safe_factory(*args, **kwargs):
        record = current_factory(*args, **kwargs)
        if _redact_web_pipeline_logs.get():
            record.msg = "web_content_diagnostic_redacted"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return record

    safe_factory._note_filler_web_redaction = True
    logging.setLogRecordFactory(safe_factory)


_install_web_log_redaction()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
DB_PATH = os.environ.get(
    "NOTE_FILLER_DB", str(BASE_DIR.parent / "data" / "law_index.db")
)
# 決策履歷預設落在 gitignore 的 .task_state/(與任務狀態同層),可用環境變數改
LEDGER_PATH = Path(
    os.environ.get(
        "NOTE_FILLER_REVIEW_LEDGER",
        str(BASE_DIR.parent / ".task_state" / "review_ledger.json"),
    )
)

app = FastAPI(title="筆記補齊")
# Issue #4 — 匯出以不可猜測的 result capability 綁定,不再是 process-global
# last_doc。結果放進有 TTL/容量上限的 dict;重啟或過期一律 404,絕不落回
# 「最新一份文件」。
app.state.results: dict[str, dict] = {}

def _positive_float_setting(name: str, default: str) -> float:
    try:
        value = float(os.environ.get(name, default))
    except ValueError:
        raise ValueError(f"{name} must be a finite positive number") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return value


def _positive_int_setting(name: str, default: str) -> int:
    try:
        value = int(os.environ.get(name, default))
    except ValueError:
        raise ValueError(f"{name} must be a positive integer") from None
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


RESULT_TTL_SECONDS = _positive_float_setting("NOTE_FILLER_RESULT_TTL_SECONDS", "3600")
RESULT_MAX_ENTRIES = _positive_int_setting("NOTE_FILLER_RESULT_MAX_ENTRIES", "64")


def _evict_expired_results() -> None:
    now = time.monotonic()
    expired = [
        rid
        for rid, entry in app.state.results.items()
        if now - entry["created_at"] >= RESULT_TTL_SECONDS
    ]
    for rid in expired:
        app.state.results.pop(rid, None)


def _store_result(doc, *, review_owner: str | None = None) -> str:
    _evict_expired_results()
    result_id = secrets.token_urlsafe(16)
    app.state.results[result_id] = {
        "doc": doc,
        "generated_doc": doc,
        "created_at": time.monotonic(),
        "document_instance": uuid4().hex,
        "review_owner": review_owner or secrets.token_urlsafe(32),
    }
    while len(app.state.results) > RESULT_MAX_ENTRIES:
        oldest = min(
            app.state.results,
            key=lambda rid: app.state.results[rid]["created_at"],
        )
        app.state.results.pop(oldest, None)
    return result_id


def _lookup_result(result_id: str):
    entry = app.state.results.get(result_id)
    if entry is None:
        return None
    if time.monotonic() - entry["created_at"] >= RESULT_TTL_SECONDS:
        app.state.results.pop(result_id, None)
        return None
    return entry["doc"]


def _build_clients() -> tuple[GrokClient, TwinkleClient, LawLookup]:
    """建立三個注入用 client;測試會 monkeypatch 掉以避免真連線/開 DB。"""
    llm = GrokClient()
    twinkle = TwinkleClient(token=os.environ.get("TWINKLE_HUB_TOKEN", ""))
    law = LawLookup(DB_PATH)
    return llm, twinkle, law


REVIEW_OWNER_COOKIE = "note_filler_review_owner"


def _review_owner_for(request: Request) -> str:
    owner = request.cookies.get(REVIEW_OWNER_COOKIE, "")
    if re.fullmatch(r"[A-Za-z0-9_-]{43}", owner):
        return owner
    return secrets.token_urlsafe(32)


def _ledger_path_for(doc, result_id: str) -> Path:
    """Persist per browser owner and document; capabilities keep result access isolated."""
    owner = app.state.results[result_id]["review_owner"]
    scope = hashlib.sha256(owner.encode()).hexdigest()[:32]
    fingerprint = doc_fingerprint(doc)
    return LEDGER_PATH.with_name(
        f"{LEDGER_PATH.stem}.{scope}.{fingerprint[:16]}{LEDGER_PATH.suffix}"
    )


def _ledger_for(doc, result_id: str) -> ReviewLedger:
    entry = app.state.results[result_id]
    fingerprint = doc_fingerprint(doc)
    ledger = entry.get("review_ledger")
    path = _ledger_path_for(doc, result_id)
    if path.exists() or ledger is None or ledger.doc_fingerprint != fingerprint:
        ledger = ReviewLedger.load_for_document(path, doc)
        entry["review_ledger"] = ledger
    return ledger


def _document_instance_for(result_id: str) -> str:
    return app.state.results[result_id]["document_instance"]


def _render_result(
    request: Request,
    doc,
    *,
    result_id: str | None = None,
    status_filter: str | None = None,
    error: str | None = None,
    input_id=None,
    status_code: int = 200,
) -> HTMLResponse:
    """共用渲染:訂正稿 + 審查佇列(計數/篩選/下一筆待審)。"""
    context = {"doc": doc, "error": error, "input_id": input_id, "result_id": result_id}
    if doc is not None:
        ledger = _ledger_for(doc, result_id)
        replay = ledger.apply_overlays(app.state.results[result_id]["generated_doc"])
        app.state.results[result_id]["doc"] = replay
        doc = replay
        context["doc"] = doc
        context["document_instance"] = _document_instance_for(result_id)
        items = ledger.queue_items(doc)
        if status_filter:
            items = [i for i in items if i["state"] == status_filter]
        context.update(
            {
                "queue_by_arg": {i["argument_id"]: i for i in items},
                "review_summary": ledger.summary(doc),
                "reason_codes": sorted(REASON_CODES),
                "review_filter": status_filter or "",
            }
        )
    return TEMPLATES.TemplateResponse(
        request, "result.html", context, status_code=status_code,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"},
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "index.html")


@app.post("/run", response_class=HTMLResponse)
async def run(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    suffix = Path(file.filename or "note.txt").suffix or ".txt"
    data = await file.read()
    tmp_path = None
    result_id = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        llm, twinkle, law = _build_clients()
        log_token = _redact_web_pipeline_logs.set(True)
        try:
            doc = await run_in_threadpool(run_pipeline, tmp_path, llm, twinkle, law)
        finally:
            _redact_web_pipeline_logs.reset(log_token)
        owner = _review_owner_for(request)
        result_id = _store_result(doc, review_owner=owner)
        response = _render_result(request, doc, result_id=result_id)
        response.set_cookie(
            REVIEW_OWNER_COOKIE, owner, httponly=True, samesite="strict",
            secure=request.url.scheme == "https",
        )
        return response
    except Exception as exc:
        if result_id is not None:
            app.state.results.pop(result_id, None)
        audit_event(
            logger,
            "web_pipeline_failed",
            "web_upload",
            level=logging.ERROR,
            error_type=type(exc).__name__,
        )
        return TEMPLATES.TemplateResponse(
            request, "result.html",
            {
                "doc": None,
                "error": "筆記處理失敗，請檢查輸入或稍後重試。",
                "input_id": file.filename,
            },
            status_code=500,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError as exc:
                audit_event(
                    logger,
                    "temp_file_cleanup_failed",
                    "web_upload",
                    error_type=type(exc).__name__,
                )


@app.get("/result", response_class=HTMLResponse)
def result_without_capability() -> HTMLResponse:
    return PlainTextResponse("結果不存在或已過期,請重新上傳筆記。", status_code=404)


@app.post("/review", response_class=HTMLResponse)
def review_without_capability() -> HTMLResponse:
    return PlainTextResponse("結果不存在或已過期,請重新上傳筆記。", status_code=404)


@app.get("/result/{result_id}", response_class=HTMLResponse)
async def result(request: Request, result_id: str, filter: str | None = None) -> HTMLResponse:
    doc = _lookup_result(result_id)
    if doc is None:
        return PlainTextResponse("結果不存在或已過期,請重新上傳筆記。", status_code=404)
    return _render_result(request, doc, result_id=result_id, status_filter=filter)


@app.post("/review/{result_id}", response_class=HTMLResponse)
async def review_decision(request: Request, result_id: str) -> HTMLResponse:
    """Persist a revision only for the result capability and current form version."""
    doc = _lookup_result(result_id)
    if doc is None:
        return PlainTextResponse("結果不存在或已過期,請重新上傳筆記。", status_code=404)
    form = await request.form()
    if doc is not _lookup_result(result_id):
        return PlainTextResponse("訂正稿已變更,請重新載入後審查。", status_code=409)
    argument_id = str(form.get("argument_id") or "")
    decision = str(form.get("decision") or "")
    reason_code = str(form.get("reason_code") or "")
    note = str(form.get("note") or "")
    reviewer = str(form.get("reviewer") or "local")
    edited_text = str(form.get("edited_text") or "").strip()

    seg = next(
        (
            s
            for s in doc.segments
            if s.type == "supplement" and s.argument_id == argument_id
        ),
        None,
    )
    if seg is None:
        return PlainTextResponse(
            f"找不到可審查的論點:{argument_id}", status_code=404
        )

    # 先建立候選修訂;寫檔失敗時不發布未持久化的主張或決策。
    candidate = replace(seg)
    # 先驗證再修改:edited_text 只能搭配核准類決策,避免把拒絕/退回誤存成已核准
    if reason_code and reason_code not in REASON_CODES:
        return PlainTextResponse(
            f"審查決策不合法:reason_code {reason_code!r} 不在允許清單",
            status_code=400,
        )
    if edited_text:
        if decision not in ("accepted", "edited_accepted"):
            return PlainTextResponse(
                "審查決策不合法:帶修訂文字時 decision 只能是 accepted/edited_accepted",
                status_code=400,
            )
        if edited_text != seg.text:
            # 手動修改 claim 後不可沿用舊 ACCEPTED:建立 EDITED_ACCEPTED 新決策
            candidate.text = edited_text
            decision = "edited_accepted"
    elif decision == "edited_accepted":
        return PlainTextResponse(
            "審查決策不合法:edited_accepted 需附 edited_text", status_code=400
        )

    ledger = _ledger_for(doc, result_id)
    if decision not in {value.value for value in REVIEWABLE_DECISIONS}:
        return PlainTextResponse("審查決策不合法:未知 decision", status_code=400)
    expected_tokens = {
        **ledger.revision_tokens(doc, seg),
        "document_instance": _document_instance_for(result_id),
    }
    if any(str(form.get(key) or "") != value for key, value in expected_tokens.items()):
        return PlainTextResponse("訂正稿或審查版本已變更,請重新載入後審查。", status_code=409)
    ledger = ReviewLedger(ledger.doc_fingerprint, ledger.records)
    try:
        record = ledger.record(
            candidate,
            decision,
            reason_code=reason_code,
            note=note,
            reviewer=reviewer,
            base_segment=seg if candidate.text != seg.text else None,
        )
    except ValueError as exc:
        return PlainTextResponse(f"審查決策不合法:{exc}", status_code=400)
    try:
        ledger.save(_ledger_path_for(doc, result_id))
    except ReviewLedgerWriteConflict:
        return PlainTextResponse(
            "既有審查履歷無法讀取,已保留原檔。請先備份並修復履歷後重試。",
            status_code=409,
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
    doc = replace(doc, segments=[candidate if s is seg else s for s in doc.segments])
    app.state.results[result_id]["doc"] = doc
    app.state.results[result_id]["review_ledger"] = ledger
    audit_event(
        logger,
        "claim_review_decision_persisted",
        argument_id,
        level=logging.INFO,
        decision=record.decision.value,
        reason_code=record.reason_code,
    )
    return _render_result(request, doc, result_id=result_id)


@app.get("/export")
def export() -> PlainTextResponse:
    return PlainTextResponse(
        "尚無可匯出的訂正稿,請先上傳筆記。", status_code=404
    )


@app.get("/export/{result_id}")
async def export_result(result_id: str, mode: str = "review-draft") -> PlainTextResponse:
    doc = _lookup_result(result_id)
    if doc is None:
        return PlainTextResponse(
            "結果不存在或已過期,請重新上傳筆記。", status_code=404
        )
    if mode not in EXPORT_MODES:
        return PlainTextResponse(
            f"未知匯出模式:{mode}(允許: {', '.join(EXPORT_MODES)})", status_code=400,
        )
    try:
        log_token = _redact_web_pipeline_logs.set(True)
        try:
            ledger = _ledger_for(doc, result_id)
            generated = app.state.results[result_id]["generated_doc"]
            md = to_markdown(generated, export_mode=mode, ledger=ledger)
        finally:
            _redact_web_pipeline_logs.reset(log_token)
    except Exception as exc:
        audit_event(
            logger,
            "web_export_failed",
            "web_export",
            level=logging.ERROR,
            error_type=type(exc).__name__,
        )
        return PlainTextResponse(
            "匯出失敗,請稍後重試。",
            status_code=500,
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )
    headers = {
        "Content-Disposition": 'attachment; filename="correction.md"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    return PlainTextResponse(
        md, media_type="text/markdown; charset=utf-8", headers=headers
    )
