import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import configforge.utils.security as security
from configforge.server import app


@pytest.fixture(autouse=True)
def temp_data_dir(monkeypatch):
    import configforge.services.connection_store as cs
    tmp = tempfile.mkdtemp()
    monkeypatch.setattr(cs, "DATA_DIR", tmp)
    monkeypatch.setattr(cs, "STORE_PATH", os.path.join(tmp, "db_connections.json"))
    # Reset SQLite allowed dirs so it recalculates with current cwd
    monkeypatch.setattr(security, "_SQLITE_ALLOWED_DIRS", None)
    yield
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)


def test_create_connection_sqlite(client):
    resp = client.post("/api/connections", json={
        "name": "Test SQLite", "db_type": "sqlite", "file_path": "tmp/test.db",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test SQLite"
    assert data["db_type"] == "sqlite"
    assert data["passwordSet"] is False


def test_create_connection_mysql(client):
    resp = client.post("/api/connections", json={
        "name": "Test MySQL", "db_type": "mysql",
        "host": "localhost", "port": 3306, "database": "test",
        "username": "root", "password": "secret",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["passwordSet"] is True


def test_list_connections(client):
    client.post("/api/connections", json={"name": "A", "db_type": "sqlite", "file_path": "tmp/a.db"})
    client.post("/api/connections", json={"name": "B", "db_type": "sqlite", "file_path": "tmp/b.db"})
    resp = client.get("/api/connections")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_connection(client):
    resp = client.post("/api/connections", json={"name": "GetMe", "db_type": "sqlite", "file_path": "tmp/g.db"})
    conn_id = resp.json()["id"]
    resp = client.get(f"/api/connections/{conn_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetMe"


def test_update_connection(client):
    resp = client.post("/api/connections", json={"name": "Old", "db_type": "sqlite", "file_path": "tmp/old.db"})
    conn_id = resp.json()["id"]
    resp = client.put(f"/api/connections/{conn_id}", json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


def test_delete_connection(client):
    resp = client.post("/api/connections", json={"name": "Del", "db_type": "sqlite", "file_path": "tmp/del.db"})
    conn_id = resp.json()["id"]
    resp = client.delete(f"/api/connections/{conn_id}")
    assert resp.status_code == 200
    resp = client.get(f"/api/connections/{conn_id}")
    assert resp.status_code == 404


def test_password_not_returned(client):
    resp = client.post("/api/connections", json={
        "name": "Secure", "db_type": "mysql",
        "host": "h", "port": 1, "database": "d",
        "username": "u", "password": "s3cr3t",
    })
    data = resp.json()
    assert "password" not in data
    assert data["passwordSet"] is True


def test_get_nonexistent_connection(client):
    resp = client.get("/api/connections/nonexistent")
    assert resp.status_code == 404


def test_update_nonexistent_connection(client):
    resp = client.put("/api/connections/nonexistent", json={"name": "Nope"})
    assert resp.status_code == 404


def test_delete_nonexistent_connection(client):
    resp = client.delete("/api/connections/nonexistent")
    assert resp.status_code == 404


def test_create_sqlite_missing_file_path(client):
    resp = client.post("/api/connections", json={
        "name": "Bad SQLite", "db_type": "sqlite",
    })
    assert resp.status_code == 400


def test_create_sqlite_path_traversal(client):
    resp = client.post("/api/connections", json={
        "name": "Evil SQLite", "db_type": "sqlite", "file_path": "../etc/passwd",
    })
    assert resp.status_code == 400
