from pydantic import BaseModel, Field
from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class User(BaseModel):
    id: str
    username: str
    role: UserRole = UserRole.editor
    created_at: str = ""


class UserWithHash(User):
    password_hash: str = ""
