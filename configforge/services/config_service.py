"""Pipeline 配置业务编排服务 (P1-4c / P1-5)。

ConfigService 作为 API 层与存储层之间的业务编排层，承担：
- WizardState 校验与序列化
- YAML 生成与文件写入
- 版本归档、回滚、diff 等业务规则
- 审计日志记录

职责边界：
- Store（ConfigStoreProtocol）：state.json / index.json / 版本目录的 CRUD
- Service（本模块）：业务编排 + YAML + 审计
- API（api/configs.py）：HTTP 装配 + 错误转换

通过依赖注入 ConfigStoreProtocol，使存储后端可切换（JSON / 未来的 SQLite）。
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import yaml

from configforge.models.user import User
from configforge.models.wizard import (
    ConfigMeta,
    ConfigVersionMeta,
    ExecuteConfigRequest,
    SaveConfigRequest,
    SaveConfigResponse,
    WizardState,
)
from configforge.services.execution_service import (
    ExecutionContext,
)
from configforge.services.execution_service import (
    execute as execute_service,
)
from configforge.services.yaml_builder import build_yaml
from configforge.storage import get_audit_store
from configforge.storage.base import AuditStoreProtocol, ConfigStoreProtocol
from configforge.utils.migration import ensure_schema_version

logger = logging.getLogger(__name__)


def _build_last_execution_map(config_ids: list[str]) -> dict[str, dict]:
    """从 execution index 构建 config_id → 最近执行记录的映射。

    execution index 按 started_at desc 排列（insert(0, ...)），所以第一条
    匹配的记录即为该 config 的最近一次执行。
    """
    if not config_ids:
        return {}
    from configforge.services.execution_store import EXEC_INDEX
    from configforge.utils.file_lock import read_json_locked
    if not os.path.exists(EXEC_INDEX):
        return {}
    index = read_json_locked(EXEC_INDEX)
    id_set = set(config_ids)
    result: dict[str, dict] = {}
    for entry in index:
        cid = entry.get("config_id", "")
        if cid in id_set and cid not in result:
            result[cid] = entry
    return result


def _deep_diff(old: Any, new: Any, path: str, result: dict) -> None:
    """Recursively compare two values and collect structured diff into result."""
    if old == new:
        return

    if isinstance(old, dict) and isinstance(new, dict):
        all_keys = set(old.keys()) | set(new.keys())
        for key in sorted(all_keys):
            child_path = f"{path}.{key}" if path else key
            if key not in old:
                result["added"].append({"path": child_path, "value": new[key]})
            elif key not in new:
                result["removed"].append({"path": child_path, "value": old[key]})
            else:
                _deep_diff(old[key], new[key], child_path, result)
        return

    if isinstance(old, list) and isinstance(new, list):
        max_len = max(len(old), len(new))
        for i in range(max_len):
            child_path = f"{path}[{i}]"
            if i >= len(old):
                result["added"].append({"path": child_path, "value": new[i]})
            elif i >= len(new):
                result["removed"].append({"path": child_path, "value": old[i]})
            else:
                _deep_diff(old[i], new[i], child_path, result)
        return

    result["modified"].append({"path": path, "old": old, "new": new})


def _diff_states(state1: dict, state2: dict) -> dict:
    """Diff two config state dicts. Returns structured changes with dot-notation paths."""
    result: dict = {"added": [], "removed": [], "modified": []}
    _deep_diff(state1, state2, "", result)
    return result


def _serialize_state_for_export(state_dict: dict) -> dict:
    """Strip internal fields before exporting state."""
    return {k: v for k, v in state_dict.items() if k not in ("_saved_at", "change_summary", "schema_version")}


class ConfigService:
    """Pipeline 配置业务编排服务。

    通过注入 ConfigStoreProtocol 实现存储后端可切换。
    封装 WizardState 校验、YAML 生成、版本管理、审计等业务逻辑，
    使 api/configs.py 退化为薄路由层。
    """

    def __init__(
        self,
        store: ConfigStoreProtocol | None = None,
        audit: AuditStoreProtocol | None = None,
    ):
        # Lazy default: 若未注入则用工厂获取（保持向后兼容）
        if store is None:
            from configforge.storage import get_config_store
            store = get_config_store()
        if audit is None:
            audit = get_audit_store()
        self._store = store
        self._audit = audit

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _configs_dir() -> str:
        """获取 CONFIGS_DIR（通过 config_store 模块，确保 patch 生效）。"""
        from configforge.services.config_store import CONFIGS_DIR
        return CONFIGS_DIR

    def _write_yaml(self, config_id: str, state: WizardState) -> str:
        """生成 YAML 并写入文件，返回路径。"""
        yaml_str = build_yaml(state)
        yaml_path = os.path.join(self._configs_dir(), f"{config_id}.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        return yaml_path

    @staticmethod
    def _strip_internal_fields(state_dict: dict) -> None:
        """移除 state dict 中的内部字段（_saved_at / change_summary / schema_version）。"""
        state_dict.pop("_saved_at", None)
        state_dict.pop("change_summary", None)
        state_dict.pop("schema_version", None)

    @staticmethod
    def _clear_file_ids(state_dict: dict) -> None:
        """清除 inputs 的 fileId（上传文件仅临时存在）。"""
        for inp in state_dict.get("inputs", []):
            inp["fileId"] = ""
        state_dict["uploaded_files"] = {}

    # ------------------------------------------------------------------
    # 列表 / 读取
    # ------------------------------------------------------------------

    def list_configs(
        self,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
        sort: str = "updated_at",
        order: str = "desc",
    ) -> dict:
        """分页列出配置（搜索 + 排序 + 分页），附带最近执行状态。"""
        index = self._store.list_configs(search or "")

        # Sort
        reverse = order.lower() == "desc"
        sort_key = "scene_name" if sort == "name" else sort
        index = sorted(index, key=lambda e: e.get(sort_key, ""), reverse=reverse)

        total = len(index)
        start = (page - 1) * page_size
        page_items = index[start:start + page_size]

        # 批量补充最近执行状态（execution index 按 started_at desc 排列，
        # 第一条匹配的即为该 config 的最近一次执行）
        last_exec_map = _build_last_execution_map([e["id"] for e in page_items])

        items = []
        for e in page_items:
            meta = ConfigMeta(**e)
            last = last_exec_map.get(meta.id)
            if last:
                meta.last_execution_status = last.get("status", "")
                meta.last_executed_at = last.get("started_at", "")
            items.append(meta)

        return {
            "configs": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def load_config(self, config_id: str) -> dict:
        """加载配置完整 state（含 schema 迁移）。不存在抛 KeyError。"""
        state_dict = self._store.get_config(config_id)
        if state_dict is None:
            raise KeyError(config_id)
        state_path = os.path.join(self._configs_dir(), f"{config_id}.state.json")
        return ensure_schema_version(state_dict, state_path)

    def get_yaml_path(self, config_id: str) -> str:
        """返回 YAML 文件路径（不校验存在性，由调用方处理）。"""
        return os.path.join(self._configs_dir(), f"{config_id}.yaml")

    # ------------------------------------------------------------------
    # 保存 / 删除
    # ------------------------------------------------------------------

    def save_config(self, req: SaveConfigRequest, user: User) -> SaveConfigResponse:
        """创建或更新配置（含版本归档、YAML 生成、审计）。"""
        config_id = req.config_id or uuid.uuid4().hex

        # 判断是否更新
        state_path = os.path.join(self._configs_dir(), f"{config_id}.state.json")
        is_update = os.path.exists(state_path)

        # 序列化 state，清除 file_id
        state_dict = req.state.model_dump(by_alias=True)
        self._clear_file_ids(state_dict)
        state_dict["_saved_at"] = datetime.now(UTC).isoformat()

        # 写 YAML（store.save_config 不写 yaml）
        self._write_yaml(config_id, req.state)

        # 保存 state + 版本归档 + 更新 index
        entry = self._store.save_config(config_id, state_dict, is_update=is_update)

        self._audit.log_audit(
            action="update" if is_update else "create",
            target_type="config",
            target_id=config_id,
            details={
                "user": user.username,
                "scene_name": entry.get("scene_name", ""),
                "version": entry.get("current_version", 1),
            },
        )

        return SaveConfigResponse(id=config_id)

    def delete_config(self, config_id: str) -> None:
        """删除配置（含文件清理、审计）。不存在抛 KeyError。"""
        deleted = self._store.delete_config(config_id)
        if not deleted:
            raise KeyError(config_id)
        self._audit.log_audit("delete", "config", config_id)

    # ------------------------------------------------------------------
    # 导出 / 导入
    # ------------------------------------------------------------------

    def export_config(self, config_id: str, fmt: str = "yaml") -> dict:
        """导出配置为 YAML 或 JSON。

        Returns:
            {content: bytes, media_type: str, filename: str, disposition: str}
        """
        if fmt not in ("yaml", "json"):
            raise ValueError(f"不支持的格式: {fmt}")

        state_dict = self._store.get_config(config_id)
        if state_dict is None:
            raise KeyError(config_id)

        state_path = os.path.join(self._configs_dir(), f"{config_id}.state.json")
        state_dict = ensure_schema_version(state_dict, state_path)
        export_data = _serialize_state_for_export(state_dict)
        export_data["_export"] = {
            "exported_at": datetime.now(UTC).isoformat(),
            "config_id": config_id,
            "format_version": 1,
        }

        scene_name = (state_dict.get("scene") or {}).get("name", config_id)
        safe_name = "".join(
            c if c.isascii() and (c.isalnum() or c in "-_") else "_"
            for c in scene_name
        )[:40] or config_id

        if fmt == "json":
            content = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")
            media_type = "application/json"
            filename = f"{safe_name}.json"
        else:
            content = yaml.safe_dump(export_data, allow_unicode=True, sort_keys=False).encode("utf-8")
            media_type = "application/x-yaml"
            filename = f"{safe_name}.yaml"

        from urllib.parse import quote
        disposition = f'attachment; filename="{safe_name}"; filename*=UTF-8\'\'{quote(filename)}'
        return {
            "content": content,
            "media_type": media_type,
            "filename": filename,
            "disposition": disposition,
        }

    def import_config(self, filename: str, raw_bytes: bytes, user: User) -> dict:
        """导入 YAML/JSON 配置文件创建新配置。

        Returns:
            {id: str, scene_name: str}
        """
        if not filename:
            raise ValueError("未提供文件")

        if len(raw_bytes) > 5 * 1024 * 1024:  # 5MB limit
            raise ValueError("文件过大（限制 5MB）")

        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("文件编码错误，请使用 UTF-8")

        # Determine format by extension or content
        filename_lower = filename.lower()
        if filename_lower.endswith(".json"):
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON 解析失败：{e}")
        else:
            try:
                data = yaml.safe_load(text)
            except yaml.YAMLError as e:
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    raise ValueError(f"YAML/JSON 解析失败：{e}")

        if not isinstance(data, dict):
            raise ValueError("配置内容必须是对象")

        # Strip export metadata & internal fields
        data.pop("_export", None)
        self._strip_internal_fields(data)

        # Validate as WizardState
        try:
            state = WizardState(**data)
        except Exception as e:
            raise ValueError(f"配置格式校验失败：{e}")

        # Save as a new config (always new ID)
        new_config_id = uuid.uuid4().hex
        state_dict = state.model_dump(by_alias=True)
        self._clear_file_ids(state_dict)
        state_dict["_saved_at"] = datetime.now(UTC).isoformat()
        state_dict["change_summary"] = "Imported from external file"

        # Write YAML + state
        self._write_yaml(new_config_id, state)
        entry = self._store.save_config(new_config_id, state_dict, is_update=False)

        self._audit.log_audit(
            action="import",
            target_type="config",
            target_id=new_config_id,
            details={
                "user": user.username,
                "scene_name": entry.get("scene_name", ""),
                "source_filename": filename,
            },
        )

        return {"id": new_config_id, "scene_name": entry.get("scene_name", "")}

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    async def execute_config(self, config_id: str, req: ExecuteConfigRequest):
        """执行已保存的配置。

        Returns:
            (ExecutionResult, ExecutionContext) — 调用方用 context.output_type
            构造数据库输出的响应（execute_service 会通过 _auto_fill_context
            填充 context.output_type）。
        """
        state_dict = self._store.get_config(config_id)
        if state_dict is None:
            raise KeyError(config_id)

        state_path = os.path.join(self._configs_dir(), f"{config_id}.state.json")
        state_dict = ensure_schema_version(state_dict, state_path)
        self._strip_internal_fields(state_dict)

        # 获取 config_version（从 index entry）
        index = self._store.list_configs("")
        entry = next((e for e in index if e.get("id") == config_id), None)
        config_version = entry.get("current_version") if entry else None

        # 用请求中的 file_id 填充各 input
        for inp in state_dict.get("inputs", []):
            param_key = inp.get("param_key", "") or inp.get("paramKey", "")
            if param_key in req.files:
                inp["fileId"] = req.files[param_key]
                inp.pop("file_id", None)

        state = WizardState(**state_dict)
        context = ExecutionContext(
            config_id=config_id,
            config_version=config_version,
        )

        result = await execute_service(state, context, sanitize_errors=True)

        self._audit.log_audit("execute", "config", config_id)
        return result, context

    # ------------------------------------------------------------------
    # 版本管理
    # ------------------------------------------------------------------

    def list_versions(self, config_id: str) -> list[ConfigVersionMeta]:
        """列出配置的版本历史。"""
        versions = self._store.list_versions(config_id)
        return [ConfigVersionMeta(**v) for v in versions]

    def get_version(self, config_id: str, version: int) -> dict:
        """获取指定版本 state（含 schema 迁移）。不存在抛 KeyError。"""
        state = self._store.get_version(config_id, version)
        if state is None:
            raise KeyError(f"v{version}")
        self._strip_internal_fields(state)
        state = ensure_schema_version(state, f"version:{config_id}:v{version}")
        state.pop("schema_version", None)
        return state

    def diff_versions(self, config_id: str, v1: int, v2: int) -> dict:
        """对比两个版本差异。版本不存在抛 KeyError。"""
        state1 = self._store.get_version(config_id, v1)
        state2 = self._store.get_version(config_id, v2)

        if state1 is None:
            raise KeyError(f"v{v1}")
        if state2 is None:
            raise KeyError(f"v{v2}")

        # Strip internal fields before diffing
        for s in (state1, state2):
            s.pop("_saved_at", None)
            s.pop("change_summary", None)

        result = _diff_states(state1, state2)
        return {"v1": v1, "v2": v2, **result}

    def rollback_version(self, config_id: str, version: int, user: User) -> dict:
        """回滚到指定版本。

        Returns:
            {new_version, rolled_back_from, rolled_back_to}
        """
        # 1. 读取目标版本 state
        target_state = self._store.get_version(config_id, version)
        if target_state is None:
            raise KeyError(f"v{version}")

        # 2. 当前配置必须存在
        current_state = self._store.get_config(config_id)
        if current_state is None:
            raise KeyError(config_id)

        # 3. 获取当前版本号
        index = self._store.list_configs("")
        entry_idx = next(
            (i for i, e in enumerate(index) if e.get("id") == config_id), None
        )
        if entry_idx is None:
            raise KeyError(f"index entry for {config_id}")
        old_version = index[entry_idx].get("current_version", 1)

        # 4. 准备回滚 state
        now_str = datetime.now(UTC).isoformat()
        target_state["_saved_at"] = now_str
        target_state["change_summary"] = f"Rolled back from v{old_version} to v{version}"

        # 5. 保存（store.save_config 会归档当前版本到 v{old_version}）
        #     注意：is_update=True，store 会把当前文件移到 v{old_version}
        entry = self._store.save_config(config_id, target_state, is_update=True)
        new_version = entry.get("current_version", old_version + 1)

        # 6. 重建 YAML（store 不写 yaml）
        rollback_state = dict(target_state)
        self._strip_internal_fields(rollback_state)
        rollback_state = ensure_schema_version(rollback_state, f"version:{config_id}:v{version}")
        rollback_state.pop("schema_version", None)
        restored_wizard = WizardState(**rollback_state)
        self._write_yaml(config_id, restored_wizard)

        # 7. 更新 index entry 的额外字段（scene version 等）
        # store.save_config 已更新 updated_at/current_version，
        # 但 rollback 还需同步 version/input_count/output_type
        index = self._store.list_configs("")
        entry_idx = next(
            (i for i, e in enumerate(index) if e.get("id") == config_id), None
        )
        if entry_idx is not None:
            index[entry_idx]["version"] = (target_state.get("scene") or {}).get("version", "1.0")
            index[entry_idx]["updated_at"] = now_str
            index[entry_idx]["input_count"] = len(target_state.get("inputs", []))
            output_type = (target_state.get("output") or {}).get("plugin", "")
            if output_type:
                index[entry_idx]["output_type"] = output_type
            # 直接写 index（绕过 store.save_config 的版本归档逻辑）
            from configforge.services.config_store import save_index as _save_index
            _save_index(index)

        self._audit.log_audit(
            action="rollback",
            target_type="config",
            target_id=config_id,
            details={
                "user": user.username,
                "rolled_back_from": old_version,
                "rolled_back_to": version,
                "new_version": new_version,
            },
        )

        return {
            "new_version": new_version,
            "rolled_back_from": old_version,
            "rolled_back_to": version,
        }
