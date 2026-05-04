import tempfile
import os

import pytest

from pipeforge.core.engine import PipelineEngine, RequiredParam


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
