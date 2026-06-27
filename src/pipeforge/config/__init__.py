from pathlib import Path

import yaml

from pipeforge.config.exceptions import ConfigError
from pipeforge.config.models import SceneConfig


def load_yaml_config(yaml_path: str) -> SceneConfig:
    """加载并校验 YAML 配置文件。"""
    path = Path(yaml_path)
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {yaml_path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ConfigError(f"Configuration file is empty: {yaml_path}")

    _inject_type_defaults(raw)

    config = SceneConfig(**raw)

    _validate_table_names(config)
    _validate_param_keys(config)
    _validate_source_table(config)

    return config


def _inject_type_defaults(raw: dict) -> None:
    """向后兼容：为不含 type 字段的 config dict 注入默认 type 值。"""
    for inp in raw.get("inputs", []):
        cfg = inp.get("config")
        if isinstance(cfg, dict) and "type" not in cfg:
            plugin = inp.get("plugin", "excel")
            if plugin == "sql":
                cfg["type"] = "sql"
            else:
                cfg["type"] = plugin

    for proc in raw.get("processors", []):
        cfg = proc.get("config")
        if isinstance(cfg, dict) and "type" not in cfg:
            plugin = proc.get("plugin", "sql")
            if plugin == "sql":
                cfg["type"] = "sql"
            elif plugin == "python":
                cfg["type"] = "python"

    output = raw.get("output")
    if isinstance(output, dict):
        cfg = output.get("config")
        if isinstance(cfg, dict) and "type" not in cfg:
            cfg["type"] = output.get("plugin", "excel")


def _validate_table_names(config: SceneConfig) -> None:
    """检测表名冲突：inputs[].table 互不相同，且不与 output_tables 冲突。"""
    seen = {}

    for inp in config.inputs:
        if inp.table in seen:
            raise ConfigError(
                f"Table name '{inp.table}' is used by both "
                f"inputs[name={seen[inp.table]}] and inputs[name={inp.name}]"
            )
        seen[inp.table] = inp.name

    for proc in config.processors:
        for ot in proc.output_tables:
            if ot in seen:
                raise ConfigError(
                    f"Output table '{ot}' conflicts with input table "
                    f"'{ot}' (inputs[name={seen[ot]}])"
                )
            seen[ot] = proc.name


def _validate_param_keys(config: SceneConfig) -> None:
    """检测 param_key 重复。"""
    seen = {}
    for inp in config.inputs:
        if inp.param_key in seen:
            raise ConfigError(
                f"param_key '{inp.param_key}' is used by both "
                f"inputs[name={seen[inp.param_key]}] and inputs[name={inp.name}]"
            )
        seen[inp.param_key] = inp.name


def _validate_source_table(config: SceneConfig) -> None:
    """检测 output.source_table 是否在某个 processor 的 output_tables 中声明。"""
    if config.output is None:
        return

    source_table = config.output.config.source_table
    declared = set()
    for proc in config.processors:
        declared.update(proc.output_tables)

    if source_table not in declared:
        raise ConfigError(
            f"Output source_table '{source_table}' is not declared in any "
            f"processor's output_tables. Declared tables: {sorted(declared)}"
        )
