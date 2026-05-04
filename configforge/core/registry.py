from typing import TypeVar
from generators.base import ConfigGenerator

T = TypeVar("T", bound=ConfigGenerator)


class GeneratorRegistry:
    _generators: dict[tuple[str, str], type[ConfigGenerator]] = {}

    @classmethod
    def register(cls, name: str, category: str):
        def decorator(generator_cls):
            cls._generators[(name, category)] = generator_cls
            return generator_cls

        return decorator

    @classmethod
    def get(cls, name: str, category: str) -> type[ConfigGenerator]:
        key = (name, category)
        if key not in cls._generators:
            raise KeyError(
                f"Generator '{name}' (category: {category}) not registered"
            )
        return cls._generators[key]

    @classmethod
    def list_all(cls) -> list[tuple[str, str]]:
        return list(cls._generators.keys())

    @classmethod
    def clear(cls):
        cls._generators.clear()
