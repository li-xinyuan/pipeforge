from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel

C = TypeVar("C", bound=BaseModel)


class ConfigGenerator(ABC, Generic[C]):
    @classmethod
    @abstractmethod
    def config_model(cls) -> type[C]: ...

    @abstractmethod
    def infer_config(self, source: dict) -> C: ...

    @abstractmethod
    def build_config(self, wizard_state: dict) -> C: ...

    @abstractmethod
    def validate_config(self, config: C) -> list[str]: ...
