from __future__ import annotations

import logging
import os
import secrets
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from note_filler.export import to_markdown
from note_filler.audit import audit_event, private_logs
from note_filler.llm import GrokClient
from note_filler.pipeline import run_pipeline
from note_filler.knowledge.law_lookup import LawLookup
from note_filler.retrieve.twinkle import TwinkleClient

from .result_store import EXPIRED, OK, ResultStore

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
DB_PATH = os.environ.get(
    "NOTE_FILLER_DB", str(BASE_DIR.parent / "data" / "law_index.db")
)
SESSION_COOKIE = "nf_session"
RESULT_TTL_SECONDS = float(
    os.environ.get("NOTE_FILLER_RESULT_TTL_SECONDS", "3600")
)

app = FastAPI(title="筆記補齊")
app.state.results = ResultStore(ttl_seconds=RESULT_TTL_SECONDS)


def _build_clients() -> tuple[GrokClient, TwinkleClient, LawLookup]:
    """建立三個注入用 client;測試會 monkeypatch 掉以避免真連線/開 DB。"""
    llm = GrokClient()
    twinkle = TwinkleClient(token=os.environ.get("TWINKLE_HUB_TOKEN", ""))
    law = LawLookup(DB_PATH)
    return llm, twinkle, law


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    response = TEMPLATES.TemplateResponse(request, "index.html")
    if SESSION_COOKIE not in request.cookies:
        # 首頁即建立 session:避免新 client 併發 /run 時各自鑄造
        # session、最後一個 Set-Cookie 覆蓋導致先到的結果被孤立。
        response.set_cookie(
            SESSION_COOKIE,
            secrets.token_urlsafe(32),
            httponly=True,
            samesite="lax",
        )
    return response


@app.post("/run", response_class=HTMLResponse)
async def run(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    suffix = Path(file.filename or "note.txt").suffix or ".txt"
    tmp_path = None
    session = request.cookies.get(SESSION_COOKIE)
    issue_cookie = session is None
    if issue_cookie:
        session = secrets.token_urlsafe(32)
    # 本次失敗時不得讓 /export 轉送上一份成功結果;
    # 只清掉自己 session 的舊結果,不影響其他 client。
    app.state.results.discard_owner(session)
    try:
        data = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        with private_logs(file.filename or "upload:unnamed"):
            llm, twinkle, law = _build_clients()
            doc = await run_in_threadpool(run_pipeline, tmp_path, llm, twinkle, law)
        result_id = app.state.results.put(doc, session)
        response = TEMPLATES.TemplateResponse(
            request, "result.html",
            {"doc": doc, "export_url": f"/export/{result_id}"},
        )
    except Exception as exc:
        audit_event(
            logger,
            "web_pipeline_failed",
            file.filename or "upload:unnamed",
            level=logging.ERROR,
            error_type=type(exc).__name__,
        )
        response = TEMPLATES.TemplateResponse(
            request, "result.html",
            {
                "doc": None,
                "error": "處理失敗，請檢查檔案格式或稍後重試。",
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
                    file.filename or tmp_path,
                    temp_path=tmp_path,
                    error=str(exc),
                )
    if issue_cookie:
        response.set_cookie(SESSION_COOKIE, session, httponly=True, samesite="lax")
    return response


@app.get("/export")
def export() -> PlainTextResponse:
    """裸 /export 不帶結果身分:一律確定性 404,永不回退到「最新一份」。"""
    return PlainTextResponse(
        "匯出需使用本次訂正結果頁提供的下載連結。", status_code=404
    )


@app.get("/export/{result_id}")
async def export_result(request: Request, result_id: str) -> PlainTextResponse:
    status, doc = app.state.results.get(
        result_id, request.cookies.get(SESSION_COOKIE)
    )
    if status == OK:
        with private_logs("export"):
            md = await run_in_threadpool(to_markdown, doc)
        headers = {"Content-Disposition": 'attachment; filename="correction.md"'}
        return PlainTextResponse(
            md, media_type="text/markdown; charset=utf-8", headers=headers
        )
    if status == EXPIRED:
        return PlainTextResponse(
            "該訂正稿已過期,請重新上傳筆記。", status_code=410
        )
    return PlainTextResponse(
        "找不到可匯出的訂正稿,請先上傳筆記。", status_code=404
    )
