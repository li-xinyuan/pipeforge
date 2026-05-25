# ConfigForge Python 处理器测试问题修复报告

> 修复日期: 2026-05-25
> 基准报告: `docs/superpowers/reviews/2026-05-25-python-processor-test-report.md`

---

## 修复概览

| # | 问题 | 严重度 | 状态 |
|---|------|--------|------|
| P0 | 前端序列化格式与后端模型不匹配 | 🔴 阻断 | ✅ 已修复 |
| P1 | AI 生成按钮无功能 | 🟡 重要 | ✅ 已修复 |
| P2 | OrchestrationResult 硬编码 SQL 标签 | 🟡 重要 | ✅ 已修复 |
| P3 | AI 编排 prompt 仅支持 SQL | 🟡 重要 | 延后 v0.4.1 |
| P4 | `as` 类型断言 | 🟢 轻微 | ✅ 已修复 |
| P5 | Python 步骤名称自动推断 | 🟢 轻微 | ✅ 已修复 |
| P6 | Python 输出表名自动推断 | 🟢 轻微 | ✅ 已修复 |

**修复率: 6/7，P3 延后至 v0.4.1（属于功能增强）**

---

## P0: 前端序列化格式不匹配

**根因**: `serialization.ts` 的 `stateToSnakeCase` 将 `script` 放入嵌套 `config: {type: 'python', script: ...}`，但后端 `ProcessorConfig` 是扁平结构，`script` 应在顶层。

**修复**: `serialization.ts` — 去除 `config` 包装，扁平化为 `{ ...base, script: p.script }`。同步更新 `SnakeState` 接口。

**验证**: `POST /api/wizard/dry-run` → 200 OK，Python 步骤正常返回 table 数据。

---

## P1: AI 生成按钮无功能

**根因**: `PythonProcessorContent.vue` 的 "✨ AI 生成" 按钮 emit `ai-generate` 事件，但没有组件监听此事件。AI 生成 Python 脚本是 v0.4.1 目标。

**修复**: 移除该按钮及相关的 `aiConfigured`、`getAiSettings`、`onMounted` 代码。

---

## P2: OrchestrationResult 硬编码 SQL 标签

**根因**: `OrchestrationResult.vue` 所有步骤显示 `<NTag type="info">SQL</NTag>`，`OrchestrationStep` 类型缺少 `plugin`/`script` 字段。

**修复**:
1. `wizard.ts` — `OrchestrationStep` 新增 `plugin?: 'sql' | 'python'` 和 `script?: string`
2. `OrchestrationResult.vue` — 标签改为动态 `<NTag :type="step.plugin === 'python' ? 'warning' : 'info'">`，代码显示改为 `step.script || step.sql`

---

## P3: AI 编排 prompt 仅支持 SQL

**根因**: `orchestrator.py` 的 orchestrate prompt 仅描述 SQL 步骤格式。

**修复**: 延后至 v0.4.1。原因：AI 生成 Python 代码的安全风险需要独立评估，v0.4.0 设计明确将"AI 编排生成 Python 步骤"列为非目标。

---

## P4: `as` 类型断言

**根因**: `PythonProcessorContent.vue` 使用 `props.proc as { plugin: 'python'; ... }` 绕过 TypeScript 检查。

**修复**: 改用运行时类型守卫 `if (props.proc.plugin !== 'python') throw new Error(...)`。

---

## P5: Python 步骤名称自动推断

**根因**: `SqlEditorTab.vue` 的 watch 在 `proc.plugin !== 'sql'` 时直接 `continue`，Python 步骤无名称推断。

**修复**: 新增 `inferPythonStepName(script)` 函数，检测 SQL 模式（DELETE/CREATE TABLE/GROUP BY/JOIN）和 Python 特有模式（正则/API 调用）。watch 中添加 Python 分支调用此函数。

---

## P6: Python 输出表名自动推断

**根因**: 同 P5。

**修复**: 新增 `inferPythonOutputTable(script)` 函数，用正则 `/CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["']?(\w+)["']?/i` 提取表名。watch 中添加 Python 分支调用此函数。

---

