"""JSON 文件后端实现 (T-5E-01)。

委托给现有的 Store 类/模块函数，不修改任何现有代码。
这是默认后端，行为与现有实现完全一致。
"""

from __future__ import annotations

from typing import Any

from configforge.scheduler import (
    add_schedule as _sched_add_schedule,
)
from configforge.scheduler import (
    list_schedules as _sched_list_schedules,
)
from configforge.scheduler import (
    remove_schedule as _sched_remove_schedule,
)
from configforge.scheduler import (
    toggle_schedule as _sched_toggle_schedule,
)
from configforge.scheduler import (
    update_schedule as _sched_update_schedule,
)
from configforge.services.audit_logger import (
    get_audit_log as _get_audit_log,
)
from configforge.services.audit_logger import (
    log_audit as _log_audit,
)
from configforge.services.connection_store import ConnectionStore
from configforge.services.template_store import TemplateStore
from configforge.services.user_store import (
    authenticate as _authenticate,
)
from configforge.services.user_store import (
    change_password as _change_password,
)
from configforge.services.user_store import (
    create_user as _create_user,
)
from configforge.services.user_store import (
    delete_user as _delete_user,
)
from configforge.services.user_store import (
    ensure_default_admin as _ensure_default_admin,
)
from configforge.services.user_store import (
    get_user_by_id as _get_user_by_id,
)
from configforge.services.user_store import (
    list_users as _list_users,
)


