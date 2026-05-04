import io
import openpyxl


def build_template(headers: list[str]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
