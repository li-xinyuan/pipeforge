import pytest
from unittest.mock import patch, MagicMock
from configforge.core.pipeline import _has_ddl, init_scene, infer_output, generate
from configforge.models.wizard import (
    SceneInitRequest,
    OutputInferRequest,
    WizardState,
    SceneInfo,
    InputSource,
    ProcessorConfig,
    OutputTarget,
    ExcelOutputConfig,
    ColumnMappingItem,
)


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
        assert _has_ddl("WITH cte AS (SELECT * FROM t) SELECT * FROM cte") is False

    def test_indented_create_table(self):
        assert _has_ddl("\n  CREATE TABLE foo AS SELECT 1") is True

    def test_create_in_lowercase(self):
        assert _has_ddl("create table foo (id int)") is True

    def test_insert_in_lowercase(self):
        assert _has_ddl("insert into foo values (1)") is True

    def test_empty_sql(self):
        assert _has_ddl("") is False

    def test_comment_with_create(self):
        # regex requires CREATE at start of string — comments before DDL not matched
        assert _has_ddl("-- comment\nCREATE TABLE foo (id INT)") is False

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
            processor=ProcessorConfig(sql="SELECT 1", output_tables=["out1"]),
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
            processor=ProcessorConfig(sql="SELECT * FROM csv_t", output_tables=["res"]),
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
            processor=ProcessorConfig(sql="", output_tables=[]),
            output=None,
        )
        result = generate(state)
        assert "yaml" in result
        assert "outputs:" not in result["yaml"]  # no output → no output section in YAML
