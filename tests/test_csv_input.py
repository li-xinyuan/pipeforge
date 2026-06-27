import os
import csv as csv_module
import tempfile

import pytest

from pipeforge.plugins.input.csv import CsvInputPlugin
from pipeforge.config.models import CsvInputConfig


class TestCsvInputPlugin:
    def test_config_model(self):
        assert CsvInputPlugin.config_model() == CsvInputConfig

    def test_read_csv_with_header(self):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        writer = csv_module.writer(tmp)
        writer.writerow(["name", "age"])
        writer.writerow(["Alice", "30"])
        writer.writerow(["Bob", "25"])
        tmp.close()

        try:
            plugin = CsvInputPlugin()
            config = CsvInputConfig(file=tmp.name)
            columns, rows = plugin._read_csv(tmp.name, config)
            assert columns == ["name", "age"]
            assert list(rows) == [("Alice", "30"), ("Bob", "25")]
        finally:
            os.unlink(tmp.name)

    def test_read_csv_no_header(self):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        writer = csv_module.writer(tmp)
        writer.writerow(["Alice", "30"])
        writer.writerow(["Bob", "25"])
        tmp.close()

        try:
            plugin = CsvInputPlugin()
            config = CsvInputConfig(file=tmp.name, has_header=False)
            columns, rows = plugin._read_csv(tmp.name, config)
            assert columns == ["col_0", "col_1"]
            assert list(rows) == [("Alice", "30"), ("Bob", "25")]
        finally:
            os.unlink(tmp.name)

    def test_read_csv_custom_delimiter(self):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        writer = csv_module.writer(tmp, delimiter=";")
        writer.writerow(["name", "age"])
        writer.writerow(["Alice", "30"])
        tmp.close()

        try:
            plugin = CsvInputPlugin()
            config = CsvInputConfig(file=tmp.name, delimiter=";")
            columns, rows = plugin._read_csv(tmp.name, config)
            assert columns == ["name", "age"]
        finally:
            os.unlink(tmp.name)

    def test_read_empty_csv(self):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        tmp.close()

        try:
            plugin = CsvInputPlugin()
            config = CsvInputConfig(file=tmp.name)
            columns, rows = plugin._read_csv(tmp.name, config)
            assert columns == []
            assert rows == []
        finally:
            os.unlink(tmp.name)

    def test_registered_as_csv_input(self):
        """Verify the plugin is registered under 'csv' input type."""
        from pipeforge.core.registry import PluginRegistry
        cls = PluginRegistry.get("csv", "input")
        assert cls.config_model() is CsvInputConfig
