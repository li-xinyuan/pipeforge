# v0.2.1 — 数据库输入源 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持从外部数据库（SQLite/MySQL/PostgreSQL）加载数据作为管道输入源，通过连接注册中心管理连接，密码服务端加密。

**Architecture:** 两层改动 — PipeForge（运行时引擎）新增 DatabaseInputPlugin；ConfigForge（向导层）新增连接管理 API + DatabaseInputConfig 模型 + YAML 构建分支；前端新增 DatabaseForm 组件 + 连接管理界面 + 类型扩展。

**Tech Stack:** Python 3.13 + Pydantic v2 + SQLAlchemy + FastAPI / Vue 3 + TypeScript + Naive UI + Pinia

**Spec:** `docs/superpowers/specs/2026-05-19-database-input-source-design.md`

**File Map:**

| File | Action | Responsibility |
|------|--------|---------------|
| `src/pipeforge/config/models.py` | Modify | Add `DbInputConfig`, extend `InputSpec.config` union |
| `src/pipeforge/plugins/input/database.py` | Create | `DatabaseInputPlugin` — connect to DB, SELECT, write to SQLite |
| `configforge/models/wizard.py` | Modify | Add `DatabaseInputConfig`, extend `InputSource` |
| `configforge/generators/input/database_generator.py` | Create | `DatabaseInputGenerator` for ConfigForge wizard |
| `configforge/services/connection_store.py` | Create | Connection CRUD + Fernet encryption + persistence |
| `configforge/api/connections.py` | Create | REST endpoints for connection management |
| `configforge/services/yaml_builder.py` | Modify | Add `database` branch for input YAML serialization |
| `configforge/core/pipeline.py` | Modify | Resolve `connectionId` → `connection_string` before YAML build |
| `configforge/server.py` | Modify | Mount connections router |
| `configforge-web/src/types/wizard.ts` | Modify | Add `DatabaseInputConfig`, extend `InputSource` |
| `configforge-web/src/stores/wizard.ts` | Modify | Extend `addInput`, `loadFromConfigState` |
| `configforge-web/src/composables/useWizardApi.ts` | Modify | Add connection API functions |
| `configforge-web/src/stores/dbConnections.ts` | Create | Frontend connection store (Pinia) |
| `configforge-web/src/components/step2/InputSourceList.vue` | Modify | Activate Database card |
| `configforge-web/src/components/step2/DatabaseForm.vue` | Create | Database input form (connection select, table/SQL) |
| `configforge-web/src/components/step2/InputSourceCard.vue` | Modify | Route to DatabaseForm when plugin='database' |
| `configforge-web/src/components/common/ConnectionManager.vue` | Create | Connection CRUD UI in Settings page |
| `configforge-web/src/views/SettingsPage.vue` | Modify | Embed ConnectionManager |

---

### Task 1: PipeForge — 新增 DbInputConfig 模型

**Files:**
- Modify: `src/pipeforge/config/models.py`

- [ ] **Step 1: Add DatabaseInputConfig and extend InputSpec**

In `src/pipeforge/config/models.py`, after the `CsvInputConfig` class (line 29), add:

```python
class DbInputConfig(BaseModel):
    """Database input configuration — connection_string is resolved by API layer before engine receives it."""
    model_config = ConfigDict(extra="forbid")
    type: Literal["database"] = "database"
    db_type: str                       # "sqlite" | "mysql" | "postgresql"
    connection_string: str             # SQLAlchemy connection string, resolved from connectionId by API
    tables: list[str] = []             # max 1 element; multi-table uses separate InputSources or SQL JOIN
    sql: str = ""                      # custom SQL query (mutually exclusive with tables)
```

Then modify `InputSpec.config` (line 38) from:
```python
config: Annotated[ExcelInputConfig | CsvInputConfig, Field(discriminator="type")]
```
to:
```python
config: Annotated[ExcelInputConfig | CsvInputConfig | DbInputConfig, Field(discriminator="type")]
```

- [ ] **Step 2: Run existing PipeForge tests to verify no regression**

```bash
cd /Users/lixinyuan/code/CCTEST && uv run pytest src/pipeforge/tests/ -v
```
Expected: All existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/pipeforge/config/models.py
git commit -m "feat(pipeforge): add DbInputConfig model for database input source"
```

---

### Task 2: PipeForge — 创建 DatabaseInputPlugin

**Files:**
- Create: `src/pipeforge/plugins/input/database.py`

- [ ] **Step 1: Write the plugin**

Create `src/pipeforge/plugins/input/database.py`:

```python
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from ..base import InputPlugin
from ...config.models import DbInputConfig
from ...core.registry import register_plugin


@register_plugin("database", "input")
class DatabaseInputPlugin(InputPlugin[DbInputConfig]):
    """Read data from external database (SQLite/MySQL/PostgreSQL) via SQLAlchemy."""

    @classmethod
    def config_model(cls):
        return DbInputConfig

    def execute(self, context, config: DbInputConfig) -> None:
        pool_kwargs = {"poolclass": NullPool} if config.db_type == "sqlite" else {"pool_size": 5}
        engine = create_engine(config.connection_string, **pool_kwargs)

        try:
            with engine.connect() as conn:
                if config.sql.strip():
                    result = conn.execute(text(config.sql))
                elif config.tables:
                    table_name = config.tables[0]
                    result = conn.execute(text(f"SELECT * FROM {table_name}"))
                else:
                    raise ValueError("tables 和 sql 必须提供一个")

                columns = list(result.keys())
                rows = [tuple(row) for row in result.fetchall()]
        finally:
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
```

- [ ] **Step 2: Verify the plugin registers correctly**

```bash
cd /Users/lixinyuan/code/CCTEST && uv run python -c "
from pipeforge.core.registry import PluginRegistry
import src.pipeforge.plugins.input.database as _
cls = PluginRegistry.get('database', 'input')
print(f'Plugin registered: {cls.__name__}')
"
```
Expected: `Plugin registered: DatabaseInputPlugin`

- [ ] **Step 3: Commit**

```bash
git add src/pipeforge/plugins/input/database.py
git commit -m "feat(pipeforge): add DatabaseInputPlugin with SQLAlchemy support"
```

---

### Task 3: ConfigForge — 新增 DatabaseInputConfig 模型

**Files:**
- Modify: `configforge/models/wizard.py`

- [ ] **Step 1: Add DatabaseInputConfig and extend InputSource**

In `configforge/models/wizard.py`, after `CsvInputConfig` (line 20), add:

```python
class DatabaseInputConfig(BaseModel):
    type: Literal["database"] = "database"
    connection_id: str = ""
    connection_string: str = ""   # API 层解析 connectionId 后填充
    db_type: str = ""             # API 层填充
    query_type: Literal["table", "sql"] = "table"
    tables: list[str] = []        # max 1 element
    sql: str = ""
