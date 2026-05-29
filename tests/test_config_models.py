import pytest
from pydantic import ValidationError

from pipeforge.config.models import (
    SceneMeta,
    ExcelInputConfig,
    CsvInputConfig,
    DbInputConfig,
    CsvOutputConfig,
    InputSpec,
    SqlProcessorConfig,
    ProcessorSpec,
    ColumnMapping,
    ExcelOutputConfig,
    OutputSpec,
    SceneConfig,
)


class TestSceneMeta:
    def test_valid_scene_meta(self):
        meta = SceneMeta(name="人员月报", description="测试场景", version="1.0")
        assert meta.name == "人员月报"
        assert meta.version == "1.0"

    def test_missing_required_name_raises(self):
        with pytest.raises(ValidationError):
            SceneMeta(description="test", version="1.0")

    def test_extra_field_forbidden(self):
        with pytest.raises(ValidationError):
            SceneMeta(name="test", description="test", version="1.0", unknown="bad")


class TestInputSpec:
    def test_valid_input_spec(self):
        spec = InputSpec(
            name="人员明细",
            plugin="excel",
            table="person_detail",
            param_key="person_file",
            config=ExcelInputConfig(sheet="人员列表"),
        )
        assert spec.config.sheet == "人员列表"

    def test_invalid_plugin_name_still_allowed_by_model(self):
        spec = InputSpec(
            name="test",
            plugin="nonexistent",
            table="t",
            param_key="p",
            config=ExcelInputConfig(sheet="s"),
        )
        assert spec.plugin == "nonexistent"

    def test_type_field_defaults_to_excel(self):
        """ExcelInputConfig 的 type 字段默认为 'excel'"""
        cfg = ExcelInputConfig(sheet="Sheet1")
        assert cfg.type == "excel"

    def test_config_rejects_wrong_type(self):
        """discriminator 拒绝不匹配的 type 值"""
        with pytest.raises(ValidationError):
            InputSpec(
                name="test",
                plugin="excel",
                table="t",
                param_key="p",
                config={"type": "json", "sheet": "s"},
            )

    def test_csv_input_spec_accepted(self):
        """CSV type is correctly routed by the discriminated union"""
        spec = InputSpec(
            name="test",
            plugin="csv",
            table="t",
            param_key="p",
            config=CsvInputConfig(delimiter=";"),
        )
        assert spec.config.type == "csv"
        assert spec.config.delimiter == ";"

    def test_csv_input_from_dict(self):
        """CSV input config can be constructed from a dict"""
        spec = InputSpec(
            name="test",
            plugin="csv",
            table="t",
            param_key="p",
            config={"type": "csv", "delimiter": "\t", "encoding": "gbk"},
        )
        assert spec.config.delimiter == "\t"
        assert spec.config.encoding == "gbk"



class TestProcessorSpec:
    def test_valid_processor_spec(self):
        spec = ProcessorSpec(
            name="数据合并",
            plugin="sql",
            output_tables=["report_data"],
            config=SqlProcessorConfig(sql="SELECT 1"),
        )
        assert spec.output_tables == ["report_data"]

    def test_empty_output_tables(self):
        spec = ProcessorSpec(
            name="test",
            plugin="sql",
            output_tables=[],
            config=SqlProcessorConfig(sql="SELECT 1"),
        )
        assert spec.output_tables == []

    def test_processor_config_type_defaults_to_sql(self):
        cfg = SqlProcessorConfig(sql="SELECT 1")
        assert cfg.type == "sql"


class TestColumnMapping:
    def test_valid_column_mapping(self):
        cm = ColumnMapping(source="姓名", target="员工姓名")
        assert cm.source == "姓名"
        assert cm.target == "员工姓名"

    def test_empty_source_raises(self):
        with pytest.raises(ValidationError):
            ColumnMapping(source="", target="姓名")


class TestProcessorSpecWithInputTables:
    def test_processor_spec_with_input_tables(self):
        spec = ProcessorSpec(
            name="test_step",
            plugin="sql",
            input_tables=["src_table"],
            output_tables=["out_table"],
            config=SqlProcessorConfig(type="sql", sql="SELECT * FROM src_table"),
        )
        assert spec.input_tables == ["src_table"]
        assert spec.output_tables == ["out_table"]

    def test_processor_spec_empty_input_tables_defaults_to_empty_list(self):
        spec = ProcessorSpec(
            name="first_step",
            plugin="sql",
            config=SqlProcessorConfig(type="sql", sql="CREATE TABLE x AS SELECT 1"),
        )
        assert spec.input_tables == []


