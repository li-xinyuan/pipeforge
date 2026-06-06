# ConfigForge 功能演进实施计划

> 日期：2026-06-06
> 版本：v1.1
> 状态：已修正（根据审查报告 v1.0 修订）

---

## 总体路线图

| 阶段 | 方向 | 预计周期 | 依赖 |
|------|------|---------|------|
| Phase 1 | 检查点规则扩展 | 1-2 周 | 无 |
| Phase 2 | 配置版本管理 | 2 周 | 无（独立，为 Phase 3 提供版本锚点） |
| Phase 3 | 执行历史与结果管理 | 2-3 周 | Phase 2（执行记录关联 config_version） |
| Phase 4 | 数据库输出 | 1-2 周 | 无（最复杂，放最后，不受前面阻塞） |

> **v1.1 变更说明**：阶段顺序从 1→2→3→4 调整为 1→2→3→4（原 Phase 4 版本管理提前到 Phase 2，原 Phase 2 数据库输出移至 Phase 4）。理由：执行记录（Phase 3）应关联配置版本号，版本管理必须先于执行历史完成。

---

## Phase 1：检查点规则扩展

### 1.1 目标

从仅支持 `row_count` 扩展为支持 5 种检查点规则，覆盖数据质量校验的常见场景。

### 1.2 规则清单与优先级

| 批次 | 规则 | type 值 | 配置参数 | 场景 |
|------|------|---------|---------|------|
| P1-a | 空值率检查 | `null_rate` | `table, column, max_null_rate(0-1), on_failure` | 检查某列空值比例是否超阈值 |
| P1-a | 唯一性检查 | `uniqueness` | `table, column, on_failure` | 检查某列值是否唯一（如 ID、编码） |
| P1-b | 范围检查 | `value_range` | `table, column, min_value, max_value, on_failure` | 检查数值列是否在合理范围 |
| P1-b | 自定义 SQL | `custom_sql` | `sql, result_column, comparison, expected_value, on_failure` | 灵活的自定义校验 |
| P1-c | 枚举检查 | `enum_check` | `table, column, allowed_values, on_failure` | 检查值是否在允许集合内 |

> 暂不实现：`duplicate_rate`（与 uniqueness 重叠）、`referential_integrity`（跨表查询复杂度高，Phase 4 数据库输出后更有意义）

### 1.3 后端改动

#### 1.3.1 数据模型 — `src/pipeforge/config/models.py`

当前：
```python
class RowCountRule(BaseModel):
    type: Literal["row_count"] = "row_count"
    table: str = ""
    min: int = 0
    max: int | None = None
    on_failure: Literal["block", "warn"] = "block"

CheckRule = RowCountRule
```

改为：
```python
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
    result_column: str = "result"       # 执行 SQL 取结果集第一行指定列的值
    comparison: Literal["<", "<=", "==", "!=", ">", ">="] = "<="  # 比较运算符
    expected_value: float | None = None  # 期望值，与实际值通过 comparison 比较
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
```

关键设计决策：
- 使用 Pydantic v2 的 `Annotated[Union, Field(discriminator="type")]` 判别联合
- 每种规则都有 `on_failure` 字段，保持一致性
- 所有新 Rule 模型添加 `model_config = ConfigDict(extra="forbid")`，防止多余字段被静默忽略
- `NullRateRule.max_null_rate` 默认 0.05（5%），使用 `ge=0, le=1` 约束
- `CustomSqlRule` 使用 `result_column` + `comparison` + `expected_value` 模式：执行 SQL 取结果集第一行指定列的值，通过 comparison 运算符与 expected_value 比较。支持 `<`, `<=`, `==`, `!=`, `>`, `>=` 六种比较方式，覆盖行数下限检查、金额对账、数据量上限等场景
- `EnumCheckRule.allowed_values` 为字符串列表，前端用逗号分隔输入

#### 1.3.2 执行器 — `src/pipeforge/core/checkpoints.py`

新增 5 个执行器函数：

