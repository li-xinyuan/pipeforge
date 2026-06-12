import pytest
from httpx import AsyncClient, ASGITransport
from configforge.server import app
from configforge.models.wizard import (
    WizardState,
    SceneInfo,
    SaveConfigRequest,
    ExecuteConfigRequest,
)


def _make_state() -> WizardState:
    return WizardState(
        current_step=1,
        scene=SceneInfo(name="Test Config", description="test", version="1.0"),
    )


@pytest.mark.anyio
async def test_list_configs_empty():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/configs")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.anyio
async def test_save_and_get_config():
    state = _make_state()
    req = SaveConfigRequest(state=state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Save
        resp = await client.post("/api/configs", json=req.model_dump())
        assert resp.status_code == 200
        saved = resp.json()
        config_id = saved["id"]
        assert config_id

        # Get
        resp = await client.get(f"/api/configs/{config_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scene"]["name"] == "Test Config"

        # Delete
        resp = await client.delete(f"/api/configs/{config_id}")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


@pytest.mark.anyio
async def test_delete_config():
    state = _make_state()
    req = SaveConfigRequest(state=state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/configs", json=req.model_dump())
        config_id = resp.json()["id"]

        resp = await client.delete(f"/api/configs/{config_id}")
        assert resp.status_code == 200

        resp = await client.get(f"/api/configs/{config_id}")
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_config_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/configs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_config_validation_rejects_traversal():
    """Path traversal via '...' (not normalized by ASGI) should be rejected."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # '...' contains '..' but is not normalized by ASGI routers
        resp = await client.get("/api/configs/...secret")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_encoded_traversal_blocked_by_middleware():
    """URL-encoded path traversal should be blocked by middleware."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/configs/..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_download_yaml():
    state = _make_state()
    req = SaveConfigRequest(state=state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/configs", json=req.model_dump())
        config_id = resp.json()["id"]

        resp = await client.get(f"/api/configs/{config_id}/yaml")
        assert resp.status_code == 200
        assert "application/x-yaml" in resp.headers.get("content-type", "")
