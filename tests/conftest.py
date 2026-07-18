import httpx
import pytest
import app.server as server


def pytest_addoption(parser):
    parser.addoption(
        "--deselected-details",
        action="store_true",
        help="列出 deselected 測試的完整 node ID 與排除原因",
    )


def pytest_deselected(items):
    if not items or not items[0].config.getoption("deselected_details"):
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
        reason = f"--deselect {matched!r}" if matched else "collection filter"
        if reasons:
            reason = ", ".join(reasons)
        details[item.nodeid] = reason


def pytest_terminal_summary(terminalreporter, exitstatus, config):
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
