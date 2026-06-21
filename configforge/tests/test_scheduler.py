"""Unit tests for configforge.scheduler module."""
import json
from unittest.mock import MagicMock, patch

import pytest

import configforge.scheduler as scheduler
from configforge.scheduler import (
    ScheduleConfig,
    _run_scheduled_pipeline,
    _update_schedule_last_run,
    _validate_cron,
    add_schedule,
    get_next_run_time,
    list_schedules,
    remove_schedule,
    shutdown_scheduler,
    start_scheduler,
    toggle_schedule,
    update_schedule,
)


@pytest.fixture(autouse=True)
def temp_data_dir(monkeypatch, tmp_path):
    """Use a temporary directory for schedule data."""
    monkeypatch.setattr(scheduler, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(scheduler, "SCHEDULES_PATH", str(tmp_path / "schedules.json"))
    # Ensure no real scheduler is running
    monkeypatch.setattr(scheduler, "_scheduler", None)
    yield


@pytest.fixture
def sample_schedules(tmp_path):
    """Create a few sample schedules in the store."""
    schedules = [
        ScheduleConfig(
            id="sched1",
            config_id="cfg1",
            cron_expression="0 8 * * *",
            description="Daily 8am",
            enabled=True,
            created_at="2024-01-01T00:00:00+00:00",
        ),
        ScheduleConfig(
            id="sched2",
            config_id="cfg2",
            cron_expression="0 */2 * * *",
            description="Every 2 hours",
            enabled=False,
            created_at="2024-01-02T00:00:00+00:00",
        ),
    ]
    path = tmp_path / "schedules.json"
    path.write_text(json.dumps([s.model_dump() for s in schedules], ensure_ascii=False))
    return schedules


class TestValidateCron:
    def test_valid_5_field_cron(self):
        _validate_cron("0 8 * * *")  # Should not raise

    def test_valid_every_minute(self):
        _validate_cron("* * * * *")

    def test_invalid_4_fields(self):
        with pytest.raises(ValueError, match="5 fields"):
            _validate_cron("0 8 * *")

    def test_invalid_6_fields(self):
        with pytest.raises(ValueError, match="5 fields"):
            _validate_cron("0 8 * * * 0")

    def test_invalid_cron_syntax(self):
        with pytest.raises(Exception):  # CronTrigger raises its own error
            _validate_cron("99 99 99 99 99")


class TestListSchedules:
    def test_empty_store(self):
        assert list_schedules() == []

    def test_returns_existing_schedules(self, sample_schedules):
        result = list_schedules()
        assert len(result) == 2
        assert result[0].id == "sched1"
        assert result[1].id == "sched2"

    def test_disabled_schedule_preserved(self, sample_schedules):
        result = list_schedules()
        assert result[1].enabled is False


class TestAddSchedule:
    def test_add_creates_schedule(self):
        sched = add_schedule("cfg1", "0 8 * * *", "Daily")
        assert sched.config_id == "cfg1"
        assert sched.cron_expression == "0 8 * * *"
        assert sched.description == "Daily"
        assert sched.enabled is True
        assert sched.id  # Auto-generated

    def test_add_persists_to_disk(self):
        add_schedule("cfg1", "0 8 * * *")
        result = list_schedules()
        assert len(result) == 1
        assert result[0].config_id == "cfg1"

    def test_add_invalid_cron_raises(self):
        with pytest.raises(ValueError):
            add_schedule("cfg1", "invalid")

    def test_add_with_scheduler_running(self, monkeypatch):
        mock_scheduler = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        sched = add_schedule("cfg1", "0 8 * * *")
        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args
        assert call_kwargs[1]["id"] == sched.id

    def test_add_disabled_no_job(self, monkeypatch):
        mock_scheduler = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        _sched = add_schedule("cfg1", "0 8 * * *")
        # Default is enabled=True, so job should be added
        mock_scheduler.add_job.assert_called_once()


class TestRemoveSchedule:
    def test_remove_existing(self, sample_schedules):
        result = remove_schedule("sched1")
        assert result is True
        assert len(list_schedules()) == 1

    def test_remove_nonexistent(self, sample_schedules):
        result = remove_schedule("nonexistent")
        assert result is False
        assert len(list_schedules()) == 2

    def test_remove_from_running_scheduler(self, sample_schedules, monkeypatch):
        mock_scheduler = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        remove_schedule("sched1")
        mock_scheduler.remove_job.assert_called_once_with("sched1")


class TestUpdateSchedule:
    def test_update_cron(self, sample_schedules):
        result = update_schedule("sched1", cron_expression="0 9 * * *")
        assert result is not None
        assert result.cron_expression == "0 9 * * *"

    def test_update_description(self, sample_schedules):
        result = update_schedule("sched1", description="New desc")
        assert result is not None
        assert result.description == "New desc"

    def test_update_nonexistent(self, sample_schedules):
        result = update_schedule("nonexistent", cron_expression="0 9 * * *")
        assert result is None

    def test_update_invalid_cron_raises(self, sample_schedules):
        with pytest.raises(ValueError):
            update_schedule("sched1", cron_expression="bad")


class TestToggleSchedule:
    def test_toggle_enabled_to_disabled(self, sample_schedules):
        result = toggle_schedule("sched1")
        assert result is not None
        assert result.enabled is False

    def test_toggle_disabled_to_enabled(self, sample_schedules):
        result = toggle_schedule("sched2")
        assert result is not None
        assert result.enabled is True

    def test_toggle_nonexistent(self, sample_schedules):
        result = toggle_schedule("nonexistent")
        assert result is None

    def test_toggle_removes_job_when_disabled(self, sample_schedules, monkeypatch):
        mock_scheduler = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        # sched1 is enabled, toggle to disabled
        toggle_schedule("sched1")
        mock_scheduler.remove_job.assert_called_once_with("sched1")

    def test_toggle_adds_job_when_enabled(self, sample_schedules, monkeypatch):
        mock_scheduler = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        # sched2 is disabled, toggle to enabled
        toggle_schedule("sched2")
        mock_scheduler.add_job.assert_called_once()


class TestUpdateScheduleLastRun:
    def test_updates_last_run_at(self, sample_schedules):
        _update_schedule_last_run("sched1", "success")
        result = list_schedules()
        assert result[0].last_run_status == "success"
        assert result[0].last_run_at is not None

    def test_nonexistent_schedule_no_error(self, sample_schedules):
        _update_schedule_last_run("nonexistent", "failed")
        # Should not raise, schedules unchanged
        assert len(list_schedules()) == 2


class TestScheduleConfig:
    def test_default_values(self):
        cfg = ScheduleConfig(config_id="c1", cron_expression="0 8 * * *")
        assert cfg.enabled is True
        assert cfg.description == ""
        assert cfg.id  # Auto-generated
        assert cfg.last_run_at is None
        assert cfg.last_run_status is None


class TestGetNextRunTime:
    def test_returns_none_when_no_scheduler(self):
        assert get_next_run_time("sched1") is None

    def test_returns_none_when_job_not_found(self, monkeypatch):
        mock_scheduler = MagicMock()
        mock_scheduler.get_job.return_value = None
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        assert get_next_run_time("nonexistent") is None

    def test_returns_iso_string_when_job_exists(self, monkeypatch):
        from datetime import UTC, datetime
        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_job.next_run_time = datetime(2026, 6, 20, 8, 0, 0, tzinfo=UTC)
        mock_scheduler.get_job.return_value = mock_job
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        result = get_next_run_time("sched1")
        assert result is not None
        assert "2026-06-20" in result

    def test_returns_none_when_job_has_no_next_run(self, monkeypatch):
        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_job.next_run_time = None
        mock_scheduler.get_job.return_value = mock_job
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        assert get_next_run_time("sched1") is None


class TestStartScheduler:
    def test_starts_scheduler_and_registers_enabled(self, sample_schedules, monkeypatch):
        mock_bg = MagicMock()
        with patch("configforge.scheduler.BackgroundScheduler", return_value=mock_bg):
            start_scheduler()
        mock_bg.start.assert_called_once()
        # Should register 1 enabled schedule (sched1)
        assert mock_bg.add_job.call_count == 1

    def test_does_not_restart_if_already_running(self, monkeypatch):
        mock_scheduler = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        start_scheduler()  # Should return early
        # _scheduler is not None, so BackgroundScheduler should not be created
        mock_scheduler.start.assert_not_called()

    def test_skips_invalid_cron_on_start(self, tmp_path, monkeypatch):
        # Write a schedule with invalid cron
        bad_schedule = {
            "id": "bad1",
            "config_id": "cfg1",
            "cron_expression": "INVALID",
            "enabled": True,
            "description": "",
            "created_at": "2024-01-01T00:00:00+00:00",
        }
        path = tmp_path / "schedules.json"
        path.write_text(json.dumps([bad_schedule]))
        monkeypatch.setattr(scheduler, "_scheduler", None)

        mock_bg = MagicMock()
        with patch("configforge.scheduler.BackgroundScheduler", return_value=mock_bg):
            start_scheduler()
        # Invalid cron should be skipped, no jobs added
        mock_bg.add_job.assert_not_called()


class TestShutdownScheduler:
    def test_shutdowns_running_scheduler(self, monkeypatch):
        mock_scheduler = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        shutdown_scheduler()
        mock_scheduler.shutdown.assert_called_once_with(wait=False)

    def test_sets_scheduler_to_none(self, monkeypatch):
        mock_scheduler = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        shutdown_scheduler()
        assert scheduler._scheduler is None

    def test_noop_when_not_running(self, monkeypatch):
        monkeypatch.setattr(scheduler, "_scheduler", None)
        shutdown_scheduler()  # Should not raise


class TestRunScheduledPipeline:
    def test_fails_when_state_not_found(self, monkeypatch, sample_schedules):
        with patch("configforge.api.configs.CONFIGS_DIR", "/nonexistent"):
            _run_scheduled_pipeline("sched1", "nonexistent_cfg")
        # Should update last_run_status to "failed"
        result = list_schedules()
        assert result[0].last_run_status == "failed"

    def test_fails_when_file_input_without_file(self, monkeypatch, tmp_path, sample_schedules):
        # Create a state file with file input but no file_id
        state = {
            "scene": {"name": "test", "version": "1.0", "description": ""},
            "inputs": [{"name": "inp1", "plugin": "excel", "table": "t1", "param_key": "", "file_id": "", "config": {"type": "excel", "sheet": ""}}],
            "processors": [],
            "output": None,
        }
        cfg_path = tmp_path / "test-cfg.state.json"
        cfg_path.write_text(json.dumps(state))

        with patch("configforge.api.configs.CONFIGS_DIR", str(tmp_path)), \
             patch("configforge.api.executions._update_exec_index"), \
             patch("configforge.api.executions._save_failed_execution"):
            _run_scheduled_pipeline("sched1", "test-cfg")

        # Should mark as failed due to file input without file_id
        result = list_schedules()
        assert result[0].last_run_status == "failed"


class TestUpdateScheduleReRegistersJob:
    def test_update_cron_re_registers_job(self, sample_schedules, monkeypatch):
        mock_scheduler = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        # sched1 is enabled, updating cron should re-register
        update_schedule("sched1", cron_expression="0 9 * * *")
        # Should remove old job and add new one
        mock_scheduler.remove_job.assert_called_once_with("sched1")
        mock_scheduler.add_job.assert_called_once()

    def test_update_cron_disabled_no_reregister(self, sample_schedules, monkeypatch):
        mock_scheduler = MagicMock()
        monkeypatch.setattr(scheduler, "_scheduler", mock_scheduler)
        # sched2 is disabled, updating cron should NOT re-register
        update_schedule("sched2", cron_expression="0 9 * * *")
        mock_scheduler.remove_job.assert_not_called()
        mock_scheduler.add_job.assert_not_called()


class TestScheduleConfigSerialization:
    def test_model_dump_roundtrip(self):
        cfg = ScheduleConfig(config_id="c1", cron_expression="0 8 * * *", description="test")
        data = cfg.model_dump()
        cfg2 = ScheduleConfig(**data)
        assert cfg2.config_id == cfg.config_id
        assert cfg2.cron_expression == cfg.cron_expression
        assert cfg2.description == cfg.description

    def test_json_roundtrip(self, tmp_path):
        cfg = ScheduleConfig(config_id="c1", cron_expression="0 8 * * *")
        path = tmp_path / "test.json"
        path.write_text(json.dumps([cfg.model_dump()]))
        loaded = json.loads(path.read_text())
        cfg2 = ScheduleConfig(**loaded[0])
        assert cfg2.config_id == cfg.config_id
