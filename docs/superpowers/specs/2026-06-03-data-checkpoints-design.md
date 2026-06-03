# 数据检查点 (Data Checkpoints) — 设计文档 v0.2

**日期**: 2026-06-03  
**状态**: 已确认 (v0.1 审核后修订)  
**审核**: [2026-06-03-data-checkpoints-review.md](../reviews/2026-06-03-data-checkpoints-review.md)

---

## 1. 目标

在数据处理管道的任意位置插入检查规则，执行时自动验证数据质量。目标是保证最终输出的稳定性和正确性。

---

## 2. 核心原则

- **确定性执行**: 所有检查规则编译为具体的、可重复执行的类型，不保留"运行时 AI 判断"的模糊规则
- **自然语言是输入方式，不是规则类型**: 用户用自然语言描述规则 → AI 翻译为具体规则类型 → 存储+执行的永远只有具体类型
- **可扩展**: 新增规则类型只需加一个 Pydantic 模型 + 一个 executor 函数
- **每条规则独立控制严重度**: `on_failure` 在规则级别，而非步骤级别

---

## 3. 数据模型

### 3.1 检查规则（PipeForge / YAML 层）

```python
class RowCountRule(BaseModel):
    type: Literal["row_count"] = "row_count"
    table: str = ""                    # 检查哪张表，空串=当前步骤输出表
    min: int | None = None
    max: int | None = None
    on_failure: Literal["block", "warn"] = "block"

class FieldNotNullRule(BaseModel):
    type: Literal["field_not_null"] = "field_not_null"
    table: str = ""
    field: str
    min_rate: float                    # 非空率下限，0.0-1.0
    on_failure: Literal["block", "warn"] = "block"

class FieldRangeRule(BaseModel):
    type: Literal["field_range"] = "field_range"
    table: str = ""
    field: str
    min: float | None = None
    max: float | None = None
    on_failure: Literal["block", "warn"] = "block"

class RowCountRatioRule(BaseModel):
    type: Literal["row_count_ratio"] = "row_count_ratio"
    source_table: str                  # 参照表（如输入表）
    target_table: str                  # 当前表（如输出表）
    min_ratio: float | None = None
    max_ratio: float | None = None
    on_failure: Literal["block", "warn"] = "block"

# Discriminated union — 扩展时追加新类型
CheckRule = Annotated[
    RowCountRule | FieldNotNullRule | FieldRangeRule | RowCountRatioRule,
    Field(discriminator="type")
]
```

### 3.2 检查点挂载位置

**检查点作为 `ProcessorSpec` 的一级字段**（非嵌套在 `config` 中），因为 `ProcessorSpec` 使用 `extra="forbid"`，且 `config` 是 discriminated union：

```python
class ProcessorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    plugin: str
    input_tables: list[str] = []
    output_tables: list[str] = []
    config: Annotated[SqlProcessorConfig | PythonProcessorConfig, Field(discriminator="type")]
    # ↓ 新增
    checkpoints: list[CheckRule] = []

class SceneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene: SceneMeta
    inputs: list[InputSpec] = []
    processors: list[ProcessorSpec] = []
    output: OutputSpec | None = None
```

**ConfigForge Wizard 层同样作为一级字段**：

```python
class ProcessorConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str = ""
    plugin: Literal["sql", "python"] = "sql"
    sql: str = Field(default="", alias="sql")
    script: str = Field(default="", alias="script")
    input_tables: list[str] = Field(default=[], alias="inputTables")
    output_tables: list[str] = Field(default=[], alias="outputTables")
    # ↓ 新增
    checkpoints: list[CheckRule] = Field(default=[])
```

### 3.3 检查结果

```python
class CheckResult(BaseModel):
    rule_type: str                     # 规则类型
    passed: bool
    message: str                       # 通过/失败的描述
    on_failure: Literal["block", "warn"]
    checked_at: str                    # ISO 8601 时间戳
```

检查结果追加到 `context` 中，前端可在预览/执行结果中展示。

### 3.4 规则来源（前端专用，不持久化到 YAML）

```python
class RuleSource(BaseModel):
    source: Literal["template", "natural_language"] = "template"
    natural_language_text: str | None = None
```

### 3.5 前端类型（对应 TypeScript）

