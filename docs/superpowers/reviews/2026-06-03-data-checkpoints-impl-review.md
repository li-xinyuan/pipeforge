# 数据检查点实施计划审核报告

> 日期：2026-06-03
> 审核对象：[2026-06-03-data-checkpoints-implementation.md](file:///Users/lixinyuan/code/CCTEST/docs/superpowers/plans/2026-06-03-data-checkpoints-implementation.md)
> 审核结论：**整体可执行，存在 2 个重要问题和 5 个轻微问题需修正**

---

## 一、重要问题

### 🟡 P1-1：`ExportActions.vue` 的 `saveConfigHandler` 手动构建 processor 对象，会丢失 `checkpoints`

**位置**：[ExportActions.vue:99-105](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step4/ExportActions.vue#L99-L105)

当前代码：
```typescript
processors: store.processors.map(p => ({
  plugin: p.plugin,
  ...(p.plugin === 'python' ? { script: p.script } : { sql: p.sql }),
  outputTables: p.outputTables,
  inputTables: p.inputTables,
  name: p.name,
})),
```

**问题**：这段代码手动构建 processor 对象，没有包含 `checkpoints` 字段。而 `downloadResult` 函数使用的是 `stateToSnakeCase(store.getWizardState())`，会正确包含 `checkpoints`。两条路径不一致，保存的配置会丢失检查点数据。

**修复建议**：`saveConfigHandler` 也应使用 `stateToSnakeCase`，或在手动构建时追加 `checkpoints`：

```typescript
processors: store.processors.map(p => ({
  plugin: p.plugin,
  ...(p.plugin === 'python' ? { script: p.script } : { sql: p.sql }),
  outputTables: p.outputTables,
  inputTables: p.inputTables,
  name: p.name,
  checkpoints: p.checkpoints || [],  // ← 新增
})),
```

**注意**：实施计划 Task 7 Step 4 只说了"确认不被过滤掉"，但没有指出 `saveConfigHandler` 的手动构建逻辑需要修改。

---

### 🟡 P1-2：`loadFromConfigState` 反序列化时 `checkpoints` 的 `on_failure` 字段名映射缺失

**位置**：[wizard.ts:146-158](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/stores/wizard.ts#L146-L158)

当前 `loadFromConfigState` 的 processor 反序列化代码：
```typescript
const base = {
  name: raw.name || '',
  plugin,
  inputTables: raw.input_tables || raw.inputTables || [],
  outputTables: raw.output_tables || raw.outputTables || (raw.outputTable ? [raw.outputTable] : []),
}
if (plugin === 'python') {
  return { ...base, script: raw.config?.script || raw.script || '' } as ProcessorStep
}
return { ...base, sql: raw.config?.sql || raw.sql || '' } as ProcessorStep
```

**问题**：后端返回的 `checkpoints` 中 `on_failure` 是 snake_case，但前端类型定义中 `on_failure` 也是 snake_case（设计文档 3.5 节 `CheckRule.on_failure`）。所以实际上不需要映射。但实施计划 Task 6 Step 3 写了：

```typescript
checkpoints: (raw.checkpoints || []).map((c: any) => ({ ...c, on_failure: c.on_failure || 'block' })),
```

这个写法**碰巧正确**（因为前后端都用 `on_failure`），但实施计划没有说明为什么这里不需要 snake_case → camelCase 转换，而其他字段（`inputTables`、`outputTables`）都需要。

**风险**：如果未来前端 `CheckRule` 改为 `onFailure`（camelCase），此处会悄悄丢失数据。

**修复建议**：在实施计划中明确注释说明 `CheckRule` 的字段命名策略——与后端保持 snake_case 一致（`on_failure` 而非 `onFailure`），不进行 camelCase 转换。这与 `inputTables`/`outputTables` 的策略不同，需要显式说明。

---

## 二、轻微问题

### 🟢 P2-1：Task 1 Step 3 和 Step 5 重复运行测试

Task 1 中 Step 3（添加模型后）和 Step 5（添加 ProcessorSpec 字段后）都运行 `pytest tests/ -q`。建议合并为一次测试运行，减少中间 commit 的数量。

### 🟢 P2-2：Task 4 测试中 `UnknownRule` 继承 `RowCountRule` 不太合理

```python
class UnknownRule(RowCountRule):
    type: str = "unknown"
```

`RowCountRule` 的 `type` 是 `Literal["row_count"]`，子类覆盖为 `str` 在 Pydantic v2 中可能产生意外行为。建议改为直接构造 dict 或使用 `BaseModel`：

```python
# 更安全的做法：直接用 RowCountRule 但修改 type 字段
rule = RowCountRule(min=1, on_failure="block")
rule_dict = rule.model_dump()
rule_dict["type"] = "unknown"
# 然后手动调用 execute_checks
```

或者，因为 `CheckRule = RowCountRule`，直接在测试中 mock `_CHECK_EXECUTORS` 来验证 `ValueError` 路径。

### 🟢 P2-3：Task 2 的 `checkpoints.py` import 路径可能有问题

```python
from pipeforge.config.models import CheckRule, CheckResult, CheckpointError, RowCountRule
from pipeforge.core.sqlite import SQLiteManager
```

`CheckpointError` 定义在 `exceptions.py` 中，不是 `models.py`。应为：

```python
from pipeforge.config.models import CheckRule, CheckResult, RowCountRule
from pipeforge.config.exceptions import CheckpointError
from pipeforge.core.sqlite import SQLiteManager
```

### 🟢 P2-4：Task 3 Step 2 的行号参考可能过时

实施计划写"约 line 63"和"约 line 108"，但代码经过多轮修改后行号可能已变化。建议改为描述性定位（如"在 `context.result.processors.append(stats)` 之后"），而非硬编码行号。

### 🟢 P2-5：Task 8 集成测试缺少 `block` 场景

当前集成测试只覆盖了 `warn` 场景（管道继续执行）和空检查点场景，缺少 `block` 场景（管道应中断）。建议增加：

```python
def test_row_count_block_pipeline_stops(self):
    """block 检查点应中断管道执行。"""
    state = WizardState(
        scene=SceneInfo(name="test_block"),
        inputs=[InputSource(...)],
        processors=[ProcessorConfig(
            name="step1", plugin="sql", sql="CREATE TABLE result AS SELECT 1",
            input_tables=["test_data"], output_tables=["result"],
            checkpoints=[{
                "type": "row_count", "table": "result",
                "min": 99999, "on_failure": "block",
            }],
        )],
    )
    # 验证 dry_run 抛出异常或返回错误
```

---

## 三、任务完整性检查

| Task | 文件覆盖 | 代码正确性 | 测试覆盖 | 评价 |
|------|---------|-----------|---------|------|
| Task 1: PipeForge 模型 | ✅ | ✅ | ✅ 有回归测试 | 好 |
| Task 2: checkpoints.py | ✅ | ⚠️ import 路径错误（P2-3） | ✅ | 需微调 |
| Task 3: engine + context | ✅ | ✅ | ✅ 有回归测试 | 好 |
| Task 4: 单元测试 | ✅ | ⚠️ UnknownRule 继承问题（P2-2） | ✅ | 需微调 |
| Task 5: ConfigForge 模型 | ✅ | ✅ | ✅ | 好 |
| Task 6: 前端类型 | ✅ | ⚠️ 命名策略未说明（P1-2） | ✅ | 需补充说明 |
| Task 7: 前端组件 | ⚠️ 遗漏 ExportActions saveConfig（P1-1） | ✅ | — | 需补充 |
| Task 8: 集成测试 | ✅ | ✅ | ⚠️ 缺 block 场景（P2-5） | 需补充 |
| Task 9: 最终验证 | ✅ | ✅ | ✅ | 好 |

---

## 四、总结

| 级别 | 数量 | 说明 |
|------|------|------|
| 🟡 重要 | 2 | ExportActions saveConfig 丢失 checkpoints；CheckRule 命名策略未说明 |
| 🟢 轻微 | 5 | 重复测试、UnknownRule 继承、import 路径、行号参考、缺 block 测试 |

**结论**：实施计划整体可执行，9 个 Task 的拆分合理、顺序正确。建议在开发前修正 2 个重要问题（P1-1 和 P1-2），轻微问题可在开发中顺带处理。
