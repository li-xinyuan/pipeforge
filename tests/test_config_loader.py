import os
import tempfile

import pytest

from pipeforge.config import load_yaml_config
from pipeforge.config.exceptions import ConfigError
from pipeforge.config.models import SceneConfig


class TestLoadYamlConfig:
    def test_load_valid_config(self):
        yaml_content = """
scene:
  name: 人员月报
  description: 测试
  version: "1.0"

inputs:
  - name: 人员明细
    plugin: excel
    table: person_detail
    param_key: person_file
    config:
      sheet: 人员列表

processors:
  - name: 数据合并
    plugin: sql
    output_tables:
      - report_data
    config:
      sql: CREATE TABLE report_data AS SELECT * FROM person_detail

output:
  plugin: excel
  config:
    template: templates/report.xlsx
    sheet: 报表
    source_table: report_data
    columns:
      - source: 姓名
        target: 姓名
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name

        try:
            config = load_yaml_config(path)
            assert isinstance(config, SceneConfig)
            assert config.scene.name == "人员月报"
        finally:
            os.unlink(path)

    def test_duplicate_table_names_detected(self):
        yaml_content = """
scene:
  name: test
  description: test
  version: "1.0"

inputs:
  - name: Input A
    plugin: excel
    table: same_table
    param_key: file_a
    config:
      sheet: Sheet1
  - name: Input B
    plugin: excel
    table: same_table
    param_key: file_b
    config:
      sheet: Sheet1

processors:
  - name: proc
    plugin: sql
    output_tables:
      - report
    config:
      sql: SELECT 1
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name

        try:
            with pytest.raises(ConfigError, match="same_table"):
                load_yaml_config(path)
        finally:
            os.unlink(path)

    def test_duplicate_param_key_detected(self):
        yaml_content = """
scene:
  name: test
  description: test
  version: "1.0"

inputs:
  - name: Input A
    plugin: excel
    table: table_a
    param_key: same_key
    config:
      sheet: Sheet1
  - name: Input B
    plugin: excel
    table: table_b
    param_key: same_key
    config:
      sheet: Sheet1

processors:
  - name: proc
    plugin: sql
    output_tables:
      - report
    config:
      sql: SELECT 1
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name

        try:
            with pytest.raises(ConfigError, match="same_key"):
                load_yaml_config(path)
        finally:
            os.unlink(path)

    def test_source_table_not_declared_in_output_tables(self):
        yaml_content = """
scene:
  name: test
  description: test
  version: "1.0"

inputs:
  - name: inp
    plugin: excel
    table: my_table
    param_key: file_key
    config:
      sheet: Sheet1

processors:
  - name: proc
    plugin: sql
    output_tables:
      - declared_table
    config:
      sql: SELECT 1

output:
  plugin: excel
  config:
    template: t.xlsx
    source_table: undeclared_table
    columns:
      - source: x
        target: y
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            path = f.name

        try:
            with pytest.raises(ConfigError, match="undeclared_table"):
                load_yaml_config(path)
        finally:
            os.unlink(path)
