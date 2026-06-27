import csv as csv_module
import os
import tempfile

from pipeforge.core.engine import PipelineEngine


def _write_yaml(content, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class TestSingleInputPipeline:
    """Single input -> SQL processing -> output end-to-end flow."""
    def test_end_to_end(self, sample_xlsx, template_xlsx):
        output_dir = tempfile.mkdtemp()
        yaml_content = f"""
scene:
  name: 单输入测试
  description: test
  version: "1.0"

inputs:
  - name: 人员
    plugin: excel
    table: person
    param_key: person_file
    config:
      sheet: 人员列表

processors:
  - name: 统计
    plugin: sql
    output_tables:
      - report
    config:
      sql: |
        CREATE TABLE report AS
        SELECT 姓名, 部门, 岗位 FROM person WHERE 部门 = '技术部'

output:
  plugin: excel
  config:
    template: {template_xlsx}
    sheet: 报表
    output_dir: {output_dir}
    source_table: report
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 所属部门
      - source: 岗位
        target: 岗位
"""
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        _write_yaml(yaml_content, yaml_path)

        try:
            engine = PipelineEngine(yaml_path)
            result = engine.execute(params={"person_file": sample_xlsx})

            assert "人员" in result.inputs
            assert result.inputs["人员"].rows_loaded == 3
            assert len(result.processors) == 1
            assert result.processors[0].tables_created == ["report"]
            assert result.output is not None
            assert result.output.rows_written == 2  # 技术部 has 2 people
            assert os.path.exists(result.output.file_path)
        finally:
            os.unlink(yaml_path)
            for f in os.listdir(output_dir):
                os.unlink(os.path.join(output_dir, f))
            os.rmdir(output_dir)


class TestMultiInputPipeline:
    """Multi-input JOIN scenario."""
    def test_join_pipeline(self, sample_xlsx, sample_xlsx_attendance, template_xlsx):
        output_dir = tempfile.mkdtemp()
        yaml_content = f"""
scene:
  name: 多输入JOIN
  description: test
  version: "1.0"

inputs:
  - name: 人员
    plugin: excel
    table: person
    param_key: person_file
    config:
      sheet: 人员列表
  - name: 考勤
    plugin: excel
    table: attendance
    param_key: attendance_file
    config:
      sheet: 考勤统计

processors:
  - name: 合并统计
    plugin: sql
    output_tables:
      - report
    config:
      sql: |
        CREATE TABLE report AS
        SELECT
          p.姓名,
          p.部门,
          p.岗位,
          a.出勤天数,
          a.迟到次数,
          CASE WHEN CAST(a.迟到次数 AS INTEGER) > 3 THEN '预警' ELSE '正常' END AS 状态
        FROM person p
        LEFT JOIN attendance a ON p.工号 = a.工号

output:
  plugin: excel
  config:
    template: {template_xlsx}
    sheet: 报表
    output_dir: {output_dir}
    source_table: report
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 所属部门
      - source: 岗位
        target: 岗位
      - source: 出勤天数
        target: 出勤天数
      - source: 迟到次数
        target: 迟到次数
      - source: 状态
        target: 状态
"""
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        _write_yaml(yaml_content, yaml_path)

        try:
            engine = PipelineEngine(yaml_path)
            result = engine.execute(params={
                "person_file": sample_xlsx,
                "attendance_file": sample_xlsx_attendance,
            })

            assert result.inputs["人员"].rows_loaded == 3
            assert result.inputs["考勤"].rows_loaded == 3
            assert result.output is not None
            assert result.output.rows_written == 3
        finally:
            os.unlink(yaml_path)
            for f in os.listdir(output_dir):
                os.unlink(os.path.join(output_dir, f))
            os.rmdir(output_dir)


class TestEmptyResultsPipeline:
    """Empty query results should produce a header-only output file."""
    def test_empty_output(self, sample_xlsx, template_xlsx):
        output_dir = tempfile.mkdtemp()
        yaml_content = f"""
scene:
  name: 空结果测试
  description: test
  version: "1.0"

inputs:
  - name: 人员
    plugin: excel
    table: person
    param_key: person_file
    config:
      sheet: 人员列表

processors:
  - name: 过滤为空
    plugin: sql
    output_tables:
      - report
    config:
      sql: CREATE TABLE report AS SELECT 姓名, 部门, 岗位 FROM person WHERE 部门 = '不存在部门'

output:
  plugin: excel
  config:
    template: {template_xlsx}
    sheet: 报表
    output_dir: {output_dir}
    source_table: report
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 所属部门
      - source: 岗位
        target: 岗位
"""
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        _write_yaml(yaml_content, yaml_path)

        try:
            engine = PipelineEngine(yaml_path)
            result = engine.execute(params={"person_file": sample_xlsx})

            assert result.output is not None
            assert result.output.rows_written == 0
            assert os.path.exists(result.output.file_path)
        finally:
            os.unlink(yaml_path)
            for f in os.listdir(output_dir):
                os.unlink(os.path.join(output_dir, f))
            os.rmdir(output_dir)


class TestNoInputPipeline:
    """Empty inputs -- processor creates table from scratch via SQL."""
    def test_no_inputs(self, template_xlsx):
        output_dir = tempfile.mkdtemp()
        yaml_content = f"""
scene:
  name: 无输入测试
  description: test
  version: "1.0"

processors:
  - name: 直接生成
    plugin: sql
    output_tables:
      - report
    config:
      sql: |
        CREATE TABLE report (姓名, 部门, 岗位);
        INSERT INTO report VALUES ('系统生成', 'IT', '自动');

output:
  plugin: excel
  config:
    template: {template_xlsx}
    sheet: 报表
    output_dir: {output_dir}
    source_table: report
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 所属部门
      - source: 岗位
        target: 岗位
"""
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        _write_yaml(yaml_content, yaml_path)

        try:
            engine = PipelineEngine(yaml_path)
            assert len(engine.required_params()) == 0
            result = engine.execute(params={})

            assert "report" in result.processors[0].tables_created
            assert result.output is not None
            assert result.output.rows_written == 1
        finally:
            os.unlink(yaml_path)
            for f in os.listdir(output_dir):
                os.unlink(os.path.join(output_dir, f))
            os.rmdir(output_dir)


class TestCsvInputPipeline:
    """CSV input -> SQL processor -> verify data loaded."""

    def test_csv_input_loads_data(self, csv_person_file):
        output_dir = tempfile.mkdtemp()
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        yaml_content = """scene:
  name: CSV场景
  description: CSV输入测试
  version: "1.0"

inputs:
  - name: csv_data
    plugin: csv
    table: csv_data
    param_key: csv_file
    config:
      type: csv
      delimiter: ","

processors:
  - name: process
    plugin: sql
    output_tables:
      - result
    config:
      type: sql
      sql: CREATE TABLE result AS SELECT * FROM csv_data WHERE 工号 = '001'
"""
        try:
            _write_yaml(yaml_content, yaml_path)
            engine = PipelineEngine(yaml_path)
            result = engine.execute(params={"csv_file": csv_person_file})

            assert result.inputs["csv_data"].rows_loaded == 2
            assert len(result.processors) == 1
        finally:
            os.unlink(yaml_path)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)


