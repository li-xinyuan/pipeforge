import pytest


@pytest.fixture
def sample_parquet_file(tmp_path):
    """创建一个示例 Parquet 文件用于测试。"""
    pyarrow = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq

    table = pyarrow.table({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    file_path = str(tmp_path / "test.parquet")
    pq.write_table(table, file_path)
    return file_path


@pytest.fixture
def parquet_with_none(tmp_path):
    """创建包含 None 值的 Parquet 文件用于测试。"""
    pyarrow = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq

    table = pyarrow.table({"col1": [1, None, 3], "col2": ["a", "b", None]})
    file_path = str(tmp_path / "test_none.parquet")
    pq.write_table(table, file_path)
    return file_path


class TestReadParquetInfo:
    def test_returns_correct_structure(self, sample_parquet_file):
        from configforge.services.parquet_reader import read_parquet_info

        result = read_parquet_info(sample_parquet_file)
        assert isinstance(result, dict)
        assert "sheets" in result
        assert "columns" in result
        assert "sample_rows" in result

    def test_returns_correct_columns(self, sample_parquet_file):
        from configforge.services.parquet_reader import read_parquet_info

        result = read_parquet_info(sample_parquet_file)
        assert result["columns"] == ["col1", "col2"]

    def test_returns_sample_rows_as_list_of_lists(self, sample_parquet_file):
        from configforge.services.parquet_reader import read_parquet_info

        result = read_parquet_info(sample_parquet_file)
        assert isinstance(result["sample_rows"], list)
        for row in result["sample_rows"]:
            assert isinstance(row, list)

    def test_respects_max_sample_rows_limit(self, tmp_path):
        pyarrow = pytest.importorskip("pyarrow")
        import pyarrow.parquet as pq

        from configforge.services.parquet_reader import read_parquet_info

        table = pyarrow.table({"col1": list(range(200)), "col2": list(range(200))})
        file_path = str(tmp_path / "large.parquet")
        pq.write_table(table, file_path)

        result = read_parquet_info(file_path, max_sample_rows=5)
        assert len(result["sample_rows"]) == 5

    def test_handles_none_values_as_empty_string(self, parquet_with_none):
        from configforge.services.parquet_reader import read_parquet_info

        result = read_parquet_info(parquet_with_none)
        # 第二行: col1=None, col2="b"
        assert result["sample_rows"][1][0] == ""
        assert result["sample_rows"][1][1] == "b"
        # 第三行: col1=3, col2=None
        assert result["sample_rows"][2][0] == "3"
        assert result["sample_rows"][2][1] == ""

    def test_returns_empty_sheets_list(self, sample_parquet_file):
        from configforge.services.parquet_reader import read_parquet_info

        result = read_parquet_info(sample_parquet_file)
        assert result["sheets"] == []


class TestReadParquetInfoFileNotFound:
    def test_raises_error_for_nonexistent_file(self):
        from configforge.services.parquet_reader import read_parquet_info

        with pytest.raises(Exception):
            read_parquet_info("/nonexistent/path/to/file.parquet")


class TestReadParquetInfoImportError:
    def test_raises_import_error_without_pyarrow(self, sample_parquet_file, monkeypatch):
        import sys

        from configforge.services.parquet_reader import read_parquet_info

        # 保存原始的 pyarrow 模块引用
        original_pa = sys.modules.get("pyarrow")
        original_pq = sys.modules.get("pyarrow.parquet")

        # 移除已加载的 pyarrow 模块
        if "pyarrow" in sys.modules:
            del sys.modules["pyarrow"]
        if "pyarrow.parquet" in sys.modules:
            del sys.modules["pyarrow.parquet"]

        # 让 import pyarrow.parquet 抛出 ImportError
        import_orig = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def mock_import(name, *args, **kwargs):
            if name == "pyarrow" or name.startswith("pyarrow."):
                raise ImportError("No module named 'pyarrow'")
            return import_orig(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        try:
            with pytest.raises(ImportError, match="pyarrow is required"):
                read_parquet_info(sample_parquet_file)
        finally:
            # 恢复原始模块
            if original_pa is not None:
                sys.modules["pyarrow"] = original_pa
            if original_pq is not None:
                sys.modules["pyarrow.parquet"] = original_pq
