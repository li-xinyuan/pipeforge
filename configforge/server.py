import asyncio
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from configforge.api.ai import router as ai_router
from configforge.api.auth import router as auth_router
from configforge.api.backup import router as backup_router
from configforge.api.configs import router as configs_router
from configforge.api.connections import router as connections_router
from configforge.api.executions import _cleanup_old_outputs
from configforge.api.executions import router as exec_router
from configforge.api.files import cleanup_old_files, cleanup_old_logs
from configforge.api.files import router as files_router
from configforge.api.notifications import router as notifications_router
from configforge.api.plugins import router as plugins_router
from configforge.api.preview import router as preview_router
from configforge.api.schedules import router as schedules_router
from configforge.api.storage import router as storage_router
from configforge.api.templates import router as templates_router
from configforge.api.wizard import router as wizard_router
from configforge.middleware.auth import AuthMiddleware, require_role
from configforge.models.user import User
from configforge.models.wizard import ErrorResponse
from configforge.scheduler import shutdown_scheduler, start_scheduler
from configforge.services.template_store import ensure_builtin_templates
from configforge.utils.logging import request_id_var, setup_logging


def _get_version() -> str:
    """Read version from pyproject.toml (works in dev mode)."""
    try:
        from importlib.metadata import version as pkg_version
        return pkg_version("pipeforge")
    except Exception:
        pass
    # Fallback: read pyproject.toml directly
    try:
        import tomllib
        pyproject_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pyproject.toml")
        if os.path.exists(pyproject_path):
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data.get("project", {}).get("version", "0.0.0")
    except Exception:
        pass
    return "0.0.0"


_CLEANUP_INTERVAL_SECONDS = 3600  # Run cleanup every hour

_logger = logging.getLogger("configforge")


async def _periodic_cleanup():
    """Background task: periodically clean old temp files, logs, and outputs."""
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
        try:
            cleanup_old_files()
            cleanup_old_logs()
            _cleanup_old_outputs()
        except Exception:
            pass  # Don't crash the background task


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    from configforge.utils.env import is_production

    if is_production():
        # 检查 JWT_SECRET
        jwt_secret = os.environ.get("CONFIGFORGE_JWT_SECRET", "")
        if not jwt_secret or len(jwt_secret) < 32:
            _logger.critical("生产模式下必须设置 CONFIGFORGE_JWT_SECRET（长度 ≥ 32）")
            raise SystemExit(1)

        # 检查 ENCRYPTION_KEY
        if not os.environ.get("CONFIGFORGE_ENCRYPTION_KEY"):
            _logger.critical("生产模式下必须设置 CONFIGFORGE_ENCRYPTION_KEY")
            raise SystemExit(1)

        # 检查 CORS 不允许 *
        cors_origins = os.environ.get("CORS_ORIGINS", "")
        if not cors_origins or cors_origins.strip() == "*":
            _logger.critical("生产模式下 CORS_ORIGINS 不允许为空或包含 *")
            raise SystemExit(1)

    start_scheduler()
    ensure_builtin_templates()
    # Auto-migrate index.json to v2 if needed
    from configforge.utils.migration import migrate_index_v1_to_v2
    migration_result = migrate_index_v1_to_v2()
    if migration_result.get("migrated"):
        _logger.info("Index migration completed: %s", migration_result.get("message"))
    elif migration_result.get("errors"):
        _logger.warning("Index migration had errors: %s", migration_result.get("errors"))
    # Ensure default admin user when JWT auth is enabled
    if os.environ.get("CONFIGFORGE_JWT_SECRET"):
        from configforge.storage import get_user_store
        get_user_store().ensure_default_admin()
    if not os.environ.get("CONFIGFORGE_ENCRYPTION_KEY"):
        _logger.warning(
            "CONFIGFORGE_ENCRYPTION_KEY not set. Auto-generated encryption key "
            "will be lost on container restart. Set this variable in production "
            "to prevent data loss."
        )
    cleanup_task = asyncio.create_task(_periodic_cleanup())
    yield
    cleanup_task.cancel()
    shutdown_scheduler()


_OPENAPI_TAGS = [
    {"name": "数据预览", "description": "文件和 SQL 数据预览"},
    {"name": "文件管理", "description": "文件上传和管理"},
    {"name": "AI 服务", "description": "AI 建议和编排"},
    {"name": "向导", "description": "配置向导流程"},
    {"name": "配置管理", "description": "管道配置的增删改查和执行"},
    {"name": "连接管理", "description": "数据库连接管理"},
    {"name": "执行历史", "description": "管道执行记录和结果"},
    {"name": "调度管理", "description": "定时调度任务管理"},
    {"name": "通知管理", "description": "通知渠道和消息管理"},
    {"name": "模板管理", "description": "配置模板市场"},
    {"name": "认证管理", "description": "JWT 用户认证和授权"},
    {"name": "系统", "description": "系统健康检查和运维接口"},
]

app = FastAPI(
    title="ConfigForge API",
    description="数据管道配置向导 API",
    version="0.8.1",
    lifespan=lifespan,
    openapi_tags=_OPENAPI_TAGS,
)

# URL-encoded path traversal patterns — checked against raw_path (URL-encoded) before Starlette normalizes
_RAW_TRAVERSAL_RE = re.compile(r"(%[2eE][%2eE]|%[2fF]|%[5cC]|%00)", re.IGNORECASE)


@app.middleware("http")
async def block_encoded_traversal(request: Request, call_next):
    raw = request.scope.get("raw_path", request.url.path.encode()).decode("latin-1", errors="replace")
    if _RAW_TRAVERSAL_RE.search(raw) or ".." in raw:
        return JSONResponse(
            status_code=400,
            content={"error": "Path traversal detected", "code": "PATH_TRAVERSAL", "recoverable": False},
        )
    return await call_next(request)