```typescript
type CheckRule =
  | { type: "row_count"; table: string; min?: number; max?: number; on_failure: "block" | "warn" }
  | { type: "field_not_null"; table: string; field: string; min_rate: number; on_failure: "block" | "warn" }
  | { type: "field_range"; table: string; field: string; min?: number; max?: number; on_failure: "block" | "warn" }
  | { type: "row_count_ratio"; source_table: string; target_table: string; min_ratio?: number; max_ratio?: number; on_failure: "block" | "warn" }

interface CheckResult {
  rule_type: string
  passed: boolean
  message: string
  on_failure: "block" | "warn"
  checked_at: string
}

interface RuleSource {
  source: "template" | "natural_language"
  natural_language_text?: string
}
```

---

## 4. 架构

### 4.1 数据模型层次

```
┌─ PipeForge 层（YAML 执行）────────────────────────────┐
│  ProcessorSpec.checkpoints: list[CheckRule] = []      │
│  （检查点作为步骤的一级属性）                            │
└───────────────────────────────────────────────────────┘
          ↕ YAML 序列化/反序列化
┌─ ConfigForge 层（Wizard API）─────────────────────────┐
│  ProcessorConfig.checkpoints: list[CheckRule] = []    │
│  （与 PipeForge 同构）                                  │
└───────────────────────────────────────────────────────┘
          ↕ API 序列化
┌─ 前端层（TypeScript）─────────────────────────────────┐
│  ProcessorStep 各分支新增 checkpoints                  │
│  serialization.ts 同步映射                             │
└───────────────────────────────────────────────────────┘
```

### 4.2 执行流程

**共享执行模块**（`pipeforge/core/checkpoints.py`），同时被 `engine.py` 和 `pipeline.py` 调用：

```python
def execute_checks(checkpoints: list[CheckRule], db: SQLiteManager) -> list[CheckResult]:
    results = []
    for rule in checkpoints:
        executor = _CHECK_EXECUTORS[rule.type]
        passed, message = executor(rule, db)
        result = CheckResult(
            rule_type=rule.type,
            passed=passed,
            message=message,
            on_failure=rule.on_failure,
            checked_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        results.append(result)
        if not passed and rule.on_failure == "block":
            raise CheckpointError(result)
    return results
```

**PipeForge engine.py** — 每个步骤执行后调用：

```python
for proc_spec in sorted_processors:
    stats = self._execute_processor(proc_spec, context)
    context.result.processors.append(stats)

    # 步骤执行后，下一步骤前，执行检查点
    if proc_spec.checkpoints:
        check_results = execute_checks(proc_spec.checkpoints, context.db)
        context.result.checks.append(check_results)
```

**ConfigForge pipeline.py** — dry-run 路径同样调用：

```python
# 现有：直接执行 SQL
result = context.db.execute(proc.sql)

# 新增：执行检查点
if proc.checkpoints:
    check_results = execute_checks(proc.checkpoints, context.db)
```

### 4.3 执行器注册

```python
# pipeforge/core/checkpoints.py

from pipeforge.config.models import CheckRule
from pipeforge.core.sqlite import SQLiteManager

_CHECK_EXECUTORS: dict[str, Callable] = {}

def register_check(type: str):
    """注册检查规则执行器。签名: (rule: CheckRule, db: SQLiteManager) -> (bool, str)"""
    def decorator(fn):
        _CHECK_EXECUTORS[type] = fn
        return fn
    return decorator

@register_check("row_count")
def _check_row_count(rule: RowCountRule, db: SQLiteManager) -> tuple[bool, str]:
    count = db.query(f'SELECT COUNT(*) FROM "{rule.table}"')[0][0]
    if rule.min is not None and count < rule.min:
        return False, f"行数 {count} < 最小值 {rule.min}"
    if rule.max is not None and count > rule.max:
        return False, f"行数 {count} > 最大值 {rule.max}"
    return True, f"行数 {count} 在范围内"
```

### 4.4 AI 翻译自然语言（v0.2）

```python
# /api/ai/translate-checkpoint
context = {
    "user_input": "结果表至少要有100行",
    "available_tables": ["test_data", "result"],
    "current_output_table": "result",
    "columns": {"result": ["姓名", "部门", "工资"]},
    "input_tables": ["test_data"],
    "available_rule_types": ["row_count", "field_not_null", "field_range", "row_count_ratio"],
}
# LLM prompt 包含完整上下文，返回具体 CheckRule JSON
```

