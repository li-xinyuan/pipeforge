"""Tests for the database output plugin (SQLAlchemy-based)."""
import os
import tempfile

import pytest
from unittest.mock import MagicMock, patch

from pipeforge.config.models import DatabaseOutputConfig
from pipeforge.core.context import Context, Logger
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.plugins.output.database import (
    DatabaseOutputPlugin,
    _detect_dialect,
    _quote,
    _build_create_table_sql,
    _build_insert_sql,
    _build_upsert_sql,
)


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------

class TestDetectDialect:
    def test_sqlite(self):
        assert _detect_dialect("sqlite:///tmp/test.db") == "sqlite"

    def test_mysql(self):
        assert _detect_dialect("mysql+pymysql://user:pass@host:3306/db") == "mysql"

    def test_postgresql(self):
        assert _detect_dialect("postgresql+psycopg2://user:pass@host:5432/db") == "postgresql"

    def test_postgres_short(self):
        assert _detect_dialect("postgres://user:pass@host:5432/db") == "postgresql"

    def test_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported database dialect"):
            _detect_dialect("oracle://user:pass@host/db")


class TestQuote:
    def test_simple(self):
        assert _quote("name") == '"name"'

    def test_chinese(self):
        assert _quote("姓名") == '"姓名"'

    def test_invalid_empty(self):
        with pytest.raises(ValueError):
            _quote("")

    def test_invalid_special_chars(self):
        with pytest.raises(ValueError):
            _quote("drop table; --")


class TestBuildCreateTableSql:
    def test_basic(self):
        sql = _build_create_table_sql("users", ["id", "name"], "sqlite")
        assert sql == 'CREATE TABLE "users" ("id" TEXT, "name" TEXT)'

    def test_with_pk(self):
        sql = _build_create_table_sql("users", ["id", "name"], "sqlite", pk_columns=["id"])
        assert sql == 'CREATE TABLE "users" ("id" TEXT, "name" TEXT, PRIMARY KEY ("id"))'


class TestBuildInsertSql:
    def test_basic(self):
        sql = _build_insert_sql("users", ["id", "name"])
        assert sql == 'INSERT INTO "users" ("id", "name") VALUES (:id, :name)'


class TestBuildUpsertSql:
    def test_sqlite(self):
        sql = _build_upsert_sql("users", ["id", "name"], ["id"], "sqlite")
        assert sql == 'INSERT OR REPLACE INTO "users" ("id", "name") VALUES (:id, :name)'

    def test_mysql_with_non_pk(self):
        sql = _build_upsert_sql("users", ["id", "name"], ["id"], "mysql")
        assert "ON DUPLICATE KEY UPDATE" in sql
        assert '`name` = new.`name`' in sql

    def test_mysql_all_pk(self):
        sql = _build_upsert_sql("users", ["id"], ["id"], "mysql")
        # All columns are PK — just INSERT (no update clause needed)
        assert sql == 'INSERT INTO `users` (`id`) VALUES (:id)'

    def test_postgresql_with_non_pk(self):
        sql = _build_upsert_sql("users", ["id", "name"], ["id"], "postgresql")
        assert "ON CONFLICT" in sql
        assert "DO UPDATE SET" in sql
        assert 'EXCLUDED."name"' in sql

    def test_postgresql_all_pk(self):
        sql = _build_upsert_sql("users", ["id"], ["id"], "postgresql")
        assert "ON CONFLICT" in sql
        assert "DO NOTHING" in sql

    def test_unsupported_dialect(self):
        with pytest.raises(ValueError, match="Upsert not supported"):
            _build_upsert_sql("users", ["id"], ["id"], "oracle")


# ---------------------------------------------------------------------------
# Integration tests using real SQLite databases
# ---------------------------------------------------------------------------

