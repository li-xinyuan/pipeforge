import yaml

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
from pipeforge.config.models import RowCountRule


# ---------------------------------------------------------------------------
# 1. Scene
# ---------------------------------------------------------------------------
class TestBuildYamlScene:
    def test_scene_name_in_output(self):
        state = WizardState(scene=SceneInfo(name="MyScene"))
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert data["scene"]["name"] == "MyScene"

    def test_scene_description_in_output(self):
        state = WizardState(scene=SceneInfo(name="S", description="hello world"))
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert data["scene"]["description"] == "hello world"

    def test_scene_version_in_output(self):
        state = WizardState(scene=SceneInfo(name="S", version="2.5"))
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert data["scene"]["version"] == "2.5"

    def test_scene_defaults(self):
        state = WizardState(scene=SceneInfo(name="S"))
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert data["scene"]["description"] == ""
        assert data["scene"]["version"] == "1.0"


# ---------------------------------------------------------------------------
# 2. Inputs
# ---------------------------------------------------------------------------
class TestBuildYamlInputs:
    def test_csv_input(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            inputs=[InputSource(
                name="csv1", plugin="csv", table="t1", param_key="p1", file_id="f1",
                config=CsvInputConfig(delimiter=";", encoding="gbk", has_header=False),
            )],
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        inp = data["inputs"][0]
        assert inp["name"] == "csv1"
        assert inp["plugin"] == "csv"
        assert inp["table"] == "t1"
        assert inp["param_key"] == "p1"
        cfg = inp["config"]
        assert cfg["type"] == "csv"
        assert cfg["delimiter"] == ";"
        assert cfg["encoding"] == "gbk"
        assert cfg["has_header"] is False

    def test_database_input(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            inputs=[InputSource(
                name="db1", plugin="database", table="users", param_key="c1", file_id="",
                config=DatabaseInputConfig(
                    connection_id="conn-1", db_type="postgres",
                    connection_string="postgres://localhost/db",
                    query_type="sql", tables=[], sql="SELECT 1",
                ),
            )],
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        cfg = data["inputs"][0]["config"]
        assert cfg["type"] == "database"
        assert cfg["db_type"] == "postgres"
        assert cfg["connection_string"] == "postgres://localhost/db"
        assert cfg["tables"] == []
        assert cfg["sql"] == "SELECT 1"

    def test_excel_input(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            inputs=[InputSource(
                name="xl1", plugin="excel", table="t1", param_key="p1", file_id="f1",
                config=ExcelInputConfig(sheet="DataSheet"),
            )],
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        cfg = data["inputs"][0]["config"]
        assert cfg["type"] == "excel"
        assert cfg["sheet"] == "DataSheet"

    def test_multiple_inputs(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            inputs=[
                InputSource(
                    name="csv_in", plugin="csv", table="t1", param_key="p1", file_id="f1",
                    config=CsvInputConfig(),
                ),
                InputSource(
                    name="db_in", plugin="database", table="t2", param_key="p2", file_id="",
                    config=DatabaseInputConfig(db_type="mysql", connection_string="mysql://localhost/db"),
                ),
                InputSource(
                    name="xl_in", plugin="excel", table="t3", param_key="p3", file_id="f2",
                    config=ExcelInputConfig(sheet="Sheet2"),
                ),
            ],
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert len(data["inputs"]) == 3
        assert data["inputs"][0]["config"]["type"] == "csv"
        assert data["inputs"][1]["config"]["type"] == "database"
        assert data["inputs"][2]["config"]["type"] == "excel"


# ---------------------------------------------------------------------------
# 3. Processors
# ---------------------------------------------------------------------------
class TestBuildYamlProcessors:
    def test_sql_processor(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            processors=[ProcessorConfig(
                name="sql_step", plugin="sql", sql="SELECT * FROM t1",
                input_tables=["t1"], output_tables=["t2"],
            )],
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        proc = data["processors"][0]
        assert proc["name"] == "sql_step"
        assert proc["plugin"] == "sql"
        assert proc["config"]["type"] == "sql"
        assert proc["config"]["sql"] == "SELECT * FROM t1"
        assert proc["input_tables"] == ["t1"]
        assert proc["output_tables"] == ["t2"]

    def test_python_processor(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            processors=[ProcessorConfig(
                name="py_step", plugin="python", script="print('hello')",
                input_tables=["t1"], output_tables=["t2"],
            )],
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        proc = data["processors"][0]
        assert proc["name"] == "py_step"
        assert proc["plugin"] == "python"
        assert proc["config"]["type"] == "python"
        assert proc["config"]["script"] == "print('hello')"

    def test_processor_with_checkpoints(self):
        rule = RowCountRule(table="t1", min=1, max=100, on_failure="block")
        state = WizardState(
            scene=SceneInfo(name="S"),
            processors=[ProcessorConfig(
                name="step1", plugin="sql", sql="SELECT 1",
                output_tables=["t1"], checkpoints=[rule],
            )],
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        proc = data["processors"][0]
        assert "checkpoints" in proc
        assert len(proc["checkpoints"]) == 1
        assert proc["checkpoints"][0]["type"] == "row_count"
        assert proc["checkpoints"][0]["table"] == "t1"

    def test_processor_name_defaults_to_step_n(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            processors=[
                ProcessorConfig(plugin="sql", sql="SELECT 1", output_tables=["t1"]),
                ProcessorConfig(plugin="python", script="pass", output_tables=["t2"]),
            ],
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert data["processors"][0]["name"] == "step_1"
        assert data["processors"][1]["name"] == "step_2"


# ---------------------------------------------------------------------------
# 4. Output
# ---------------------------------------------------------------------------
class TestBuildYamlOutput:
    def test_csv_output(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            output=OutputTarget(
                plugin="csv",
                config=CsvOutputConfig(
                    source_table="t1", output_dir="/out", filename="result.csv",
                    delimiter="\t", encoding="utf-8",
                    columns=[ColumnMappingItem(source="a", target="b")],
                ),
            ),
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        cfg = data["output"]["config"]
        assert cfg["type"] == "csv"
        assert cfg["source_table"] == "t1"
        assert cfg["output_dir"] == "/out"
        assert cfg["filename"] == "result.csv"
        assert cfg["delimiter"] == "\t"
        assert cfg["encoding"] == "utf-8"
        assert cfg["columns"] == [{"source": "a", "target": "b"}]

    def test_database_output(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            output=OutputTarget(
                plugin="database",
                config=DatabaseOutputConfig(
                    connection_id="conn-1", target_table="target_tbl",
                    write_mode="upsert", source_table="t1",
                    connection_string="mysql://localhost/db",
                    columns=[ColumnMappingItem(source="x", target="y")],
                    primary_key_columns=["id"],
                ),
            ),
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        cfg = data["output"]["config"]
        assert cfg["type"] == "database"
        assert cfg["connection_id"] == "conn-1"
        assert cfg["target_table"] == "target_tbl"
        assert cfg["write_mode"] == "upsert"
        assert cfg["source_table"] == "t1"
        assert cfg["connection_string"] == "mysql://localhost/db"
        assert cfg["columns"] == [{"source": "x", "target": "y"}]
        assert cfg["primary_key_columns"] == ["id"]

    def test_excel_output(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            output=OutputTarget(
                plugin="excel",
                config=ExcelOutputConfig(
                    template="tpl.xlsx", source_table="t1", sheet="Result",
                    output_dir="/out", filename="out.xlsx",
                    columns=[ColumnMappingItem(source="c1", target="c2")],
                ),
            ),
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        cfg = data["output"]["config"]
        assert cfg["type"] == "excel"
        assert cfg["template"] == "tpl.xlsx"
        assert cfg["source_table"] == "t1"
        assert cfg["sheet"] == "Result"
        assert cfg["output_dir"] == "/out"
        assert cfg["filename"] == "out.xlsx"
        assert cfg["columns"] == [{"source": "c1", "target": "c2"}]

    def test_no_output(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            output=None,
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert "output" not in data


# ---------------------------------------------------------------------------
# 5. Combinations
# ---------------------------------------------------------------------------
class TestBuildYamlCombinations:
    def test_full_pipeline_with_all_types(self):
        state = WizardState(
            scene=SceneInfo(name="FullPipeline", description="all types", version="3.0"),
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
                    checkpoints=[RowCountRule(table="final", min=1, on_failure="warn")],
                ),
            ],
            output=OutputTarget(
                plugin="database",
                config=DatabaseOutputConfig(
                    connection_id="conn-1", target_table="result",
                    write_mode="append", source_table="final",
                    connection_string="mysql://localhost/db",
                    columns=[ColumnMappingItem(source="a", target="b")],
                    primary_key_columns=["id"],
                ),
            ),
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)

        assert data["scene"]["name"] == "FullPipeline"
        assert data["scene"]["version"] == "3.0"
        assert len(data["inputs"]) == 3
        assert len(data["processors"]) == 2
        assert data["processors"][1]["checkpoints"][0]["type"] == "row_count"
        assert data["output"]["config"]["type"] == "database"

    def test_minimal_pipeline_scene_only(self):
        state = WizardState(
            scene=SceneInfo(name="Minimal"),
            inputs=[],
            processors=[],
            output=None,
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert data["scene"]["name"] == "Minimal"
        assert data["inputs"] == []
        assert data["processors"] == []
        assert "output" not in data


# ---------------------------------------------------------------------------
# 6. Edge cases
# ---------------------------------------------------------------------------
class TestBuildYamlEdgeCases:
    def test_empty_processor_name_gets_default(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            processors=[
                ProcessorConfig(name="", plugin="sql", sql="SELECT 1", output_tables=["t1"]),
            ],
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert data["processors"][0]["name"] == "step_1"

    def test_empty_columns_list(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            output=OutputTarget(
                plugin="csv",
                config=CsvOutputConfig(
                    source_table="t1", filename="out.csv",
                    columns=[],
                ),
            ),
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert data["output"]["config"]["columns"] == []

    def test_database_output_no_columns_no_primary_key(self):
        state = WizardState(
            scene=SceneInfo(name="S"),
            output=OutputTarget(
                plugin="database",
                config=DatabaseOutputConfig(
                    target_table="tgt", source_table="t1",
                    connection_string="sqlite:///db.sqlite",
                    columns=[], primary_key_columns=[],
                ),
            ),
        )
        result = build_yaml(state)
        data = yaml.safe_load(result)
        cfg = data["output"]["config"]
        assert "columns" not in cfg
        assert "primary_key_columns" not in cfg

    def test_unicode_scene_name(self):
        state = WizardState(scene=SceneInfo(name="中文场景测试", description="包含中文描述"))
        result = build_yaml(state)
        data = yaml.safe_load(result)
        assert data["scene"]["name"] == "中文场景测试"
        assert data["scene"]["description"] == "包含中文描述"
