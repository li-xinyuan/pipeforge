import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from configforge.models.wizard import FileUploadResponse, ErrorResponse

router = APIRouter()

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_FILE_SIZE = 50 * 1024 * 1024
UPLOAD_DIR = "tmp/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


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
    return {"file_id": file_id, "original_name": file.filename}
