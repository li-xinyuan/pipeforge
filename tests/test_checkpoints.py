from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pipeforge.config.exceptions import CheckpointError
from pipeforge.config.models import RowCountRule
from pipeforge.core.checkpoints import execute_checks


class TestRowCountExecutor:
    def test_passes_when_count_in_range(self):
        mock_db = MagicMock()
        mock_db.query.return_value = [(50,)]

        rule = RowCountRule(min=10, max=100, on_failure="block")
        results = execute_checks([rule], mock_db, "test_table")
        assert results[0].passed is True
        assert "50" in results[0].message

    def test_fails_when_count_below_min(self):
        mock_db = MagicMock()
        mock_db.query.return_value = [(5,)]

        rule = RowCountRule(min=10, on_failure="block")
        with pytest.raises(CheckpointError) as exc:
            execute_checks([rule], mock_db, "test_table")
        assert len(exc.value.results) == 1
        assert exc.value.results[0].passed is False
        assert "5 < 最小值 10" in exc.value.results[0].message

    def test_fails_when_count_above_max(self):
        mock_db = MagicMock()
        mock_db.query.return_value = [(150,)]

        rule = RowCountRule(max=100, on_failure="block")
        with pytest.raises(CheckpointError) as exc:
            execute_checks([rule], mock_db, "test_table")
        assert exc.value.results[0].passed is False

    def test_warn_does_not_block(self):
        mock_db = MagicMock()
        mock_db.query.return_value = [(5,)]

        rule = RowCountRule(min=10, on_failure="warn")
        results = execute_checks([rule], mock_db, "test_table")
        assert results[0].passed is False
        # warn should NOT raise CheckpointError

    def test_empty_table_defaults_to_default_table(self):
        mock_db = MagicMock()
        mock_db.query.return_value = [(42,)]

        rule = RowCountRule(table="", min=1, on_failure="block")
        results = execute_checks([rule], mock_db, "actual_table")
        assert results[0].passed is True
        mock_db.query.assert_called_with('SELECT COUNT(*) FROM "actual_table"')


class TestExecuteChecks:
    def test_collects_all_results_before_raising(self):
        """block rules should collect all results before raising, not stop at first failure."""
        mock_db = MagicMock()
        mock_db.query.return_value = [(3,)]  # below min=5 for both

        rules = [
            RowCountRule(min=5, on_failure="block"),
            RowCountRule(min=5, on_failure="block"),
        ]
        with pytest.raises(CheckpointError) as exc:
            execute_checks(rules, mock_db, "t")
        assert len(exc.value.results) == 2  # both checked, not just first

    def test_unknown_rule_type_raises(self):
        """Unregistered rule type should raise ValueError. Use model_construct to bypass Pydantic Literal restriction."""
        mock_db = MagicMock()
        # Construct a rule with type="unknown" by bypassing Pydantic Literal validation
        unknown_rule = RowCountRule.model_construct(type="unknown", min=1, on_failure="block")

        with pytest.raises(ValueError, match="Unknown check rule type"):
            execute_checks([unknown_rule], mock_db, "t")

    def test_empty_checkpoints_returns_empty(self):
        mock_db = MagicMock()
        results = execute_checks([], mock_db, "t")
        assert results == []

    def test_result_has_checked_at_timestamp(self):
        mock_db = MagicMock()
        mock_db.query.return_value = [(10,)]

        rule = RowCountRule(min=1, on_failure="block")
        results = execute_checks([rule], mock_db, "t")
        assert results[0].checked_at
        # Verify ISO 8601 format
        datetime.fromisoformat(results[0].checked_at)
