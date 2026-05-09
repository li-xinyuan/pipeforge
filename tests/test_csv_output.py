import os
import csv as csv_module
import tempfile
import pytest
from unittest.mock import MagicMock

from pipeforge.plugins.output.csv import CsvOutputPlugin
from pipeforge.config.models import CsvOutputConfig, ColumnMapping


def _make_context(db, scene_name="test_scene"):
    ctx = MagicMock()
    ctx.db = db
    ctx.scene_name = scene_name
    ctx.logger = MagicMock()
    ctx.output_path = None
    return ctx


def _setup_db(db, table_name, columns, rows):
    db.create_table(table_name, columns)
    for row in rows:
        db.insert_row(table_name, row)
    db._conn.commit()


class TestCsvOutputPlugin:
    def test_config_model(self):
        assert CsvOutputPlugin.config_model() == CsvOutputConfig

    def test_registered_as_csv_output(self):
        from pipeforge.core.registry import PluginRegistry
        cls = PluginRegistry.get("csv", "output")
        assert cls is CsvOutputPlugin

    def test_basic_write(self):
        from pipeforge.core.sqlite import SQLiteManager

        db = SQLiteManager()
        try:
            _setup_db(db, "person", ["name", "age"], [("Alice", "30"), ("Bob", "25")])

            output_dir = tempfile.mkdtemp()
            config = CsvOutputConfig(
                source_table="person",
                output_dir=output_dir,
                filename="out.csv",
                columns=[
                    ColumnMapping(source="name", target="name"),
                    ColumnMapping(source="age", target="age"),
                ],
            )

            ctx = _make_context(db)
            plugin = CsvOutputPlugin()
            plugin.execute(ctx, config)

            csv_path = os.path.join(output_dir, "out.csv")
            assert os.path.exists(csv_path)

            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv_module.reader(f)
                rows = list(reader)
                assert rows[0] == ["name", "age"]
                assert rows[1:] == [["Alice", "30"], ["Bob", "25"]]
        finally:
            db.close()
            db.remove()

    def test_column_reorder(self):
        from pipeforge.core.sqlite import SQLiteManager

        db = SQLiteManager()
        try:
            _setup_db(db, "person", ["name", "age", "city"],
                      [("Alice", "30", "NYC")])

            output_dir = tempfile.mkdtemp()
            config = CsvOutputConfig(
                source_table="person",
                output_dir=output_dir,
                filename="out.csv",
                columns=[
                    ColumnMapping(source="city", target="城市"),
                    ColumnMapping(source="name", target="姓名"),
                ],
            )

            ctx = _make_context(db)
            plugin = CsvOutputPlugin()
            plugin.execute(ctx, config)

            csv_path = os.path.join(output_dir, "out.csv")
            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv_module.reader(f)
                rows = list(reader)
                assert rows[0] == ["城市", "姓名"]
                assert rows[1] == ["NYC", "Alice"]
        finally:
            db.close()
            db.remove()

    def test_custom_delimiter(self):
        from pipeforge.core.sqlite import SQLiteManager

        db = SQLiteManager()
        try:
            _setup_db(db, "t", ["a", "b"], [("1", "2")])

            output_dir = tempfile.mkdtemp()
            config = CsvOutputConfig(
                source_table="t",
                output_dir=output_dir,
                filename="out.csv",
                delimiter=";",
                columns=[
                    ColumnMapping(source="a", target="a"),
                    ColumnMapping(source="b", target="b"),
                ],
            )

            ctx = _make_context(db)
            plugin = CsvOutputPlugin()
            plugin.execute(ctx, config)

            csv_path = os.path.join(output_dir, "out.csv")
            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                content = f.read()
                assert "a;b" in content
                assert "1;2" in content
        finally:
            db.close()
            db.remove()

    def test_custom_encoding(self):
        from pipeforge.core.sqlite import SQLiteManager

        db = SQLiteManager()
        try:
            _setup_db(db, "t", ["姓名"], [("张三",)])

            output_dir = tempfile.mkdtemp()
            config = CsvOutputConfig(
                source_table="t",
                output_dir=output_dir,
                filename="out.csv",
                encoding="gbk",
                columns=[ColumnMapping(source="姓名", target="姓名")],
            )

            ctx = _make_context(db)
            plugin = CsvOutputPlugin()
            plugin.execute(ctx, config)

            csv_path = os.path.join(output_dir, "out.csv")
            with open(csv_path, "r", encoding="gbk", newline="") as f:
                reader = csv_module.reader(f)
                rows = list(reader)
                assert rows[0] == ["姓名"]
                assert rows[1] == ["张三"]
        finally:
            db.close()
            db.remove()

    def test_default_filename_from_scene_name(self):
        from pipeforge.core.sqlite import SQLiteManager

        db = SQLiteManager()
        try:
            _setup_db(db, "t", ["x"], [("1",)])

            output_dir = tempfile.mkdtemp()
            config = CsvOutputConfig(
                source_table="t",
                output_dir=output_dir,
                filename="",  # empty → fallback to scene_name.csv
                columns=[ColumnMapping(source="x", target="x")],
            )

            ctx = _make_context(db, scene_name="my_pipeline")
            plugin = CsvOutputPlugin()
            plugin.execute(ctx, config)

            csv_path = os.path.join(output_dir, "my_pipeline.csv")
            assert os.path.exists(csv_path)
        finally:
            db.close()
            db.remove()

    def test_source_column_not_found(self):
        from pipeforge.core.sqlite import SQLiteManager

        db = SQLiteManager()
        try:
            _setup_db(db, "t", ["a", "b"], [("1", "2")])

            output_dir = tempfile.mkdtemp()
            config = CsvOutputConfig(
                source_table="t",
                output_dir=output_dir,
                filename="out.csv",
                columns=[ColumnMapping(source="nonexistent", target="x")],
            )

            ctx = _make_context(db)
            plugin = CsvOutputPlugin()
            with pytest.raises(ValueError, match="nonexistent"):
                plugin.execute(ctx, config)
        finally:
            db.close()
            db.remove()

    def test_output_path_set_on_context(self):
        from pipeforge.core.sqlite import SQLiteManager

        db = SQLiteManager()
        try:
            _setup_db(db, "t", ["a"], [("1",)])

            output_dir = tempfile.mkdtemp()
            config = CsvOutputConfig(
                source_table="t",
                output_dir=output_dir,
                filename="result.csv",
                columns=[ColumnMapping(source="a", target="a")],
            )

            ctx = _make_context(db)
            plugin = CsvOutputPlugin()
            plugin.execute(ctx, config)

            assert ctx.output_path == os.path.join(output_dir, "result.csv")
        finally:
            db.close()
            db.remove()