class JsonConnectionStore:
    """JSON 后端 — 数据库连接存储，委托给现有 ConnectionStore。"""

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        return ConnectionStore.create(data)

    def list_all(self) -> list[dict[str, Any]]:
        return ConnectionStore.list_all()

    def get(self, conn_id: str) -> dict[str, Any] | None:
        return ConnectionStore.get(conn_id)

    def get_with_plaintext_password(self, conn_id: str) -> dict[str, Any] | None:
        return ConnectionStore.get_with_plaintext_password(conn_id)

    def update(self, conn_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        return ConnectionStore.update(conn_id, data)

    def delete(self, conn_id: str) -> bool:
        return ConnectionStore.delete(conn_id)

    def build_connection_string(self, entry: dict[str, Any]) -> str:
        return ConnectionStore.build_connection_string(entry)

    def count_references(self, conn_id: str) -> list[str]:
        return ConnectionStore.count_references(conn_id)

    def update_verified(self, conn_id: str, verified: bool) -> None:
        ConnectionStore._update_verified(conn_id, verified)


class JsonTemplateStore:
    """JSON 后端 — 配置模板存储，委托给现有 TemplateStore。"""

    def list_templates(
        self, category: str | None = None, search: str | None = None,
    ) -> list[dict[str, Any]]:
        return TemplateStore.list_templates(category, search)

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        return TemplateStore.get_template(template_id)

    def create_template(
        self, name: str, description: str, category: str, tags: list[str],
        config_state: dict[str, Any], author: str = "", is_official: bool = False,
    ) -> dict[str, Any]:
        return TemplateStore.create_template(
            name, description, category, tags, config_state, author, is_official,
        )

    def update_template(self, template_id: str, **updates: Any) -> dict[str, Any] | None:
        return TemplateStore.update_template(template_id, **updates)

    def delete_template(self, template_id: str) -> bool:
        return TemplateStore.delete_template(template_id)

    def increment_usage(self, template_id: str) -> None:
        TemplateStore.increment_usage(template_id)


class JsonUserStore:
    """JSON 后端 — 用户存储，委托给现有 user_store 模块。"""

    def ensure_default_admin(self) -> None:
        _ensure_default_admin()

    def create_user(self, username: str, password: str, role: str = "editor") -> Any:
        return _create_user(username, password, role)

    def authenticate(self, username: str, password: str) -> Any:
        return _authenticate(username, password)

    def list_users(self) -> list[Any]:
        return _list_users()

    def delete_user(self, user_id: str) -> bool:
        return _delete_user(user_id)

    def get_user_by_id(self, user_id: str) -> Any:
        return _get_user_by_id(user_id)

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        return _change_password(user_id, old_password, new_password)


class JsonScheduleStore:
    """JSON 后端 — 定时调度存储，委托给现有 scheduler 模块。

    注意：scheduler 模块的函数同时管理存储和 BackgroundScheduler 任务注册，
    因此此处的"存储"操作也会有调度器副作用。这是 T-5E-01 的过渡设计，
    T-5E-02（SQLite 后端）会进一步解耦存储与调度逻辑。
    """

    _SUPPORTED_UPDATE_KEYS = {"cron_expression", "description", "retry_count", "retry_interval"}

    def list_schedules(self) -> list[dict[str, Any]]:
        return [s.model_dump() for s in _sched_list_schedules()]

    def add_schedule(self, schedule: dict[str, Any]) -> dict[str, Any]:
        result = _sched_add_schedule(
            config_id=schedule["config_id"],
            cron_expression=schedule["cron_expression"],
            description=schedule.get("description", ""),
            retry_count=schedule.get("retry_count", 0),
            retry_interval=schedule.get("retry_interval", 300),
        )
        return result.model_dump()

    def update_schedule(self, schedule_id: str, **updates: Any) -> dict[str, Any] | None:
        # Filter to only supported keys (scheduler.update_schedule has specific kwargs)
        filtered = {k: v for k, v in updates.items() if k in self._SUPPORTED_UPDATE_KEYS}
        result = _sched_update_schedule(schedule_id, **filtered)
        return result.model_dump() if result else None

    def remove_schedule(self, schedule_id: str) -> bool:
        return _sched_remove_schedule(schedule_id)

    def toggle_schedule(self, schedule_id: str) -> dict[str, Any] | None:
        result = _sched_toggle_schedule(schedule_id)
        return result.model_dump() if result else None

    def update_last_run(self, schedule_id: str, status: str) -> None:
        """T-5E-04: 更新调度任务的最后执行时间和状态。

        直接写 schedules.json，不委托给 scheduler._update_schedule_last_run
        （后者会调用 store.update_last_run，导致无限递归）。
        """
        from datetime import UTC, datetime

        from configforge.scheduler import _load_schedules, _save_schedules

        schedules = _load_schedules()
        for s in schedules:
            if s.get("id") == schedule_id:
                s["last_run_at"] = datetime.now(UTC).isoformat()
                s["last_run_status"] = status
                break
        _save_schedules(schedules)


class JsonAuditStore:
    """JSON 后端 — 审计日志存储，委托给现有 audit_logger 模块。"""

    def log_audit(
        self, action: str, target_type: str, target_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        _log_audit(action, target_type, target_id, details)

    def get_audit_log(
        self, target_type: str | None = None, action: str | None = None,
        limit: int = 100, user: str | None = None,
        start_time: str | None = None, end_time: str | None = None,
    ) -> list[dict[str, Any]]:
        return _get_audit_log(target_type, action, limit, user, start_time, end_time)


class JsonSettingsStore:
    """JSON 后端 — 通用设置存储（SMTP / AI）。

    通过 kind 参数区分不同设置类型。
    """

    def __init__(self, kind: str = "smtp"):
        self._kind = kind

    def load_settings(self) -> Any:
        if self._kind == "smtp":
            from configforge.services.notifier.smtp_settings import load_settings
            return load_settings()
        elif self._kind == "ai":
            from configforge.services.ai.settings import load_settings
            return load_settings()
        raise ValueError(f"Unknown settings kind: {self._kind}")

    def save_settings(self, settings: Any) -> None:
        if self._kind == "smtp":
            from configforge.services.notifier.smtp_settings import save_settings
            save_settings(settings)
        elif self._kind == "ai":
            from configforge.services.ai.settings import save_settings
            save_settings(settings)
        else:
            raise ValueError(f"Unknown settings kind: {self._kind}")