```python
@register_check("null_rate")
def _check_null_rate(rule: NullRateRule, db: SQLiteManager, default_table: str) -> CheckResult:
    table = rule.table or default_table
    sql = f'SELECT COUNT(*) AS total, SUM(CASE WHEN "{rule.column}" IS NULL THEN 1 ELSE 0 END) AS nulls FROM "{table}"'
    row = db.query(sql)[0]
    total, nulls = row["total"], row["nulls"]
    actual_rate = nulls / total if total > 0 else 0
    passed = actual_rate <= rule.max_null_rate
    return CheckResult(
        type=rule.type, passed=passed,
        message=f"列 {rule.column} 空值率 {actual_rate:.2%}（阈值 {rule.max_null_rate:.2%}）",
        on_failure=rule.on_failure,
    )

@register_check("uniqueness")
def _check_uniqueness(rule: UniquenessRule, db: SQLiteManager, default_table: str) -> CheckResult:
    table = rule.table or default_table
    # 排除 NULL 值：NULL 在 COUNT(DISTINCT) 中被视为一个值，会导致含 NULL 的唯一列误判为不唯一
    sql = f'SELECT COUNT("{rule.column}") AS total, COUNT(DISTINCT "{rule.column}") AS distinct_count FROM "{table}" WHERE "{rule.column}" IS NOT NULL'
    row = db.query(sql)[0]
    passed = row["total"] == row["distinct_count"]
    return CheckResult(
        type=rule.type, passed=passed,
        message=f"列 {rule.column} 唯一性检查：{row['total']} 行中 {row['distinct_count']} 个不同值（排除 NULL）",
        on_failure=rule.on_failure,
    )

@register_check("value_range")
def _check_value_range(rule: ValueRangeRule, db: SQLiteManager, default_table: str) -> CheckResult:
    table = rule.table or default_table
    conditions = []
    if rule.min_value is not None:
        conditions.append(f'"{rule.column}" >= {rule.min_value}')
    if rule.max_value is not None:
        conditions.append(f'"{rule.column}" <= {rule.max_value}')
    if not conditions:
        return CheckResult(type=rule.type, passed=True, message="未设置范围约束", on_failure=rule.on_failure)
    where = " AND ".join(conditions)
    sql = f'SELECT COUNT(*) AS total, SUM(CASE WHEN {where} THEN 1 ELSE 0 END) AS in_range FROM "{table}"'
    row = db.query(sql)[0]
    passed = row["total"] == row["in_range"]
    range_desc = f"[{rule.min_value}, {rule.max_value}]" if rule.min_value is not None and rule.max_value is not None else f"{'≥' + str(rule.min_value) if rule.min_value is not None else ''}{'≤' + str(rule.max_value) if rule.max_value is not None else ''}"
    return CheckResult(
        type=rule.type, passed=passed,
        message=f"列 {rule.column} 范围检查 {range_desc}：{row['in_range']}/{row['total']} 行在范围内",
        on_failure=rule.on_failure,
    )

@register_check("custom_sql")
def _check_custom_sql(rule: CustomSqlRule, db: SQLiteManager, default_table: str) -> CheckResult:
    if not rule.sql.strip():
        return CheckResult(type=rule.type, passed=True, message="SQL 为空，跳过检查", on_failure=rule.on_failure)
    rows = db.query(rule.sql)
    if not rows:
        return CheckResult(type=rule.type, passed=False, message="SQL 执行无结果", on_failure=rule.on_failure)
    actual_value = rows[0].get(rule.result_column)
    if actual_value is None:
        return CheckResult(type=rule.type, passed=False, message=f"结果列 '{rule.result_column}' 不存在", on_failure=rule.on_failure)
    if rule.expected_value is None:
        return CheckResult(type=rule.type, passed=True, message=f"自定义 SQL 结果 {rule.result_column}={actual_value}（未设置期望值）", on_failure=rule.on_failure)
    # 使用 comparison 运算符进行比较
    ops = {"<": lambda a, e: a < e, "<=": lambda a, e: a <= e, "==": lambda a, e: a == e,
           "!=": lambda a, e: a != e, ">": lambda a, e: a > e, ">=": lambda a, e: a >= e}
    passed = ops[rule.comparison](float(actual_value), rule.expected_value)
    op_symbols = {"<": "<", "<=": "≤", "==": "=", "!=": "≠", ">": ">", ">=": "≥"}
    return CheckResult(
        type=rule.type, passed=passed,
        message=f"自定义 SQL 结果 {rule.result_column}={actual_value}（期望 {op_symbols[rule.comparison]}{rule.expected_value}）",
        on_failure=rule.on_failure,
    )

@register_check("enum_check")
def _check_enum_check(rule: EnumCheckRule, db: SQLiteManager, default_table: str) -> CheckResult:
    table = rule.table or default_table
    if not rule.allowed_values:
        return CheckResult(type=rule.type, passed=True, message="允许值列表为空，跳过检查", on_failure=rule.on_failure)
    # 注意：SQLite 参数上限为 999，allowed_values 超过此限制时需分批查询
    if len(rule.allowed_values) > 900:  # 留出安全余量
        return CheckResult(type=rule.type, passed=False, message=f"枚举值数量 {len(rule.allowed_values)} 超过 SQLite 参数上限（999），请减少枚举值", on_failure=rule.on_failure)
    placeholders = ",".join("?" for _ in rule.allowed_values)
    sql = f'SELECT COUNT(*) AS total, SUM(CASE WHEN "{rule.column}" IN ({placeholders}) THEN 1 ELSE 0 END) AS valid FROM "{table}"'
    row = db.query(sql, rule.allowed_values)[0]
    passed = row["total"] == row["valid"]
    return CheckResult(
        type=rule.type, passed=passed,
        message=f"列 {rule.column} 枚举检查：{row['valid']}/{row['total']} 行在允许值内",
        on_failure=rule.on_failure,
    )
```

安全注意事项：
- `custom_sql` 的 SQL 需经过 `_has_ddl()` 检查，禁止 DDL 语句
- 所有表名/列名使用双引号 `""` 转义（与现有代码库 `sqlite.py`、`preview.py` 保持一致）
- `enum_check` 使用参数化查询防止注入；当枚举值超过 900 个时直接拒绝执行，避免触发 SQLite 999 参数上限
- `uniqueness` 检查加 `WHERE "{column}" IS NOT NULL` 排除 NULL 值，避免 NULL 干扰唯一性判断

#### 1.3.3 API 层 — `configforge/api/ai.py`

更新 AI 翻译 prompt 中的规则类型列表：

