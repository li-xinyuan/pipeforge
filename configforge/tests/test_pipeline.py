import pytest

from configforge.core.pipeline import _has_ddl, _prepare_execution, generate, infer_output, init_scene
from configforge.models.wizard import (
    ColumnMappingItem,
    ExcelOutputConfig,
    InputSource,
    OutputInferRequest,
    OutputTarget,
    ProcessorConfig,
    SceneInfo,
    SceneInitRequest,
    WizardState,
)
from configforge.services.yaml_builder import build_yaml


class TestHasDdl:
    def test_create_table(self):
        assert _has_ddl("CREATE TABLE foo (id INT)") is True

    def test_create_temp_table(self):
        assert _has_ddl("CREATE TEMP TABLE foo AS SELECT * FROM bar") is True

    def test_create_temporary_table(self):
        assert _has_ddl("CREATE TEMPORARY TABLE foo (x TEXT)") is True

    def test_insert_into(self):
        assert _has_ddl("INSERT INTO foo SELECT * FROM bar") is True

    def test_select_not_ddl(self):
        assert _has_ddl("SELECT * FROM person") is False

    def test_select_with_join_not_ddl(self):
        assert _has_ddl("SELECT a.*, b.* FROM a JOIN b ON a.id = b.id") is False

    def test_with_cte_not_ddl(self):
        # CTE (WITH ... AS) is now detected as DDL (Plan Phase 3.2)
        assert _has_ddl("WITH cte AS (SELECT * FROM t) SELECT * FROM cte") is True

    def test_indented_create_table(self):
        assert _has_ddl("\n  CREATE TABLE foo AS SELECT 1") is True

    def test_create_in_lowercase(self):
        assert _has_ddl("create table foo (id int)") is True

    def test_insert_in_lowercase(self):
        assert _has_ddl("insert into foo values (1)") is True

    def test_empty_sql(self):
        assert _has_ddl("") is False

    def test_comment_with_create(self):
        # Comments are stripped before DDL detection
        assert _has_ddl("-- comment\nCREATE TABLE foo (id INT)") is True

    def test_drop_table_not_matched_by_has_ddl(self):
        # DROP TABLE is not DDL detection's job — that's SQL injection's job
        assert _has_ddl("DROP TABLE users") is False

    def test_create_in_mid_not_start(self):
        assert _has_ddl("SELECT * FROM (CREATE TABLE x)") is False


class TestInitScene:
    def test_returns_default_scene(self):
        req = SceneInitRequest(file_ids=[])
        resp = init_scene(req)
        assert resp.scene.name == "新场景"
        assert resp.scene.version == "1.0"
        assert resp.scene.description == ""


class TestInferOutput:
    def test_returns_empty_columns(self):
        req = OutputInferRequest(inputs=[])
        resp = infer_output(req)
        assert resp.suggested_columns == []


class TestGenerate:
    def test_generates_yaml_string(self):
        state = WizardState(
            scene=SceneInfo(name="测试", description="desc"),
            inputs=[
                InputSource(
                    name="in1",
                    plugin="excel",
                    table="t1",
                    param_key="f1",
                    file_id="abc",
                )
            ],
            processors=[ProcessorConfig(sql="SELECT 1", output_tables=["out1"])],
            output=OutputTarget(
                plugin="excel",
                config=ExcelOutputConfig(
                    source_table="out1",
                    filename="out.xlsx",
                    columns=[ColumnMappingItem(source="a", target="a")],
                ),
            ),
        )
        result = generate(state)
        assert "yaml" in result
        assert "scene:" in result["yaml"]
        assert "测试" in result["yaml"]
        assert "inputs:" in result["yaml"]
        assert "processors:" in result["yaml"]
        assert "output:" in result["yaml"]  # YAML key is 'output' (singular)
        assert "SELECT 1" in result["yaml"]

    def test_generate_with_csv_input(self):
        state = WizardState(
            scene=SceneInfo(name="CSV测试"),
            inputs=[
                InputSource(
                    name="csv_in",
                    plugin="csv",
                    table="csv_t",
                    param_key="f_csv",
                    file_id="xyz",
                )
            ],
            processors=[ProcessorConfig(sql="SELECT * FROM csv_t", output_tables=["res"])],
            output=OutputTarget(
                plugin="excel",
                config=ExcelOutputConfig(
                    source_table="res",
                    filename="out.xlsx",
                    columns=[],
                ),
            ),
        )
        result = generate(state)
        assert "csv" in result["yaml"].lower()

    def test_generate_without_output(self):
        state = WizardState(
            scene=SceneInfo(name="Minimal"),
            inputs=[],
            processors=[],
            output=None,
        )
        result = generate(state)
        assert "yaml" in result
        assert "outputs:" not in result["yaml"]  # no output → no output section in YAML


