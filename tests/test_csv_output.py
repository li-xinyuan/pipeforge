import os
import csv as csv_module
import tempfile

from pipeforge.plugins.output.csv import CsvOutputPlugin
from pipeforge.config.models import CsvOutputConfig, ColumnMapping


class TestCsvOutputPlugin:
    def test_config_model(self):
        assert CsvOutputPlugin.config_model() == CsvOutputConfig

    def test_registered_as_csv_output(self):
        """Verify the plugin is registered under 'csv' output type."""
        from pipeforge.core.registry import PluginRegistry
        cls = PluginRegistry.get("csv", "output")
        assert cls is CsvOutputPlugin