```python
可用规则类型：
- row_count: 行数检查 {table, min, max}
- null_rate: 空值率检查 {table, column, max_null_rate}
- uniqueness: 唯一性检查 {table, column}
- value_range: 范围检查 {table, column, min_value, max_value}
- custom_sql: 自定义SQL {sql, result_column, comparison, expected_value}
- enum_check: 枚举检查 {table, column, allowed_values}
```

#### 1.3.4 不需要改动的文件

| 文件 | 原因 |
|------|------|
| `configforge/models/wizard.py` | `ProcessorConfig.checkpoints` 类型为 `list[CheckRule]`，自动跟随 Union 变化 |
| `configforge/services/yaml_builder.py` | 使用 `r.model_dump()` 自动序列化，Union 类型不影响 |
| `configforge/core/pipeline.py` | `execute_checks()` 已是通用分发逻辑 |
| `configforge/api/wizard.py` | CheckpointError 处理逻辑不变 |

### 1.4 前端改动

#### 1.4.1 类型定义 — `configforge-web/src/types/wizard.ts`

当前：
```ts
export interface CheckRule {
  type: 'row_count'
  table: string
  min: number
  max?: number
  on_failure: 'block' | 'warn'
}
```

改为：
```ts
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

#### 1.4.2 序列化 — `configforge-web/src/utils/serialization.ts`

`stateToSnakeCase()` 中 checkpoints 的序列化需要根据 `type` 字段做 discriminated union 处理。当前实现是直接映射，需要确保每种规则的特有字段都被正确转换。

新增字段映射：
```ts
// NullRateRule
max_null_rate → max_null_rate  // 已是 snake_case
// ValueRangeRule
min_value → min_value  // 已是 snake_case
max_value → max_value  // 已是 snake_case
// CustomSqlRule
result_column → result_column  // 已是 snake_case
comparison → comparison  // 已是 snake_case
expected_value → expected_value  // 已是 snake_case
// EnumCheckRule
allowed_values → allowed_values  // 已是 snake_case
```

> 大部分字段名已经是 snake_case，序列化层改动极小。

#### 1.4.3 CheckpointSection 组件 — `configforge-web/src/components/step3/CheckpointSection.vue`

**核心改造**：从硬编码 row_count 表单改为动态规则类型表单。

> **组件拆分建议**：由于 6 种规则的模板+逻辑会使 CheckpointSection 超过 400 行，建议将每种规则类型的表单拆分为独立子组件（如 `NullRateForm.vue`、`CustomSqlForm.vue` 等），CheckpointSection 仅负责规则列表管理和类型切换分发。

模板结构：
```html
<template>
  <div class="border border-slate-200 rounded-lg overflow-hidden">
    <!-- 头部：展开/折叠 + 标题 + 添加按钮 -->
    <div class="flex items-center gap-2 px-3 py-2 bg-slate-50 border-b border-slate-200 cursor-pointer" @click="expanded = !expanded">
      <span class="text-xs font-medium flex-1">数据检查点</span>
      <NTag v-if="rules.length" size="small" type="info">{{ rules.length }} 条规则</NTag>
      <NButton text size="tiny" @click.stop="expanded = !expanded">{{ expanded ? '收起' : '展开' }}</NButton>
    </div>

    <!-- 规则列表 -->
    <div v-if="expanded" class="p-3 space-y-3">
      <div v-for="(rule, i) in rules" :key="i" class="border border-slate-200 rounded-lg p-3 space-y-2">
        <!-- 规则类型选择器 + 删除 -->
        <div class="flex items-center gap-2">
          <NSelect v-model:value="rule.type" :options="ruleTypeOptions" size="small" style="width: 140px;" @update:value="onRuleTypeChange(i, $event)" />
          <NSelect v-model:value="rule.on_failure" :options="onFailureOptions" size="small" style="width: 100px;" />
          <NButton text type="error" size="tiny" class="ml-auto" @click="removeRule(i)">删除</NButton>
        </div>

        <!-- 通用：检查表 -->
        <div v-if="needsTable(rule)" class="flex items-center gap-2">
          <label style="font-size: var(--font-size-xs); font-weight: 500; color: var(--color-text-muted); width: 60px;">检查表</label>
          <NSelect v-model:value="rule.table" :options="tableOptions" size="small" placeholder="默认使用输出表" />
        </div>

        <!-- row_count 专属 -->
        <template v-if="rule.type === 'row_count'">
          <div class="flex items-center gap-2">
            <label style="...">最小行数</label>
            <NInputNumber v-model:value="rule.min" size="small" :min="0" />
            <label style="...">最大行数</label>
            <NInputNumber v-model:value="rule.max" size="small" :min="0" />
          </div>
        </template>

        <!-- null_rate 专属 -->
        <template v-if="rule.type === 'null_rate'">
          <div class="flex items-center gap-2">
            <label style="...">检查列</label>
            <NSelect v-model:value="rule.column" :options="columnOptions(rule.table)" size="small" />
            <label style="...">最大空值率</label>
            <NInputNumber v-model:value="rule.max_null_rate" size="small" :min="0" :max="1" :step="0.01" />
          </div>
        </template>

        <!-- uniqueness 专属 -->
        <template v-if="rule.type === 'uniqueness'">
          <div class="flex items-center gap-2">
            <label style="...">检查列</label>
            <NSelect v-model:value="rule.column" :options="columnOptions(rule.table)" size="small" />
          </div>
        </template>

        <!-- value_range 专属 -->
        <template v-if="rule.type === 'value_range'">
          <div class="flex items-center gap-2">
            <label style="...">检查列</label>
            <NSelect v-model:value="rule.column" :options="columnOptions(rule.table)" size="small" />
            <label style="...">最小值</label>
            <NInputNumber v-model:value="rule.min_value" size="small" />
            <label style="...">最大值</label>
            <NInputNumber v-model:value="rule.max_value" size="small" />
          </div>
        </template>

        <!-- custom_sql 专属 -->
        <template v-if="rule.type === 'custom_sql'">
          <div class="space-y-2">
            <label style="...">SQL 语句</label>
            <textarea v-model="rule.sql" rows="3" style="width:100%;font-family:monospace;font-size:12px;padding:8px;border:1px solid var(--color-border);border-radius:var(--radius-sm);resize:vertical;" />
            <div class="flex items-center gap-2">
              <label style="...">结果列名</label>
              <NInput v-model:value="rule.result_column" size="small" />
              <label style="...">比较方式</label>
              <NSelect v-model:value="rule.comparison" :options="comparisonOptions" size="small" style="width: 80px;" />
              <label style="...">期望值</label>
              <NInputNumber v-model:value="rule.expected_value" size="small" />
            </div>
          </div>
        </template>

        <!-- enum_check 专属 -->
        <template v-if="rule.type === 'enum_check'">
          <div class="flex items-center gap-2">
            <label style="...">检查列</label>
            <NSelect v-model:value="rule.column" :options="columnOptions(rule.table)" size="small" />
          </div>
          <div class="flex items-center gap-2">
            <label style="...">允许值</label>
            <NInput :value="enumValuesText(i)" size="small" placeholder="值1,值2,值3" @update:value="updateEnumValues(i, $event)" />
          </div>
        </template>
      </div>

      <!-- 添加按钮 -->
      <NButton dashed size="small" block @click="addRule">+ 添加规则</NButton>
    </div>
  </div>
