from __future__ import annotations

import logging
import os
import tempfile
import traceback
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from note_filler.export import EXPORT_MODES, to_markdown
from note_filler.audit import audit_event
from note_filler.llm import GrokClient
from note_filler.pipeline import run_pipeline
from note_filler.knowledge.law_lookup import LawLookup
from note_filler.review import REASON_CODES, ReviewLedger, doc_fingerprint
from note_filler.retrieve.twinkle import TwinkleClient

logger = logging.getLogger(__name__)

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
app.state.last_doc = None
app.state.review_ledger = None


def _build_clients() -> tuple[GrokClient, TwinkleClient, LawLookup]:
    """建立三個注入用 client;測試會 monkeypatch 掉以避免真連線/開 DB。"""
    llm = GrokClient()
    twinkle = TwinkleClient(token=os.environ.get("TWINKLE_HUB_TOKEN", ""))
    law = LawLookup(DB_PATH)
    return llm, twinkle, law


def _ledger_path_for(doc) -> Path:
    """每份文件一份履歷檔(以文件指紋命名),避免新文件覆寫舊文件的決策歷史。"""
    fingerprint = doc_fingerprint(doc)
    return LEDGER_PATH.with_name(
        f"{LEDGER_PATH.stem}.{fingerprint[:16]}{LEDGER_PATH.suffix}"
    )


def _ledger_for(doc) -> ReviewLedger:
    """回傳綁定目前文件的履歷;文件不同則從磁碟重播或重建(fail closed)。"""
    fingerprint = doc_fingerprint(doc)
    ledger = getattr(app.state, "review_ledger", None)
    if ledger is None or ledger.doc_fingerprint != fingerprint:
        ledger = ReviewLedger.load_for_document(_ledger_path_for(doc), doc)
        app.state.review_ledger = ledger
    return ledger


def _render_result(
    request: Request,
    doc,
    *,
    status_filter: str | None = None,
    error: str | None = None,
    input_id=None,
    status_code: int = 200,
) -> HTMLResponse:
    """共用渲染:訂正稿 + 審查佇列(計數/篩選/下一筆待審)。"""
    context = {"doc": doc, "error": error, "input_id": input_id}
    if doc is not None:
        ledger = _ledger_for(doc)
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
        request, "result.html", context, status_code=status_code
    )


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
        app.state.last_doc = doc  # 供 /export、/review、/result 使用
        _ledger_for(doc)          # 載入/重建本文件的決策履歷
        return _render_result(request, doc)
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
        return _render_result(
            request,
            None,
            error=f"{type(exc).__name__}: {exc}",
            input_id=file.filename,
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


@app.get("/result", response_class=HTMLResponse)
def result(request: Request, filter: str | None = None) -> HTMLResponse:
    """重看上一份訂正稿的審查佇列;filter 只顯示特定審查狀態。"""
    doc = app.state.last_doc
    if doc is None:
        return PlainTextResponse("尚無訂正稿,請先上傳筆記。", status_code=404)
    return _render_result(request, doc, status_filter=filter)


@app.post("/review", response_class=HTMLResponse)
async def review_decision(request: Request) -> HTMLResponse:
    """記錄一筆主張級人工決策並落盤;修訂文字一律轉 EDITED_ACCEPTED。"""
    doc = app.state.last_doc
    if doc is None:
        return PlainTextResponse("尚無訂正稿,請先上傳筆記。", status_code=404)
    form = await request.form()
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
            seg.text = edited_text
            decision = "edited_accepted"
    elif decision == "edited_accepted":
        return PlainTextResponse(
            "審查決策不合法:edited_accepted 需附 edited_text", status_code=400
        )

    ledger = _ledger_for(doc)
    try:
        record = ledger.record(
            seg,
            decision,
            reason_code=reason_code,
            note=note,
            reviewer=reviewer,
        )
    except ValueError as exc:
        return PlainTextResponse(f"審查決策不合法:{exc}", status_code=400)
    ledger.save(_ledger_path_for(doc))
    audit_event(
        logger,
        "claim_review_decision_persisted",
        argument_id,
        level=logging.INFO,
        decision=record.decision.value,
        reason_code=record.reason_code,
        reviewer=record.reviewer,
        ledger_path=str(LEDGER_PATH),
    )
    return _render_result(request, doc)


@app.get("/export")
def export(mode: str = "review-draft") -> PlainTextResponse:
    doc = app.state.last_doc
    if doc is None:
        return PlainTextResponse(
            "尚無可匯出的訂正稿,請先上傳筆記。", status_code=404
        )
    if mode not in EXPORT_MODES:
        return PlainTextResponse(
            f"未知匯出模式:{mode}(允許: {', '.join(EXPORT_MODES)})",
            status_code=400,
        )
    ledger = _ledger_for(doc)
    md = to_markdown(doc, export_mode=mode, ledger=ledger)
    headers = {"Content-Disposition": 'attachment; filename="correction.md"'}
    return PlainTextResponse(
        md, media_type="text/markdown; charset=utf-8", headers=headers
    )
