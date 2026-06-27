import atexit
import copy
import glob
import os
import re
import shutil
import signal
import tempfile
import uuid

from configforge.models.wizard import (
    ColumnMappingItem,
    InputInferRequest,
    InputInferResponse,
    OutputInferRequest,
    OutputInferResponse,
    ProcessorConfig,
    SceneInfo,
    SceneInitRequest,
    SceneInitResponse,
    WizardState,
)
from configforge.services.reader_dispatch import read_file_info
from configforge.services.yaml_builder import build_yaml
from configforge.utils.paths import get_log_dir, get_output_dir, get_pipeline_timeout, get_upload_dir
from configforge.utils.security import validate_id
from pipeforge.core.engine import PipelineEngine

UPLOAD_DIR = get_upload_dir()
LOG_DIR = get_log_dir()
OUTPUT_DIR = get_output_dir()
PIPELINE_TIMEOUT_SECONDS = get_pipeline_timeout()


class PipelineTimeoutError(TimeoutError):
    """Raised when pipeline execution exceeds the configured timeout."""
    pass


def _timeout_handler(signum, frame):
    raise PipelineTimeoutError(
        f"Pipeline execution timed out after {PIPELINE_TIMEOUT_SECONDS} seconds"
    )


def _cleanup_temp_dirs():
    """atexit handler: remove any leftover pipeforge_out_* and pipeforge_exec_* temp dirs."""
    tmp_base = tempfile.gettempdir()
    for pattern in ("pipeforge_out_*", "pipeforge_exec_*"):
        for d in glob.glob(os.path.join(tmp_base, pattern)):
            shutil.rmtree(d, ignore_errors=True)


atexit.register(_cleanup_temp_dirs)


def init_scene(req: SceneInitRequest) -> SceneInitResponse:
    return SceneInitResponse(
        scene=SceneInfo(name="新场景", description="", version="1.0")
    )


def infer_input(
    input_name: str, req: InputInferRequest
) -> InputInferResponse:
    validate_id(req.file_id, "file_id")
    path = os.path.join(UPLOAD_DIR, req.file_id)
    info = read_file_info(path, file_type=req.type)
    # Build per-column sample values from sample_rows
    col_samples: dict[str, list[str]] = {c: [] for c in info["columns"]}
    for row in info["sample_rows"]:
        for idx, c in enumerate(info["columns"]):
            if idx < len(row) and len(col_samples[c]) < 3:
                col_samples[c].append(str(row[idx]))

    return InputInferResponse(
        columns=[
            {"name": c, "sample_values": col_samples[c]}
            for c in info["columns"]
        ],
        suggested_table=input_name,
        suggested_param_key=f"{input_name}_file",
    )


def infer_output(req: OutputInferRequest) -> OutputInferResponse:
    """Infer suggested output columns from input sources.

    Merges columns from all inputs that have column metadata.
    For database inputs with tables, includes table_name as prefix.
    """
    from configforge.models.wizard import ColumnMappingItem

    cols: list[ColumnMappingItem] = []
    seen: set[str] = set()

    for inp in req.inputs:
        cfg = inp.config
        # Only database inputs may have column info via query/table
        if inp.plugin == "database" and hasattr(cfg, "tables") and cfg.tables:
            for tbl in cfg.tables:
                if tbl and tbl not in seen:
                    seen.add(tbl)
                    cols.append(ColumnMappingItem(source=tbl, target=tbl))
        elif inp.table and inp.table not in seen:
            seen.add(inp.table)
            cols.append(ColumnMappingItem(source=inp.table, target=inp.table))

    return OutputInferResponse(suggested_columns=cols)


def generate(state: WizardState) -> dict:
    yaml = build_yaml(state)
    return {"yaml": yaml}


def _get_processors(exec_state: WizardState) -> list[ProcessorConfig]:
    """Return list of processors from exec_state."""
    return exec_state.processors


def _has_ddl(sql: str) -> bool:
    """检测 SQL 是否已包含 DDL 或 CTE。"""
    # Strip comments first
    sql_clean = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql_clean = re.sub(r"--[^\n]*", "", sql_clean)
    return bool(
        re.search(
            r"^\s*(CREATE\s+(?:TEMP\s+|TEMPORARY\s+)?(?:TABLE|VIEW|INDEX)|INSERT\s+INTO|WITH\s+\w+\s+AS\s*\()",
            sql_clean,
            re.IGNORECASE,
        )
    )