</template>
```

Script 关键逻辑：
```ts
const ruleTypeOptions = [
  { label: '行数检查', value: 'row_count' },
  { label: '空值率检查', value: 'null_rate' },
  { label: '唯一性检查', value: 'uniqueness' },
  { label: '范围检查', value: 'value_range' },
  { label: '自定义 SQL', value: 'custom_sql' },
  { label: '枚举检查', value: 'enum_check' },
]

const onFailureOptions = [
  { label: '阻断', value: 'block' },
  { label: '警告', value: 'warn' },
]

const comparisonOptions = [
  { label: '≤', value: '<=' },
  { label: '<', value: '<' },
  { label: '=', value: '==' },
  { label: '≠', value: '!=' },
  { label: '>', value: '>' },
  { label: '≥', value: '>=' },
]

function onRuleTypeChange(index: number, newType: string) {
  const rule = rules.value[index]
  const base = { type: newType, on_failure: rule.on_failure, table: rule.table }
  switch (newType) {
    case 'row_count': Object.assign(rule, { ...base, min: 0, max: null }); break
    case 'null_rate': Object.assign(rule, { ...base, column: '', max_null_rate: 0.05 }); break
    case 'uniqueness': Object.assign(rule, { ...base, column: '' }); break
    case 'value_range': Object.assign(rule, { ...base, column: '', min_value: null, max_value: null }); break
    case 'custom_sql': Object.assign(rule, { ...base, sql: '', result_column: 'result', comparison: '<=', expected_value: null }); break
    case 'enum_check': Object.assign(rule, { ...base, column: '', allowed_values: [] }); break
  }
}

function needsTable(rule: CheckRule): boolean {
  return rule.type !== 'custom_sql'
}

// 枚举值输入：allowed_values 数组 ↔ 逗号分隔字符串
function enumValuesText(index: number): string {
  const rule = rules.value[index]
  if (rule.type === 'enum_check') return rule.allowed_values.join(',')
  return ''
}

