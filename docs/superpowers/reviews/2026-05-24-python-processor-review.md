# ConfigForge Python 处理器设计审核报告

**审核日期**: 2026-05-24
**审核文档**: `docs/superpowers/specs/2026-05-24-python-processor-design.md`
**审核结论**: **有条件可行** — 方向正确，但存在 3 个阻断性问题、5 个重要问题需修改后才能实施

---

## 一、总体评价

| 维度 | 评分 | 说明 |
|------|------|------|
| 方向正确性 | ★★★★★ | Python 处理器是 SQL 的自然扩展，用户需求真实 |
| 架构兼容性 | ★★★★☆ | 插件体系天然支持扩展，但 discriminated union 改动需谨慎 |
| API 设计 | ★★★☆☆ | ctx API 过于简陋，缺少关键能力 |
| 安全性 | ★★☆☆☆ | 信任模型可接受，但缺少基本防护 |
| 前端方案 | ★★☆☆☆ | 过于粗略，缺少关键交互细节 |
| 改动清单 | ★★★☆☆ | 遗漏多个必要文件和逻辑 |
| 可行性 | ★★★★☆ | 核心路径可行，但工作量被低估约 40% |

---

## 二、阻断性问题（必须修改）

### 🔴 P1：`ProcessorSpec.config` 的 discriminated union 扩展方式有误

**现状**：PipeForge 的 [models.py](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/config/models.py) 中：

```python
class ProcessorSpec(BaseModel):
    config: Annotated[SqlProcessorConfig, Field(discriminator="type")]
```

当前 `config` 是单一类型 `SqlProcessorConfig`，discriminated union 尚未形成。设计文档说"扩展 `ProcessorSpec.config` union"，但没给出具体改法。

