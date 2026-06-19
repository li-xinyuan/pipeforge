"""SMTP settings storage — mirrors the AI settings pattern."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from base64 import urlsafe_b64encode
from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field


_SETTINGS_DIR = os.environ.get("CONFIGFORGE_DATA_DIR", os.path.join(os.getcwd(), "data"))
SETTINGS_FILE = os.path.join(_SETTINGS_DIR, "smtp_settings.json")


class SmtpSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = ""
    port: int = Field(default=587, ge=1, le=65535)
    user: str = ""
    password: str = Field(default="", max_length=512)
    use_tls: bool = True
    sender: str = ""


class SmtpSettingsUpdate(BaseModel):
    """For PUT — password=None means keep the old value, password="" means clear it."""

    model_config = ConfigDict(extra="forbid")

    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    user: str | None = None
    password: str | None = Field(default=None, max_length=512)
    use_tls: bool | None = None
    sender: str | None = None


def _get_cipher() -> Fernet:
    raw = os.environ.get("CONFIGFORGE_ENCRYPTION_KEY", "")
    if raw:
        key = urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
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


def load_settings() -> SmtpSettings:
    if not os.path.exists(SETTINGS_FILE):
        return SmtpSettings()
    with open(SETTINGS_FILE, "r") as f:
        raw = json.load(f)
    if raw.get("password"):
        try:
            cipher = _get_cipher()
            raw["password"] = cipher.decrypt(raw["password"].encode()).decode()
        except Exception:
            logging.getLogger("configforge.smtp").warning(
                "Failed to decrypt stored SMTP password — encryption key may have changed. "
                "Password has been cleared; please reconfigure in Settings."
            )
            raw["password"] = ""
    return SmtpSettings(**raw)


def save_settings(settings: SmtpSettings) -> None:
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    data = settings.model_dump()
    if data.get("password"):
        cipher = _get_cipher()
        data["password"] = cipher.encrypt(data["password"].encode()).decode()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def mask_password(password: str) -> str:
    if not password or len(password) <= 6:
        return password
    return password[:3] + "***" + password[-3:]
