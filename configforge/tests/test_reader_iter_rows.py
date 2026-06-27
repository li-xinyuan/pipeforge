"""限制③C reader 全量读取接口测试（Day 4）

验证 iter_json_rows / iter_xml_rows / iter_parquet_rows 的全量读取行为。
这是 ReaderBackedInputPlugin 的数据源接口，Day 5-7 将实现适配器。

关键验证点：
1. 返回 (columns, row_iterator) 结构
2. 列名是所有行键的并集（json/xml）
3. 行迭代器产出 tuple，缺失键补 ""
4. 全量数据正确（与 read_xxx_info 的 columns 一致）
"""
import json
import tempfile
from pathlib import Path

import pytest

from configforge.services.json_reader import iter_json_rows
from configforge.services.xml_reader import iter_xml_rows
from configforge.services.parquet_reader import iter_parquet_rows


# ---------------------------------------------------------------------------
# iter_json_rows
# ---------------------------------------------------------------------------
class TestIterJsonRows:
    def test_returns_columns_and_iterator(self):
        """返回 (columns, iterator) 结构。"""
        content = json.dumps([{"a": 1, "b": 2}]).encode("utf-8")
        columns, row_iter = iter_json_rows(content)
        assert isinstance(columns, list)
        assert hasattr(row_iter, "__iter__")

    def test_simple_array(self):
        """简单数组全量读取。"""
        content = json.dumps([
            {"a": 1, "b": 2},
            {"a": 3, "b": 4},
        ]).encode("utf-8")
        columns, row_iter = iter_json_rows(content)
        assert columns == ["a", "b"]
        rows = list(row_iter)
        assert rows == [("1", "2"), ("3", "4")]

    def test_heterogeneous_keys_union(self):
        """不同行有不同键，列名取并集，缺失键补 ""。"""
        content = json.dumps([
            {"a": 1, "b": 2},
            {"a": 3, "c": 4},
        ]).encode("utf-8")
        columns, row_iter = iter_json_rows(content)
        assert set(columns) == {"a", "b", "c"}
        rows = list(row_iter)
        assert len(rows) == 2
        # 第二行缺 b，应为 ""
        b_idx = columns.index("b")
        assert rows[1][b_idx] == ""

    def test_nested_flatten(self):
        """嵌套对象拍平。"""
        content = json.dumps([
            {"user": {"name": "alice", "age": 30}},
        ]).encode("utf-8")
        columns, row_iter = iter_json_rows(content, flatten_separator=".")
        assert "user.name" in columns
        assert "user.age" in columns
        rows = list(row_iter)
        assert rows[0][columns.index("user.name")] == "alice"

    def test_empty_array(self):
        """空数组返回空列+空迭代器。"""
        content = json.dumps([]).encode("utf-8")
        columns, row_iter = iter_json_rows(content)
        assert columns == []
        assert list(row_iter) == []

    def test_single_object_wrapped(self):
        """单个对象（非数组）被包装为数组。"""
        content = json.dumps({"x": 1, "y": 2}).encode("utf-8")
        columns, row_iter = iter_json_rows(content)
        assert set(columns) == {"x", "y"}
        rows = list(row_iter)
        assert len(rows) == 1

    def test_none_value_becomes_empty(self):
        """None 值转为 ""。"""
        content = json.dumps([{"a": None, "b": "val"}]).encode("utf-8")
        columns, row_iter = iter_json_rows(content)
        rows = list(row_iter)
        a_idx = columns.index("a")
        assert rows[0][a_idx] == ""

    def test_columns_match_read_info(self):
        """iter_rows 的列名与 read_json_info 的 columns 一致。"""
        from configforge.services.json_reader import read_json_info

        content = json.dumps([
            {"a": 1, "b": 2},
            {"a": 3, "c": 4},
        ]).encode("utf-8")
        iter_cols, _ = iter_json_rows(content)
        info = read_json_info(content)
        assert set(iter_cols) == set(info["columns"])