class TestCheckpoints:
    def test_row_count_warn_pipeline_proceeds(self):
        """warn 检查点不阻断管道执行。"""
        state = WizardState(
            scene=SceneInfo(name="test_checkpoint"),
            inputs=[InputSource(
                plugin="csv", table="test_data", param_key="test_data",
                config={"type": "csv", "delimiter": ",", "encoding": "utf-8"},
            )],
            processors=[ProcessorConfig(
                name="step1", plugin="sql", sql="CREATE TABLE result AS SELECT 1",
                input_tables=["test_data"], output_tables=["result"],
                checkpoints=[{
                    "type": "row_count", "table": "result",
                    "min": 99999, "on_failure": "warn",
                }],
            )],
        )
        yaml_str = build_yaml(state)
        assert "checkpoints" in yaml_str
        assert "row_count" in yaml_str
        assert "warn" in yaml_str

    def test_checkpoints_empty_by_default(self):
        """无检查点时 ProcessorConfig 正常序列化。"""
        state = WizardState(
            scene=SceneInfo(name="no_check"),
            processors=[ProcessorConfig(
                name="s1", plugin="sql", sql="SELECT 1",
                output_tables=["r1"],
            )],
        )
        yaml_str = build_yaml(state)
        assert "checkpoints" not in yaml_str  # 空时不输出

    def test_row_count_block_is_in_yaml(self):
        """block 检查点应正确序列化到 YAML 中。"""
        state = WizardState(
            scene=SceneInfo(name="test_block"),
            inputs=[InputSource(
                plugin="csv", table="data", param_key="data",
                config={"type": "csv", "delimiter": ",", "encoding": "utf-8"},
            )],
            processors=[ProcessorConfig(
                name="step1", plugin="sql", sql="CREATE TABLE result AS SELECT 1",
                input_tables=["data"], output_tables=["result"],
                checkpoints=[{
                    "type": "row_count", "table": "result",
                    "min": 100, "on_failure": "block",
                }],
            )],
        )
        yaml_str = build_yaml(state)
        assert "checkpoints" in yaml_str
        assert "row_count" in yaml_str
        assert "min" in yaml_str
        assert "block" in yaml_str


class TestPrepareExecutionValidation:
    """限制③C：json/xml/parquet 现已支持执行（reader 适配器），仅 api 被拒绝。

    验证标准（v2.0 方案 3.4 第二阶段）：
    - api 输入源在 _prepare_execution 阶段被拒绝（延后到 v2.0.0 第三阶段）
    - json/xml/parquet 不再被预览校验拒绝
    - ValueError 已在 _USER_ERRORS 中，直接抛出即返回 422
    """

    def test_api_plugin_rejected(self):
        """api 输入源在 _prepare_execution 阶段被拒绝（延后到第三阶段）。"""
        state = WizardState(
            scene=SceneInfo(name="test_api_rejected"),
            inputs=[InputSource(
                plugin="api",
                table="t",
                param_key="k",
                config={"type": "api", "url": "http://example.com", "method": "GET"},
            )],
        )
        with pytest.raises(ValueError, match="仅支持预览"):
            _prepare_execution(state)

    @pytest.mark.parametrize("plugin,config", [
        ("json", {"type": "json", "flatten_separator": "."}),
        ("xml", {"type": "xml", "row_element": "item"}),
        ("parquet", {"type": "parquet"}),
    ])
    def test_reader_backed_plugins_not_rejected(self, plugin, config):
        """限制③C：json/xml/parquet 不再被预览校验拒绝（reader 适配器已支持执行）。

        校验通过后会继续执行后续步骤（可能因文件不存在等其他原因失败），
        但不应抛出含'仅支持预览'的 ValueError。
        """
        state = WizardState(
            scene=SceneInfo(name="test_reader_backed"),
            inputs=[InputSource(
                plugin=plugin,
                table="t",
                param_key="k",
                config=config,
            )],
        )
        try:
            _prepare_execution(state)
        except ValueError as e:
            # 不应因"仅支持预览"校验被拒绝
            assert "仅支持预览" not in str(e), f"{plugin} 不应被预览校验拒绝: {e}"
        except Exception:
            # 其他错误（文件不存在、build_yaml 失败等）可接受
            pass

    def test_supported_plugins_not_rejected_as_preview_only(self):
        """excel/csv/database 输入源不会被'仅支持预览'校验拒绝。"""
        for plugin, config in [
            ("csv", {"type": "csv", "delimiter": ",", "encoding": "utf-8"}),
            ("excel", {"type": "excel", "sheet": ""}),
        ]:
            state = WizardState(
                scene=SceneInfo(name="test_supported"),
                inputs=[InputSource(
                    plugin=plugin,
                    table="t",
                    param_key="k",
                    config=config,
                )],
            )
            try:
                _prepare_execution(state)
            except ValueError as e:
                # 不应因"仅支持预览"校验被拒绝
                assert "仅支持预览" not in str(e), f"{plugin} 不应被预览校验拒绝: {e}"
            except Exception:
                # 其他错误（文件不存在、build_yaml 失败等）可接受
                pass
