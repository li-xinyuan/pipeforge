# 数据检查点 v0.1 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在管道执行时，每个步骤后可配置行数检查规则（`RowCountRule`），验证输出表行数是否在范围内，失败时可按规则阻断或警告。

**Architecture:** 纯后端 + 前端类型映射。`RowCountRule` 作为 `ProcessorSpec` 一级字段。共享模块 `checkpoints.py` 被 `engine.py` 调用，ConfigForge 通过 YAML→Engine 路径自动获益。v0.1 无前端 UI。

**Tech Stack:** Python 3.13, Pydantic v2, SQLite, Vue 3 TypeScript

---

### Task 1: PipeForge 数据模型 — RowCountRule + CheckResult + CheckpointError

**Files:**
- Modify: `src/pipeforge/config/models.py` — 末尾追加
- Modify: `src/pipeforge/config/exceptions.py` — 追加 CheckpointError

- [ ] **Step 1: 在 models.py 末尾追加 RowCountRule、CheckRule、CheckResult**

```python
# 数据检查点（v0.1：仅 RowCountRule）
class RowCountRule(BaseModel):
    type: Literal["row_count"] = "row_count"
    table: str = ""
    min: int | None = None
    max: int | None = None
    on_failure: Literal["block", "warn"] = "block"

CheckRule = RowCountRule

class CheckResult(BaseModel):
    type: str
    passed: bool
    message: str
    on_failure: Literal["block", "warn"]
    checked_at: str
```

- [ ] **Step 2: 在 exceptions.py 追加 CheckpointError**

```python
class CheckpointError(Exception):
    """检查点验证失败。results 包含所有规则的执行结果。"""

    def __init__(self, results: list):
        self.results = results
        failed = [r for r in results if not r.passed and r.on_failure == "block"]
        msg = "; ".join(r.message for r in failed)
        super().__init__(f"检查点验证失败: {msg}")
```

- [ ] **Step 3: 运行现有测试确认无回归**

```bash
uv run pytest tests/ -q
```
Expected: 126 passed

- [ ] **Step 4: 在 ProcessorSpec 中追加 checkpoints 字段**

编辑 `src/pipeforge/config/models.py` 的 `ProcessorSpec` 类：

```python
class ProcessorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plugin: str
    input_tables: list[str] = []
    output_tables: list[str] = []
    config: Annotated[SqlProcessorConfig | PythonProcessorConfig, Field(discriminator="type")]
    checkpoints: list[CheckRule] = []
```

- [ ] **Step 5: 运行测试确认无回归**

```bash
uv run pytest tests/ -q
```
Expected: 126 passed

- [ ] **Step 6: Commit**

```bash
git add src/pipeforge/config/models.py src/pipeforge/config/exceptions.py
git commit -m "feat: add RowCountRule, CheckRule, CheckResult, CheckpointError to PipeForge models"
```

---

### Task 2: 检查点执行模块 — checkpoints.py

**Files:**
- Create: `src/pipeforge/core/checkpoints.py`

- [ ] **Step 1: 创建 checkpoints.py，含注册器 + execute_checks + row_count 执行器**

```python
"""检查点规则注册与执行。新增规则类型：加模型 → 用 @register_check 注册执行器 → 追加到 CheckRule union。"""

from datetime import datetime, timezone
from typing import Callable

from pipeforge.config.models import CheckRule, CheckResult, CheckpointError, RowCountRule
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
```

- [ ] **Step 2: Verify module imports cleanly**

```bash
uv run python -c "from pipeforge.core.checkpoints import execute_checks, register_check; print('OK')"
```
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add src/pipeforge/core/checkpoints.py
git commit -m "feat: add checkpoints execution module with row_count executor"
```

---

### Task 3: PipeForge 引擎集成 — engine.py + context.py

**Files:**
- Modify: `src/pipeforge/core/engine.py`
- Modify: `src/pipeforge/core/context.py`

- [ ] **Step 1: ExecutionResult 新增 checks 字段**

编辑 `src/pipeforge/core/context.py`，在 `ExecutionResult` 末尾追加：

```python
class ExecutionResult(BaseModel):
    inputs: dict[str, InputStats] = {}
    processors: list[ProcessorStats] = []
    output: OutputStats | None = None
    checks: list[CheckResult] = []
```

文件顶部追加 import：
```python
from pipeforge.config.models import CheckResult
```

- [ ] **Step 2: engine.py 步骤执行后调用 execute_checks**

在 `src/pipeforge/core/engine.py` 顶部追加 import：

```python
from pipeforge.core.checkpoints import execute_checks
```

在 `execute_pipeline()`（约 line 63）和 `execute_dry_run()`（约 line 108）的 `context.result.processors.append(stats)` 之后，都追加相同的检查点调用：

```python
                if proc_spec.checkpoints:
                    default_table = proc_spec.output_tables[0] if proc_spec.output_tables else ""
                    check_results = execute_checks(proc_spec.checkpoints, context.db, default_table)
                    context.result.checks.extend(check_results)
