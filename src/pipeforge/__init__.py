"""PipeForge — CLI data pipeline framework."""

__version__ = "0.1.0"

# T-5E-05: 自动加载所有插件模块，触发 @register_plugin 装饰器注册。
# 新增插件只需放入 plugins/{input,processor,output}/ 目录，无需修改此文件。
from pipeforge.plugins._loader import load_all_plugins

load_all_plugins()
