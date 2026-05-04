from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

C = TypeVar("C", bound=BaseModel)


class Plugin(ABC, Generic[C]):
    """所有插件的抽象基类。name 和 label 由引擎实例化后注入。"""

    @classmethod
    @abstractmethod
    def config_model(cls) -> type[C]:
        """返回该插件的配置 Pydantic 模型。"""
        ...

    @abstractmethod
    def execute(self, context: "Context", config: C) -> None:
        """执行插件逻辑。"""
        ...


class InputPlugin(Plugin[C], ABC):
    """输入插件基类 — table_name 由引擎注入。"""


class ProcessorPlugin(Plugin[C], ABC):
    """处理插件基类 — MVP 与 Plugin 相同，预留扩展。"""


class OutputPlugin(Plugin[C], ABC):
    """输出插件基类 — MVP 与 Plugin 相同，预留扩展。"""
