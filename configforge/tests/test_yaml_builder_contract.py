"""契约测试：configforge → build_yaml → pipeforge load_yaml_config → 字段 round-trip。

目标：锁定翻译层行为，任何字段丢失/类型不匹配/alias 转换错误立即测试失败。
覆盖：csv/excel/database input + sql/python processor + csv/excel/database output

响应 v2.0 方案 4.5 第一步 + 审核报告 3.3 alias 差异测试建议。
"""
from configforge.models.wizard import (
    ColumnMappingItem,
    CsvInputConfig,
    CsvOutputConfig,
    DatabaseInputConfig,
    DatabaseOutputConfig,
    ExcelInputConfig,
    ExcelOutputConfig,
    InputSource,
    OutputTarget,
    ProcessorConfig,
    SceneInfo,
    WizardState,
)
from configforge.services.yaml_builder import build_yaml
from pipeforge.config import load_yaml_config
from pipeforge.config.models import SceneConfig


def _build_and_load(state: WizardState, tmp_path) -> SceneConfig:
    """辅助：build_yaml → 写临时文件 → pipeforge load_yaml_config。"""
    yaml_str = build_yaml(state)
    yaml_path = tmp_path / "pipeline.yaml"
    yaml_path.write_text(yaml_str, encoding="utf-8")
    return load_yaml_config(str(yaml_path))


# ---------------------------------------------------------------------------
# 1. 输入源 round-trip 契约测试
# ---------------------------------------------------------------------------
class TestInputContract:
    """输入源 configforge → pipeforge 字段一致性。"""

    def test_csv_input_round_trip(self, tmp_path):
        """csv input: delimiter/encoding/has_header 全字段 round-trip。"""
        state = WizardState(
            scene=SceneInfo(name="csv_contract"),
            inputs=[InputSource(
                name="csv_in", plugin="csv", table="raw_data", param_key="p1", file_id="f1",
                config=CsvInputConfig(delimiter=";", encoding="gbk", has_header=False),
            )],
        )
        config = _build_and_load(state, tmp_path)
        inp = config.inputs[0]
        assert inp.name == "csv_in"
        assert inp.plugin == "csv"
        assert inp.table == "raw_data"
        assert inp.param_key == "p1"
        cfg = inp.config
        assert cfg.type == "csv"
        assert cfg.delimiter == ";"
        assert cfg.encoding == "gbk"
        assert cfg.has_header is False

    def test_excel_input_round_trip(self, tmp_path):
        """excel input: sheet 字段 round-trip。"""
        state = WizardState(
            scene=SceneInfo(name="excel_contract"),
            inputs=[InputSource(
                name="xl_in", plugin="excel", table="orders", param_key="p1", file_id="f1",
                config=ExcelInputConfig(sheet="Orders"),
            )],
        )
        config = _build_and_load(state, tmp_path)
        cfg = config.inputs[0].config
        assert cfg.type == "excel"
        assert cfg.sheet == "Orders"

    def test_database_input_with_tables_round_trip(self, tmp_path):
        """database input (tables 模式): db_type/connection_string/tables round-trip。"""
        state = WizardState(
            scene=SceneInfo(name="db_contract"),
            inputs=[InputSource(
                name="db_in", plugin="database", table="users", param_key="p1", file_id="",
                config=DatabaseInputConfig(
                    db_type="postgres",
                    connection_string="postgres://localhost/db",
                    tables=["users"],
                ),
            )],
        )
        config = _build_and_load(state, tmp_path)
        cfg = config.inputs[0].config
        assert cfg.type == "database"
        assert cfg.db_type == "postgres"
        assert cfg.connection_string == "postgres://localhost/db"
        assert cfg.tables == ["users"]

    def test_database_input_with_sql_round_trip(self, tmp_path):
        """database input (sql 模式): sql 字段 round-trip。"""
        state = WizardState(
            scene=SceneInfo(name="db_sql_contract"),
            inputs=[InputSource(
                name="db_in", plugin="database", table="custom", param_key="p1", file_id="",
                config=DatabaseInputConfig(
                    db_type="mysql",
                    connection_string="mysql://localhost/db",
                    sql="SELECT id, name FROM users WHERE active = 1",
                ),
            )],
        )
        config = _build_and_load(state, tmp_path)
        cfg = config.inputs[0].config
        assert cfg.type == "database"
        assert cfg.sql == "SELECT id, name FROM users WHERE active = 1"
        assert cfg.tables == []


