from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

from configforge.utils.crypto import get_cipher
from configforge.utils.paths import get_data_dir

if TYPE_CHECKING:
    from configforge.models.ai import AiSettings

SETTINGS_FILE = os.path.join(get_data_dir(), "ai_settings.json")


def load_settings() -> AiSettings:
    from configforge.models.ai import AiSettings

    if not os.path.exists(SETTINGS_FILE):
        return AiSettings()
    with open(SETTINGS_FILE) as f:
        raw = json.load(f)
    # schema_version is storage metadata (added by load_with_migration), not a model field
    raw.pop("schema_version", None)
    if raw.get("api_key"):
        try:
            cipher = get_cipher()
            raw["api_key"] = cipher.decrypt(raw["api_key"].encode()).decode()
        except Exception:
            logging.getLogger("configforge.ai").warning(
                "Failed to decrypt stored API key — encryption key may have changed. "
                "API key has been cleared; please reconfigure in Settings."
            )
            raw["api_key"] = ""
    return AiSettings(**raw)


def save_settings(settings: AiSettings) -> None:
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    data = settings.model_dump()
    if data.get("api_key"):
        cipher = get_cipher()
        data["api_key"] = cipher.encrypt(data["api_key"].encode()).decode()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def mask_key(key: str) -> str:
    if not key or len(key) <= 6:
        return key
    return key[:3] + "***" + key[-3:]
