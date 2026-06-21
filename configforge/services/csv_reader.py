import csv

MAX_CSV_ROWS = 100


def read_csv_info(file_path: str, delimiter: str = ",", encoding: str = "utf-8", max_sample_rows: int = MAX_CSV_ROWS) -> dict:
    """Read CSV file content in streaming fashion, return columns and sample_rows (same interface as read_excel_info)."""
    with open(file_path, encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter)

        try:
            header = next(reader)
        except StopIteration:
            return {"sheets": [], "columns": [], "sample_rows": []}

        columns = [str(c).strip() for c in header]
        sample_rows = []
        for i, row in enumerate(reader):
            if i >= max_sample_rows:
                break
            sample_rows.append([str(v) for v in row])

    return {
        "sheets": [],
        "columns": columns,
        "sample_rows": sample_rows,
    }
