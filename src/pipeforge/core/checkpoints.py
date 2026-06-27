"""检查点规则注册与执行。新增规则类型：加模型 → 用 @register_check 注册执行器 → 追加到 CheckRule union。"""

import re
from collections.abc import Callable
from datetime import datetime, timezone

from pipeforge.config.exceptions import CheckpointError
from pipeforge.config.models import (
    CheckResult,
    CheckRule,
    CustomSqlRule,
    EnumCheckRule,
    NullRateRule,
    RowCountRule,
    UniquenessRule,
    ValueRangeRule,
)
from pipeforge.core.sqlite import SQLiteManager

_CHECK_EXECUTORS: dict[str, Callable] = {}


def register_check(type: str):
    """注册检查规则执行器。签名: (table: str, rule: CheckRule, db: SQLiteManager) -> (bool, str)"""

    def decorator(fn):
        _CHECK_EXECUTORS[type] = fn
        return fn

    return decorator


def execute_checks(
    checkpoints: list[CheckRule],
    db: SQLiteManager,
    default_table: str = "",
) -> list[CheckResult]:
    """执行所有检查规则。block 失败时收集全部结果后统一抛出 CheckpointError。"""
    results = []
    has_block_failure = False
    for rule in checkpoints:
        table = getattr(rule, "table", None) or default_table
        executor = _CHECK_EXECUTORS.get(rule.type)
        if not executor:
            raise ValueError(
                f"Unknown check rule type: {rule.type}. "
                f"Available: {list(_CHECK_EXECUTORS.keys())}"
            )
        passed, message = executor(table, rule, db)
        result = CheckResult(
            type=rule.type,
            passed=passed,
            message=message,
            on_failure=rule.on_failure,
            checked_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        results.append(result)
        if not passed and rule.on_failure == "block":
            has_block_failure = True
    if has_block_failure:
        raise CheckpointError(results)
    return results


def _has_ddl(sql: str) -> bool:
    """检查 SQL 是否包含 DDL/DML 语句（禁止修改数据或结构）。"""
    return bool(re.search(r"\b(CREATE|INSERT|DROP|ALTER|WITH)\b", sql, re.IGNORECASE))


@register_check("row_count")
def _check_row_count(table: str, rule: RowCountRule, db: SQLiteManager) -> tuple[bool, str]:
    if not table:
        return False, "未指定检查表名"
    count = db.query(f'SELECT COUNT(*) FROM "{table}"')[0][0]
    if rule.min is not None and count < rule.min:
        return False, f"表 {table} 行数 {count} < 最小值 {rule.min}"
    if rule.max is not None and count > rule.max:
        return False, f"表 {table} 行数 {count} > 最大值 {rule.max}"
    return True, f"表 {table} 行数 {count} 在范围内"


@register_check("null_rate")
def _check_null_rate(table: str, rule: NullRateRule, db: SQLiteManager) -> tuple[bool, str]:
    """检查某列空值比例是否超过阈值。"""
    sql = f'SELECT COUNT(*) AS total, SUM(CASE WHEN "{rule.column}" IS NULL THEN 1 ELSE 0 END) AS nulls FROM "{table}"'
    row = db.query(sql)[0]
    total = row[0] if isinstance(row[0], int) else 0
    nulls = row[1] if isinstance(row[1], int) else 0
    actual_rate = nulls / total if total > 0 else 0
    passed = actual_rate <= rule.max_null_rate
    return passed, f"列 {rule.column} 空值率 {actual_rate:.2%}（阈值 {rule.max_null_rate:.2%}）"


@register_check("uniqueness")
def _check_uniqueness(table: str, rule: UniquenessRule, db: SQLiteManager) -> tuple[bool, str]:
    """检查某列值是否唯一。排除 NULL 值避免误判。"""
    sql = f'SELECT COUNT("{rule.column}") AS total, COUNT(DISTINCT "{rule.column}") AS distinct_count FROM "{table}" WHERE "{rule.column}" IS NOT NULL'
    row = db.query(sql)[0]
    total = row[0] if isinstance(row[0], int) else 0
    distinct = row[1] if isinstance(row[1], int) else 0
    passed = total == distinct
    return passed, f"列 {rule.column} 唯一性检查：{total} 行中 {distinct} 个不同值（排除 NULL）"


@register_check("value_range")
def _check_value_range(table: str, rule: ValueRangeRule, db: SQLiteManager) -> tuple[bool, str]:
    """检查数值列是否在指定范围内。"""
    col = f'CAST("{rule.column}" AS REAL)'
    conditions = []
    if rule.min_value is not None:
        conditions.append(f"{col} >= {rule.min_value}")
    if rule.max_value is not None:
        conditions.append(f"{col} <= {rule.max_value}")
    if not conditions:
        return True, "未设置范围约束"

    where = " AND ".join(conditions)
    sql = f'SELECT COUNT(*) AS total, SUM(CASE WHEN {where} THEN 1 ELSE 0 END) AS in_range FROM "{table}"'
    row = db.query(sql)[0]
    total = row[0] if isinstance(row[0], int) else 0
    in_range = row[1] if isinstance(row[1], int) else 0
    passed = total == in_range

    if rule.min_value is not None and rule.max_value is not None:
        range_desc = f"[{rule.min_value}, {rule.max_value}]"
    elif rule.min_value is not None:
        range_desc = f"≥{rule.min_value}"
    else:
        range_desc = f"≤{rule.max_value}"

    return passed, f"列 {rule.column} 范围检查 {range_desc}：{in_range}/{total} 行在范围内"


@register_check("custom_sql")
def _check_custom_sql(table: str, rule: CustomSqlRule, db: SQLiteManager) -> tuple[bool, str]:
    """执行自定义 SQL，将结果与期望值通过 comparison 运算符比较。"""
    if not rule.sql.strip():
        return True, "SQL 为空，跳过检查"

    if _has_ddl(rule.sql):
        return False, "自定义 SQL 不允许包含 DDL 语句（CREATE/INSERT/WITH 等）"

    rows = db.query(rule.sql)
    if not rows:
        return False, "SQL 执行无结果"

    row = rows[0]
    # With sqlite3.Row, we can access by column name
    actual_value = row[rule.result_column] if rule.result_column in row.keys() else row[0]

    if actual_value is None:
        return False, f"结果列 '{rule.result_column}' 的值不存在或为 NULL"

    if rule.expected_value is None:
        return True, f"自定义 SQL 结果 {rule.result_column}={actual_value}（未设置期望值）"

    ops = {
        "<": lambda a, e: a < e,
        "<=": lambda a, e: a <= e,
        "==": lambda a, e: a == e,
        "!=": lambda a, e: a != e,
        ">": lambda a, e: a > e,
        ">=": lambda a, e: a >= e,
    }
    op_symbols = {"<": "<", "<=": "≤", "==": "=", "!=": "≠", ">": ">", ">=": "≥"}

    try:
        passed = ops[rule.comparison](float(actual_value), rule.expected_value)
    except (ValueError, TypeError):
        return False, f"无法比较结果值 '{actual_value}' 与期望值 {rule.expected_value}"

    return passed, f"自定义 SQL 结果 {rule.result_column}={actual_value}（期望 {op_symbols[rule.comparison]}{rule.expected_value}）"


@register_check("enum_check")
def _check_enum_check(table: str, rule: EnumCheckRule, db: SQLiteManager) -> tuple[bool, str]:
    """检查列值是否在允许的枚举集合内。"""
    if not rule.allowed_values:
        return True, "允许值列表为空，跳过检查"

    if len(rule.allowed_values) > 900:
        return False, f"枚举值数量 {len(rule.allowed_values)} 超过 SQLite 参数上限（999），请减少枚举值"

    placeholders = ",".join("?" for _ in rule.allowed_values)
    sql = f'SELECT COUNT(*) AS total, SUM(CASE WHEN "{rule.column}" IN ({placeholders}) THEN 1 ELSE 0 END) AS valid FROM "{table}"'
    row = db.query(sql, tuple(rule.allowed_values))[0]
    total = row[0] if isinstance(row[0], int) else 0
    valid = row[1] if isinstance(row[1], int) else 0
    passed = total == valid
    return passed, f"列 {rule.column} 枚举检查：{valid}/{total} 行在允许值内"
