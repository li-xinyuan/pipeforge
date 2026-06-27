from typing import Iterator


def iter_parquet_rows(file_path: str) -> tuple[list[str], Iterator[tuple]]:
    """全量读取 Parquet，返回 (列名列表, 行迭代器)。

    限制③C reader 适配器第一步：为 ReaderBackedInputPlugin 提供全量读取接口。
    与 read_parquet_info（轻量预览）不同，本函数流式产出所有行，供 pipeline 执行。

    Parquet 的 schema 在文件头声明（schema_arrow），列名已知，无需两遍扫描。
    用 pyarrow 的 iter_batches(batch_size=100) 分批流式读取，避免一次性加载全表。

    Args:
        file_path: Parquet 文件磁盘路径

    Returns:
        (columns, row_iterator): 列名列表 + 行元组迭代器
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

    def _row_iter() -> Iterator[tuple]:
        for batch in pf.iter_batches(batch_size=100):
            for i in range(batch.num_rows):
                row = []
                for col_name in columns:
                    val = batch.column(col_name)[i].as_py()
                    row.append(str(val) if val is not None else "")
                yield tuple(row)

    return columns, _row_iter()


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
