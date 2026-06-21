import glob
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from configforge.models.template import TemplateRequirement
from configforge.utils.cache import TTLCache
from configforge.utils.file_lock import write_json_locked
from configforge.utils.migration import load_with_migration
from configforge.utils.paths import get_data_dir

logger = logging.getLogger(__name__)

DATA_DIR = get_data_dir()
STORE_PATH = os.path.join(DATA_DIR, "templates.json")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
_cache = TTLCache(ttl=30.0)


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load() -> dict:
    _ensure_data_dir()
    cached = _cache.get("templates")
    if cached is not None:
        return cached
    data = load_with_migration(STORE_PATH, default={"templates": {}})
    _cache.set("templates", data)
    return data


def _save(data: dict):
    _ensure_data_dir()
    write_json_locked(STORE_PATH, data)
    _cache.invalidate("templates")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TemplateStore:
    """Repository for pipeline configuration templates."""

    @staticmethod
    def list_templates(category: str | None = None, search: str | None = None) -> list[dict]:
        store = _load()
        templates = list(store["templates"].values())

        if category:
            templates = [t for t in templates if t.get("category") == category]

        if search:
            q = search.lower()
            templates = [
                t for t in templates
                if q in t.get("name", "").lower()
                or q in t.get("description", "").lower()
                or any(q in tag.lower() for tag in t.get("tags", []))
            ]

        # Sort: official first, then by usage_count descending
        templates.sort(key=lambda t: (not t.get("is_official", False), -t.get("usage_count", 0)))
        return templates

    @staticmethod
    def get_template(template_id: str) -> dict | None:
        store = _load()
        return store["templates"].get(template_id)

    @staticmethod
    def create_template(
        name: str,
        description: str,
        category: str,
        tags: list[str],
        config_state: dict,
        author: str = "",
        is_official: bool = False,
    ) -> dict:
        template_id = uuid.uuid4().hex[:12]
        now = _now_iso()

        requirements = TemplateStore.extract_requirements(config_state)

        entry = {
            "id": template_id,
            "name": name,
            "description": description,
            "category": category,
            "tags": tags,
            "author": author,
            "version": "1.0",
            "config_state": config_state,
            "requirements": [r.model_dump() for r in requirements],
            "usage_count": 0,
            "is_official": is_official,
            "created_at": now,
            "updated_at": now,
        }

        store = _load()
        store["templates"][template_id] = entry
        _save(store)
        return entry

    @staticmethod
    def update_template(template_id: str, **updates) -> dict | None:
        store = _load()
        entry = store["templates"].get(template_id)
        if not entry:
            return None

        allowed_fields = {"name", "description", "category", "tags", "author", "version", "config_state"}
        for field in allowed_fields:
            if field in updates:
                entry[field] = updates[field]

        # Re-extract requirements if config_state changed
        if "config_state" in updates:
            requirements = TemplateStore.extract_requirements(updates["config_state"])
            entry["requirements"] = [r.model_dump() for r in requirements]

        entry["updated_at"] = _now_iso()
        store["templates"][template_id] = entry
        _save(store)
        return entry

    @staticmethod
    def delete_template(template_id: str) -> bool:
        store = _load()
        if template_id not in store["templates"]:
            return False
        del store["templates"][template_id]
        _save(store)
        return True

    @staticmethod
    def increment_usage(template_id: str) -> None:
        store = _load()
        entry = store["templates"].get(template_id)
        if entry:
            entry["usage_count"] = entry.get("usage_count", 0) + 1
            entry["updated_at"] = _now_iso()
            store["templates"][template_id] = entry
            _save(store)

    @staticmethod
    def extract_requirements(config_state: dict) -> list[TemplateRequirement]:
        requirements = []

        # Check if any input has plugin="database"
        inputs = config_state.get("inputs", [])
        has_database = any(
            inp.get("plugin") == "database"
            for inp in inputs
        )
        if has_database:
            requirements.append(TemplateRequirement(
                type="database",
                description="Requires a configured database connection",
            ))

        # Check if any processor uses AI (python processor may use AI libraries)
        processors = config_state.get("processors", [])
        has_ai = any(
            "ai" in proc.get("name", "").lower()
            or "ai" in proc.get("sql", "").lower()
            or "ai" in proc.get("script", "").lower()
            for proc in processors
        )
        if has_ai:
            requirements.append(TemplateRequirement(
                type="ai",
                description="Requires AI service configuration",
            ))

        # Check input file formats
        input_formats = set()
        for inp in inputs:
            plugin = inp.get("plugin", "")
            if plugin and plugin != "database":
                input_formats.add(plugin)
        if input_formats:
            formats_str = ", ".join(sorted(input_formats))
            requirements.append(TemplateRequirement(
                type="input_format",
                description=f"Supports input formats: {formats_str}",
            ))

        return requirements


def ensure_builtin_templates() -> None:
    """Load built-in templates from configforge/templates/ if not already present."""
    store = _load()
    existing_ids = set(store["templates"].keys())

    if not os.path.isdir(TEMPLATES_DIR):
        logger.warning("Built-in templates directory not found: %s", TEMPLATES_DIR)
        return

    for path in sorted(glob.glob(os.path.join(TEMPLATES_DIR, "*.json"))):
        filename = os.path.basename(path)
        try:
            with open(path, encoding="utf-8") as f:
                builtin = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load built-in template %s: %s", filename, e)
            continue

        builtin_id = builtin.get("id", "")
        if builtin_id and builtin_id in existing_ids:
            continue

        # Create via store to get proper requirements extraction and timestamps
        entry = TemplateStore.create_template(
            name=builtin.get("name", ""),
            description=builtin.get("description", ""),
            category=builtin.get("category", "general"),
            tags=builtin.get("tags", []),
            config_state=builtin.get("config_state", {}),
            author=builtin.get("author", "ConfigForge"),
            is_official=True,
        )

        # Override the generated ID with the built-in ID if provided
        if builtin_id and builtin_id != entry["id"]:
            store = _load()
            store["templates"][builtin_id] = store["templates"].pop(entry["id"])
            store["templates"][builtin_id]["id"] = builtin_id
            _save(store)

        logger.info("Loaded built-in template: %s", builtin.get("name", filename))
