def read_parquet_info(file_path: str, max_sample_rows: int = 10) -> dict:
    """Read Parquet file, return columns and sample_rows (same interface as read_excel_info).

    Args:
        file_path: Path to the Parquet file on disk
        max_sample_rows: Max number of sample rows to return
    """
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "pyarrow is required for Parquet support. "
            "Install it with: pip install pyarrow"
        )

    table = pq.read_table(file_path)
    schema = table.schema

    columns = [field.name for field in schema]
    num_rows = table.num_rows

    sample_rows = []
    for i in range(min(num_rows, max_sample_rows)):
        row = []
        for col_name in columns:
            val = table.column(col_name)[i].as_py()
            row.append(str(val) if val is not None else "")
        sample_rows.append(row)

    return {
        "sheets": [],
        "columns": columns,
        "sample_rows": sample_rows,
    }
