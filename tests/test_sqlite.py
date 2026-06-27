import os

import pytest

from pipeforge.core.sqlite import SQLiteManager


class TestSQLiteManager:
    @pytest.fixture
    def db(self):
        manager = SQLiteManager()
        yield manager
        manager.close()
        manager.remove()

    def test_create_table(self, db):
        db.create_table("users", ["id", "name", "age"])
        tables = db.list_tables()
        assert "users" in tables

    def test_insert_and_query(self, db):
        db.create_table("users", ["id", "name"])
        with db.transaction():
            db.insert_row("users", ("1", "Alice"))
            db.insert_row("users", ("2", "Bob"))
        rows = db.query("SELECT * FROM users ORDER BY id")
        assert [tuple(r) for r in rows] == [("1", "Alice"), ("2", "Bob")]

    def test_transaction_rollback(self, db):
        db.create_table("users", ["id", "name"])
        try:
            with db.transaction():
                db.insert_row("users", ("1", "Alice"))
                raise RuntimeError("forced error")
        except RuntimeError:
            pass
        rows = db.query("SELECT * FROM users")
        assert len(rows) == 0

    def test_execute_returning_rows(self, db):
        db.create_table("users", ["id", "name"])
        with db.transaction():
            db.insert_row("users", ("1", "Alice"))
        db.execute("CREATE TABLE copy AS SELECT * FROM users")
        rows = db.query("SELECT * FROM copy")
        assert [tuple(r) for r in rows] == [("1", "Alice")]

    def test_table_exists(self, db):
        db.create_table("users", ["id"])
        assert db.table_exists("users") is True
        assert db.table_exists("nonexistent") is False

    def test_db_file_exists(self, db):
        assert os.path.exists(db.path)

    def test_close_and_remove(self, db):
        path = db.path
        assert os.path.exists(path)
        db.close()
        db.remove()
        assert not os.path.exists(path)
