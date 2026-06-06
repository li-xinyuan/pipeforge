from sqlalchemy import create_engine, table, column, text, select
from sqlalchemy.pool import NullPool
from pipeforge.plugins.base import InputPlugin
from pipeforge.config.models import DbInputConfig
from pipeforge.core.registry import register_plugin


@register_plugin("database", "input")
class DatabaseInputPlugin(InputPlugin[DbInputConfig]):
    """Read data from external database (SQLite/MySQL/PostgreSQL) via SQLAlchemy."""

    @classmethod
    def config_model(cls) -> type[DbInputConfig]:
        return DbInputConfig

    def execute(self, context, config: DbInputConfig) -> None:
        pool_kwargs = {"poolclass": NullPool} if config.db_type == "sqlite" else {"pool_size": 5}

        engine = None
        try:
            engine = create_engine(config.connection_string, **pool_kwargs)
            with engine.connect() as conn:
                if config.sql.strip():
                    result = conn.execute(text(config.sql))
                elif config.tables:
                    table_name = config.tables[0]
                    # Use SQLAlchemy table() to safely reference the table
                    result = conn.execute(select(column("*")).select_from(table(table_name)))
                else:
                    raise ValueError("tables 和 sql 必须提供一个")

                columns = list(result.keys())
                rows = [tuple(row) for row in result.fetchall()]
        finally:
            if engine is not None:
                engine.dispose()

        if not columns:
            context.logger.warning(f"Database input '{self.label}': query returned 0 columns")
            return

        context.db.create_table(self.table_name, columns)
        with context.db.transaction():
            for row in rows:
                context.db.insert_row(self.table_name, tuple(str(v) if v is not None else "" for v in row))

        context.logger.info(
            f"Input '{self.label}': loaded {len(rows)} rows from {config.db_type} "
            f"into table '{self.table_name}' ({len(columns)} columns)"
        )
