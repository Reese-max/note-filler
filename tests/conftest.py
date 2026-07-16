import httpx
import pytest
import app.server as server


@pytest.fixture
def async_client():
    transport = httpx.ASGITransport(app=server.app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")
