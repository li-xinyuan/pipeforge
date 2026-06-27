"""Simple API Key / JWT authentication middleware.

When CONFIGFORGE_JWT_SECRET environment variable is set, JWT-based
authentication is enabled: all API requests (except health check,
auth endpoints, and static files) must include a valid Bearer token
in the Authorization header.

When CONFIGFORGE_API_KEY environment variable is set (and JWT is not
enabled), all API requests must include the key via X-API-Key header.

If neither is set, authentication is disabled (dev mode).
"""
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def _get_api_key() -> str:
    """Get API key from environment (dynamic, not cached at import time)."""
    return os.environ.get("CONFIGFORGE_API_KEY", "")

# Paths that don't require authentication
PUBLIC_PATHS = {"/", "/api/health", "/api/metrics", "/api/error-report"}

# Paths that are public when JWT auth is enabled (login/register)
JWT_PUBLIC_PATHS = {"/api/auth/login", "/api/auth/register"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        jwt_secret = os.environ.get("CONFIGFORGE_JWT_SECRET", "")
        api_key = _get_api_key()

        # No auth configured — auth disabled (dev mode)
        if not api_key and not jwt_secret:
            return await call_next(request)

        # Public paths don't require auth
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Static files don't require auth
        if request.url.path.startswith("/assets") or request.url.path.endswith((".js", ".css", ".ico", ".png", ".svg")):
            return await call_next(request)

        # JWT authentication mode
        if jwt_secret:
            # Auth endpoints are public (login/register need to be accessible without token)
            if request.url.path in JWT_PUBLIC_PATHS:
                return await call_next(request)

            # All other endpoints (including /api/auth/me) require a valid JWT
            from configforge.middleware.jwt import decode_token

            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized: Bearer token required", "code": "AUTH_FAILED"},
                )

            token = auth_header[7:]
            payload = decode_token(token)
            if not payload:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized: invalid or expired token", "code": "AUTH_FAILED"},
                )

            return await call_next(request)

        return await call_next(request)


from fastapi import Depends, HTTPException, Request

from configforge.models.user import User, UserRole


async def get_current_user_dep(request: Request) -> User:
    """FastAPI 依赖：从请求中提取已认证用户。

    JWT 未启用时返回默认 admin 用户（开发模式）。
    """
    from configforge.middleware.jwt import is_jwt_enabled

    if not is_jwt_enabled():
        # 开发模式：返回默认 admin 用户
        return User(id="dev", username="dev", role=UserRole.admin)

    # 从 Authorization 头解析用户
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error": "未认证", "code": "AUTH_REQUIRED"})

    from configforge.middleware.jwt import decode_token
    from configforge.storage import get_user_store

    token = auth_header[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail={"error": "令牌无效或已过期", "code": "AUTH_FAILED"})

    user = get_user_store().get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=401, detail={"error": "用户不存在", "code": "USER_NOT_FOUND"})

    return user


def require_role(*roles: str):
    """角色权限依赖工厂。返回一个 FastAPI 依赖，检查当前用户是否具有指定角色之一。"""
    async def dependency(request: Request, user: User = Depends(get_current_user_dep)):
        if user.role not in [UserRole(r) for r in roles]:
            # 记录权限拒绝审计日志
            try:
                from configforge.storage import get_audit_store
                get_audit_store().log_audit(
                    action="permission_denied",
                    target_type="auth",
                    target_id=user.id,
                    details={"message": f"需要角色 {roles}，当前角色 {user.role.value}，访问 {request.method} {request.url.path}"},
                )
            except Exception:
                pass  # 审计日志不应影响主流程
            raise HTTPException(
                status_code=403,
                detail={"error": f"权限不足：需要角色 {roles}，当前角色 {user.role.value}", "code": "FORBIDDEN"},
            )
        return user
    return dependency
