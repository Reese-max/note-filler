from __future__ import annotations

import logging
import os
import tempfile
import traceback
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from note_filler.export import to_markdown
from note_filler.audit import audit_event
from note_filler.llm import GrokClient
from note_filler.pipeline import run_pipeline
from note_filler.knowledge.law_lookup import LawLookup
from note_filler.retrieve.twinkle import TwinkleClient

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))
DB_PATH = os.environ.get(
    "NOTE_FILLER_DB", str(BASE_DIR.parent / "data" / "law_index.db")
)

app = FastAPI(title="筆記補齊")
app.state.last_doc = None


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
    app.state.last_doc = None  # 本次失敗時不得讓 /export 轉送上一份成功結果
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        llm, twinkle, law = _build_clients()
        doc = run_pipeline(tmp_path, llm, twinkle, law)
        app.state.last_doc = doc  # 供 /export 使用
        return TEMPLATES.TemplateResponse(
            request, "result.html", {"doc": doc}
        )
    except Exception as exc:
        tb = traceback.format_exc()
        audit_event(
            logger,
            "web_pipeline_failed",
            file.filename or "upload:unnamed",
            level=logging.ERROR,
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=tb,
        )
        return TEMPLATES.TemplateResponse(
            request, "result.html",
            {
                "doc": None,
                "error": f"{type(exc).__name__}: {exc}",
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


@app.get("/export")
def export() -> PlainTextResponse:
    doc = app.state.last_doc
    if doc is None:
        return PlainTextResponse(
            "尚無可匯出的訂正稿,請先上傳筆記。", status_code=404
        )
    md = to_markdown(doc)
    headers = {"Content-Disposition": 'attachment; filename="correction.md"'}
    return PlainTextResponse(
        md, media_type="text/markdown; charset=utf-8", headers=headers
    )
