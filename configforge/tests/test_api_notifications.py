"""Tests for notification API endpoints."""
import json
import os
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock

from configforge.server import app


@pytest.fixture(autouse=True)
def _tmp_data(tmp_path, monkeypatch):
    """Use temp directory for notification data files."""
    monkeypatch.setattr(
        "configforge.api.notifications._NOTIFICATIONS_PATH",
        tmp_path / "notifications.json",
    )
    monkeypatch.setattr(
        "configforge.api.notifications._HISTORY_PATH",
        tmp_path / "notification_history.json",
    )


@pytest.fixture
def sample_config():
    """Create a sample notification config via API."""
    return {
        "name": "钉钉推送",
        "type": "webhook",
        "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=test",
        "webhook_provider": "dingtalk",
        "trigger_on_success": True,
        "trigger_on_failure": True,
    }


@pytest.mark.asyncio
async def test_list_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/notifications/configs")
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_create_notification_config(sample_config):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/notifications/configs", json=sample_config)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "钉钉推送"
        assert data["type"] == "webhook"
        assert data["webhook_provider"] == "dingtalk"
        assert "id" in data


@pytest.mark.asyncio
async def test_create_webhook_without_url_fails():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/notifications/configs", json={
            "name": "空推送",
            "type": "webhook",
            "webhook_url": "",
        })
        assert resp.status_code == 400
        assert "URL" in resp.json()["error"]


@pytest.mark.asyncio
async def test_get_notification_config(sample_config):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create first
        create_resp = await client.post("/api/notifications/configs", json=sample_config)
        config_id = create_resp.json()["id"]

        # Get
        resp = await client.get(f"/api/notifications/configs/{config_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == config_id


@pytest.mark.asyncio
async def test_get_nonexistent_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/notifications/configs/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_notification_config(sample_config):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/api/notifications/configs", json=sample_config)
        config_id = create_resp.json()["id"]

        resp = await client.put(f"/api/notifications/configs/{config_id}", json={
            "name": "企微推送",
            "webhook_provider": "wecom",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "企微推送"
        assert resp.json()["webhook_provider"] == "wecom"


@pytest.mark.asyncio
async def test_update_nonexistent_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put("/api/notifications/configs/nonexistent", json={"name": "x"})
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_notification_config(sample_config):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/api/notifications/configs", json=sample_config)
        config_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/notifications/configs/{config_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify deleted
        list_resp = await client.get("/api/notifications/configs")
        assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/notifications/configs/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_test_notification(sample_config):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/api/notifications/configs", json=sample_config)
        config_id = create_resp.json()["id"]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Delivered"
        mock_result.provider = "dingtalk"

        with patch("configforge.api.notifications._send_notification", new_callable=AsyncMock, return_value=mock_result):
            resp = await client.post(f"/api/notifications/test/{config_id}")
            assert resp.status_code == 200
            assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_test_disabled_notification(sample_config):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sample_config["enabled"] = False
        create_resp = await client.post("/api/notifications/configs", json=sample_config)
        config_id = create_resp.json()["id"]

        resp = await client.post(f"/api/notifications/test/{config_id}")
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_notification_history_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/notifications/history")
        assert resp.status_code == 200
        assert resp.json() == []
