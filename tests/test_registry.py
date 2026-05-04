import pytest
from pydantic import BaseModel

from pipeforge.plugins.base import InputPlugin, ProcessorPlugin, OutputPlugin
from pipeforge.core.registry import PluginRegistry, register_plugin, PluginNotFoundError


class FakeConfig(BaseModel):
    pass


class TestPluginRegistry:
    def test_register_and_get(self):
        @register_plugin("test_excel", "input")
        class TestExcelInput(InputPlugin):
            @classmethod
            def config_model(cls) -> type[FakeConfig]:
                return FakeConfig

            def execute(self, context, config: FakeConfig) -> None:
                pass

        cls = PluginRegistry.get("test_excel", "input")
        assert cls == TestExcelInput

    def test_get_nonexistent_plugin_raises(self):
        with pytest.raises(PluginNotFoundError) as exc:
            PluginRegistry.get("nonexistent", "input")
        assert "nonexistent" in str(exc.value)

    def test_register_duplicate_overwrites(self):
        @register_plugin("dup_plugin", "output")
        class FirstOutput(OutputPlugin):
            @classmethod
            def config_model(cls) -> type[FakeConfig]:
                return FakeConfig

            def execute(self, context, config: FakeConfig) -> None:
                pass

        @register_plugin("dup_plugin", "output")
        class SecondOutput(OutputPlugin):
            @classmethod
            def config_model(cls) -> type[FakeConfig]:
                return FakeConfig

            def execute(self, context, config: FakeConfig) -> None:
                pass

        cls = PluginRegistry.get("dup_plugin", "output")
        assert cls == SecondOutput

    def test_list_by_type(self):
        PluginRegistry.clear()

        @register_plugin("list_test", "processor")
        class ListTestProc(ProcessorPlugin):
            @classmethod
            def config_model(cls) -> type[FakeConfig]:
                return FakeConfig

            def execute(self, context, config: FakeConfig) -> None:
                pass

        plugins = PluginRegistry.list_by_type("processor")
        assert "list_test" in plugins
