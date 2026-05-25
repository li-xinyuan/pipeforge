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
