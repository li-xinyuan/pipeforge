import csv
import io


MAX_CSV_ROWS = 50000


def read_csv_info(file_content: bytes, delimiter: str = ",", encoding: str = "utf-8", max_rows: int = MAX_CSV_ROWS) -> dict:
    """Read CSV file content, return columns and sample_rows (same interface as read_excel_info)."""
    text = file_content.decode(encoding)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)

    rows = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            break
        rows.append(row)
    if not rows:
        return {"sheets": [], "columns": [], "sample_rows": []}

    columns = [str(c).strip() for c in rows[0]]
    sample_rows = [[str(v) for v in row] for row in rows[1:11]]

    return {
        "sheets": [],
        "columns": columns,
        "sample_rows": sample_rows,
    }
