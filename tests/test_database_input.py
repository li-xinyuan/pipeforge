from unittest.mock import MagicMock, patch

import pytest

from pipeforge.config.models import DbInputConfig
from pipeforge.core.context import Context
from pipeforge.plugins.input.database import DatabaseInputPlugin


class TestDatabaseInputPlugin:
    def test_label(self):
        plugin = DatabaseInputPlugin()
        assert plugin.label is not None

    def test_config_model_returns_db_input_config(self):
        assert DatabaseInputPlugin.config_model() is DbInputConfig

    def test_table_name_default(self):
        plugin = DatabaseInputPlugin()
        assert isinstance(plugin.table_name, str)

    @patch("pipeforge.plugins.input.database.create_engine")
    def test_execute_with_sql(self, mock_create_engine):
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "name"]
        mock_result.fetchall.return_value = [(1, "Alice")]
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        plugin = DatabaseInputPlugin()
        config = DbInputConfig(type="database", connection_string="sqlite:///test.db", db_type="sqlite", sql="SELECT * FROM users")

        mock_db = MagicMock()
        mock_logger = MagicMock()
        ctx = Context(db=mock_db, logger=mock_logger, params={}, yaml_dir="/tmp", scene_name="test")

        plugin.execute(ctx, config)

        mock_db.create_table.assert_called_once()
        mock_db.insert_row.assert_called_once()

    @patch("pipeforge.plugins.input.database.create_engine")
    def test_execute_with_tables(self, mock_create_engine):
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id"]
        mock_result.fetchall.return_value = [(1,)]
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        plugin = DatabaseInputPlugin()
        config = DbInputConfig(type="database", connection_string="sqlite:///test.db", tables=["users"])

        mock_db = MagicMock()
        mock_logger = MagicMock()
        ctx = Context(db=mock_db, logger=mock_logger, params={}, yaml_dir="/tmp", scene_name="test")

        plugin.execute(ctx, config)

        mock_db.create_table.assert_called_once()

    @patch("pipeforge.plugins.input.database.create_engine")
    def test_execute_with_tables_and_sql_mutually_exclusive(self, mock_create_engine):
        """DbInputConfig model_validator rejects both tables and sql together."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            DbInputConfig(type="database", connection_string="sqlite:///test.db", tables=["users"], sql="SELECT * FROM users")
