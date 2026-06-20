from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from configforge.middleware.jwt import (
    create_access_token,
    decode_token,
    is_jwt_enabled,
)
from configforge.services.user_store import (
    authenticate,
    create_user,
    get_user_by_id,
)

router = APIRouter(prefix="/api/auth", tags=["认证管理"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "editor"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def _get_current_user_from_request(request: Request) -> dict | None:
    """Extract and verify the current user from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    payload = decode_token(token)
    if not payload:
        return None
    return payload


@router.post("/login", response_model=TokenResponse, summary="用户登录", description="使用用户名和密码进行身份验证，成功后返回 JWT 访问令牌。需要先设置 CONFIGFORGE_JWT_SECRET 环境变量启用 JWT 认证。")
async def login(req: LoginRequest):
    """Authenticate user and return JWT token."""
    if not is_jwt_enabled():
        raise HTTPException(
            status_code=400,
            detail={"error": "JWT authentication is not enabled. Set CONFIGFORGE_JWT_SECRET to enable.", "code": "AUTH_DISABLED"},
        )

    user = authenticate(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid username or password", "code": "AUTH_FAILED"},
        )

    token = create_access_token(user.id, user.username, user.role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={"id": user.id, "username": user.username, "role": user.role},
    )


@router.post("/register", summary="注册新用户", description="注册新用户账号。仅管理员可执行此操作，需要在 Authorization 头中提供管理员 JWT 令牌。支持 admin、editor、viewer 三种角色。")
async def register(req: RegisterRequest, request: Request):
    """Register a new user. Only admin can register new users."""
    if not is_jwt_enabled():
        raise HTTPException(
            status_code=400,
            detail={"error": "JWT authentication is not enabled", "code": "AUTH_DISABLED"},
        )

    # Verify caller is admin
    payload = _get_current_user_from_request(request)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail={"error": "Authentication required", "code": "AUTH_REQUIRED"},
        )
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail={"error": "Only admin can register new users", "code": "FORBIDDEN"},
        )

    # Validate role
    if req.role not in ("admin", "editor", "viewer"):
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid role. Must be admin, editor, or viewer", "code": "INVALID_ROLE"},
        )

    user = create_user(req.username, req.password, req.role)
    if not user:
        raise HTTPException(
            status_code=409,
            detail={"error": "Username already exists", "code": "USERNAME_EXISTS"},
        )

    return {"id": user.id, "username": user.username, "role": user.role, "created_at": user.created_at}


@router.get("/me", summary="获取当前用户信息", description="获取当前已认证用户的信息，包括用户 ID、用户名、角色和创建时间。需要在 Authorization 头中提供有效的 JWT 令牌。")
async def get_current_user(request: Request):
    """Get current authenticated user info."""
    if not is_jwt_enabled():
        raise HTTPException(
            status_code=400,
            detail={"error": "JWT authentication is not enabled", "code": "AUTH_DISABLED"},
        )

    payload = _get_current_user_from_request(request)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid or expired token", "code": "AUTH_FAILED"},
        )

    user = get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"error": "User not found", "code": "USER_NOT_FOUND"},
        )

    return {"id": user.id, "username": user.username, "role": user.role, "created_at": user.created_at}
