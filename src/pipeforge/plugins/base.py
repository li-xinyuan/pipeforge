from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

C = TypeVar("C", bound=BaseModel)


class Plugin(ABC, Generic[C]):
    """所有插件的抽象基类。name 和 label 由引擎实例化后注入。"""

    name: str = ""
    label: str = ""

    @classmethod
    @abstractmethod
    def config_model(cls) -> type[C]:
        """返回该插件的配置 Pydantic 模型。"""
        ...

    @classmethod
    def config_schema(cls) -> dict:
        """T-5E-05: 返回插件配置的 JSON Schema。

        默认实现从 ``config_model()`` 的 Pydantic 模型自动生成。
        子类可覆盖以提供自定义 schema（如增减字段、调整 UI 提示）。
        """
        return cls.config_model().model_json_schema()

    @abstractmethod
    def execute(self, context: Any, config: C) -> None:
        """执行插件逻辑。Context 由 Task 6 定义，运行时注入。"""
        ...


class InputPlugin(Plugin[C], ABC):
    """输入插件基类 — table_name 由引擎注入。"""

    table_name: str = ""


class ProcessorPlugin(Plugin[C], ABC):
    """处理插件基类 — MVP 与 Plugin 相同，预留扩展。"""


class OutputPlugin(Plugin[C], ABC):
    """输出插件基类 — MVP 与 Plugin 相同，预留扩展。"""
