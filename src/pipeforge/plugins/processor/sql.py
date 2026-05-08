from jinja2 import StrictUndefined, Template

from pipeforge.config.models import SqlProcessorConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import ProcessorPlugin


@register_plugin("sql", "processor")
class SqlProcessorPlugin(ProcessorPlugin):
    """在 SQLite 中执行 SQL 语句，支持 Jinja2 模板变量。"""

    @classmethod
    def config_model(cls) -> type[SqlProcessorConfig]:
        return SqlProcessorConfig

    def execute(self, context, config: SqlProcessorConfig) -> None:
        rendered_sql = Template(config.sql, undefined=StrictUndefined).render(
            **context.params
        )
        context.db.execute(rendered_sql)
        context.logger.info(f"Processor '{self.label}': SQL executed successfully")
