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
from configforge.services import config_store as _config_store
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


class JsonConfigStore:
    """JSON 后端 — Pipeline 配置存储 (P1-5 落地 ConfigStoreProtocol)。

    实现 ConfigStoreProtocol 的 7 个方法，封装 state.json / index.json / 版本目录
    的持久化细节。委托给 services.config_store 模块的函数与常量，保持与现有
    函数式 API 一致；通过模块引用（而非 from...import 常量）确保测试 patch
    config_store.CONFIGS_DIR / INDEX_PATH 生效。

    职责边界：
    - Store：state.json + index.json + 版本目录的 CRUD（不生成 YAML）
    - Service（ConfigService）：WizardState 校验 / YAML 生成 / 审计 / 业务编排
    """

    def list_configs(self, search: str = "") -> list[dict[str, Any]]:
        """列出配置索引（搜索过滤后的全量列表，不排序不分页）。

        搜索范围：scene_name / description / name / tags。
        排序与分页由 ConfigService 负责。
        """
        index = _config_store.load_index()

        if search:
            q = search.lower()
            index = [
                e for e in index
                if q in e.get("scene_name", "").lower()
                or q in e.get("description", "").lower()
                or q in e.get("name", "").lower()
                or any(q in t for t in e.get("tags", []))
            ]
        return index

    def get_config(self, config_id: str) -> dict[str, Any] | None:
        """读取配置的完整 state.json。不存在返回 None。"""
        import os

        from configforge.utils.file_lock import read_json_locked

        state_path = os.path.join(_config_store.CONFIGS_DIR, f"{config_id}.state.json")
        if not os.path.exists(state_path):
            return None
        return read_json_locked(state_path)

    def save_config(
        self, config_id: str, state: dict[str, Any], is_update: bool = False,
    ) -> dict[str, Any]:
        """保存配置：版本归档 + 写 state.json + 更新 index。返回 index entry。

        注意：不写 YAML 文件（由 ConfigService 调用 build_yaml 后单独写入）。
        state dict 应已清除 file_id、设置 uploaded_files={} 等持久化字段。
        """
        import os
        import shutil
        from datetime import UTC, datetime

        from configforge.utils.file_lock import write_json_locked

        now_str = datetime.now(UTC).isoformat()
        configs_dir = _config_store.CONFIGS_DIR
        versions_dir = os.path.join(configs_dir, config_id)

        if is_update:
            index = _config_store.load_index()
            old_entry = next((e for e in index if e.get("id") == config_id), None)
            old_version = old_entry.get("current_version", 1) if old_entry else 1
            created_at = old_entry.get("created_at", now_str) if old_entry else now_str

            # Move current files to version directory before overwriting
            os.makedirs(versions_dir, exist_ok=True)
            for suffix in ("state.json", "yaml"):
                current_path = os.path.join(configs_dir, f"{config_id}.{suffix}")
                target_path = os.path.join(versions_dir, f"v{old_version}.{suffix}")
                if os.path.exists(current_path):
                    shutil.move(current_path, target_path)
            current_version = old_version + 1
        else:
            created_at = now_str
            current_version = 1

        state_path = os.path.join(configs_dir, f"{config_id}.state.json")
        state["_saved_at"] = now_str
        write_json_locked(state_path, state)

        # Build index entry from state dict
        scene = state.get("scene") or {}
        inputs = state.get("inputs") or []
        output = state.get("output") or {}
        entry = {
            "id": config_id,
            "scene_name": scene.get("name", "未命名配置"),
            "description": scene.get("description", ""),
            "input_count": len(inputs),
            "output_type": output.get("plugin", ""),
            "version": scene.get("version", "1.0"),
            "updated_at": now_str,
            "current_version": current_version,
            "created_at": created_at,
            "inputs": [
                {
                    "name": i.get("name", ""),
                    "param_key": i.get("param_key", "") or i.get("paramKey", ""),
                    "plugin": i.get("plugin", ""),
                }
                for i in inputs
            ],
            "tags": scene.get("tags", []),
            "input_types": list(dict.fromkeys(i.get("plugin", "") for i in inputs)),
        }

        index = _config_store.load_index()
        existing = next(
            (i for i, e in enumerate(index) if e.get("id") == config_id), None
        )
        if existing is not None:
            index[existing] = entry
        else:
            index.append(entry)
        _config_store.save_index(index)

        return entry

    def delete_config(self, config_id: str) -> bool:
        """删除配置：从 index 移除 + 删 state.json + 删 yaml + 删版本目录。"""
        import os
        import shutil

        index = _config_store.load_index()
        entry = next((e for e in index if e.get("id") == config_id), None)
        if entry is None:
            return False

        index = [e for e in index if e.get("id") != config_id]
        _config_store.save_index(index)

        configs_dir = _config_store.CONFIGS_DIR
        for ext in (".yaml", ".state.json"):
            p = os.path.join(configs_dir, f"{config_id}{ext}")
            if os.path.exists(p):
                os.remove(p)

        versions_dir = os.path.join(configs_dir, config_id)
        if os.path.isdir(versions_dir):
            shutil.rmtree(versions_dir)
        return True

    def list_versions(self, config_id: str) -> list[dict[str, Any]]:
        """列出配置的版本历史，返回版本元信息 dict 列表。"""
        versions = _config_store.list_version_files(config_id)
        result: list[dict[str, Any]] = []
        for v in versions:
            state = _config_store.read_version_state(config_id, v)
            if state is None:
                continue
            scene = state.get("scene") or {}
            output = state.get("output") or {}
            result.append({
                "version": v,
                "scene_version": scene.get("version", "1.0"),
                "change_summary": state.get("change_summary", ""),
                "created_at": state.get("_saved_at", ""),
                "input_count": len(state.get("inputs", [])),
                "processor_count": len(state.get("processors", [])),
                "output_type": output.get("plugin", ""),
            })
        return result

    def get_version(self, config_id: str, version: int) -> dict[str, Any] | None:
        """读取指定版本的 state。不存在返回 None。"""
        return _config_store.read_version_state(config_id, version)

    def save_version(self, config_id: str, version: int, state: dict[str, Any]) -> None:
        """写入一个版本快照到 versions 目录。"""
        import os

        from configforge.utils.file_lock import write_json_locked

        versions_dir = os.path.join(_config_store.CONFIGS_DIR, config_id)
        os.makedirs(versions_dir, exist_ok=True)
        path = os.path.join(versions_dir, f"v{version}.state.json")
        write_json_locked(path, state)
