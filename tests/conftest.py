import httpx
import pytest
import app.server as server


@pytest.fixture
async def async_client():
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
