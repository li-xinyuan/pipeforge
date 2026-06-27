import os
import tempfile

import pytest
from click.testing import CliRunner

from pipeforge.cli import main

YAML_FIXTURE = """
scene:
  name: CLI测试
  description: test
  version: "1.0"

inputs:
  - name: 数据源
    plugin: excel
    table: source_tbl
    param_key: data_file
    config:
      sheet: Sheet1

processors:
  - name: 处理
    plugin: sql
    output_tables:
      - result
    config:
      sql: CREATE TABLE result AS SELECT 1 AS x

output:
  plugin: excel
  config:
    template: templates/report.xlsx
    sheet: 报表
    source_table: result
    columns:
      - source: x
        target: x
"""


class TestCLI:
    @pytest.fixture
    def yaml_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(YAML_FIXTURE)
            path = f.name
        yield path
        os.unlink(path)

    def test_run_missing_required_params_shows_error(self, yaml_config):
        runner = CliRunner()
        result = runner.invoke(main, ["run", yaml_config])
        assert result.exit_code != 0
        assert "data_file" in result.output or "Missing" in result.output

    def test_run_nonexistent_file(self):
        runner = CliRunner()
        result = runner.invoke(main, ["run", "/nonexistent/path.yaml"])
        assert result.exit_code != 0

    def test_version_command(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
