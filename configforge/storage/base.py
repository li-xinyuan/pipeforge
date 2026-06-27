"""存储层抽象接口定义 (T-5E-01)。

定义所有 Store 的 Protocol 接口，使后端实现可切换（JSON / SQLite / PostgreSQL）。
每个 Protocol 与现有 Store 的公开方法签名保持一致，确保向后兼容。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConfigStoreProtocol(Protocol):
    """Pipeline 配置存储接口。"""

    def list_configs(
        self, page: int = 1, page_size: int = 20,
        search: str = "", sort: str = "updated",
    ) -> dict[str, Any]:
        """分页列出配置，返回 {items, total, page, page_size}。"""
        ...

    def get_config(self, config_id: str) -> dict[str, Any] | None:
        """获取单个配置的完整 state。"""
        ...

    def save_config(self, config_id: str, state: dict[str, Any], is_update: bool = False) -> dict[str, Any]:
        """保存配置（新建或更新），返回 index entry。"""
        ...

    def delete_config(self, config_id: str) -> bool:
        """删除配置及其关联文件（state.json / yaml / 版本历史）。"""
        ...

    def list_versions(self, config_id: str) -> list[dict[str, Any]]:
        """列出配置的版本历史。"""
        ...

    def get_version(self, config_id: str, version: int) -> dict[str, Any] | None:
        """获取指定版本的 state。"""
        ...

    def save_version(self, config_id: str, version: int, state: dict[str, Any]) -> None:
        """保存一个版本快照。"""
        ...


@runtime_checkable
class ConnectionStoreProtocol(Protocol):
    """数据库连接存储接口。"""

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        ...

    def list_all(self) -> list[dict[str, Any]]:
        ...

    def get(self, conn_id: str) -> dict[str, Any] | None:
        ...

    def get_with_plaintext_password(self, conn_id: str) -> dict[str, Any] | None:
        ...

    def update(self, conn_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        ...

    def delete(self, conn_id: str) -> bool:
        ...

    def build_connection_string(self, entry: dict[str, Any]) -> str:
        ...

    def count_references(self, conn_id: str) -> list[str]:
        ...

    def update_verified(self, conn_id: str, verified: bool) -> None:
        ...


@runtime_checkable
class TemplateStoreProtocol(Protocol):
    """配置模板存储接口。"""

    def list_templates(
        self, category: str | None = None, search: str | None = None,
    ) -> list[dict[str, Any]]:
        ...

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        ...

    def create_template(
        self, name: str, description: str, category: str, tags: list[str],
        config_state: dict[str, Any], author: str = "", is_official: bool = False,
    ) -> dict[str, Any]:
        ...

    def update_template(self, template_id: str, **updates: Any) -> dict[str, Any] | None:
        ...

    def delete_template(self, template_id: str) -> bool:
        ...

    def increment_usage(self, template_id: str) -> None:
        ...


@runtime_checkable
class UserStoreProtocol(Protocol):
    """用户存储接口。"""

    def ensure_default_admin(self) -> None:
        ...

    def create_user(self, username: str, password: str, role: str = "editor") -> Any:
        ...

    def authenticate(self, username: str, password: str) -> Any:
        ...

    def list_users(self) -> list[Any]:
        ...

    def delete_user(self, user_id: str) -> bool:
        ...

    def get_user_by_id(self, user_id: str) -> Any:
        ...

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        ...


@runtime_checkable
class ScheduleStoreProtocol(Protocol):
    """定时调度存储接口。"""

    def list_schedules(self) -> list[dict[str, Any]]:
        ...

    def add_schedule(self, schedule: dict[str, Any]) -> dict[str, Any]:
        ...

    def update_schedule(self, schedule_id: str, **updates: Any) -> dict[str, Any] | None:
        ...

    def remove_schedule(self, schedule_id: str) -> bool:
        ...

    def toggle_schedule(self, schedule_id: str) -> dict[str, Any] | None:
        ...

    def update_last_run(self, schedule_id: str, status: str) -> None:
        """更新调度任务的最后执行时间和状态（T-5E-04）。"""
        ...


@runtime_checkable
class AuditStoreProtocol(Protocol):
    """审计日志存储接口。"""

    def log_audit(
        self, action: str, target_type: str, target_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        ...

    def get_audit_log(
        self, target_type: str | None = None, action: str | None = None,
        limit: int = 100, user: str | None = None,
        start_time: str | None = None, end_time: str | None = None,
    ) -> list[dict[str, Any]]:
        ...


@runtime_checkable
class SettingsStoreProtocol(Protocol):
    """通用设置存储接口（SMTP / AI 等）。"""

    def load_settings(self) -> dict[str, Any]:
        ...

    def save_settings(self, settings: dict[str, Any]) -> None:
        ...