function updateEnumValues(index: number, text: string) {
  const rule = rules.value[index]
  if (rule.type === 'enum_check') rule.allowed_values = text.split(',').map(s => s.trim()).filter(Boolean)
}
```

#### 1.4.4 列选项获取

需要新增 API 调用获取指定表的列列表。当前 `dry_run` 返回的中间表信息已包含列名，可从 store 中获取。

方案：CheckpointSection 接收 `availableTables` prop（与 SqlProcessorContent 一致），从中提取列信息。

> **注意**：用户可能在 dry_run 之前就配置检查点，此时列选项为空。应在 UI 上给出提示（如"请先执行预览以获取列列表"），同时允许手动输入列名。

### 1.5 测试计划

| 测试类型 | 范围 | 用例数 |
|----------|------|--------|
| 后端单元测试 | 每种规则的执行器 | 5×2 = 10（通过/失败各一） |
| 后端单元测试 | CustomSqlRule 六种 comparison 运算符 | 6 |
| 后端单元测试 | UniquenessRule NULL 排除逻辑 | 2 |
| 后端单元测试 | EnumCheckRule 参数超限拒绝 | 1 |
| 后端集成测试 | `execute_checks()` 完整流程 | 3 |
| API E2E 测试 | 创建配置+检查点 → dry_run → 验证结果 | 3 |
| 前端组件测试 | CheckpointSection 动态表单 | 5 |
| 前端 E2E 测试 | 完整向导流程含检查点 | 2 |

### 1.6 交付标准

- [ ] 5 种检查点规则后端执行器全部实现并通过单元测试
- [ ] CustomSqlRule 支持 6 种比较运算符
- [ ] UniquenessRule 正确排除 NULL 值
- [ ] EnumCheckRule 超过 900 个枚举值时拒绝执行
- [ ] Pydantic discriminated union 反序列化正确
- [ ] 新 Rule 模型均有 `extra="forbid"` 配置
- [ ] YAML 序列化/反序列化兼容
- [ ] 前端 CheckpointSection 动态表单正确渲染
- [ ] 规则类型切换时字段正确重置
- [ ] AI 翻译 prompt 更新
- [ ] 0 个 type error，所有测试通过

---

## Phase 2：配置版本管理

### 2.1 目标

配置保存时自动创建版本快照，支持查看版本历史、对比差异、回滚到历史版本。为 Phase 3（执行历史）提供版本锚点。

### 2.2 存储方案

继续使用文件系统，在现有配置目录下增加版本子目录：

```
configforge/
  configs/
    index.json                          # 索引（增加 current_version, created_at 字段）
    {config_id}.state.json              # 当前最新版本
    {config_id}.yaml                    # 当前最新 YAML
    {config_id}/                        # 版本历史目录
      v1.state.json
      v1.yaml
      v2.state.json
      v2.yaml
```

### 2.3 数据模型

```python
class ConfigMeta(BaseModel):
    id: str
    scene_name: str
    description: str = ""
    version: str = "1.0"           # 用户填写的场景版本
    current_version: int = 1       # 自动递增的配置版本号
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    input_count: int = 0
    output_type: str = ""

class ConfigVersionMeta(BaseModel):
    version: int
    scene_version: str = "1.0"
    change_summary: str = ""
    created_at: str = ""
    input_count: int = 0
    processor_count: int = 0
    output_type: str = ""
```

### 2.4 API 设计

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/configs` | POST | 保存配置（自动递增版本号，旧版本移入历史目录） |
| `/api/configs/{id}/versions` | GET | 获取版本列表 |
| `/api/configs/{id}/versions/{v}` | GET | 获取指定版本的 state JSON |
| `/api/configs/{id}/versions/{v}/yaml` | GET | 下载指定版本的 YAML |
| `/api/configs/{id}/diff?v1=X&v2=Y` | GET | 版本对比（结构化 diff） |
| `/api/configs/{id}/versions/{v}/rollback` | POST | 回滚到指定版本（追加式） |

### 2.5 版本对比实现

后端使用 `deepdiff` 库做深度对比：

> **新增依赖**：`deepdiff` 需在 `requirements.txt` / `pyproject.toml` 中显式声明。

```python
from deepdiff import DeepDiff

def compare_versions(state_v1: dict, state_v2: dict) -> dict:
    diff = DeepDiff(state_v1, state_v2, ignore_order=True)
    return {
        "added": [...],      # 新增的路径
        "removed": [...],    # 删除的路径
        "changed": [...],    # 修改的路径（含旧值和新值）
        "summary": "...",    # 人类可读的变更摘要
    }
```

前端版本对比组件：
- 左右分栏展示两个版本的 YAML
- 差异行高亮（新增=绿色、删除=红色、修改=黄色）
- 结构化变更列表（输入源增删、步骤增删、配置修改）

### 2.6 回滚语义（追加式）

回滚采用**追加式（方案 B）**：回滚时创建新版本，内容等于目标版本，而非修改历史指针。

```python
def rollback_config(config_id: str, target_version: int) -> ConfigMeta:
    # 1. 读取目标版本的内容
    target_state = read_version_file(config_id, target_version)
    target_yaml = read_version_yaml(config_id, target_version)

    # 2. 递增版本号，创建新版本
    new_version = meta.current_version + 1
    write_version_file(config_id, new_version, target_state)
    write_version_yaml(config_id, new_version, target_yaml)

    # 3. 更新当前版本
    write_current_state(config_id, target_state)
    write_current_yaml(config_id, target_yaml)

    # 4. 更新元数据
    meta.current_version = new_version
    meta.updated_at = datetime.now().isoformat()

    return meta
```

关键特性：
- 历史始终线性递增，不会出现分叉
- 回滚操作的 `change_summary` 自动标注 `"回滚自 v{target_version}"`
- 用户可以"回滚的回滚"，操作完全可逆
- 不会丢失任何历史版本

### 2.7 交付标准

- [ ] 保存配置时自动创建版本快照
- [ ] 版本列表页面可用
- [ ] 版本对比功能正确展示差异
- [ ] 回滚功能采用追加式，创建新版本而非修改历史指针
- [ ] 现有无版本数据自动标记为 v1
- [ ] `deepdiff` 依赖已声明
- [ ] 0 个 type error，所有测试通过

---

## Phase 3：执行历史与结果管理

### 3.1 目标

将执行结果持久化，支持查看历史执行记录、下载历史输出文件、查看执行详情。执行记录关联配置版本号，实现完整可追溯。

