import pytest
from configforge.generators.output.excel_output import ExcelOutputGenerator
from configforge.models.wizard import ExcelOutputConfig, ColumnMappingItem


def test_build_config():
    gen = ExcelOutputGenerator()
    state = {
        "template": "templates/report.xlsx",
        "sheet": "报表",
        "output_dir": "./output/",
        "source_table": "monthly_report",
        "filename": "report_{{date:%Y%m%d}}.xlsx",
        "columns": [{"source": "姓名", "target": "姓名"}],
    }
    config = gen.build_config(state)
    assert config.template == "templates/report.xlsx"
    assert config.source_table == "monthly_report"
    assert len(config.columns) == 1


def test_validate_empty_columns():
    gen = ExcelOutputGenerator()
    errors = gen.validate_config(ExcelOutputConfig(
        template="t.xlsx", source_table="t1", filename="f.xlsx", columns=[],
    ))
    assert any("columns" in e.lower() for e in errors)


def test_validate_missing_template():
    gen = ExcelOutputGenerator()
    errors = gen.validate_config(ExcelOutputConfig(
        template="", source_table="t1", filename="f.xlsx",
        columns=[ColumnMappingItem(source="a", target="a")],
    ))
    assert any("template" in e.lower() for e in errors)
