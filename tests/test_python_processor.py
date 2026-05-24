import pytest


def test_python_processor_registered():
    from pipeforge.plugins.processor.python import PythonProcessorPlugin  # noqa: F401
    from pipeforge.core.registry import PluginRegistry
    cls = PluginRegistry.get("python", "processor")
    assert cls is not None


def test_python_processor_executes_script(tmp_path):
    from pipeforge.core.engine import PipelineEngine
    import openpyxl

    xlsx = tmp_path / "test.xlsx"
    wb = openpyxl.Workbook()
    wb.active.append(["name", "age"])
    wb.active.append(["Alice", "30"])
    wb.save(str(xlsx))

    yaml_path = tmp_path / "pipeline.yaml"
    yaml_path.write_text(f"""
scene: {{name: test, version: "1.0"}}
inputs:
  - name: src
    plugin: excel
    table: raw_data
    param_key: f
    config: {{type: excel, sheet: Sheet}}
processors:
  - name: py_step
    plugin: python
    input_tables: [raw_data]
    output_tables: [adults]
    config:
      type: python
      script: |
        def process(ctx):
            conn = ctx.db.connection
            conn.execute('CREATE TABLE adults AS SELECT * FROM raw_data WHERE CAST(age AS INTEGER) >= 18')
""")

    engine = PipelineEngine(str(yaml_path))
    result = engine.execute({"f": str(xlsx)})
    assert result is not None


def test_python_processor_missing_process_fn():
    from pipeforge.plugins.processor.python import PythonProcessorPlugin
    from pipeforge.config.models import PythonProcessorConfig
    from pipeforge.core.context import Context, Logger
    from pipeforge.core.sqlite import SQLiteManager

    db = SQLiteManager()
    ctx = Context(db=db, params={}, yaml_dir="/tmp", scene_name="test", logger=Logger())
    plugin = PythonProcessorPlugin()
    config = PythonProcessorConfig(script="x = 1")
    with pytest.raises(ValueError, match="必须定义 process"):
        plugin.execute(ctx, config)