```

Modify `InputSource` (line 23-31):
- `plugin: Literal["excel", "csv"]` → `plugin: Literal["excel", "csv", "database"]`
- `config: Annotated[ExcelInputConfig | CsvInputConfig, ...]` → `config: Annotated[ExcelInputConfig | CsvInputConfig | DatabaseInputConfig, ...]`

- [ ] **Step 2: Run ConfigForge tests to verify no regression**

```bash
cd /Users/lixinyuan/code/CCTEST && uv run pytest configforge/tests/ -v
```
Expected: All existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add configforge/models/wizard.py
git commit -m "feat(configforge): add DatabaseInputConfig model for wizard layer"
```

---

### Task 4: ConfigForge — 创建 DatabaseInputGenerator

**Files:**
- Create: `configforge/generators/input/database_generator.py`

- [ ] **Step 1: Write the generator**

Create `configforge/generators/input/database_generator.py`:

```python
from typing import Literal
from ..base import ConfigGenerator
from ...models.wizard import DatabaseInputConfig
from ...core.registry import GeneratorRegistry


@GeneratorRegistry.register("database", "input")
class DatabaseInputGenerator(ConfigGenerator[DatabaseInputConfig]):
    """Database input generator for ConfigForge wizard."""

    @classmethod
    def config_model(cls):
        return DatabaseInputConfig

    def infer_config(self, source: dict) -> DatabaseInputConfig:
        return DatabaseInputConfig(
            query_type=source.get("query_type", "table"),
            tables=source.get("tables", []),
            sql=source.get("sql", ""),
        )

    def build_config(self, wizard_state: dict) -> DatabaseInputConfig:
        return DatabaseInputConfig(
            connection_id=wizard_state.get("connection_id", ""),
            db_type=wizard_state.get("db_type", ""),
            query_type=wizard_state.get("query_type", "table"),
            tables=wizard_state.get("tables", []),
            sql=wizard_state.get("sql", ""),
        )

    def validate_config(self, config: DatabaseInputConfig) -> list[str]:
        errors = []
        if not config.connection_id:
            errors.append("Connection is required")
        has_tables = len(config.tables) > 0
        has_sql = bool(config.sql.strip())
        if has_tables and has_sql:
            errors.append("tables and sql are mutually exclusive")
        if not has_tables and not has_sql:
            errors.append("Either tables or sql must be provided")
        return errors
```

- [ ] **Step 2: Verify generator registration**

```bash
cd /Users/lixinyuan/code/CCTEST && uv run python -c "
from configforge.core.registry import GeneratorRegistry
import configforge.generators.input.database_generator as _
cls = GeneratorRegistry.get('database', 'input')
print(f'Generator registered: {cls.__name__}')
"
```
Expected: `Generator registered: DatabaseInputGenerator`

- [ ] **Step 3: Commit**

```bash
git add configforge/generators/input/database_generator.py
git commit -m "feat(configforge): add DatabaseInputGenerator for wizard layer"
```

---

### Task 5: ConfigForge — 创建 ConnectionStore 服务

**Files:**
- Create: `configforge/services/connection_store.py`

- [ ] **Step 1: Write the ConnectionStore**

Create `configforge/services/connection_store.py`:

```python
import json
import os
import fcntl
import uuid
from datetime import datetime, timezone
from configforge.services.ai.settings import _get_cipher

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
STORE_PATH = os.path.join(DATA_DIR, "db_connections.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load() -> dict:
    _ensure_data_dir()
    if not os.path.exists(STORE_PATH):
        return {"connections": {}}
    with open(STORE_PATH, "r", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _save(data: dict):
    _ensure_data_dir()
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(data, f, indent=2, ensure_ascii=False)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConnectionStore:
    """Repository for database connections with Fernet-encrypted passwords."""

    @staticmethod
    def create(data: dict) -> dict:
        cipher = _get_cipher()
        conn_id = uuid.uuid4().hex[:16]
        password = data.get("password", "")
        encrypted = cipher.encrypt(password.encode()).decode() if password else ""

        store = _load()
        entry = {
            "id": conn_id,
            "name": data["name"],
            "db_type": data["db_type"],
        }
        if data["db_type"] == "sqlite":
            entry["file_path"] = data["file_path"]
        else:
            entry["host"] = data["host"]
            entry["port"] = int(data.get("port", 3306))
            entry["database"] = data["database"]
            entry["username"] = data["username"]
            entry["password"] = encrypted

        entry["created_at"] = _now_iso()
        entry["updated_at"] = _now_iso()
        store["connections"][conn_id] = entry
        _save(store)

        return ConnectionStore._summarize(conn_id, entry)

    @staticmethod
    def list_all() -> list[dict]:
        store = _load()
        return [ConnectionStore._summarize(cid, c) for cid, c in store["connections"].items()]

    @staticmethod
    def get(conn_id: str) -> dict | None:
        store = _load()
        entry = store["connections"].get(conn_id)
        if not entry:
            return None
        return ConnectionStore._summarize(conn_id, entry)

    @staticmethod
    def get_with_plaintext_password(conn_id: str) -> dict | None:
        """Internal use — returns full entry with decrypted password."""
        store = _load()
        entry = store["connections"].get(conn_id)
        if not entry:
            return None
        cipher = _get_cipher()
        entry = dict(entry)
        if entry.get("password"):
            entry["password"] = cipher.decrypt(entry["password"].encode()).decode()
        entry["id"] = conn_id
        return entry

    @staticmethod
    def update(conn_id: str, data: dict) -> dict | None:
        store = _load()
        entry = store["connections"].get(conn_id)
        if not entry:
            return None
        cipher = _get_cipher()

        for field in ("name", "host", "port", "database", "username", "file_path"):
            if field in data:
                entry[field] = data[field]
        if "password" in data and data["password"]:
            entry["password"] = cipher.encrypt(data["password"].encode()).decode()
        entry["updated_at"] = _now_iso()
        store["connections"][conn_id] = entry
        _save(store)
        return ConnectionStore._summarize(conn_id, entry)

    @staticmethod
    def delete(conn_id: str) -> bool:
        store = _load()
        if conn_id not in store["connections"]:
            return False
        del store["connections"][conn_id]
        _save(store)
        return True

    @staticmethod
    def build_connection_string(entry: dict) -> str:
        """Build SQLAlchemy connection string from a connection entry (with plaintext password)."""
        db_type = entry["db_type"]
        if db_type == "sqlite":
            return f"sqlite:///{entry['file_path']}"
        elif db_type == "mysql":
            return (
                f"mysql+pymysql://{entry['username']}:{entry['password']}"
                f"@{entry['host']}:{entry['port']}/{entry['database']}"
            )
        elif db_type == "postgresql":
            return (
                f"postgresql+psycopg2://{entry['username']}:{entry['password']}"
                f"@{entry['host']}:{entry['port']}/{entry['database']}"
            )
        raise ValueError(f"Unsupported db_type: {db_type}")

    @staticmethod
    def count_references(conn_id: str) -> list[str]:
        """Check how many saved configs reference this connection. Returns list of config IDs."""
        # Stub — will be implemented when config search is available
        return []

    @staticmethod
    def _summarize(conn_id: str, entry: dict) -> dict:
        host = entry.get("file_path", entry.get("host", ""))
        result = {
            "id": conn_id,
            "name": entry["name"],
            "db_type": entry["db_type"],
            "host": host,
            "passwordSet": bool(entry.get("password", "")),
            "verified": entry.get("verified", False),
            "createdAt": entry.get("created_at", ""),
            "updatedAt": entry.get("updated_at", ""),
        }
        if entry["db_type"] != "sqlite":
            result["port"] = entry.get("port")
            result["database"] = entry.get("database")
            result["username"] = entry.get("username")
        return result
```