class TestSceneConfig:
    def test_full_valid_config(self):
        config = SceneConfig(
            scene=SceneMeta(name="人员月报", description="测试", version="1.0"),
            inputs=[
                InputSpec(
                    name="人员明细",
                    plugin="excel",
                    table="person_detail",
                    param_key="person_file",
                    config=ExcelInputConfig(sheet="人员列表"),
                )
            ],
            processors=[
                ProcessorSpec(
                    name="数据合并",
                    plugin="sql",
                    output_tables=["report_data"],
                    config=SqlProcessorConfig(
                        sql="CREATE TABLE report_data AS SELECT * FROM person_detail"
                    ),
                )
            ],
            output=OutputSpec(
                plugin="excel",
                config=ExcelOutputConfig(
                    template="templates/report.xlsx",
                    sheet="报表",
                    source_table="report_data",
                    columns=[ColumnMapping(source="姓名", target="姓名")],
                ),
            ),
        )
        assert config.scene.name == "人员月报"

    def test_empty_inputs_is_valid(self):
        config = SceneConfig(
            scene=SceneMeta(name="test", description="test", version="1.0"),
            inputs=[],
            processors=[
                ProcessorSpec(
                    name="gen",
                    plugin="sql",
                    output_tables=["data"],
                    config=SqlProcessorConfig(sql="CREATE TABLE data AS SELECT 1 AS x"),
                )
            ],
        )
        assert len(config.inputs) == 0

    def test_empty_columns_allowed(self):
        cfg = ExcelOutputConfig(
            template="t.xlsx",
            source_table="t",
            columns=[],
        )
        assert cfg.columns == []

    def test_output_config_type_defaults_to_excel(self):
        cfg = ExcelOutputConfig(
            template="t.xlsx",
            source_table="t",
            columns=[ColumnMapping(source="a", target="b")],
        )
        assert cfg.type == "excel"


class TestCsvInputConfig:
    def test_type_defaults_to_csv(self):
        cfg = CsvInputConfig()
        assert cfg.type == "csv"

    def test_default_values(self):
        cfg = CsvInputConfig()
        assert cfg.delimiter == ","
        assert cfg.encoding == "utf-8"
        assert cfg.has_header is True

    def test_custom_delimiter(self):
        cfg = CsvInputConfig(delimiter=";")
        assert cfg.delimiter == ";"

    def test_custom_encoding(self):
        cfg = CsvInputConfig(encoding="gbk")
        assert cfg.encoding == "gbk"

    def test_no_header(self):
        cfg = CsvInputConfig(has_header=False)
        assert cfg.has_header is False


class TestCsvOutputConfig:
    def test_type_defaults_to_csv(self):
        cfg = CsvOutputConfig(
            source_table="t",
            columns=[ColumnMapping(source="a", target="b")],
        )
        assert cfg.type == "csv"

    def test_default_delimiter(self):
        cfg = CsvOutputConfig(
            source_table="t",
            columns=[ColumnMapping(source="a", target="b")],
        )
        assert cfg.delimiter == ","

    def test_empty_columns_allowed(self):
        cfg = CsvOutputConfig(source_table="t", columns=[])
        assert cfg.columns == []


class TestDbInputConfig:
    def test_type_defaults_to_database(self):
        cfg = DbInputConfig(connection_string="sqlite:///test.db", tables=["users"])
        assert cfg.type == "database"

    def test_default_tables_empty(self):
        cfg = DbInputConfig(connection_string="sqlite:///test.db", tables=["users"])
        assert cfg.tables == ["users"]

    def test_default_sql_empty(self):
        cfg = DbInputConfig(connection_string="sqlite:///test.db", sql="SELECT 1")
        assert cfg.sql == "SELECT 1"

    def test_tables_and_sql_mutually_exclusive(self):
        with pytest.raises(ValidationError, match="互斥"):
            DbInputConfig(connection_string="sqlite:///test.db", tables=["users"], sql="SELECT 1")

    def test_neither_tables_nor_sql_raises(self):
        with pytest.raises(ValidationError, match="tables 和 sql 必须提供一个"):
            DbInputConfig(connection_string="sqlite:///test.db")

    def test_empty_tables_raises(self):
        with pytest.raises(ValidationError, match="tables 和 sql 必须提供一个"):
            DbInputConfig(connection_string="sqlite:///test.db", tables=[])

    def test_whitespace_sql_raises(self):
        with pytest.raises(ValidationError, match="tables 和 sql 必须提供一个"):
            DbInputConfig(connection_string="sqlite:///test.db", sql="   ")

    def test_extra_field_forbidden(self):
        with pytest.raises(ValidationError):
            DbInputConfig(connection_string="sqlite:///test.db", tables=["users"], unknown="x")

    def test_valid_with_tables(self):
        cfg = DbInputConfig(connection_string="sqlite:///test.db", db_type="sqlite", tables=["users"])
        assert cfg.tables == ["users"]
        assert cfg.sql == ""

    def test_valid_with_sql(self):
        cfg = DbInputConfig(connection_string="sqlite:///test.db", db_type="sqlite", sql="SELECT * FROM users")
        assert cfg.sql == "SELECT * FROM users"
        assert cfg.tables == []
