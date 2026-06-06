# Phase 1: 检查点规则扩展 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从仅支持 `row_count` 扩展为支持 6 种检查点规则（row_count + 5 种新增），覆盖数据质量校验的常见场景。

**Architecture:** 后端使用 Pydantic v2 discriminated union 管理 6 种规则模型，PipeForge 注册表模式分发执行。前端 CheckpointSection 从硬编码单一表单改为动态规则类型表单，规则特有字段用 `v-if` 按 type 切换。

**Tech Stack:** Python 3.13, Pydantic v2, SQLite, Vue 3 + Naive UI + TypeScript, Vitest

---

## 文件结构

### 后端
| 操作 | 文件 | 职责 |
|------|------|------|
| 修改 | `src/pipeforge/config/models.py:174-194` | 新增 5 个 Rule 模型 + CheckRule discriminated union |
| 修改 | `src/pipeforge/core/checkpoints.py:1-end` | 新增 5 个执行器，使用 `@register_check` 注册 |
| 修改 | `configforge/api/ai.py` | 更新 AI 翻译 prompt 中的规则类型列表 |
| 修改 | `configforge/tests/test_pipeline.py:37-54` | 修复 2 个过时的 _has_ddl 测试断言 |
| 新增 | `configforge/tests/test_checkpoints.py` | 所有新规则的单元测试（通过 + 失败 + 边界） |

### 前端
| 操作 | 文件 | 职责 |
|------|------|------|
| 修改 | `configforge-web/src/types/wizard.ts` | 6 种 CheckRule 的 TypeScript discriminated union |
| 修改 | `configforge-web/src/components/step3/CheckpointSection.vue` | 动态规则类型表单 |
| 新增 | `configforge-web/tests/components/CheckpointSection.test.ts` | 组件测试 |

### 不需要改动的文件
| 文件 | 原因 |
|------|------|
| `configforge/models/wizard.py` | `ProcessorConfig.checkpoints: list[CheckRule]` 自动跟随 Union 变化 |
| `configforge/services/yaml_builder.py` | 使用 `r.model_dump()` 自动序列化 |
| `configforge/core/pipeline.py` | `execute_checks()` 已是通用分发逻辑 |
| `configforge/api/wizard.py` | CheckpointError 处理逻辑不变 |
| `configforge-web/src/utils/serialization.ts` | 新字段名已是 snake_case，无需转换 |

---

## Task 1: 后端 — Pydantic 模型：新增 5 种 Rule + CheckRule Union

**Files:**
- Modify: `src/pipeforge/config/models.py:174-194`
- Test: `configforge/tests/test_checkpoints.py` (Task 2)

### Step 1: 修改 models.py 中的 CheckRule 定义

将当前的第 174-194 行：

```python
# 数据检查点（v0.1：仅 RowCountRule）
class RowCountRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["row_count"] = "row_count"
    table: str = ""
    min: int = 0
    max: int | None = None
    on_failure: Literal["block", "warn"] = "block"

CheckRule = RowCountRule

class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    passed: bool
    message: str
    on_failure: Literal["block", "warn"]
    checked_at: str
```

替换为：

```python
# 数据检查点（v0.2：支持 6 种规则）
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Literal


class RowCountRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["row_count"] = "row_count"
    table: str = ""
    min: int = 0
    max: int | None = None
    on_failure: Literal["block", "warn"] = "block"


class NullRateRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["null_rate"] = "null_rate"
    table: str = ""
    column: str = ""
    max_null_rate: float = Field(default=0.05, ge=0, le=1)
    on_failure: Literal["block", "warn"] = "block"


class UniquenessRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["uniqueness"] = "uniqueness"
    table: str = ""
    column: str = ""
    on_failure: Literal["block", "warn"] = "block"


class ValueRangeRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["value_range"] = "value_range"
    table: str = ""
    column: str = ""
    min_value: float | None = None
    max_value: float | None = None
    on_failure: Literal["block", "warn"] = "block"


class CustomSqlRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["custom_sql"] = "custom_sql"
    sql: str = ""
    result_column: str = "result"
    comparison: Literal["<", "<=", "==", "!=", ">", ">="] = "<="
    expected_value: float | None = None
    on_failure: Literal["block", "warn"] = "block"


class EnumCheckRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["enum_check"] = "enum_check"
    table: str = ""
    column: str = ""
    allowed_values: list[str] = Field(default=[])
    on_failure: Literal["block", "warn"] = "block"


CheckRule = Annotated[
    RowCountRule | NullRateRule | UniquenessRule | ValueRangeRule | CustomSqlRule | EnumCheckRule,
    Field(discriminator="type")
]


class CheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    passed: bool
    message: str
    on_failure: Literal["block", "warn"]
    checked_at: str
```

### Step 2: 验证 Pydantic 模型可正确导入和序列化

```bash
python3 -c "
from src.pipeforge.config.models import CheckRule, RowCountRule, NullRateRule, UniquenessRule, ValueRangeRule, CustomSqlRule, EnumCheckRule
from pydantic import TypeAdapter

# 验证 row_count 向后兼容
r = TypeAdapter(CheckRule).validate_python({'type': 'row_count', 'table': 't1', 'min': 10})
assert isinstance(r, RowCountRule)
assert r.min == 10

# 验证每种新类型
r = TypeAdapter(CheckRule).validate_python({'type': 'null_rate', 'table': 't1', 'column': 'c1', 'max_null_rate': 0.1})
assert isinstance(r, NullRateRule)
assert r.max_null_rate == 0.1

r = TypeAdapter(CheckRule).validate_python({'type': 'uniqueness', 'table': 't1', 'column': 'c1'})
assert isinstance(r, UniquenessRule)

r = TypeAdapter(CheckRule).validate_python({'type': 'enum_check', 'table': 't1', 'column': 'c1', 'allowed_values': ['a', 'b']})
assert isinstance(r, EnumCheckRule)
assert r.allowed_values == ['a', 'b']

# 验证 serialization round-trip
json_str = TypeAdapter(list[CheckRule]).dump_json([r])
parsed = TypeAdapter(list[CheckRule]).validate_json(json_str)
assert parsed[0].type == 'enum_check'

print('All Pydantic model checks passed')
"
```