- [ ] **Step 2: Write unit tests**

Create `configforge/tests/services/test_connection_store.py`:

```python
import os
import tempfile
import pytest
from configforge.services.connection_store import ConnectionStore, STORE_PATH, DATA_DIR

# Use temp dirs to isolate tests
@pytest.fixture(autouse=True)
def temp_data_dir(monkeypatch):
    import configforge.services.connection_store as cs
    tmp = tempfile.mkdtemp()
    monkeypatch.setattr(cs, "DATA_DIR", tmp)
    monkeypatch.setattr(cs, "STORE_PATH", os.path.join(tmp, "db_connections.json"))
    yield
    # cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

def test_create_mysql_connection():
    conn = ConnectionStore.create({
        "name": "Test MySQL",
        "db_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database": "testdb",
        "username": "root",
        "password": "secret123",
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
    conn = ConnectionStore.create({"name": "PG", "db_type": "postgresql", "host": "pg.example.com", "port": 5432, "database": "prod", "username": "admin", "password": "s3cr3t"})
    full = ConnectionStore.get_with_plaintext_password(conn["id"])
    assert full["password"] == "s3cr3t"

def test_password_is_encrypted_on_disk():
    conn = ConnectionStore.create({"name": "Test", "db_type": "sqlite", "file_path": "/tmp/test.db"})
    raw = open(STORE_PATH).read()
    assert "secret" not in raw
    assert conn["passwordSet"] is False

def test_delete_connection():
    conn = ConnectionStore.create({"name": "Delete Me", "db_type": "sqlite", "file_path": "/tmp/del.db"})
    assert ConnectionStore.delete(conn["id"]) is True
    assert ConnectionStore.get(conn["id"]) is None

def test_update_connection():
    conn = ConnectionStore.create({"name": "Old", "db_type": "mysql", "host": "old", "port": 3306, "database": "old", "username": "u", "password": "old"})
    updated = ConnectionStore.update(conn["id"], {"name": "New", "password": "newpass"})
    assert updated["name"] == "New"
    full = ConnectionStore.get_with_plaintext_password(conn["id"])
    assert full["password"] == "newpass"

def test_build_connection_string_sqlite():
    cs = ConnectionStore.build_connection_string({"db_type": "sqlite", "file_path": "/data/report.db"})
    assert cs == "sqlite:////data/report.db"

def test_build_connection_string_mysql():
    cs = ConnectionStore.build_connection_string({"db_type": "mysql", "username": "user", "password": "pass", "host": "10.0.0.1", "port": 3306, "database": "mydb"})
    assert "mysql+pymysql://user:pass@10.0.0.1:3306/mydb" == cs
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/lixinyuan/code/CCTEST && uv run pytest configforge/tests/services/test_connection_store.py -v
```
Expected: 8 tests pass.

- [ ] **Step 4: Commit**

```bash
git add configforge/services/connection_store.py configforge/tests/services/test_connection_store.py
git commit -m "feat(configforge): add ConnectionStore service with Fernet-encrypted persistence"
```

---

### Task 6: ConfigForge — 创建连接管理 API

**Files:**
- Create: `configforge/api/connections.py`

- [ ] **Step 1: Write the connections API router**

Create `configforge/api/connections.py`:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from configforge.services.connection_store import ConnectionStore
from configforge.models.wizard import ErrorResponse

router = APIRouter()


class CreateConnectionRequest(BaseModel):
    name: str
    db_type: str  # "sqlite" | "mysql" | "postgresql"
    host: str = ""
    port: int = 3306
    database: str = ""
    username: str = ""
    password: str = ""
    file_path: str = ""


