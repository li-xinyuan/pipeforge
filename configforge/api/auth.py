from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from configforge.middleware.auth import require_role
from configforge.middleware.jwt import (
    create_access_token,
    decode_token,
    is_jwt_enabled,
)
from configforge.models.user import User
from configforge.services.user_store import (
    authenticate,
    change_password,
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


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


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
        user={"id": user.id, "username": user.username, "role": user.role, "must_change_password": user.must_change_password},
    )


@router.post("/register", summary="注册新用户", description="注册新用户账号。仅管理员可执行此操作，需要在 Authorization 头中提供管理员 JWT 令牌。支持 admin、editor、viewer 三种角色。")
async def register(req: RegisterRequest, _user: User = Depends(require_role("admin"))):
    """Register a new user. Only admin can register new users."""
    if not is_jwt_enabled():
        raise HTTPException(
            status_code=400,
            detail={"error": "JWT authentication is not enabled", "code": "AUTH_DISABLED"},
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


@router.post("/change-password", summary="修改密码", description="修改当前用户的登录密码。需要在 Authorization 头中提供有效的 JWT 令牌，并正确输入旧密码。")
async def change_password_endpoint(req: ChangePasswordRequest, request: Request):
    payload = _get_current_user_from_request(request)
    if not payload:
        raise HTTPException(401, detail={"error": "Authentication required", "code": "AUTH_REQUIRED"})
    success = change_password(payload.get("sub", ""), req.old_password, req.new_password)
    if not success:
        raise HTTPException(400, detail={"error": "旧密码错误", "code": "INVALID_PASSWORD"})
    return {"message": "密码修改成功"}


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
