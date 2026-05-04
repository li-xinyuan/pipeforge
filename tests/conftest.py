import tempfile
import os
import copy

import pytest
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


@pytest.fixture
def sample_xlsx():
    """Create a test Excel file with person details."""
    wb = Workbook()
    ws = wb.active
    ws.title = "人员列表"
    ws.append(["工号", "姓名", "部门", "岗位"])
    ws.append(["001", "张三", "技术部", "工程师"])
    ws.append(["002", "李四", "产品部", "产品经理"])
    ws.append(["003", "王五", "技术部", "高级工程师"])

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    yield path
    os.unlink(path)


@pytest.fixture
def sample_xlsx_attendance():
    """Create a test Excel file with attendance data."""
    wb = Workbook()
    ws = wb.active
    ws.title = "考勤统计"
    ws.append(["工号", "出勤天数", "迟到次数"])
    ws.append(["001", "22", "1"])
    ws.append(["002", "20", "4"])
    ws.append(["003", "21", "0"])

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    yield path
    os.unlink(path)


@pytest.fixture
def template_xlsx():
    """Create a styled Excel template for output."""
    wb = Workbook()
    ws = wb.active
    ws.title = "报表"

    header_font = Font(name="微软雅黑", bold=True, size=12)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

    headers = ["姓名", "所属部门", "岗位", "出勤天数", "迟到次数", "状态"]
    for i, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=i, value=h)
        cell.font = copy.copy(header_font)
        cell.fill = copy.copy(header_fill)

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 15
    ws.freeze_panes = "A2"

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    yield path
    os.unlink(path)
