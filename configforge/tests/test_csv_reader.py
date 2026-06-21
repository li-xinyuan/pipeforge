import os
import tempfile

from configforge.services.csv_reader import read_csv_info


def _write_temp_csv(content: bytes, suffix=".csv") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(content)
    return path


def test_read_csv_with_header():
    path = _write_temp_csv(b"name,age\nAlice,30\nBob,25")
    try:
        result = read_csv_info(path)
        assert result["sheets"] == []
        assert result["columns"] == ["name", "age"]
        assert len(result["sample_rows"]) == 2
        assert result["sample_rows"][0] == ["Alice", "30"]
    finally:
        os.unlink(path)


def test_read_csv_without_header():
    path = _write_temp_csv(b"Alice,30\nBob,25")
    try:
        result = read_csv_info(path)
        assert result["columns"] == ["Alice", "30"]
        assert len(result["sample_rows"]) == 1
        assert result["sample_rows"][0] == ["Bob", "25"]
    finally:
        os.unlink(path)


def test_read_csv_custom_delimiter():
    path = _write_temp_csv(b"name;age\nAlice;30")
    try:
        result = read_csv_info(path, delimiter=";")
        assert result["columns"] == ["name", "age"]
        assert result["sample_rows"][0] == ["Alice", "30"]
    finally:
        os.unlink(path)


def test_read_csv_tab_delimiter():
    path = _write_temp_csv(b"name\tage\nAlice\t30")
    try:
        result = read_csv_info(path, delimiter="\t")
        assert result["columns"] == ["name", "age"]
        assert result["sample_rows"][0] == ["Alice", "30"]
    finally:
        os.unlink(path)


def test_read_csv_gbk_encoding():
    path = _write_temp_csv("姓名,年龄\n张三,30".encode("gbk"))
    try:
        result = read_csv_info(path, encoding="gbk")
        assert result["columns"] == ["姓名", "年龄"]
        assert result["sample_rows"][0] == ["张三", "30"]
    finally:
        os.unlink(path)


def test_read_csv_empty():
    path = _write_temp_csv(b"")
    try:
        result = read_csv_info(path)
        assert result["sheets"] == []
        assert result["columns"] == []
        assert result["sample_rows"] == []
    finally:
        os.unlink(path)


def test_read_csv_single_column():
    path = _write_temp_csv(b"name\nAlice\nBob")
    try:
        result = read_csv_info(path)
        assert result["columns"] == ["name"]
        assert len(result["sample_rows"]) == 2
    finally:
        os.unlink(path)
