# ConfigForge Python 处理器功能测试报告

**测试日期**: 2026-05-25
**测试范围**: Python 处理器步骤功能端到端测试 + 回归测试
**测试基线**: `docs/superpowers/specs/2026-05-24-python-processor-design.md`
**实现计划**: `docs/superpowers/plans/2026-05-24-python-processor-implementation.md`

---

## 一、测试概览

| 测试类别 | 通过 | 失败 | 总计 |
|---------|------|------|------|
| 后端单元测试 | 263 | 0 | 263 |
| 前端单元测试 | 113 | 0 | 113 |
| 后端 API 测试 | 2 | 3 | 5 |
| 前端 UI 测试 | 9 | 1 | 10 |
| **合计** | **387** | **4** | **391** |

**总体结论**: ⚠️ **存在 1 个阻断性 Bug**，3 个重要问题，4 个轻微问题。Python 处理器核心功能已实现，但前后端数据格式不匹配导致 API 调用失败。

---

## 二、阻断性问题

### 🔴 P0：前端序列化格式与后端模型不匹配 — Python 步骤 API 调用全部失败

**严重程度**: 🔴 阻断 — Python 步骤无法通过 API 执行任何操作

**问题描述**:

前端 `serialization.ts` 的 `stateToSnakeCase()` 将 Python 步骤的 `script` 放入嵌套的 `config` 对象：

```typescript
// configforge-web/src/utils/serialization.ts 第 106-108 行
if (p.plugin === 'python') {
  return { ...base, config: { type: 'python', script: p.script } }
}
```

生成的 JSON：
```json
{
  "plugin": "python",
  "config": {"type": "python", "script": "def process(ctx): ..."},
  "input_tables": [...],
  "output_tables": [...]
}
```

但后端 `ProcessorConfig` 模型是**扁平结构**，`script` 是顶层字段：

```python
# configforge/models/wizard.py 第 55-58 行
class ProcessorConfig(BaseModel):
    plugin: Literal["sql", "python"] = "sql"
    sql: str = Field(default="", alias="sql")
    script: str = Field(default="", alias="script")
```

后端期望的 JSON：
```json
{
  "plugin": "python",
  "script": "def process(ctx): ...",
  "input_tables": [...],
  "output_tables": [...]
}
```

**影响**:
- 前端发送的 `config.script` 被后端忽略（`ProcessorConfig` 没有 `config` 字段）
- `ProcessorConfig.script` 始终为空字符串 `""`
- `model_validator` 检测到 `plugin == "python"` 但 `script` 为空，抛出 422 错误
- **所有涉及 Python 步骤的 API 调用（dry-run、generate、execute）全部失败**

**API 测试证据**:
```
POST /api/wizard/dry-run → 422
{"detail": [{"msg": "Value error, Python 步骤的 script 字段不能为空"}]}
```

**根因分析**:

前端序列化沿用了 PipeForge YAML 格式（`config: {type: python, script: ...}`），但 ConfigForge API 层的 `ProcessorConfig` 是扁平结构。两层的数据契约不一致。

**修复方案**（二选一）:

**方案 A（推荐）— 修改前端序列化，将 script/sql 提升到顶层**:

```typescript
// serialization.ts — stateToSnakeCase processors 映射
processors: state.processors.map((p) => {
  const base = {
    name: p.name,
    plugin: p.plugin,
    input_tables: p.inputTables,
    output_tables: p.outputTables,
  }
  if (p.plugin === 'python') {
    return { ...base, script: p.script }
  }
  return { ...base, sql: p.sql }
}),
```

**方案 B — 修改后端 ProcessorConfig，添加 config 嵌套字段**:

```python
class ProcessorConfig(BaseModel):
    plugin: Literal["sql", "python"] = "sql"
    name: str = ""
    config: Annotated[SqlProcessorConfig | PythonProcessorConfig, Field(discriminator="type")] | None = None
    input_tables: list[str] = []
    output_tables: list[str] = []
```

此方案需要同时修改 `yaml_builder.py`、`pipeline.py` 等多处从 `proc.sql`/`proc.script` 读取的代码，改动量大。

**推荐方案 A**，改动量小且与后端现有模型一致。但需注意：`yaml_builder.py` 中构建 YAML 时仍需将 `script` 放入 `config` 嵌套对象（因为 PipeForge 的 `ProcessorSpec` 使用 discriminated union），这部分逻辑已正确实现。