## 附加修复: 插件注册

**问题**: `PythonProcessorPlugin` 虽在 `python.py` 中通过 `@register_plugin` 装饰器注册，但模块未在 `__init__.py` 中导入，导致运行时 `PluginNotFoundError`。

**修复**: `src/pipeforge/plugins/processor/__init__.py` 添加 `from pipeforge.plugins.processor.python import PythonProcessorPlugin`。

---

## 验证结果

| 测试 | 修复前 | 修复后 |
|------|--------|--------|
| `POST /api/wizard/dry-run` (Python 步骤) | 422 | **200 OK** |
| `POST /api/wizard/dry-run` (SQL+Python 混合) | 422 | **200 OK** |
| `vue-tsc --noEmit` | 0 errors | **0 errors** |
| `vitest run tests/` | 113 passed | **113 passed** |
| `pytest tests/ configforge/tests/` | 263 passed | **263 passed** |

---

## 独立验证结果（2026-05-25）

以下验证由独立测试执行，非修复者自测。

### 代码级验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| P0: `serialization.ts` 扁平化 `script: p.script` | ✅ | 1 处，无嵌套 config |
| P0: `SnakeState.processors` 类型含 `sql?`/`script?` | ✅ | 与后端 `ProcessorConfig` 扁平结构匹配 |
| P1: `PythonProcessorContent.vue` 无 "AI 生成" 按钮 | ✅ | 0 处 "AI 生成" |
| P1: `PythonProcessorContent.vue` 无 `ai-generate` emit | ✅ | 0 处 |
| P1: `PythonProcessorContent.vue` 无 `aiConfigured` | ✅ | 0 处 |
| P2: `OrchestrationResult.vue` 动态 plugin 标签 | ✅ | `step.plugin === 'python' ? 'warning' : 'info'` |
| P2: `OrchestrationResult.vue` 动态代码显示 | ✅ | `step.script \|\| step.sql` |
| P2: `OrchestrationStep` 含 `plugin?: 'sql' \| 'python'` | ✅ | wizard.ts 第 26 行 |
| P2: `OrchestrationStep` 含 `script?: string` | ✅ | wizard.ts 第 28 行 |
| P4: 类型守卫 `props.proc.plugin !== 'python'` | ✅ | 1 处，无 `as` 断言 |
| P5: `inferPythonStepName` 函数 | ✅ | 2 处引用 |
| P6: `inferPythonOutputTable` 函数 | ✅ | 2 处引用 |
| 附加: `PythonProcessorPlugin` 注册 | ✅ | `__init__.py` 含导入 |
| 附加: `pipeline.py` 跳过 Python 步骤 | ✅ | 2 处 `continue` |

### API 端到端测试

| 测试 | 结果 | 说明 |
|------|------|------|
| Python Processor Dry Run | ✅ PASS | adults 表 2 行（Alice, Charlie） |
| Mixed SQL+Python Pipeline | ✅ PASS | result 表 2 行（Alice, Charlie） |
| Python Error Handling (missing process) | ✅ PASS | 500 + "必须定义 process(ctx) 函数" |
| Python Syntax Error | ✅ PASS | 500 + "expected ':'" |
| YAML Generation with Python | ✅ PASS | 含 `plugin: python`、`script:`、`type: python` |
| Python Timeout (infinite loop) | ✅ PASS | 500 + "执行超时（30秒）" |
| SQL-Only Pipeline (regression) | ✅ PASS | 无回归 |
| Python ctx.db API (multi-op) | ✅ PASS | INSERT + CREATE TABLE 正常执行 |

### 单元测试

| 测试套件 | 结果 |
|---------|------|
| `vitest run` (前端) | **113 passed** |
| `pytest configforge/tests/` (ConfigForge 后端) | **137 passed** |
| `pytest tests/` (集成测试) | **126 passed** |
| `vue-tsc --noEmit` (TypeScript 类型检查) | **0 errors** |

### 全量代码审查

