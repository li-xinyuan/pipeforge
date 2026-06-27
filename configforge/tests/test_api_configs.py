import pytest
from httpx import ASGITransport, AsyncClient

from configforge.models.wizard import (
    SaveConfigRequest,
    SceneInfo,
    WizardState,
)
from configforge.server import app


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
    assert "configs" in data
    assert isinstance(data["configs"], list)


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


@pytest.mark.anyio
async def test_export_config_yaml():
    state = _make_state()
    req = SaveConfigRequest(state=state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/configs", json=req.model_dump())
        config_id = resp.json()["id"]

        # Export as YAML
        resp = await client.get(f"/api/configs/{config_id}/export?format=yaml")
        assert resp.status_code == 200
        assert "application/x-yaml" in resp.headers.get("content-type", "")
        content_disp = resp.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert ".yaml" in content_disp
        body = resp.text
        assert "scene:" in body
        assert "Test Config" in body

        # Cleanup
        await client.delete(f"/api/configs/{config_id}")


@pytest.mark.anyio
async def test_export_config_json():
    state = _make_state()
    req = SaveConfigRequest(state=state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/configs", json=req.model_dump())
        config_id = resp.json()["id"]

        resp = await client.get(f"/api/configs/{config_id}/export?format=json")
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")
        data = resp.json()
        assert data["scene"]["name"] == "Test Config"
        assert "_export" in data
        assert data["_export"]["config_id"] == config_id

        await client.delete(f"/api/configs/{config_id}")


@pytest.mark.anyio
async def test_export_config_invalid_format():
    state = _make_state()
    req = SaveConfigRequest(state=state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/configs", json=req.model_dump())
        config_id = resp.json()["id"]

        resp = await client.get(f"/api/configs/{config_id}/export?format=xml")
        assert resp.status_code == 400

        await client.delete(f"/api/configs/{config_id}")


@pytest.mark.anyio
async def test_export_config_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/configs/nonexistent_id/export")
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_import_config_yaml():
    """Export a config as YAML, then import it as a new config."""
    state = _make_state()
    req = SaveConfigRequest(state=state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create and export
        resp = await client.post("/api/configs", json=req.model_dump())
        original_id = resp.json()["id"]

        resp = await client.get(f"/api/configs/{original_id}/export?format=yaml")
        assert resp.status_code == 200
        yaml_content = resp.text

        # Import as new config
        resp = await client.post(
            "/api/configs/import",
            files={"file": ("test.yaml", yaml_content.encode("utf-8"), "application/x-yaml")},
        )
        assert resp.status_code == 200
        imported = resp.json()
        assert "id" in imported
        new_id = imported["id"]
        assert new_id != original_id
        assert imported["scene_name"] == "Test Config"

        # Verify the imported config exists and has correct data
        resp = await client.get(f"/api/configs/{new_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scene"]["name"] == "Test Config"

        # Cleanup
        await client.delete(f"/api/configs/{original_id}")
        await client.delete(f"/api/configs/{new_id}")


@pytest.mark.anyio
async def test_import_config_json():
    """Import a config from a JSON file."""
    state = _make_state()
    req = SaveConfigRequest(state=state)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/configs", json=req.model_dump())
        original_id = resp.json()["id"]

        resp = await client.get(f"/api/configs/{original_id}/export?format=json")
        json_content = resp.text

        resp = await client.post(
            "/api/configs/import",
            files={"file": ("test.json", json_content.encode("utf-8"), "application/json")},
        )
        assert resp.status_code == 200
        new_id = resp.json()["id"]
        assert new_id != original_id

        await client.delete(f"/api/configs/{original_id}")
        await client.delete(f"/api/configs/{new_id}")


@pytest.mark.anyio
async def test_import_config_invalid_content():
    """Importing invalid content should return 400/422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Invalid YAML
        resp = await client.post(
            "/api/configs/import",
            files={"file": ("bad.yaml", b":::not valid yaml::: [[[", "application/x-yaml")},
        )
        # Either YAML parse fails or it parses but WizardState validation fails
        assert resp.status_code in (400, 422)

        # Valid YAML but not a valid WizardState
        resp = await client.post(
            "/api/configs/import",
            files={"file": ("bad.yaml", b"just: a string", "application/x-yaml")},
        )
        assert resp.status_code in (400, 422)


@pytest.mark.anyio
async def test_import_config_no_file():
    """Importing without a file should return 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/configs/import")
        assert resp.status_code == 422
