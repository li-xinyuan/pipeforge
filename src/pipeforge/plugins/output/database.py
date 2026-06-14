"""Database output plugin — writes pipeline results to a database.

Supports SQLite, MySQL, and PostgreSQL via SQLAlchemy.
Write modes:
  - append: INSERT rows
  - replace: DROP + CREATE + INSERT
  - upsert: INSERT ON CONFLICT UPDATE (dialect-specific)
"""
from pipeforge.plugins.base import OutputPlugin
from pipeforge.config.models import DatabaseOutputConfig
from pipeforge.core.registry import register_plugin
from pipeforge.core.sqlite import safe_identifier

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.pool import NullPool


def _detect_dialect(conn_str: str) -> str:
    """Return a normalised dialect name from a SQLAlchemy connection string."""
    lower = conn_str.lower()
    if lower.startswith("sqlite"):
        return "sqlite"
    if lower.startswith("mysql"):
        return "mysql"
    if lower.startswith("postgresql") or lower.startswith("postgres"):
        return "postgresql"
    raise ValueError(f"Unsupported database dialect in connection string: {conn_str[:30]}...")


def _quote(identifier: str, dialect: str = "sqlite") -> str:
    """Quote a SQL identifier using the appropriate quoting for the dialect.

    SQLite / PostgreSQL: double quotes (")
    MySQL: backticks (`)
    """
    safe_identifier(identifier, "identifier")
    if dialect == "mysql":
        return f"`{identifier}`"
    return f'"{identifier}"'


def _build_create_table_sql(table_name: str, columns: list[str], dialect: str, pk_columns: list[str] | None = None) -> str:
    """Build a CREATE TABLE statement with all TEXT columns.

    If *pk_columns* is provided, a PRIMARY KEY constraint is added.
    """
    col_defs = [f"{_quote(c, dialect)} TEXT" for c in columns]
    if pk_columns:
        pk = ", ".join(_quote(c, dialect) for c in pk_columns)
        col_defs.append(f"PRIMARY KEY ({pk})")
    return f"CREATE TABLE {_quote(table_name, dialect)} ({', '.join(col_defs)})"


