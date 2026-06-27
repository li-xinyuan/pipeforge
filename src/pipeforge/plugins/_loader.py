"""T-5E-05: 插件自动加载机制。

扫描 ``pipeforge.plugins.{input,processor,output}`` 三个子包，
自动 import 所有模块以触发 ``@register_plugin`` 装饰器注册。

替代 ``pipeforge/__init__.py`` 中的手动 import 列表，新增插件无需修改任何注册代码。
"""
from __future__ import annotations

import importlib
import logging
import pkgutil

logger = logging.getLogger("pipeforge.plugins._loader")

# 插件子包名称（对应 input/processor/output 三类插件）
_PLUGIN_SUBPACKAGES: tuple[str, ...] = ("input", "processor", "output")


def load_all_plugins() -> None:
    """扫描所有插件子包，自动 import 模块触发注册。

    幂等操作：``@register_plugin`` 是覆盖式注册，重复调用无副作用。
    跳过以 ``_`` 开头的私有模块（如 ``_loader``、``_helpers``）。
    """
    for subpkg in _PLUGIN_SUBPACKAGES:
        full_pkg = f"pipeforge.plugins.{subpkg}"
        try:
            pkg = importlib.import_module(full_pkg)
        except ImportError as exc:
            logger.warning("Failed to import plugin subpackage %s: %s", full_pkg, exc)
            continue

        for _finder, name, _ispkg in pkgutil.iter_modules(pkg.__path__):
            if name.startswith("_"):
                continue  # 跳过私有模块
            module_path = f"{full_pkg}.{name}"
            try:
                importlib.import_module(module_path)
                logger.debug("Auto-loaded plugin module: %s", module_path)
            except ImportError as exc:
                logger.warning("Failed to import plugin %s: %s", module_path, exc)
