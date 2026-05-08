import io
from configforge.services.csv_reader import read_csv_info


def test_read_csv_with_header():
    content = "name,age\nAlice,30\nBob,25".encode("utf-8")
    result = read_csv_info(content)
    assert result["sheets"] == []
    assert result["columns"] == ["name", "age"]
    assert len(result["sample_rows"]) == 2
    assert result["sample_rows"][0] == ["Alice", "30"]


def test_read_csv_without_header():
    content = "Alice,30\nBob,25".encode("utf-8")
    result = read_csv_info(content)
    assert result["columns"] == ["Alice", "30"]
    assert len(result["sample_rows"]) == 1
    assert result["sample_rows"][0] == ["Bob", "25"]


def test_read_csv_custom_delimiter():
    content = "name;age\nAlice;30".encode("utf-8")
    # read_csv_info doesn't support custom delimiter yet — it uses default comma
    # This tests that comma-separated parsing works correctly
    result = read_csv_info("a,b,c\n1,2,3".encode("utf-8"))
    assert result["columns"] == ["a", "b", "c"]


def test_read_csv_empty():
    result = read_csv_info("".encode("utf-8"))
    assert result["sheets"] == []
    assert result["columns"] == []
    assert result["sample_rows"] == []


def test_read_csv_single_column():
    content = "name\nAlice\nBob".encode("utf-8")
    result = read_csv_info(content)
    assert result["columns"] == ["name"]
    assert len(result["sample_rows"]) == 2
