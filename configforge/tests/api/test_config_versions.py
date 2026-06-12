"""Tests for config version management API."""
import pytest
from fastapi.testclient import TestClient
import os
import glob

from configforge.server import app
from configforge.api.configs import CONFIGS_DIR

client = TestClient(app)


def _delete_test_configs(prefix="test_"):
    """Clean up test config files."""
    for f in glob.glob(os.path.join(CONFIGS_DIR, f"{prefix}*")):
        if os.path.isfile(f):
            os.remove(f)
    # Also clean up version directories
    for d in glob.glob(os.path.join(CONFIGS_DIR, f"{prefix}*")):
        if os.path.isdir(d):
            import shutil
            shutil.rmtree(d)


class TestConfigVersions:
    def test_first_save_has_current_version_1(self):
        resp = client.post("/api/configs", json={
            "config_id": None,
            "state": {
                "current_step": 1,
                "scene": {"name": "Test V1", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        assert resp.status_code == 200
        config_id = resp.json()["id"]

        index_resp = client.get("/api/configs", params={"page_size": 9999})
        metas = [m for m in index_resp.json()["items"] if m["id"] == config_id]
        assert len(metas) == 1
        assert metas[0]["current_version"] == 1
        assert metas[0]["created_at"] != ""

    def test_second_save_creates_version_history(self):
        resp = client.post("/api/configs", json={
            "config_id": None,
            "state": {
                "current_step": 1,
                "scene": {"name": "Original", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        config_id = resp.json()["id"]

        # Save again (update)
        resp2 = client.post("/api/configs", json={
            "config_id": config_id,
            "state": {
                "current_step": 2,
                "scene": {"name": "Updated", "description": "changed", "version": "2.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        assert resp2.status_code == 200

        # Check current version
        index_resp = client.get("/api/configs", params={"page_size": 9999})
        metas = [m for m in index_resp.json()["items"] if m["id"] == config_id]
        assert metas[0]["current_version"] == 2

    def test_list_versions(self):
        resp = client.post("/api/configs", json={
            "config_id": None,
            "state": {
                "current_step": 1,
                "scene": {"name": "List Test", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        config_id = resp.json()["id"]

        # Save 3 more times
        for i in range(2, 5):
            client.post("/api/configs", json={
                "config_id": config_id,
                "state": {
                    "current_step": 1,
                    "scene": {"name": f"V{i}", "description": "", "version": f"{i}.0"},
                    "inputs": [],
                    "processors": [],
                    "output": None,
                }
            })

        versions = client.get(f"/api/configs/{config_id}/versions")
        assert versions.status_code == 200
        vlist = versions.json()
        # v1, v2, v3 archived, v4 is current
        assert len(vlist) >= 3
        version_numbers = [v["version"] for v in vlist]
        assert 1 in version_numbers
        assert 2 in version_numbers

    def test_get_specific_version(self):
        resp = client.post("/api/configs", json={
            "config_id": None,
            "state": {
                "current_step": 1,
                "scene": {"name": "Detail", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        config_id = resp.json()["id"]

        # Update (this archives v1)
        client.post("/api/configs", json={
            "config_id": config_id,
            "state": {
                "current_step": 2,
                "scene": {"name": "Detail V2", "description": "", "version": "2.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })

        v1 = client.get(f"/api/configs/{config_id}/versions/1")
        assert v1.status_code == 200
        assert v1.json()["scene"]["name"] == "Detail"

    def test_rollback_creates_new_version(self):
        resp = client.post("/api/configs", json={
            "config_id": None,
            "state": {
                "current_step": 1,
                "scene": {"name": "Original", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        config_id = resp.json()["id"]

        # Update
        client.post("/api/configs", json={
            "config_id": config_id,
            "state": {
                "current_step": 1,
                "scene": {"name": "Modified", "description": "changed", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })

        # Rollback to v1
        rb = client.post(f"/api/configs/{config_id}/versions/1/rollback")
        assert rb.status_code == 200
        data = rb.json()
        assert data["new_version"] >= 3  # v1 and v2 existed, rollback creates v3
        assert data["rolled_back_from"] == 2
        assert data["rolled_back_to"] == 1

        # Verify content is v1's
        cur = client.get(f"/api/configs/{config_id}")
        assert cur.json()["scene"]["name"] == "Original"

    def test_diff_between_versions(self):
        resp = client.post("/api/configs", json={
            "config_id": None,
            "state": {
                "current_step": 1,
                "scene": {"name": "Diff V1", "description": "", "version": "1.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })
        config_id = resp.json()["id"]

        client.post("/api/configs", json={
            "config_id": config_id,
            "state": {
                "current_step": 1,
                "scene": {"name": "Diff V2", "description": "new desc", "version": "2.0"},
                "inputs": [],
                "processors": [],
                "output": None,
            }
        })

        diff_resp = client.get(f"/api/configs/{config_id}/diff?v1=1&v2=2")
        assert diff_resp.status_code == 200
        data = diff_resp.json()
        assert len(data["changes"]) > 0
        # Should have at least a change for scene.name
        name_changes = [c for c in data["changes"] if "scene" in c["path"] and "name" in c["path"]]
        assert len(name_changes) > 0

    def test_invalid_config_id_returns_400(self):
        # ID containing space fails _VALID_ID_RE
        resp = client.get("/api/configs/invalid%20id/versions")
        assert resp.status_code == 400

    def test_nonexistent_config_returns_200_empty_list(self):
        # Valid ID format but non-existent config returns empty version list
        resp = client.get("/api/configs/nonexistent/versions")
        assert resp.status_code == 200
        assert resp.json() == []
