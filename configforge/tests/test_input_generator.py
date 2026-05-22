import io, pytest
from configforge.generators.input.excel_input import ExcelInputGenerator
from configforge.models.wizard import ExcelInputConfig


def test_infer_config_from_excel_info():
    gen = ExcelInputGenerator()
    config = gen.infer_config({"file_id": "f1", "type": "excel", "columns": ["姓名", "部门"], "original_name": "person.xlsx"})
    assert config.type == "excel"
    assert config.sheet == "Sheet1"


def test_build_config_from_wizard_state():
    gen = ExcelInputGenerator()
    state = {"name": "人员明细", "table": "person", "param_key": "person_file", "file_id": "f1", "sheet": "人员列表"}
    config = gen.build_config(state)
    assert config.sheet == "人员列表"


def test_validate_empty_sheet_rejected():
    gen = ExcelInputGenerator()
    errors = gen.validate_config(ExcelInputConfig(sheet=""))
    assert any("Sheet" in str(e) for e in errors)


class TestDatabaseInputGenerator:
    def test_infer_config_from_source(self):
        from configforge.generators.input.database_generator import DatabaseInputGenerator
        gen = DatabaseInputGenerator()
        config = gen.infer_config({"query_type": "table", "tables": ["users"], "sql": ""})
        assert config.type == "database"
        assert config.query_type == "table"
        assert config.tables == ["users"]

    def test_infer_config_defaults_to_table(self):
        from configforge.generators.input.database_generator import DatabaseInputGenerator
        gen = DatabaseInputGenerator()
        config = gen.infer_config({"tables": ["orders"]})
        assert config.query_type == "table"

    def test_build_config_from_wizard_state(self):
        from configforge.generators.input.database_generator import DatabaseInputGenerator
        gen = DatabaseInputGenerator()
        config = gen.build_config({
            "connection_id": "conn-1",
            "db_type": "mysql",
            "query_type": "sql",
            "tables": [],
            "sql": "SELECT * FROM users",
        })
        assert config.type == "database"
        assert config.connection_id == "conn-1"
        assert config.db_type == "mysql"
        assert config.query_type == "sql"
        assert config.sql == "SELECT * FROM users"

    def test_validate_empty_connection_id(self):
        from configforge.generators.input.database_generator import DatabaseInputGenerator
        from configforge.models.wizard import DatabaseInputConfig
        gen = DatabaseInputGenerator()
        errors = gen.validate_config(DatabaseInputConfig(tables=["users"]))
        assert any("Connection" in e for e in errors)

    def test_validate_tables_and_sql_mutually_exclusive(self):
        from configforge.generators.input.database_generator import DatabaseInputGenerator
        from configforge.models.wizard import DatabaseInputConfig
        gen = DatabaseInputGenerator()
        errors = gen.validate_config(DatabaseInputConfig(
            connection_id="c1", tables=["users"], sql="SELECT 1",
        ))
        assert any("mutually exclusive" in e for e in errors)

    def test_validate_either_tables_or_sql_required(self):
        from configforge.generators.input.database_generator import DatabaseInputGenerator
        from configforge.models.wizard import DatabaseInputConfig
        gen = DatabaseInputGenerator()
        errors = gen.validate_config(DatabaseInputConfig(connection_id="c1"))
        assert any("Either tables or sql" in e for e in errors)

    def test_validate_passing(self):
        from configforge.generators.input.database_generator import DatabaseInputGenerator
        from configforge.models.wizard import DatabaseInputConfig
        gen = DatabaseInputGenerator()
        errors = gen.validate_config(DatabaseInputConfig(connection_id="c1", tables=["users"]))
        assert errors == []
