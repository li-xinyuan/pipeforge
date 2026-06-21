"""Tests for audit logging service."""

import json
import os

import pytest

from configforge.services import audit_logger


@pytest.fixture(autouse=True)
def _use_tmp_data_dir(tmp_path, monkeypatch):
    """Redirect audit log to a temp directory for each test."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(audit_logger, "AUDIT_LOG_PATH", str(data_dir / "audit_log.json"))
    monkeypatch.setenv("CONFIGFORGE_DATA_DIR", str(data_dir))


class TestLogAudit:
    def test_log_audit_writes_entry(self):
        """log_audit should persist an entry to the audit log file."""
        audit_logger.log_audit("create", "config", "cfg-001")
        entries = audit_logger.get_audit_log()
        assert len(entries) == 1
        assert entries[0]["action"] == "create"
        assert entries[0]["target_type"] == "config"
        assert entries[0]["target_id"] == "cfg-001"

    def test_log_audit_with_details(self):
        """log_audit should persist details when provided."""
        audit_logger.log_audit("update", "connection", "conn-1", {"field": "host", "old": "a", "new": "b"})
        entries = audit_logger.get_audit_log()
        assert len(entries) == 1
        assert entries[0]["details"]["field"] == "host"
        assert entries[0]["details"]["old"] == "a"

    def test_log_audit_details_default_empty(self):
        """log_audit without details should default to empty dict."""
        audit_logger.log_audit("delete", "template", "tpl-1")
        entries = audit_logger.get_audit_log()
        assert entries[0]["details"] == {}

    def test_log_audit_timestamp(self):
        """Each audit entry should have a valid ISO timestamp."""
        audit_logger.log_audit("execute", "schedule", "sch-1")
        entries = audit_logger.get_audit_log()
        assert "timestamp" in entries[0]
        # Should be parseable as ISO format
        from datetime import datetime
        datetime.fromisoformat(entries[0]["timestamp"])

    def test_log_audit_multiple_entries(self):
        """Multiple log_audit calls should append entries."""
        audit_logger.log_audit("create", "config", "c1")
        audit_logger.log_audit("update", "config", "c2")
        audit_logger.log_audit("delete", "config", "c3")
        entries = audit_logger.get_audit_log(limit=100)
        assert len(entries) == 3

    def test_log_audit_persists_to_file(self):
        """Entries should be written to the JSON file."""
        audit_logger.log_audit("create", "config", "c1")
        log_path = audit_logger.AUDIT_LOG_PATH
        assert os.path.exists(log_path)
        with open(log_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["target_id"] == "c1"


class TestGetAuditLog:
    def test_get_audit_log_empty(self):
        """get_audit_log on empty log should return empty list."""
        entries = audit_logger.get_audit_log()
        assert entries == []

    def test_get_audit_log_filter_by_target_type(self):
        """Filtering by target_type should return only matching entries."""
        audit_logger.log_audit("create", "config", "c1")
        audit_logger.log_audit("create", "connection", "conn1")
        audit_logger.log_audit("delete", "config", "c2")

        entries = audit_logger.get_audit_log(target_type="config")
        assert len(entries) == 2
        assert all(e["target_type"] == "config" for e in entries)

    def test_get_audit_log_filter_by_action(self):
        """Filtering by action should return only matching entries."""
        audit_logger.log_audit("create", "config", "c1")
        audit_logger.log_audit("update", "config", "c2")
        audit_logger.log_audit("delete", "config", "c3")

        entries = audit_logger.get_audit_log(action="delete")
        assert len(entries) == 1
        assert entries[0]["action"] == "delete"

    def test_get_audit_log_combined_filters(self):
        """Filtering by both target_type and action should work."""
        audit_logger.log_audit("create", "config", "c1")
        audit_logger.log_audit("create", "template", "t1")
        audit_logger.log_audit("delete", "config", "c2")

        entries = audit_logger.get_audit_log(target_type="config", action="create")
        assert len(entries) == 1
        assert entries[0]["target_id"] == "c1"

    def test_get_audit_log_limit(self):
        """get_audit_log should respect the limit parameter."""
        for i in range(10):
            audit_logger.log_audit("create", "config", f"c{i}")

        entries = audit_logger.get_audit_log(limit=3)
        assert len(entries) == 3
        # Should return the most recent entries
        assert entries[0]["target_id"] == "c7"
        assert entries[1]["target_id"] == "c8"
        assert entries[2]["target_id"] == "c9"


class TestMaxAuditEntries:
    def test_audit_log_trims_at_max(self):
        """Audit log should trim to MAX_AUDIT_ENTRIES when exceeded."""
        monkeypatch_val = 5
        import configforge.services.audit_logger as al
        original_max = al.MAX_AUDIT_ENTRIES
        al.MAX_AUDIT_ENTRIES = monkeypatch_val
        try:
            for i in range(8):
                al.log_audit("create", "config", f"c{i}")

            entries = al.get_audit_log(limit=100)
            assert len(entries) == 5
            # Should keep the most recent entries
            assert entries[0]["target_id"] == "c3"
            assert entries[-1]["target_id"] == "c7"
        finally:
            al.MAX_AUDIT_ENTRIES = original_max

    def test_load_entries_handles_corrupt_file(self):
        """_load_entries should return empty list for corrupt JSON file."""
        log_path = audit_logger.AUDIT_LOG_PATH
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w") as f:
            f.write("not valid json {{{")
        entries = audit_logger._load_entries()
        assert entries == []

    def test_load_entries_handles_missing_file(self):
        """_load_entries should return empty list when file doesn't exist."""
        log_path = audit_logger.AUDIT_LOG_PATH
        if os.path.exists(log_path):
            os.remove(log_path)
        entries = audit_logger._load_entries()
        assert entries == []
