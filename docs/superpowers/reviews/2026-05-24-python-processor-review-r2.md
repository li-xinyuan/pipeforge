# ConfigForge Python 处理器设计审核报告（第二轮）

**审核日期**: 2026-05-24
**审核文档**: `docs/superpowers/specs/2026-05-24-python-processor-design.md`（修订版）
**对比基线**: 第一轮审核报告 `docs/superpowers/reviews/2026-05-24-python-processor-review.md`
**审核结论**: **基本可行** — 上轮 3 个阻断性问题已解决，仍有 2 个重要问题 + 4 个遗漏需补充

---

## 一、上轮问题修复状态

| 上轮问题 | 严重程度 | 修复状态 | 评价 |
|---------|---------|---------|------|
| P1: ProcessorSpec union 扩展方式 | 🔴 阻断 | ✅ 已修复 | 给出了完整的 `PythonProcessorConfig` + union 改法 + `_inject_type_defaults` 更新 |
| P2: ctx API 缺失 | 🔴 阻断 | ✅ 已修复 | 明确了 `ctx.db.connection` 暴露原始连接、输出表通过 YAML 声明、异常传播机制 |
| P3: 执行实现方案空白 | 🔴 阻断 | ✅ 已修复 | 给出了 `exec()` + 受限 builtins + `signal.alarm` 超时的完整实现代码 |
| P4: ProcessorStep 类型 | 🟡 重要 | ✅ 已修复 | 改为 discriminated union |
| P5: ProcessorCard 双模式 | 🟡 重要 | ✅ 已修复 | 采用方案 B 组件拆分 |
| P6: YAML 多行字符串 | 🟡 重要 | ✅ 已修复 | 说明 YAML 库自动处理 |
| P7: 预览执行 API | 🟡 重要 | ✅ 已修复 | 复用 dry-run 端点 |
| P8: 改动清单遗漏 | 🟡 重要 | ⚠️ 部分修复 | 补充了部分文件，仍有遗漏（见下文） |

**总体**：上轮 8 个问题中 6 个完全修复，2 个部分修复。设计质量显著提升。

---

## 二、新发现的问题

### 🟡 重要问题 1：`pipeline.py` 中 SQL 自动包装逻辑不适用于 Python 步骤

