"""Backup and restore API endpoints."""

import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from configforge.middleware.auth import require_role
from configforge.models.user import User
from configforge.storage import get_audit_store
from configforge.utils.backup import (
    create_backup,
    list_backups,
    restore_backup,
    save_backup_to_disk,
)

router = APIRouter(prefix="/api/backup", tags=["系统"])

_audit = get_audit_store()


class BackupListResponse(BaseModel):
    backups: list[dict]


class RestoreResponse(BaseModel):
    ok: bool
    restored_files: int
    errors: list[str]


@router.get("", summary="列出备份", description="列出所有可用的数据备份文件。", response_model=BackupListResponse)
async def list_backups_api(_user: User = Depends(require_role("admin"))):
    return BackupListResponse(backups=list_backups())


@router.post("", summary="创建备份", description="创建一个新的数据备份（zip 格式），包含所有配置和数据文件。", response_model=dict)
async def create_backup_api(_user: User = Depends(require_role("admin"))):
    filename, zip_bytes = create_backup()
    filepath = save_backup_to_disk(zip_bytes, filename)
    _audit.log_audit("backup", "system", filename)
    return {"filename": filename, "size": len(zip_bytes), "path": filepath}


@router.get("/download/{filename}", summary="下载备份", description="下载指定的备份文件。")
async def download_backup_api(filename: str, _user: User = Depends(require_role("admin"))):
    import os

    from configforge.utils.backup import _get_backup_dir

    # Validate filename to prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = os.path.join(_get_backup_dir(), filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Backup not found")

    with open(filepath, "rb") as f:
        data = f.read()

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/restore", summary="恢复备份", description="从上传的 zip 备份文件恢复数据。会覆盖现有的配置和数据文件。", response_model=RestoreResponse)
async def restore_backup_api(file: UploadFile = File(...), _user: User = Depends(require_role("admin"))):
    zip_bytes = await file.read()
    if not zip_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    result = restore_backup(zip_bytes)
    _audit.log_audit("restore", "system", file.filename or "unknown")
    return RestoreResponse(ok=True, restored_files=result["restored_files"], errors=result["errors"])