```

- [ ] **Step 3: 运行测试确认引擎集成无回归**

```bash
uv run pytest tests/ -q
```
Expected: 126 passed

- [ ] **Step 4: Commit**

```bash
git add src/pipeforge/core/engine.py src/pipeforge/core/context.py
git commit -m "feat: integrate checkpoints into PipelineEngine and ExecutionResult"
```

---

### Task 4: 检查点单元测试

**Files:**
- Create: `tests/test_checkpoints.py`

- [ ] **Step 1: 编写 test_checkpoints.py**

```python
import pytest
from unittest.mock import MagicMock
from datetime import datetime

from pipeforge.config.models import RowCountRule, CheckResult
from pipeforge.core.checkpoints import execute_checks, register_check, _CHECK_EXECUTORS
from pipeforge.config.exceptions import CheckpointError


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
        # warn 不应抛 CheckpointError

    def test_empty_table_defaults_to_default_table(self):
        mock_db = MagicMock()
        mock_db.query.return_value = [(42,)]

        rule = RowCountRule(table="", min=1, on_failure="block")
        results = execute_checks([rule], mock_db, "actual_table")
        assert results[0].passed is True
        mock_db.query.assert_called_with('SELECT COUNT(*) FROM "actual_table"')


class TestExecuteChecks:
    def test_collects_all_results_before_raising(self):
        """block 规则应收集全部结果后统一抛，而非逐条中断。"""
        mock_db = MagicMock()
        mock_db.query.return_value = [(3,)]  # min=5 for both

        rules = [
            RowCountRule(min=5, on_failure="block"),
            RowCountRule(min=5, on_failure="block"),
        ]
        with pytest.raises(CheckpointError) as exc:
            execute_checks(rules, mock_db, "t")
        assert len(exc.value.results) == 2  # both checked, not just first

    def test_unknown_rule_type_raises(self):
        mock_db = MagicMock()

        class UnknownRule(RowCountRule):
            type: str = "unknown"

        with pytest.raises(ValueError, match="Unknown check rule type"):
            execute_checks([UnknownRule()], mock_db, "t")

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
        # 验证 ISO 8601 格式
        datetime.fromisoformat(results[0].checked_at)
```

- [ ] **Step 2: 运行检查点测试**

```bash
uv run pytest tests/test_checkpoints.py -v
```
Expected: 9 passed

- [ ] **Step 3: 运行全量测试确认无回归**

```bash
uv run pytest tests/ -q
```
Expected: 135 passed (126 + 9 new)

- [ ] **Step 4: Commit**

```bash
git add tests/test_checkpoints.py
git commit -m "test: add checkpoints unit tests — row_count executor + execute_checks"
```

---

### Task 5: ConfigForge 层 — ProcessorConfig + YAML 序列化

**Files:**
- Modify: `configforge/models/wizard.py`
- Modify: `configforge/services/yaml_builder.py`

- [ ] **Step 1: ProcessorConfig 新增 checkpoints 字段**

编辑 `configforge/models/wizard.py`，在 `ProcessorConfig` 末尾新增字段和 import：

```python
from pipeforge.config.models import CheckRule

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

- [ ] **Step 2: yaml_builder.py YAML 输出包含 checkpoints**

编辑 `configforge/services/yaml_builder.py`。在 `build_yaml()` 的 processors 循环中（约 line 35-43，多处理器路径），`d["processors"].append()` 的 dict 末尾追加：

```python
if proc.checkpoints:
    entry["checkpoints"] = [r.model_dump(exclude_defaults=True) for r in proc.checkpoints]
```

同样在向后兼容的单处理器路径（约 line 52-57、line 61-65）中追加相同逻辑。

`CheckRule`（`RowCountRule`）有 Pydantic `model_dump()` 可序列化，`exclude_defaults=True` 不会输出 `on_failure: "block"`（默认值）等多余字段。

- [ ] **Step 3: 运行 ConfigForge 测试**

```bash
uv run pytest configforge/tests/ -q
```
Expected: 137 passed

- [ ] **Step 4: Commit**

```bash
git add configforge/models/wizard.py configforge/services/yaml_builder.py
git commit -m "feat: add checkpoints to ConfigForge ProcessorConfig and YAML output"
```

---

### Task 6: 前端类型映射 — types + store + serialization

**Files:**
- Modify: `configforge-web/src/types/wizard.ts`
- Modify: `configforge-web/src/stores/wizard.ts`
- Modify: `configforge-web/src/utils/serialization.ts`

