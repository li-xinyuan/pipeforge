import io, pytest
from configforge.generators.input.excel_input import ExcelInputGenerator
from configforge.models.wizard import ExcelInputConfig


def test_infer_config_from_excel_info():
    gen = ExcelInputGenerator()
    config = gen.infer_config({"file_id": "f1", "type": "excel", "columns": ["姓名", "部门"], "original_name": "person.xlsx"})
    assert config.type == "excel"
    assert config.sheet == "Sheet1"


def test_build_config_from_wizard_state():
    gen = ExcelInputGenerator()
    state = {"name": "人员明细", "table": "person", "param_key": "person_file", "file_id": "f1", "sheet": "人员列表"}
    config = gen.build_config(state)
    assert config.sheet == "人员列表"


def test_validate_empty_sheet_rejected():
    gen = ExcelInputGenerator()
    errors = gen.validate_config(ExcelInputConfig(sheet=""))
    assert any("Sheet" in str(e) for e in errors)
