import io
from configforge.models.wizard import (
    WizardState, SceneInfo, InputSource, ProcessorConfig, OutputTarget,
    ExcelOutputConfig, ExcelInputConfig, ColumnMappingItem
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