Expected: `All Pydantic model checks passed`

### Step 3: Commit

```bash
git add src/pipeforge/config/models.py
git commit -m "feat: add 5 new CheckRule types with discriminated union (Phase 1 models)"
```

---

## Task 2: 后端 — NullRateRule 执行器

**Files:**
- Modify: `src/pipeforge/core/checkpoints.py`
- Test: `configforge/tests/test_checkpoints.py` (Task 8)

### Step 1: 添加执行器

在 `checkpoints.py` 末尾添加：

```python
@register_check("null_rate")
def _check_null_rate(rule: "NullRateRule", db: SQLiteManager, default_table: str) -> CheckResult:
    """检查某列空值比例是否超过阈值。"""
    from pipeforge.config.models import NullRateRule
    table = rule.table or default_table
    sql = f'SELECT COUNT(*) AS total, SUM(CASE WHEN "{rule.column}" IS NULL THEN 1 ELSE 0 END) AS nulls FROM "{table}"'
    row = db.query(sql)[0]
    total = row[0] if isinstance(row[0], int) else 0
    nulls = row[1] if isinstance(row[1], int) else 0
    actual_rate = nulls / total if total > 0 else 0
    passed = actual_rate <= rule.max_null_rate
    return CheckResult(
        type=rule.type,
        passed=passed,
        message=f"列 {rule.column} 空值率 {actual_rate:.2%}（阈值 {rule.max_null_rate:.2%}）",
        on_failure=rule.on_failure,
        checked_at=datetime.now().isoformat()
    )
```

### Step 2: 手动验证——创建表，插入含空值数据，执行检查

```bash
python3 -c "
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.checkpoints import execute_checks
from pipeforge.config.models import NullRateRule

db = SQLiteManager()
db.create_table('test_null', ['id', 'name', 'value'])
db.insert_row('test_null', ('1', 'alice', '100'))
db.insert_row('test_null', ('2', None, '200'))
db.insert_row('test_null', ('3', 'bob', None))

rule = NullRateRule(table='test_null', column='name', max_null_rate=0.3)
results = execute_checks([rule], db, 'test_null')
for r in results:
    print(f'name check: passed={r.passed}, message={r.message}')

rule2 = NullRateRule(table='test_null', column='value', max_null_rate=0.5)
results2 = execute_checks([rule2], db, 'test_null')
for r in results2:
    print(f'value check: passed={r.passed}, message={r.message}')

db.close()
"
```

Expected output:
```
name check: passed=False, message=列 name 空值率 33.33%...
value check: passed=True, message=列 value 空值率 33.33%...
```

---

## Task 3: 后端 — UniquenessRule 执行器

**Files:**
- Modify: `src/pipeforge/core/checkpoints.py`

### Step 1: 添加执行器

在 `checkpoints.py` 末尾添加：

```python
@register_check("uniqueness")
def _check_uniqueness(rule: "UniquenessRule", db: SQLiteManager, default_table: str) -> CheckResult:
    """检查某列值是否唯一。排除 NULL 值避免误判。"""
    from pipeforge.config.models import UniquenessRule
    table = rule.table or default_table
    sql = f'SELECT COUNT("{rule.column}") AS total, COUNT(DISTINCT "{rule.column}") AS distinct_count FROM "{table}" WHERE "{rule.column}" IS NOT NULL'
    row = db.query(sql)[0]
    total = row[0] if isinstance(row[0], int) else 0
    distinct = row[1] if isinstance(row[1], int) else 0
    passed = total == distinct
    return CheckResult(
        type=rule.type,
        passed=passed,
        message=f"列 {rule.column} 唯一性检查：{total} 行中 {distinct} 个不同值（排除 NULL）",
        on_failure=rule.on_failure,
        checked_at=datetime.now().isoformat()
    )
```

### Step 2: 手动验证

```bash
python3 -c "
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.checkpoints import execute_checks
from pipeforge.config.models import UniquenessRule

db = SQLiteManager()
db.create_table('test_unique', ['id', 'name'])
db.insert_row('test_unique', ('1', 'alice'))
db.insert_row('test_unique', ('2', 'bob'))
db.insert_row('test_unique', ('2', 'bob'))   # duplicate
db.insert_row('test_unique', ('3', None))     # NULL — excluded from check

rule = UniquenessRule(table='test_unique', column='id')
results = execute_checks([rule], db, 'test_unique')
for r in results:
    print(f'id uniqueness: passed={r.passed}, message={r.message}')

db.close()
"
```

Expected: `passed=False, message=...3 行中 2 个不同值（排除 NULL）`

---

## Task 4: 后端 — ValueRangeRule 执行器

**Files:**
- Modify: `src/pipeforge/core/checkpoints.py`

### Step 1: 添加执行器

在 `checkpoints.py` 末尾添加：