---

## 三、重要问题

### 🟡 P1：PythonProcessorContent 的 "✨ AI 生成" 按钮无功能

**严重程度**: 🟡 重要 — 用户点击后无任何反应

**问题描述**:

[PythonProcessorContent.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/PythonProcessorContent.vue) 第 63 行有 "✨ AI 生成" 按钮：

```vue
<NButton size="tiny" :disabled="!aiConfigured" @click="$emit('ai-generate')">✨ AI 生成</NButton>
```

该组件 emit 了 `ai-generate` 事件，但：

1. [ProcessorCard.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/ProcessorCard.vue) 没有监听此事件（仅监听 `update`）
2. [SqlEditorTab.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/SqlEditorTab.vue) 也没有处理

**对比**: SQL 步骤的 AI 生成功能是在 `SqlProcessorContent.vue` 内部自行实现的（有 `showNlInput` 状态、`onAiGenerateSql` 函数、自然语言输入框等），不依赖外部事件传递。

**修复方案**:

在 `PythonProcessorContent.vue` 内部实现 AI 生成 Python 脚本的功能，参考 `SqlProcessorContent.vue` 的模式：

```vue
<div v-if="showNlInput" class="p-3 bg-amber-50 border border-amber-200 rounded-lg">
  <NInput v-model:value="nlText" type="textarea"
    :autosize="{ minRows: 3, maxRows: 6 }"
    placeholder="用自然语言描述你想要的 Python 处理逻辑" />
  <div class="flex gap-2 mt-2">
    <NButton size="small" type="warning" :loading="suggesting" @click="onAiGenerateScript">生成脚本</NButton>
    <NButton size="small" @click="showNlInput = false">取消</NButton>
  </div>
</div>
```

或者，如果当前版本不支持 AI 生成 Python 脚本，应移除该按钮或添加 `disabled` 提示。

### 🟡 P2：OrchestrationResult 组件硬编码 SQL 标签

**严重程度**: 🟡 重要 — AI 编排结果无法正确显示 Python 步骤

**问题描述**:

[OrchestrationResult.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/wizard/OrchestrationResult.vue) 第 6 行：

```vue
<NTag size="tiny" type="info">SQL</NTag>
```

所有编排步骤都显示 "SQL" 标签，即使步骤可能是 Python 类型。

**同时**，`OrchestrationStep` 类型定义只有 `sql` 字段，没有 `plugin` 和 `script`：

```typescript
// wizard.ts 第 24-28 行
export interface OrchestrationStep {
  name: string
  input_tables: string[]
  output_tables: string[]
  sql: string  // 缺少 plugin 和 script 字段
}
```

**修复方案**:

1. 扩展 `OrchestrationStep` 类型：
```typescript
export interface OrchestrationStep {
  name: string
  plugin?: 'sql' | 'python'
  input_tables: string[]
  output_tables: string[]
  sql: string
  script?: string
}
```

2. 修改 `OrchestrationResult.vue` 的标签：
```vue
<NTag size="tiny" :type="step.plugin === 'python' ? 'warning' : 'info'">
  {{ step.plugin === 'python' ? 'Python' : 'SQL' }}
</NTag>
```

3. 修改代码显示区域，Python 步骤显示 `script` 而非 `sql`

### 🟡 P3：后端 AI 编排 prompt 仅支持 SQL 步骤

**严重程度**: 🟡 重要 — AI 编排无法生成 Python 步骤

**问题描述**:

