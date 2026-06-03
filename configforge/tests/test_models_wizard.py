import pytest
from pydantic import ValidationError
from configforge.models.wizard import (
    SceneInfo, ProcessorConfig, InputSource, WizardState,
    ExcelInputConfig, CsvInputConfig, DatabaseInputConfig,
)


class TestSceneInfo:
    def test_defaults(self):
        s = SceneInfo(name="test")
        assert s.description == ""
        assert s.version == "1.0"

    def test_name_below_min_length_raises(self):
        with pytest.raises(ValidationError):
            SceneInfo(name="")

    def test_name_max_length(self):
        s = SceneInfo(name="a" * 200)
        assert len(s.name) == 200

    def test_name_exceeds_max_length_raises(self):
        with pytest.raises(ValidationError):
            SceneInfo(name="a" * 201)


class TestProcessorConfig:
    def test_default_sql(self):
        p = ProcessorConfig()
        assert p.plugin == "sql"
        assert p.sql == ""
        assert p.script == ""

    def test_python_plugin(self):
        p = ProcessorConfig(plugin="python", script="def process(ctx): pass", output_tables=["out"])
        assert p.plugin == "python"

    def test_empty_config_is_valid(self):
        """Empty placeholder ProcessorConfig should pass validation."""
        p = ProcessorConfig()
        assert p.plugin == "sql"

    def test_sql_with_empty_sql_raises(self):
        """If output_tables is set, sql must be non-empty for sql plugin."""
        with pytest.raises(ValidationError, match="sql 字段不能为空"):
            ProcessorConfig(plugin="sql", sql="", output_tables=["out"])

    def test_sql_with_non_empty_sql_passes(self):
        p = ProcessorConfig(plugin="sql", sql="SELECT 1", output_tables=["out"])
        assert p.sql == "SELECT 1"

    def test_python_with_empty_script_raises(self):
        """If output_tables is set, script must be non-empty for python plugin."""
        with pytest.raises(ValidationError, match="script 字段不能为空"):
            ProcessorConfig(plugin="python", script="", output_tables=["out"])

    def test_python_with_script_passes(self):
        p = ProcessorConfig(plugin="python", script="def process(ctx): pass", output_tables=["out"])
        assert p.script == "def process(ctx): pass"


class TestInputSource:
    def test_default_excel(self):
        inp = InputSource()
        assert inp.plugin == "excel"
        assert isinstance(inp.config, ExcelInputConfig)

    def test_csv_input(self):
        inp = InputSource(plugin="csv", config={"type": "csv", "delimiter": ";", "encoding": "gbk", "hasHeader": True})
        assert isinstance(inp.config, CsvInputConfig)
        assert inp.config.delimiter == ";"

    def test_database_input(self):
        inp = InputSource(plugin="database", config={"type": "database", "connectionId": "conn-1", "queryType": "table", "tables": ["users"]})
        assert isinstance(inp.config, DatabaseInputConfig)
        assert inp.config.connection_id == "conn-1"


class TestWizardState:
    def test_defaults(self):
        ws = WizardState()
        assert ws.current_step == 1
        assert ws.scene.name == "Untitled Scene"
        assert ws.inputs == []
        assert ws.output is None

    def test_serialization_roundtrip(self):
        ws = WizardState(current_step=2)
        data = ws.model_dump()
        assert data["current_step"] == 2
        ws2 = WizardState(**data)
        assert ws2.current_step == 2
