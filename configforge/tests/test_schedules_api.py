"""Tests for schedules API endpoints."""

import json
import os

import pytest
from httpx import ASGITransport, AsyncClient

import configforge.api.configs as configs_module
import configforge.scheduler as scheduler
from configforge.server import app


@pytest.fixture(autouse=True)
def _setup_test_env(tmp_path, monkeypatch):
    """Redirect data directories to temp paths and disable real scheduler."""
    data_dir = str(tmp_path / "data")
    configs_dir = str(tmp_path / "configs")

    monkeypatch.setattr(scheduler, "DATA_DIR", data_dir)
    monkeypatch.setattr(scheduler, "SCHEDULES_PATH", os.path.join(data_dir, "schedules.json"))
    monkeypatch.setattr(scheduler, "_scheduler", None)

    monkeypatch.setattr(configs_module, "CONFIGS_DIR", configs_dir)
    monkeypatch.setattr(configs_module, "INDEX_PATH", os.path.join(configs_dir, "index.json"))
    configs_module._cache.invalidate("index")

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(configs_dir, exist_ok=True)


def _seed_config_index(tmp_path, entries=None):
    """Write a config index file with the given entries (or empty)."""
    configs_dir = str(tmp_path / "configs")
    index_path = os.path.join(configs_dir, "index.json")
    data = {"schema_version": 2, "configs": entries or []}
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    configs_module._cache.invalidate("index")


class TestListSchedules:
    @pytest.mark.anyio
    async def test_list_empty(self, tmp_path):
        """Listing schedules when none exist should return empty list."""
        _seed_config_index(tmp_path)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/schedules")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_list_includes_config_name_and_next_run_time(self, tmp_path):
        """Listed schedules should include config_name and next_run_time."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "My Config", "current_version": 1},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Add a schedule first
            add_resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "0 8 * * *",
                "description": "Daily 8am",
            })
            assert add_resp.status_code == 200

            resp = await client.get("/api/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["config_name"] == "My Config"
        assert data[0]["next_run_time"] is None  # No scheduler running

    @pytest.mark.anyio
    async def test_list_unknown_config_name(self, tmp_path):
        """Schedule whose config_id is not in index should show 未知配置."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Exists"},
        ])
        # Manually write a schedule referencing a deleted config
        sched = scheduler.ScheduleConfig(
            id="s1", config_id="gone", cron_expression="0 8 * * *"
        )
        schedules_path = os.path.join(str(tmp_path / "data"), "schedules.json")
        with open(schedules_path, "w", encoding="utf-8") as f:
            json.dump([sched.model_dump()], f)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/schedules")
        data = resp.json()
        assert data[0]["config_name"] == "未知配置"


