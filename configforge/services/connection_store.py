import json
import os
import uuid
from datetime import datetime, timezone
from configforge.services.ai.settings import _get_cipher
from configforge.utils.file_lock import read_json_locked, write_json_locked

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
STORE_PATH = os.path.join(DATA_DIR, "db_connections.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load() -> dict:
    _ensure_data_dir()
    if not os.path.exists(STORE_PATH):
        return {"connections": {}}
    return read_json_locked(STORE_PATH)


def _save(data: dict):
    _ensure_data_dir()
    write_json_locked(STORE_PATH, data)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConnectionStore:
    """Repository for database connections with Fernet-encrypted passwords."""

    @staticmethod
    def create(data: dict) -> dict:
        cipher = _get_cipher()
        conn_id = uuid.uuid4().hex[:16]
        password = data.get("password", "")
        encrypted = cipher.encrypt(password.encode()).decode() if password else ""

        store = _load()
        entry = {
            "id": conn_id,
            "name": data["name"],
            "db_type": data["db_type"],
        }
        if data["db_type"] == "sqlite":
            entry["file_path"] = data.get("file_path", "")
            entry["verified"] = False
        else:
            entry["host"] = data.get("host", "")
            entry["port"] = int(data.get("port", 3306))
            entry["database"] = data.get("database", "")
            entry["username"] = data.get("username", "")
            entry["password"] = encrypted
            entry["verified"] = False

        entry["created_at"] = _now_iso()
        entry["updated_at"] = _now_iso()
        store["connections"][conn_id] = entry
        _save(store)

        return ConnectionStore._summarize(conn_id, entry)

    @staticmethod
    def list_all() -> list[dict]:
        store = _load()
        return [ConnectionStore._summarize(cid, c) for cid, c in store["connections"].items()]

    @staticmethod
    def get(conn_id: str) -> dict | None:
        store = _load()
        entry = store["connections"].get(conn_id)
        if not entry:
            return None
        return ConnectionStore._summarize(conn_id, entry)

    @staticmethod
    def get_with_plaintext_password(conn_id: str) -> dict | None:
        """Internal use — returns full entry with decrypted password."""
        store = _load()
        entry = store["connections"].get(conn_id)
        if not entry:
            return None
        cipher = _get_cipher()
        entry = dict(entry)
        if entry.get("password"):
            entry["password"] = cipher.decrypt(entry["password"].encode()).decode()
        entry["id"] = conn_id
        return entry

    @staticmethod
    def update(conn_id: str, data: dict) -> dict | None:
        store = _load()
        entry = store["connections"].get(conn_id)
        if not entry:
            return None
        cipher = _get_cipher()

        for field in ("name", "host", "port", "database", "username", "file_path"):
            if field in data:
                entry[field] = data[field]
        if "password" in data and data["password"]:
            entry["password"] = cipher.encrypt(data["password"].encode()).decode()
        entry["updated_at"] = _now_iso()
        store["connections"][conn_id] = entry
        _save(store)
        return ConnectionStore._summarize(conn_id, entry)

    @staticmethod
    def delete(conn_id: str) -> bool:
        store = _load()
        if conn_id not in store["connections"]:
            return False
        del store["connections"][conn_id]
        _save(store)
        return True

    @staticmethod
    def build_connection_string(entry: dict) -> str:
        """Build SQLAlchemy connection string from a connection entry (with plaintext password)."""
        db_type = entry["db_type"]
        if db_type == "sqlite":
            return f"sqlite:///{entry['file_path']}"
        elif db_type == "mysql":
            return (
                f"mysql+pymysql://{entry['username']}:{entry['password']}"
                f"@{entry['host']}:{entry['port']}/{entry['database']}"
            )
        elif db_type == "postgresql":
            return (
                f"postgresql+psycopg2://{entry['username']}:{entry['password']}"
                f"@{entry['host']}:{entry['port']}/{entry['database']}"
            )
        raise ValueError(f"Unsupported db_type: {db_type}")

    @staticmethod
    def _update_verified(conn_id: str, verified: bool):
        store = _load()
        entry = store["connections"].get(conn_id)
        if entry:
            entry["verified"] = verified
            entry["updated_at"] = _now_iso()
            store["connections"][conn_id] = entry
            _save(store)

    @staticmethod
    def count_references(conn_id: str) -> list[str]:
        """Check how many saved configs reference this connection. Returns list of config IDs."""
        # Search saved wizard configs for references to this connection
        import glob
        refs = []
        for path in glob.glob(os.path.join(DATA_DIR, "..", "configs", "*.state.json")):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                for inp in data.get("inputs", []):
                    cfg = inp.get("config", {})
                    if cfg.get("connection_id") == conn_id or cfg.get("connectionId") == conn_id:
                        refs.append(os.path.basename(path).replace(".json", ""))
                        break
            except (json.JSONDecodeError, IOError):
                continue
        return refs

    @staticmethod
    def _summarize(conn_id: str, entry: dict) -> dict:
        host = entry.get("file_path", entry.get("host", ""))
        result = {
            "id": conn_id,
            "name": entry["name"],
            "db_type": entry["db_type"],
            "host": host,
            "passwordSet": bool(entry.get("password", "")),
            "verified": entry.get("verified", False),
            "createdAt": entry.get("created_at", ""),
            "updatedAt": entry.get("updated_at", ""),
        }
        if entry.get("db_type") != "sqlite":
            result["port"] = entry.get("port")
            result["database"] = entry.get("database")
            result["username"] = entry.get("username")
        return result