class TestDatabaseOutputPluginSQLite:
    """End-to-end tests using SQLite as both source (intermediate) and target."""

    def _make_context(self, source_db: SQLiteManager) -> Context:
        logger = Logger()
        return Context(db=source_db, logger=logger, params={}, yaml_dir="/tmp", scene_name="test")

    def test_append_mode(self):
        """append mode: create table if not exists, then insert rows."""
        source_db = SQLiteManager()
        source_db.create_table("src", ["id", "name"])
        with source_db.transaction():
            source_db.insert_row("src", ("1", "Alice"))
            source_db.insert_row("src", ("2", "Bob"))

        fd, target_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            config = DatabaseOutputConfig(
                type="database",
                connection_string=f"sqlite:///{target_path}",
                target_table="target_tbl",
                write_mode="append",
                source_table="src",
                create_table_if_not_exists=True,
            )
            ctx = self._make_context(source_db)
            plugin = DatabaseOutputPlugin()
            count = plugin.execute(ctx, config)
            assert count == 2

            # Verify target
            target_db = SQLiteManager(target_path)
            rows = target_db.query('SELECT * FROM "target_tbl"')
            assert len(rows) == 2
            target_db.close()
        finally:
            source_db.close()
            source_db.remove()
            os.unlink(target_path)

    def test_replace_mode(self):
        """replace mode: drop + create + insert."""
        source_db = SQLiteManager()
        source_db.create_table("src", ["id", "val"])
        with source_db.transaction():
            source_db.insert_row("src", ("1", "hello"))

        fd, target_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            # Pre-populate target with old data
            target_db = SQLiteManager(target_path)
            target_db.create_table("target_tbl", ["id", "val"])
            with target_db.transaction():
                target_db.insert_row("target_tbl", ("99", "old"))
            target_db.close()

            config = DatabaseOutputConfig(
                type="database",
                connection_string=f"sqlite:///{target_path}",
                target_table="target_tbl",
                write_mode="replace",
                source_table="src",
            )
            ctx = self._make_context(source_db)
            plugin = DatabaseOutputPlugin()
            count = plugin.execute(ctx, config)
            assert count == 1

            # Verify target has only new data
            target_db = SQLiteManager(target_path)
            rows = target_db.query('SELECT * FROM "target_tbl"')
            assert len(rows) == 1
            assert rows[0][0] == "1"
            target_db.close()
        finally:
            source_db.close()
            source_db.remove()
            os.unlink(target_path)

    def test_upsert_mode_sqlite(self):
        """upsert on SQLite: INSERT OR REPLACE."""
        source_db = SQLiteManager()
        source_db.create_table("src", ["id", "name"])
        with source_db.transaction():
            source_db.insert_row("src", ("1", "Alice"))
            source_db.insert_row("src", ("2", "Bob"))

        fd, target_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            # Pre-populate target with existing row — table must have PRIMARY KEY for upsert
            target_db = SQLiteManager(target_path)
            target_db._conn.execute(
                'CREATE TABLE "target_tbl" ("id" TEXT, "name" TEXT, PRIMARY KEY ("id"))'
            )
            target_db._conn.commit()
            with target_db.transaction():
                target_db.insert_row("target_tbl", ("1", "OldAlice"))
            target_db.close()

            config = DatabaseOutputConfig(
                type="database",
                connection_string=f"sqlite:///{target_path}",
                target_table="target_tbl",
                write_mode="upsert",
                source_table="src",
                primary_key_columns=["id"],
            )
            ctx = self._make_context(source_db)
            plugin = DatabaseOutputPlugin()
            count = plugin.execute(ctx, config)
            assert count == 2

            # Verify target: id=1 should be updated, id=2 inserted
            target_db = SQLiteManager(target_path)
            rows = target_db.query('SELECT * FROM "target_tbl" ORDER BY "id"')
            assert len(rows) == 2
            assert rows[0][1] == "Alice"  # updated
            assert rows[1][1] == "Bob"    # inserted
            target_db.close()
        finally:
            source_db.close()
            source_db.remove()
            os.unlink(target_path)

    def test_missing_connection_string_raises(self):
        source_db = SQLiteManager()
        try:
            config = DatabaseOutputConfig(
                type="database",
                connection_string="",
                target_table="t",
                write_mode="append",
            )
            ctx = self._make_context(source_db)
            plugin = DatabaseOutputPlugin()
            with pytest.raises(ValueError, match="connection_string"):
                plugin.execute(ctx, config)
        finally:
            source_db.close()
            source_db.remove()

    def test_no_source_table_raises(self):
        source_db = SQLiteManager()
        try:
            config = DatabaseOutputConfig(
                type="database",
                connection_string="sqlite:///tmp/test.db",
                target_table="t",
                write_mode="append",
                source_table="",
            )
            ctx = self._make_context(source_db)
            plugin = DatabaseOutputPlugin()
            with pytest.raises(ValueError, match="No source table"):
                plugin.execute(ctx, config)
        finally:
            source_db.close()
            source_db.remove()

    def test_batch_size(self):
        """Verify batched inserts work correctly with small batch size."""
        source_db = SQLiteManager()
        source_db.create_table("src", ["id", "name"])
        with source_db.transaction():
            for i in range(5):
                source_db.insert_row("src", (str(i), f"name_{i}"))

        fd, target_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            config = DatabaseOutputConfig(
                type="database",
                connection_string=f"sqlite:///{target_path}",
                target_table="target_tbl",
                write_mode="append",
                source_table="src",
                batch_size=2,  # small batch to test batching
            )
            ctx = self._make_context(source_db)
            plugin = DatabaseOutputPlugin()
            count = plugin.execute(ctx, config)
            assert count == 5

            target_db = SQLiteManager(target_path)
            rows = target_db.query('SELECT * FROM "target_tbl"')
            assert len(rows) == 5
            target_db.close()
        finally:
            source_db.close()
            source_db.remove()
            os.unlink(target_path)


