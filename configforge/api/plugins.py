"""API endpoints for plugin management (T-5E-05).

暴露已注册插件的清单和配置 schema，供前端动态渲染配置表单。
"""
from fastapi import APIRouter, Depends, Query

from configforge.middleware.auth import require_role
from configforge.models.user import User

router = APIRouter(prefix="/api/plugins", tags=["插件管理"])


@router.get(
    "",
    summary="获取插件清单",
    description="返回所有已注册插件（input/processor/output）的清单和配置 schema，"
    "供前端动态渲染配置表单。支持按类型过滤。",
)
async def list_plugins(
    plugin_type: str | None = Query(
        None, description="按类型过滤：input / processor / output"
    ),
    _user: User = Depends(require_role("viewer", "editor", "admin")),
):
    """List all registered plugins with their config schemas.

    T-5E-05: 前端据此动态渲染插件配置表单，无需为每个插件硬编码表单字段。
    """
    # 确保插件已加载（幂等；import pipeforge 不会重新触发 __init__.py，
    # 若注册表被 clear() 需显式重新加载）
    from pipeforge.core.registry import PluginRegistry
    from pipeforge.plugins._loader import load_all_plugins

    if not PluginRegistry._plugins:
        load_all_plugins()

    plugins = PluginRegistry.list_all()
    if plugin_type is not None:
        plugins = [p for p in plugins if p["type"] == plugin_type]
    return plugins
