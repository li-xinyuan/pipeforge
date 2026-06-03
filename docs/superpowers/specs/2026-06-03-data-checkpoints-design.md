# 数据检查点 (Data Checkpoints) — 设计文档 v0.3

**日期**: 2026-06-03  
**状态**: 已确认 (两轮审核后修订)  
**审核**: [2026-06-03-data-checkpoints-review.md](../reviews/2026-06-03-data-checkpoints-review.md)

---

## 1. 目标

在数据处理管道的任意位置插入检查规则，执行时自动验证数据质量。目标是保证最终输出的稳定性和正确性。

---

## 2. 核心原则

- **确定性执行**: 所有检查规则编译为具体的、可重复执行的类型，不保留"运行时 AI 判断"的模糊规则
- **自然语言是输入方式，不是规则类型**: 用户用自然语言描述规则 → AI 翻译为具体规则类型 → 存储+执行的永远只有具体类型
- **可扩展**: 新增规则类型只需加一个 Pydantic 模型 + 一个 executor 函数，然后追加到 `CheckRule` union
- **每条规则独立控制严重度**: `on_failure` 在规则级别，而非步骤级别
- **block 规则收集全部结果后统一中断**: 一次执行中能看到所有失败规则，而非修一个才能看到下一个

---

## 3. 数据模型

### 3.1 检查规则（v0.1 仅 RowCountRule）

```python
# === v0.1：仅 RowCountRule ===

class RowCountRule(BaseModel):
    type: Literal["row_count"] = "row_count"
    table: str = ""                    # 空串=当前步骤输出表（由 execute_checks 的 default_table 解析）
    min: int | None = None
    max: int | None = None
    on_failure: Literal["block", "warn"] = "block"

CheckRule = RowCountRule

# v0.1 的 CheckRule union 只含 RowCountRule。
# 扩展方式：新增模型后追加到 Union，如：
# CheckRule = Annotated[RowCountRule | FieldNotNullRule | ..., Field(discriminator="type")]

# === v0.2+：追加以下模型 ===

# class FieldNotNullRule(BaseModel):
#     type: Literal["field_not_null"] = "field_not_null"
#     table: str = ""
#     field: str
#     min_rate: float                  # 非空率下限，0.0-1.0
#     on_failure: Literal["block", "warn"] = "block"

# class FieldRangeRule(BaseModel):
#     type: Literal["field_range"] = "field_range"
#     table: str = ""
#     field: str
#     min: float | None = None
#     max: float | None = None
#     on_failure: Literal["block", "warn"] = "block"

# class RowCountRatioRule(BaseModel):
#     type: Literal["row_count_ratio"] = "row_count_ratio"
#     source_table: str
#     target_table: str
#     min_ratio: float | None = None
#     max_ratio: float | None = None
#     on_failure: Literal["block", "warn"] = "block"
```

### 3.2 检查点挂载位置

检查点作为 `ProcessorSpec` 的一级字段（非嵌套在 `config` 中），因为 `ProcessorSpec` 使用 `extra="forbid"`，且 `config` 是 discriminated union：

```python
class ProcessorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    plugin: str
    input_tables: list[str] = []
    output_tables: list[str] = []
    config: Annotated[SqlProcessorConfig | PythonProcessorConfig, Field(discriminator="type")]
    checkpoints: list[CheckRule] = []  # ← 新增一级字段

class SceneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene: SceneMeta
    inputs: list[InputSpec] = []
    processors: list[ProcessorSpec] = []
    output: OutputSpec | None = None
```

**ConfigForge Wizard 层** `ProcessorConfig` 同样作为一级字段，与 PipeForge 同构：

```python
class ProcessorConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str = ""
    plugin: Literal["sql", "python"] = "sql"
    sql: str = Field(default="", alias="sql")
    script: str = Field(default="", alias="script")
    input_tables: list[str] = Field(default=[], alias="inputTables")
    output_tables: list[str] = Field(default=[], alias="outputTables")
    checkpoints: list[CheckRule] = Field(default=[])  # ← 新增
```

### 3.3 检查结果

```python
class CheckResult(BaseModel):
    type: str                          # 规则类型
    passed: bool
    message: str
    on_failure: Literal["block", "warn"]
    checked_at: str                    # ISO 8601
```

检查结果追加到 `context.result.checks` 中，由 `ExecutionResult`（`context.py`）承载：

```python
# pipeforge/core/context.py
class ExecutionResult:
    inputs: list[InputStats] = []
    processors: list[ProcessorStats] = []
    output: OutputStats | None = None
    checks: list[CheckResult] = []     # ← 新增
```

### 3.4 自定义异常

