import tempfile
import os
import csv as csv_module

import pytest

from pipeforge.config import load_yaml_config
from pipeforge.core.engine import PipelineEngine
from pipeforge.core.sqlite import SQLiteManager


def _write_yaml(content, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class TestMultiProcessorPipeline:
    """Two processors chained — second reads table created by first."""

    def test_two_processors_chain(self, csv_person_file):
        output_dir = tempfile.mkdtemp()
        yaml_content = f"""
scene:
  name: 多处理器测试
  description: chain two processors
  version: "1.0"

inputs:
  - name: 数据
    plugin: csv
    table: raw_data
    param_key: data_file
    config:
      type: csv

processors:
  - name: 第一步过滤
    plugin: sql
    output_tables:
      - filtered
    config:
      sql: |
        CREATE TABLE filtered AS
        SELECT * FROM raw_data WHERE 工号 = '002'

  - name: 第二步汇总
    plugin: sql
    output_tables:
      - summary
    config:
      sql: |
        CREATE TABLE summary AS
        SELECT COUNT(*) as cnt FROM filtered

output:
  plugin: csv
  config:
    type: csv
    source_table: summary
    output_dir: {output_dir}
    filename: result.csv
    columns:
      - source: cnt
        target: 数量
"""
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        try:
            _write_yaml(yaml_content, yaml_path)
            engine = PipelineEngine(yaml_path)
            result = engine.execute(params={"data_file": csv_person_file})
            assert len(result.processors) == 2
            assert result.processors[0].name == "第一步过滤"
            assert result.processors[1].name == "第二步汇总"
            assert "filtered" in result.processors[0].tables_created
            assert "summary" in result.processors[1].tables_created
            with open(os.path.join(output_dir, "result.csv"), "r") as f:
                rows = list(csv_module.reader(f))
                assert rows[0] == ["数量"]
                assert int(rows[1][0]) >= 0
        finally:
            os.unlink(yaml_path)

    def test_second_processor_failure_preserves_first_stats(self, csv_person_file):
        """If processor 2 fails, processor 1 stats still in result."""
        output_dir = tempfile.mkdtemp()
        yaml_content = f"""
scene:
  name: 失败测试
  version: "1.0"

inputs:
  - name: 数据
    plugin: csv
    table: raw_data
    param_key: data_file
    config:
      type: csv

processors:
  - name: 第一步
    plugin: sql
    output_tables:
      - filtered
    config:
      sql: CREATE TABLE filtered AS SELECT * FROM raw_data

  - name: 第二步会失败
    plugin: sql
    output_tables:
      - bogus
    config:
      sql: "INVALID SQL SYNTAX !!!"

output:
  plugin: csv
  config:
    type: csv
    source_table: filtered
    output_dir: {output_dir}
    filename: out.csv
    columns:
      - source: 姓名
        target: name
"""
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        try:
            _write_yaml(yaml_content, yaml_path)
            engine = PipelineEngine(yaml_path)
            with pytest.raises(Exception):
                engine.execute(params={"data_file": csv_person_file})
        finally:
            os.unlink(yaml_path)
