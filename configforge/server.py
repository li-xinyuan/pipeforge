from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from configforge.api.preview import router as preview_router
from configforge.api.files import router as files_router
from configforge.api.ai import router as ai_router
from configforge.api.wizard import router as wizard_router
from configforge.models.wizard import ErrorResponse

app = FastAPI(title="ConfigForge", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(detail), code="VALIDATION_ERROR", recoverable=True
        ).model_dump(),
    )


app.include_router(preview_router, prefix="/api/preview")
app.include_router(files_router, prefix="/api/files")
app.include_router(ai_router, prefix="/api/ai")
app.include_router(wizard_router, prefix="/api/wizard")


@app.get("/api/health")
async def health():
    return {"status": "ok"}

from fastapi.staticfiles import StaticFiles
import os

# mount must be last — all API routes registered above
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
