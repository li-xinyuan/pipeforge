import os
import sqlite3
import tempfile
from contextlib import contextmanager


class SQLiteManager:
    """Manage creation, writing, querying, and cleanup of a temporary SQLite database."""

    def __init__(self):
        fd, self.path = tempfile.mkstemp(suffix=".db", prefix="pipeforge_")
        os.close(fd)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA journal_mode=WAL")

    def create_table(self, table_name: str, columns: list[str]) -> None:
        cols_def = ", ".join(f'"{c}" TEXT' for c in columns)
        self._conn.execute(f'CREATE TABLE "{table_name}" ({cols_def})')
        self._conn.commit()

    def insert_row(self, table_name: str, row: tuple) -> None:
        placeholders = ", ".join("?" for _ in row)
        self._conn.execute(
            f'INSERT INTO "{table_name}" VALUES ({placeholders})', row
        )

    def query(self, sql: str) -> list[tuple]:
        return self._conn.execute(sql).fetchall()

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

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def remove(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)