```python
# pipeforge/config/exceptions.py 或 pipeforge/core/checkpoints.py
class CheckpointError(Exception):
    """检查点验证失败。results 包含所有规则的执行结果。"""
    def __init__(self, results: list[CheckResult]):
        self.results = results
        failed = [r for r in results if not r.passed and r.on_failure == "block"]
        msg = "; ".join(r.message for r in failed)
        super().__init__(f"检查点验证失败: {msg}")
```

### 3.5 规则来源（前端专用）

```python
class RuleSource(BaseModel):
    source: Literal["template", "natural_language"] = "template"
    natural_language_text: str | None = None
```

### 3.6 前端类型

```typescript
// v0.1
type CheckRule = {
  type: "row_count"; table: string; min?: number; max?: number; on_failure: "block" | "warn"
}

interface CheckResult {
  type: string; passed: boolean; message: string; on_failure: "block" | "warn"; checked_at: string
}

interface RuleSource {
  source: "template" | "natural_language"; natural_language_text?: string
}
```

---

## 4. 架构

### 4.1 数据模型层次

```
┌─ PipeForge 层（YAML 执行）────────────────────────────┐
│  ProcessorSpec.checkpoints: list[CheckRule] = []      │
│  （一级字段，非嵌套在 config 中）                        │
└───────────────────────────────────────────────────────┘
          ↕ YAML 序列化/反序列化
┌─ ConfigForge 层（Wizard API）─────────────────────────┐
│  ProcessorConfig.checkpoints: list[CheckRule] = []    │
│  （与 PipeForge 同构）                                  │
└───────────────────────────────────────────────────────┘
          ↕ API 序列化
┌─ 前端层（TypeScript）─────────────────────────────────┐
│  ProcessorStep 新增 checkpoints                        │
│  serialization.ts 同步映射                             │
└───────────────────────────────────────────────────────┘
```

**关键发现**：ConfigForge 的 `pipeline.py` 实际通过构建 YAML → 调用 `PipelineEngine` 来执行（`engine = PipelineEngine(yaml_path); engine.execute_dry_run(...)`）。因此检查点只需在 PipeForge `engine.py` 中实现，ConfigForge 自动获得检查点能力，`pipeline.py` 无需额外修改。

### 4.2 执行流程

**共享执行模块**（`pipeforge/core/checkpoints.py`），被 `engine.py` 调用。关键行为：先收集全部结果，再统一判断是否需要阻断——确保用户一次看到所有失败规则。

```python
def execute_checks(
    checkpoints: list[CheckRule],
    db: SQLiteManager,
    default_table: str = "",         # 当前步骤的第一张输出表
) -> list[CheckResult]:
    """执行所有检查规则。block 失败时会收集全部结果后统一抛出 CheckpointError。"""
    results = []
    has_block_failure = False
    for rule in checkpoints:
        table = rule.table or default_table
        executor = _CHECK_EXECUTORS[rule.type]
        passed, message = executor(table, rule, db)
        result = CheckResult(
            type=rule.type, passed=passed, message=message,
            on_failure=rule.on_failure,
            checked_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        results.append(result)
        if not passed and rule.on_failure == "block":
            has_block_failure = True
    if has_block_failure:
        raise CheckpointError(results)   # 传入全部结果
    return results
```

**PipeForge engine.py** — 每个步骤执行后调用：

```python
for proc_spec in sorted_processors:
    stats = self._execute_processor(proc_spec, context)
    context.result.processors.append(stats)

    if proc_spec.checkpoints:
        default_table = proc_spec.output_tables[0] if proc_spec.output_tables else ""
        check_results = execute_checks(proc_spec.checkpoints, context.db, default_table)
        context.result.checks.extend(check_results)
```

### 4.3 执行器

```python
# pipeforge/core/checkpoints.py

_CHECK_EXECUTORS: dict[str, Callable] = {}

def register_check(type: str):
    """注册检查规则执行器。签名: (table: str, rule: CheckRule, db: SQLiteManager) -> (bool, str)"""
    def decorator(fn):
        _CHECK_EXECUTORS[type] = fn
        return fn
    return decorator

@register_check("row_count")
def _check_row_count(table: str, rule: RowCountRule, db: SQLiteManager) -> tuple[bool, str]:
    count = db.query(f'SELECT COUNT(*) FROM "{table}"')[0][0]
    if rule.min is not None and count < rule.min:
        return False, f"表 {table} 行数 {count} < 最小值 {rule.min}"
    if rule.max is not None and count > rule.max:
        return False, f"表 {table} 行数 {count} > 最大值 {rule.max}"
    return True, f"表 {table} 行数 {count} 在范围内"
```

### 4.4 YAML 序列化格式