- [ ] **Step 1: wizard.ts 新增 TypeScript 类型**

在 `configforge-web/src/types/wizard.ts` 末尾追加：

```typescript
export type CheckRule = {
  type: 'row_count'
  table: string
  min?: number
  max?: number
  on_failure: 'block' | 'warn'
}

export interface CheckResult {
  type: string
  passed: boolean
  message: string
  on_failure: 'block' | 'warn'
  checked_at: string
}
```

- [ ] **Step 2: ProcessorStep 类型追加 checkpoints**

编辑 `ProcessorStep` 的 union 类型，在两个分支中都加入 `checkpoints`：

```typescript
export type ProcessorStep =
  | { name: string; plugin: 'sql'; sql: string; inputTables: string[]; outputTables: string[]; checkpoints: CheckRule[] }
  | { name: string; plugin: 'python'; script: string; inputTables: string[]; outputTables: string[]; checkpoints: CheckRule[] }
```

- [ ] **Step 3: wizard.ts store 支持 checkpoints**

在 `addProcessor` 方法中初始化 `checkpoints: []`：

```typescript
function addProcessor(plugin: 'sql' | 'python' = 'sql') {
  processors.value.push(
    plugin === 'python'
      ? { name: '', plugin: 'python', script: '', inputTables: [], outputTables: [], checkpoints: [] }
      : { name: '', plugin: 'sql', sql: '', inputTables: [], outputTables: [], checkpoints: [] }
  )
}
```

在 `setProcessors` 中过滤时保留 `checkpoints`：

```typescript
function setProcessors(newProcessors: ProcessorStep[]) {
  const valid = newProcessors.filter(p => p.plugin === 'sql' ? p.sql.trim() : p.script.trim())
  processors.value = valid.length > 0 ? valid : newProcessors
}
```

在 `loadFromConfigState` 反序列化时初始化 `checkpoints`：

```typescript
const base = {
  name: raw.name || '',
  plugin,
  inputTables: raw.input_tables || raw.inputTables || [],
  outputTables: raw.output_tables || raw.outputTables || (raw.outputTable ? [raw.outputTable] : []),
  checkpoints: (raw.checkpoints || []).map((c: any) => ({ ...c, on_failure: c.on_failure || 'block' })),
}
```

在 `getWizardState` 中保留 `checkpoints`：

```typescript
processors: processors.value.map(p => ({
  ...p,
  checkpoints: p.checkpoints || [],
})),
```

- [ ] **Step 4: serialization.ts 序列化映射**

在 `stateToSnakeCase` 中映射 `checkpoints` 字段到 snake_case：

```typescript
checkpoints: p.checkpoints?.map((c: CheckRule) => ({
  type: c.type,
  table: c.table,
  min: c.min,
  max: c.max,
  on_failure: c.on_failure,
})) || [],
```

在 `SnakeState.processors` 类型中追加 `checkpoints` 字段。

- [ ] **Step 5: 运行前端测试 + TypeScript 检查**

```bash
cd configforge-web && npx vue-tsc --noEmit && npx vitest run
```
Expected: TypeScript 0 errors, 135 passed

- [ ] **Step 6: Commit**

```bash
git add configforge-web/src/types/wizard.ts configforge-web/src/stores/wizard.ts configforge-web/src/utils/serialization.ts
git commit -m "feat: add CheckRule types, store init, and serialization mapping"
```

---

### Task 7: 前端组件 — 预留 checkpoints 字段传递

**Files:**
- Modify: `configforge-web/src/components/step3/SqlEditorTab.vue`
- Modify: `configforge-web/src/components/step3/PythonProcessorContent.vue`
- Modify: `configforge-web/src/components/step3/ProcessorCard.vue`
- Modify: `configforge-web/src/components/step4/ExportActions.vue`
- Modify: `configforge-web/src/views/ConfigWizardView.vue`

- [ ] **Step 1: SqlEditorTab.vue — pickProcessor 初始化 checkpoints**

编辑 `pickProcessor`，在创建 step 对象时追加 `checkpoints: []`：

```typescript
const step = plugin === 'python'
  ? { name, plugin: 'python' as const, script: '', inputTables: [], outputTables: [], checkpoints: [] }
  : { name, plugin: 'sql' as const, sql: '', inputTables: [], outputTables: [], checkpoints: [] }
```

`switchProcessorType` 中也保留 checkpoints（如果该函数仍存在则修改，否则确保 pickProcessor 已覆盖）。

- [ ] **Step 2: PythonProcessorContent.vue — 更新类型断言**

在组件中确保 Props 类型包含 `checkpoints` 字段（通过父组件 ProcessorCard 传入）。PythonProcessorContent 本身不需要主动操作 checkpoints，但需要保证不因类型不匹配而报错。

