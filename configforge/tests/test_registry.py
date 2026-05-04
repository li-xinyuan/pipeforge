import pytest
from pydantic import BaseModel
from generators.base import ConfigGenerator
from core.registry import GeneratorRegistry


class FakeConfig(BaseModel):
    type: str = "fake"
    name: str = ""


@GeneratorRegistry.register("fake", "input")
class FakeGenerator(ConfigGenerator[FakeConfig]):
    @classmethod
    def config_model(cls):
        return FakeConfig

    def infer_config(self, source: dict) -> FakeConfig:
        return FakeConfig(name=source.get("name", ""))

    def build_config(self, state: dict) -> FakeConfig:
        return FakeConfig(name=state.get("name", ""))

    def validate_config(self, config: FakeConfig) -> list[str]:
        return [] if config.name else ["name is required"]


def test_register_and_retrieve():
    cls = GeneratorRegistry.get("fake", "input")
    assert cls == FakeGenerator


def test_unregistered_raises():
    with pytest.raises(KeyError):
        GeneratorRegistry.get("nonexistent", "input")