[orchestrator.py](file:///Users/lixinyuan/code/CCTEST/configforge/services/ai/orchestrator.py) 的 `orchestrate` prompt 明确要求 AI 只生成 SQL：

```
"你是一个数据流水线架构师。用户提供输入源和输出目标，你需要规划 SQL 步骤链。\n\n"
...
'{"steps": [{"name": "...", "input_tables": [...], "output_tables": [...], "sql": "..."}], ...}'
```

返回格式中没有 `plugin` 和 `script` 字段，AI 无法规划 Python 步骤。

**影响**: 即使前端 `onOrchestrateConfirm` 已支持 Python 步骤（第 570 行），AI 编排永远不会返回 Python 步骤。

**修复方案**: 修改 orchestrate prompt，允许 AI 在需要复杂数据转换时生成 Python 步骤：

```
"## 规则\n"
"- 简单查询和聚合用 SQL 步骤（plugin: sql）\n"
"- 需要复杂逻辑（循环、条件分支、字符串处理）时用 Python 步骤（plugin: python）\n"
...
'{"steps": [{"name": "...", "plugin": "sql|python", "input_tables": [...], "output_tables": [...], "sql": "...", "script": "..."}], ...}'
```

---

## 四、轻微问题

### 🟢 P4：PythonProcessorContent 使用 `as` 类型断言而非类型守卫

**位置**: [PythonProcessorContent.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/PythonProcessorContent.vue) 第 90 行

```typescript
const pyProc = computed(() => props.proc as { plugin: 'python'; script: string; ... })
```

使用 `as` 断言绕过了 TypeScript 的类型检查。如果 `proc` 实际上是 SQL 步骤，访问 `pyProc.script` 会得到 `undefined`。

**建议**: 使用类型守卫：
```typescript
const pyProc = computed(() => {
  if (props.proc.plugin === 'python') return props.proc
  throw new Error('PythonProcessorContent received non-Python step')
})
```

### 🟢 P5：PythonProcessorContent 缺少步骤名称自动推断

**位置**: [SqlEditorTab.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/SqlEditorTab.vue) 第 163-189 行

SQL 步骤有自动推断步骤名称的逻辑（`inferStepName`），但 Python 步骤没有。Python 卡片的步骤名称始终需要手动输入。

**建议**: 添加 Python 步骤名称推断，例如检测 `process(ctx)` 中的 SQL 语句类型。

### 🟢 P6：PythonProcessorContent 缺少输出表名自动推断

SQL 步骤会根据 SQL 内容自动推断输出表名（`inferOutputTable`），但 Python 步骤没有此功能。用户必须手动输入输出表名。

**建议**: 可以解析 Python 脚本中的 `CREATE TABLE ...` 语句来推断输出表名。

### 🟢 P7：SqlEditorTab 中 Python 步骤的自动 SQL 填充逻辑可能误触发

**位置**: [SqlEditorTab.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/SqlEditorTab.vue) 第 153-159 行

```typescript
watch(inputTableNames, (tables) => {
  if (tables.length > 0) {
    for (const proc of store.processors) {
      if (proc.plugin === 'sql' && !proc.sql.trim()) {
        proc.sql = `SELECT * FROM "${tables[0]}"`
        break
      }
    }
  }
})
```

此逻辑正确跳过了 Python 步骤（`proc.plugin === 'sql'`），但如果所有步骤都是 Python 类型，没有任何步骤会被填充，这是预期行为。无需修改，仅记录。

---

## 五、与设计文档的偏差

| 设计要求 | 实现状态 | 偏差说明 |
|---------|---------|---------|
| PipeForge `PythonProcessorConfig` | ✅ 已实现 | `src/pipeforge/config/models.py` |
| PipeForge `PythonProcessorPlugin` | ✅ 已实现 | `src/pipeforge/plugins/processor/python.py` |
| `_inject_type_defaults` 支持 python | ✅ 已实现 | `src/pipeforge/config/__init__.py` |
| `pipeline.py` SQL 自动包装跳过 Python | ✅ 已实现 | 两处循环均添加了 `continue` |
| ConfigForge `ProcessorConfig` 扩展 | ✅ 已实现 | `plugin` + `script` + `model_validator` |
| `yaml_builder.py` Python 序列化 | ✅ 已实现 | 主分支 + 向后兼容分支 |
| `PythonProcessorGenerator` | ✅ 已实现 | AST 校验 `process` 函数 |
| 前端 `ProcessorStep` discriminated union | ✅ 已实现 | `wizard.ts` |
| 前端 `serialization.ts` 分支 | ⚠️ 有偏差 | 格式与后端模型不匹配（P0） |
| 前端 `wizard store` 6 处适配 | ✅ 已实现 | `addProcessor`/`canProceed`/`stepValidation`/`setProcessors`/`resetAll`/`loadFromConfigState` |
| `PythonProcessorContent.vue` | ✅ 已实现 | 含 textarea、预览、AI 生成按钮 |
| `ProcessorCard.vue` v-if 分支 | ✅ 已实现 | SQL/Python 双模式渲染 |
| `SqlEditorTab.vue` "+ Python 步骤" 按钮 | ✅ 已实现 | 橙色 warning 类型 |
| `ConfigWizardView.vue` 5 处适配 | ✅ 已实现 | `plugin === 'sql'` 三元判断 |
| `ExportActions.vue` 适配 | ✅ 已实现 | `p.plugin === 'python' ? { script } : { sql }` |
| `OutputConfigTab.vue` 4 处适配 | ✅ 已实现 | `p.plugin === 'sql' ? p.sql : p.script` |
| 预览执行复用 dry-run | ⚠️ 受 P0 阻断 | 逻辑正确但 API 调用失败 |
| AI 编排支持 Python 步骤 | ❌ 未实现 | prompt 和类型均未扩展 |

---

## 六、测试详细结果

### 6.1 后端单元测试

```
263 passed in 0.81s
```

包含：
- `tests/test_python_processor.py` — 3 个测试全部通过
  - `test_python_processor_registered` ✅
  - `test_python_processor_executes_script` ✅
  - `test_python_processor_missing_process_fn` ✅

### 6.2 前端单元测试

```
113 passed in 1.68s
```

TypeScript 编译 0 errors — discriminated union 类型安全验证通过。

### 6.3 后端 API 测试

| 测试 | 状态 | 说明 |
|------|------|------|
| Python Processor Dry Run | ❌ 422 | `script` 字段为空，验证失败 |
| Mixed SQL+Python Pipeline | ❌ 422 | 同上 |
| Python Error Handling | ✅ | 正确返回 422 + "必须定义 process" |
| Python Syntax Error | ✅ | 正确返回 422 |
| YAML Generation with Python | ❌ 422 | 同 P0 问题 |

### 6.4 前端 UI 测试

| 测试 | 状态 | 说明 |
|------|------|------|
| "+ Python 步骤" 按钮存在 | ✅ | 橙色 warning 按钮 |
| 点击后创建 Python 卡片 | ✅ | NTag 显示 "Python" |
| Python 脚本 textarea | ✅ | placeholder 包含 `process(ctx)` |
| 填写 Python 脚本 | ✅ | 值正确设置 |
| Python 卡片无 SQL 元素 | ✅ | 无 SQL placeholder |
| Python 卡片有输出表名字段 | ✅ | 包含所有必要字段 |
| SQL + Python 步骤共存 | ✅ | 两种卡片正确渲染 |
| 预览按钮存在 | ✅ | "▶ 预览结果" |
| AI 生成按钮存在 | ✅ | "✨ AI 生成" |
| AI 生成按钮功能 | ❌ | 点击无反应（P1） |

---

## 七、修复优先级

| 优先级 | 问题 | 修复工作量 |
|--------|------|-----------|
| 🔴 P0 | 前端序列化格式与后端模型不匹配 | 小（修改 `serialization.ts` 约 5 行） |
| 🟡 P1 | AI 生成按钮无功能 | 中（需实现 AI 生成 Python 脚本或移除按钮） |
| 🟡 P2 | OrchestrationResult 硬编码 SQL | 小（修改类型定义 + 组件约 10 行） |
| 🟡 P3 | AI 编排 prompt 仅支持 SQL | 中（修改 prompt + 后端解析约 20 行） |
| 🟢 P4 | `as` 类型断言 | 极小（1 行） |
| 🟢 P5 | Python 步骤名称自动推断 | 小（约 10 行） |
| 🟢 P6 | Python 输出表名自动推断 | 小（约 15 行） |

**建议修复顺序**: P0 → P1 → P2 → P3 → P4-P6

---

## 八、结论

Python 处理器功能的**核心实现已完成**，后端 PipeForge 层（插件注册、exec 执行、超时控制、YAML 序列化）和前端 UI 层（discriminated union 类型、Python 卡片、按钮栏）均已正确实现。

但存在一个**阻断性 Bug**（P0）：前端序列化将 `script` 放入嵌套 `config` 对象，而后端 `ProcessorConfig` 是扁平结构，导致所有 Python 步骤的 API 调用返回 422。此问题修复量极小（约 5 行代码），修复后 Python 步骤功能即可正常使用。

其余 3 个重要问题（AI 生成按钮、编排结果展示、编排 prompt）属于功能增强，不影响 Python 步骤的手动创建和执行，可在后续迭代中修复。
