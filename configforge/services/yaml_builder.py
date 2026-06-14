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
        else:
            config_dict = {"type": "excel", "sheet": cfg.sheet}
        d["inputs"].append({
            "name": inp.name, "plugin": inp.plugin, "table": inp.table,
            "param_key": inp.param_key, "config": config_dict,
        })
    d["processors"] = []
    for i, proc in enumerate(state.processors):
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
            config_dict = {
                "type": "database",
                "connection_id": out_cfg.connection_id,
                "target_table": out_cfg.target_table,
                "write_mode": out_cfg.write_mode,
                "source_table": out_cfg.source_table,
                "connection_string": out_cfg.connection_string,
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