# ---------------------------------------------------------------------------
# iter_xml_rows
# ---------------------------------------------------------------------------
class TestIterXmlRows:
    def test_returns_columns_and_iterator(self):
        """返回 (columns, iterator) 结构。"""
        content = b"<root><item><a>1</a></item></root>"
        columns, row_iter = iter_xml_rows(content, row_element="item")
        assert isinstance(columns, list)
        assert hasattr(row_iter, "__iter__")

    def test_explicit_row_element(self):
        """显式 row_element 全量读取。"""
        content = b"""<root>
            <item><a>1</a><b>2</b></item>
            <item><a>3</a><b>4</b></item>
        </root>"""
        columns, row_iter = iter_xml_rows(content, row_element="item")
        assert set(columns) == {"a", "b"}
        rows = list(row_iter)
        assert len(rows) == 2
        assert rows[0] == ("1", "2")

    def test_auto_detect_row_element(self):
        """自动检测最高频子元素。"""
        content = b"""<root>
            <item><a>1</a></item>
            <item><a>2</a></item>
            <other>x</other>
        </root>"""
        columns, row_iter = iter_xml_rows(content)  # 无 row_element
        rows = list(row_iter)
        assert len(rows) == 2  # item 出现 2 次

    def test_heterogeneous_keys_union(self):
        """不同行元素有不同子元素，列名取并集。"""
        content = b"""<root>
            <item><a>1</a><b>2</b></item>
            <item><a>3</a><c>4</c></item>
        </root>"""
        columns, row_iter = iter_xml_rows(content, row_element="item")
        assert set(columns) == {"a", "b", "c"}
        rows = list(row_iter)
        # 第二行缺 b
        b_idx = columns.index("b")
        assert rows[1][b_idx] == ""

    def test_attributes_prefixed(self):
        """属性用 @ 前缀。"""
        content = b'<root><item id="5"><name>x</name></item></root>'
        columns, row_iter = iter_xml_rows(content, row_element="item")
        assert "@id" in columns
        assert "name" in columns
        rows = list(row_iter)
        assert rows[0][columns.index("@id")] == "5"

    def test_empty_xml(self):
        """无匹配行元素返回空。"""
        content = b"<root></root>"
        columns, row_iter = iter_xml_rows(content, row_element="nonexistent")
        assert columns == []
        assert list(row_iter) == []


# ---------------------------------------------------------------------------
# iter_parquet_rows
# ---------------------------------------------------------------------------
class TestIterParquetRows:
    def _make_parquet(self, tmp_path: Path) -> str:
        """生成测试用 Parquet 文件。"""
        import pyarrow as pa
        import pyarrow.parquet as pq

        table = pa.table({
            "a": [1, 2, 3],
            "b": ["x", "y", "z"],
        })
        path = tmp_path / "test.parquet"
        pq.write_table(table, path)
        return str(path)

    def test_returns_columns_and_iterator(self, tmp_path):
        """返回 (columns, iterator) 结构。"""
        path = self._make_parquet(tmp_path)
        columns, row_iter = iter_parquet_rows(path)
        assert isinstance(columns, list)
        assert hasattr(row_iter, "__iter__")

    def test_full_read(self, tmp_path):
        """全量读取 Parquet。"""
        path = self._make_parquet(tmp_path)
        columns, row_iter = iter_parquet_rows(path)
        assert columns == ["a", "b"]
        rows = list(row_iter)
        assert len(rows) == 3
        assert rows[0] == ("1", "x")
        assert rows[2] == ("3", "z")

    def test_columns_match_read_info(self, tmp_path):
        """iter_rows 的列名与 read_parquet_info 的 columns 一致。"""
        from configforge.services.parquet_reader import read_parquet_info

        path = self._make_parquet(tmp_path)
        iter_cols, _ = iter_parquet_rows(path)
        info = read_parquet_info(path)
        assert iter_cols == info["columns"]

    def test_none_value_becomes_empty(self, tmp_path):
        """None 值转为 ""。"""
        import pyarrow as pa
        import pyarrow.parquet as pq

        table = pa.table({
            "a": [1, None, 3],
            "b": ["x", "y", None],
        })
        path = tmp_path / "nulls.parquet"
        pq.write_table(table, path)

        columns, row_iter = iter_parquet_rows(str(path))
        rows = list(row_iter)
        # 第二行 a 为 None
        a_idx = columns.index("a")
        assert rows[1][a_idx] == ""
        # 第三行 b 为 None
        b_idx = columns.index("b")
        assert rows[2][b_idx] == ""
