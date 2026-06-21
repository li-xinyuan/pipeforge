"""Tests for JSON reader."""
import json

import pytest

from configforge.services.json_reader import _flatten, read_json_info


class TestFlatten:
    def test_flat_dict(self):
        result = _flatten({"a": 1, "b": "hello"})
        assert result == {"a": 1, "b": "hello"}

    def test_nested_dict(self):
        result = _flatten({"parent": {"child": "value"}})
        assert result == {"parent.child": "value"}

    def test_deeply_nested(self):
        result = _flatten({"a": {"b": {"c": 1}}})
        assert result == {"a.b.c": 1}

    def test_list_value(self):
        result = _flatten({"tags": ["a", "b"]})
        assert result == {"tags": '["a", "b"]'}

    def test_empty_list(self):
        result = _flatten({"tags": []})
        assert result == {"tags": ""}

    def test_none_value(self):
        result = _flatten({"name": None})
        assert result == {"name": ""}

    def test_custom_separator(self):
        result = _flatten({"a": {"b": 1}}, separator="_")
        assert result == {"a_b": 1}


class TestReadJsonInfo:
    def test_array_of_objects(self):
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        content = json.dumps(data).encode("utf-8")
        result = read_json_info(content)
        assert result["columns"] == ["name", "age"]
        assert len(result["sample_rows"]) == 2
        assert result["sample_rows"][0] == ["Alice", "30"]

    def test_single_object(self):
        data = {"name": "Alice", "age": 30}
        content = json.dumps(data).encode("utf-8")
        result = read_json_info(content)
        assert result["columns"] == ["name", "age"]
        assert len(result["sample_rows"]) == 1

    def test_nested_objects(self):
        data = [{"user": {"name": "Alice"}, "score": 100}]
        content = json.dumps(data).encode("utf-8")
        result = read_json_info(content)
        assert "user.name" in result["columns"]
        assert "score" in result["columns"]

    def test_empty_array(self):
        result = read_json_info(b"[]")
        assert result["columns"] == []
        assert result["sample_rows"] == []

    def test_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            read_json_info(b"not json")

    def test_missing_keys(self):
        data = [{"a": 1, "b": 2}, {"a": 3, "c": 4}]
        content = json.dumps(data).encode("utf-8")
        result = read_json_info(content)
        assert set(result["columns"]) == {"a", "b", "c"}
        assert result["sample_rows"][1] == ["3", "", "4"]

    def test_custom_separator(self):
        data = [{"parent": {"child": "value"}}]
        content = json.dumps(data).encode("utf-8")
        result = read_json_info(content, flatten_separator="_")
        assert "parent_child" in result["columns"]
