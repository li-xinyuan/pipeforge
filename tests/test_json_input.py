"""限制③C：JSON 输入插件端到端测试。

验证：上传 json 文件 → 配置输入源 → 执行 pipeline → 数据正确写入 SQLite。
对应方案 3.4 第二阶段步骤 6。
"""
import json

from pipeforge.config.models import JsonInputConfig
from pipeforge.core.registry import PluginRegistry
from pipeforge.plugins.input.json import JsonInputPlugin


class TestJsonInputPlugin:
    def test_config_model(self):
        assert JsonInputPlugin.config_model() == JsonInputConfig

    def test_registered_as_json_input(self):
        cls = PluginRegistry.get("json", "input")
        assert cls.config_model() is JsonInputConfig

    def test_read_rows_simple(self, tmp_path):
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        file_path = tmp_path / "test.json"
        file_path.write_text(json.dumps(data), encoding="utf-8")

        plugin = JsonInputPlugin()
        config = JsonInputConfig(file=str(file_path))
        columns, rows = plugin._read_rows(str(file_path), config)
        assert set(columns) == {"a", "b"}
        rows_list = list(rows)
        assert len(rows_list) == 2

    def test_read_rows_nested_flatten(self, tmp_path):
        data = [{"user": {"name": "alice", "age": 30}}]
        file_path = tmp_path / "nested.json"
        file_path.write_text(json.dumps(data), encoding="utf-8")

        plugin = JsonInputPlugin()
        config = JsonInputConfig(file=str(file_path), flatten_separator=".")
        columns, rows = plugin._read_rows(str(file_path), config)
        assert "user.name" in columns
        assert "user.age" in columns


class TestJsonPipelineEndToEnd:
    """端到端：JSON 输入 → SQL 处理 → 验证结果。"""

    def test_json_input_to_sqlite(self, tmp_path):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        json_path = tmp_path / "input.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        yaml_content = """
scene:
  name: json_test
  version: "1.0"

inputs:
  - name: people
    plugin: json
    table: person
    param_key: people_file
    config:
      type: json
      flatten_separator: "."

processors:
  - name: filter
    plugin: sql
    output_tables:
      - adults
    config:
      sql: |
        CREATE TABLE adults AS
        SELECT name, age FROM person WHERE age > 26
    checkpoints:
      - type: row_count
        table: adults
        min: 1
        max: 1
        on_failure: block
"""
        yaml_path = tmp_path / "pipeline.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        from pipeforge.core.engine import PipelineEngine

        engine = PipelineEngine(str(yaml_path))
        result = engine.execute(params={"people_file": str(json_path)})

        assert "people" in result.inputs
        assert result.inputs["people"].rows_loaded == 2
        assert result.processors[0].tables_created == ["adults"]
        # checkpoint 验证 adults 表恰好 1 行（Alice 30 > 26，Bob 25 不 > 26）
        assert len(result.checks) == 1
        assert result.checks[0].passed is True

    def test_json_input_heterogeneous_keys(self, tmp_path):
        """不同行有不同键，列名取并集，缺失键补空，全量加载。"""
        data = [
            {"a": 1, "b": 2},
            {"a": 3, "c": 4},
        ]
        json_path = tmp_path / "hetero.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")

        yaml_content = """
scene:
  name: hetero_test
  version: "1.0"

inputs:
  - name: data
    plugin: json
    table: raw
    param_key: data_file
    config:
      type: json
      flatten_separator: "."
"""
        yaml_path = tmp_path / "pipeline.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        from pipeforge.core.engine import PipelineEngine

        engine = PipelineEngine(str(yaml_path))
        result = engine.execute(params={"data_file": str(json_path)})

        assert result.inputs["data"].rows_loaded == 2
