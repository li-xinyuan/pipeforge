from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from configforge.services.connection_store import ConnectionStore
from configforge.models.wizard import ErrorResponse
from configforge.utils.security import validate_id, sanitize_connection_string, validate_sqlite_path, safe_identifier

router = APIRouter()


class CreateConnectionRequest(BaseModel):
    name: str
    db_type: str
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


@router.post("/connections")
def create_connection(req: CreateConnectionRequest):
    data = {"name": req.name, "db_type": req.db_type}
    if req.db_type == "sqlite":
        if not req.file_path:
            raise HTTPException(400, detail=ErrorResponse(
                error="file_path is required for SQLite",
                code="VALIDATION_ERROR", recoverable=True,
            ).model_dump())
        # Validate SQLite file path is within allowed directories
        try:
            validate_sqlite_path(req.file_path, "file_path")
        except ValueError as e:
            raise HTTPException(400, detail=ErrorResponse(
                error=str(e), code="VALIDATION_ERROR", recoverable=True,
            ).model_dump())
        # Validate file is a valid SQLite database
        import os as _os
        path = req.file_path
        if _os.path.exists(path):
            if not _os.path.isfile(path):
                raise HTTPException(400, detail=ErrorResponse(
                    error=f"Path is not a file: {path}",
                    code="VALIDATION_ERROR", recoverable=True,
                ).model_dump())
            with open(path, "rb") as f:
                header = f.read(16)
            if header[:16] != b"SQLite format 3\0":
                raise HTTPException(400, detail=ErrorResponse(
                    error=f"File is not a valid SQLite database: {path}",
                    code="VALIDATION_ERROR", recoverable=True,
                ).model_dump())
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
    validate_id(conn_id, "conn_id")
    conn = ConnectionStore.get(conn_id)
    if not conn:
        raise HTTPException(404, detail=ErrorResponse(
            error="Connection not found", code="NOT_FOUND", recoverable=True,
        ).model_dump())
    return conn


@router.put("/connections/{conn_id}")
def update_connection(conn_id: str, req: UpdateConnectionRequest):
    validate_id(conn_id, "conn_id")
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(400, detail=ErrorResponse(
            error="No fields to update", code="VALIDATION_ERROR", recoverable=True,
        ).model_dump())
    conn = ConnectionStore.update(conn_id, data)
    if not conn:
        raise HTTPException(404, detail=ErrorResponse(
            error="Connection not found", code="NOT_FOUND", recoverable=True,
        ).model_dump())
    return conn


@router.delete("/connections/{conn_id}")
def delete_connection(conn_id: str):
    validate_id(conn_id, "conn_id")
    refs = ConnectionStore.count_references(conn_id)
    if refs:
        raise HTTPException(409, detail=ErrorResponse(
            error=f"Connection is referenced by {len(refs)} config(s)",
            code="CONFLICT", recoverable=True,
        ).model_dump())
    deleted = ConnectionStore.delete(conn_id)
    if not deleted:
        raise HTTPException(404, detail=ErrorResponse(
            error="Connection not found", code="NOT_FOUND", recoverable=True,
        ).model_dump())
    return {"ok": True}


@router.post("/connections/{conn_id}/test")
def test_connection(conn_id: str):
    validate_id(conn_id, "conn_id")
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    entry = ConnectionStore.get_with_plaintext_password(conn_id)
    if not entry:
        raise HTTPException(404, detail=ErrorResponse(
            error="Connection not found", code="NOT_FOUND", recoverable=True,
        ).model_dump())
    try:
        cs = ConnectionStore.build_connection_string(entry)
        pool_kwargs = {"poolclass": NullPool} if entry["db_type"] == "sqlite" else {"pool_size": 1}
        engine_kwargs = dict(pool_kwargs)
        if entry["db_type"] != "sqlite":
            engine_kwargs["connect_args"] = {"connect_timeout": 10}
        engine = create_engine(cs, **engine_kwargs)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        ConnectionStore._update_verified(conn_id, True)
        return {"ok": True, "message": "Connection successful"}
    except Exception as e:
        ConnectionStore._update_verified(conn_id, False)
        # Sanitize error message to avoid leaking connection strings with passwords
        error_msg = sanitize_connection_string(str(e))
        return {"ok": False, "error": error_msg}


@router.get("/connections/{conn_id}/tables")
def list_tables(conn_id: str):
    validate_id(conn_id, "conn_id")
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.pool import NullPool

    entry = ConnectionStore.get_with_plaintext_password(conn_id)
    if not entry:
        raise HTTPException(404, detail=ErrorResponse(
            error="Connection not found", code="NOT_FOUND", recoverable=True,
        ).model_dump())
    try:
        cs = ConnectionStore.build_connection_string(entry)
        pool_kwargs = {"poolclass": NullPool} if entry["db_type"] == "sqlite" else {"pool_size": 1}
        engine = create_engine(cs, **pool_kwargs)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        engine.dispose()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(500, detail=ErrorResponse(
            error=sanitize_connection_string(f"Failed to list tables: {e}"),
            code="DB_ERROR", recoverable=True,
        ).model_dump())


@router.get("/connections/{conn_id}/tables/{table}/columns")
def get_table_columns(conn_id: str, table: str):
    validate_id(conn_id, "conn_id")
    safe_identifier(table, "table")
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.pool import NullPool

    entry = ConnectionStore.get_with_plaintext_password(conn_id)
    if not entry:
        raise HTTPException(404, detail=ErrorResponse(
            error="Connection not found", code="NOT_FOUND", recoverable=True,
        ).model_dump())
    try:
        cs = ConnectionStore.build_connection_string(entry)
        pool_kwargs = {"poolclass": NullPool} if entry["db_type"] == "sqlite" else {"pool_size": 1}
        engine = create_engine(cs, **pool_kwargs)
        inspector = inspect(engine)
        cols = inspector.get_columns(table)
        engine.dispose()
        return {"columns": [{"name": c["name"], "type": str(c["type"])} for c in cols]}
    except Exception as e:
        raise HTTPException(500, detail=ErrorResponse(
            error=sanitize_connection_string(f"Failed to get columns: {e}"),
            code="DB_ERROR", recoverable=True,
        ).model_dump())
