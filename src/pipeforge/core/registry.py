from typing import Type

from pipeforge.plugins.base import Plugin


class PluginNotFoundError(Exception):
    """请求的插件未在注册中心中找到。"""
    def __init__(self, name: str, plugin_type: str):
        self.name = name
        self.plugin_type = plugin_type
        super().__init__(f"Plugin '{name}' of type '{plugin_type}' not found in registry")


class PluginRegistry:
    """全局插件注册中心。插件通过 @register_plugin 装饰器注册。"""

    _plugins: dict[tuple[str, str], Type[Plugin]] = {}

    @classmethod
    def register(cls, name: str, plugin_type: str, plugin_cls: Type[Plugin]) -> None:
        cls._plugins[(name, plugin_type)] = plugin_cls

    @classmethod
    def get(cls, name: str, plugin_type: str) -> Type[Plugin]:
        key = (name, plugin_type)
        if key not in cls._plugins:
            raise PluginNotFoundError(name, plugin_type)
        return cls._plugins[key]

    @classmethod
    def list_by_type(cls, plugin_type: str) -> list[str]:
        return [name for (name, ptype) in cls._plugins if ptype == plugin_type]

    @classmethod
    def list_all(cls) -> list[dict]:
        """T-5E-05: 返回所有已注册插件的详情列表（含配置 schema）。

        每项格式：``{"name": str, "type": str, "label": str, "config_schema": dict}``。
        供 ``GET /api/plugins`` 端点使用，前端据此动态渲染配置表单。
        """
        result: list[dict] = []
        for (name, plugin_type), plugin_cls in cls._plugins.items():
            try:
                schema = plugin_cls.config_schema()
            except Exception:
                schema = {}
            result.append({
                "name": name,
                "type": plugin_type,
                "label": getattr(plugin_cls, "label", "") or name,
                "config_schema": schema,
            })
        return result

    @classmethod
    def clear(cls) -> None:
        """清空注册中心（仅供测试使用）。"""
        cls._plugins.clear()


def register_plugin(name: str, plugin_type: str):
    """注册插件到全局注册中心的装饰器。"""
    def decorator(cls: Type[Plugin]) -> Type[Plugin]:
        PluginRegistry.register(name, plugin_type, cls)
        return cls
    return decorator
