import yaml

from configforge.models.wizard import WizardState

# configforge DatabaseInputConfig 专有字段（pipeforge DbInputConfig 不识别，extra="forbid"）
_DB_INPUT_EXCLUDE = {"connection_id", "query_type"}


def _dump_input_config(cfg) -> dict:
    """输入配置 → snake_case dict（供 pipeforge 加载）。

    限制②C：利用 loose 模型继承，model_dump() 默认输出 snake_case 字段名，
    与 pipeforge strict 模型字段名一致。仅排除 configforge 专有字段。
    api 类型延后到第三阶段，暂不支持执行。
    """
    if cfg.type == "api":
        raise ValueError(
            f"输入源 '{cfg.type}' 当前仅支持预览，暂不可执行。"
            f"支持的输入类型：excel / csv / database / json / xml / parquet"
        )
    exclude = _DB_INPUT_EXCLUDE if cfg.type == "database" else set()
    return cfg.model_dump(exclude=exclude)


def _dump_output_config(cfg) -> dict:
    """输出配置 → snake_case dict（供 pipeforge 加载）。

    database output 的 columns/primary_key_columns 为空时省略（保持既有行为）。
    """
    config_dict = cfg.model_dump()
    if cfg.type == "database":
        if not config_dict.get("columns"):
            config_dict.pop("columns", None)
        if not config_dict.get("primary_key_columns"):
            config_dict.pop("primary_key_columns", None)
    return config_dict


def build_yaml(state: WizardState) -> str:
    d = {"scene": {
        "name": state.scene.name,
        "description": state.scene.description,
        "version": state.scene.version,
    }}
    d["inputs"] = [
        {
            "name": inp.name,
            "plugin": inp.plugin,
            "table": inp.table,
            "param_key": inp.param_key,
            "config": _dump_input_config(inp.config),
        }
        for inp in state.inputs
    ]
    d["processors"] = []
    for i, proc in enumerate(state.processors):
        # bug #7 修复：空占位符检查，未完成的 processor 翻译时给出清晰错误
        step_name = proc.name or f"step_{i+1}"
        if proc.plugin == "sql" and not proc.sql.strip():
            raise ValueError(f"处理器 '{step_name}' 的 SQL 为空，请填写后再生成/执行")
        if proc.plugin == "python" and not proc.script.strip():
            raise ValueError(f"处理器 '{step_name}' 的脚本为空，请填写后再生成/执行")
        # processor 配置：sql → {type, sql}，python → {type, script}
        config_key = "sql" if proc.plugin == "sql" else "script"
        config_value = proc.sql if proc.plugin == "sql" else proc.script
        entry = {
            "name": step_name,
            "plugin": proc.plugin,
            "input_tables": proc.input_tables,
            "output_tables": proc.output_tables,
            "config": {"type": proc.plugin, config_key: config_value},
        }
        if proc.checkpoints:
            entry["checkpoints"] = [r.model_dump() for r in proc.checkpoints]
        d["processors"].append(entry)
    if state.output:
        d["output"] = {
            "plugin": state.output.plugin,
            "config": _dump_output_config(state.output.config),
        }
    return yaml.dump(d, allow_unicode=True, default_flow_style=False, sort_keys=False)
