import tempfile
import os

import pytest
from openpyxl import Workbook

from pipeforge.plugins.input.excel import ExcelInputPlugin, read_excel_rows
from pipeforge.plugins.input import ExcelInputPlugin as ImportedPlugin
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.context import Context
from pipeforge.config.models import ExcelInputConfig


@pytest.fixture
def sample_xlsx():
    """创建一个简单的测试 Excel 文件。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "人员列表"
    ws.append(["姓名", "部门", "年龄"])
    ws.append(["张三", "技术部", "30"])
    ws.append(["李四", "产品部", "28"])

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    yield path
    os.unlink(path)


class TestReadExcelRows:
    def test_read_excel_rows(self, sample_xlsx):
        columns, rows = read_excel_rows(sample_xlsx, "人员列表")
        assert columns == ["姓名", "部门", "年龄"]
        data = list(rows)
        assert len(data) == 2
        assert data[0] == ("张三", "技术部", "30")
        assert data[1] == ("李四", "产品部", "28")

    def test_read_excel_rows_default_sheet(self, sample_xlsx):
        columns, rows = read_excel_rows(sample_xlsx, None)
        assert columns == ["姓名", "部门", "年龄"]

    def test_empty_file_raises(self):
        wb = Workbook()
        ws = wb.active
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        wb.save(path)

        try:
            with pytest.raises(ValueError, match="header"):
                read_excel_rows(path, "Sheet")
        finally:
            os.unlink(path)

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            read_excel_rows("/nonexistent/file.xlsx", "Sheet1")


class TestExcelInputPlugin:
    def test_config_model(self):
        assert ExcelInputPlugin.config_model() == ExcelInputConfig

    def test_execute_writes_to_db(self, sample_xlsx):
        db = SQLiteManager()
        context = Context(db=db, params={}, yaml_dir="/tmp", scene_name="test")
        config = ExcelInputConfig(file=sample_xlsx, sheet="人员列表")

        plugin = ExcelInputPlugin()
        plugin.name = "excel"
        plugin.label = "人员明细"
        plugin.table_name = "person_detail"
        plugin.execute(context, config)

        assert db.table_exists("person_detail")
        rows = db.query("SELECT * FROM person_detail")
        assert len(rows) == 2
        assert rows[0] == ("张三", "技术部", "30")

        db.close()
        db.remove()