# ---------------------------------------------------------------------------
# Mock-based tests for MySQL / PostgreSQL dialects
# ---------------------------------------------------------------------------

class TestDatabaseOutputPluginMySQL:
    """Test MySQL-specific upsert SQL generation using mocks."""

    @patch("pipeforge.plugins.output.database.create_engine")
    def test_mysql_upsert(self, mock_create_engine):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        # Mock inspector to say table doesn't exist
        with patch("pipeforge.plugins.output.database.inspect") as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspector.get_table_names.return_value = []
            mock_inspect.return_value = mock_inspector

            mock_engine = MagicMock()
            mock_engine.connect.return_value = mock_conn
            mock_engine.begin.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            source_db = SQLiteManager()
            try:
                source_db.create_table("src", ["id", "name"])
                with source_db.transaction():
                    source_db.insert_row("src", ("1", "Alice"))

                config = DatabaseOutputConfig(
                    type="database",
                    connection_string="mysql+pymysql://user:pass@host:3306/db",
                    target_table="target_tbl",
                    write_mode="upsert",
                    source_table="src",
                    primary_key_columns=["id"],
                )
                logger = Logger()
                ctx = Context(db=source_db, logger=logger, params={}, yaml_dir="/tmp", scene_name="test")

                plugin = DatabaseOutputPlugin()
                count = plugin.execute(ctx, config)
                assert count == 1

                # Verify the upsert SQL was used
                executed_texts = [
                    call.args[0].text for call in mock_conn.execute.call_args_list
                ]
                upsert_calls = [t for t in executed_texts if "ON DUPLICATE KEY UPDATE" in t]
                assert len(upsert_calls) >= 1
            finally:
                source_db.close()
                source_db.remove()


class TestDatabaseOutputPluginPostgreSQL:
    """Test PostgreSQL-specific upsert SQL generation using mocks."""

    @patch("pipeforge.plugins.output.database.create_engine")
    def test_pg_upsert(self, mock_create_engine):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch("pipeforge.plugins.output.database.inspect") as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspector.get_table_names.return_value = []
            mock_inspect.return_value = mock_inspector

            mock_engine = MagicMock()
            mock_engine.connect.return_value = mock_conn
            mock_engine.begin.return_value = mock_conn
            mock_create_engine.return_value = mock_engine

            source_db = SQLiteManager()
            try:
                source_db.create_table("src", ["id", "name"])
                with source_db.transaction():
                    source_db.insert_row("src", ("1", "Alice"))

                config = DatabaseOutputConfig(
                    type="database",
                    connection_string="postgresql+psycopg2://user:pass@host:5432/db",
                    target_table="target_tbl",
                    write_mode="upsert",
                    source_table="src",
                    primary_key_columns=["id"],
                )
                logger = Logger()
                ctx = Context(db=source_db, logger=logger, params={}, yaml_dir="/tmp", scene_name="test")

                plugin = DatabaseOutputPlugin()
                count = plugin.execute(ctx, config)
                assert count == 1

                executed_texts = [
                    call.args[0].text for call in mock_conn.execute.call_args_list
                ]
                upsert_calls = [t for t in executed_texts if "ON CONFLICT" in t and "DO UPDATE" in t]
                assert len(upsert_calls) >= 1
            finally:
                source_db.close()
                source_db.remove()


class TestDatabaseOutputPluginConfigModel:
    def test_config_model(self):
        assert DatabaseOutputPlugin.config_model() is DatabaseOutputConfig