def _prepare_execution(state: WizardState, skip_output: bool = False):
    """Common preparation logic shared by execute_pipeline and dry_run.

    Returns (exec_state, tmp_dir, yaml_path, params).
    """
    exec_state = copy.deepcopy(state)

    if skip_output:
        exec_state.output = None  # dry-run skips output, avoid output validation errors

    # Auto-fill empty param_keys (PipeForge requires non-empty)
    for inp in exec_state.inputs:
        if not inp.param_key.strip():
            inp.param_key = inp.table or f"input_{id(inp)}"

    # Auto-wrap non-DDL SQL for all processors
    for proc in _get_processors(exec_state):
        if proc.plugin == "python":
            continue  # Python 步骤不需要 SQL 自动包装
        if proc.output_tables and proc.sql.strip() and not _has_ddl(proc.sql):
            output_table = proc.output_tables[0].replace('"', '')
            proc.sql = (
                f'CREATE TABLE "{output_table}" AS '
                f"SELECT * FROM ({proc.sql})"
            )

    # Auto-fill output source_table from last processor if empty
    if not skip_output and exec_state.output and not getattr(exec_state.output.config, 'source_table', None):
        procs = _get_processors(exec_state)
        if procs and procs[-1].output_tables:
            exec_state.output.config.source_table = procs[-1].output_tables[0]

    tmp_dir = tempfile.mkdtemp(prefix="pipeforge_exec_")

    # 当 output columns 为空时，自动从输入文件推断列映射
    if not skip_output and exec_state.output and exec_state.output.config.type == "excel" and not exec_state.output.config.columns:
        inferred: list[ColumnMappingItem] = []
        for inp in exec_state.inputs:
            if inp.file_id:
                validate_id(inp.file_id, "file_id")
                path = os.path.join(UPLOAD_DIR, inp.file_id)
                if os.path.exists(path):
                    info = read_file_info(path, file_type=inp.plugin)
                    inferred = [ColumnMappingItem(source=c, target=c) for c in info.get("columns", [])]
                    if inferred:
                        break
        if inferred:
            exec_state.output.config.columns = inferred

    # Excel 输出需要模板：拷贝已有模板，或在无模板时生成仅含表头的最小模板。
    if not skip_output and exec_state.output and exec_state.output.config.type == "excel":
        template_id = exec_state.output.config.template
        if template_id:
            validate_id(template_id, "template_id")
            src = os.path.join(UPLOAD_DIR, template_id)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(tmp_dir, template_id))
        else:
            from openpyxl import Workbook

            gen_name = "_generated_template.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.title = exec_state.output.config.sheet or "Sheet1"
            for i, col in enumerate(exec_state.output.config.columns, start=1):
                ws.cell(row=1, column=i, value=col.target)
            wb.save(os.path.join(tmp_dir, gen_name))
            wb.close()
            exec_state.output.config.template = gen_name

    # Resolve database connectionIds to connection_strings before building YAML
    from configforge.storage import get_connection_store
    _conn_store = get_connection_store()

    for inp in exec_state.inputs:
        cfg = inp.config
        if hasattr(cfg, 'type') and cfg.type == "database":
            if not cfg.connection_id:
                raise RuntimeError("Database input is missing connection_id")
            entry = _conn_store.get_with_plaintext_password(cfg.connection_id)
            if not entry:
                raise RuntimeError(f"Connection '{cfg.connection_id}' not found — please reconfigure")
            cfg.connection_string = _conn_store.build_connection_string(entry)
            cfg.db_type = entry["db_type"]

    # Resolve database output connection string
    if exec_state.output and exec_state.output.plugin == "database":
        db_config = exec_state.output.config
        if hasattr(db_config, 'connection_id') and getattr(db_config, 'connection_id', ''):
            try:
                entry = _conn_store.get_with_plaintext_password(db_config.connection_id)
                if entry:
                    db_config.connection_string = _conn_store.build_connection_string(entry)
            except Exception:
                pass  # connection might not exist yet during wizard preview

    # 在模板就绪后再构建 YAML
    yaml_str = build_yaml(exec_state)
    yaml_path = os.path.join(tmp_dir, "pipeline.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)

    # 复制输入文件到临时目录，或为数据库输入源注册占位参数
    params: dict[str, str] = {}
    for inp in exec_state.inputs:
        cfg = inp.config
        if hasattr(cfg, 'type') and cfg.type == "database":
            params[inp.param_key] = ""  # 数据库输入不需要文件路径
        elif inp.file_id:
            validate_id(inp.file_id, "file_id")
            src = os.path.join(UPLOAD_DIR, inp.file_id)
            if os.path.exists(src):
                ext = os.path.splitext(inp.file_id)[1].lower()
                if ext in (".xlsx", ".xls", ".csv"):
                    dst_name = inp.file_id
                else:
                    dst_name = inp.file_id + (".xlsx" if inp.plugin == "excel" else ".csv")
                dst = os.path.join(tmp_dir, dst_name)
                shutil.copy2(src, dst)
                params[inp.param_key] = os.path.abspath(dst)

    return exec_state, tmp_dir, yaml_path, params


def execute_pipeline(state: WizardState) -> str | None:
    """使用真实数据执行 pipeline，返回输出文件路径。

    对于 database output，返回 None（无文件输出）。
    """
    exec_state, tmp_dir, yaml_path, params = _prepare_execution(state, skip_output=False)

    is_db_output = (
        exec_state.output is not None
        and exec_state.output.plugin == "database"
    )

    engine = PipelineEngine(yaml_path)

    try:
        # Set timeout alarm (Unix/macOS only)
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(PIPELINE_TIMEOUT_SECONDS)
        try:
            result = engine.execute(params, log_dir=LOG_DIR)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    except (PipelineTimeoutError, Exception):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    if is_db_output:
        # Database output writes to a database, not a file
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    output_path = result.output.file_path if result.output else ""
    if not output_path or not os.path.exists(output_path):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError("Pipeline executed but no output file was generated")

    execution_id = uuid.uuid4().hex[:8]
    persist_dir = os.path.join(OUTPUT_DIR, execution_id)
    os.makedirs(persist_dir, exist_ok=True)
    output_filename = os.path.basename(output_path)
    persisted_path = os.path.join(persist_dir, output_filename)
    shutil.move(output_path, persisted_path)

    shutil.rmtree(tmp_dir, ignore_errors=True)

    return persisted_path


def dry_run(state: WizardState) -> dict:
    """Execute input + processor phases only, return table preview data.

    Used by the frontend Dry-Run button in Step 3 to preview SQL results
    before committing to full pipeline execution and file download.
    """
    exec_state, tmp_dir, yaml_path, params = _prepare_execution(state, skip_output=True)

    engine = PipelineEngine(yaml_path)
    result = engine.execute_dry_run(params, log_dir=LOG_DIR)

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return result