### 3.2 存储方案

**选择方案 A：继续使用 JSON 文件存储**（与现有架构一致）

目录结构：
```
configforge/
  data/
    executions/
      index.json                    # 执行历史索引
      {exec_id}/
        result.json                 # ExecutionRecord
        output.xlsx / output.csv    # 输出文件（保留）
```

### 3.3 数据模型

```python
class ExecutionRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    config_id: str
    config_version: int | None = None   # 关联配置版本号（Phase 2 提供）
    scene_name: str
    status: Literal["success", "failed"] = "success"  # running 预留给异步执行，当前同步模式下仅 success/failed
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str | None = None
    duration_ms: int = 0
    inputs_summary: list[dict] = []
    processors_summary: list[dict] = []
    output_summary: dict | None = None
    checks_summary: list[dict] = []
    error_message: str | None = None
    output_file_name: str | None = None
```

关键设计决策：
- `config_version`：关联执行时配置的版本号，由 Phase 2 的版本管理系统提供。若配置尚未保存过版本，该字段为 `None`
- `status`：当前同步执行模式下仅使用 `success`/`failed`。`running` 状态预留给未来异步执行，当前不在代码中使用
- **敏感数据脱敏**：`inputs_summary` 和 `output_summary` 中涉及连接字符串等敏感信息时，需脱敏处理（如 `mysql://user:***@host:3306/db`），避免明文存储密码

### 3.4 API 设计

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/executions` | GET | 列出执行历史（支持 `?config_id=xxx` 过滤、分页） |
| `/api/executions/{exec_id}` | GET | 获取单次执行详情 |
| `/api/executions/{exec_id}/download` | GET | 下载执行输出文件 |
| `/api/executions/{exec_id}` | DELETE | 删除执行记录及文件 |

修改现有 API：
- `POST /api/wizard/execute` — 执行后创建记录（status=success/failed），输出文件移到执行目录
- `POST /api/configs/{config_id}/execute` — 同上

### 3.5 前端改动

1. **新增路由** `/history`
2. **新增页面** `ExecutionHistoryView.vue` — 执行历史列表（表格：时间、配置名、版本号、状态、耗时、操作）
3. **新增组件** `ExecutionDetailModal.vue` — 执行详情弹窗（输入统计、步骤耗时、检查点结果、错误信息）
4. **修改 AppNavBar** — 添加"执行历史"导航入口
5. **修改 HomeView** — 配置卡片增加"查看执行历史"入口
6. **修改 ExecuteConfigModal** — 执行完成后展示结果摘要+下载按钮

### 3.6 关键设计决策

- **输出文件保留策略**：默认保留最近 50 次执行的输出文件，超过自动清理最旧的
- **同步执行**：当前执行是同步的（HTTP 请求阻塞直到完成），Phase 3 暂不改为异步，仅记录最终状态
- **执行 ID 格式**：8 位短 ID，便于 URL 和展示
- **版本关联**：执行记录通过 `config_version` 字段关联 Phase 2 的版本快照，实现"哪次执行用了哪个配置版本"的完整追溯

### 3.7 交付标准

- [ ] 执行记录持久化到 JSON 文件
- [ ] 执行记录包含 `config_version` 字段，关联配置版本
- [ ] 敏感信息（连接字符串等）在记录中脱敏
- [ ] 输出文件保留而非立即删除
- [ ] 执行历史列表页面可用
- [ ] 执行详情弹窗展示完整统计
- [ ] 历史输出文件可下载
- [ ] 0 个 type error，所有测试通过

---

## Phase 4：数据库输出

### 4.1 目标

支持将管道处理结果直接写入数据库（MySQL/PostgreSQL/SQLite），补齐"文件进→数据库出"的数据流闭环。

### 4.2 后端改动

#### 4.2.1 输出配置模型 — `src/pipeforge/config/models.py`

```python
class DatabaseOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["database"] = "database"
    connection_id: str = ""
    target_table: str = ""
    write_mode: Literal["replace", "append", "upsert"] = "replace"
    source_table: str = ""
    columns: list[ColumnMapping] = Field(default=[])
    create_table_if_not_exists: bool = True
    primary_key_columns: list[str] = Field(default=[])
    batch_size: int = Field(default=1000, ge=1, le=100000)
    connection_string: str = ""  # 由 _prepare_execution() 解析后写入，插件仅读取
```

修改 `OutputSpec.config` 联合类型：
```python
OutputConfig = Annotated[
    ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig,
    Field(discriminator="type")
]

class OutputSpec(BaseModel):
    plugin: Literal["excel", "csv", "database"] = "excel"
    config: OutputConfig = Field(default=ExcelOutputConfig())
```

#### 4.2.2 Wizard 层模型 — `configforge/models/wizard.py`

当前 `OutputTarget` 缺少 `DatabaseOutputConfig`，需补充：

```python
class OutputTarget(BaseModel):
    plugin: Literal["excel", "csv", "database"] = "excel"  # 增加 "database"
    config: Annotated[ExcelOutputConfig | CsvOutputConfig | DatabaseOutputConfig,
           Field(discriminator="type")]  # 增加 DatabaseOutputConfig