# ---------------------------------------------------------------------------
# 2. 处理器 round-trip 契约测试
# ---------------------------------------------------------------------------
class TestProcessorContract:
    """处理器 configforge → pipeforge 字段一致性。"""

    def test_sql_processor_round_trip(self, tmp_path):
        """sql processor: name/plugin/sql/input_tables/output_tables round-trip。"""
        state = WizardState(
            scene=SceneInfo(name="sql_proc"),
            inputs=[InputSource(
                name="csv_in", plugin="csv", table="raw", param_key="p1", file_id="f1",
                config=CsvInputConfig(),
            )],
            processors=[ProcessorConfig(
                name="sql_step", plugin="sql", sql="SELECT * FROM raw",
                input_tables=["raw"], output_tables=["result"],
            )],
        )
        config = _build_and_load(state, tmp_path)
        proc = config.processors[0]
        assert proc.name == "sql_step"
        assert proc.plugin == "sql"
        assert proc.input_tables == ["raw"]
        assert proc.output_tables == ["result"]
        assert proc.config.type == "sql"
        assert proc.config.sql == "SELECT * FROM raw"

    def test_python_processor_round_trip(self, tmp_path):
        """python processor: script 字段 round-trip。"""
        state = WizardState(
            scene=SceneInfo(name="py_proc"),
            inputs=[InputSource(
                name="csv_in", plugin="csv", table="raw", param_key="p1", file_id="f1",
                config=CsvInputConfig(),
            )],
            processors=[ProcessorConfig(
                name="py_step", plugin="python", script="df['x'] = 1",
                input_tables=["raw"], output_tables=["result"],
            )],
        )
        config = _build_and_load(state, tmp_path)
        proc = config.processors[0]
        assert proc.name == "py_step"
        assert proc.plugin == "python"
        assert proc.config.type == "python"
        assert proc.config.script == "df['x'] = 1"


# ---------------------------------------------------------------------------
# 3. 输出 round-trip 契约测试
# ---------------------------------------------------------------------------
class TestOutputContract:
    """输出 configforge → pipeforge 字段一致性。"""

    @staticmethod
    def _make_pipeline_with_output(output_config) -> WizardState:
        """辅助：构造 input + processor + output 的完整 pipeline。"""
        return WizardState(
            scene=SceneInfo(name="output_contract"),
            inputs=[InputSource(
                name="csv_in", plugin="csv", table="raw", param_key="p1", file_id="f1",
                config=CsvInputConfig(),
            )],
            processors=[ProcessorConfig(
                name="step1", plugin="sql", sql="SELECT * FROM raw",
                input_tables=["raw"], output_tables=["result"],
            )],
            output=OutputTarget(plugin=output_config.type, config=output_config),
        )

    def test_csv_output_round_trip(self, tmp_path):
        """csv output: source_table/output_dir/filename/delimiter/encoding/columns round-trip。"""
        state = self._make_pipeline_with_output(CsvOutputConfig(
            source_table="result", output_dir="/out", filename="out.csv",
            delimiter="\t", encoding="utf-8",
            columns=[ColumnMappingItem(source="a", target="b")],
        ))
        config = _build_and_load(state, tmp_path)
        cfg = config.output.config
        assert cfg.type == "csv"
        assert cfg.source_table == "result"
        assert cfg.output_dir == "/out"
        assert cfg.filename == "out.csv"
        assert cfg.delimiter == "\t"
        assert cfg.encoding == "utf-8"
        assert len(cfg.columns) == 1
        assert cfg.columns[0].source == "a"
        assert cfg.columns[0].target == "b"

    def test_excel_output_round_trip(self, tmp_path):
        """excel output: template/sheet/output_dir/filename/columns round-trip。"""
        state = self._make_pipeline_with_output(ExcelOutputConfig(
            template="tpl.xlsx", source_table="result", sheet="Result",
            output_dir="/out", filename="out.xlsx",
            columns=[ColumnMappingItem(source="c1", target="c2")],
        ))
        config = _build_and_load(state, tmp_path)
        cfg = config.output.config
        assert cfg.type == "excel"
        assert cfg.template == "tpl.xlsx"
        assert cfg.source_table == "result"
        assert cfg.sheet == "Result"
        assert cfg.output_dir == "/out"
        assert cfg.filename == "out.xlsx"
        assert cfg.columns[0].source == "c1"
        assert cfg.columns[0].target == "c2"

    def test_database_output_round_trip(self, tmp_path):
        """bug #2 验证: database output 的 batch_size 和 create_table_if_not_exists 正确 round-trip。"""
        state = self._make_pipeline_with_output(DatabaseOutputConfig(
            target_table="tgt", source_table="result",
            connection_string="sqlite:///db.sqlite",
            batch_size=5000,
            create_table_if_not_exists=False,
            columns=[ColumnMappingItem(source="x", target="y")],
            primary_key_columns=["id"],
        ))
        config = _build_and_load(state, tmp_path)
        cfg = config.output.config
        assert cfg.type == "database"
        assert cfg.target_table == "tgt"
        assert cfg.source_table == "result"
        assert cfg.connection_string == "sqlite:///db.sqlite"
        assert cfg.batch_size == 5000  # bug #2 关键断言
        assert cfg.create_table_if_not_exists is False  # bug #2 关键断言
        assert cfg.primary_key_columns == ["id"]
        assert cfg.columns[0].source == "x"
        assert cfg.columns[0].target == "y"


