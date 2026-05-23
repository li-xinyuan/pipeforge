import os
import tempfile

import pytest
from httpx import AsyncClient, ASGITransport
from configforge.server import app


@pytest.fixture(autouse=True)
def _isolate_ai_settings():
    """每个测试使用独立临时文件，防止测试间状态泄漏。"""
    import configforge.services.ai.settings as mod
    orig = mod.SETTINGS_FILE
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(tmp)  # 删除空文件，让 load_settings 返回默认值
    mod.SETTINGS_FILE = tmp
    yield
    mod.SETTINGS_FILE = orig
    if os.path.exists(tmp):
        os.unlink(tmp)


@pytest.mark.anyio
async def test_ai_suggest_returns_noop():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/ai/suggest", json={"category": "sql", "context": {"inputs": []}})
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data


@pytest.mark.anyio
async def test_ai_suggest_disabled():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/ai/suggest", json={"category": "scene", "context": {}})
    assert resp.status_code == 200
    assert "未配置" in resp.json()["content"]


@pytest.mark.anyio
async def test_ai_settings_get():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/ai/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data
    assert "enabled" in data


@pytest.mark.anyio
async def test_ai_settings_put():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put("/api/ai/settings", json={
            "provider": "openai", "api_key": "sk-keep-existing", "enabled": False,
            "temperature": 0.7, "max_tokens": 4096, "model": "", "base_url": "",
        })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.anyio
async def test_ai_settings_mask():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/api/ai/settings", json={
            "provider": "openai", "api_key": "sk-abc123def456", "enabled": False,
            "temperature": 0.7, "max_tokens": 4096, "model": "", "base_url": "",
        })
        resp = await client.get("/api/ai/settings")
    assert "***" in resp.json()["api_key"]


@pytest.mark.anyio
async def test_ai_settings_clear_key():
    """PUT api_key=None 保留旧值，PUT api_key="" 清空。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 先设置一个有 Key
        await client.put("/api/ai/settings", json={
            "provider": "openai", "api_key": "sk-my-secret", "enabled": False,
            "temperature": 0.7, "max_tokens": 4096, "model": "", "base_url": "",
        })
        # api_key=null → 保留旧值
        await client.put("/api/ai/settings", json={
            "provider": "openai", "api_key": None, "enabled": False,
            "temperature": 0.7, "max_tokens": 4096, "model": "", "base_url": "",
        })
        resp = await client.get("/api/ai/settings")
        assert "***" in resp.json()["api_key"]  # Key 仍存在（脱敏显示）
        # api_key="" → 清空
        await client.put("/api/ai/settings", json={
            "provider": "openai", "api_key": "", "enabled": False,
            "temperature": 0.7, "max_tokens": 4096, "model": "", "base_url": "",
        })
        resp = await client.get("/api/ai/settings")
        assert resp.json()["api_key"] == ""  # Key 已清空


@pytest.mark.anyio
async def test_orchestrate_endpoint_no_ai_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/ai/orchestrate", json={
            "context": {"inputs": [], "naturalLanguage": "test"},
        })
    assert resp.status_code in (400, 200)


@pytest.mark.anyio
async def test_ai_test_connection_no_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.put("/api/ai/settings", json={
            "provider": "openai", "api_key": "", "enabled": False,
            "temperature": 0.7, "max_tokens": 4096, "model": "", "base_url": "",
        })
        resp = await client.post("/api/ai/test")
    assert resp.status_code == 400
