"""T-5E-05: 插件自动加载机制 + config_schema + list_all 单测。

验证：
1. load_all_plugins() 自动发现并注册所有插件模块
2. Plugin.config_schema() 返回有效的 JSON Schema
3. PluginRegistry.list_all() 返回完整的插件详情
"""
from __future__ import annotations

import pytest

from pipeforge.core.registry import PluginRegistry
from pipeforge.plugins._loader import load_all_plugins


@pytest.fixture(autouse=True)
def _ensure_plugins_loaded():
    """每个测试前确保插件已加载（防止 test_registry.clear() 污染）。"""
    load_all_plugins()
    yield


class TestAutoLoad:
    """T-5E-05: 自动加载机制测试。"""

    def test_load_all_registers_input_plugins(self):
        """load_all_plugins 应注册 3 个 input 插件。"""
        inputs = PluginRegistry.list_by_type("input")
        assert "csv" in inputs
        assert "excel" in inputs
        assert "database" in inputs

    def test_load_all_registers_processor_plugins(self):
        """load_all_plugins 应注册 2 个 processor 插件。"""
        processors = PluginRegistry.list_by_type("processor")
        assert "sql" in processors
        assert "python" in processors

    def test_load_all_registers_output_plugins(self):
        """load_all_plugins 应注册 3 个 output 插件。"""
        outputs = PluginRegistry.list_by_type("output")
        assert "csv" in outputs
        assert "excel" in outputs
        assert "database" in outputs

    def test_load_all_total_plugin_count(self):
        """总共应注册 8 个插件。"""
        total = (
            len(PluginRegistry.list_by_type("input"))
            + len(PluginRegistry.list_by_type("processor"))
            + len(PluginRegistry.list_by_type("output"))
        )
        assert total == 8

    def test_load_all_is_idempotent(self):
        """重复调用 load_all_plugins 不应产生副作用（覆盖式注册）。"""
        load_all_plugins()
        load_all_plugins()
        total = (
            len(PluginRegistry.list_by_type("input"))
            + len(PluginRegistry.list_by_type("processor"))
            + len(PluginRegistry.list_by_type("output"))
        )
        assert total == 8


class TestConfigSchema:
    """T-5E-05: config_schema() 测试。"""

    def test_csv_input_config_schema_has_file_field(self):
        """csv input 插件的 schema 应包含 file 字段。"""
        cls = PluginRegistry.get("csv", "input")
        schema = cls.config_schema()
        assert "properties" in schema
        assert "file" in schema["properties"]

    def test_sql_processor_config_schema_has_sql_field(self):
        """sql processor 插件的 schema 应包含 sql 字段。"""
        cls = PluginRegistry.get("sql", "processor")
        schema = cls.config_schema()
        assert "properties" in schema
        assert "sql" in schema["properties"]

    def test_config_schema_returns_dict(self):
        """所有插件的 config_schema 应返回 dict 类型。"""
        for ptype in ("input", "processor", "output"):
            for name in PluginRegistry.list_by_type(ptype):
                cls = PluginRegistry.get(name, ptype)
                schema = cls.config_schema()
                assert isinstance(schema, dict), f"{name}/{ptype} schema not dict"
                assert "properties" in schema, f"{name}/{ptype} missing properties"

    def test_config_schema_has_type_field(self):
        """所有插件的 schema 应包含 type 字段（discriminator）。"""
        for ptype in ("input", "processor", "output"):
            for name in PluginRegistry.list_by_type(ptype):
                cls = PluginRegistry.get(name, ptype)
                schema = cls.config_schema()
                assert "type" in schema.get("properties", {}), (
                    f"{name}/{ptype} schema missing 'type' field"
                )


class TestListAll:
    """T-5E-05: PluginRegistry.list_all() 测试。"""

    def test_list_all_returns_list(self):
        """list_all 应返回 list 类型。"""
        result = PluginRegistry.list_all()
        assert isinstance(result, list)

    def test_list_all_returns_8_plugins(self):
        """list_all 应返回 8 个插件。"""
        assert len(PluginRegistry.list_all()) == 8

    def test_list_all_item_has_required_fields(self):
        """每项应包含 name/type/label/config_schema 四个字段。"""
        for item in PluginRegistry.list_all():
            assert "name" in item
            assert "type" in item
            assert "label" in item
            assert "config_schema" in item

    def test_list_all_item_types_valid(self):
        """每项的 type 应为 input/processor/output 之一。"""
        valid_types = {"input", "processor", "output"}
        for item in PluginRegistry.list_all():
            assert item["type"] in valid_types

    def test_list_all_label_never_empty(self):
        """label 为空时应回退为 name。"""
        for item in PluginRegistry.list_all():
            assert item["label"], f"{item['name']}/{item['type']} has empty label"

    def test_list_all_config_schema_not_empty(self):
        """每项的 config_schema 不应为空。"""
        for item in PluginRegistry.list_all():
            assert item["config_schema"], f"{item['name']}/{item['type']} empty schema"
            assert "properties" in item["config_schema"]