| 文件 | 适配状态 | 说明 |
|------|---------|------|
| `serialization.ts` | ✅ | 扁平化 script/sql，SnakeState 同步更新 |
| `PythonProcessorContent.vue` | ✅ | 移除 AI 生成按钮，类型守卫替代 as 断言 |
| `OrchestrationResult.vue` | ✅ | 动态 plugin 标签 + script/sql 显示 |
| `wizard.ts` (类型) | ✅ | OrchestrationStep 含 plugin/script，ProcessorStep discriminated union |
| `SqlEditorTab.vue` | ✅ | inferPythonStepName + inferPythonOutputTable |
| `ConfigWizardView.vue` | ✅ | 16 处 `.sql` 全部适配为 `p.plugin === 'sql' ? p.sql : p.script` |
| `ExportActions.vue` | ✅ | `p.plugin === 'python' ? { script } : { sql }` |
| `OutputConfigTab.vue` | ✅ | 4 处 `.sql` 适配 |
| `wizard.ts` (store) | ✅ | addProcessor/setProcessors/loadFromConfigState/canProceed/stepValidation |
| `pipeline.py` | ✅ | 2 处 SQL 自动包装跳过 Python |
| `yaml_builder.py` | ✅ | 主分支 + 向后兼容分支均支持 Python |
| `PythonProcessorGenerator` | ✅ | AST 校验 process 函数 |
| `PythonProcessorPlugin` | ✅ | exec + 超时 + commit |
| `PythonProcessorConfig` | ✅ | discriminated union + script 非空校验 |
| `_inject_type_defaults` | ✅ | Python plugin 注入 type |
| `ProcessorSpec` | ✅ | `SqlProcessorConfig \| PythonProcessorConfig` |

---

## 新发现的问题

### 🟡 新问题 1：`serialization.ts` 的 `SnakeState` 中 `sql`/`script` 均为可选，但后端 `ProcessorConfig` 的 `model_validator` 在有 `output_tables` 时要求非空

**位置**: [serialization.ts](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/utils/serialization.ts) 第 17-18 行

```typescript
processors: Array<{
  name: string
  plugin: string
  input_tables: string[]
  output_tables: string[]
  sql?: string    // 可选
  script?: string // 可选
}>
```

**问题**: 前端类型允许 `sql` 和 `script` 同时为 `undefined`，但后端 `ProcessorConfig` 的 `model_validator` 在有 `output_tables` 时会校验对应字段非空。如果前端发送了 `plugin: 'python'` 但忘记附带 `script`，后端会返回 422。

**影响**: 低 — 当前代码路径中 `stateToSnakeCase` 总是附带 `sql` 或 `script`，不会产生 undefined。但类型定义不够严格，可能导致未来开发中遗漏。

**建议**: 将 `SnakeState.processors` 改为 discriminated union：

```typescript
processors: Array<
  | { name: string; plugin: 'sql'; input_tables: string[]; output_tables: string[]; sql: string }
  | { name: string; plugin: 'python'; input_tables: string[]; output_tables: string[]; script: string }
>
```

### 🟢 新问题 2：`PythonProcessorPlugin` 的 `exec()` 使用空全局命名空间 `{}`，但 `process(ctx)` 内的 `import` 语句仍可工作

**位置**: [python.py](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/plugins/processor/python.py) 第 20 行

```python
exec(config.script, {}, local_ns)
```

**说明**: `exec` 的第二个参数是全局命名空间，设为空 `{}` 意味着脚本顶层代码无法访问任何内置函数。但 Python 的 `import` 机制不依赖全局命名空间中的 `__builtins__`，所以 `import` 语句仍可工作。然而，如果脚本顶层直接使用 `print()`、`len()` 等内置函数，会报 `NameError`。

**影响**: 低 — 设计文档明确要求脚本定义 `process(ctx)` 函数，函数内部的 `import` 正常工作。顶层代码使用内置函数的场景极少。

**建议**: 如果需要支持顶层内置函数，可将 `__builtins__` 加入全局命名空间：

```python
exec(config.script, {"__builtins__": __builtins__}, local_ns)
```

但这与"信任执行模型"一致，不影响安全性。

### 🟢 新问题 3：`onOrchestrateConfirm` 中 Python 步骤的 `script` 回退到 `s.sql`

