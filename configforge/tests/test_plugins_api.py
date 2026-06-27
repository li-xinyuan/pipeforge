"""T-5E-05: 插件管理 API 端点测试。

验证 GET /api/plugins 端点：
- 返回所有已注册插件清单
- 支持按类型过滤
- 每项包含 name/type/label/config_schema
"""
import importlib
import pkgutil
import sys

import pytest
from httpx import ASGITransport, AsyncClient

from configforge.server import app


@pytest.fixture(autouse=True)
def _ensure_plugins_registered():
    """确保插件注册表只含 11 个真实插件（6 input + 2 processor + 3 output）。

    全量测试运行时，tests/test_registry.py 注册的 fake 插件（如 list_test）
    会残留在全局注册表中。先 clear 清空所有，再 reload 真实插件模块
    重新触发 @register_plugin 装饰器注册。
    """
    from pipeforge.core.registry import PluginRegistry

    PluginRegistry.clear()
    for subpkg in ("input", "processor", "output"):
        pkg = importlib.import_module(f"pipeforge.plugins.{subpkg}")
        for _finder, name, _ispkg in pkgutil.iter_modules(pkg.__path__):
            if name.startswith("_"):
                continue
            mod_path = f"pipeforge.plugins.{subpkg}.{name}"
            if mod_path in sys.modules:
                importlib.reload(sys.modules[mod_path])
            else:
                importlib.import_module(mod_path)
    yield


class TestListPlugins:
    """T-5E-05: GET /api/plugins 端点测试。"""

    @pytest.mark.anyio
    async def test_list_plugins_returns_all(self):
        """应返回所有 11 个已注册插件。"""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/plugins")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 11

    @pytest.mark.anyio
    async def test_list_plugins_filter_input(self):
        """按 type=input 过滤应返回 6 个输入插件（含 ③C reader 适配器）。"""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/plugins", params={"plugin_type": "input"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 6
        names = {p["name"] for p in data}
        assert names == {"csv", "excel", "database", "json", "xml", "parquet"}
        assert all(p["type"] == "input" for p in data)

    @pytest.mark.anyio
    async def test_list_plugins_filter_processor(self):
        """按 type=processor 过滤应返回 2 个处理插件。"""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/plugins", params={"plugin_type": "processor"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {p["name"] for p in data}
        assert names == {"sql", "python"}

    @pytest.mark.anyio
    async def test_list_plugins_filter_output(self):
        """按 type=output 过滤应返回 3 个输出插件。"""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/plugins", params={"plugin_type": "output"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        names = {p["name"] for p in data}
        assert names == {"csv", "excel", "database"}

    @pytest.mark.anyio
    async def test_list_plugins_item_structure(self):
        """每项应包含 name/type/label/config_schema 字段。"""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/plugins", params={"plugin_type": "input"})
        data = resp.json()
        for item in data:
            assert "name" in item
            assert "type" in item
            assert "label" in item
            assert "config_schema" in item
            assert isinstance(item["config_schema"], dict)

    @pytest.mark.anyio
    async def test_list_plugins_csv_input_has_schema(self):
        """csv input 插件的 config_schema 应包含 file 字段。"""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/plugins", params={"plugin_type": "input"})
        data = resp.json()
        csv_plugin = next(p for p in data if p["name"] == "csv")
        assert "file" in csv_plugin["config_schema"].get("properties", {})

    @pytest.mark.anyio
    async def test_list_plugins_filter_empty_result(self):
        """无效的类型应返回空列表。"""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/plugins", params={"plugin_type": "nonexistent"})
        assert resp.status_code == 200
        assert resp.json() == []