```

> **关键**：若遗漏此修改，API 层反序列化会失败——FastAPI 路由接收请求时无法识别 `type: "database"`。

#### 4.2.3 数据库输出插件 — `src/pipeforge/plugins/output/database.py`（新增）

```python
@register_plugin("database", "output")
class DatabaseOutputPlugin(OutputPlugin[DatabaseOutputConfig]):
    @classmethod
    def config_model(cls) -> type[DatabaseOutputConfig]:
        return DatabaseOutputConfig

    def execute(self, context: ExecutionContext, config: DatabaseOutputConfig) -> OutputStats:
        # 1. 从 context 获取源表数据
        source_df = context.get_table(config.source_table)

        # 2. 连接字符串已由 _prepare_execution() 解析并写入 config.connection_string
        conn_str = config.connection_string

        # 3. 列映射
        if config.columns:
            source_df = self._apply_column_mapping(source_df, config.columns)

        # 4. 写入目标数据库
        engine = create_engine(conn_str)
        with engine.connect() as conn:
            if config.write_mode == "replace":
                if config.create_table_if_not_exists:
                    source_df.to_sql(config.target_table, conn, if_exists="replace", index=False, chunksize=config.batch_size)
                else:
                    conn.execute(text(f'TRUNCATE TABLE "{config.target_table}"'))
                    source_df.to_sql(config.target_table, conn, if_exists="append", index=False, chunksize=config.batch_size)
            elif config.write_mode == "append":
                source_df.to_sql(config.target_table, conn, if_exists="append", index=False, chunksize=config.batch_size)
            elif config.write_mode == "upsert":
                self._upsert(conn, source_df, config)

        return OutputStats(rows_written=len(source_df), file_path=None, elapsed_ms=...)

    def _upsert(self, conn, df, config):
        """实现 upsert 逻辑

        注意：不同数据库的 upsert 语法差异较大，需分别实现：
        - MySQL: ON DUPLICATE KEY UPDATE
        - PostgreSQL: ON CONFLICT ... DO UPDATE
        - SQLite: INSERT OR REPLACE（注意：REPLACE 会先删后插，触发器行为不同）

        建议使用 SQLAlchemy 2.0 的 insert().on_conflict_do_update() 统一抽象。
        """
        ...

    def _apply_column_mapping(self, df, columns):
        """应用列映射：重命名列、选择列"""
        ...
```

关键设计决策：
- **插件不解析连接**：删除 `_resolve_connection` 方法，连接字符串由 `_prepare_execution()` 在插件外部解析后直接写入 `config.connection_string`，插件仅读取该字段。这遵循依赖方向：PipeForge 层不应依赖 ConfigForge 层
- 复用 `ConnectionStore` 获取连接信息，不重复存储密码
- `write_mode` 三种模式：replace（覆盖）、append（追加）、upsert（更新插入）
- `create_table_if_not_exists` 控制是否自动建表
- `primary_key_columns` 用于 upsert 模式的冲突检测
- `batch_size` 控制批量写入大小，避免内存溢出
- **upsert 跨数据库实现**：MySQL `ON DUPLICATE KEY`、PostgreSQL `ON CONFLICT`、SQLite `INSERT OR REPLACE` 语法完全不同，建议使用 SQLAlchemy 2.0 的 `insert().on_conflict_do_update()` 统一抽象

#### 4.2.4 连接解析 — `configforge/core/pipeline.py`

在 `_prepare_execution()` 中添加数据库输出连接解析：

```python
# 已有数据库输入解析（第173-184行），参考同样模式
if out_spec.plugin == "database":
    db_config = out_spec.config
    if isinstance(db_config, dict):
        db_config = DatabaseOutputConfig(**db_config)
    conn = conn_store.get_with_plaintext_password(db_config.connection_id)
    db_config.connection_string = build_connection_string(conn)  # 解析后写入 config
```

#### 4.2.5 YAML 序列化 — `configforge/services/yaml_builder.py`

在输出配置序列化中添加数据库输出处理：

```python
if output_config.get("type") == "database":
    entry = {
        "plugin": "database",
        "connection_id": output_config["connection_id"],
        "target_table": output_config["target_table"],
        "write_mode": output_config["write_mode"],
        "source_table": output_config["source_table"],
    }
    if output_config.get("columns"):
        entry["columns"] = output_config["columns"]
    if output_config.get("primary_key_columns"):
        entry["primary_key_columns"] = output_config["primary_key_columns"]