class TestAddSchedule:
    @pytest.mark.anyio
    async def test_add_success(self, tmp_path):
        """Adding a schedule for an existing config should succeed."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Test Config"},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "0 8 * * *",
                "description": "Daily 8am",
                "retry_count": 3,
                "retry_interval": 60,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["config_id"] == "cfg1"
        assert data["cron_expression"] == "0 8 * * *"
        assert data["description"] == "Daily 8am"
        assert data["retry_count"] == 3
        assert data["retry_interval"] == 60
        assert data["enabled"] is True
        assert data["id"]

    @pytest.mark.anyio
    async def test_add_config_not_found(self, tmp_path):
        """Adding a schedule for a non-existing config_id should return 404."""
        _seed_config_index(tmp_path, [])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/schedules", json={
                "config_id": "nonexistent",
                "cron_expression": "0 8 * * *",
            })
        assert resp.status_code == 404
        assert "配置不存在" in resp.json()["error"]

    @pytest.mark.anyio
    async def test_add_invalid_cron(self, tmp_path):
        """Adding a schedule with invalid cron expression should return 400."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Test Config"},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "invalid",
            })
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_add_default_values(self, tmp_path):
        """Adding a schedule without optional fields should use defaults."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Test Config"},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "0 8 * * *",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == ""
        assert data["retry_count"] == 0
        assert data["retry_interval"] == 300


class TestUpdateSchedule:
    @pytest.mark.anyio
    async def test_update_success(self, tmp_path):
        """Updating a schedule should change the specified fields."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Test Config"},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            add_resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "0 8 * * *",
                "description": "Original",
            })
            schedule_id = add_resp.json()["id"]

            resp = await client.put(f"/api/schedules/{schedule_id}", json={
                "cron_expression": "0 9 * * *",
                "description": "Updated",
                "retry_count": 5,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["cron_expression"] == "0 9 * * *"
        assert data["description"] == "Updated"
        assert data["retry_count"] == 5

    @pytest.mark.anyio
    async def test_update_not_found(self, tmp_path):
        """Updating a non-existent schedule should return 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put("/api/schedules/nonexistent", json={
                "cron_expression": "0 9 * * *",
            })
        assert resp.status_code == 404
        assert "定时任务不存在" in resp.json()["error"]

    @pytest.mark.anyio
    async def test_update_invalid_cron(self, tmp_path):
        """Updating with invalid cron expression should return 400."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Test Config"},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            add_resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "0 8 * * *",
            })
            schedule_id = add_resp.json()["id"]

            resp = await client.put(f"/api/schedules/{schedule_id}", json={
                "cron_expression": "bad-cron",
            })
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_update_partial(self, tmp_path):
        """Updating only some fields should leave others unchanged."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Test Config"},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            add_resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "0 8 * * *",
                "description": "Keep this",
            })
            schedule_id = add_resp.json()["id"]

            resp = await client.put(f"/api/schedules/{schedule_id}", json={
                "retry_count": 10,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "Keep this"
        assert data["cron_expression"] == "0 8 * * *"
        assert data["retry_count"] == 10


class TestDeleteSchedule:
    @pytest.mark.anyio
    async def test_delete_success(self, tmp_path):
        """Deleting an existing schedule should succeed."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Test Config"},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            add_resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "0 8 * * *",
            })
            schedule_id = add_resp.json()["id"]

            resp = await client.delete(f"/api/schedules/{schedule_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.anyio
    async def test_delete_not_found(self, tmp_path):
        """Deleting a non-existent schedule should return 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete("/api/schedules/nonexistent")
        assert resp.status_code == 404
        assert "定时任务不存在" in resp.json()["error"]

    @pytest.mark.anyio
    async def test_delete_then_list_empty(self, tmp_path):
        """After deleting the only schedule, list should be empty."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Test Config"},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            add_resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "0 8 * * *",
            })
            schedule_id = add_resp.json()["id"]

            await client.delete(f"/api/schedules/{schedule_id}")
            list_resp = await client.get("/api/schedules")
        assert list_resp.json() == []


class TestToggleSchedule:
    @pytest.mark.anyio
    async def test_toggle_enabled_to_disabled(self, tmp_path):
        """Toggling an enabled schedule should disable it."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Test Config"},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            add_resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "0 8 * * *",
            })
            schedule_id = add_resp.json()["id"]
            assert add_resp.json()["enabled"] is True

            resp = await client.post(f"/api/schedules/{schedule_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

    @pytest.mark.anyio
    async def test_toggle_disabled_to_enabled(self, tmp_path):
        """Toggling a disabled schedule should enable it."""
        _seed_config_index(tmp_path, [
            {"id": "cfg1", "scene_name": "Test Config"},
        ])
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            add_resp = await client.post("/api/schedules", json={
                "config_id": "cfg1",
                "cron_expression": "0 8 * * *",
            })
            schedule_id = add_resp.json()["id"]

            # Toggle once to disable
            await client.post(f"/api/schedules/{schedule_id}/toggle")
            # Toggle again to enable
            resp = await client.post(f"/api/schedules/{schedule_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    @pytest.mark.anyio
    async def test_toggle_not_found(self, tmp_path):
        """Toggling a non-existent schedule should return 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/schedules/nonexistent/toggle")
        assert resp.status_code == 404
        assert "定时任务不存在" in resp.json()["error"]
