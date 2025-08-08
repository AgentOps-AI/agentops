import pytest
from httpx import ASGITransport


__all__ = [
    "async_app_client",
]


@pytest.fixture
async def async_app_client(event_loop):
    from httpx import AsyncClient

    from agentops.app import app

    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )
    yield client
    await client.aclose()  # Properly close the client
