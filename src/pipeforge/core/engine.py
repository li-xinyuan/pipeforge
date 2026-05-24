import copy
import time
from pathlib import Path

from pydantic import BaseModel

from pipeforge.config import load_yaml_config
from pipeforge.config.models import SceneConfig
from pipeforge.core.context import Context, InputStats, ProcessorStats, OutputStats, ExecutionResult, Logger
from pipeforge.core.registry import PluginRegistry
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.plugins.base import InputPlugin


class RequiredParam(BaseModel):
    key: str
    label: str
    description: str = ""


class PipelineEngine:
    """PipeForge 流水线引擎。"""

    def __init__(self, yaml_path: str):
        self._yaml_path = yaml_path
        self._yaml_dir = str(Path(yaml_path).parent.resolve())
        self.config: SceneConfig = load_yaml_config(yaml_path)

    def required_params(self) -> list[RequiredParam]:
        """返回流水线所需的运行时参数列表。"""
        return [
            RequiredParam(key=inp.param_key, label=inp.name)
            for inp in self.config.inputs
            if inp.param_key
        ]

    def execute(self, params: dict[str, str], cleanup: bool = False, log_dir: str | None = None) -> ExecutionResult:
        """执行流水线。"""
        _validate_params(self.required_params(), params)

        db = SQLiteManager()
        context = Context(
            db=db,
            params=params,
            yaml_dir=self._yaml_dir,
            scene_name=self.config.scene.name,
            logger=Logger(log_dir=log_dir),
        )

        try:
            for inp_spec in self.config.inputs:
                stats = self._execute_input(inp_spec, context)
                context.result.inputs[inp_spec.name] = stats

            if self.config.processors:
                input_tables = {inp.table for inp in self.config.inputs}
                sorted_processors = self._topological_sort(self.config.processors, input_tables)
                for proc_spec in sorted_processors:
                    for table in proc_spec.input_tables:
                        if table not in context.db.list_tables():
                            raise ValueError(f"Processor '{proc_spec.name}': input table '{table}' not found. Available: {context.db.list_tables()}")
                    stats = self._execute_processor(proc_spec, context)
                    context.result.processors.append(stats)

            if self.config.output is not None:
                stats = self._execute_output(self.config.output, context)
                context.result.output = stats

        except Exception:
            context.logger.error(f"Temporary database preserved at: {db.path}")
            raise
        finally:
            context.logger.close()
            if cleanup:
                db.close()
                db.remove()
            else:
                db.close()

        return context.result

    def execute_dry_run(self, params: dict[str, str], log_dir: str | None = None) -> dict:
        """Execute input + processor stages, skip output. Return intermediate table preview data."""
        _validate_params(self.required_params(), params)

        db = SQLiteManager()
        context = Context(
            db=db,
            params=params,
            yaml_dir=self._yaml_dir,
            scene_name=self.config.scene.name,
            logger=Logger(log_dir=log_dir),
        )

        try:
            for inp_spec in self.config.inputs:
                stats = self._execute_input(inp_spec, context)
                context.result.inputs[inp_spec.name] = stats

            if self.config.processors:
                input_tables = {inp.table for inp in self.config.inputs}
                sorted_processors = self._topological_sort(self.config.processors, input_tables)
                for proc_spec in sorted_processors:
                    for table in proc_spec.input_tables:
                        if table not in context.db.list_tables():
                            raise ValueError(f"Processor '{proc_spec.name}': input table '{table}' not found. Available: {context.db.list_tables()}")
                    stats = self._execute_processor(proc_spec, context)
                    context.result.processors.append(stats)

            # Capture table data before closing the database
            tables = []
            for table_name in db.list_tables():
                rows = db.query(f"SELECT * FROM \"{table_name}\" LIMIT 100")
                tables.append({
                    "table_name": table_name,
                    "columns": db.get_column_names(table_name),
                    "rows": [list(row) for row in rows],
                    "total_rows": db.query(f'SELECT COUNT(*) FROM "{table_name}"')[0][0],
                })

        except Exception:
            context.logger.error("Dry-run failed.")
            raise
        finally:
            context.logger.close()
            db.close()
            db.remove()

        return {
            "inputs": [{"name": k, "rows_loaded": v.rows_loaded} for k, v in context.result.inputs.items()],
            "processors": [{"name": p.name, "tables_created": p.tables_created} for p in context.result.processors],
            "tables": tables,
        }

    def _topological_sort(self, processors, available_tables: set[str]) -> list:
        """Kahn's algorithm — sort processors by input/output table dependencies."""
        remaining = list(processors)
        ordered = []
        available = set(available_tables)
        while remaining:
            ready = [
                p
                for p in remaining
                if not p.input_tables or all(t in available for t in p.input_tables)
            ]
            if not ready:
                missing = []
                for p in remaining:
                    missing.extend(t for t in p.input_tables if t not in available)
                raise ValueError(
                    f"Circular dependency or missing input table(s): "
                    f"{sorted(set(missing))}. Available tables: {sorted(available)}."
                )
            for p in ready:
                ordered.append(p)
                available.update(p.output_tables)
                remaining.remove(p)
        return ordered

    def _execute_input(self, inp_spec, context):
        start = time.time()
        file_path = context.params.get(inp_spec.param_key)
        if not file_path:
            context.logger.error(f"Skipping input '{inp_spec.name}': param '{
                inp_spec.param_key}' not found in runtime params")
            return InputStats(name=inp_spec.name, rows_loaded=0, elapsed_ms=0)
        plugin_cls = PluginRegistry.get(inp_spec.plugin, "input")
        plugin = plugin_cls()
        plugin.name = inp_spec.plugin
        plugin.label = inp_spec.name
        plugin.table_name = inp_spec.table
        config = copy.deepcopy(inp_spec.config)
        config.file = file_path
        plugin.execute(context, config)
        elapsed = (time.time() - start) * 1000
        rows = context.db.query(f'SELECT COUNT(*) FROM "{inp_spec.table}"')
        return InputStats(
            name=inp_spec.name,
            rows_loaded=rows[0][0],
            elapsed_ms=round(elapsed, 2),
        )

    def _execute_processor(self, proc_spec, context):
        start = time.time()
        before_tables = set(context.db.list_tables())
        plugin_cls = PluginRegistry.get(proc_spec.plugin, "processor")
        plugin = plugin_cls()
        plugin.name = proc_spec.plugin
        plugin.label = proc_spec.name
        plugin.execute(context, proc_spec.config)
        elapsed = (time.time() - start) * 1000
        after_tables = set(context.db.list_tables())
        created = sorted(after_tables - before_tables)
        return ProcessorStats(
            name=proc_spec.name,
            tables_created=created,
            elapsed_ms=round(elapsed, 2),
        )

    def _execute_output(self, out_spec, context):
        start = time.time()
        plugin_cls = PluginRegistry.get(out_spec.plugin, "output")
        plugin = plugin_cls()
        plugin.name = out_spec.plugin
        plugin.label = "output"
        plugin.execute(context, out_spec.config)
        elapsed = (time.time() - start) * 1000
        rows = context.db.query(f'SELECT COUNT(*) FROM "{out_spec.config.source_table}"')
        return OutputStats(
            rows_written=rows[0][0],
            file_path=context.output_path or "",
            elapsed_ms=round(elapsed, 2),
        )


def _validate_params(required: list[RequiredParam], provided: dict[str, str]) -> None:
    missing = [p.key for p in required if p.key not in provided]
    if missing:
        raise ValueError(
            f"Missing required parameters: {', '.join(missing)}. "
            f"Use --param key=value to provide them."
        )