_cors_origins_env = os.environ.get("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

# Development fallback: allow localhost if no origins configured
if not _cors_origins:
    _cors_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)


@app.middleware("http")
async def request_id_middleware(request, call_next):
    request_id_var.set(uuid.uuid4().hex[:12])
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    response.headers["X-Request-ID"] = request_id_var.get("")
    # Record metrics (skip /api/metrics itself to avoid recursion)
    if not request.url.path.startswith("/api/metrics"):
        try:
            from configforge.utils.metrics import record_http_request
            record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                duration=duration,
            )
        except Exception:
            pass
    return response

# API Key authentication (disabled when CONFIGFORGE_API_KEY is not set)
app.add_middleware(AuthMiddleware)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    detail = exc.detail
    if isinstance(detail, dict):
        if "code" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail)
        # Preserve structured error info (e.g., checkpoint checks)
        return JSONResponse(status_code=exc.status_code, content={"error": str(detail), **detail})
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(detail), code="VALIDATION_ERROR", recoverable=True
        ).model_dump(),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError (e.g., from validate_id) as 400 Bad Request."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=str(exc), code="VALIDATION_ERROR", recoverable=True
        ).model_dump(),
    )


app.include_router(preview_router, prefix="/api/preview", tags=["数据预览"])
app.include_router(files_router, prefix="/api/files", tags=["文件管理"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI 服务"])
app.include_router(wizard_router, prefix="/api/wizard", tags=["向导"])
app.include_router(configs_router, prefix="/api/configs", tags=["配置管理"])
app.include_router(connections_router, prefix="/api", tags=["连接管理"])
app.include_router(exec_router, tags=["执行历史"])
app.include_router(schedules_router, tags=["调度管理"])
app.include_router(notifications_router, tags=["通知管理"])
app.include_router(templates_router, prefix="/api/templates", tags=["模板管理"])
app.include_router(storage_router, tags=["存储后端"])
app.include_router(plugins_router, tags=["插件管理"])
app.include_router(auth_router, tags=["认证管理"])
app.include_router(backup_router, tags=["系统"])


@app.get("/api/audit-log", summary="获取审计日志", description="获取系统审计日志记录。支持按目标类型、操作类型、用户、时间范围筛选，默认返回最近 100 条。", tags=["认证管理"])
async def get_audit_log_api(
    target_type: str | None = None,
    action: str | None = None,
    user: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = 100,
    _user: User = Depends(require_role("admin")),
):
    from configforge.storage import get_audit_store
    return {"entries": get_audit_store().get_audit_log(target_type, action, limit, user=user, start_time=start_time, end_time=end_time)}


@app.get("/api/health", summary="健康检查", description="检查系统健康状态，包括数据目录可写性、配置目录存在性、调度器运行状态和加密密钥配置情况。", tags=["系统"])
async def health():
    from configforge.utils.paths import get_configs_dir, get_data_dir

    checks = {
        "status": "ok",
        "version": _get_version(),
    }

    # Check data directory writable
    data_dir = get_data_dir()
    try:
        os.makedirs(data_dir, exist_ok=True)
        test_file = os.path.join(data_dir, ".health_check")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        checks["data_dir_writable"] = True
    except Exception:
        checks["data_dir_writable"] = False
        checks["status"] = "degraded"

    # Check configs directory
    configs_dir = get_configs_dir()
    checks["configs_dir_exists"] = os.path.isdir(configs_dir)

    # Check scheduler
    try:
        from configforge.scheduler import _scheduler
        checks["scheduler_running"] = _scheduler.running if _scheduler else False
    except Exception:
        checks["scheduler_running"] = False

    # Check encryption key
    checks["encryption_key_set"] = bool(os.environ.get("CONFIGFORGE_ENCRYPTION_KEY"))

    return checks


@app.get("/api/metrics", summary="Prometheus 指标", description="返回 Prometheus 格式的监控指标数据，包括 HTTP 请求计数、请求延迟、Pipeline 执行统计等。可用于集成 Prometheus + Grafana 监控系统。", tags=["系统"])
async def metrics():
    from configforge.utils.metrics import get_metrics, get_metrics_content_type
    from fastapi import Response
    return Response(content=get_metrics(), media_type=get_metrics_content_type())


@app.post("/api/error-report", summary="前端错误上报", description="接收前端 JavaScript 错误报告，用于监控前端运行时异常。", tags=["系统"])
async def error_report(request: Request):
    import logging
    _logger = logging.getLogger("configforge.frontend_errors")
    try:
        body = await request.json()
        reports = body.get("reports", [])
        for report in reports:
            _logger.error(
                "Frontend %s: %s at %s",
                report.get("level", "error"),
                report.get("message", "unknown"),
                report.get("url", "unknown"),
                extra={"stack": report.get("stack"), "context": report.get("context")},
            )
    except Exception:
        pass
    return {"ok": True}


from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_static_dir = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(_static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(_static_dir, "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't intercept API or docs routes
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi"):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"error": "Not found"})
        file_path = os.path.join(_static_dir, full_path)
        real = os.path.realpath(file_path)
        if not real.startswith(os.path.realpath(_static_dir) + os.sep):
            return JSONResponse(status_code=403, content={"error": "Forbidden"})
        if full_path and os.path.isfile(real):
            return FileResponse(real)
        index_path = os.path.join(_static_dir, "index.html")
        return FileResponse(index_path)
