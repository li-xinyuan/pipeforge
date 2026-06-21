def read_parquet_info(file_path: str, max_sample_rows: int = 100) -> dict:
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

    pf = pq.ParquetFile(file_path)
    schema = pf.schema_arrow

    columns = [field.name for field in schema]

    sample_rows = []
    for batch in pf.iter_batches(batch_size=100):
        for i in range(batch.num_rows):
            if len(sample_rows) >= max_sample_rows:
                break
            row = []
            for col_name in columns:
                val = batch.column(col_name)[i].as_py()
                row.append(str(val) if val is not None else "")
            sample_rows.append(row)
        if len(sample_rows) >= max_sample_rows:
            break

    return {
        "sheets": [],
        "columns": columns,
        "sample_rows": sample_rows,
    }