**问题**：
1. 直接改为 `SqlProcessorConfig | PythonProcessorConfig` 需要同步修改 `_inject_type_defaults()` 函数（[config/__init__.py](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/config/__init__.py) 第 28-30 行），否则旧 YAML 无 `type` 字段时默认注入逻辑会出错
2. `ProcessorSpec.plugin` 字段与 `config.type` 存在语义重叠 — 当前 SQL 处理器的 `plugin="sql"` 和 `config.type="sql"` 是同一个值，Python 处理器也会出现 `plugin="python"` 和 `config.type="python"` 重复
3. ConfigForge 后端 [wizard.py](file:///Users/lixinyuan/code/CCTEST/configforge/models/wizard.py) 的 `ProcessorConfig` 也有独立的 `plugin` 字段，需要同步扩展

**建议**：
- 明确 `plugin` 和 `config.type` 的关系：`plugin` 决定使用哪个插件类，`config.type` 决定配置模型反序列化方式，两者必须一致
- 在 `_inject_type_defaults()` 中添加 Python 类型的默认注入逻辑
- 给出 `PythonProcessorConfig` 的完整 Pydantic 模型定义，包括字段校验

### 🔴 P2：ctx API 缺少关键能力，设计过于简陋

**当前设计**：

```python
def process(ctx):
    ctx.db      # SQLite 连接
    ctx.params  # 运行时参数
    ctx.logger  # 日志
```

**缺失的关键 API**：

| 缺失 API | 影响 | 严重程度 |
|---------|------|---------|
| `ctx.db.query()` 返回值类型 | 设计中 `rows = ctx.db.query(...)` 但当前 `SQLiteManager` 没有 `query` 方法，只有 `execute` | 🔴 阻断 |
| `ctx.db.execute()` 签名 | 当前 `SQLiteManager.execute()` 执行的是单条 SQL，Python 用户需要执行多条 SQL | 🟡 重要 |
| `ctx.db` 暴露原始连接 | 当前 `SQLiteManager` 封装了 `_conn`，Python 用户需要直接操作 `sqlite3.Connection` | 🟡 重要 |
| 错误处理/异常传播 | 设计未说明 Python 脚本抛异常时引擎如何处理 | 🟡 重要 |
| 返回值约定 | `process(ctx)` 返回什么？如何声明输出表？ | 🔴 阻断 |

**建议**：重新设计 ctx API，至少包含：

```python
def process(ctx):
    # 数据库操作
    conn = ctx.db.connection   # 原始 sqlite3.Connection
    conn.execute("CREATE TABLE result AS ...")

    # 或高级 API
    rows = ctx.db.query("SELECT * FROM person")  # 返回 list[dict]
    ctx.db.execute("CREATE TABLE result AS ...")

    # 输出表声明（必须）
    ctx.declare_output("result")  # 或通过 output_tables YAML 字段

    # 参数
    threshold = ctx.params.get("min_age", 18)

    # 日志
    ctx.logger.info(f"处理了 {len(rows)} 行")
```

关键决策点：
1. **`ctx.db` 暴露什么？** 建议暴露原始 `sqlite3.Connection`，Python 用户自行操作，最灵活
2. **输出表如何声明？** 两种方案：(a) YAML `output_tables` 字段声明（与 SQL 一致）；(b) Python 代码中 `ctx.declare_output()` 动态声明。建议用 (a)，保持一致性
3. **异常如何处理？** 建议捕获异常后记录到 `ExecutionResult`，标记该步骤失败，停止后续步骤

### 🔴 P3：Python 代码执行实现方案未设计

**设计文档**只说了"信任执行"模型，但完全没有给出实现方案。这是核心功能，不能留空。

**需要回答的问题**：

1. **如何加载用户代码？**
   - 方案 A：`exec(script, {"ctx": ctx})` — 简单但无法调试
   - 方案 B：`exec(script, restricted_globals)` — 可控制全局命名空间
   - 方案 C：写入临时 .py 文件后 `importlib` 加载 — 可调试但复杂

2. **如何调用 `process(ctx)` 入口函数？**
   - `exec` 后从局部命名空间取出 `process` 函数再调用
   - 需要校验 `process` 函数存在且可调用

3. **超时控制？**
   - Python 代码可能死循环，需要 `signal.alarm` 或 `threading.Timer` 超时机制
   - 设计文档"非目标"中未提及超时，这是必须的

4. **标准输出/错误捕获？**
   - Python 代码中的 `print()` 输出需要重定向到 `ctx.logger`

**建议**：采用方案 B + 超时控制：

```python
class PythonProcessorPlugin(ProcessorPlugin):
    def execute(self, context, config):
        restricted_globals = {
            "__builtins__": {
                "print": lambda *a: context.logger.info(" ".join(str(x) for x in a)),
                "len": len, "range": range, "enumerate": enumerate,
                "dict": dict, "list": list, "set": set, "tuple": tuple,
                "str": str, "int": int, "float": float, "bool": bool,
                "sorted": sorted, "reversed": reversed, "zip": zip,
                "map": map, "filter": filter, "sum": sum, "min": min, "max": max,
                "abs": abs, "round": round, "isinstance": isinstance,
                "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError,
                "RuntimeError": RuntimeError,
            },
        }
        local_ns = {}
        exec(config.script, restricted_globals, local_ns)

        process_fn = local_ns.get("process")
        if not process_fn or not callable(process_fn):
            raise ValueError("Python 脚本必须定义 process(ctx) 函数")

        # 超时控制
        import signal
        def timeout_handler(signum, frame):
            raise TimeoutError("Python 脚本执行超时")
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 秒超时

        try:
            process_fn(context)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
```

---

## 三、重要问题（应当修改）

### 🟡 P4：前端 `ProcessorStep` 类型扩展不完整

**当前** [wizard.ts](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/types/wizard.ts)：

```typescript
export interface ProcessorStep {
  name: string
  plugin: 'sql'
  sql: string
  inputTables: string[]
  outputTables: string[]
}
```

**问题**：
1. `plugin` 需扩展为 `'sql' | 'python'`
2. Python 步骤没有 `sql` 字段，需要 `script` 字段
3. 当前 `ProcessorStep` 是扁平结构，SQL 和 Python 字段混在一起会导致类型不安全

**建议**：使用 discriminated union：

```typescript
export type ProcessorStep =
  | {
      name: string
      plugin: 'sql'
      sql: string
      inputTables: string[]
      outputTables: string[]
    }
  | {
      name: string
      plugin: 'python'
      script: string
      inputTables: string[]
      outputTables: string[]
    }
```

这样 TypeScript 可以通过 `step.plugin` 自动推断可用字段。但这会影响大量现有代码（`ProcessorCard.vue`、`wizard store`、`yaml_builder.py` 等），需要评估改动范围。

### 🟡 P5：`ProcessorCard.vue` 需要支持双模式，改动量被低估

**当前** [ProcessorCard.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/ProcessorCard.vue) 是纯 SQL 卡片，硬编码了：
- `<NTag size="tiny" type="info">SQL</NTag>` — 类型标签
- SQL textarea 编辑器
- SQL 预览执行逻辑
- AI 生成 SQL 功能

**Python 卡片需要**：
- 类型标签 `<NTag size="tiny" type="warning">Python</NTag>`
- Python 代码编辑器（语法不同，placeholder 不同）
- Python 预览执行逻辑（需要新的后端 API）
- AI 生成 Python 代码功能（设计文档说非目标，但用户会期望）

**建议**：两种方案：
- **方案 A**：`ProcessorCard.vue` 内部通过 `v-if="proc.plugin === 'sql'"` / `v-if="proc.plugin === 'python'"` 分支渲染 — 简单但文件膨胀
- **方案 B**：抽取 `SqlProcessorContent.vue` 和 `PythonProcessorContent.vue` 作为子组件 — 更清晰但文件更多

推荐方案 B，保持组件职责单一。

### 🟡 P6：YAML 序列化需要处理 Python 脚本的多行字符串

**当前** [yaml_builder.py](file:///Users/lixinyuan/code/CCTEST/configforge/services/yaml_builder.py) 中 SQL 序列化：

```python
"config": {"type": "sql", "sql": proc.sql}
```

Python 脚本通常有多行，YAML 中需要使用 `|` 块标量：

```yaml
config:
  type: python
  script: |
    def process(ctx):
        ctx.db.execute('CREATE TABLE adults AS ...')
```

**问题**：当前 `yaml.dump()` 默认可能将多行字符串序列化为引号包裹的单行（`"def process(ctx):\n    ..."`），可读性极差。

**建议**：对 `script` 字段使用 `yaml.dump` 的多行字符串处理，或手动控制序列化格式。

### 🟡 P7：Python 步骤的预览执行需要新的后端 API

**当前** SQL 步骤有 `/api/sql/execute` 用于预览执行。Python 步骤需要类似能力，但设计文档未提及。

**需要新增**：
- `POST /api/python/execute` — 接受 Python 脚本 + 输入表映射，返回执行结果
- 后端需要在临时 SQLite 上执行 Python 代码，返回输出表数据
- 需要超时控制和错误捕获

### 🟡 P8：改动文件清单遗漏

| 遗漏文件 | 遗漏原因 |
|---------|---------|
| `src/pipeforge/config/__init__.py` | `_inject_type_defaults()` 需添加 Python 类型默认注入 |
| `configforge/api/` 相关路由 | Python 预览执行 API |
| `configforge-web/src/composables/useWizardApi.ts` | Python 预览执行 composable |
| `configforge-web/src/components/step3/PythonProcessorContent.vue` | Python 卡片内容组件（如果采用方案 B） |
| `configforge-web/src/components/step3/ProcessorCard.vue` | 需要支持双模式渲染 |
| `configforge-web/src/utils/sql.ts` | `inferOutputTable` / `inferStepName` 需要支持 Python |
| 测试文件 | PipeForge Python 插件测试、ConfigForge YAML 序列化测试、前端 Python 卡片测试 |

---

## 四、轻微问题（可以优化）

### 🟢 P9：信任模型需要文档化边界

"信任执行"意味着 Python 代码可以：
- 访问文件系统（`open()`, `os`）
- 执行系统命令（`subprocess`）
- 访问网络（`urllib`, `requests`）
- 导入任意模块

设计文档说"非目标"中排除网络和文件系统访问，但"信任执行"模型与这个约束矛盾。如果真的信任，就不需要约束；如果需要约束，就不是信任模型。

**建议**：二选一：
1. 真正的信任模型：不限制任何操作，在文档中明确说明风险
2. 受限执行模型：通过 `__builtins__` 白名单限制危险操作（如 P3 建议的实现）

### 🟢 P10：Python 代码编辑器体验

设计文档说"后续按需升级为 Monaco Editor"，但 `<NInput type="textarea">` 对 Python 代码编辑体验极差：
- 无语法高亮
- 无自动缩进
- 无括号匹配
- 无代码补全

**建议**：v0.4.0 至少支持基本的 Python 语法高亮（可用 `highlight.js`，项目已依赖），Monaco Editor 作为 v0.4.1 目标。

### 🟢 P11：AI 编排生成 Python 步骤

设计文档将"AI 编排生成 Python 步骤"列为非目标，但 v0.3.1 的 AI 编排功能已经能生成 SQL 步骤链。如果 Python 步骤不支持 AI 编排，用户在混合链中会有体验断裂。

**建议**：v0.4.0 至少支持 AI 编排在需要复杂逻辑时生成 Python 步骤（而非 SQL 步骤），v0.4.1 完善混合链编排。

---

## 五、与现有代码的兼容性分析

### 5.1 PipeForge 层

| 组件 | 兼容性 | 改动量 |
|------|--------|--------|
| 插件注册机制 | ✅ 天然兼容 | `@register_plugin("python", "processor")` 即可 |
| `ProcessorPlugin` 基类 | ✅ 兼容 | 继承即可 |
| `ProcessorSpec.config` | ⚠️ 需改为 union | 中等 |
| `_inject_type_defaults()` | ⚠️ 需添加 Python 分支 | 小 |
| 引擎拓扑排序 | ✅ 不受影响 | 无 |
| `_execute_processor()` | ✅ 不受影响 | 通过插件注册自动路由 |

### 5.2 ConfigForge 层

| 组件 | 兼容性 | 改动量 |
|------|--------|--------|
| `ProcessorConfig` (wizard.py) | ⚠️ 需扩展 plugin 和 config | 中等 |
| `yaml_builder.py` | ⚠️ 需添加 Python 序列化 | 中等 |
| API 路由 | ⚠️ 需新增 Python 执行端点 | 大 |

### 5.3 Frontend 层

| 组件 | 兼容性 | 改动量 |
|------|--------|--------|
| `ProcessorStep` 类型 | ⚠️ 需改为 union | 大（影响所有引用处） |
| `wizard store` | ⚠️ `addProcessor` / `setProcessors` / `canProceed` 都需改 | 大 |
| `ProcessorCard.vue` | ⚠️ 需支持双模式 | 大 |
| `SqlEditorTab.vue` | ⚠️ 需添加 "+ Python 步骤" 按钮 | 中等 |
| AI 编排 | ⚠️ 编排结果 `OrchestrationStep.sql` 需支持 `script` | 中等 |

---

## 六、建议的修改优先级

### 第一优先级（阻断 — 必须修改后才能开发）

1. **补全 `PythonProcessorConfig` 模型定义** — 给出完整 Pydantic 模型
2. **重新设计 ctx API** — 明确 `ctx.db` 暴露什么、输出表如何声明、异常如何传播
3. **给出 Python 代码执行实现方案** — `exec` + 受限全局命名空间 + 超时控制

### 第二优先级（重要 — 影响开发质量）

4. **`ProcessorStep` 改为 discriminated union** — 类型安全
5. **补全改动文件清单** — 至少遗漏 7 个文件
6. **新增 Python 预览执行 API** — 前端预览功能依赖
7. **YAML 多行字符串处理** — Python 脚本可读性

### 第三优先级（优化 — 可后续迭代）

8. Python 代码语法高亮
9. AI 编排支持 Python 步骤
10. 信任模型边界文档化

---

## 七、结论

设计方向正确，Python 处理器是 ConfigForge 的自然演进。但当前设计文档过于粗略，**核心实现方案（Python 代码执行机制、ctx API、前端双模式渲染）均未给出具体方案**，直接进入开发会遇到大量设计决策点。

**建议**：修改设计文档，补全 P1-P3 三个阻断性问题的具体方案后，再进入开发阶段。预计补全设计需要额外 1-2 天，但可以避免开发过程中的返工。