def _build_insert_sql(table_name: str, columns: list[str], dialect: str = "sqlite") -> str:
    """Build a parameterised INSERT statement."""
    quoted_cols = ", ".join(_quote(c, dialect) for c in columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    return f"INSERT INTO {_quote(table_name, dialect)} ({quoted_cols}) VALUES ({placeholders})"


def _build_upsert_sql(
    table_name: str,
    columns: list[str],
    pk_columns: list[str],
    dialect: str,
) -> str:
    """Build a dialect-specific upsert (INSERT … ON CONFLICT) statement."""
    quoted_cols = ", ".join(_quote(c, dialect) for c in columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    insert = f"INSERT INTO {_quote(table_name, dialect)} ({quoted_cols}) VALUES ({placeholders})"

    non_pk = [c for c in columns if c not in pk_columns]

    if dialect == "sqlite":
        return f"INSERT OR REPLACE INTO {_quote(table_name, dialect)} ({quoted_cols}) VALUES ({placeholders})"

    if dialect == "mysql":
        if non_pk:
            update_clause = ", ".join(f"{_quote(c, dialect)} = new.{_quote(c, dialect)}" for c in non_pk)
            return f"{insert} AS new ON DUPLICATE KEY UPDATE {update_clause}"
        return insert  # all columns are PK — INSERT OR REPLACE equivalent

    if dialect == "postgresql":
        if non_pk:
            conflict_cols = ", ".join(_quote(c, dialect) for c in pk_columns)
            update_clause = ", ".join(f"{_quote(c, dialect)} = EXCLUDED.{_quote(c, dialect)}" for c in non_pk)
            return f"{insert} ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}"
        conflict_cols = ", ".join(_quote(c, dialect) for c in pk_columns)
        return f"{insert} ON CONFLICT ({conflict_cols}) DO NOTHING"

    raise ValueError(f"Upsert not supported for dialect: {dialect}")


@register_plugin("database", "output")
class DatabaseOutputPlugin(OutputPlugin[DatabaseOutputConfig]):

    @classmethod
    def config_model(cls) -> type[DatabaseOutputConfig]:
        return DatabaseOutputConfig

    def execute(self, context, config: DatabaseOutputConfig) -> int:
        conn_str = config.connection_string
        if not conn_str:
            raise ValueError("Database output requires connection_string (resolved by pipeline)")

        dialect = _detect_dialect(conn_str)

        # Determine source table
        source_table = config.source_table or getattr(context, "default_output_table", "")
        if not source_table:
            source_table = context.db.list_tables()[-1] if context.db.list_tables() else ""
        if not source_table:
            raise ValueError("No source table found for database output")
        # Validate source_table against SQL injection
        safe_identifier(source_table, "source_table")

        # Read column info and data from the intermediate SQLite DB
        # Use safe_identifier-validated name with proper quoting
        quoted_source = _quote(source_table, "sqlite")
        col_rows = context.db._conn.execute(
            f'PRAGMA table_info({quoted_source})'
        ).fetchall()
        columns = [c[1] for c in col_rows]

        rows = context.db.query(f'SELECT * FROM {quoted_source}')

        # Build SQLAlchemy engine
        pool_kwargs = {"poolclass": NullPool} if dialect == "sqlite" else {"pool_size": 5}
        engine_kwargs = dict(pool_kwargs)
        if dialect != "sqlite":
            engine_kwargs["connect_args"] = {"connect_timeout": 30}

        engine = create_engine(conn_str, **engine_kwargs)

        try:
            with engine.connect() as conn:
                target = config.target_table

                # --- Handle write modes ---
                pk = config.primary_key_columns if config.primary_key_columns else columns[:1]
                if config.write_mode == "replace":
                    # DROP if exists, then CREATE
                    conn.execute(text(f"DROP TABLE IF EXISTS {_quote(target, dialect)}"))
                    conn.execute(text(_build_create_table_sql(target, columns, dialect, pk_columns=pk)))
                    self._batch_insert(conn, target, columns, rows, config.batch_size, dialect)
                elif config.write_mode == "append":
                    if config.create_table_if_not_exists:
                        self._ensure_table(conn, target, columns, dialect)
                    self._batch_insert(conn, target, columns, rows, config.batch_size, dialect)
                elif config.write_mode == "upsert":
                    if config.create_table_if_not_exists:
                        self._ensure_table(conn, target, columns, dialect, pk_columns=pk)
                    self._batch_upsert(conn, target, columns, rows, pk, dialect, config.batch_size)
                else:
                    raise ValueError(f"Unsupported write_mode: {config.write_mode}")

            row_count = len(rows)
            context.logger.info(
                f"Database output: wrote {row_count} rows to table "
                f"'{target}' (mode={config.write_mode}, dialect={dialect})"
            )
            return row_count
        finally:
            engine.dispose()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_table(conn, table_name: str, columns: list[str], dialect: str, pk_columns: list[str] | None = None) -> None:
        """Create the target table if it does not already exist."""
        inspector = inspect(conn)
        if table_name not in inspector.get_table_names():
            conn.execute(text(_build_create_table_sql(table_name, columns, dialect, pk_columns=pk_columns)))
            conn.commit()

    @staticmethod
    def _batch_insert(conn, table_name: str, columns: list[str], rows: list[tuple], batch_size: int, dialect: str = "sqlite") -> None:
        """Insert rows in batches using parameterised statements."""
        insert_sql = text(_build_insert_sql(table_name, columns, dialect))
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            params = [dict(zip(columns, row)) for row in batch]
            conn.execute(insert_sql, params)
            conn.commit()

    @staticmethod
    def _batch_upsert(
        conn,
        table_name: str,
        columns: list[str],
        rows: list[tuple],
        pk_columns: list[str],
        dialect: str,
        batch_size: int,
    ) -> None:
        """Upsert rows in batches using dialect-specific ON CONFLICT syntax."""
        upsert_sql = text(_build_upsert_sql(table_name, columns, pk_columns, dialect))
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            params = [dict(zip(columns, row)) for row in batch]
            conn.execute(upsert_sql, params)
            conn.commit()