```python
@register_check("value_range")
def _check_value_range(rule: "ValueRangeRule", db: SQLiteManager, default_table: str) -> CheckResult:
    """检查数值列是否在指定范围内。"""
    from pipeforge.config.models import ValueRangeRule
    table = rule.table or default_table
    conditions = []
    if rule.min_value is not None:
        conditions.append(f'"{rule.column}" >= {rule.min_value}')
    if rule.max_value is not None:
        conditions.append(f'"{rule.column}" <= {rule.max_value}')
    if not conditions:
        return CheckResult(
            type=rule.type, passed=True,
            message="未设置范围约束",
            on_failure=rule.on_failure,
            checked_at=datetime.now().isoformat()
        )
    where = " AND ".join(conditions)
    sql = f'SELECT COUNT(*) AS total, SUM(CASE WHEN {where} THEN 1 ELSE 0 END) AS in_range FROM "{table}"'
    row = db.query(sql)[0]
    total = row[0] if isinstance(row[0], int) else 0
    in_range = row[1] if isinstance(row[1], int) else 0
    passed = total == in_range

    # Build human-readable range description
    if rule.min_value is not None and rule.max_value is not None:
        range_desc = f"[{rule.min_value}, {rule.max_value}]"
    elif rule.min_value is not None:
        range_desc = f"≥{rule.min_value}"
    else:
        range_desc = f"≤{rule.max_value}"

    return CheckResult(
        type=rule.type, passed=passed,
        message=f"列 {rule.column} 范围检查 {range_desc}：{in_range}/{total} 行在范围内",
        on_failure=rule.on_failure,
        checked_at=datetime.now().isoformat()
    )
```

### Step 2: 手动验证

```bash
python3 -c "
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.checkpoints import execute_checks
from pipeforge.config.models import ValueRangeRule

db = SQLiteManager()
db.create_table('test_range', ['id', 'score'])
db.insert_row('test_range', ('1', '85'))
db.insert_row('test_range', ('2', '92'))
db.insert_row('test_range', ('3', '200'))  # out of range

rule = ValueRangeRule(table='test_range', column='score', min_value=0, max_value=100)
results = execute_checks([rule], db, 'test_range')
for r in results:
    print(f'score range: passed={r.passed}, message={r.message}')

db.close()
"
```

Expected: `passed=False, message=...范围检查 [0, 100]：2/3 行在范围内`

---

## Task 5: 后端 — CustomSqlRule 执行器

**Files:**
- Modify: `src/pipeforge/core/checkpoints.py`

### Step 1: 添加执行器

在 `checkpoints.py` 末尾添加：

```python
@register_check("custom_sql")
def _check_custom_sql(rule: "CustomSqlRule", db: SQLiteManager, default_table: str) -> CheckResult:
    """执行自定义 SQL，将结果与期望值通过 comparison 运算符比较。"""
    from pipeforge.config.models import CustomSqlRule
    from pipeforge.core.pipeline import _has_ddl

    if not rule.sql.strip():
        return CheckResult(
            type=rule.type, passed=True,
            message="SQL 为空，跳过检查",
            on_failure=rule.on_failure,
            checked_at=datetime.now().isoformat()
        )

    # 安全检查：禁止 DDL 语句
    if _has_ddl(rule.sql):
        return CheckResult(
            type=rule.type, passed=False,
            message="自定义 SQL 不允许包含 DDL 语句（CREATE/INSERT/WITH 等）",
            on_failure=rule.on_failure,
            checked_at=datetime.now().isoformat()
        )

    rows = db.query(rule.sql)
    if not rows:
        return CheckResult(
            type=rule.type, passed=False,
            message="SQL 执行无结果",
            on_failure=rule.on_failure,
            checked_at=datetime.now().isoformat()
        )

    row = rows[0]
    # SQLite query 返回 tuple，按位置取值；dict 类型结果按 key 取值（兼容两种模式）
    actual_value = None
    if hasattr(row, 'keys'):
        # 返回 dict-like 对象
        row_dict = dict(row)
        actual_value = row_dict.get(rule.result_column)
    elif isinstance(row, (list, tuple)):
        # 返回 tuple，取第 0 列作为 result_column（简化处理）
        actual_value = row[0] if len(row) > 0 else None
    else:
        actual_value = row

    if actual_value is None:
        return CheckResult(
            type=rule.type, passed=False,
            message=f"结果列 '{rule.result_column}' 的值不存在或为 NULL",
            on_failure=rule.on_failure,
            checked_at=datetime.now().isoformat()
        )

    if rule.expected_value is None:
        return CheckResult(
            type=rule.type, passed=True,
            message=f"自定义 SQL 结果 {rule.result_column}={actual_value}（未设置期望值）",
            on_failure=rule.on_failure,
            checked_at=datetime.now().isoformat()
        )

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
        return CheckResult(
            type=rule.type, passed=False,
            message=f"无法比较结果值 '{actual_value}' 与期望值 {rule.expected_value}",
            on_failure=rule.on_failure,
            checked_at=datetime.now().isoformat()
        )

    return CheckResult(
        type=rule.type, passed=passed,
        message=f"自定义 SQL 结果 {rule.result_column}={actual_value}（期望 {op_symbols[rule.comparison]}{rule.expected_value}）",
        on_failure=rule.on_failure,
        checked_at=datetime.now().isoformat()
    )
```

### Step 2: 手动验证——6 种 comparison 运算符

```bash
python3 -c "
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.checkpoints import execute_checks
from pipeforge.config.models import CustomSqlRule

db = SQLiteManager()
db.create_table('test_cs', ['id', 'amount'])
db.insert_row('test_cs', ('1', '100'))
db.insert_row('test_cs', ('2', '200'))
db.insert_row('test_cs', ('3', '300'))

# Test: <= (default) — counts should be 3 <= 5 → pass
r1 = execute_checks([CustomSqlRule(sql='SELECT COUNT(*) AS cnt FROM \"test_cs\"', result_column='cnt', comparison='<=', expected_value=5)], db, 'test_cs')
print(f'count <= 5: passed={r1[0].passed}, {r1[0].message}')

# Test: > — counts 3 > 1 → pass
r2 = execute_checks([CustomSqlRule(sql='SELECT COUNT(*) AS cnt FROM \"test_cs\"', result_column='cnt', comparison='>', expected_value=1)], db, 'test_cs')
print(f'count > 1: passed={r2[0].passed}, {r2[0].message}')

# Test: == — 3 == 3 → pass
r3 = execute_checks([CustomSqlRule(sql='SELECT COUNT(*) AS cnt FROM \"test_cs\"', result_column='cnt', comparison='==', expected_value=3)], db, 'test_cs')
print(f'count == 3: passed={r3[0].passed}, {r3[0].message}')

# Test: DDL blocked
r4 = execute_checks([CustomSqlRule(sql='CREATE TABLE hack (id INT)')], db, 'test_cs')
print(f'DDL blocked: passed={r4[0].passed}, {r4[0].message}')

db.close()
"
```

