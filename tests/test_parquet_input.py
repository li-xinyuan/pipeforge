"""限制③C：Parquet 输入插件端到端测试。

验证：上传 parquet 文件 → 配置输入源 → 执行 pipeline → 数据正确写入 SQLite。
对应方案 3.4 第二阶段步骤 6。
"""


from pipeforge.config.models import ParquetInputConfig
from pipeforge.core.registry import PluginRegistry
from pipeforge.plugins.input.parquet import ParquetInputPlugin


def _write_parquet(path, data: dict):
    """生成测试用 Parquet 文件。"""
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.table(data)
    pq.write_table(table, path)


class TestParquetInputPlugin:
    def test_config_model(self):
        assert ParquetInputPlugin.config_model() == ParquetInputConfig

    def test_registered_as_parquet_input(self):
        cls = PluginRegistry.get("parquet", "input")
        assert cls.config_model() is ParquetInputConfig

    def test_read_rows(self, tmp_path):
        file_path = tmp_path / "test.parquet"
        _write_parquet(str(file_path), {"a": [1, 2, 3], "b": ["x", "y", "z"]})

        plugin = ParquetInputPlugin()
        config = ParquetInputConfig(file=str(file_path))
        columns, rows = plugin._read_rows(str(file_path), config)
        assert columns == ["a", "b"]
        rows_list = list(rows)
        assert len(rows_list) == 3
        assert rows_list[0] == ("1", "x")


class TestParquetPipelineEndToEnd:
    """端到端：Parquet 输入 → SQL 处理 → 验证结果。"""

    def test_parquet_input_to_sqlite(self, tmp_path):
        file_path = tmp_path / "input.parquet"
        _write_parquet(str(file_path), {
            "name": ["Alice", "Bob", "Carol"],
            "age": [30, 25, 35],
        })

        yaml_content = """
scene:
  name: parquet_test
  version: "1.0"

inputs:
  - name: people
    plugin: parquet
    table: person
    param_key: people_file
    config:
      type: parquet

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
        min: 2
        max: 2
        on_failure: block
"""
        yaml_path = tmp_path / "pipeline.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        from pipeforge.core.engine import PipelineEngine

        engine = PipelineEngine(str(yaml_path))
        result = engine.execute(params={"people_file": str(file_path)})

        assert "people" in result.inputs
        assert result.inputs["people"].rows_loaded == 3
        assert result.processors[0].tables_created == ["adults"]
        # checkpoint 验证 adults 表恰好 2 行（Alice 30, Carol 35 > 26）
        assert len(result.checks) == 1
        assert result.checks[0].passed is True

    def test_parquet_input_null_values(self, tmp_path):
        """None 值转为空字符串，全量加载 3 行。"""
        import pyarrow as pa
        import pyarrow.parquet as pq

        table = pa.table({"a": [1, None, 3], "b": ["x", "y", None]})
        file_path = tmp_path / "nulls.parquet"
        pq.write_table(table, str(file_path))

        yaml_content = """
scene:
  name: parquet_null_test
  version: "1.0"

inputs:
  - name: data
    plugin: parquet
    table: raw
    param_key: data_file
    config:
      type: parquet
"""
        yaml_path = tmp_path / "pipeline.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        from pipeforge.core.engine import PipelineEngine

        engine = PipelineEngine(str(yaml_path))
        result = engine.execute(params={"data_file": str(file_path)})

        assert result.inputs["data"].rows_loaded == 3
