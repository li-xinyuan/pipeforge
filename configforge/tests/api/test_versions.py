"""Tests for config version management endpoints (list, get, rollback, diff)."""
import json
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from configforge.server import app
import configforge.api.configs as configs_mod


@pytest.fixture(autouse=True)
def temp_data_dir(monkeypatch, tmp_path):
    """Use a temporary directory for config data."""
    configs_dir = str(tmp_path / "configs")
    monkeypatch.setattr(configs_mod, "CONFIGS_DIR", configs_dir)
    os.makedirs(configs_dir, exist_ok=True)
    monkeypatch.setattr(configs_mod, "INDEX_PATH", os.path.join(configs_dir, "index.json"))
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _base_state(name="Test"):
    return {
        "scene": {"name": name, "description": "", "version": "1.0"},
        "inputs": [],
        "processors": [],
        "output": None,
        "current_step": 4,
        "uploaded_files": {},
    }


def _save_config(client, state=None, config_id=None):
    """Helper: save a config and return its ID."""
    if state is None:
        state = _base_state()
    body = {"state": state}
    if config_id:
        body["config_id"] = config_id
    resp = client.post("/api/configs", json=body)
    assert resp.status_code == 200
    return resp.json()["id"]


class TestListVersions:
    def test_initial_save_creates_v1(self, client):
        config_id = _save_config(client)
        resp = client.get(f"/api/configs/{config_id}/versions")
        assert resp.status_code == 200
        versions = resp.json()
        assert len(versions) >= 1
        assert versions[0]["version"] == 1

    def test_multiple_saves_create_versions(self, client):
        config_id = _save_config(client)
        # Save again with different data (same config_id)
        _save_config(client, _base_state("Test v2"), config_id)

        resp = client.get(f"/api/configs/{config_id}/versions")
        assert resp.status_code == 200
        versions = resp.json()
        assert len(versions) >= 2


class TestGetVersion:
    def test_get_existing_version(self, client):
        config_id = _save_config(client)
        resp = client.get(f"/api/configs/{config_id}/versions/1")
        assert resp.status_code == 200
        state = resp.json()
        assert "scene" in state

    def test_get_nonexistent_version(self, client):
        config_id = _save_config(client)
        resp = client.get(f"/api/configs/{config_id}/versions/999")
        assert resp.status_code == 404


class TestRollbackVersion:
    def test_rollback_to_v1(self, client):
        config_id = _save_config(client)
        # Save v2
        _save_config(client, _base_state("Test v2"), config_id)

        # Rollback to v1
        resp = client.post(f"/api/configs/{config_id}/versions/1/rollback")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rolled_back_to"] == 1
        assert data["new_version"] >= 2

    def test_rollback_nonexistent_version(self, client):
        config_id = _save_config(client)
        resp = client.post(f"/api/configs/{config_id}/versions/999/rollback")
        assert resp.status_code == 404


class TestDiffVersions:
    def test_diff_same_version(self, client):
        config_id = _save_config(client)
        resp = client.get(f"/api/configs/{config_id}/diff?v1=1&v2=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["v1"] == 1
        assert data["v2"] == 1

    def test_diff_different_versions(self, client):
        config_id = _save_config(client)
        _save_config(client, _base_state("Test v2"), config_id)

        resp = client.get(f"/api/configs/{config_id}/diff?v1=1&v2=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["v1"] == 1
        assert data["v2"] == 2

    def test_diff_nonexistent_version(self, client):
        config_id = _save_config(client)
        resp = client.get(f"/api/configs/{config_id}/diff?v1=1&v2=999")
        assert resp.status_code == 404
