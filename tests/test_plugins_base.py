import pytest
from pydantic import BaseModel

from pipeforge.plugins.base import Plugin, InputPlugin, ProcessorPlugin, OutputPlugin


class FakeConfig(BaseModel):
    value: str


class FakeInputPlugin(InputPlugin):
    @classmethod
    def config_model(cls) -> type[FakeConfig]:
        return FakeConfig

    def execute(self, context, config: FakeConfig) -> None:
        pass


class TestPluginBase:
    def test_plugin_has_name_attribute(self):
        plugin = FakeInputPlugin()
        plugin.name = "test_plugin"
        assert plugin.name == "test_plugin"

    def test_plugin_has_label_attribute(self):
        plugin = FakeInputPlugin()
        plugin.label = "Test Label"
        assert plugin.label == "Test Label"

    def test_input_plugin_has_table_name(self):
        plugin = FakeInputPlugin()
        plugin.table_name = "my_table"
        assert plugin.table_name == "my_table"

    def test_config_model_returns_correct_type(self):
        assert FakeInputPlugin.config_model() == FakeConfig

    def test_cannot_instantiate_abstract_plugin(self):
        with pytest.raises(TypeError):
            Plugin()  # type: ignore

    def test_cannot_instantiate_without_execute(self):
        class BadPlugin(InputPlugin):
            @classmethod
            def config_model(cls) -> type[FakeConfig]:
                return FakeConfig

        with pytest.raises(TypeError):
            BadPlugin()  # type: ignore
