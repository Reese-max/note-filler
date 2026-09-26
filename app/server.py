from __future__ import annotations

import logging
import math
import os
import secrets
import tempfile
import time
from contextvars import ContextVar
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from note_filler.export import to_markdown
from note_filler.audit import audit_event
from note_filler.llm import GrokClient
from note_filler.pipeline import run_pipeline
from note_filler.knowledge.law_lookup import LawLookup
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


def _store_result(doc) -> str:
    _evict_expired_results()
    result_id = secrets.token_urlsafe(16)
    app.state.results[result_id] = {"doc": doc, "created_at": time.monotonic()}
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


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "index.html")


@app.post("/run", response_class=HTMLResponse)
async def run(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    suffix = Path(file.filename or "note.txt").suffix or ".txt"
    data = await file.read()
    tmp_path = None
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
        result_id = _store_result(doc)
        return TEMPLATES.TemplateResponse(
            request, "result.html", {"doc": doc, "result_id": result_id}
        )
    except Exception as exc:
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


@app.get("/export")
def export() -> PlainTextResponse:
    return PlainTextResponse(
        "尚無可匯出的訂正稿,請先上傳筆記。", status_code=404
    )


@app.get("/export/{result_id}")
async def export_result(result_id: str) -> PlainTextResponse:
    doc = _lookup_result(result_id)
    if doc is None:
        return PlainTextResponse(
            "結果不存在或已過期,請重新上傳筆記。", status_code=404
        )
    log_token = _redact_web_pipeline_logs.set(True)
    try:
        md = to_markdown(doc)
    finally:
        _redact_web_pipeline_logs.reset(log_token)
    headers = {
        "Content-Disposition": 'attachment; filename="correction.md"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    return PlainTextResponse(
        md, media_type="text/markdown; charset=utf-8", headers=headers
    )