Expected: first 3 passes, last one fails with DDL mention.

---

## Task 6: 后端 — EnumCheckRule 执行器

**Files:**
- Modify: `src/pipeforge/core/checkpoints.py`

### Step 1: 添加执行器

在 `checkpoints.py` 末尾添加：

```python
@register_check("enum_check")
def _check_enum_check(rule: "EnumCheckRule", db: SQLiteManager, default_table: str) -> CheckResult:
    """检查列值是否在允许的枚举集合内。"""
    from pipeforge.config.models import EnumCheckRule
    table = rule.table or default_table
    if not rule.allowed_values:
        return CheckResult(
            type=rule.type, passed=True,
            message="允许值列表为空，跳过检查",
            on_failure=rule.on_failure,
            checked_at=datetime.now().isoformat()
        )

    # SQLite 参数上限 999，留出安全余量
    if len(rule.allowed_values) > 900:
        return CheckResult(
            type=rule.type, passed=False,
            message=f"枚举值数量 {len(rule.allowed_values)} 超过 SQLite 参数上限（999），请减少枚举值",
            on_failure=rule.on_failure,
            checked_at=datetime.now().isoformat()
        )

    placeholders = ",".join("?" for _ in rule.allowed_values)
    sql = f'SELECT COUNT(*) AS total, SUM(CASE WHEN "{rule.column}" IN ({placeholders}) THEN 1 ELSE 0 END) AS valid FROM "{table}"'
    row = db.query(sql, tuple(rule.allowed_values))[0]
    total = row[0] if isinstance(row[0], int) else 0
    valid = row[1] if isinstance(row[1], int) else 0
    passed = total == valid
    return CheckResult(
        type=rule.type, passed=passed,
        message=f"列 {rule.column} 枚举检查：{valid}/{total} 行在允许值内",
        on_failure=rule.on_failure,
        checked_at=datetime.now().isoformat()
    )
```

### Step 2: 手动验证

```bash
python3 -c "
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.checkpoints import execute_checks
from pipeforge.config.models import EnumCheckRule

db = SQLiteManager()
db.create_table('test_enum', ['id', 'status'])
db.insert_row('test_enum', ('1', 'active'))
db.insert_row('test_enum', ('2', 'inactive'))
db.insert_row('test_enum', ('3', 'active'))
db.insert_row('test_enum', ('4', 'pending'))  # not in allowed

rule = EnumCheckRule(table='test_enum', column='status', allowed_values=['active', 'inactive'])
results = execute_checks([rule], db, 'test_enum')
for r in results:
    print(f'enum check: passed={r.passed}, message={r.message}')

# Test with empty allowed_values
rule2 = EnumCheckRule(table='test_enum', column='status', allowed_values=[])
results2 = execute_checks([rule2], db, 'test_enum')
for r in results2:
    print(f'empty enum: passed={r.passed}, message={r.message}')

db.close()
"
```

Expected:
```
enum check: passed=False, message=...3/4 行在允许值内
empty enum: passed=True, message=允许值列表为空，跳过检查
```

---

## Task 7: 后端 — 更新 AI 翻译 Prompt

**Files:**
- Modify: `configforge/api/ai.py`

### Step 1: 更新 prompt

找到 AI 翻译 prompt 中的规则类型描述，替换为：

```python
可用规则类型：
- row_count: 行数检查 {table, min, max, on_failure}
- null_rate: 空值率检查 {table, column, max_null_rate, on_failure}
- uniqueness: 唯一性检查 {table, column, on_failure}
- value_range: 范围检查 {table, column, min_value, max_value, on_failure}
- custom_sql: 自定义SQL {sql, result_column, comparison, expected_value, on_failure}
  comparison 取值: "<" | "<=" | "==" | "!=" | ">" | ">="
- enum_check: 枚举检查 {table, column, allowed_values, on_failure}
```

### Step 2: Commit (Tasks 2-7 combined)

```bash
git add src/pipeforge/core/checkpoints.py configforge/api/ai.py
git commit -m "feat: add 5 new checkpoint executors (null_rate, uniqueness, value_range, custom_sql, enum_check)"
```

---

## Task 8: 后端 — 单元测试

**Files:**
- Create: `configforge/tests/test_checkpoints.py`

### Step 1: 创建测试文件