**现状**：[pipeline.py](file:///Users/lixinyuan/code/CCTEST/configforge/core/pipeline.py) 第 82-93 行和第 217-222 行有两处 SQL 自动包装逻辑：

```python
for proc in _get_processors(exec_state):
    if proc.output_tables and proc.sql.strip():
        if not _has_ddl(proc.sql):
            output_table = proc.output_tables[0].replace('"', '')
            proc.sql = (
                f'CREATE TABLE "{output_table}" AS '
                f"SELECT * FROM ({proc.sql})"
            )
```

这段代码对**所有处理器**都执行 SQL 包装，但 Python 步骤的 `proc.sql` 字段不存在（改为 `proc.script`），且 Python 步骤不需要 SQL 自动包装。

**影响**：
- `dry_run()` 和 `execute_pipeline()` 都会崩溃（`AttributeError: 'ProcessorConfig' object has no attribute 'sql'` 当 plugin=python 时）
- 这是运行时阻断问题

**建议**：在 `_get_processors` 循环中添加 `plugin` 判断：

```python
for proc in _get_processors(exec_state):
    if proc.plugin == "python":
        continue  # Python 步骤不需要 SQL 自动包装
    if proc.output_tables and proc.sql.strip():
        if not _has_ddl(proc.sql):
            ...
```

改动清单中需要添加 `configforge/core/pipeline.py`。

### 🟡 重要问题 2：`serialization.ts` 的 `stateToSnakeCase` 硬编码了 SQL

**现状**：[serialization.ts](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/utils/serialization.ts) 第 103-107 行：

```typescript
processors: state.processors.map((p) => ({
  name: p.name,
  plugin: p.plugin,
  input_tables: p.inputTables,
  output_tables: p.outputTables,
  config: { type: 'sql', sql: p.sql },  // ← 硬编码 SQL
})),
```

改为 discriminated union 后，`p.sql` 在 Python 步骤中不存在，需要根据 `p.plugin` 分支处理：

```typescript
processors: state.processors.map((p) => {
  const base = {
    name: p.name,
    plugin: p.plugin,
    input_tables: p.inputTables,
    output_tables: p.outputTables,
  }
  if (p.plugin === 'python') {
    return { ...base, config: { type: 'python', script: p.script } }
  }
  return { ...base, config: { type: 'sql', sql: p.sql } }
}),
```

设计文档改动清单中提到了 `serialization.ts`，但没有说明具体改法。

### 🟢 遗漏 1：`wizard.ts` store 中大量 `.sql` 引用需适配

**受影响位置**（共 6 处）：

| 文件 | 行号 | 代码 | 问题 |
|------|------|------|------|
| `stores/wizard.ts` | 20 | `p.sql.trim().length > 0` | `canProceed` 校验 |
| `stores/wizard.ts` | 33 | `p.sql.trim()` | `stepValidation` 校验 |
| `stores/wizard.ts` | 75 | `p.sql.trim()` | `setProcessors` 过滤 |
| `stores/wizard.ts` | 9 | `{ ..., sql: '', ... }` | `addProcessor` 默认值 |
| `stores/wizard.ts` | 141 | `raw.config?.sql \|\| raw.sql \|\| ''` | `loadFromConfigState` 反序列化 |
| `stores/wizard.ts` | 100 | `{ name: '', plugin: 'sql', sql: '', ... }` | `resetAll` 默认值 |

改为 discriminated union 后，TypeScript 编译器会在每个 `p.sql` 处报错（因为 Python 步骤没有 `sql` 字段）。需要：
- `canProceed` / `stepValidation` 改为 `p.plugin === 'sql' ? p.sql.trim() : p.script.trim()`
- `addProcessor` 需要支持 `addProcessor('python')` 生成 `{ plugin: 'python', script: '', ... }`
- `loadFromConfigState` 需要处理 Python 步骤的反序列化

### 🟢 遗漏 2：`ConfigWizardView.vue` 中 `.sql` 引用需适配

**受影响位置**（共 5 处）：

| 行号 | 代码 | 问题 |
|------|------|------|
| 113 | `store.processors.some(p => !p.sql.trim()` | Step 3 脉冲 CTA |
| 122 | `store.processors.every(p => p.sql.trim()` | Step 3 保存按钮 disabled |
| 123-124 | `store.processors.some(p => !p.sql.trim())` | 校验消息 |
| 263 | `store.processors.every(p => !p.sql.trim())` | AI 提示显示条件 |
| 373 | `store.processors.map(p => p.sql)` | AI 上下文构建 |

### 🟢 遗漏 3：`ExportActions.vue` 中 `.sql` 引用需适配

[ExportActions.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step4/ExportActions.vue) 第 101 行：

```typescript
processors: store.processors.map(p => ({
  plugin: p.plugin,
  sql: p.sql,  // ← Python 步骤没有 sql 字段
  ...
})),
```

### 🟢 遗漏 4：`onOrchestrateConfirm` 硬编码 `plugin: 'sql'`

[ConfigWizardView.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/views/ConfigWizardView.vue) 第 552-563 行：

```typescript
function onOrchestrateConfirm(result: any) {
  const processors = result.steps.map((s: any, i: number) => {
    return {
      name: s.name || `步骤 ${i + 1}`,
      plugin: 'sql' as const,  // ← 硬编码 SQL
      sql: s.sql || '',
      ...
    }
```

v0.4.0 非目标中说不支持 AI 编排 Python 步骤，但这段代码未来需要扩展。建议预留 `s.plugin || 'sql'` 的写法。

---

## 三、设计细节审查

### 3.1 执行模型 — 信号量方案的平台兼容性 ⚠️

`signal.SIGALRM` 仅在 Unix/macOS 上可用，**Windows 不支持**。如果 ConfigForge 未来需要在 Windows 上运行，这个方案会直接报 `AttributeError`。

**建议**：添加平台检测，Windows 使用 `threading.Timer` 替代：

```python
import sys
if sys.platform != "win32":
    import signal
    # signal.alarm 方案
else:
    # threading.Timer 方案
```

或者直接使用 `multiprocessing` + 超时，跨平台兼容性更好。

### 3.2 `ctx.db.connection` 暴露原始连接 — 线程安全风险 ⚠️

当前 `SQLiteManager._conn` 是单个 `sqlite3.Connection`，Python 步骤直接操作这个连接时，如果用户代码中执行了未提交的写操作，可能影响后续步骤的数据一致性。

**建议**：在 Python 步骤执行后，自动执行 `ctx.db._conn.commit()` 确保数据持久化。可以在 `PythonProcessorPlugin.execute()` 的 `finally` 块中添加。

### 3.3 受限 `__builtins__` 的绕过方式 ⚠️

当前受限 builtins 白名单中没有 `__import__`，用户无法 `import os` 等模块。但 Python 有多种方式绕过：

```python
# 绕过方式 1：通过已有对象访问 __class__.__bases__ 等
().__class__.__bases__[0].__subclasses__()

# 绕过方式 2：通过 getattr 访问
getattr(getattr((), '__class__'), '__bases__')
```

设计文档说"信任执行"，但又用了受限 builtins，这两个理念矛盾。如果真的信任，就不需要受限；如果需要限制，当前方案不够安全。

**建议**：二选一：
1. **纯信任模型**：不限制 `__builtins__`，在文档中明确说明风险
2. **受限模型**：移除 `getattr`/`hasattr`/`isinstance`，添加 `__import__` 白名单（只允许 `import sqlite3, json, re, math, datetime, collections`）

推荐方案 1（纯信任），因为当前用户场景是内部工具。

### 3.4 `ProcessorConfig` 后端模型需要同步扩展

设计文档改动清单提到了 `configforge/models/wizard.py` 的 `ProcessorConfig.plugin` 扩展，但没有给出 `ProcessorConfig` 的完整新定义。

**当前**：

```python
class ProcessorConfig(BaseModel):
    plugin: Literal["sql"] = "sql"
    sql: str
    input_tables: list[str] = []
    output_tables: list[str] = []
```

**需要改为**：

```python
class ProcessorConfig(BaseModel):
    plugin: Literal["sql", "python"] = "sql"
    sql: str = ""           # SQL 步骤必填
    script: str = ""        # Python 步骤必填
    input_tables: list[str] = []
    output_tables: list[str] = []
```

或者也改为 discriminated union（与前端一致）。但后端用扁平结构更简单，因为 `wizard.py` 的模型主要用于 API 序列化，不需要 Pydantic 的 discriminator 做反序列化。

### 3.5 YAML 序列化 — `yaml.dump` 多行字符串行为

设计文档说"YAML 库会自动将多行字符串序列化为块标量格式"，这**不完全正确**。PyYAML 的默认行为取决于字符串内容：

```python
yaml.dump({"script": "def process(ctx):\n    pass"})
# 输出: script: "def process(ctx):\n    pass"  ← 引号包裹，非块标量
```

要强制使用块标量，需要自定义 Representer：

```python
class LiteralStr(str): pass

def literal_str_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

yaml.add_representer(LiteralStr, literal_str_representer)
```

或在 `yaml_builder.py` 中对 `script` 字段手动处理。

---

## 四、改动清单补充

设计文档改动清单遗漏了以下文件：

| 遗漏文件 | 原因 |
|---------|------|
| `configforge/core/pipeline.py` | SQL 自动包装逻辑需跳过 Python 步骤 |
| `configforge-web/src/views/ConfigWizardView.vue` | 5 处 `.sql` 引用需适配 |
| `configforge-web/src/components/step4/ExportActions.vue` | `.sql` 引用需适配 |
| `configforge-web/src/components/wizard/OrchestrationResult.vue` | 预留 `plugin` 字段 |
| `configforge-web/src/components/step3/OutputConfigTab.vue` | watch processors `.sql` 需适配 |

---

## 五、总结

| 评估项 | 上轮 | 本轮 | 变化 |
|-------|------|------|------|
| 阻断性问题 | 3 | 0 | ✅ 全部修复 |
| 重要问题 | 5 | 2 | ⬇️ 显著减少 |
| 轻微/遗漏 | 3 | 5 | ⬆️ 细节遗漏暴露 |
| 整体可行性 | 有条件可行 | **基本可行** | ✅ 可进入开发 |

**剩余 2 个重要问题**：
1. `pipeline.py` 的 SQL 自动包装逻辑会崩溃 — 需添加 `plugin` 判断
2. `serialization.ts` 硬编码 SQL — 需分支处理

**5 个遗漏**：主要是前端代码中散落的 `.sql` 引用（共约 16 处），改为 discriminated union 后 TypeScript 编译器会自动报错，开发时可以逐一修复。建议在改动清单中明确列出这些位置，避免遗漏。

**结论**：设计已达到可开发状态。建议开发前先处理 `pipeline.py` 和 `serialization.ts` 两个重要问题，其余遗漏可在开发过程中通过 TypeScript 编译错误逐一发现和修复。
