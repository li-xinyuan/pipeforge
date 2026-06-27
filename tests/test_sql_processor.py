import sqlite3

import pytest

from pipeforge.config.models import SqlProcessorConfig
from pipeforge.core.context import Context
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.plugins.processor.sql import SqlProcessorPlugin


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
        assert tuple(rows[0]) == ("1", "Alice")

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

    def test_jinja2_template_rendering(self, setup_db):
        """SQL 中的 {{param}} 被 context.params 的值替换"""
        db, context = setup_db
        context.params = {"source_table": "source_tbl", "target_name": "Alice"}

        config = SqlProcessorConfig(
            sql="CREATE TABLE filtered AS "
                "SELECT * FROM {{ source_table }} WHERE name = '{{ target_name }}'"
        )
        plugin = SqlProcessorPlugin()
        plugin.name = "sql"
        plugin.label = "模板渲染"
        plugin.execute(context, config)

        assert db.table_exists("filtered")
        rows = db.query("SELECT * FROM filtered")
        assert len(rows) == 1
        assert tuple(rows[0]) == ("1", "Alice")

    def test_jinja2_missing_param_raises(self, setup_db):
        """引用未定义的变量抛出 StrictUndefined 错误"""
        db, context = setup_db
        context.params = {}

        config = SqlProcessorConfig(
            sql="SELECT * FROM {{ undefined_var }}"
        )
        plugin = SqlProcessorPlugin()
        plugin.name = "sql"
        plugin.label = "缺失参数"
        with pytest.raises(Exception):
            plugin.execute(context, config)

    def test_jinja2_no_variables_still_works(self, setup_db):
        """没有 {{ }} 的 SQL 正常执行（向后兼容）"""
        db, context = setup_db
        context.params = {"unused": "value"}

        config = SqlProcessorConfig(
            sql="CREATE TABLE copy AS SELECT * FROM source_tbl"
        )
        plugin = SqlProcessorPlugin()
        plugin.name = "sql"
        plugin.label = "无变量"
        plugin.execute(context, config)
        assert db.table_exists("copy")

    def test_jinja2_multiple_params_in_one_sql(self, setup_db):
        """多个模板变量在一次渲染中全部替换"""
        db, context = setup_db
        context.params = {"src": "source_tbl", "dest": "multi_test", "id_val": "1"}

        config = SqlProcessorConfig(
            sql="CREATE TABLE {{ dest }} AS "
                "SELECT * FROM {{ src }} WHERE id = '{{ id_val }}'"
        )
        plugin = SqlProcessorPlugin()
        plugin.name = "sql"
        plugin.label = "多变量"
        plugin.execute(context, config)
        assert db.table_exists("multi_test")