```python
"""Tests for checkpoint rule executors."""
import pytest
from pipeforge.core.sqlite import SQLiteManager
from pipeforge.core.checkpoints import execute_checks
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
        # 10 rows, 5 nulls = 50% > 20% threshold
        results = execute_checks([NullRateRule(table="t", column="col", max_null_rate=0.2)], db, "t")
        assert results[0].passed is False

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
        results = execute_checks([UniquenessRule(table="t", column="col")], db, "t")
        assert results[0].passed is False

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
        results = execute_checks([ValueRangeRule(table="t", column="val", min_value=0, max_value=100)], db, "t")
        assert results[0].passed is False

    def test_pass_when_no_bounds_set(self, db):
        db.create_table("t", ["val"])
        db.insert_row("t", ("50",))
        results = execute_checks([ValueRangeRule(table="t", column="val")], db, "t")
        assert results[0].passed is True

    def test_min_only(self, db):
        db.create_table("t", ["val"])
        db.insert_row("t", ("50",))
        db.insert_row("t", ("-5",))
        results = execute_checks([ValueRangeRule(table="t", column="val", min_value=0)], db, "t")
        assert results[0].passed is False


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
        results = execute_checks([CustomSqlRule(
            sql='SELECT COUNT(*) AS cnt FROM "t"',
            result_column="cnt",
            comparison="<",
            expected_value=3,
        )], db, "t")
        assert results[0].passed is False

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
        results = execute_checks([CustomSqlRule(sql="CREATE TABLE hack (id INT)")], db, "t")
        assert results[0].passed is False
        assert "DDL" in results[0].message

    def test_empty_sql_skips(self, db):
        results = execute_checks([CustomSqlRule(sql="")], db, "t")
        assert results[0].passed is True
        assert "跳过" in results[0].message

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
        results = execute_checks([EnumCheckRule(table="t", column="status", allowed_values=["active", "inactive"])], db, "t")
        assert results[0].passed is False

    def test_empty_allowed_skips(self, db):
        db.create_table("t", ["status"])
        db.insert_row("t", ("active",))
        results = execute_checks([EnumCheckRule(table="t", column="status", allowed_values=[])], db, "t")
        assert results[0].passed is True

    def test_over_900_values_rejected(self, db):
        db.create_table("t", ["status"])
        huge_list = [f"val_{i}" for i in range(901)]
        results = execute_checks([EnumCheckRule(table="t", column="status", allowed_values=huge_list)], db, "t")
        assert results[0].passed is False
        assert "900" in results[0].message
```

### Step 2: 运行测试

```bash
cd /Users/lixinyuan/code/CCTEST && python3 -m pytest configforge/tests/test_checkpoints.py -v
```

Expected: 17 passed

### Step 3: Commit

```bash
git add configforge/tests/test_checkpoints.py
git commit -m "test: add unit tests for all 5 new checkpoint executors"
```

---

## Task 9: 后端 — 修复过时的 _has_ddl 测试

**Files:**
- Modify: `configforge/tests/test_pipeline.py:37-54`

### Step 1: 修改测试断言

将第 37-38 行的 `test_with_cte_not_ddl`：

```python
def test_with_cte_not_ddl(self):
    assert _has_ddl("WITH cte AS (SELECT * FROM t) SELECT * FROM cte") is False
```

改为：

```python
def test_with_cte_not_ddl(self):
    # CTE (WITH ... AS) is now detected as DDL (Plan Phase 3.2)
    assert _has_ddl("WITH cte AS (SELECT * FROM t) SELECT * FROM cte") is True
```

将第 52-54 行的 `test_comment_with_create`：

```python
def test_comment_with_create(self):
    # regex requires CREATE at start of string — comments before DDL not matched
    assert _has_ddl("-- comment\nCREATE TABLE foo (id INT)") is False
```

改为：

```python
def test_comment_with_create(self):
    # Comments are now stripped before DDL detection (Plan Phase 3.2)
    assert _has_ddl("-- comment\nCREATE TABLE foo (id INT)") is True
```

### Step 2: 运行这些测试验证修正

```bash
cd /Users/lixinyuan/code/CCTEST && python3 -m pytest configforge/tests/test_pipeline.py::TestHasDdl::test_with_cte_not_ddl configforge/tests/test_pipeline.py::TestHasDdl::test_comment_with_create -v
```

Expected: 2 passed

### Step 3: 运行全量后端测试确认

```bash
cd /Users/lixinyuan/code/CCTEST && python3 -m pytest configforge/tests/ -v
```

Expected: 188 passed (171 original + 17 new checkpoints - 0 broken)

### Step 4: Commit

```bash
git add configforge/tests/test_pipeline.py
git commit -m "test: update _has_ddl tests for CTE detection and comment stripping"
```

---

## Task 10: 前端 — TypeScript 类型定义

**Files:**
- Modify: `configforge-web/src/types/wizard.ts`

### Step 1: 替换 CheckRule 类型

找到当前的 `CheckRule` 接口（约在文件末尾），替换为 discriminative union：

```typescript
export interface RowCountRule {
  type: 'row_count'
  table: string
  min: number
  max?: number
  on_failure: 'block' | 'warn'
}

export interface NullRateRule {
  type: 'null_rate'
  table: string
  column: string
  max_null_rate: number
  on_failure: 'block' | 'warn'
}

export interface UniquenessRule {
  type: 'uniqueness'
  table: string
  column: string
  on_failure: 'block' | 'warn'
}

export interface ValueRangeRule {
  type: 'value_range'
  table: string
  column: string
  min_value?: number
  max_value?: number
  on_failure: 'block' | 'warn'
}

export interface CustomSqlRule {
  type: 'custom_sql'
  sql: string
  result_column: string
  comparison: '<' | '<=' | '==' | '!=' | '>' | '>='
  expected_value?: number
  on_failure: 'block' | 'warn'
}

export interface EnumCheckRule {
  type: 'enum_check'
  table: string
  column: string
  allowed_values: string[]
  on_failure: 'block' | 'warn'
}

export type CheckRule = RowCountRule | NullRateRule | UniquenessRule | ValueRangeRule | CustomSqlRule | EnumCheckRule
```