```

### 4.3 前端改动

#### 4.3.1 类型定义 — `configforge-web/src/types/wizard.ts`

```ts
export interface DatabaseOutputConfig {
  type: 'database'
  connection_id: string
  target_table: string
  write_mode: 'replace' | 'append' | 'upsert'
  source_table: string
  columns: ColumnMappingItem[]
  create_table_if_not_exists: boolean
  primary_key_columns: string[]
  batch_size: number
}
```

#### 4.3.2 OutputConfigTab — `configforge-web/src/components/step3/OutputConfigTab.vue`

1. 激活 Database 类型选择卡片（当前灰色不可点击）
2. 添加数据库输出配置表单：
   - 连接选择（NSelect，从 ConnectionManager 获取连接列表）
   - 目标表名（NInput）
   - 写入模式（NSelect：覆盖/追加/更新插入）
   - 列映射（复用现有 ColumnMapping 组件）
   - 高级选项折叠区：自动建表开关、主键列、批量大小

3. 连接列表获取：调用 `/api/connections` API

### 4.4 测试计划

| 测试类型 | 范围 | 用例数 |
|----------|------|--------|
| 后端单元测试 | DatabaseOutputPlugin 三种写入模式 | 3 |
| 后端单元测试 | upsert 跨数据库语法适配 | 3（MySQL/PG/SQLite） |
| 后端集成测试 | 完整管道：CSV输入→SQL处理→数据库输出 | 2 |
| API E2E 测试 | 创建配置+数据库输出 → 执行 → 验证目标表数据 | 2 |
| 前端组件测试 | OutputConfigTab 数据库配置表单 | 3 |
| 前端 E2E 测试 | 完整向导流程含数据库输出 | 1 |

### 4.5 交付标准

- [ ] DatabaseOutputPlugin 三种写入模式全部实现
- [ ] 插件不包含 `_resolve_connection`，连接字符串由 `_prepare_execution()` 解析
- [ ] Wizard 层 `OutputTarget` 包含 `DatabaseOutputConfig`
- [ ] 复用 ConnectionStore 连接管理
- [ ] YAML 序列化/反序列化正确
- [ ] 前端 OutputConfigTab 数据库配置表单可用
- [ ] 列映射与 Excel/CSV 输出一致
- [ ] 0 个 type error，所有测试通过

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Pydantic discriminated union 反序列化兼容性 | Phase 1 | 先写单元测试验证 Union 类型序列化/反序列化 |
| custom_sql 检查点的 SQL 注入 | Phase 1 | 复用 `_has_ddl()` + `safe_identifier()` 防护 |
| enum_check 枚举值超 SQLite 参数上限 | Phase 1 | 超过 900 个枚举值时拒绝执行，给出明确提示 |
| 版本对比 deepdiff 性能 | Phase 2 | 限制对比深度 + 缓存 diff 结果 |
| deepdiff 新增依赖 | Phase 2 | 在 requirements.txt / pyproject.toml 中显式声明 |
| 执行历史输出文件磁盘占用 | Phase 3 | 保留最近 50 次 + 定期清理策略 |
| 数据库输出大表写入性能 | Phase 4 | `batch_size` 参数控制 + 可选的流式写入 |
| 数据库输出列类型映射 | Phase 4 | SQLite → MySQL/PG 类型映射表，不支持的类型降级为 TEXT |
| upsert 跨数据库语法差异 | Phase 4 | 使用 SQLAlchemy 2.0 的 `insert().on_conflict_do_update()` 统一抽象 |

---

## v1.1 修订记录

| 修订项 | 原内容 | 修订后 | 依据 |
|--------|--------|--------|------|
| 阶段顺序 | 1→2(DB输出)→3(执行历史)→4(版本管理) | 1→2(版本管理)→3(执行历史)→4(DB输出) | 审查建议 #4：执行记录需关联 config_version，版本管理必须先于执行历史 |
| SQLite 标识符 | `[]` 包裹 | `""` 包裹 | 审查问题 #1：与现有代码库风格不一致 |
| DB 输出插件 `_resolve_connection` | 插件内含 `_resolve_connection` 方法 | 删除，连接字符串由 `_prepare_execution()` 解析后写入 `config.connection_string` | 审查问题 #2：PipeForge 层不应依赖 ConfigForge 层 |
| Wizard 层模型 | 遗漏 `DatabaseOutputConfig` | 补充到 `OutputTarget` | 审查问题 #3：API 层反序列化会失败 |
| CustomSqlRule | `expected_column` + `max_value` + 仅 `<=` | `result_column` + `comparison`(6种运算符) + `expected_value` | 审查建议 #6：校验语义过窄 |
| 唯一性检查 | 无 NULL 排除 | 加 `WHERE "{column}" IS NOT NULL` | 审查建议 #7：NULL 导致误判 |
| 回滚语义 | 未明确 | 追加式（方案 B），回滚创建新版本 | 审查建议 #8：线性历史、可逆 |
| ExecutionRecord.status | `running`/`success`/`failed` | 仅 `success`/`failed`，`running` 预留 | 审查建议 #5：同步执行下 running 无意义 |
| ExecutionRecord | 无 `config_version` | 增加 `config_version: int \| None = None` | 审查问题 #16：执行记录需关联版本 |
| 新 Rule 模型 | 无 `extra="forbid"` | 添加 `model_config = ConfigDict(extra="forbid")` | 审查问题 #9：与近期修复不一致 |
| deepdiff | 未声明依赖 | 显式声明为新增 Python 依赖 | 审查问题 #18 |
| enum_check | 无参数限制说明 | 超过 900 个枚举值时拒绝执行 | 审查问题 #12：SQLite 999 参数上限 |
| 执行记录敏感数据 | 未提及脱敏 | 连接字符串等敏感信息需脱敏 | 审查问题 #17 |
| CheckpointSection | 单组件承载全部模板 | 建议拆分子组件 | 审查问题 #10：预计超 400 行 |
| 列选项获取 | 未考虑 dry_run 前场景 | 加提示"请先执行预览"，允许手动输入 | 审查问题 #14 |
| upsert 跨数据库 | 未提及语法差异 | 明确 MySQL/PG/SQLite 语法差异，建议 SQLAlchemy 2.0 统一抽象 | 审查问题 #15 |
