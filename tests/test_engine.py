import os
import tempfile

import pytest

from pipeforge.core.engine import PipelineEngine

YAML_FIXTURE = """
scene:
  name: 测试场景
  description: 引擎单元测试
  version: "1.0"

inputs:
  - name: 输入A
    plugin: excel
    table: source_a
    param_key: file_a
    config:
      sheet: Sheet1

processors:
  - name: 处理A
    plugin: sql
    output_tables:
      - result_a
    config:
      sql: CREATE TABLE result_a AS SELECT 1 AS x

output:
  plugin: excel
  config:
    template: templates/report.xlsx
    sheet: 报表
    source_table: result_a
    columns:
      - source: x
        target: x
"""


@pytest.fixture
def yaml_path():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(YAML_FIXTURE)
        path = f.name
    yield path
    os.unlink(path)


class TestPipelineEngine:
    def test_load_config(self, yaml_path):
        engine = PipelineEngine(yaml_path)
        config = engine.config
        assert config.scene.name == "测试场景"

    def test_required_params(self, yaml_path):
        engine = PipelineEngine(yaml_path)
        params = engine.required_params()
        assert len(params) == 1
        assert params[0].key == "file_a"
        assert params[0].label == "输入A"

    def test_missing_params_raises(self, yaml_path):
        engine = PipelineEngine(yaml_path)
        with pytest.raises(ValueError, match="file_a"):
            engine.execute(params={})


def test_execute_dry_run_returns_intermediate_tables(tmp_path):
    """execute_dry_run should run input+processor steps, skip output, return intermediate table data."""
    from openpyxl import Workbook

    from pipeforge.core.engine import PipelineEngine

    # Create a minimal test Excel file with header row
    test_xlsx = tmp_path / "test.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["col"])
    ws.append(["hello"])
    wb.save(str(test_xlsx))

    yaml_path = tmp_path / "dry_run_test.yaml"
    yaml_path.write_text("""
scene: {name: test, version: "1.0"}
inputs:
  - name: src
    plugin: excel
    table: raw_data
    param_key: src_file
    config: {type: excel, sheet: Sheet1}
processors:
  - name: step1
    plugin: sql
    output_tables: [result]
    config: {type: sql, sql: "CREATE TABLE result AS SELECT 'hello' AS col FROM raw_data"}
output: null
""")
    engine = PipelineEngine(str(yaml_path))
    result = engine.execute_dry_run({"src_file": str(test_xlsx)})
    assert isinstance(result, dict)
    assert "tables" in result
    tables = {t["table_name"]: t for t in result["tables"]}
    assert "raw_data" in tables
    assert tables["raw_data"]["total_rows"] == 1
    assert "inputs" in result
    assert result["inputs"][0]["name"] == "src"
    assert "processors" in result
    assert result["processors"][0]["tables_created"] == ["result"]


class TestTopologicalSort:
    def test_linear_chain(self):
        from pipeforge.config.models import ProcessorSpec, SqlProcessorConfig
        from pipeforge.core.engine import PipelineEngine

        engine = PipelineEngine.__new__(PipelineEngine)
        procs = [
            ProcessorSpec(name="step1", plugin="sql", input_tables=[], output_tables=["t1"], config=SqlProcessorConfig(type="sql", sql="...")),
            ProcessorSpec(name="step2", plugin="sql", input_tables=["t1"], output_tables=["t2"], config=SqlProcessorConfig(type="sql", sql="...")),
            ProcessorSpec(name="step3", plugin="sql", input_tables=["t2"], output_tables=["t3"], config=SqlProcessorConfig(type="sql", sql="...")),
        ]
        result = engine.topological_sort(procs, {"src"})
        assert [p.name for p in result] == ["step1", "step2", "step3"]

    def test_parallel_branches(self):
        from pipeforge.config.models import ProcessorSpec, SqlProcessorConfig
        from pipeforge.core.engine import PipelineEngine

        engine = PipelineEngine.__new__(PipelineEngine)
        procs = [
            ProcessorSpec(name="step_b", plugin="sql", input_tables=[], output_tables=["tb"], config=SqlProcessorConfig(type="sql", sql="...")),
            ProcessorSpec(name="step_a", plugin="sql", input_tables=[], output_tables=["ta"], config=SqlProcessorConfig(type="sql", sql="...")),
            ProcessorSpec(name="merge", plugin="sql", input_tables=["ta", "tb"], output_tables=["tm"], config=SqlProcessorConfig(type="sql", sql="...")),
        ]
        result = engine.topological_sort(procs, {"src"})
        names = [p.name for p in result]
        assert names.index("merge") == 2
        assert set(names[:2]) == {"step_a", "step_b"}

    def test_detects_cycle(self):
        import pytest

        from pipeforge.config.models import ProcessorSpec, SqlProcessorConfig
        from pipeforge.core.engine import PipelineEngine

        engine = PipelineEngine.__new__(PipelineEngine)
        procs = [
            ProcessorSpec(name="a", plugin="sql", input_tables=["tb"], output_tables=["ta"], config=SqlProcessorConfig(type="sql", sql="...")),
            ProcessorSpec(name="b", plugin="sql", input_tables=["ta"], output_tables=["tb"], config=SqlProcessorConfig(type="sql", sql="...")),
        ]
        with pytest.raises(ValueError, match="Circular dependency"):
            engine.topological_sort(procs, {"src"})
