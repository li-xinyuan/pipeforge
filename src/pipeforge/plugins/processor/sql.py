from pipeforge.config.models import SqlProcessorConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import ProcessorPlugin


@register_plugin("sql", "processor")
class SqlProcessorPlugin(ProcessorPlugin):
    """在 SQLite 中执行 SQL 语句。"""

    @classmethod
    def config_model(cls) -> type[SqlProcessorConfig]:
        return SqlProcessorConfig

    def execute(self, context, config: SqlProcessorConfig) -> None:
        context.db.execute(config.sql)
        context.logger.info(f"Processor '{self.label}': SQL executed successfully")