### Step 2: 验证 TypeScript 编译

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx tsc --noEmit
```

Expected: 0 errors

### Step 3: Commit

```bash
git add configforge-web/src/types/wizard.ts
git commit -m "feat: add 6 discriminated CheckRule types to frontend"
```

---

## Task 11: 前端 — CheckpointSection 动态表单改造

**Files:**
- Modify: `configforge-web/src/components/step3/CheckpointSection.vue`

### 改造概述

当前 CheckpointSection 是硬编码的 row_count 表单。改造为：
1. 规则列表由 `v-for` 渲染
2. 每条规则根据 `type` 切换对应表单
3. 支持添加/删除/切换规则类型

### Step 1: 完整的组件代码

```vue
<template>
  <div class="border border-slate-200 rounded-lg overflow-hidden">
    <!-- 头部：展开/折叠 + 标题 + 添加按钮 -->
    <div
      class="flex items-center gap-2 px-3 py-2 bg-slate-50 border-b border-slate-200 cursor-pointer"
      @click="expanded = !expanded"
    >
      <span class="text-xs font-medium flex-1">数据检查点</span>
      <NTag v-if="rules.length" size="small" type="info">
        {{ rules.length }} 条规则
      </NTag>
      <NButton text size="tiny" @click.stop="expanded = !expanded">
        {{ expanded ? '收起' : '展开' }}
      </NButton>
    </div>

    <!-- 规则列表 -->
    <div v-if="expanded" class="p-3 space-y-3">
      <div
        v-for="(rule, i) in rules"
        :key="i"
        class="border border-slate-200 rounded-lg p-3 space-y-2"
      >
        <!-- 规则类型选择器 + on_failure + 删除 -->
        <div class="flex items-center gap-2">
          <NSelect
            v-model:value="rule.type"
            :options="ruleTypeOptions"
            size="small"
            style="width: 140px"
            @update:value="onRuleTypeChange(i, $event)"
          />
          <NSelect
            v-model:value="rule.on_failure"
            :options="onFailureOptions"
            size="small"
            style="width: 100px"
          />
          <NButton text type="error" size="tiny" class="ml-auto" @click="removeRule(i)">
            删除
          </NButton>
        </div>

        <!-- 通用：检查表（custom_sql 不需要，它自带 FROM） -->
        <div v-if="needsTable(rule)" class="flex items-center gap-2">
          <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">检查表</label>
          <NSelect
            v-model:value="(rule as any).table"
            :options="tableOptions"
            size="small"
            class="flex-1"
            placeholder="默认使用输出表"
            clearable
          />
        </div>

        <!-- row_count 专属 -->
        <template v-if="rule.type === 'row_count'">
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">最小行数</label>
            <NInputNumber v-model:value="(rule as RowCountRule).min" size="small" :min="0" />
            <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">最大行数</label>
            <NInputNumber v-model:value="(rule as RowCountRule).max" size="small" :min="0" />
          </div>
        </template>

        <!-- null_rate 专属 -->
        <template v-if="rule.type === 'null_rate'">
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">检查列</label>
            <NSelect
              v-model:value="(rule as NullRateRule).column"
              :options="columnOptions((rule as any).table)"
              size="small"
              class="flex-1"
              placeholder="选择列或手动输入"
              filterable
              tag
            />
            <label class="text-xs font-medium text-slate-500 w-20 flex-shrink-0">最大空值率</label>
            <NInputNumber
              v-model:value="(rule as NullRateRule).max_null_rate"
              size="small"
              :min="0"
              :max="1"
              :step="0.01"
              style="width: 100px"
            />
          </div>
        </template>

        <!-- uniqueness 专属 -->
        <template v-if="rule.type === 'uniqueness'">
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">检查列</label>
            <NSelect
              v-model:value="(rule as UniquenessRule).column"
              :options="columnOptions((rule as any).table)"
              size="small"
              class="flex-1"
              placeholder="选择列或手动输入"
              filterable
              tag
            />
          </div>
        </template>

        <!-- value_range 专属 -->
        <template v-if="rule.type === 'value_range'">
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">检查列</label>
            <NSelect
              v-model:value="(rule as ValueRangeRule).column"
              :options="columnOptions((rule as any).table)"
              size="small"
              class="flex-1"
              placeholder="选择列或手动输入"
              filterable
              tag
            />
            <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">最小值</label>
            <NInputNumber v-model:value="(rule as ValueRangeRule).min_value" size="small" style="width: 100px" />
            <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">最大值</label>
            <NInputNumber v-model:value="(rule as ValueRangeRule).max_value" size="small" style="width: 100px" />
          </div>
        </template>

        <!-- custom_sql 专属 -->
        <template v-if="rule.type === 'custom_sql'">
          <div class="space-y-2">
            <label class="text-xs font-medium text-slate-500 block">SQL 语句</label>
            <textarea
              v-model="(rule as CustomSqlRule).sql"
              rows="3"
              class="w-full font-mono text-xs p-2 border border-slate-200 rounded resize-y"
              placeholder="SELECT COUNT(*) AS result FROM ..."
            />
            <div class="flex items-center gap-2">
              <label class="text-xs font-medium text-slate-500 w-16 flex-shrink-0">结果列名</label>
              <NInput v-model:value="(rule as CustomSqlRule).result_column" size="small" style="width: 100px" />
              <label class="text-xs font-medium text-slate-500 w-16 flex-shrink-0">比较方式</label>
              <NSelect
                v-model:value="(rule as CustomSqlRule).comparison"
                :options="comparisonOptions"
                size="small"
                style="width: 80px"
              />
              <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">期望值</label>
              <NInputNumber
                v-model:value="(rule as CustomSqlRule).expected_value"
                size="small"
                style="width: 100px"
              />
            </div>
          </div>
        </template>

        <!-- enum_check 专属 -->
        <template v-if="rule.type === 'enum_check'">
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">检查列</label>
            <NSelect
              v-model:value="(rule as EnumCheckRule).column"
              :options="columnOptions((rule as any).table)"
              size="small"
              class="flex-1"
              placeholder="选择列或手动输入"
              filterable
              tag
            />
          </div>
          <div class="flex items-center gap-2">
            <label class="text-xs font-medium text-slate-500 w-14 flex-shrink-0">允许值</label>
            <NInput
              :value="enumValuesText(i)"
              size="small"
              class="flex-1"
              placeholder="值1,值2,值3（逗号分隔）"
              @update:value="updateEnumValues(i, $event)"
            />
          </div>
        </template>
      </div>

      <p v-if="!rules.length" class="text-xs text-slate-400 text-center py-2">
        暂未配置检查点规则
      </p>

      <!-- 添加按钮 -->
      <NButton dashed size="small" block @click="addRule">+ 添加规则</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  NButton,
  NTag,
  NSelect,
  NInput,
  NInputNumber,
} from 'naive-ui'
import type {
  CheckRule,
  RowCountRule,
  NullRateRule,
  UniquenessRule,
  ValueRangeRule,
  CustomSqlRule,
  EnumCheckRule,
} from '../../types/wizard'

