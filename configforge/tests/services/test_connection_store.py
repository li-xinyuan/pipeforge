import os
import tempfile
import pytest
from configforge.services.connection_store import ConnectionStore


@pytest.fixture(autouse=True)
def temp_data_dir(monkeypatch):
    import configforge.services.connection_store as cs
    tmp = tempfile.mkdtemp()
    monkeypatch.setattr(cs, "DATA_DIR", tmp)
    monkeypatch.setattr(cs, "STORE_PATH", os.path.join(tmp, "db_connections.json"))
    yield
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def test_create_mysql_connection():
    conn = ConnectionStore.create({
        "name": "Test MySQL", "db_type": "mysql",
        "host": "localhost", "port": 3306, "database": "testdb",
        "username": "root", "password": "secret123",
    })
    assert conn["name"] == "Test MySQL"
    assert conn["db_type"] == "mysql"
    assert conn["passwordSet"] is True


def test_list_connections():
    ConnectionStore.create({"name": "Conn A", "db_type": "sqlite", "file_path": "/tmp/a.db"})
    ConnectionStore.create({"name": "Conn B", "db_type": "sqlite", "file_path": "/tmp/b.db"})
    all_conns = ConnectionStore.list_all()
    assert len(all_conns) == 2


def test_get_with_password():
    conn = ConnectionStore.create({
        "name": "PG", "db_type": "postgresql",
        "host": "pg.example.com", "port": 5432,
        "database": "prod", "username": "admin", "password": "s3cr3t",
    })
    full = ConnectionStore.get_with_plaintext_password(conn["id"])
    assert full["password"] == "s3cr3t"


def test_password_not_in_summary():
    conn = ConnectionStore.create({
        "name": "Secure", "db_type": "mysql",
        "host": "h", "port": 1, "database": "d",
        "username": "u", "password": "secret",
    })
    assert "password" not in conn
    assert conn["passwordSet"] is True


def test_password_is_encrypted_on_disk():
    import configforge.services.connection_store as cs
    conn = ConnectionStore.create({
        "name": "Secure", "db_type": "mysql",
        "host": "h", "port": 1, "database": "d",
        "username": "u", "password": "secret",
    })
    raw = open(cs.STORE_PATH).read()
    assert "secret" not in raw


def test_delete_connection():
    conn = ConnectionStore.create({"name": "Delete Me", "db_type": "sqlite", "file_path": "/tmp/del.db"})
    assert ConnectionStore.delete(conn["id"]) is True
    assert ConnectionStore.get(conn["id"]) is None


def test_update_connection():
    conn = ConnectionStore.create({
        "name": "Old", "db_type": "mysql",
        "host": "old", "port": 3306, "database": "old",
        "username": "u", "password": "oldpass",
    })
    updated = ConnectionStore.update(conn["id"], {"name": "New", "password": "newpass"})
    assert updated["name"] == "New"
    full = ConnectionStore.get_with_plaintext_password(conn["id"])
    assert full["password"] == "newpass"


def test_build_connection_string_sqlite():
    cs = ConnectionStore.build_connection_string({
        "db_type": "sqlite", "file_path": "/data/report.db",
    })
    assert cs == "sqlite:////data/report.db"


def test_build_connection_string_mysql():
    cs = ConnectionStore.build_connection_string({
        "db_type": "mysql", "username": "user", "password": "pass",
        "host": "10.0.0.1", "port": 3306, "database": "mydb",
    })
    assert cs == "mysql+pymysql://user:pass@10.0.0.1:3306/mydb"


def test_create_sqlite_connection():
    conn = ConnectionStore.create({
        "name": "Local SQLite", "db_type": "sqlite",
        "file_path": "/data/local.db",
    })
    assert conn["db_type"] == "sqlite"
    assert conn["host"] == "/data/local.db"
    assert conn["passwordSet"] is False