```yaml
processors:
  - name: step1
    plugin: sql
    input_tables: [test_data]
    output_tables: [result]
    config:
      type: sql
      sql: CREATE TABLE result AS SELECT * FROM test_data WHERE amount > 0
    checkpoints:                        # ← ProcessorSpec 一级字段
      - type: row_count
        table: result
        min: 100
        on_failure: block
```

### 4.5 AI 翻译自然语言（v0.2）

```python
# /api/ai/translate-checkpoint
context = {
    "user_input": "结果表至少要有100行",
    "available_tables": ["test_data", "result"],
    "current_output_table": "result",
    "columns": {"result": ["姓名", "部门", "工资"]},
    "input_tables": ["test_data"],
    "available_rule_types": ["row_count"],
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

展开后：
```
  ┌─ 规则 1 ──────────────────────────────────────────┐
  │  类型: [行数范围 ▾]  处理方式: [阻断 ▾]             │
  │  检查表: result1                                   │
  │  最小行数: 1000   最大行数: (不限制)                 │
  │  [删除此规则]                                      │
  └───────────────────────────────────────────────────┘
  [+ 添加规则]
```

---

## 6. v0.1 范围

| 包含 | 排除 (v0.2+) |
|------|-------------|
| `RowCountRule` + `CheckRule = RowCountRule` | `field_not_null`、`field_range`、`row_count_ratio` |
| `CheckResult` + `CheckpointError` | AI 翻译端点 |
| `ProcessorSpec.checkpoints` | 前端 UI（CheckpointSection 组件） |
| `ProcessorConfig.checkpoints` | 自然语言输入 |
| `context.py` `ExecutionResult.checks` | OutputConfigTab 检查点 |
| `checkpoints.py` 共享模块 + `row_count` 执行器 | 前端测试 |
| `engine.py` 集成 | |
| YAML 序列化 | |
| 前端类型 + Store + serialization 映射 | |
| 后端单元测试 | |

---

## 7. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/pipeforge/config/models.py` | 修改 | 新增 `RowCountRule`、`CheckRule`、`CheckResult` |
| `src/pipeforge/config/exceptions.py` | 修改 | 新增 `CheckpointError` |
| `src/pipeforge/core/checkpoints.py` | 新建 | 执行器注册、`execute_checks()`、`row_count` 执行器 |
| `src/pipeforge/core/engine.py` | 修改 | 步骤执行后调用 `execute_checks` |
| `src/pipeforge/core/context.py` | 修改 | `ExecutionResult` 新增 `checks` 字段 |
| `configforge/models/wizard.py` | 修改 | `ProcessorConfig` 新增 `checkpoints` |
| `configforge/services/yaml_builder.py` | 修改 | YAML 序列化包含 `checkpoints` |
| `configforge-web/src/types/wizard.ts` | 修改 | 新增 `CheckRule`、`CheckResult`、`RuleSource` 类型 |
| `configforge-web/src/stores/wizard.ts` | 修改 | `addProcessor`/`setProcessors` 初始化 `checkpoints` |
| `configforge-web/src/utils/serialization.ts` | 修改 | `SnakeState` + `stateToSnakeCase` 映射 |
| `configforge-web/src/components/step3/ProcessorCard.vue` | 修改 | 预留检查区域（v0.1 仅静态展示，UI v0.2） |
| `configforge-web/src/components/step3/SqlEditorTab.vue` | 修改 | `pickProcessor` 初始化 `checkpoints` |
| `configforge-web/src/components/step3/PythonProcessorContent.vue` | 修改 | 同理初始化 `checkpoints`（更新 emit 签名） |
| `configforge-web/src/components/step4/ExportActions.vue` | 修改 | YAML 导出包含 `checkpoints` |
| `configforge-web/src/views/ConfigWizardView.vue` | 修改 | AI 编排确认时保留 `checkpoints` |
| `tests/test_checkpoints.py` | 新建 | 检查点单元测试（`row_count` 执行器 + `execute_checks`） |
| `configforge/tests/test_pipeline.py` | 修改 | 检查点通过 YAML→引擎的集成测试 |

**注**：`configforge/core/pipeline.py` 无需修改 — ConfigForge 的 dry_run 通过构建 YAML → `PipelineEngine` 执行，自动获得检查点能力。

---

## 8. 验证方式

1. `row_count` 规则 min=1000 → 表行数不足 → `CheckpointError` 阻断
2. `on_failure: "warn"` → 验证不阻断，结果中包含警告
3. 多条 `block` 规则同时失败 → `CheckpointError` 包含所有失败结果（非逐条中断）
4. YAML 序列化/反序列化 round-trip（`checkpoints` 字段不丢失）
5. 后端全量测试通过（`uv run pytest`）
6. 前端全量测试通过（`npx vitest run`）
7. TypeScript 类型检查通过（`npx vue-tsc --noEmit`）
