import csv
import os

from pipeforge.config.models import CsvInputConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import InputPlugin


@register_plugin("csv", "input")
class CsvInputPlugin(InputPlugin[CsvInputConfig]):
    """CSV file input plugin."""

    @classmethod
    def config_model(cls) -> type[CsvInputConfig]:
        return CsvInputConfig

    def execute(self, context, config: CsvInputConfig) -> None:
        filepath = os.path.join(context.yaml_dir, config.file)

        columns, rows = self._read_csv(filepath, config)

        if not columns:
            raise ValueError(f"CSV file is empty: {config.file}")

        context.db.create_table(self.table_name, columns)

        with context.db.transaction():
            for row in rows:
                context.db.insert_row(self.table_name, tuple(str(v) for v in row))

        context.logger.info(
            f"Loaded CSV: {config.file} -> table '{self.table_name}' "
            f"({len(columns)} columns)"
        )

    def _read_csv(
        self, filepath: str, config: CsvInputConfig
    ) -> tuple[list[str], list[tuple]]:
        """Read a CSV file and return (columns, rows)."""
        with open(filepath, encoding=config.encoding, newline="") as f:
            reader = csv.reader(f, delimiter=config.delimiter)

            first_row = next(reader, None)
            if first_row is None:
                return [], []

            if config.has_header:
                columns = [str(c).strip() for c in first_row]
            else:
                columns = [f"col_{i}" for i in range(len(first_row))]
                # First row is data, not a header
                rows = [tuple(str(v) for v in first_row)]
                rows += [tuple(str(v) for v in row) for row in reader]
                return columns, rows

            rows = [tuple(str(v) for v in row) for row in reader]
            return columns, rows
