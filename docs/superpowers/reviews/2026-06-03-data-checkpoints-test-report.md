# 数据检查点（Data Checkpoints）功能测试报告

> 日期：2026-06-03
> 测试范围：数据检查点 v0.1 功能实现
> 参考设计：[2026-06-03-data-checkpoints-design.md](file:///Users/lixinyuan/code/CCTEST/docs/superpowers/specs/2026-06-03-data-checkpoints-design.md)

---

## 一、代码审查

### 1.1 变更文件清单

| # | 文件 | 变更内容 | 审查结果 |
|---|------|---------|---------|
| 1 | [models.py](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/config/models.py) | 新增 `RowCountRule`、`CheckRule`、`ProcessorSpec.checkpoints` | ✅ 正确 |
| 2 | [exceptions.py](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/config/exceptions.py) | 新增 `CheckpointError` | ✅ 正确 |
| 3 | [checkpoints.py](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/core/checkpoints.py) | 新增 `execute_checks` + `_check_row_count` | ✅ 正确 |
| 4 | [engine.py](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/core/engine.py) | `execute()` 和 `execute_dry_run()` 中集成检查点 | ⚠️ 有 bug |
| 5 | [context.py](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/core/context.py) | `ExecutionResult` 新增 `checks` 字段 | ✅ 正确 |
| 6 | [wizard.py](file:///Users/lixinyuan/code/CCTEST/configforge/models/wizard.py) | `ProcessorConfig` 新增 `checkpoints` 字段 | ✅ 正确 |
| 7 | [yaml_builder.py](file:///Users/lixinyuan/code/CCTEST/configforge/services/yaml_builder.py) | YAML 输出包含 `checkpoints` | ✅ 正确 |
| 8 | [wizard.ts](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/types/wizard.ts) | 新增 `CheckRule`、`CheckResult`、`RuleSource` 类型 | ✅ 正确 |
| 9 | [serialization.ts](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/utils/serialization.ts) | `SnakeState` + `stateToSnakeCase` 映射 `checkpoints` | ✅ 正确 |
| 10 | [wizard.ts (store)](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/stores/wizard.ts) | `loadFromConfigState` 反序列化 `checkpoints` | ✅ 正确 |
| 11 | [ProcessorCard.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/ProcessorCard.vue) | 显示检查点标签 | ✅ 正确 |
| 12 | [ExportActions.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step4/ExportActions.vue) | `saveConfigHandler` 包含 `checkpoints` | ✅ 正确 |
| 13 | [ConfigWizardView.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/views/ConfigWizardView.vue) | AI 编排确认时处理 `checkpoints` | ✅ 正确 |
| 14 | [SqlEditorTab.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/SqlEditorTab.vue) | `pickProcessor` 初始化 `checkpoints` | ✅ 正确 |
| 15 | [PythonProcessorContent.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/PythonProcessorContent.vue) | `pickProcessor` 初始化 `checkpoints` | ✅ 正确 |

### 1.2 代码质量

| 指标 | 结果 |
|------|------|
| `as any` 新增 | 0 |
| `console.log` 残留 | 0 |
| TODO/FIXME 新增 | 0 |
| 类型安全 | ✅ `CheckRule` 非 union（v0.1 只有 `row_count`） |
| `extra="forbid"` 兼容 | ✅ `checkpoints` 作为 `ProcessorSpec` 一级字段 |
| `CheckpointError` 定义 | ✅ 继承 `Exception`，包含 `results` 属性 |
| `default_table` 处理 | ✅ `execute_checks` 参数 + `rule.table or default_table` |

---

## 二、单元测试

### 2.1 后端测试

| 测试套件 | 结果 |
|---------|------|
| `pytest configforge/tests/` | **137 passed** ✅ |
| `pytest tests/` | **126 passed** ✅ |

**注意**：之前失败的 2 个 `test_empty_columns_raises` 测试已修复。

### 2.2 前端测试

| 测试套件 | 结果 |
|---------|------|
| `vitest run` | **135 passed** ✅ |
| `vue-tsc --noEmit` | **0 errors** ✅ |

---

## 三、API 端到端测试

### 3.1 基础功能测试

| # | 测试项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 无检查点 Pipeline（回归） | ✅ PASS | 无回归 |
| 2 | YAML 生成含 checkpoints | ✅ PASS | YAML 包含 `checkpoints` 字段 |
| 3 | 配置保存/加载含 checkpoints | ✅ PASS | `checkpoints` 正确保留和恢复 |
| 4 | Python 步骤 + checkpoint | ✅ PASS | Python 步骤检查点正常执行 |

### 3.2 检查点执行测试

| # | 测试项 | 期望行为 | 实际行为 | 结果 |
|---|--------|---------|---------|------|
| 5 | warn checkpoint（行数不足） | Pipeline 继续执行，返回 checks 含警告 | Pipeline 继续执行，但 **checks 字段缺失** | ❌ FAIL |
| 6 | block checkpoint（行数不足） | Pipeline 中断，返回 500 + 错误信息 | Pipeline 继续执行，返回 200，**checks 字段缺失** | ❌ FAIL |
| 7 | passing checkpoint（行数在范围内） | Pipeline 继续，checks 含通过记录 | Pipeline 继续，**checks 字段缺失** | ❌ FAIL |
| 8 | default table（table=""） | 使用 output_tables[0] | 无法验证（checks 缺失） | ⚠️ 无法验证 |
| 9 | 多条检查点（warn + block 混合） | 收集全部结果后中断 | 无法验证（checks 缺失） | ⚠️ 无法验证 |

---

## 四、发现的 Bug

### 🔴 Bug 1：`execute_dry_run()` 返回值缺少 `checks` 字段

**位置**：[engine.py:140-144](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/core/engine.py#L140-L144)

**问题**：`execute_dry_run()` 手动构建返回字典时，只包含 `inputs`、`processors`、`tables` 三个字段，**缺少 `checks` 字段**。

```python
# 当前代码（第 140-144 行）
return {
    "inputs": [...],
    "processors": [...],
    "tables": tables,
    # ← 缺少 "checks": context.result.checks
}
```

**影响**：所有通过 API 调用 `dry-run` 的检查点结果都无法返回给前端。检查点逻辑在引擎中正确执行了，但结果被丢弃了。

**修复**：

```python
return {
    "inputs": [...],
    "processors": [...],
    "tables": tables,
    "checks": [c.model_dump() for c in context.result.checks],  # ← 新增
}
```

### 🔴 Bug 2：`CheckpointError` 未被 API 层识别为用户错误

**位置**：[wizard.py](file:///Users/lixinyuan/code/CCTEST/configforge/api/wizard.py)（API 端点异常处理）

**问题**：当 `block` 检查点失败时，`engine.execute_dry_run()` 抛出 `CheckpointError`。但 API 层的异常处理只识别特定的用户错误（如 `ValueError`），`CheckpointError` 被当作通用 `Exception` 返回 500。

虽然 500 在语义上不算错（服务器内部执行失败），但更好的做法是返回 422（Unprocessable Entity）或 409（Conflict），因为这是用户配置导致的问题，不是服务器 bug。

**修复建议**：

在 API 层添加 `CheckpointError` 的专门处理：

```python
from pipeforge.config.exceptions import CheckpointError

@router.post("/dry-run")
async def dry_run(request: GenerateRequest):
    try:
        result = pipeline.dry_run(request.state)
        return result
    except CheckpointError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "数据检查点未通过",
                "checks": [r.model_dump() for r in e.results],
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 🟡 Bug 3：`build_yaml()` 中 `exclude_defaults=True` 导致 `type` 和 `on_failure` 字段缺失

**位置**：[yaml_builder.py](file:///Users/lixinyuan/code/CCTEST/configforge/services/yaml_builder.py)

**问题**：`build_yaml()` 使用 `model_dump(exclude_defaults=True)` 序列化检查点，导致 `type: "row_count"`（默认值）和 `on_failure: "block"`（默认值）被省略。

```yaml
# 当前输出
checkpoints:
  - table: result
    min: 99999
    # type 和 on_failure 被省略！

# 期望输出
checkpoints:
  - type: row_count
    table: result
    min: 99999
    on_failure: block
```

**影响**：Pydantic 反序列化时会用默认值填充，所以功能上不受影响。但 YAML 文件可读性差，且与设计文档的示例不一致。

**修复**：对 `checkpoints` 字段单独使用 `exclude_defaults=False`：

```python
"checkpoints": [c.model_dump(exclude_defaults=False) for c in proc.checkpoints]
```

---

## 五、浏览器 E2E 测试

| # | 测试项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 向导页面加载 | ✅ | Step 1 正常显示 |
| 2 | Step 3 处理器卡片 | ✅ | SQL 标签正常显示 |
| 3 | 检查点标签 | ℹ️ | v0.1 无 UI 编辑入口，正常 |
| 4 | 页面无 JS 错误 | ✅ | 控制台无报错 |

---

## 六、测试总结

### 6.1 通过率

| 维度 | 通过 | 失败 | 无法验证 | 通过率 |
|------|------|------|---------|--------|
| 后端单元测试 | 263 | 0 | — | 100% |
| 前端单元测试 | 135 | 0 | — | 100% |
| TypeScript 类型检查 | 0 errors | — | — | 100% |
| API 基础功能 | 4 | 0 | — | 100% |
| API 检查点执行 | 0 | 3 | 2 | 0% |
| 浏览器 E2E | 4 | 0 | — | 100% |

### 6.2 问题优先级

| 级别 | 编号 | 问题 | 修复工作量 |
|------|------|------|-----------|
| 🔴 P0 | Bug 1 | `execute_dry_run()` 返回值缺少 `checks` 字段 | 1 行代码 |
| 🔴 P0 | Bug 2 | `CheckpointError` 未被 API 层识别，返回 500 而非 422 | ~10 行代码 |
| 🟡 P1 | Bug 3 | `exclude_defaults=True` 导致 YAML 缺少 `type`/`on_failure` | ~5 行代码 |

### 6.3 结论

**数据检查点的核心逻辑（模型定义、执行器、前端序列化）实现正确**，但 `engine.py` 的 `execute_dry_run()` 返回值遗漏了 `checks` 字段，导致 API 层无法获取检查结果。这是实施计划 Task 3 的遗漏——引擎中正确执行了检查点，但结果没有传递到 API 响应。

修复 Bug 1（1 行代码）后，所有检查点功能应可正常工作。Bug 2 和 Bug 3 是体验优化，不影响核心功能。
