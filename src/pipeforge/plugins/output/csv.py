import csv
import os

from pipeforge.plugins.base import OutputPlugin
from pipeforge.config.models import CsvOutputConfig
from pipeforge.core.registry import register_plugin


@register_plugin("csv", "output")
class CsvOutputPlugin(OutputPlugin[CsvOutputConfig]):
    """CSV file output plugin."""

    @classmethod
    def config_model(cls) -> type[CsvOutputConfig]:
        return CsvOutputConfig

    def execute(self, context, config: CsvOutputConfig) -> None:
        source_columns = context.db.get_column_names(config.source_table)

        source_to_idx = {col: i for i, col in enumerate(source_columns)}
        for cm in config.columns:
            if cm.source not in source_to_idx:
                raise ValueError(
                    f"Source column '{cm.source}' not found in table "
                    f"'{config.source_table}'. Available: {source_columns}"
                )

        target_columns = [cm.target for cm in config.columns]

        filename = config.filename or f"{context.scene_name}.csv"
        output_path = os.path.join(config.output_dir, filename)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, "w", encoding=config.encoding, newline="") as f:
            writer = csv.writer(f, delimiter=config.delimiter)
            writer.writerow(target_columns)

            rows = context.db.query(f'SELECT * FROM "{config.source_table}"')
            for row in rows:
                mapped = [str(row[source_to_idx[cm.source]]) if row[source_to_idx[cm.source]] is not None else "" for cm in config.columns]
                writer.writerow(mapped)

        context.output_path = output_path
        context.logger.info(f"Written CSV: {output_path}")