class UpdateConnectionRequest(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    file_path: str | None = None


class TestConnectionRequest(BaseModel):
    pass  # uses stored connection credentials


@router.post("/connections")
def create_connection(req: CreateConnectionRequest):
    data = {
        "name": req.name,
        "db_type": req.db_type,
    }
    if req.db_type == "sqlite":
        if not req.file_path:
            raise HTTPException(400, detail=ErrorResponse(error="file_path is required for SQLite", code="VALIDATION_ERROR", recoverable=True).model_dump())
        data["file_path"] = req.file_path
    else:
        data["host"] = req.host
        data["port"] = req.port
        data["database"] = req.database
        data["username"] = req.username
        data["password"] = req.password

    conn = ConnectionStore.create(data)
    return conn


@router.get("/connections")
def list_connections():
    return ConnectionStore.list_all()


@router.get("/connections/{conn_id}")
def get_connection(conn_id: str):
    conn = ConnectionStore.get(conn_id)
    if not conn:
        raise HTTPException(404, detail=ErrorResponse(error="Connection not found", code="NOT_FOUND", recoverable=True).model_dump())
    return conn


@router.put("/connections/{conn_id}")
def update_connection(conn_id: str, req: UpdateConnectionRequest):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(400, detail=ErrorResponse(error="No fields to update", code="VALIDATION_ERROR", recoverable=True).model_dump())
    conn = ConnectionStore.update(conn_id, data)
    if not conn:
        raise HTTPException(404, detail=ErrorResponse(error="Connection not found", code="NOT_FOUND", recoverable=True).model_dump())
    return conn


@router.delete("/connections/{conn_id}")
def delete_connection(conn_id: str):
    refs = ConnectionStore.count_references(conn_id)
    if refs:
        raise HTTPException(409, detail=ErrorResponse(
            error=f"Connection is referenced by {len(refs)} config(s)",
            code="CONFLICT",
            recoverable=True,
        ).model_dump())
    deleted = ConnectionStore.delete(conn_id)
    if not deleted:
        raise HTTPException(404, detail=ErrorResponse(error="Connection not found", code="NOT_FOUND", recoverable=True).model_dump())
    return {"ok": True}


@router.post("/connections/{conn_id}/test")
def test_connection(conn_id: str):
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool
    entry = ConnectionStore.get_with_plaintext_password(conn_id)
    if not entry:
        raise HTTPException(404, detail=ErrorResponse(error="Connection not found", code="NOT_FOUND", recoverable=True).model_dump())
    try:
        cs = ConnectionStore.build_connection_string(entry)
        pool_kwargs = {"poolclass": NullPool} if entry["db_type"] == "sqlite" else {"pool_size": 1}
        engine = create_engine(cs, **pool_kwargs)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return {"ok": True, "message": "Connection successful"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/connections/{conn_id}/tables")
def list_tables(conn_id: str):
    from sqlalchemy import create_engine, inspect, NullPool
    entry = ConnectionStore.get_with_plaintext_password(conn_id)
    if not entry:
        raise HTTPException(404, detail=ErrorResponse(error="Connection not found", code="NOT_FOUND", recoverable=True).model_dump())
    try:
        cs = ConnectionStore.build_connection_string(entry)
        pool_kwargs = {"poolclass": NullPool} if entry["db_type"] == "sqlite" else {"pool_size": 1}
        engine = create_engine(cs, **pool_kwargs)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        engine.dispose()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(500, detail=ErrorResponse(error=f"Failed to list tables: {e}", code="DB_ERROR", recoverable=True).model_dump())


@router.get("/connections/{conn_id}/tables/{table}/columns")
def get_table_columns(conn_id: str, table: str):
    from sqlalchemy import create_engine, inspect, NullPool
    entry = ConnectionStore.get_with_plaintext_password(conn_id)
    if not entry:
        raise HTTPException(404, detail=ErrorResponse(error="Connection not found", code="NOT_FOUND", recoverable=True).model_dump())
    try:
        cs = ConnectionStore.build_connection_string(entry)
        pool_kwargs = {"poolclass": NullPool} if entry["db_type"] == "sqlite" else {"pool_size": 1}
        engine = create_engine(cs, **pool_kwargs)
        inspector = inspect(engine)
        cols = inspector.get_columns(table)
        engine.dispose()
        return {"columns": [{"name": c["name"], "type": str(c["type"])} for c in cols]}
    except Exception as e:
        raise HTTPException(500, detail=ErrorResponse(error=f"Failed to get columns: {e}", code="DB_ERROR", recoverable=True).model_dump())
```

- [ ] **Step 2: Mount router in server.py**

In `configforge/server.py`, add after line 11:
```python
from configforge.api.connections import router as connections_router
```

And after line 57:
```python
app.include_router(connections_router, prefix="/api")
```

- [ ] **Step 3: Verify endpoints register**

```bash
cd /Users/lixinyuan/code/CCTEST && uv run uvicorn configforge.server:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/connections | python -m json.tool
curl -s http://localhost:8000/api/health | python -m json.tool
kill %1
```
Expected: `/api/connections` returns `[]`, `/api/health` returns `{"status": "ok"}`.

- [ ] **Step 4: Commit**

```bash
git add configforge/api/connections.py configforge/server.py
git commit -m "feat(configforge): add connection management API endpoints"
```

---

### Task 7: ConfigForge — 更新 YAML builder 和 pipeline

**Files:**
- Modify: `configforge/services/yaml_builder.py`
- Modify: `configforge/core/pipeline.py`

- [ ] **Step 1: Add database branch to build_yaml**

In `configforge/services/yaml_builder.py`, in the input loop (line 8-22), change the `if/else` to `if/elif/else`:

```python
for inp in state.inputs:
    cfg = inp.config
    if cfg.type == "csv":
        config_dict = {
            "type": "csv",
            "delimiter": cfg.delimiter,
            "encoding": cfg.encoding,
            "has_header": cfg.has_header,
        }
    elif cfg.type == "database":
        config_dict = {
            "type": "database",
            "db_type": cfg.db_type,
            "connection_string": cfg.connection_string,
            "tables": cfg.tables,
            "sql": cfg.sql,
        }
    else:
        config_dict = {"type": "excel", "sheet": cfg.sheet}
    ...
```

- [ ] **Step 2: Add connectionId resolution in execute_pipeline**

In `configforge/core/pipeline.py`, after `exec_state = copy.deepcopy(state)` (line 71), add:

```python
# Resolve database connectionIds to connection_strings before building YAML
from configforge.services.connection_store import ConnectionStore

for inp in exec_state.inputs:
    cfg = inp.config
    if hasattr(cfg, 'type') and cfg.type == "database":
        entry = ConnectionStore.get_with_plaintext_password(cfg.connection_id)
        if not entry:
            raise RuntimeError(f"Connection '{cfg.connection_id}' not found — please reconfigure")
        cfg.connection_string = ConnectionStore.build_connection_string(entry)
        cfg.db_type = entry["db_type"]
```

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/lixinyuan/code/CCTEST && uv run pytest configforge/tests/ src/pipeforge/tests/ -v
```
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add configforge/services/yaml_builder.py configforge/core/pipeline.py
git commit -m "feat(configforge): wire database input into YAML builder and pipeline execution"
```

---

### Task 8: Frontend — 扩展类型定义

**Files:**
- Modify: `configforge-web/src/types/wizard.ts`

- [ ] **Step 1: Add database types**

In `configforge-web/src/types/wizard.ts`, after `CsvInputConfig` (line 38), add:

```typescript
export type DbType = 'sqlite' | 'mysql' | 'postgresql'

export interface DatabaseInputConfig {
  type: 'database'
  connectionId: string
  queryType: 'table' | 'sql'
  tables: string[]    // max 1 element
  sql: string
}

export type DbConnection =
  | {
      id: string
      name: string
      dbType: 'sqlite'
      filePath: string
      createdAt: number
      updatedAt: number
    }
  | {
      id: string
      name: string
      dbType: 'mysql' | 'postgresql'
      host: string
      port: number
      database: string
      username: string
      password: string
      createdAt: number
      updatedAt: number
    }

export interface DbConnectionSummary {
  id: string
  name: string
  dbType: DbType
  // sqlite → filePath, mysql/postgresql → hostname/IP
  host: string
  port?: number
  database?: string
  username?: string
  passwordSet: boolean
  verified: boolean
  createdAt: number
  updatedAt: number
}
```

Modify `InputSource` (line 40):
- `plugin: 'excel' | 'csv'` → `plugin: 'excel' | 'csv' | 'database'`
- `config: ExcelInputConfig | CsvInputConfig` → `config: ExcelInputConfig | CsvInputConfig | DatabaseInputConfig`

- [ ] **Step 2: Type check**

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit 2>&1 | head -20
```
Expected: No new type errors from the added types (existing errors may exist).

- [ ] **Step 3: Commit**

```bash
git add configforge-web/src/types/wizard.ts
git commit -m "feat(configforge-web): add database input types (DbConnection, DatabaseInputConfig)"
```

---

### Task 9: Frontend — 扩展 Wizard Store

**Files:**
- Modify: `configforge-web/src/stores/wizard.ts`

- [ ] **Step 1: Extend addInput for 'database' plugin**

In `configforge-web/src/stores/wizard.ts`, modify `addInput` function signature (line 37):
```typescript
function addInput(plugin: 'excel' | 'csv' | 'database' = 'excel') {
```

And add a database branch to the config construction:
```typescript
function addInput(plugin: 'excel' | 'csv' | 'database' = 'excel') {
  let config: ExcelInputConfig | CsvInputConfig | DatabaseInputConfig
  if (plugin === 'csv') {
    config = { type: 'csv' as const, delimiter: ',', encoding: 'utf-8', hasHeader: true }
  } else if (plugin === 'database') {
    config = { type: 'database' as const, connectionId: '', queryType: 'table', tables: [], sql: '' }
  } else {
    config = { type: 'excel' as const, sheet: '' }
  }

  inputs.value.push({
    plugin,
    table: '',
    paramKey: '',
    fileId: '',
    config,
  } as InputSource)
}
```

- [ ] **Step 2: Update loadFromConfigState for database deserialization**

In `loadFromConfigState`, in the input mapping section (lines 79-92), add handling for `database` config type. After the existing `let config` block:

```typescript
// In the input loop ~line 82, extend the config mapping:
let config: any
if (inp.config.type === 'csv') {
  config = { type: 'csv', delimiter: inp.config.delimiter, encoding: inp.config.encoding, hasHeader: inp.config.has_header }
} else if (inp.config.type === 'database') {
  config = { type: 'database', connectionId: inp.config.connection_id || '', queryType: inp.config.query_type || 'table', tables: inp.config.tables || [], sql: inp.config.sql || '' }
} else {
  config = { type: 'excel', sheet: inp.config.sheet || 'Sheet1' }
}
```

- [ ] **Step 3: Type check and verify**

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit 2>&1 | head -20
```
Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add configforge-web/src/stores/wizard.ts
git commit -m "feat(configforge-web): extend wizard store for database input sources"
```

---

### Task 10: Frontend — 添加连接 API 函数

**Files:**
- Modify: `configforge-web/src/composables/useWizardApi.ts`

- [ ] **Step 1: Add connection API functions**

In `configforge-web/src/composables/useWizardApi.ts`, add after the existing `useWizardApi` composable:

```typescript
export function useConnectionApi() {
  const connecting = ref(false)
  const connectionError = ref<string | null>(null)

  async function request<T>(method: string, url: string, body?: any): Promise<T | null> {
    try {
      const opts: RequestInit = {
        method,
        headers: { 'Content-Type': 'application/json' },
      }
      if (body) opts.body = JSON.stringify(body)
      const res = await fetch(url, opts)
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }))
        connectionError.value = err.error || err.detail || 'Request failed'
        return null
      }
      return await res.json()
    } catch (e: any) {
      connectionError.value = e.message || 'Network error'
      return null
    }
  }

  async function fetchConnections(): Promise<DbConnectionSummary[]> {
    const result = await request<DbConnectionSummary[]>('GET', '/api/connections')
    return result || []
  }

  async function createConnection(data: Record<string, any>): Promise<DbConnectionSummary | null> {
    return request<DbConnectionSummary>('POST', '/api/connections', data)
  }

  async function updateConnection(id: string, data: Record<string, any>): Promise<DbConnectionSummary | null> {
    return request<DbConnectionSummary>('PUT', `/api/connections/${id}`, data)
  }

  async function deleteConnection(id: string): Promise<boolean> {
    const result = await request<{ ok: boolean }>('DELETE', `/api/connections/${id}`)
    return result?.ok ?? false
  }

  async function testConnection(id: string): Promise<{ ok: boolean; error?: string }> {
    connecting.value = true
    const result = await request<{ ok: boolean; error?: string }>('POST', `/api/connections/${id}/test`)
    connecting.value = false
    return result || { ok: false, error: 'Request failed' }
  }

  async function fetchTables(id: string): Promise<string[]> {
    const result = await request<{ tables: string[] }>('GET', `/api/connections/${id}/tables`)
    return result?.tables || []
  }

  async function fetchColumns(id: string, table: string): Promise<{ name: string; type: string }[]> {
    const result = await request<{ columns: { name: string; type: string }[] }>('GET', `/api/connections/${id}/tables/${table}/columns`)
    return result?.columns || []
  }

  return {
    connecting,
    connectionError,
    fetchConnections,
    createConnection,
    updateConnection,
    deleteConnection,
    testConnection,
    fetchTables,
    fetchColumns,
  }
}
```

Make sure to import `DbConnectionSummary` at the top:
```typescript
import type { DbConnectionSummary } from '../types/wizard'
```

- [ ] **Step 2: Type check**

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add configforge-web/src/composables/useWizardApi.ts
git commit -m "feat(configforge-web): add connection API functions to useWizardApi"
```

---

### Task 11: Frontend — 激活 Database 卡片

**Files:**
- Modify: `configforge-web/src/components/step2/InputSourceList.vue`

- [ ] **Step 1: Activate the Database card**

In `configforge-web/src/components/step2/InputSourceList.vue`, find the Database placeholder `NCard` (around lines 33-37). Replace it with a functional card:

```html
<NCard
  hoverable
  :class="[
    'cursor-pointer text-center border-2 transition-colors',
    store.inputs.some(i => i.plugin === 'database') ? 'border-purple-600 bg-purple-50' : 'border-dashed border-slate-200'
  ]"
  @click="addInput('database')"
>
  <span class="text-2xl block mb-2">🔌</span>
  <span class="text-sm font-semibold">Database</span>
</NCard>
```

- [ ] **Step 2: Update addInput wrapper**

Update the `addInput` function signature (line 77):
```typescript
function addInput(plugin: 'excel' | 'csv' | 'database' = 'excel') {
```

- [ ] **Step 3: Type check**

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 4: Commit**

```bash
git add configforge-web/src/components/step2/InputSourceList.vue
git commit -m "feat(configforge-web): activate Database input card in InputSourceList"
```

---

### Task 12: Frontend — 创建 DatabaseForm 组件

**Files:**
- Create: `configforge-web/src/components/step2/DatabaseForm.vue`

- [ ] **Step 1: Write DatabaseForm component**

Create `configforge-web/src/components/step2/DatabaseForm.vue`:

```vue
<template>
  <div class="space-y-3">
    <!-- Connection selector -->
    <div>
      <label class="block text-sm font-medium text-slate-900 mb-1">数据库连接</label>
      <NSelect
        v-model:value="selectedConnectionId"
        :options="connectionOptions"
        placeholder="选择已有连接..."
        @update:value="onConnectionSelected"
      />
      <p class="text-xs text-slate-400 mt-1">
        或前往
        <RouterLink to="/settings" class="text-blue-600 underline">设置页</RouterLink>
        管理连接
      </p>
    </div>

    <!-- Test connection + load tables -->
    <div v-if="selectedConnectionId" class="flex gap-2">
      <NButton size="small" :loading="testing" @click="onTestConnection">测试连通</NButton>
      <NButton size="small" :loading="loadingTables" @click="onLoadTables">加载表列表</NButton>
    </div>
    <p v-if="testResult" :class="testResult.ok ? 'text-green-600' : 'text-red-500'" class="text-xs">
      {{ testResult.ok ? '连接成功' : testResult.error }}
    </p>

    <!-- Query type toggle -->
    <div v-if="selectedConnectionId">
      <label class="block text-sm font-medium text-slate-900 mb-1">查询方式</label>
      <NRadioGroup v-model:value="queryType">
        <NRadio value="table">选择表</NRadio>
        <NRadio value="sql">自定义 SQL</NRadio>
      </NRadioGroup>
    </div>

    <!-- Table selector -->
    <div v-if="selectedConnectionId && queryType === 'table'">
      <label class="block text-sm font-medium text-slate-900 mb-1">选择表</label>
      <NSelect
        v-model:value="selectedTable"
        :options="tableOptions"
        placeholder="选择数据库表..."
      />
    </div>

    <!-- SQL editor -->
    <div v-if="selectedConnectionId && queryType === 'sql'">
      <label class="block text-sm font-medium text-slate-900 mb-1">SQL 查询</label>
      <NInput
        v-model:value="sqlQuery"
        type="textarea"
        placeholder="SELECT * FROM ..."
        :rows="3"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { NSelect, NButton, NRadioGroup, NRadio, NInput, useMessage } from 'naive-ui'
import { RouterLink } from 'vue-router'
import { useConnectionApi } from '../../composables/useWizardApi'
import type { InputSource, DbConnectionSummary } from '../../types/wizard'

const props = defineProps<{ input: InputSource; index: number }>()
const emit = defineEmits<{ update: [input: InputSource] }>()

const message = useMessage()
const api = useConnectionApi()

const selectedConnectionId = ref(props.input.config.type === 'database' ? (props.input.config as any).connectionId || '' : '')
const queryType = ref<'table' | 'sql'>('table')
const selectedTable = ref('')
const sqlQuery = ref('')
const testing = ref(false)
const loadingTables = ref(false)
const testResult = ref<{ ok: boolean; error?: string } | null>(null)
const connections = ref<DbConnectionSummary[]>([])
const tableList = ref<string[]>([])

const connectionOptions = computed(() =>
  connections.value.map(c => ({ label: c.name, value: c.id }))
)

const tableOptions = computed(() =>
  tableList.value.map(t => ({ label: t, value: t }))
)

function emitUpdate() {
  const config: any = {
    type: 'database',
    connectionId: selectedConnectionId.value,
    queryType: queryType.value,
    tables: queryType.value === 'table' && selectedTable.value ? [selectedTable.value] : [],
    sql: queryType.value === 'sql' ? sqlQuery.value : '',
  }
  emit('update', { ...props.input, config })
}

onMounted(async () => {
  connections.value = await api.fetchConnections()
})

async function onConnectionSelected() {
  testResult.value = null
  tableList.value = []
  emitUpdate()
}

async function onTestConnection() {
  testing.value = true
  testResult.value = await api.testConnection(selectedConnectionId.value)
  testing.value = false
}

async function onLoadTables() {
  loadingTables.value = true
  tableList.value = await api.fetchTables(selectedConnectionId.value)
  loadingTables.value = false
}

watch([selectedTable, sqlQuery], () => emitUpdate())
watch(queryType, () => {
  selectedTable.value = ''
  sqlQuery.value = ''
  emitUpdate()
})
</script>
```

- [ ] **Step 2: Type check**

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit 2>&1 | head -30
```
Expected: Fix any type errors in the new component.

- [ ] **Step 3: Commit**

```bash
git add configforge-web/src/components/step2/DatabaseForm.vue
git commit -m "feat(configforge-web): add DatabaseForm component for database input configuration"
```

---

### Task 13: Frontend — 更新 InputSourceCard 路由数据库表单

**Files:**
- Modify: `configforge-web/src/components/step2/InputSourceCard.vue`

- [ ] **Step 1: Add DatabaseForm rendering in InputSourceCard**

In `configforge-web/src/components/step2/InputSourceCard.vue`:

1. Import `DatabaseForm`:
```typescript
import DatabaseForm from './DatabaseForm.vue'
```

2. Update the tag badge (around line 7-9):
```html
<NTag :type="input.plugin === 'csv' ? 'info' : input.plugin === 'database' ? 'warning' : 'success'" size="small">
  {{ input.plugin === 'csv' ? 'CSV' : input.plugin === 'database' ? 'DB' : 'Excel' }}
</NTag>
```

3. After the CSV form block (line 75-107 area), add the Database form:
```html
<!-- Database-specific fields -->
<div v-if="input.plugin === 'database'" class="pt-3 border-t border-dashed border-slate-200">
  <DatabaseForm :input="input" :index="index" @update="handleUpdate" />
</div>
```

4. Hide the file upload section for database inputs by adding `v-if="input.plugin !== 'database'"` to the upload area (around line 17-38).

5. Skip the AI column analysis for database inputs — the `onAnalyzeClick` and related sections already check for `fileId`, so they naturally skip.

- [ ] **Step 2: Type check**

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit 2>&1 | head -30
```

- [ ] **Step 3: Commit**

```bash
git add configforge-web/src/components/step2/InputSourceCard.vue
git commit -m "feat(configforge-web): route database inputs to DatabaseForm in InputSourceCard"
```

---

### Task 14: Frontend — 创建 ConnectionManager 组件

**Files:**
- Create: `configforge-web/src/components/common/ConnectionManager.vue`

- [ ] **Step 1: Write ConnectionManager component**

Create `configforge-web/src/components/common/ConnectionManager.vue`:

```vue
<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold text-slate-700">数据库连接</h3>
      <NButton size="tiny" @click="showForm = !showForm">
        {{ showForm ? '取消' : '+ 新建连接' }}
      </NButton>
    </div>

    <!-- Connection list -->
    <div v-if="connections.length === 0 && !showForm" class="text-xs text-slate-400 py-2">
      暂无连接配置
    </div>

    <div v-for="conn in connections" :key="conn.id" class="flex items-center justify-between py-2 px-3 bg-slate-50 rounded text-sm">
      <div>
        <span class="font-medium">{{ conn.name }}</span>
        <span class="text-xs text-slate-400 ml-2">{{ conn.dbType }}</span>
        <span v-if="!conn.verified" class="text-xs text-orange-500 ml-1">未验证</span>
      </div>
      <div class="flex gap-1">
        <NButton text size="tiny" @click="onTest(conn.id)">测试</NButton>
        <NButton text size="tiny" type="error" @click="onDelete(conn.id)">删除</NButton>
      </div>
    </div>

    <!-- Add/Edit form -->
    <div v-if="showForm" class="space-y-2 p-3 border border-slate-200 rounded">
      <NInput v-model:value="form.name" size="small" placeholder="连接名称" />
      <NSelect v-model:value="form.dbType" size="small" :options="dbTypeOptions" placeholder="数据库类型" />
      <template v-if="form.dbType === 'sqlite'">
        <NInput v-model:value="form.filePath" size="small" placeholder="文件路径（如 /data/report.db）" />
      </template>
      <template v-else>
        <NInput v-model:value="form.host" size="small" placeholder="主机" />
        <NInputNumber v-model:value="form.port" size="small" placeholder="端口" :min="1" :max="65535" />
        <NInput v-model:value="form.database" size="small" placeholder="数据库名" />
        <NInput v-model:value="form.username" size="small" placeholder="用户名" />
        <NInput v-model:value="form.password" size="small" type="password" placeholder="密码" />
      </template>
      <div class="flex gap-2">
        <NButton size="small" type="primary" :loading="saving" @click="onSave">保存</NButton>
        <NButton size="small" @click="onSaveAndTest" :loading="saving">保存并测试</NButton>
      </div>
      <p v-if="errorMsg" class="text-xs text-red-500">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { NButton, NInput, NSelect, NInputNumber, useMessage } from 'naive-ui'
import { useConnectionApi } from '../../composables/useWizardApi'
import type { DbConnectionSummary } from '../../types/wizard'

const message = useMessage()
const api = useConnectionApi()

const connections = ref<DbConnectionSummary[]>([])
const showForm = ref(false)
const saving = ref(false)
const errorMsg = ref<string | null>(null)

const dbTypeOptions = [
  { label: 'SQLite', value: 'sqlite' },
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgresql' },
]

const emptyForm = () => ({
  name: '',
  dbType: 'mysql' as string,
  host: 'localhost',
  port: 3306,
  database: '',
  username: 'root',
  password: '',
  filePath: '',
})

const form = reactive(emptyForm())

async function refresh() {
  connections.value = await api.fetchConnections()
}

onMounted(refresh)

async function onSave() {
  saving.value = true
  errorMsg.value = null
  const result = await api.createConnection({ ...form })
  if (result) {
    message.success('连接已保存')
    Object.assign(form, emptyForm())
    showForm.value = false
    await refresh()
  } else {
    errorMsg.value = api.connectionError.value || '保存失败'
  }
  saving.value = false
}

async function onSaveAndTest() {
  saving.value = true
  errorMsg.value = null
  const result = await api.createConnection({ ...form })
  if (!result) {
    errorMsg.value = api.connectionError.value || '保存失败'
    saving.value = false
    return
  }
  const testResult = await api.testConnection(result.id)
  if (testResult.ok) {
    message.success('连接已保存并验证成功')
  } else {
    message.warning(`连接已保存但验证失败: ${testResult.error}`)
  }
  Object.assign(form, emptyForm())
  showForm.value = false
  await refresh()
  saving.value = false
}

async function onTest(id: string) {
  const result = await api.testConnection(id)
  if (result.ok) {
    message.success('连接成功')
  } else {
    message.error(`连接失败: ${result.error}`)
  }
}

async function onDelete(id: string) {
  const ok = await api.deleteConnection(id)
  if (ok) {
    message.success('连接已删除')
    await refresh()
  } else {
    message.error(api.connectionError.value || '删除失败')
  }
}
</script>
```

- [ ] **Step 2: Type check**

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit 2>&1 | head -30
```

- [ ] **Step 3: Commit**

```bash
git add configforge-web/src/components/common/ConnectionManager.vue
git commit -m "feat(configforge-web): add ConnectionManager component for connection CRUD"
```

---

### Task 15: Frontend — 在 SettingsPage 嵌入 ConnectionManager

**Files:**
- Modify: `configforge-web/src/views/SettingsPage.vue`

- [ ] **Step 1: Embed ConnectionManager**

In `configforge-web/src/views/SettingsPage.vue`:

1. Import `ConnectionManager`:
```typescript
import ConnectionManager from '../components/common/ConnectionManager.vue'
```

2. After the AI settings card (after the `</div>` closing `settings__card` around line 82), add a second card:

```html
<div class="settings__card">
  <ConnectionManager />
</div>
```

- [ ] **Step 2: Type check and build**

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add configforge-web/src/views/SettingsPage.vue
git commit -m "feat(configforge-web): embed ConnectionManager in SettingsPage"
```

---

### Task 16: Backend — 集成测试

**Files:**
- Create: `configforge/tests/api/test_connections.py`

- [ ] **Step 1: Write connection API integration tests**

```python
import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from configforge.server import app

# Isolate data directory for tests
@pytest.fixture(autouse=True)
def temp_data_dir(monkeypatch):
    import configforge.services.connection_store as cs
    tmp = tempfile.mkdtemp()
    monkeypatch.setattr(cs, "DATA_DIR", tmp)
    monkeypatch.setattr(cs, "STORE_PATH", os.path.join(tmp, "db_connections.json"))
    yield
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

@pytest.fixture
def client():
    return TestClient(app)

def test_create_connection_sqlite(client):
    resp = client.post("/api/connections", json={
        "name": "Test SQLite", "db_type": "sqlite", "file_path": "/tmp/test.db"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test SQLite"
    assert data["db_type"] == "sqlite"
    assert data["passwordSet"] is False

def test_create_connection_mysql(client):
    resp = client.post("/api/connections", json={
        "name": "Test MySQL", "db_type": "mysql",
        "host": "localhost", "port": 3306, "database": "test",
        "username": "root", "password": "secret"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["passwordSet"] is True

def test_list_connections(client):
    client.post("/api/connections", json={"name": "A", "db_type": "sqlite", "file_path": "/tmp/a.db"})
    client.post("/api/connections", json={"name": "B", "db_type": "sqlite", "file_path": "/tmp/b.db"})
    resp = client.get("/api/connections")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

def test_get_connection(client):
    resp = client.post("/api/connections", json={"name": "GetMe", "db_type": "sqlite", "file_path": "/tmp/g.db"})
    conn_id = resp.json()["id"]
    resp = client.get(f"/api/connections/{conn_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetMe"

def test_update_connection(client):
    resp = client.post("/api/connections", json={"name": "Old", "db_type": "sqlite", "file_path": "/tmp/old.db"})
    conn_id = resp.json()["id"]
    resp = client.put(f"/api/connections/{conn_id}", json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"

def test_delete_connection(client):
    resp = client.post("/api/connections", json={"name": "Del", "db_type": "sqlite", "file_path": "/tmp/del.db"})
    conn_id = resp.json()["id"]
    resp = client.delete(f"/api/connections/{conn_id}")
    assert resp.status_code == 200
    resp = client.get(f"/api/connections/{conn_id}")
    assert resp.status_code == 404

def test_connection_not_returned_password(client):
    resp = client.post("/api/connections", json={"name": "Secure", "db_type": "mysql", "host": "h", "port": 1, "database": "d", "username": "u", "password": "s3cr3t"})
    data = resp.json()
    assert "password" not in data
    assert data["passwordSet"] is True
```

- [ ] **Step 2: Run integration tests**

```bash
cd /Users/lixinyuan/code/CCTEST && uv run pytest configforge/tests/api/test_connections.py -v
```
Expected: 7 tests pass.

- [ ] **Step 3: Commit**

```bash
git add configforge/tests/api/test_connections.py
git commit -m "test(configforge): add connection API integration tests"
```

---

### Task 17: 端到端验证

- [ ] **Step 1: Run all backend tests**

```bash
cd /Users/lixinyuan/code/CCTEST && uv run pytest configforge/tests/ src/pipeforge/tests/ -v
```
Expected: All tests pass.

- [ ] **Step 2: Frontend type check**

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vue-tsc --noEmit
```
Expected: No new type errors.

- [ ] **Step 3: Frontend build**

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npm run build
```
Expected: Build succeeds.

- [ ] **Step 4: Manual smoke test**

```bash
# Start backend
cd /Users/lixinyuan/code/CCTEST && uv run uvicorn configforge.server:app --port 8000 &
# Start frontend
cd /Users/lixinyuan/code/CCTEST/configforge-web && npm run dev &
```
Manual steps:
1. Open http://localhost:5173/settings → verify "数据库连接" section appears
2. Create a SQLite connection (point to a test .db file)
3. Open http://localhost:5173/config/new → Step 2 → click Database card
4. Select the connection → test → load tables
5. Verify the database input appears in the inputs list
6. Continue through Step 3/4/5

---

## Task Dependency Order

```
Task 1 (PipeForge models)
  └─ Task 2 (PipeForge plugin)

Task 3 (ConfigForge models)
  └─ Task 4 (ConfigForge generator)
       └─ Task 7 (YAML + pipeline wiring)

Task 5 (ConnectionStore)
  └─ Task 6 (Connections API)
       └─ Task 16 (API tests)

Task 8 (Frontend types)
  └─ Task 9 (Wizard store)
       └─ Task 11 (InputSourceList card)
       └─ Task 10 (Connection API composable)
            └─ Task 12 (DatabaseForm)
            └─ Task 14 (ConnectionManager)
                 └─ Task 15 (SettingsPage embed)
Task 13 (InputSourceCard) depends on Task 12

Task 17 (E2E) depends on everything
```

Independent work streams:
- **Stream A:** Tasks 1 → 2 → 7 (PipeForge + pipeline wiring)
- **Stream B:** Tasks 3 → 4 → 7 (ConfigForge models + generator)
- **Stream C:** Tasks 5 → 6 → 16 (ConnectionStore + API + tests)
- **Stream D:** Tasks 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 (Frontend)
- Streams A, B, C can be done in parallel; Stream D after A+B+C (or at least after C for API availability)