---

## 5. UI 设计（v0.2）

在 ProcessorCard 底部新增可折叠区域，默认折叠：

```
┌─ ProcessorCard ─────────────────────────────────────┐
│  步骤名称 [xxxx]  输入表 [xxxx]         [SQL] [删除] │
│  SQL 编辑器 ...                                      │
│  ────────────────────────────────────────────────── │
│  ▸ 数据检查 (1 条规则)                    [展开/折叠] │
└─────────────────────────────────────────────────────┘
```

展开后每条规则独立控制阻断/警告：
```
  ┌─ 规则 1 ──────────────────────────────────────────┐
  │  类型: [行数范围 ▾]  严重度: [阻断 ▾]               │
  │  检查表: result1                                   │
  │  最小行数: 1000   最大行数: (不限制)                 │
  │  [删除此规则]                                      │
  └───────────────────────────────────────────────────┘
  [+ 添加规则]
```

---

## 6. v0.1 范围（收窄后）

审查建议收窄，理由：
- `row_count_ratio` 需要行数快照机制（源表可能在执行中被修改），复杂度不适合 v0.1
- 先做最简单的 `row_count` 验证端到端流程，确认架构可行

| 包含 (v0.1) | 排除 (v0.2+) |
|-------------|--------------|
| `CheckRule` 完整模型定义（4 种类型） | `row_count_ratio` 执行器（需快照） |
| `row_count` 规则 + 执行器 | `field_not_null`、`field_range` 执行器 |
| PipeForge `ProcessorSpec.checkpoints` | AI 翻译端点 |
| ConfigForge `ProcessorConfig.checkpoints` | 前端 UI（CheckpointSection 组件） |
| 共享执行模块 `checkpoints.py` | 前端测试 |
| engine.py + pipeline.py 调用共享模块 | 自然语言输入 |
| YAML 序列化/反序列化 | OutputConfigTab 检查点 |
| 后端测试 | 检查失败的 AI 诊断 |

---

## 7. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/pipeforge/config/models.py` | 修改 | 新增 CheckRule 等 4 个模型 + CheckResult |
| `src/pipeforge/core/checkpoints.py` | 新建 | 执行器注册 + execute_checks 共享函数 + row_count 执行器 |
| `src/pipeforge/core/engine.py` | 修改 | 步骤执行后调用 execute_checks |
| `configforge/models/wizard.py` | 修改 | ProcessorConfig 新增 checkpoints 字段 |
| `configforge/core/pipeline.py` | 修改 | dry-run 路径调用 execute_checks |
| `configforge/generators/yaml.py` | 修改 | YAML 序列化包含 checkpoints |
| `configforge-web/src/types/wizard.ts` | 修改 | 新增 CheckRule、CheckResult、RuleSource 类型 |
| `configforge-web/src/stores/wizard.ts` | 修改 | addProcessor/setProcessors 初始化 checkpoints |
| `configforge-web/src/utils/serialization.ts` | 修改 | SnakeState + stateToSnakeCase 映射 checkpoints |
| `configforge-web/src/components/step3/ProcessorCard.vue` | 修改 | 预留检查区域（v0.1 仅展示静态标签，UI v0.2） |
| `configforge-web/src/components/step3/SqlEditorTab.vue` | 修改 | pickProcessor 初始化 checkpoints |
| `configforge-web/src/components/step4/ExportActions.vue` | 修改 | YAML 导出包含检查点 |
| `configforge-web/src/views/ConfigWizardView.vue` | 修改 | AI 编排确认时保留 checkpoints |
| `tests/test_checkpoints.py` | 新建 | 检查点单元测试 |
| `configforge/tests/test_pipeline.py` | 修改 | 检查点集成测试 |

---

## 8. 验证方式

1. 定义 `row_count` 规则（min=1000）→ 跑管道 → 表行数不足时触发 CheckpointError
2. 规则 `on_failure: "warn"` → 验证不阻断，结果中包含警告
3. 规则 `on_failure: "block"` → 验证阻断，后续步骤不执行
4. YAML 序列化/反序列化 round-trip（检查点字段不丢失）
5. 后端全量测试通过（`uv run pytest`）
6. 前端全量测试通过（`npx vitest run`）
7. TypeScript 类型检查通过（`npx vue-tsc --noEmit`）