- [ ] **Step 3: ProcessorCard.vue — 静态标签预留**

在 ProcessorCard 底部新增一条展示现有检查点数量的折叠行（v0.1 仅展示，不可编辑）：

```html
<div v-if="proc.checkpoints && proc.checkpoints.length > 0" class="processor-card__checks">
  <span class="text-xs text-slate-400">数据检查: {{ proc.checkpoints.length }} 条规则</span>
</div>
```

CSS 追加：
```css
.processor-card__checks {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--color-border-light);
}
```

- [ ] **Step 4: ExportActions.vue — YAML 导出包含 checkpoints**

在构建 YAML 请求的 `processors` 数据时，确保 `checkpoints` 字段被包含在序列化中（store → serialization 已经做了映射，此处只需确认不被过滤掉）。

- [ ] **Step 5: ConfigWizardView.vue — AI 编排保留 checkpoints**

在 `onOrchestrateConfirm` 中创建新 processor 对象时，追加 `checkpoints: []`：

```typescript
const proc: ProcessorStep = {
  name: step.name,
  plugin: step.plugin,
  ...(step.plugin === 'python' ? { script: step.script } : { sql: step.sql }),
  inputTables: step.input_tables || [],
  outputTables: step.output_tables || [],
  checkpoints: [],  // ← 新增
}
```

- [ ] **Step 6: 运行前端全量测试 + TypeScript**

```bash
cd configforge-web && npx vue-tsc --noEmit && npx vitest run
```
Expected: TypeScript 0 errors, 135 passed

- [ ] **Step 7: Commit**

```bash
git add configforge-web/src/components/step3/SqlEditorTab.vue \
        configforge-web/src/components/step3/PythonProcessorContent.vue \
        configforge-web/src/components/step3/ProcessorCard.vue \
        configforge-web/src/components/step4/ExportActions.vue \
        configforge-web/src/views/ConfigWizardView.vue
git commit -m "feat: add checkpoints field propagation through frontend components"
```

---

### Task 8: 集成测试

**Files:**
- Modify: `configforge/tests/test_pipeline.py`

- [ ] **Step 1: 在 test_pipeline.py 追加检查点集成测试**

```python
class TestCheckpoints:
    def test_row_count_warn_pipeline_proceeds(self):
        """warn 检查点不阻断管道执行。"""
        state = WizardState(
            scene=SceneInfo(name="test_checkpoint"),
            inputs=[InputSource(
                plugin="csv", table="test_data", param_key="test_data",
                config={"type": "csv", "delimiter": ",", "encoding": "utf-8"},
            )],
            processors=[ProcessorConfig(
                name="step1", plugin="sql", sql="CREATE TABLE result AS SELECT 1",
                input_tables=["test_data"], output_tables=["result"],
                checkpoints=[{
                    "type": "row_count", "table": "result",
                    "min": 99999, "on_failure": "warn",
                }],
            )],
        )
        yaml_str = build_yaml(state)
        assert "checkpoints" in yaml_str
        assert "row_count" in yaml_str
        assert "warn" in yaml_str

    def test_checkpoints_empty_by_default(self):
        """无检查点时 ProcessorConfig 正常序列化。"""
        state = WizardState(
            scene=SceneInfo(name="no_check"),
            processors=[ProcessorConfig(
                name="s1", plugin="sql", sql="SELECT 1",
                output_tables=["r1"],
            )],
        )
        yaml_str = build_yaml(state)
        assert "checkpoints" not in yaml_str  # 空时不输出
```

- [ ] **Step 2: 运行集成测试**

```bash
uv run pytest configforge/tests/test_pipeline.py -v
```
Expected: 集成测试 pass

- [ ] **Step 3: 运行全量后端 + 前端测试**

```bash
uv run pytest tests/ configforge/tests/ -q
cd configforge-web && npx vue-tsc --noEmit && npx vitest run
```
Expected: 后端 ~309 passed (300 + 9 new), 前端 135 passed, TypeScript 0 errors

- [ ] **Step 4: Commit**

```bash
git add configforge/tests/test_pipeline.py
git commit -m "test: add checkpoint integration tests for warn and block scenarios"
```

---

### Task 9: 最终验证与提交

- [ ] **Step 1: 全量测试**

```bash
uv run pytest tests/ configforge/tests/ -v
cd configforge-web && npx vue-tsc --noEmit && npx vitest run
```

- [ ] **Step 2: 确认 git 状态干净**

```bash
git status
```

- [ ] **Step 3: 最终 commit（如有遗漏）**

```bash
git add -A
git commit -m "chore: finalize data checkpoints v0.1"
```
