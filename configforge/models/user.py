from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class User(BaseModel):
    id: str
    username: str
    role: UserRole = UserRole.editor
    created_at: str = ""
    must_change_password: bool = False


class UserWithHash(User):
    password_hash: str = ""