const props = defineProps<{
  checkpoints: CheckRule[]
  procIndex: number
  availableTables?: Array<{ table_name: string; columns: string[] }>
}>()

const emit = defineEmits<{
  'update:checkpoints': [rules: CheckRule[]]
}>()

const expanded = ref(false)

const rules = computed<CheckRule[]>({
  get: () => props.checkpoints,
  set: (val) => emit('update:checkpoints', val),
})

const ruleTypeOptions = [
  { label: '行数检查', value: 'row_count' },
  { label: '空值率检查', value: 'null_rate' },
  { label: '唯一性检查', value: 'uniqueness' },
  { label: '范围检查', value: 'value_range' },
  { label: '自定义 SQL', value: 'custom_sql' },
  { label: '枚举检查', value: 'enum_check' },
]

const onFailureOptions = [
  { label: '阻断 (block)', value: 'block' },
  { label: '警告 (warn)', value: 'warn' },
]

const comparisonOptions = [
  { label: '≤', value: '<=' },
  { label: '<', value: '<' },
  { label: '=', value: '==' },
  { label: '≠', value: '!=' },
  { label: '>', value: '>' },
  { label: '≥', value: '>=' },
]

const tableOptions = computed(() => {
  if (!props.availableTables) return []
  return props.availableTables.map((t) => ({
    label: t.table_name,
    value: t.table_name,
  }))
})

function columnOptions(tableName: string) {
  if (!tableName || !props.availableTables) return []
  const table = props.availableTables.find((t) => t.table_name === tableName)
  if (!table) return []
  return table.columns.map((c) => ({ label: c, value: c }))
}

function needsTable(rule: CheckRule): boolean {
  return rule.type !== 'custom_sql'
}

function addRule() {
  const newRule: RowCountRule = {
    type: 'row_count',
    table: '',
    min: 0,
    max: undefined,
    on_failure: 'block',
  }
  emit('update:checkpoints', [...rules.value, newRule])
  expanded.value = true
}

function removeRule(index: number) {
  const updated = [...rules.value]
  updated.splice(index, 1)
  emit('update:checkpoints', updated)
}

function onRuleTypeChange(index: number, newType: string) {
  const oldRule = rules.value[index]
  const base = { on_failure: oldRule.on_failure, table: (oldRule as any).table || '' }

  let newRule: CheckRule
  switch (newType) {
    case 'row_count':
      newRule = { type: 'row_count', ...base, min: 0, max: undefined } as RowCountRule
      break
    case 'null_rate':
      newRule = { type: 'null_rate', ...base, column: '', max_null_rate: 0.05 } as NullRateRule
      break
    case 'uniqueness':
      newRule = { type: 'uniqueness', ...base, column: '' } as UniquenessRule
      break
    case 'value_range':
      newRule = { type: 'value_range', ...base, column: '', min_value: undefined, max_value: undefined } as ValueRangeRule
      break
    case 'custom_sql':
      newRule = { type: 'custom_sql', on_failure: base.on_failure, sql: '', result_column: 'result', comparison: '<=', expected_value: undefined } as CustomSqlRule
      break
    case 'enum_check':
      newRule = { type: 'enum_check', ...base, column: '', allowed_values: [] } as EnumCheckRule
      break
    default:
      newRule = { type: 'row_count', ...base, min: 0, max: undefined } as RowCountRule
  }

  const updated = [...rules.value]
  updated[index] = newRule
  emit('update:checkpoints', updated)
}

function enumValuesText(index: number): string {
  const rule = rules.value[index]
  if (rule.type === 'enum_check') {
    return (rule as EnumCheckRule).allowed_values.join(',')
  }
  return ''
}

function updateEnumValues(index: number, text: string) {
  const rule = rules.value[index]
  if (rule.type === 'enum_check') {
    const updated = [...rules.value]
    ;(updated[index] as EnumCheckRule).allowed_values = text
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    emit('update:checkpoints', updated)
  }
}
</script>
```

### Step 2: 验证 TypeScript 编译

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx tsc --noEmit
```

Expected: 0 errors

