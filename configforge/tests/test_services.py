import io
from configforge.models.wizard import (
    WizardState, SceneInfo, InputSource, ProcessorConfig, OutputTarget,
    ExcelOutputConfig, ExcelInputConfig, CsvInputConfig, CsvOutputConfig, ColumnMappingItem
)
from configforge.services.yaml_builder import build_yaml
from configforge.services.template_builder import build_template


def test_build_yaml_has_all_sections():
    state = WizardState(
        scene=SceneInfo(name="测试", description="测试描述", version="1.0"),
        inputs=[InputSource(name="in1", plugin="excel", table="t1", param_key="f1", file_id="x1",
                             config=ExcelInputConfig(sheet="Sheet1"))],
        processor=ProcessorConfig(sql="SELECT 1", output_tables=["t1"]),
        output=OutputTarget(plugin="excel", config=ExcelOutputConfig(
            template="t.xlsx", source_table="t1", filename="out.xlsx",
            columns=[ColumnMappingItem(source="a", target="a")],
        )),
    )
    y = build_yaml(state)
    assert "scene:" in y
    assert "inputs:" in y
    assert "processors:" in y
    assert "output:" in y
    assert "snake_case" not in y
    assert "source_table" in y


def test_build_template_returns_bytes():
    buf = build_template(["姓名", "部门"])
    assert isinstance(buf, io.BytesIO)


def test_build_yaml_with_csv_input():
    """YAML should include CSV-specific fields (delimiter, encoding, has_header) for CSV inputs."""
    state = WizardState(
        scene=SceneInfo(name="CSV测试", description="", version="1.0"),
        inputs=[InputSource(
            name="csv_in", plugin="csv", table="t1", param_key="f1", file_id="x1",
            config=CsvInputConfig(delimiter=",", encoding="utf-8", has_header=True),
        )],
        processor=ProcessorConfig(sql="SELECT 1", output_tables=["t1"]),
        output=None,
    )
    y = build_yaml(state)
    assert "type: csv" in y
    assert "delimiter:" in y
    assert "encoding:" in y
    assert "has_header:" in y
    assert "sheet:" not in y  # CSV should NOT have sheet


def test_build_yaml_with_csv_output():
    """YAML should include CSV-specific fields for CSV output, not template/sheet."""
    state = WizardState(
        scene=SceneInfo(name="CSV输出", description="", version="1.0"),
        inputs=[],
        processor=ProcessorConfig(sql="SELECT 1", output_tables=["t1"]),
        output=OutputTarget(
            plugin="csv",
            config=CsvOutputConfig(
                source_table="t1", filename="out.csv",
                delimiter=";", encoding="gbk",
                columns=[ColumnMappingItem(source="a", target="a")],
            ),
        ),
    )
    y = build_yaml(state)
    assert "type: csv" in y
    assert "delimiter: ;" in y or "delimiter: ';'" in y
    assert "encoding: gbk" in y
    assert "template:" not in y  # CSV should NOT have template
    assert "sheet:" not in y  # CSV should NOT have sheet


def test_build_yaml_still_works_for_excel():
    """Existing Excel test should still pass — Excel paths unaffected."""
    state = WizardState(
        scene=SceneInfo(name="测试", description="测试描述", version="1.0"),
        inputs=[InputSource(name="in1", plugin="excel", table="t1", param_key="f1", file_id="x1",
                             config=ExcelInputConfig(sheet="Sheet1"))],
        processor=ProcessorConfig(sql="SELECT 1", output_tables=["t1"]),
        output=OutputTarget(plugin="excel", config=ExcelOutputConfig(
            template="t.xlsx", source_table="t1", filename="out.xlsx",
            columns=[ColumnMappingItem(source="a", target="a")],
        )),
    )
    y = build_yaml(state)
    assert "scene:" in y
    assert "sheet: Sheet1" in y
    assert "template: t.xlsx" in y
