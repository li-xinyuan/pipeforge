"""检查点规则注册与执行。新增规则类型：加模型 → 用 @register_check 注册执行器 → 追加到 CheckRule union。"""

from datetime import datetime, timezone
from typing import Callable

from pipeforge.config.models import CheckRule, CheckResult, RowCountRule
from pipeforge.config.exceptions import CheckpointError
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
        table = rule.table or default_table
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
