"""Tests for SSRF protection (validate_url)."""
import pytest

from configforge.utils.security import validate_url


class TestValidateUrl:
    def test_allows_https(self):
        assert validate_url("https://api.example.com/data") == "https://api.example.com/data"

    def test_allows_http(self):
        assert validate_url("http://api.example.com/data") == "http://api.example.com/data"

    def test_rejects_ftp_scheme(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            validate_url("ftp://example.com/data")

    def test_rejects_file_scheme(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            validate_url("file:///etc/passwd")

    def test_rejects_empty_url(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_url("")

    def test_rejects_cloud_metadata(self):
        with pytest.raises(ValueError, match="metadata endpoint"):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_rejects_google_metadata(self):
        with pytest.raises(ValueError, match="metadata endpoint"):
            validate_url("http://metadata.google.internal/")

    def test_rejects_azure_metadata(self):
        with pytest.raises(ValueError, match="metadata endpoint"):
            validate_url("http://metadata.azure.com/")

    def test_rejects_private_ip_10(self):
        with pytest.raises(ValueError, match="internal IP"):
            validate_url("http://10.0.0.1/api")

    def test_rejects_private_ip_172(self):
        with pytest.raises(ValueError, match="internal IP"):
            validate_url("http://172.16.0.1/api")

    def test_rejects_private_ip_192(self):
        with pytest.raises(ValueError, match="internal IP"):
            validate_url("http://192.168.1.1/api")

    def test_rejects_loopback(self):
        with pytest.raises(ValueError, match="internal IP"):
            validate_url("http://127.0.0.1/api")

    def test_rejects_link_local(self):
        with pytest.raises(ValueError, match="internal IP"):
            validate_url("http://169.254.0.1/api")

    def test_allows_public_domain(self):
        assert validate_url("https://jsonplaceholder.typicode.com/users") == "https://jsonplaceholder.typicode.com/users"

    def test_rejects_no_hostname(self):
        with pytest.raises(ValueError, match="valid hostname"):
            validate_url("http://")
