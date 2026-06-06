"""Tests for checkpoint rule executors."""
import pytest
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.checkpoints import execute_checks
from pipeforge.config.exceptions import CheckpointError
from pipeforge.config.models import (
    NullRateRule,
    UniquenessRule,
    ValueRangeRule,
    CustomSqlRule,
    EnumCheckRule,
)


@pytest.fixture
def db():
    db = SQLiteManager()
    yield db
    db.close()


class TestNullRateRule:
    def test_pass_when_under_threshold(self, db):
        db.create_table("t", ["col"])
        for _ in range(8):
            db.insert_row("t", ("val",))
        db.insert_row("t", (None,))
        db.insert_row("t", (None,))
        # 10 rows, 2 nulls = 20% < 30% threshold
        results = execute_checks([NullRateRule(table="t", column="col", max_null_rate=0.3)], db, "t")
        assert results[0].passed is True

    def test_fail_when_over_threshold(self, db):
        db.create_table("t", ["col"])
        for _ in range(5):
            db.insert_row("t", ("val",))
        for _ in range(5):
            db.insert_row("t", (None,))
        # 10 rows, 5 nulls = 50% > 20% threshold — block raises CheckpointError
        with pytest.raises(CheckpointError) as exc_info:
            execute_checks([NullRateRule(table="t", column="col", max_null_rate=0.2)], db, "t")
        assert exc_info.value.results[0].passed is False

    def test_empty_table_no_division_by_zero(self, db):
        db.create_table("t", ["col"])
        results = execute_checks([NullRateRule(table="t", column="col", max_null_rate=0.1)], db, "t")
        assert results[0].passed is True


class TestUniquenessRule:
    def test_pass_when_all_unique(self, db):
        db.create_table("t", ["col"])
        db.insert_row("t", ("a",))
        db.insert_row("t", ("b",))
        db.insert_row("t", ("c",))
        results = execute_checks([UniquenessRule(table="t", column="col")], db, "t")
        assert results[0].passed is True

    def test_fail_when_duplicate_exists(self, db):
        db.create_table("t", ["col"])
        db.insert_row("t", ("a",))
        db.insert_row("t", ("a",))
        with pytest.raises(CheckpointError) as exc_info:
            execute_checks([UniquenessRule(table="t", column="col")], db, "t")
        assert exc_info.value.results[0].passed is False

    def test_null_values_excluded(self, db):
        db.create_table("t", ["col"])
        db.insert_row("t", ("a",))
        db.insert_row("t", ("b",))
        db.insert_row("t", (None,))
        db.insert_row("t", (None,))
        # a and b are unique, NULLs excluded — should pass
        results = execute_checks([UniquenessRule(table="t", column="col")], db, "t")
        assert results[0].passed is True


class TestValueRangeRule:
    def test_pass_when_all_in_range(self, db):
        db.create_table("t", ["val"])
        db.insert_row("t", ("50",))
        db.insert_row("t", ("75",))
        results = execute_checks([ValueRangeRule(table="t", column="val", min_value=0, max_value=100)], db, "t")
        assert results[0].passed is True

    def test_fail_when_out_of_range(self, db):
        db.create_table("t", ["val"])
        db.insert_row("t", ("50",))
        db.insert_row("t", ("200",))
        with pytest.raises(CheckpointError) as exc_info:
            execute_checks([ValueRangeRule(table="t", column="val", min_value=0, max_value=100)], db, "t")
        assert exc_info.value.results[0].passed is False

    def test_pass_when_no_bounds_set(self, db):
        db.create_table("t", ["val"])
        db.insert_row("t", ("50",))
        results = execute_checks([ValueRangeRule(table="t", column="val")], db, "t")
        assert results[0].passed is True

    def test_min_only(self, db):
        db.create_table("t", ["val"])
        db.insert_row("t", ("50",))
        db.insert_row("t", ("-5",))
        with pytest.raises(CheckpointError) as exc_info:
            execute_checks([ValueRangeRule(table="t", column="val", min_value=0)], db, "t")
        assert exc_info.value.results[0].passed is False


