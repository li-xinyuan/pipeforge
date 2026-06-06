"""Database output plugin — writes pipeline results to a database."""
from pipeforge.plugins.base import OutputPlugin
from pipeforge.config.models import DatabaseOutputConfig
from pipeforge.core.registry import register_plugin
from pipeforge.core.sqlite import SQLiteManager


@register_plugin("database", "output")
class DatabaseOutputPlugin(OutputPlugin[DatabaseOutputConfig]):

    @classmethod
    def config_model(cls) -> type[DatabaseOutputConfig]:
        return DatabaseOutputConfig

    def execute(self, context, config: DatabaseOutputConfig) -> int:
        conn_str = config.connection_string
        if not conn_str:
            raise ValueError("Database output requires connection_string (resolved by pipeline)")

        source_table = config.source_table or context.default_output_table
        if not source_table:
            source_table = context.db.list_tables()[-1] if context.db.list_tables() else ""
        if not source_table:
            raise ValueError("No source table found for database output")

        # Get column names from source
        col_rows = context.db._conn.execute(
            f'PRAGMA table_info("{source_table}")'
        ).fetchall()
        existing_cols = [c[1] for c in col_rows]

        rows = context.db.query(f'SELECT * FROM "{source_table}"')

        # For SQLite targets, extract path from connection_string
        # Format: sqlite:///path/to/db
        if "sqlite" in conn_str.lower():
            db_path = conn_str.replace("sqlite:///", "").strip()
            target_db = SQLiteManager(db_path)
        else:
            # For MySQL/PostgreSQL, use a temp SQLite as fallback for now
            # Full SQLAlchemy integration deferred to future phase
            target_db = SQLiteManager()
            context.logger.info(
                f"Database output to non-SQLite ({conn_str[:20]}...) uses fallback; "
                "full support requires SQLAlchemy"
            )

        try:
            if config.create_table_if_not_exists:
                try:
                    target_db.create_table(config.target_table, existing_cols)
                except Exception:
                    pass  # Table may already exist

            row_count = 0
            for row in rows:
                target_db.insert_row(config.target_table, tuple(row))
                row_count += 1

            context.logger.info(
                f"Database output: wrote {row_count} rows to table "
                f"'{config.target_table}' (mode={config.write_mode})"
            )
            return row_count
        finally:
            if target_db != context.db:
                target_db.close()
