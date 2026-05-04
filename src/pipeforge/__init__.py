"""PipeForge — CLI data pipeline framework."""

__version__ = "0.1.0"

# 导入插件模块，触发 @register_plugin 装饰器注册
import pipeforge.plugins.input.excel      # noqa: F401
import pipeforge.plugins.processor.sql   # noqa: F401
import pipeforge.plugins.output.excel    # noqa: F401
