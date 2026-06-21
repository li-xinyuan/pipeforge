"""Tests for authentication API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from configforge.server import app


@pytest.fixture(autouse=True)
def _setup_jwt(monkeypatch, tmp_path):
    """Enable JWT for auth tests and use a temp data dir."""
    monkeypatch.setenv("CONFIGFORGE_JWT_SECRET", "test-secret-key-for-testing")
    monkeypatch.setenv("CONFIGFORGE_DATA_DIR", str(tmp_path / "data"))
    # Clear user store cache by resetting module state
    from configforge.services import user_store
    monkeypatch.setattr(user_store, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(user_store, "STORE_PATH", str(tmp_path / "data" / "users.json"))


@pytest.fixture()
def _create_admin(tmp_path):
    """Create a default admin user for tests."""
    from configforge.services.user_store import create_user
    create_user("admin", "admin123", "admin")


@pytest.mark.anyio
async def test_login_disabled_when_jwt_not_set(monkeypatch):
    """Login should return 400 when JWT is not enabled."""
    monkeypatch.delenv("CONFIGFORGE_JWT_SECRET", raising=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "admin123"
        })
    assert resp.status_code == 400
    assert resp.json()["code"] == "AUTH_DISABLED"


@pytest.mark.anyio
async def test_login_success(_create_admin):
    """Login with correct credentials should return a token."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "admin123"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"


@pytest.mark.anyio
async def test_login_failure_wrong_password(_create_admin):
    """Login with wrong password should return 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong-password"
        })
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_FAILED"


@pytest.mark.anyio
async def test_login_failure_unknown_user():
    """Login with non-existent user should return 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/auth/login", json={
            "username": "nonexistent", "password": "whatever"
        })
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_FAILED"


@pytest.mark.anyio
async def test_register_requires_admin_token(_create_admin):
    """Register without admin token should return 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/auth/register", json={
            "username": "newuser", "password": "pass123", "role": "editor"
        })
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"


@pytest.mark.anyio
async def test_register_success_with_admin_token(_create_admin):
    """Register a new user with admin token should succeed."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Login as admin first
        login_resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "admin123"
        })
        token = login_resp.json()["access_token"]

        # Register new user
        resp = await client.post("/api/auth/register", json={
            "username": "neweditor", "password": "pass123", "role": "editor"
        }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "neweditor"
    assert data["role"] == "editor"


@pytest.mark.anyio
async def test_register_forbidden_for_non_admin(_create_admin):
    """Non-admin users should not be able to register new users."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create an editor user first
        login_resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "admin123"
        })
        admin_token = login_resp.json()["access_token"]

        await client.post("/api/auth/register", json={
            "username": "editor1", "password": "pass123", "role": "editor"
        }, headers={"Authorization": f"Bearer {admin_token}"})

        # Login as editor
        editor_login = await client.post("/api/auth/login", json={
            "username": "editor1", "password": "pass123"
        })
        editor_token = editor_login.json()["access_token"]

        # Try to register another user as editor
        resp = await client.post("/api/auth/register", json={
            "username": "another", "password": "pass123", "role": "editor"
        }, headers={"Authorization": f"Bearer {editor_token}"})
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


@pytest.mark.anyio
async def test_register_duplicate_username(_create_admin):
    """Registering a duplicate username should return 409."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        login_resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "admin123"
        })
        token = login_resp.json()["access_token"]

        # Register first time
        await client.post("/api/auth/register", json={
            "username": "dupuser", "password": "pass123", "role": "editor"
        }, headers={"Authorization": f"Bearer {token}"})

        # Register same username again
        resp = await client.post("/api/auth/register", json={
            "username": "dupuser", "password": "pass456", "role": "viewer"
        }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "USERNAME_EXISTS"


@pytest.mark.anyio
async def test_register_invalid_role(_create_admin):
    """Registering with an invalid role should return 400."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        login_resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "admin123"
        })
        token = login_resp.json()["access_token"]

        resp = await client.post("/api/auth/register", json={
            "username": "badrole", "password": "pass123", "role": "superadmin"
        }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_ROLE"


@pytest.mark.anyio
async def test_get_current_user(_create_admin):
    """GET /me should return current user info with valid token."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        login_resp = await client.post("/api/auth/login", json={
            "username": "admin", "password": "admin123"
        })
        token = login_resp.json()["access_token"]

        resp = await client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


@pytest.mark.anyio
async def test_get_current_user_no_token():
    """GET /me without token should return 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_FAILED"


@pytest.mark.anyio
async def test_get_current_user_invalid_token():
    """GET /me with invalid token should return 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid-token-here"
        })
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_me_disabled_when_jwt_not_set(monkeypatch):
    """GET /me should return 400 when JWT is not enabled."""
    monkeypatch.delenv("CONFIGFORGE_JWT_SECRET", raising=False)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/auth/me")
    assert resp.status_code == 400
    assert resp.json()["code"] == "AUTH_DISABLED"
