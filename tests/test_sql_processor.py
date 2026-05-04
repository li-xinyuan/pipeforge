import sqlite3

import pytest

from pipeforge.plugins.processor.sql import SqlProcessorPlugin
from pipeforge.plugins.processor import SqlProcessorPlugin as ImportedPlugin
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.context import Context
from pipeforge.config.models import SqlProcessorConfig


class TestSqlProcessorPlugin:
    @pytest.fixture
    def setup_db(self):
        db = SQLiteManager()
        db.create_table("source_tbl", ["id", "name"])
        with db.transaction():
            db.insert_row("source_tbl", ("1", "Alice"))
            db.insert_row("source_tbl", ("2", "Bob"))
        context = Context(db=db, params={}, yaml_dir="/tmp", scene_name="test")
        yield db, context
        db.close()
        db.remove()

    def test_config_model(self):
        assert SqlProcessorPlugin.config_model() == SqlProcessorConfig

    def test_execute_creates_table(self, setup_db):
        db, context = setup_db
        config = SqlProcessorConfig(
            sql="CREATE TABLE report AS SELECT * FROM source_tbl WHERE id = '1'"
        )
        plugin = SqlProcessorPlugin()
        plugin.name = "sql"
        plugin.label = "过滤器"
        plugin.execute(context, config)

        assert db.table_exists("report")
        rows = db.query("SELECT * FROM report")
        assert len(rows) == 1
        assert rows[0] == ("1", "Alice")

    def test_invalid_sql_raises(self, setup_db):
        db, context = setup_db
        config = SqlProcessorConfig(sql="SELECT * FROM nonexistent_table")
        plugin = SqlProcessorPlugin()
        plugin.name = "sql"
        plugin.label = "bad_sql"

        with pytest.raises(sqlite3.OperationalError):
            plugin.execute(context, config)

    def test_multiple_statements(self, setup_db):
        db, context = setup_db
        config = SqlProcessorConfig(
            sql="""
            CREATE TABLE report_a AS SELECT * FROM source_tbl;
            CREATE TABLE report_b AS SELECT name FROM source_tbl;
            """
        )
        plugin = SqlProcessorPlugin()
        plugin.name = "sql"
        plugin.label = "多语句"
        plugin.execute(context, config)

        assert db.table_exists("report_a")
        assert db.table_exists("report_b")
