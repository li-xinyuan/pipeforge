import yaml

from configforge.models.wizard import WizardState


def build_yaml(state: WizardState) -> str:
    d = {"scene": {"name": state.scene.name, "description": state.scene.description, "version": state.scene.version}}
    d["inputs"] = []
    for inp in state.inputs:
        cfg = inp.config
        if cfg.type == "csv":
            config_dict = {
                "type": "csv",
                "delimiter": cfg.delimiter,
                "encoding": cfg.encoding,
                "has_header": cfg.has_header,
            }
        elif cfg.type == "database":
            config_dict = {
                "type": "database",
                "db_type": cfg.db_type,
                "connection_string": cfg.connection_string,
                "tables": cfg.tables,
                "sql": cfg.sql,
            }
        elif cfg.type == "excel":
            config_dict = {"type": "excel", "sheet": cfg.sheet}
        elif cfg.type == "json":
            # 限制③C：json 输入源现在可执行（reader 适配器）
            config_dict = {
                "type": "json",
                "flatten_separator": cfg.flatten_separator,
            }
        elif cfg.type == "xml":
            # 限制③C：xml 输入源现在可执行（reader 适配器）
            config_dict = {
                "type": "xml",
                "row_element": cfg.row_element,
            }
        elif cfg.type == "parquet":
            # 限制③C：parquet 输入源现在可执行（reader 适配器）
            config_dict = {"type": "parquet"}
        else:
            # api 输入源延后到 v2.0.0（第三阶段），暂不支持执行
            raise ValueError(
                f"输入源 '{cfg.type}' 当前仅支持预览，暂不可执行。"
                f"支持的输入类型：excel / csv / database / json / xml / parquet"
            )
        d["inputs"].append({
            "name": inp.name, "plugin": inp.plugin, "table": inp.table,
            "param_key": inp.param_key, "config": config_dict,
        })
    d["processors"] = []
    for i, proc in enumerate(state.processors):
        # bug #7 修复：空占位符检查，未完成的 processor 翻译时给出清晰错误
        step_name = proc.name or f"step_{i+1}"
        if proc.plugin == "sql" and not proc.sql.strip():
            raise ValueError(f"处理器 '{step_name}' 的 SQL 为空，请填写后再生成/执行")
        if proc.plugin == "python" and not proc.script.strip():
            raise ValueError(f"处理器 '{step_name}' 的脚本为空，请填写后再生成/执行")
        if proc.plugin == "python":
            entry = {
                "name": proc.name or f"step_{i+1}",
                "plugin": "python",
                "input_tables": proc.input_tables,
                "output_tables": proc.output_tables,
                "config": {"type": "python", "script": proc.script},
            }
            if proc.checkpoints:
                entry["checkpoints"] = [r.model_dump(exclude_defaults=False) for r in proc.checkpoints]
            d["processors"].append(entry)
        else:
            entry = {
                "name": proc.name or f"step_{i+1}",
                "plugin": proc.plugin,
                "input_tables": proc.input_tables,
                "output_tables": proc.output_tables,
                "config": {"type": "sql", "sql": proc.sql},
            }
            if proc.checkpoints:
                entry["checkpoints"] = [r.model_dump(exclude_defaults=False) for r in proc.checkpoints]
            d["processors"].append(entry)
    if state.output:
        out_cfg = state.output.config
        if out_cfg.type == "csv":
            config_dict = {
                "type": "csv",
                "source_table": out_cfg.source_table,
                "output_dir": out_cfg.output_dir,
                "filename": out_cfg.filename,
                "delimiter": out_cfg.delimiter,
                "encoding": out_cfg.encoding,
                "columns": [{"source": c.source, "target": c.target} for c in out_cfg.columns],
            }
        elif out_cfg.type == "database":
            # bug #2 修复：补全 batch_size 和 create_table_if_not_exists，避免静默丢失
            config_dict = {
                "type": "database",
                "connection_id": out_cfg.connection_id,
                "target_table": out_cfg.target_table,
                "write_mode": out_cfg.write_mode,
                "source_table": out_cfg.source_table,
                "connection_string": out_cfg.connection_string,
                "batch_size": out_cfg.batch_size,
                "create_table_if_not_exists": out_cfg.create_table_if_not_exists,
            }
            if out_cfg.columns:
                config_dict["columns"] = [{"source": c.source, "target": c.target} for c in out_cfg.columns]
            if out_cfg.primary_key_columns:
                config_dict["primary_key_columns"] = out_cfg.primary_key_columns
        else:
            config_dict = {
                "type": "excel",
                "template": out_cfg.template,
                "source_table": out_cfg.source_table,
                "sheet": out_cfg.sheet,
                "output_dir": out_cfg.output_dir,
                "filename": out_cfg.filename,
                "columns": [{"source": c.source, "target": c.target} for c in out_cfg.columns],
            }
        d["output"] = {
            "plugin": state.output.plugin,
            "config": config_dict,
        }
    return yaml.dump(d, allow_unicode=True, default_flow_style=False, sort_keys=False)
