"""SMTP settings storage — mirrors the AI settings pattern."""

from __future__ import annotations

import json
import logging
import os
from pydantic import BaseModel, ConfigDict, Field

from configforge.utils.paths import get_data_dir
from configforge.utils.crypto import get_cipher

SETTINGS_FILE = os.path.join(get_data_dir(), "smtp_settings.json")


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


def load_settings() -> SmtpSettings:
    if not os.path.exists(SETTINGS_FILE):
        return SmtpSettings()
    with open(SETTINGS_FILE, "r") as f:
        raw = json.load(f)
    if raw.get("password"):
        try:
            cipher = get_cipher()
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
        cipher = get_cipher()
        data["password"] = cipher.encrypt(data["password"].encode()).decode()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def mask_password(password: str) -> str:
    if not password or len(password) <= 6:
        return password
    return password[:3] + "***" + password[-3:]
