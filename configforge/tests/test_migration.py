"""Tests for schema versioning and migration framework."""

import json
import os

from configforge.utils.migration import (
    CURRENT_SCHEMA_VERSION,
    _migrate_v0_to_v1,
    ensure_schema_version,
    load_with_migration,
)


class TestEnsureSchemaVersion:
    """Tests for ensure_schema_version()."""

    def test_current_version_no_migration(self):
        """Data with current schema_version should pass through unchanged."""
        data = {"schema_version": CURRENT_SCHEMA_VERSION, "key": "value"}
        result = ensure_schema_version(data, "test.json")
        assert result == data

    def test_missing_version_triggers_migration(self):
        """Data without schema_version should be migrated from v0."""
        data = {"key": "value"}
        result = ensure_schema_version(data, "test.json")
        assert result["schema_version"] == CURRENT_SCHEMA_VERSION
        assert result["key"] == "value"

    def test_old_version_triggers_migration(self):
        """Data with schema_version 0 should be migrated."""
        data = {"schema_version": 0, "key": "value"}
        result = ensure_schema_version(data, "test.json")
        assert result["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_future_version_no_migration(self):
        """Data with a newer schema_version should pass through with a warning."""
        data = {"schema_version": CURRENT_SCHEMA_VERSION + 1, "key": "value"}
        result = ensure_schema_version(data, "test.json")
        assert result["schema_version"] == CURRENT_SCHEMA_VERSION + 1
        assert result["key"] == "value"

    def test_list_data_wrapped_and_unwrapped(self):
        """List data should be wrapped for migration and unwrapped after."""
        data = [{"id": 1}, {"id": 2}]
        result = ensure_schema_version(data, "test.json")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_list_data_current_version(self):
        """List data with current version should pass through."""
        data = [{"id": 1}]
        # Lists don't have schema_version, so they get wrapped and migrated
        result = ensure_schema_version(data, "test.json")
        assert isinstance(result, list)
        assert len(result) == 1


class TestMigrateV0ToV1:
    """Tests for _migrate_v0_to_v1()."""

    def test_processor_to_processors_migration(self):
        """Legacy 'processor' field should be migrated to 'processors' list."""
        data = {
            "processor": {
                "name": "test_proc",
                "plugin": "sql",
                "sql": "SELECT 1",
                "outputTable": "result",
            }
        }
        result = _migrate_v0_to_v1(data)
        assert "processor" not in result
        assert "processors" in result
        assert len(result["processors"]) == 1
        assert result["processors"][0]["name"] == "test_proc"
        assert "outputTable" not in result["processors"][0]
        assert result["processors"][0]["output_tables"] == ["result"]

    def test_processor_dict_without_output_table(self):
        """Processor without outputTable should still migrate."""
        data = {
            "processor": {
                "name": "test_proc",
                "plugin": "sql",
                "sql": "SELECT 1",
            }
        }
        result = _migrate_v0_to_v1(data)
        assert "processors" in result
        assert len(result["processors"]) == 1
        assert "output_tables" not in result["processors"][0]

    def test_no_processor_field(self):
        """Data without 'processor' field should pass through."""
        data = {"key": "value"}
        result = _migrate_v0_to_v1(data)
        assert result == {"key": "value"}

    def test_processor_with_existing_processors(self):
        """If 'processors' already exists, 'processor' should just be removed."""
        data = {
            "processor": {"name": "old"},
            "processors": [{"name": "existing"}],
        }
        result = _migrate_v0_to_v1(data)
        assert "processor" not in result
        assert len(result["processors"]) == 1
        assert result["processors"][0]["name"] == "existing"


class TestLoadWithMigration:
    """Tests for load_with_migration()."""

    def test_nonexistent_file_returns_default(self):
        """Non-existent file should return the default value."""
        result = load_with_migration("/tmp/nonexistent_test_file.json", default={"key": "val"})
        assert result["key"] == "val"
        assert result["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_nonexistent_file_no_default(self):
        """Non-existent file with no default should return empty dict."""
        result = load_with_migration("/tmp/nonexistent_test_file.json")
        assert result == {}

    def test_loads_and_migrates_file(self, tmp_path):
        """Should load a file and migrate it if needed."""
        file_path = str(tmp_path / "test_data.json")
        data = {"key": "value"}
        with open(file_path, "w") as f:
            json.dump(data, f)

        result = load_with_migration(file_path)
        assert result["key"] == "value"
        assert result["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_saves_migrated_data_back(self, tmp_path):
        """Should save migrated data back to disk."""
        file_path = str(tmp_path / "test_data.json")
        data = {"key": "value"}
        with open(file_path, "w") as f:
            json.dump(data, f)

        load_with_migration(file_path)

        # Verify file was updated with schema_version
        with open(file_path) as f:
            saved = json.load(f)
        assert saved["schema_version"] == CURRENT_SCHEMA_VERSION
        assert saved["key"] == "value"

    def test_no_save_when_already_current(self, tmp_path):
        """Should not save when schema_version is already current."""
        file_path = str(tmp_path / "test_data.json")
        data = {"key": "value", "schema_version": CURRENT_SCHEMA_VERSION}
        with open(file_path, "w") as f:
            json.dump(data, f)

        original_mtime = os.path.getmtime(file_path)
        import time
        time.sleep(0.1)

        load_with_migration(file_path)

        # File should not have been modified
        new_mtime = os.path.getmtime(file_path)
        assert new_mtime == original_mtime

    def test_list_default(self, tmp_path):
        """Should handle list defaults correctly."""
        file_path = str(tmp_path / "test_list.json")
        data = [{"id": 1}, {"id": 2}]
        with open(file_path, "w") as f:
            json.dump(data, f)

        result = load_with_migration(file_path, default=[])
        assert isinstance(result, list)
        assert len(result) == 2
