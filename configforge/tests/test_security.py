import pytest
from configforge.utils.security import validate_id


class TestValidateId:
    def test_valid_alphanumeric(self):
        assert validate_id("abc123") == "abc123"

    def test_valid_with_underscore(self):
        assert validate_id("my_file_id") == "my_file_id"

    def test_valid_with_hyphen(self):
        assert validate_id("file-001") == "file-001"

    def test_valid_with_dot(self):
        assert validate_id("file.xlsx") == "file.xlsx"

    def test_valid_uuid(self):
        assert validate_id("550e8400-e29b-41d4-a716-446655440000") == "550e8400-e29b-41d4-a716-446655440000"

    def test_valid_single_char(self):
        assert validate_id("a") == "a"

    def test_empty_string(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_id("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="contains invalid characters"):
            validate_id("   ")

    def test_path_traversal_double_dot(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_id("../../etc/passwd")

    def test_path_traversal_double_dot_mid(self):
        with pytest.raises(ValueError, match="path traversal"):
            validate_id("file..hidden")

    def test_forward_slash(self):
        with pytest.raises(ValueError, match="path separator"):
            validate_id("etc/passwd")

    def test_backslash(self):
        with pytest.raises(ValueError, match="path separator"):
            validate_id("C:\\Windows\\System32")

    def test_null_byte(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_id("good\0bad")

    def test_special_chars(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_id("rm -rf")

    def test_spaces(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_id("my file")

    def test_newline(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_id("ok\nDROP TABLE")

    def test_url_encoded_traversal(self):
        # %2F contains no actual / so path separator won't catch it,
        # but %2F itself is not alphanumeric, so invalid-char check applies
        with pytest.raises(ValueError, match="invalid characters"):
            validate_id("%2Fsecret")

    def test_double_encoded_traversal(self):
        # ..%252F = double-encoded — %25 decodes to %, so the raw string
        # still contains '..' which triggers path traversal detection
        with pytest.raises(ValueError, match="path traversal"):
            validate_id("..%252F..%252Fsecret")

    def test_custom_param_name_in_error(self):
        with pytest.raises(ValueError, match="file_id contains illegal path traversal"):
            validate_id("../../../etc", "file_id")

    def test_custom_param_name_empty(self):
        with pytest.raises(ValueError, match="config_id must not be empty"):
            validate_id("", "config_id")
