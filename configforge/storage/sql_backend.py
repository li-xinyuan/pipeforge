"""通用 SQL 存储后端实现 (T-5E-03)。

为每个 Protocol 提供 SQL 实现，使用 SQLAlchemy 2.0 Core API。
通过 `configforge.storage.sql_schema.get_engine()` 自动适配 SQLite / PostgreSQL。

类名保留 `Sqlite*Store` 前缀以保持向后兼容（T-5E-02 既有引用与测试不变），
但实现本身是方言无关的——SQLAlchemy Core 根据 URL 自动选择方言。

密码/密钥加密复用现有 Fernet cipher（与 JSON 后端兼容，迁移无需重新加密）。
用户密码哈希复用现有 user_store 的哈希函数（bcrypt/sha256）。

设计要点：
- 连接字符串构建逻辑（build_connection_string）是纯逻辑，委托给现有 ConnectionStore
- count_references 需要读取 configs（仍为 JSON），委托给现有 ConnectionStore
- T-5E-04: SqliteScheduleStore CRUD 操作同步注册/移除 BackgroundScheduler 任务，
  与 JSON 后端行为一致。调度器管理通过 scheduler._register_job / _unregister_job
  纯函数实现，不涉及持久化。
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, insert, select, update

from configforge.services.connection_store import ConnectionStore
from configforge.services.user_store import (
    _hash_password as _hash_pw,
    _verify_password as _verify_pw,
)
from configforge.storage.sql_schema import (
    audit_log_table,
    connections_table,
    get_engine,
    schedules_table,
    settings_table,
    templates_table,
    users_table,
)
from configforge.utils.crypto import get_cipher

_logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _try_register_job(schedule_dict: dict) -> None:
    """T-5E-04: Best-effort 注册调度任务到 BackgroundScheduler。

    任务已持久化到数据库，注册失败时只记录日志不抛异常。
    下次 start_scheduler() 会从 DB 重新加载并注册。
    """
    try:
        from configforge.scheduler import _register_job
        _register_job(schedule_dict)
    except Exception as e:
        _logger.warning(
            "Failed to register scheduler job %s: %s (will retry on next start_scheduler)",
            schedule_dict.get("id"), e,
        )


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    return json.loads(value)


# ---------------------------------------------------------------------------
# ConnectionStore
# ---------------------------------------------------------------------------


class SqliteConnectionStore:
    """SQL 后端 — 数据库连接存储。"""

    def _summarize(self, row: dict) -> dict:
        """将数据库行转换为 API 返回的摘要格式（与 JSON 后端一致）。"""
        host = row.get("file_path") or row.get("host") or ""
        result = {
            "id": row["id"],
            "name": row["name"],
            "db_type": row["db_type"],
            "host": host,
            "passwordSet": bool(row.get("password", "")),
            "verified": bool(row.get("verified", 0)),
            "createdAt": row.get("created_at", ""),
            "updatedAt": row.get("updated_at", ""),
        }
        if row.get("db_type") != "sqlite":
            result["port"] = row.get("port")
            result["database"] = row.get("database")
            result["username"] = row.get("username")
        return result

    def _get_row(self, conn_id: str) -> dict | None:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                select(connections_table).where(connections_table.c.id == conn_id)
            ).fetchone()
            if result is None:
                return None
            return dict(result._mapping)

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        cipher = get_cipher()
        conn_id = uuid.uuid4().hex[:16]
        password = data.get("password", "")
        encrypted = cipher.encrypt(password.encode()).decode() if password else ""

        now = _now_iso()
        row = {
            "id": conn_id,
            "name": data["name"],
            "db_type": data["db_type"],
            "verified": 0,
            "created_at": now,
            "updated_at": now,
        }
        if data["db_type"] == "sqlite":
            row["file_path"] = data.get("file_path", "")
        else:
            row["host"] = data.get("host", "")
            row["port"] = int(data.get("port", 3306))
            row["database"] = data.get("database", "")
            row["username"] = data.get("username", "")
            row["password"] = encrypted

        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(insert(connections_table).values(row))
        return self._summarize(row)

    def list_all(self) -> list[dict[str, Any]]:
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(select(connections_table)).fetchall()
        return [self._summarize(dict(r._mapping)) for r in rows]

    def get(self, conn_id: str) -> dict[str, Any] | None:
        row = self._get_row(conn_id)
        if not row:
            return None
        return self._summarize(row)

    def get_with_plaintext_password(self, conn_id: str) -> dict[str, Any] | None:
        row = self._get_row(conn_id)
        if not row:
            return None
        entry = dict(row)
        if entry.get("password"):
            cipher = get_cipher()
            entry["password"] = cipher.decrypt(entry["password"].encode()).decode()
        return entry

    def update(self, conn_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        row = self._get_row(conn_id)
        if not row:
            return None

        updates: dict[str, Any] = {"updated_at": _now_iso()}
        for field in ("name", "host", "port", "database", "username", "file_path"):
            if field in data:
                updates[field] = data[field]
        if "password" in data and data["password"]:
            cipher = get_cipher()
            updates["password"] = cipher.encrypt(data["password"].encode()).decode()

        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                update(connections_table)
                .where(connections_table.c.id == conn_id)
                .values(updates)
            )
        # Return updated summary
        return self.get(conn_id)

    def delete(self, conn_id: str) -> bool:
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(
                delete(connections_table).where(connections_table.c.id == conn_id)
            )
        return result.rowcount > 0

    def build_connection_string(self, entry: dict[str, Any]) -> str:
        # 纯逻辑，委托给现有实现（与 JSON 后端行为一致）
        return ConnectionStore.build_connection_string(entry)

    def count_references(self, conn_id: str) -> list[str]:
        # configs 仍为 JSON 存储，委托给现有实现
        return ConnectionStore.count_references(conn_id)

    def update_verified(self, conn_id: str, verified: bool) -> None:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                update(connections_table)
                .where(connections_table.c.id == conn_id)
                .values(verified=1 if verified else 0, updated_at=_now_iso())
            )


# ---------------------------------------------------------------------------
# TemplateStore
# ---------------------------------------------------------------------------


class SqliteTemplateStore:
    """SQL 后端 — 配置模板存储。"""

    def _row_to_dict(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row.get("description", ""),
            "category": row.get("category", ""),
            "tags": _json_loads(row.get("tags", "[]"), []),
            "author": row.get("author", ""),
            "version": row.get("version", "1.0"),
            "config_state": _json_loads(row.get("config_state", "{}"), {}),
            "requirements": _json_loads(row.get("requirements", "[]"), []),
            "usage_count": row.get("usage_count", 0),
            "is_official": bool(row.get("is_official", 0)),
            "created_at": row.get("created_at", ""),
            "updated_at": row.get("updated_at", ""),
        }

    def list_templates(
        self, category: str | None = None, search: str | None = None,
    ) -> list[dict[str, Any]]:
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(select(templates_table)).fetchall()

        templates = [self._row_to_dict(dict(r._mapping)) for r in rows]

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

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                select(templates_table).where(templates_table.c.id == template_id)
            ).fetchone()
        if result is None:
            return None
        return self._row_to_dict(dict(result._mapping))

    def create_template(
        self, name: str, description: str, category: str, tags: list[str],
        config_state: dict[str, Any], author: str = "", is_official: bool = False,
    ) -> dict[str, Any]:
        # Reuse existing extract_requirements logic
        from configforge.services.template_store import TemplateStore
        requirements = TemplateStore.extract_requirements(config_state)

        template_id = uuid.uuid4().hex[:12]
        now = _now_iso()
        row = {
            "id": template_id,
            "name": name,
            "description": description,
            "category": category,
            "tags": _json_dumps(tags),
            "author": author,
            "version": "1.0",
            "config_state": _json_dumps(config_state),
            "requirements": _json_dumps([r.model_dump() for r in requirements]),
            "usage_count": 0,
            "is_official": 1 if is_official else 0,
            "created_at": now,
            "updated_at": now,
        }

        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(insert(templates_table).values(row))
        return self._row_to_dict(row)

    def update_template(self, template_id: str, **updates: Any) -> dict[str, Any] | None:
        existing = self.get_template(template_id)
        if not existing:
            return None

        db_updates: dict[str, Any] = {"updated_at": _now_iso()}
        allowed_fields = {"name", "description", "category", "author", "version"}
        for field in allowed_fields:
            if field in updates:
                db_updates[field] = updates[field]
        if "tags" in updates:
            db_updates["tags"] = _json_dumps(updates["tags"])
        if "config_state" in updates:
            db_updates["config_state"] = _json_dumps(updates["config_state"])
            # Re-extract requirements
            from configforge.services.template_store import TemplateStore
            requirements = TemplateStore.extract_requirements(updates["config_state"])
            db_updates["requirements"] = _json_dumps([r.model_dump() for r in requirements])

        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                update(templates_table)
                .where(templates_table.c.id == template_id)
                .values(db_updates)
            )
        return self.get_template(template_id)

    def delete_template(self, template_id: str) -> bool:
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(
                delete(templates_table).where(templates_table.c.id == template_id)
            )
        return result.rowcount > 0

    def increment_usage(self, template_id: str) -> None:
        engine = get_engine()
        with engine.begin() as conn:
            # Atomic increment
            conn.execute(
                update(templates_table)
                .where(templates_table.c.id == template_id)
                .values(
                    usage_count=templates_table.c.usage_count + 1,
                    updated_at=_now_iso(),
                )
            )


# ---------------------------------------------------------------------------
# UserStore
# ---------------------------------------------------------------------------


class SqliteUserStore:
    """SQL 后端 — 用户存储，复用现有密码哈希函数。"""

    def _row_to_user(self, row: dict, include_sensitive: bool = False):
        """Convert DB row to User model (without password hash)."""
        from configforge.models.user import User
        return User(
            id=row["id"],
            username=row["username"],
            role=row.get("role", "editor"),
            created_at=row.get("created_at", ""),
            must_change_password=bool(row.get("must_change_password", 0)),
        )

    def ensure_default_admin(self) -> None:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                select(users_table).where(users_table.c.username == "admin")
            ).fetchone()
        if result is not None:
            return  # Admin already exists

        admin_id = uuid.uuid4().hex[:16]
        with engine.begin() as conn:
            conn.execute(insert(users_table).values(
                id=admin_id,
                username="admin",
                role="admin",
                password_hash=_hash_pw("admin123"),
                created_at=_now_iso(),
                must_change_password=1,
            ))

    def create_user(self, username: str, password: str, role: str = "editor") -> Any:
        engine = get_engine()
        # Check username uniqueness
        with engine.connect() as conn:
            existing = conn.execute(
                select(users_table).where(users_table.c.username == username)
            ).fetchone()
        if existing is not None:
            return None

        user_id = uuid.uuid4().hex[:16]
        now = _now_iso()
        with engine.begin() as conn:
            conn.execute(insert(users_table).values(
                id=user_id,
                username=username,
                role=role,
                password_hash=_hash_pw(password),
                created_at=now,
            ))

        from configforge.models.user import User
        return User(id=user_id, username=username, role=role, created_at=now)

    def authenticate(self, username: str, password: str) -> Any:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                select(users_table).where(users_table.c.username == username)
            ).fetchone()
        if result is None:
            return None
        row = dict(result._mapping)
        if not _verify_pw(password, row.get("password_hash", "")):
            return None
        return self._row_to_user(row)

    def list_users(self) -> list[Any]:
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(select(users_table)).fetchall()
        return [self._row_to_user(dict(r._mapping)) for r in rows]

    def delete_user(self, user_id: str) -> bool:
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(
                delete(users_table).where(users_table.c.id == user_id)
            )
        return result.rowcount > 0

    def get_user_by_id(self, user_id: str) -> Any:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                select(users_table).where(users_table.c.id == user_id)
            ).fetchone()
        if result is None:
            return None
        return self._row_to_user(dict(result._mapping))

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                select(users_table).where(users_table.c.id == user_id)
            ).fetchone()
        if result is None:
            return False
        row = dict(result._mapping)
        if not _verify_pw(old_password, row.get("password_hash", "")):
            return False

        with engine.begin() as conn:
            conn.execute(
                update(users_table)
                .where(users_table.c.id == user_id)
                .values(
                    password_hash=_hash_pw(new_password),
                    must_change_password=0,
                )
            )
        return True


# ---------------------------------------------------------------------------
# AuditStore
# ---------------------------------------------------------------------------


class SqliteAuditStore:
    """SQL 后端 — 审计日志存储。"""

    MAX_ENTRIES = 10000

    def log_audit(
        self, action: str, target_type: str, target_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(insert(audit_log_table).values(
                timestamp=_now_iso(),
                action=action,
                target_type=target_type,
                target_id=target_id,
                details=_json_dumps(details or {}),
            ))
            # Trim old entries if too many
            count = conn.execute(
                select(func.count()).select_from(audit_log_table)
            ).scalar()
            if count and count > self.MAX_ENTRIES:
                # Delete oldest entries beyond MAX_ENTRIES
                excess = count - self.MAX_ENTRIES
                old_ids = conn.execute(
                    select(audit_log_table.c.id)
                    .order_by(audit_log_table.c.id)
                    .limit(excess)
                ).scalars().all()
                if old_ids:
                    conn.execute(
                        delete(audit_log_table).where(audit_log_table.c.id.in_(old_ids))
                    )

    def get_audit_log(
        self, target_type: str | None = None, action: str | None = None,
        limit: int = 100, user: str | None = None,
        start_time: str | None = None, end_time: str | None = None,
    ) -> list[dict[str, Any]]:
        engine = get_engine()
        query = select(audit_log_table)

        if target_type:
            query = query.where(audit_log_table.c.target_type == target_type)
        if action:
            query = query.where(audit_log_table.c.action == action)
        if start_time:
            query = query.where(audit_log_table.c.timestamp >= start_time)
        if end_time:
            query = query.where(audit_log_table.c.timestamp <= end_time)
        # Order by timestamp descending, then we reverse at the end
        query = query.order_by(audit_log_table.c.id.desc()).limit(limit)

        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()

        entries = []
        for r in rows:
            row = dict(r._mapping)
            entry = {
                "timestamp": row["timestamp"],
                "action": row["action"],
                "target_type": row["target_type"],
                "target_id": row["target_id"],
                "details": _json_loads(row.get("details", "{}"), {}),
            }
            # User filter (applied after load since it checks both target_id and details.user)
            if user:
                if entry["target_id"] != user and entry["details"].get("user") != user:
                    continue
            entries.append(entry)

        # Reverse to chronological order (oldest first, matching JSON backend)
        entries.reverse()
        return entries


# ---------------------------------------------------------------------------
# SettingsStore
# ---------------------------------------------------------------------------


class SqliteSettingsStore:
    """SQL 后端 — 通用设置存储（SMTP / AI）。

    存储为 JSON 文本（含 Fernet 加密的密钥），加载时还原为 Pydantic 模型。
    与 JSON 后端行为一致，确保调用方无需感知后端差异。
    """

    def __init__(self, kind: str = "smtp"):
        self._kind = kind

    def _get_model_class(self):
        if self._kind == "smtp":
            from configforge.services.notifier.smtp_settings import SmtpSettings
            return SmtpSettings
        elif self._kind == "ai":
            from configforge.models.ai import AiSettings
            return AiSettings
        raise ValueError(f"Unknown settings kind: {self._kind}")

    def load_settings(self) -> Any:
        model_cls = self._get_model_class()
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                select(settings_table).where(settings_table.c.kind == self._kind)
            ).fetchone()

        if result is None:
            return model_cls()  # Return defaults

        row = dict(result._mapping)
        raw = _json_loads(row.get("data", "{}"), {})
        # schema_version is storage metadata, not a model field
        raw.pop("schema_version", None)

        # Decrypt sensitive field
        cipher = get_cipher()
        if self._kind == "smtp" and raw.get("password"):
            try:
                raw["password"] = cipher.decrypt(raw["password"].encode()).decode()
            except Exception:
                raw["password"] = ""
        elif self._kind == "ai" and raw.get("api_key"):
            try:
                raw["api_key"] = cipher.decrypt(raw["api_key"].encode()).decode()
            except Exception:
                raw["api_key"] = ""

        return model_cls(**raw)

    def save_settings(self, settings: Any) -> None:
        data = settings.model_dump()
        cipher = get_cipher()

        # Encrypt sensitive field
        if self._kind == "smtp" and data.get("password"):
            data["password"] = cipher.encrypt(data["password"].encode()).decode()
        elif self._kind == "ai" and data.get("api_key"):
            data["api_key"] = cipher.encrypt(data["api_key"].encode()).decode()

        engine = get_engine()
        now = _now_iso()
        # Upsert: try insert, on conflict update
        with engine.begin() as conn:
            existing = conn.execute(
                select(settings_table).where(settings_table.c.kind == self._kind)
            ).fetchone()
            if existing is None:
                conn.execute(insert(settings_table).values(
                    kind=self._kind,
                    data=_json_dumps(data),
                    updated_at=now,
                ))
            else:
                conn.execute(
                    update(settings_table)
                    .where(settings_table.c.kind == self._kind)
                    .values(data=_json_dumps(data), updated_at=now)
                )


# ---------------------------------------------------------------------------
# ScheduleStore
# ---------------------------------------------------------------------------


class SqliteScheduleStore:
    """SQL 后端 — 定时调度存储。

    T-5E-04: CRUD 操作同步注册/移除 BackgroundScheduler 任务，
    与 JSON 后端行为一致。调度器管理通过 scheduler._register_job / _unregister_job
    纯函数实现，不涉及持久化。
    """

    _SUPPORTED_UPDATE_KEYS = {"cron_expression", "description", "retry_count", "retry_interval"}

    def _row_to_dict(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "config_id": row["config_id"],
            "cron_expression": row["cron_expression"],
            "description": row.get("description", ""),
            "retry_count": row.get("retry_count", 0),
            "retry_interval": row.get("retry_interval", 300),
            "enabled": bool(row.get("enabled", 1)),
            "created_at": row.get("created_at", ""),
            "last_run_at": row.get("last_run_at", "") or None,
            "last_run_status": row.get("last_run_status", "") or None,
        }

    def list_schedules(self) -> list[dict[str, Any]]:
        engine = get_engine()
        with engine.connect() as conn:
            rows = conn.execute(select(schedules_table)).fetchall()
        return [self._row_to_dict(dict(r._mapping)) for r in rows]

    def add_schedule(self, schedule: dict[str, Any]) -> dict[str, Any]:
        # Validate cron expression
        from configforge.scheduler import _validate_cron
        _validate_cron(schedule["cron_expression"])

        schedule_id = uuid.uuid4().hex
        now = _now_iso()
        row = {
            "id": schedule_id,
            "config_id": schedule["config_id"],
            "cron_expression": schedule["cron_expression"],
            "description": schedule.get("description", ""),
            "retry_count": schedule.get("retry_count", 0),
            "retry_interval": schedule.get("retry_interval", 300),
            "enabled": 1,
            "created_at": now,
        }

        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(insert(schedules_table).values(row))
        result = self._row_to_dict(row)
        # T-5E-04: 同步注册 BackgroundScheduler 任务（与 JSON 后端行为一致）
        _try_register_job(result)
        return result

    def update_schedule(self, schedule_id: str, **updates: Any) -> dict[str, Any] | None:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                select(schedules_table).where(schedules_table.c.id == schedule_id)
            ).fetchone()
        if result is None:
            return None

        # Validate cron if being updated
        if "cron_expression" in updates and updates["cron_expression"] is not None:
            from configforge.scheduler import _validate_cron
            _validate_cron(updates["cron_expression"])

        db_updates: dict[str, Any] = {}
        for key in self._SUPPORTED_UPDATE_KEYS:
            if key in updates and updates[key] is not None:
                db_updates[key] = updates[key]

        if db_updates:
            with engine.begin() as conn:
                conn.execute(
                    update(schedules_table)
                    .where(schedules_table.c.id == schedule_id)
                    .values(db_updates)
                )

        # Return updated schedule
        with engine.connect() as conn:
            result = conn.execute(
                select(schedules_table).where(schedules_table.c.id == schedule_id)
            ).fetchone()
        if result is None:
            return None
        updated = self._row_to_dict(dict(result._mapping))
        # T-5E-04: 重新注册 BackgroundScheduler 任务（仅当 enabled 时，disabled 的任务无 job）
        if updated.get("enabled", True):
            from configforge.scheduler import _unregister_job
            _unregister_job(schedule_id)
            _try_register_job(updated)
        return updated

    def remove_schedule(self, schedule_id: str) -> bool:
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(
                delete(schedules_table).where(schedules_table.c.id == schedule_id)
            )
        removed = result.rowcount > 0
        if removed:
            # T-5E-04: 同步移除 BackgroundScheduler 任务
            from configforge.scheduler import _unregister_job
            _unregister_job(schedule_id)
        return removed

    def toggle_schedule(self, schedule_id: str) -> dict[str, Any] | None:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                select(schedules_table).where(schedules_table.c.id == schedule_id)
            ).fetchone()
        if result is None:
            return None

        row = dict(result._mapping)
        new_enabled = 0 if row.get("enabled", 1) else 1
        with engine.begin() as conn:
            conn.execute(
                update(schedules_table)
                .where(schedules_table.c.id == schedule_id)
                .values(enabled=new_enabled)
            )

        row["enabled"] = new_enabled
        result_dict = self._row_to_dict(row)
        # T-5E-04: 根据新状态注册/移除 BackgroundScheduler 任务
        from configforge.scheduler import _unregister_job
        if result_dict["enabled"]:
            _try_register_job(result_dict)
        else:
            _unregister_job(schedule_id)
        return result_dict

    def update_last_run(self, schedule_id: str, status: str) -> None:
        """T-5E-04: 更新调度任务的最后执行时间和状态。"""
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                update(schedules_table)
                .where(schedules_table.c.id == schedule_id)
                .values(
                    last_run_at=_now_iso(),
                    last_run_status=status,
                )
            )