class TestCustomSqlRule:
    def test_pass_when_comparison_holds(self, db):
        db.create_table("t", ["id"])
        for i in range(5):
            db.insert_row("t", (str(i),))
        results = execute_checks([CustomSqlRule(
            sql='SELECT COUNT(*) AS cnt FROM "t"',
            result_column="cnt",
            comparison="<=",
            expected_value=5,
        )], db, "t")
        assert results[0].passed is True

    def test_fail_when_comparison_violated(self, db):
        db.create_table("t", ["id"])
        for i in range(5):
            db.insert_row("t", (str(i),))
        with pytest.raises(CheckpointError) as exc_info:
            execute_checks([CustomSqlRule(
                sql='SELECT COUNT(*) AS cnt FROM "t"',
                result_column="cnt",
                comparison="<",
                expected_value=3,
            )], db, "t")
        assert exc_info.value.results[0].passed is False

    def test_all_six_comparison_operators(self, db):
        db.create_table("t", ["id"])
        db.insert_row("t", ("1",))
        db.insert_row("t", ("2",))
        # COUNT(*) = 2
        sql = 'SELECT COUNT(*) AS cnt FROM "t"'
        ops = {"<": 3, "<=": 2, "==": 2, "!=": 99, ">": 1, ">=": 2}
        for op, expected in ops.items():
            results = execute_checks([CustomSqlRule(sql=sql, result_column="cnt", comparison=op, expected_value=expected)], db, "t")
            assert results[0].passed is True, f"comparison {op} {expected} should pass for count=2"

    def test_ddl_blocked(self, db):
        with pytest.raises(CheckpointError) as exc_info:
            execute_checks([CustomSqlRule(sql="CREATE TABLE hack (id INT)")], db, "t")
        assert exc_info.value.results[0].passed is False
        assert "DDL" in exc_info.value.results[0].message or "不允许" in exc_info.value.results[0].message

    def test_empty_sql_skips(self, db):
        results = execute_checks([CustomSqlRule(sql="")], db, "t")
        assert results[0].passed is True
        assert "跳过" in results[0].message or "为空" in results[0].message

    def test_no_expected_value_passes(self, db):
        db.create_table("t", ["id"])
        db.insert_row("t", ("1",))
        results = execute_checks([CustomSqlRule(sql='SELECT COUNT(*) AS cnt FROM "t"', result_column="cnt")], db, "t")
        assert results[0].passed is True


class TestEnumCheckRule:
    def test_pass_when_all_in_allowed(self, db):
        db.create_table("t", ["status"])
        db.insert_row("t", ("active",))
        db.insert_row("t", ("inactive",))
        results = execute_checks([EnumCheckRule(table="t", column="status", allowed_values=["active", "inactive"])], db, "t")
        assert results[0].passed is True

    def test_fail_when_value_not_allowed(self, db):
        db.create_table("t", ["status"])
        db.insert_row("t", ("active",))
        db.insert_row("t", ("banned",))
        with pytest.raises(CheckpointError) as exc_info:
            execute_checks([EnumCheckRule(table="t", column="status", allowed_values=["active", "inactive"])], db, "t")
        assert exc_info.value.results[0].passed is False

    def test_empty_allowed_skips(self, db):
        db.create_table("t", ["status"])
        db.insert_row("t", ("active",))
        results = execute_checks([EnumCheckRule(table="t", column="status", allowed_values=[])], db, "t")
        assert results[0].passed is True

    def test_over_900_values_rejected(self, db):
        db.create_table("t", ["status"])
        huge_list = [f"val_{i}" for i in range(901)]
        with pytest.raises(CheckpointError) as exc_info:
            execute_checks([EnumCheckRule(table="t", column="status", allowed_values=huge_list)], db, "t")
        assert exc_info.value.results[0].passed is False
        assert "901" in exc_info.value.results[0].message
