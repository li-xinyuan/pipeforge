import pytest
from httpx import AsyncClient, ASGITransport
from configforge.server import app


@pytest.mark.anyio
async def test_ai_suggest_returns_noop():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/ai/suggest", json={"category": "sql", "context": {"inputs": []}})
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
