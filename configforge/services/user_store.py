"""User store with bcrypt password hashing (fallback to hashlib.sha256)."""

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timezone

from configforge.models.user import User, UserWithHash, UserRole
from configforge.utils.file_lock import read_json_locked, write_json_locked
from configforge.utils.migration import load_with_migration
from configforge.utils.paths import get_data_dir

DATA_DIR = get_data_dir()
STORE_PATH = os.path.join(DATA_DIR, "users.json")

# Try bcrypt via passlib, then bcrypt directly, then fall back to hashlib
_HASH_BACKEND = "sha256"

try:
    from passlib.hash import bcrypt as passlib_bcrypt

    def _hash_password(password: str) -> str:
        return passlib_bcrypt.hash(password)

    def _verify_password(password: str, password_hash: str) -> bool:
        try:
            return passlib_bcrypt.verify(password, password_hash)
        except Exception:
            return False

    _HASH_BACKEND = "passlib"
except ImportError:
    try:
        import bcrypt as _bcrypt

        def _hash_password(password: str) -> str:
            return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()

        def _verify_password(password: str, password_hash: str) -> bool:
            try:
                return _bcrypt.checkpw(password.encode(), password_hash.encode())
            except Exception:
                return False

        _HASH_BACKEND = "bcrypt"
    except ImportError:
        # Fallback: hashlib.sha256 with salt
        def _hash_password(password: str) -> str:
            salt = secrets.token_hex(16)
            h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
            return f"sha256${salt}${h}"

        def _verify_password(password: str, password_hash: str) -> bool:
            if not password_hash.startswith("sha256$"):
                return False
            try:
                _, salt, h = password_hash.split("$", 2)
                return hmac_compare(
                    hashlib.sha256(f"{salt}{password}".encode()).hexdigest(), h
                )
            except Exception:
                return False

        import hmac as _hmac

        def hmac_compare(a: str, b: str) -> bool:
            return _hmac.compare_digest(a.encode(), b.encode())


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load() -> dict:
    _ensure_data_dir()
    return load_with_migration(STORE_PATH, default={"users": {}})


def _save(data: dict):
    _ensure_data_dir()
    write_json_locked(STORE_PATH, data)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_default_admin():
    """Ensure the default admin user exists (username: admin, password: admin123)."""
    store = _load()
    users = store.get("users", {})
    for uid, u in users.items():
        if u.get("username") == "admin":
            return  # Admin already exists
    # Create default admin
    admin_id = uuid.uuid4().hex[:16]
    users[admin_id] = {
        "id": admin_id,
        "username": "admin",
        "role": "admin",
        "password_hash": _hash_password("admin123"),
        "created_at": _now_iso(),
    }
    store["users"] = users
    _save(store)


def create_user(username: str, password: str, role: str = "editor") -> User | None:
    """Create a new user. Returns User or None if username already exists."""
    store = _load()
    users = store.get("users", {})
    for u in users.values():
        if u.get("username") == username:
            return None
    user_id = uuid.uuid4().hex[:16]
    now = _now_iso()
    users[user_id] = {
        "id": user_id,
        "username": username,
        "role": role,
        "password_hash": _hash_password(password),
        "created_at": now,
    }
    store["users"] = users
    _save(store)
    return User(id=user_id, username=username, role=role, created_at=now)


def authenticate(username: str, password: str) -> User | None:
    """Authenticate a user by username and password. Returns User or None."""
    store = _load()
    users = store.get("users", {})
    for u in users.values():
        if u.get("username") == username:
            if _verify_password(password, u.get("password_hash", "")):
                return User(
                    id=u["id"],
                    username=u["username"],
                    role=u.get("role", "editor"),
                    created_at=u.get("created_at", ""),
                )
            return None
    return None


def list_users() -> list[User]:
    """List all users (without password hashes)."""
    store = _load()
    users = store.get("users", {})
    return [
        User(
            id=u["id"],
            username=u["username"],
            role=u.get("role", "editor"),
            created_at=u.get("created_at", ""),
        )
        for u in users.values()
    ]


def delete_user(user_id: str) -> bool:
    """Delete a user by ID. Returns True if deleted, False if not found."""
    store = _load()
    users = store.get("users", {})
    if user_id not in users:
        return False
    del users[user_id]
    store["users"] = users
    _save(store)
    return True


def get_user_by_id(user_id: str) -> User | None:
    """Get a user by ID (without password hash)."""
    store = _load()
    users = store.get("users", {})
    u = users.get(user_id)
    if not u:
        return None
    return User(
        id=u["id"],
        username=u["username"],
        role=u.get("role", "editor"),
        created_at=u.get("created_at", ""),
    )