class TestCsvOutputPipeline:
    """Input -> SQL -> CSV output."""

    def test_pipeline_to_csv_output(self, sample_xlsx):
        output_dir = tempfile.mkdtemp()
        fd, yaml_path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        yaml_content = f"""scene:
  name: CSV输出测试
  description: 输出CSV格式
  version: "1.0"

inputs:
  - name: people
    plugin: excel
    table: person
    param_key: person_file
    config:
      type: excel
      sheet: 人员列表

processors:
  - name: process
    plugin: sql
    output_tables:
      - result
    config:
      type: sql
      sql: CREATE TABLE result AS SELECT * FROM person

output:
  plugin: csv
  config:
    type: csv
    source_table: result
    output_dir: "{output_dir}"
    filename: output.csv
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 部门
      - source: 工号
        target: 工号
"""
        try:
            _write_yaml(yaml_content, yaml_path)
            engine = PipelineEngine(yaml_path)
            result = engine.execute(params={"person_file": sample_xlsx})

            assert result.inputs["people"].rows_loaded > 0
            assert result.output.rows_written > 0

            # Verify CSV output exists and has correct content
            csv_path = os.path.join(output_dir, "output.csv")
            assert os.path.exists(csv_path)

            with open(csv_path, encoding="utf-8", newline="") as f:
                reader = csv_module.reader(f)
                rows = list(reader)
                assert rows[0] == ["姓名", "部门", "工号"]
                assert len(rows) > 1  # At least one data row
        finally:
            os.unlink(yaml_path)
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
