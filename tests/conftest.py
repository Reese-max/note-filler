import json

import httpx
import pytest
import app.server as server


def pytest_addoption(parser):
    parser.addoption(
        "--deselected-details",
        action="store_true",
        help="列出 deselected 測試的完整 node ID 與排除原因",
    )

    parser.addoption(
        "--collection-record-json",
        action="store_true",
        help="輸出一筆嚴格 JSON collection 記錄（不改變選取或執行）",
    )

def pytest_deselected(items):
    if not items or not (
        items[0].config.getoption("deselected_details")
        or items[0].config.getoption("collection_record_json")
    ):
        return
    config = items[0].config
    details = getattr(config, "_deselected_details", None)
    if details is None:
        details = config._deselected_details = {}
    reasons = []
    markexpr = config.getoption("markexpr")
    if markexpr:
        reasons.append(f"-m {markexpr!r}")
    keyword = config.getoption("keyword")
    if keyword:
        reasons.append(f"-k {keyword!r}")
    deselect = config.getoption("deselect") or []
    for item in items:
        matched = [prefix for prefix in deselect if item.nodeid.startswith(prefix)]
        item_reasons = list(reasons)
        if matched:
            item_reasons.append(f"--deselect {matched!r}")
        if not item_reasons:
            item_reasons.append("collection filter")
        details[item.nodeid] = ", ".join(item_reasons)


def pytest_collection_finish(session):
    if session.config.getoption("collection_record_json"):
        session.config._collection_record_selected = [item.nodeid for item in session.items]


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if config.getoption("collection_record_json"):
        selected = getattr(config, "_collection_record_selected", None)
        if selected is not None:
            details = getattr(config, "_deselected_details", {})
            record = {
                "schema": "note-filler.pytest-collection/v1",
                "selected": selected,
                "deselected": [
                    {"node_id": nodeid, "reason": f"deselected by {reason}"}
                    for nodeid, reason in sorted(details.items())
                ],
            }
            terminalreporter.write_line(
                "NOTE_FILLER_COLLECTION_JSON_V1=" + json.dumps(record, ensure_ascii=True)
            )
    if not config.getoption("deselected_details"):
        return
    details = getattr(config, "_deselected_details", {})
    if not details:
        return
    terminalreporter.write_sep("=", "deselected details")
    for nodeid, reason in sorted(details.items()):
        terminalreporter.write_line(f"{nodeid} | reason: deselected by {reason}")


@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
