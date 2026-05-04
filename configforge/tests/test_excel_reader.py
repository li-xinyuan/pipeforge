import io
import openpyxl
from configforge.services.excel_reader import read_excel_info


def make_xlsx(headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def test_read_columns_and_sample():
    buf = make_xlsx(["姓名", "部门", "工号"], [["张三", "研发", "001"], ["李四", "产品", "002"]])
    info = read_excel_info(buf)
    assert info["columns"] == ["姓名", "部门", "工号"]
    assert len(info["sample_rows"]) == 2
    assert info["sample_rows"][0] == ["张三", "研发", "001"]


def test_read_sheet_names():
    buf = make_xlsx(["A"], [["x"]])
    info = read_excel_info(buf)
    assert "Sheet" in info["sheets"][0]
