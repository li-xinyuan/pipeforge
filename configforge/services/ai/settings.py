import json
import os
from base64 import urlsafe_b64encode
from cryptography.fernet import Fernet


_SETTINGS_DIR = os.environ.get("CONFIGFORGE_DATA_DIR", os.path.join(os.getcwd(), "data"))
SETTINGS_FILE = os.path.join(_SETTINGS_DIR, "ai_settings.json")


def _get_cipher() -> Fernet:
    raw = os.environ.get("CONFIGFORGE_ENCRYPTION_KEY", "")
    if raw:
        key = urlsafe_b64encode(raw.encode().ljust(32, b"\x00")[:32])
    else:
        key_path = os.path.join(_SETTINGS_DIR, ".fernet_key")
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(_SETTINGS_DIR, exist_ok=True)
            with open(key_path, "wb") as f:
                f.write(key)
    return Fernet(key)


def load_settings() -> "AiSettings":
    from configforge.models.ai import AiSettings

    if not os.path.exists(SETTINGS_FILE):
        return AiSettings()
    with open(SETTINGS_FILE, "r") as f:
        raw = json.load(f)
    if raw.get("api_key"):
        try:
            cipher = _get_cipher()
            raw["api_key"] = cipher.decrypt(raw["api_key"].encode()).decode()
        except Exception:
            raw["api_key"] = ""
    return AiSettings(**raw)


def save_settings(settings: "AiSettings") -> None:
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    data = settings.model_dump()
    if data.get("api_key"):
        cipher = _get_cipher()
        data["api_key"] = cipher.encrypt(data["api_key"].encode()).decode()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def mask_key(key: str) -> str:
    if not key or len(key) <= 6:
        return key
    return key[:3] + "***" + key[-3:]
