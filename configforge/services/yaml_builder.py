import yaml
from configforge.models.wizard import WizardState


def build_yaml(state: WizardState) -> str:
    d = {"scene": {"name": state.scene.name, "description": state.scene.description, "version": state.scene.version}}
    d["inputs"] = []
    for inp in state.inputs:
        d["inputs"].append({
            "name": inp.name, "plugin": inp.plugin, "table": inp.table,
            "param_key": inp.param_key, "config": {"sheet": inp.config.sheet},
        })
    d["processors"] = [{
        "name": state.scene.name + "处理",
        "plugin": state.processor.plugin,
        "output_tables": state.processor.output_tables,
        "config": {"sql": state.processor.sql},
    }]
    if state.output:
        out_cfg = state.output.config
        d["output"] = {
            "plugin": state.output.plugin,
            "config": {
                "template": out_cfg.template,
                "source_table": out_cfg.source_table,
                "sheet": out_cfg.sheet,
                "output_dir": out_cfg.output_dir,
                "filename": out_cfg.filename,
                "columns": [{"source": c.source, "target": c.target} for c in out_cfg.columns],
            },
        }
    return yaml.dump(d, allow_unicode=True, default_flow_style=False, sort_keys=False)