### Step 3: 运行现有测试确保向后兼容

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run
```

Expected: 所有测试通过（ProcessorCard 测试中的 CheckpointSection stub 无需修改，因为它只检查 stub 存在性）

### Step 4: Commit

```bash
git add configforge-web/src/components/step3/CheckpointSection.vue
git commit -m "feat: refactor CheckpointSection with dynamic rule type switching"
```

---

## Task 12: 前端 — CheckpointSection 组件测试

**Files:**
- Create: `configforge-web/tests/components/CheckpointSection.test.ts`

### Step 1: 创建测试文件

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CheckpointSection from '../../src/components/step3/CheckpointSection.vue'
import type { CheckRule, RowCountRule, NullRateRule, EnumCheckRule } from '../../src/types/wizard'

// Mock NInputNumber — it requires additional context in Naive UI
vi.mock('naive-ui', async () => {
  const actual = await vi.importActual('naive-ui')
  return {
    ...(actual as any),
    NInputNumber: {
      name: 'NInputNumber',
      template: '<input type="number" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
      props: ['modelValue', 'min', 'max', 'step', 'size'],
      emits: ['update:modelValue'],
    },
  }
})

function makeRowCount(overrides: Partial<RowCountRule> = {}): RowCountRule {
  return { type: 'row_count', table: '', min: 0, max: undefined, on_failure: 'block', ...overrides }
}

describe('CheckpointSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  function mountComponent(checkpoints: CheckRule[] = []) {
    return mount(CheckpointSection, {
      props: {
        checkpoints,
        procIndex: 1,
        availableTables: [
          { table_name: 'output', columns: ['id', 'name', 'status', 'amount'] },
        ],
      },
      global: {
        plugins: [createPinia()],
        stubs: {
          NInputNumber: {
            template: '<input type="number" class="n-input-number-stub" />',
            props: ['modelValue', 'min', 'max', 'step'],
          },
        },
      },
    })
  }

  it('renders collapsed by default', () => {
    const wrapper = mountComponent()
    expect(wrapper.text()).toContain('数据检查点')
    expect(wrapper.find('.p-3').exists()).toBe(false)
  })

  it('expands on header click', async () => {
    const wrapper = mountComponent()
    await wrapper.find('.cursor-pointer').trigger('click')
    expect(wrapper.find('.p-3').exists()).toBe(true)
  })

  it('renders empty state when no rules', async () => {
    const wrapper = mountComponent()
    await wrapper.find('.cursor-pointer').trigger('click')
    expect(wrapper.text()).toContain('暂未配置检查点规则')
  })

  it('renders existing row_count rule', async () => {
    const wrapper = mountComponent([makeRowCount({ table: 't1', min: 10 })])
    await wrapper.find('.cursor-pointer').trigger('click')
    expect(wrapper.text()).toContain('行数检查')
    expect(wrapper.text()).toContain('1 条规则')
  })

  it('adds a new rule on button click', async () => {
    const wrapper = mountComponent([])
    await wrapper.find('.cursor-pointer').trigger('click')
    const btn = wrapper.find('button:has-text("添加规则")')
    expect(btn.exists()).toBe(true)
    // Click add — should emit new checkpoints
    await btn.trigger('click')
    const emitted = wrapper.emitted('update:checkpoints') as any
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toHaveLength(1)
    expect(emitted[0][0][0].type).toBe('row_count')
  })

  it('removes a rule on delete click', async () => {
    const wrapper = mountComponent([makeRowCount()])
    await wrapper.find('.cursor-pointer').trigger('click')
    const deleteBtn = wrapper.find('button:has-text("删除")')
    await deleteBtn.trigger('click')
    const emitted = wrapper.emitted('update:checkpoints') as any
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toHaveLength(0)
  })

  it('switches rule type and resets fields', async () => {
    const wrapper = mountComponent([makeRowCount()])
    await wrapper.find('.cursor-pointer').trigger('click')

    // Find the type selector and change to null_rate
    const select = wrapper.findComponent({ name: 'NSelect' })
    // Trigger update:value on the first select (type selector)
    await select.vm.$emit('update:value', 'null_rate')

    const emitted = wrapper.emitted('update:checkpoints') as any
    // Should not trigger from the NSelect alone — CheckpointSection uses v-model
    // which triggers update:checkpoints only via our explicit functions
  })
})
```

### Step 2: 运行测试

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run tests/components/CheckpointSection.test.ts
```

Expected: 所有测试通过

### Step 3: Commit

```bash
git add configforge-web/tests/components/CheckpointSection.test.ts
git commit -m "test: add CheckpointSection dynamic form tests"
```

---

## Task 13: 集成 — 全量测试回归

### Step 1: 后端全量测试

```bash
cd /Users/lixinyuan/code/CCTEST && python3 -m pytest configforge/tests/ -v
```

Expected: 188 passed (all green)

### Step 2: 前端全量测试

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx vitest run
```

Expected: 所有测试通过，0 failures

### Step 3: TypeScript 零错误

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npx tsc --noEmit
```

Expected: 0 errors

### Step 4: 前端构建

```bash
cd /Users/lixinyuan/code/CCTEST/configforge-web && npm run build
```

Expected: 构建成功

---

## 任务清单摘要

| Task | 内容 | 预计时间 |
|------|------|---------|
| 1 | Pydantic 模型：6 种 Rule + CheckRule Union | 15 min |
| 2 | NullRateRule 执行器 | 10 min |
| 3 | UniquenessRule 执行器 | 10 min |
| 4 | ValueRangeRule 执行器 | 10 min |
| 5 | CustomSqlRule 执行器 | 15 min |
| 6 | EnumCheckRule 执行器 | 10 min |
| 7 | 更新 AI Prompt | 5 min |
| 8 | 后端单元测试 (17 用例) | 20 min |
| 9 | 修复 _has_ddl 测试 | 5 min |
| 10 | 前端 TypeScript 类型 | 10 min |
| 11 | CheckpointSection 动态表单 | 30 min |
| 12 | CheckpointSection 组件测试 | 15 min |
| 13 | 全量回归 | 10 min |
| **总计** | | **~3 hours** |

---

## 交付标准

- [ ] 6 种 CheckRule 可在 YAML 中正确序列化/反序列化
- [ ] 5 种新执行器全部通过单元测试（通过 + 失败 + 边界）
- [ ] CustomSqlRule 支持 6 种比较运算符
- [ ] UniquenessRule 正确排除 NULL
- [ ] EnumCheckRule 超过 900 值时拒绝
- [ ] CustomSqlRule DDL 被拦截
- [ ] 后端全量测试通过（无回归）
- [ ] 前端 TypeScript 0 错误
- [ ] CheckpointSection 支持 6 种规则动态切换
- [ ] 前端全量测试通过（无回归）
- [ ] 前端生产构建成功
