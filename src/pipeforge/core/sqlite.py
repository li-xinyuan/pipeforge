import os
import re
import sqlite3
import tempfile
from contextlib import contextmanager


# SQL identifier whitelist: only letters, digits, underscores
_SQL_ID_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")


def safe_identifier(name: str, param_name: str = "identifier") -> str:
    """Validate a SQL table/column identifier against injection."""
    if not name:
        raise ValueError(f"{param_name} must not be empty")
    if not _SQL_ID_RE.fullmatch(name):
        raise ValueError(
            f"{param_name} '{name}' is not a valid SQL identifier "
            "(must start with letter/underscore, contain only letters/digits/underscores, max 64 chars)"
        )
    return name


class SQLiteManager:
    """Manage creation, writing, querying, and cleanup of a temporary SQLite database."""

    def __init__(self, db_path: str | None = None):
        if db_path:
            self.path = db_path
        else:
            fd, self.path = tempfile.mkstemp(suffix=".db", prefix="pipeforge_")
            os.close(fd)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")

    def create_table(self, table_name: str, columns: list[str]) -> None:
        safe_name = safe_identifier(table_name, "table_name")
        safe_cols = ", ".join(
            f'"{safe_identifier(c, "column_name")}" TEXT' for c in columns
        )
        self._conn.execute(f'CREATE TABLE "{safe_name}" ({safe_cols})')
        self._conn.commit()

    def insert_row(self, table_name: str, row: tuple) -> None:
        safe_name = safe_identifier(table_name, "table_name")
        placeholders = ", ".join("?" for _ in row)
        self._conn.execute(
            f'INSERT INTO "{safe_name}" VALUES ({placeholders})', row
        )

    def query(self, sql: str, params: tuple | None = None) -> list[tuple]:
        """Execute a SELECT query. User-supplied values should use parameterized placeholders (?)."""
        if params is not None:
            return self._conn.execute(sql, params).fetchall()
        return self._conn.execute(sql).fetchall()

    @property
    def connection(self):
        """Expose the underlying SQLite connection for use by Python processors."""
        return self._conn

    def execute(self, sql: str) -> None:
        self._conn.executescript(sql)
        self._conn.commit()

    @contextmanager
    def transaction(self):
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def list_tables(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]

    def table_exists(self, table_name: str) -> bool:
        return table_name in self.list_tables()

    def get_column_names(self, table_name: str) -> list[str]:
        safe_name = safe_identifier(table_name, "table_name")
        rows = self._conn.execute(
            f'PRAGMA table_info("{safe_name}")'
        ).fetchall()
        return [r[1] for r in rows]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def remove(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)
        for suffix in ("-wal", "-shm"):
            p = self.path + suffix
            if os.path.exists(p):
                os.remove(p)
