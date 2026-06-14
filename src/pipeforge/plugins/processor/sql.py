import re

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from pipeforge.config.models import SqlProcessorConfig
from pipeforge.core.registry import register_plugin
from pipeforge.plugins.base import ProcessorPlugin

# Only allow SELECT statements (including CTE) for real database connections
_SELECT_ONLY_RE = re.compile(
    r'^\s*(WITH\s+.*?\s+)?SELECT\s',
    re.IGNORECASE | re.DOTALL,
)


def _is_read_only_sql(sql: str) -> bool:
    """Check if SQL is a read-only SELECT statement."""
    stripped = sql.strip().rstrip(';').strip()
    return bool(_SELECT_ONLY_RE.match(stripped))


@register_plugin("sql", "processor")
class SqlProcessorPlugin(ProcessorPlugin):
    """在 SQLite 中执行 SQL 语句，支持 Jinja2 模板变量。"""

    @classmethod
    def config_model(cls) -> type[SqlProcessorConfig]:
        return SqlProcessorConfig

    def execute(self, context, config: SqlProcessorConfig) -> None:
        rendered_sql = SandboxedEnvironment(undefined=StrictUndefined).from_string(config.sql).render(
            **context.params
        )

        # For real database connections (non-temp SQLite), enforce read-only by default
        if not context.db_is_temp and not _is_read_only_sql(rendered_sql):
            raise ValueError(
                "出于安全考虑，连接真实数据库时仅允许 SELECT 查询。"
                "如需写入，请使用 CSV/Excel 输出方式。"
            )

        context.db.execute(rendered_sql)
        context.logger.info(f"Processor '{self.label}': SQL executed successfully")