**位置**: [ConfigWizardView.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/views/ConfigWizardView.vue) 第 570 行

```typescript
return { name: s.name || `步骤 ${i + 1}`, plugin, script: s.script || s.sql || '', inputTables, outputTables: s.output_tables || [] }
```

**说明**: 当 `plugin === 'python'` 但 `s.script` 为空时，会回退到 `s.sql`。这是为了兼容当前 AI 编排只返回 `sql` 字段的情况（P3 延后），但语义上不太准确——Python 步骤不应该使用 SQL 代码。

**影响**: 低 — 当前 AI 编排不会返回 Python 步骤（P3 延后），此回退逻辑不会被触发。当 P3 实现后，AI 返回的 Python 步骤应包含 `script` 字段，此回退可移除。

**建议**: 在 P3 实现时移除 `|| s.sql` 回退。

---

## 验证结论

✅ **修复报告中的 6 项修复 + 3 个新发现问题全部通过独立验证**，P3 按计划延后。

- P0（阻断性 Bug）已彻底修复：API 从 422 恢复为 200，Python 步骤可正常执行
- P1-P6 修复均经代码审查和测试验证确认
- 附加修复（插件注册）已验证
- 3 个新发现问题（SnakeState 类型、exec builtins、orchestrate 回退）均已修复并验证
- 无回归：SQL-only 流程、前端 113 测试、后端 263 测试均通过
- 全量代码审查未发现新问题

---

## 第二轮验证结果（2026-05-25）

3 个新发现问题修复后的独立验证。

### 新发现问题修复验证

| 问题 | 修复内容 | 验证方式 | 结果 |
|------|---------|---------|------|
| 🟡 SnakeState `sql?`/`script?` 可选 | 改为 discriminated union | TypeScript 编译 + 代码审查 | ✅ |
| 🟢 `exec()` 空全局命名空间 | 添加 `{"__builtins__": __builtins__}` | API 测试 Test 8（`len()` 可用） | ✅ |
| 🟢 `onOrchestrateConfirm` `s.sql` 回退 | 移除 `|| s.sql` | 代码审查 | ✅ |

### API 端到端测试（10/10 通过）

| 测试 | 结果 | 说明 |
|------|------|------|
| Python Processor Dry Run | ✅ PASS | adults 表 2 行 |
| Mixed SQL+Python Pipeline | ✅ PASS | result 表 2 行 |
| Python Error (missing process) | ✅ PASS | 500 + "必须定义 process(ctx) 函数" |
| Python Syntax Error | ✅ PASS | 500 + "expected ':'" |
| YAML Generation with Python | ✅ PASS | 含 plugin/script/type 字段 |
| Python Timeout | ✅ PASS | 500 + "执行超时（30秒）" |
| SQL-Only Regression | ✅ PASS | 无回归 |
| Python `__builtins__` Access | ✅ PASS | `len()` 函数正常工作，stats 表返回 [[3]] |
| Python Top-level Builtins | ✅ PASS | 顶层 `import` 正常 |
| Python ctx.params Access | ✅ PASS | ctx API 正常 |

### 单元测试

| 测试套件 | 结果 |
|---------|------|
| `vitest run` (前端) | **113 passed** |
| `pytest configforge/tests/ tests/` (后端) | **263 passed** |
| `vue-tsc --noEmit` (TypeScript 类型检查) | **0 errors** |

### 全量代码审查

审查了所有涉及 `.sql` 引用的 40 处代码，确认：
- 所有 `ProcessorStep` 的 `.sql` 访问均通过 `p.plugin === 'sql'` 类型守卫保护
- `SqlEditorTab.vue` 的 `checkTableRenames` 和 `onReplaceTableName` 正确跳过 Python 步骤
- `ConfigWizardView.vue` 的 AI chat 逻辑正确查找 SQL 步骤填充，不覆盖 Python 步骤
- `serialization.ts` 使用 `as const` 确保与 `SnakeState` discriminated union 类型匹配
- `loadFromConfigState` 兼容扁平格式和嵌套 config 格式

**未发现新问题。**
