"""Tests for templates API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

from configforge.server import app


@pytest.fixture(autouse=True)
def _mock_template_store(tmp_path, monkeypatch):
    """Use a fresh in-memory template store for each test."""
    monkeypatch.setenv("CONFIGFORGE_DATA_DIR", str(tmp_path / "data"))
    # Clear the template cache
    from configforge.services.template_store import _cache
    _cache.invalidate("templates")


class TestListTemplates:
    @pytest.mark.anyio
    async def test_list_templates_empty(self):
        """Listing templates when none exist should return empty list."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.anyio
    async def test_list_templates_after_create(self):
        """Listing templates after creating one should include it."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create a template
            await client.post("/api/templates", json={
                "name": "Test Template",
                "description": "A test template",
                "category": "general",
                "tags": ["test"],
                "config_state": {"inputs": [], "processors": []},
                "author": "tester",
            })
            resp = await client.get("/api/templates")
        data = resp.json()
        assert data["total"] >= 1
        names = [t["name"] for t in data["items"]]
        assert "Test Template" in names

    @pytest.mark.anyio
    async def test_list_templates_filter_by_category(self):
        """Filtering by category should return only matching templates."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post("/api/templates", json={
                "name": "Sales Report",
                "description": "desc",
                "category": "sales",
                "tags": [],
                "config_state": {"inputs": [], "processors": []},
            })
            await client.post("/api/templates", json={
                "name": "HR Report",
                "description": "desc",
                "category": "hr",
                "tags": [],
                "config_state": {"inputs": [], "processors": []},
            })
            resp = await client.get("/api/templates", params={"category": "sales"})
        data = resp.json()
        assert all(t["category"] == "sales" for t in data["items"])


class TestGetTemplate:
    @pytest.mark.anyio
    async def test_get_template_not_found(self):
        """Getting a non-existent template should return 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/templates/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_get_template_success(self):
        """Getting an existing template should return its data."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            create_resp = await client.post("/api/templates", json={
                "name": "Fetchable Template",
                "description": "Can be fetched",
                "category": "general",
                "tags": ["fetch"],
                "config_state": {"inputs": [], "processors": []},
            })
            template_id = create_resp.json()["id"]

            resp = await client.get(f"/api/templates/{template_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Fetchable Template"

    @pytest.mark.anyio
    async def test_get_template_invalid_id(self):
        """Getting a template with invalid ID format should return 400."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/templates/..bad-id")
        assert resp.status_code == 400


class TestCreateTemplate:
    @pytest.mark.anyio
    async def test_create_template_success(self):
        """Creating a template with valid data should succeed."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/templates", json={
                "name": "New Template",
                "description": "A new template",
                "category": "finance",
                "tags": ["finance", "report"],
                "config_state": {"inputs": [], "processors": []},
                "author": "tester",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Template"
        assert data["category"] == "finance"
        assert data["id"]

    @pytest.mark.anyio
    async def test_create_template_empty_name_rejected(self):
        """Creating a template with empty name should be rejected."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/templates", json={
                "name": "",
                "description": "desc",
                "category": "general",
                "tags": [],
                "config_state": {},
            })
        assert resp.status_code == 422  # Pydantic validation error


class TestDeleteTemplate:
    @pytest.mark.anyio
    async def test_delete_template_success(self):
        """Deleting an existing template should succeed."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            create_resp = await client.post("/api/templates", json={
                "name": "To Delete",
                "description": "Will be deleted",
                "category": "general",
                "tags": [],
                "config_state": {"inputs": [], "processors": []},
            })
            template_id = create_resp.json()["id"]

            resp = await client.delete(f"/api/templates/{template_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.anyio
    async def test_delete_template_not_found(self):
        """Deleting a non-existent template should return 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/templates/nonexistent-id")
        assert resp.status_code == 404


class TestCheckCompatibility:
    @pytest.mark.anyio
    async def test_check_compatibility_no_requirements(self):
        """Template with no requirements should be compatible."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            create_resp = await client.post("/api/templates", json={
                "name": "Simple Template",
                "description": "No special requirements",
                "category": "general",
                "tags": [],
                "config_state": {"inputs": [], "processors": []},
            })
            template_id = create_resp.json()["id"]

            resp = await client.post(f"/api/templates/{template_id}/check-compatibility")
        assert resp.status_code == 200
        data = resp.json()
        assert data["compatible"] is True
        assert data["issues"] == []

    @pytest.mark.anyio
    async def test_check_compatibility_not_found(self):
        """Compatibility check for non-existent template should return 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/templates/nonexistent-id/check-compatibility")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_check_compatibility_with_database_requirement(self, monkeypatch):
        """Template requiring database should report missing if no connections."""
        from configforge.services import connection_store
        monkeypatch.setattr(connection_store, "DATA_DIR", "/tmp/nonexistent_test_cf_data")
        monkeypatch.setattr(connection_store, "STORE_PATH", "/tmp/nonexistent_test_cf_data/db_connections.json")
        connection_store._cache.invalidate("connections")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            create_resp = await client.post("/api/templates", json={
                "name": "DB Template",
                "description": "Needs a database",
                "category": "general",
                "tags": [],
                "config_state": {
                    "inputs": [{"plugin": "database", "name": "db_input"}],
                    "processors": [],
                },
            })
            template_id = create_resp.json()["id"]

            resp = await client.post(f"/api/templates/{template_id}/check-compatibility")
        assert resp.status_code == 200
        data = resp.json()
        assert data["compatible"] is False
        assert any(i["status"] == "missing" for i in data["issues"])
