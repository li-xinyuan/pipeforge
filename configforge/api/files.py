import os
import time
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from configforge.models.wizard import FileUploadResponse, ErrorResponse

router = APIRouter()

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_FILE_SIZE = 50 * 1024 * 1024
UPLOAD_DIR = "tmp/uploads"
MAX_FILE_AGE_SECONDS = 24 * 60 * 60

os.makedirs(UPLOAD_DIR, exist_ok=True)


def cleanup_old_files() -> int:
    now = time.time()
    removed = 0
    for name in os.listdir(UPLOAD_DIR):
        path = os.path.join(UPLOAD_DIR, name)
        if not os.path.isfile(path):
            continue
        if now - os.path.getmtime(path) > MAX_FILE_AGE_SECONDS:
            os.remove(path)
            removed += 1
    return removed


cleanup_old_files()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error="No file provided",
                code="VALIDATION_ERROR",
                recoverable=True,
            ).model_dump(),
        )
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error=f"Unsupported format '{ext}'",
                code="FILE_FORMAT_UNSUPPORTED",
                recoverable=True,
            ).model_dump(),
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=ErrorResponse(
                error="File exceeds 50MB limit",
                code="FILE_TOO_LARGE",
                recoverable=True,
            ).model_dump(),
        )
    file_id = uuid.uuid4().hex + ext
    path = os.path.join(UPLOAD_DIR, file_id)
    with open(path, "wb") as f:
        f.write(content)

    file_type = "csv" if ext == ".csv" else "excel"
    import json
    meta_path = os.path.join(UPLOAD_DIR, file_id + ".meta.json")
    with open(meta_path, "w") as f:
        json.dump({"original_name": file.filename, "type": file_type}, f)

    return {"file_id": file_id, "original_name": file.filename}
