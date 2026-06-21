"""Tests for API reader."""
from unittest.mock import MagicMock, patch

import pytest

from configforge.services.api_reader import _extract_data, read_api_info


class TestExtractData:
    def test_array_response(self):
        data = [{"name": "Alice"}, {"name": "Bob"}]
        result = _extract_data(data, "")
        assert len(result) == 2

    def test_nested_path(self):
        data = {"data": {"items": [{"name": "Alice"}]}}
        result = _extract_data(data, "data.items")
        assert len(result) == 1

    def test_single_object(self):
        data = {"name": "Alice"}
        result = _extract_data(data, "")
        assert len(result) == 1

    def test_empty_path_missing_key(self):
        data = {"other": []}
        result = _extract_data(data, "data.items")
        assert result == []


class TestReadApiInfo:
    @patch("configforge.services.api_reader.httpx.Client")
    def test_simple_get(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"name": "Alice", "age": 30}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = read_api_info(url="https://api.example.com/users")
        assert "name" in result["columns"]
        assert "age" in result["columns"]
        assert len(result["sample_rows"]) == 1

    @patch("configforge.services.api_reader.httpx.Client")
    def test_with_data_path(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"users": [{"name": "Alice"}]}}
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = read_api_info(url="https://api.example.com", data_path="data.users")
        assert "name" in result["columns"]

    @patch("configforge.services.api_reader.httpx.Client")
    def test_http_error(self, mock_client_cls):
        import httpx
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")
        mock_client_cls.return_value = mock_client

        with pytest.raises(ValueError, match="API request failed"):
            read_api_info(url="https://api.example.com")

    @patch("configforge.services.api_reader.httpx.Client")
    def test_post_method(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = read_api_info(url="https://api.example.com", method="POST", body={"query": "test"})
        assert "id" in result["columns"]