# ---------------------------------------------------------------------------
# 4. 完整 pipeline round-trip 契约测试
# ---------------------------------------------------------------------------
class TestFullPipelineContract:
    """完整 pipeline 全字段 round-trip。"""

    def test_full_pipeline_round_trip(self, tmp_path):
        """3 input + 2 processor + database output 全字段 round-trip。"""
        state = WizardState(
            scene=SceneInfo(name="full_contract", description="all types", version="2.0"),
            inputs=[
                InputSource(
                    name="csv_in", plugin="csv", table="raw", param_key="p1", file_id="f1",
                    config=CsvInputConfig(delimiter=",", encoding="utf-8", has_header=True),
                ),
                InputSource(
                    name="db_in", plugin="database", table="users", param_key="p2", file_id="",
                    config=DatabaseInputConfig(
                        db_type="mysql", connection_string="mysql://localhost/db",
                        tables=["users"],
                    ),
                ),
                InputSource(
                    name="xl_in", plugin="excel", table="orders", param_key="p3", file_id="f2",
                    config=ExcelInputConfig(sheet="Orders"),
                ),
            ],
            processors=[
                ProcessorConfig(
                    name="join", plugin="sql", sql="SELECT * FROM raw JOIN users",
                    input_tables=["raw", "users"], output_tables=["joined"],
                ),
                ProcessorConfig(
                    name="transform", plugin="python", script="df['x'] = 1",
                    input_tables=["joined"], output_tables=["final"],
                ),
            ],
            output=OutputTarget(
                plugin="database",
                config=DatabaseOutputConfig(
                    target_table="result", source_table="final",
                    connection_string="mysql://localhost/db",
                    batch_size=2000,
                    create_table_if_not_exists=True,
                    columns=[ColumnMappingItem(source="a", target="b")],
                    primary_key_columns=["id"],
                ),
            ),
        )
        config = _build_and_load(state, tmp_path)

        # Scene
        assert config.scene.name == "full_contract"
        assert config.scene.description == "all types"
        assert config.scene.version == "2.0"

        # Inputs
        assert len(config.inputs) == 3
        assert config.inputs[0].config.type == "csv"
        assert config.inputs[0].config.delimiter == ","
        assert config.inputs[1].config.type == "database"
        assert config.inputs[1].config.tables == ["users"]
        assert config.inputs[2].config.type == "excel"
        assert config.inputs[2].config.sheet == "Orders"

        # Processors
        assert len(config.processors) == 2
        assert config.processors[0].config.type == "sql"
        assert config.processors[0].config.sql == "SELECT * FROM raw JOIN users"
        assert config.processors[1].config.type == "python"
        assert config.processors[1].config.script == "df['x'] = 1"

        # Output (bug #2 验证)
        out_cfg = config.output.config
        assert out_cfg.type == "database"
        assert out_cfg.batch_size == 2000
        assert out_cfg.create_table_if_not_exists is True
        assert out_cfg.primary_key_columns == ["id"]


