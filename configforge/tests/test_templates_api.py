"""Tests for templates API endpoints."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

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


class TestUpdateTemplate:
    @pytest.mark.anyio
    async def test_update_name_and_description(self):
        """Updating name and description of an existing template should succeed."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            create_resp = await client.post("/api/templates", json={
                "name": "Original Name",
                "description": "Original desc",
                "category": "general",
                "tags": [],
                "config_state": {"inputs": [], "processors": []},
            })
            template_id = create_resp.json()["id"]

            resp = await client.put(f"/api/templates/{template_id}", json={
                "name": "Updated Name",
                "description": "Updated desc",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated desc"

    @pytest.mark.anyio
    async def test_update_config_state(self):
        """Updating config_state of an existing template should succeed."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            create_resp = await client.post("/api/templates", json={
                "name": "Config Template",
                "description": "desc",
                "category": "general",
                "tags": [],
                "config_state": {"inputs": [], "processors": []},
            })
            template_id = create_resp.json()["id"]

            new_config = {"inputs": [{"plugin": "csv"}], "processors": [{"type": "filter"}]}
            resp = await client.put(f"/api/templates/{template_id}", json={
                "config_state": new_config,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["config_state"] == new_config

    @pytest.mark.anyio
    async def test_update_no_fields_returns_400(self):
        """Updating a template with no fields provided should return 400."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            create_resp = await client.post("/api/templates", json={
                "name": "No Update Template",
                "description": "desc",
                "category": "general",
                "tags": [],
                "config_state": {"inputs": [], "processors": []},
            })
            template_id = create_resp.json()["id"]

            resp = await client.put(f"/api/templates/{template_id}", json={})
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_update_nonexistent_returns_404(self):
        """Updating a non-existent template should return 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put("/api/templates/nonexistent-id", json={
                "name": "New Name",
            })
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_update_invalid_id_format_returns_400(self):
        """Updating a template with invalid ID format should return 400."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put("/api/templates/..bad-id", json={
                "name": "New Name",
            })
        assert resp.status_code == 400


class TestInstantiateTemplate:
    @pytest.mark.anyio
    async def test_instantiate_success(self):
        """Instantiating an existing template should return config_state and template_id."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            create_resp = await client.post("/api/templates", json={
                "name": "Instantiable Template",
                "description": "Can be instantiated",
                "category": "general",
                "tags": [],
                "config_state": {"inputs": [{"plugin": "csv"}], "processors": []},
            })
            template_id = create_resp.json()["id"]

            resp = await client.post(f"/api/templates/{template_id}/instantiate")
        assert resp.status_code == 200
        data = resp.json()
        assert "config_state" in data
        assert data["template_id"] == template_id
        assert data["config_state"]["inputs"] == [{"plugin": "csv"}]

    @pytest.mark.anyio
    async def test_instantiate_increments_usage_count(self):
        """Instantiating a template should increment its usage_count."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            create_resp = await client.post("/api/templates", json={
                "name": "Usage Count Template",
                "description": "Track usage",
                "category": "general",
                "tags": [],
                "config_state": {"inputs": [], "processors": []},
            })
            template_id = create_resp.json()["id"]

            # Get initial usage count
            get_resp = await client.get(f"/api/templates/{template_id}")
            initial_count = get_resp.json().get("usage_count", 0)

            # Instantiate
            await client.post(f"/api/templates/{template_id}/instantiate")

            # Check usage count after
            get_resp2 = await client.get(f"/api/templates/{template_id}")
            new_count = get_resp2.json().get("usage_count", 0)
        assert new_count == initial_count + 1

    @pytest.mark.anyio
    async def test_instantiate_nonexistent_returns_404(self):
        """Instantiating a non-existent template should return 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/templates/nonexistent-id/instantiate")
        assert resp.status_code == 404


class TestExportTemplate:
    @pytest.mark.anyio
    async def test_export_success(self):
        """Exporting an existing template should return JSON with Content-Disposition header."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            create_resp = await client.post("/api/templates", json={
                "name": "Exportable Template",
                "description": "Can be exported",
                "category": "general",
                "tags": ["export"],
                "config_state": {"inputs": [], "processors": []},
            })
            template_id = create_resp.json()["id"]

            resp = await client.get(f"/api/templates/{template_id}/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Exportable Template"
        assert "Content-Disposition" in resp.headers
        assert f"template_{template_id}.json" in resp.headers["Content-Disposition"]

    @pytest.mark.anyio
    async def test_export_nonexistent_returns_404(self):
        """Exporting a non-existent template should return 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/templates/nonexistent-id/export")
        assert resp.status_code == 404


class TestImportTemplate:
    @pytest.mark.anyio
    async def test_import_success(self):
        """Importing a valid JSON template file should succeed."""
        import io
        template_json = json.dumps({
            "name": "Imported Template",
            "description": "Imported from file",
            "category": "imported",
            "tags": ["imported"],
            "config_state": {"inputs": [], "processors": []},
            "author": "importer",
        })
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/templates/import",
                files={"file": ("template.json", io.BytesIO(template_json.encode()), "application/json")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    @pytest.mark.anyio
    async def test_import_invalid_json_returns_400(self):
        """Importing a file with invalid JSON should return 400."""
        import io
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/templates/import",
                files={"file": ("bad.json", io.BytesIO(b"not valid json{"), "application/json")},
            )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_import_missing_required_fields_returns_400(self):
        """Importing a JSON file missing required fields should return 400."""
        import io
        template_json = json.dumps({
            "name": "Incomplete Template",
            # missing category and config_state
        })
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/templates/import",
                files={"file": ("incomplete.json", io.BytesIO(template_json.encode()), "application/json")},
            )
        assert resp.status_code == 400