# ---------------------------------------------------------------------------
# 5. alias 差异测试（响应审核报告 3.3）
# ---------------------------------------------------------------------------
class TestAliasContract:
    """configforge camelCase alias 与 pipeforge snake_case 的转换验证。

    configforge 模型用 camelCase alias（前端友好），pipeforge 用 snake_case（CLI 友好）。
    build_yaml 是翻译桥梁：configforge model → dict(snake_case) → YAML → pipeforge model。
    """

    def test_csv_input_has_header_alias_round_trip(self, tmp_path):
        """configforge 用 alias hasHeader=False → build_yaml 输出 has_header → pipeforge 读取 has_header=False。"""
        # 用 alias 构造 configforge 模型
        cfg = CsvInputConfig.model_validate({"type": "csv", "hasHeader": False})
        assert cfg.has_header is False  # configforge 侧确认 alias 解析正确

        state = WizardState(
            scene=SceneInfo(name="alias_csv"),
            inputs=[InputSource(
                name="csv_in", plugin="csv", table="raw", param_key="p1", file_id="f1",
                config=cfg,
            )],
        )
        config = _build_and_load(state, tmp_path)
        # pipeforge 侧确认（snake_case）
        assert config.inputs[0].config.has_header is False

    def test_database_output_alias_round_trip(self, tmp_path):
        """configforge DatabaseOutputConfig 用 alias 构造 → build_yaml → pipeforge 读取 snake_case。

        验证 targetTable/writeMode/sourceTable/primaryKeyColumns/createTableIfNotExists
        等 alias 字段正确转换为 snake_case 并被 pipeforge 读取。
        注：batch_size 无 alias，用 snake_case 传入。
        """
        # 用 alias 构造（batch_size 例外，无 alias）
        cfg = DatabaseOutputConfig.model_validate({
            "type": "database",
            "targetTable": "tgt",
            "sourceTable": "result",
            "writeMode": "upsert",
            "primaryKeyColumns": ["id"],
            "createTableIfNotExists": False,
            "batch_size": 9999,  # 无 alias，用 snake_case
        })
        state = WizardState(
            scene=SceneInfo(name="alias_db"),
            inputs=[InputSource(
                name="csv_in", plugin="csv", table="raw", param_key="p1", file_id="f1",
                config=CsvInputConfig(),
            )],
            processors=[ProcessorConfig(
                name="step1", plugin="sql", sql="SELECT * FROM raw",
                input_tables=["raw"], output_tables=["result"],
            )],
            output=OutputTarget(plugin="database", config=cfg),
        )
        config = _build_and_load(state, tmp_path)
        out_cfg = config.output.config
        assert out_cfg.target_table == "tgt"
        assert out_cfg.source_table == "result"
        assert out_cfg.write_mode == "upsert"
        assert out_cfg.primary_key_columns == ["id"]
        assert out_cfg.create_table_if_not_exists is False
        assert out_cfg.batch_size == 9999

    def test_csv_output_alias_round_trip(self, tmp_path):
        """configforge CsvOutputConfig 用 alias 构造 → build_yaml → pipeforge 读取。"""
        cfg = CsvOutputConfig.model_validate({
            "type": "csv",
            "sourceTable": "result",
            "outputDir": "/out",
            "filename": "out.csv",
            "delimiter": "|",
            "encoding": "latin-1",
        })
        state = WizardState(
            scene=SceneInfo(name="alias_csv_out"),
            inputs=[InputSource(
                name="csv_in", plugin="csv", table="raw", param_key="p1", file_id="f1",
                config=CsvInputConfig(),
            )],
            processors=[ProcessorConfig(
                name="step1", plugin="sql", sql="SELECT * FROM raw",
                input_tables=["raw"], output_tables=["result"],
            )],
            output=OutputTarget(plugin="csv", config=cfg),
        )
        config = _build_and_load(state, tmp_path)
        out_cfg = config.output.config
        assert out_cfg.source_table == "result"
        assert out_cfg.output_dir == "/out"
        assert out_cfg.filename == "out.csv"
        assert out_cfg.delimiter == "|"
        assert out_cfg.encoding == "latin-1"
