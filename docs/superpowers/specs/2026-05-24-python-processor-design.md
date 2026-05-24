# ConfigForge Python 处理器 v0.4.0 设计

> 日期: 2026-05-24（审查修订）
> 当前基线: v0.3.1（SQL 多步管道 + AI 编排）

---

## 一、目标

新增 Python Processor，用户可编写 Python 脚本作为处理步骤，与 SQL 步骤在 DAG 中自由串联。

---

## 二、执行模型与实现方案（P3）

### 2.1 加载与执行

采用 `exec()` + 受限 `__builtins__` + `signal.alarm` 超时：

```python
class PythonProcessorPlugin(ProcessorPlugin):
    """Python 代码处理器 — 信任执行模型。"""

    TIMEOUT_SECONDS = 30

    @classmethod
    def config_model(cls):
        return PythonProcessorConfig

    def execute(self, context, config: PythonProcessorConfig):
        # 受限内置函数 + print → logger 重定向
        restricted_builtins = {
            "print": lambda *a: context.logger.info(" ".join(str(x) for x in a)),
            "len": len, "range": range, "enumerate": enumerate,
            "dict": dict, "list": list, "set": set, "tuple": tuple,
            "str": str, "int": int, "float": float, "bool": bool,
            "sorted": sorted, "reversed": reversed, "zip": zip,
            "sum": sum, "min": min, "max": max, "abs": abs, "round": round,
            "isinstance": isinstance, "hasattr": hasattr, "getattr": getattr,
            "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError,
            "RuntimeError": RuntimeError, "Exception": Exception,
        }

        globals_ns = {"__builtins__": restricted_builtins}
        local_ns = {}
        exec(config.script, globals_ns, local_ns)

        process_fn = local_ns.get("process")
        if not process_fn or not callable(process_fn):
            raise ValueError("Python 脚本必须定义 process(ctx) 函数")

        # 超时控制
        import signal
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Python 脚本执行超时（{self.TIMEOUT_SECONDS}秒）")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.TIMEOUT_SECONDS)
        try:
            process_fn(context)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
```

### 2.2 信任边界

"信任执行"意味着 Python 代码可以使用任意 Python 语法和导入任意模块。这对内部工具是可接受的。同时通过受限 `__builtins__` 降低误操作风险。

---

## 三、ctx API（P2）

### 3.1 暴露能力

Python 脚本通过 `context` 参数（PipeForge 的 `Context` 对象）与管道交互：

```python
def process(ctx):
    # ctx.db — SQLiteManager 实例
    conn = ctx.db.connection        # 原始 sqlite3.Connection（最灵活）
    ctx.db.execute("SQL ...")       # 执行 SQL
    ctx.db.list_tables()            # 列出所有表
    ctx.db.query("SELECT ...")      # 返回 list[tuple]（当前方法）

    # ctx.params — dict[str, str]，运行时参数
    threshold = int(ctx.params.get("min_age", 18))

    # ctx.yaml_dir — str，YAML 所在目录（读参考文件）
    # ctx.scene_name — str，场景名称
    # ctx.logger — Logger 实例
    ctx.logger.info("处理完成")
    ctx.logger.error("处理失败")
```

**关键决策：**
- `ctx.db.connection` 暴露原始 `sqlite3.Connection`，Python 用户可直接使用完整的 SQLite API
- 输出表通过 YAML 的 `output_tables` 声明（与 SQL 步骤一致），无需 `ctx.declare_output()`
- Python 脚本通过 `CREATE TABLE` 写入数据（与 SQL Processor 模式一致）

### 3.2 异常传播

Python 脚本抛出异常时：引擎捕获 → 记录到 `ExecutionResult` → 标记该步骤失败 → 停止后续步骤。`try/finally` 确保数据库连接正确关闭。

---

## 四、PipeForge 模型（P1）

### 4.1 PythonProcessorConfig

```python
# src/pipeforge/config/models.py

class PythonProcessorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["python"] = "python"
    script: str

    @field_validator("script")
    @classmethod
    def script_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("script must not be empty")
        return v
```

### 4.2 ProcessorSpec 扩展

```python
class ProcessorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    plugin: str
    input_tables: list[str] = []
    output_tables: list[str] = []
    config: Annotated[SqlProcessorConfig | PythonProcessorConfig, Field(discriminator="type")]
```

**`plugin` vs `config.type` 关系**：`plugin` 决定使用哪个插件类（`PluginRegistry.get("python", "processor")`），`config.type` 决定配置模型的 discriminator。两者必须一致——`plugin="python"` 则 `config.type="python"`。

### 4.3 _inject_type_defaults 更新

```python
# src/pipeforge/config/__init__.py

def _inject_type_defaults(config_dict: dict, plugin: str) -> None:
    if plugin == "sql" and "type" not in config_dict:
        config_dict["type"] = "sql"
    elif plugin == "python" and "type" not in config_dict:
        config_dict["type"] = "python"
```

---

## 五、前端类型（P4）

`ProcessorStep` 改为 discriminated union：

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

---

## 六、前端 UI（P5）

### 6.1 组件拆分

采用方案 B——抽取子组件：

```
src/components/step3/
├── ProcessorCard.vue        # 卡片容器（类型标签、展开/删除）【修改】
├── SqlProcessorContent.vue  # SQL 编辑器区域（已有逻辑）【抽取】
└── PythonProcessorContent.vue # Python 编辑器区域【新建】
```

`ProcessorCard.vue` 通过 `v-if="proc.plugin === 'sql'"` / `v-else-if="proc.plugin === 'python'"` 渲染对应子组件。

### 6.2 Python 代码编辑器

用 `<NInput type="textarea">` + `highlight.js` 做基本语法高亮（项目已依赖 highlight.js）。

### 6.3 按钮栏

Step 3 新增"+ Python 步骤"按钮（橙色边框），与"+ SQL 步骤"并列。

---

## 七、YAML 序列化（P6）

Python 脚本使用 YAML `|` 块标量：

```python
# yaml_builder.py
elif proc.plugin == "python":
    d["processors"].append({
        "name": proc.name or f"step_{i+1}",
        "plugin": "python",
        "input_tables": proc.input_tables,
        "output_tables": proc.output_tables,
        "config": {"type": "python", "script": proc.script},
    })
```

YAML 库会自动将多行字符串序列化为块标量格式。

---

## 八、预览执行 API（P7）

复用现有 dry-run 端点。Python 步骤的预览执行通过 `/api/wizard/dry-run` 走完整管道（与 SQL 一致），无需单独 API。`execute_dry_run()` 方法调用 `PythonProcessorPlugin` 执行脚本。

---

## 九、改动清单（P8 补全后）

| 层 | 文件 | 改动 |
|-----|------|------|
| PipeForge | `src/pipeforge/config/models.py` | 新增 `PythonProcessorConfig`，`ProcessorSpec.config` → union |
| PipeForge | `src/pipeforge/config/__init__.py` | `_inject_type_defaults` 添加 python 分支 |
| PipeForge | `src/pipeforge/plugins/processor/python.py` | **新建** Python Processor（exec + timeout + restricted builtins） |
| ConfigForge | `configforge/models/wizard.py` | `ProcessorConfig.plugin` 扩展 `"python"` |
| ConfigForge | `configforge/services/yaml_builder.py` | Python 步骤序列化 |
| Frontend | `configforge-web/src/types/wizard.ts` | `ProcessorStep` → discriminated union |
| Frontend | `configforge-web/src/stores/wizard.ts` | `addProcessor("python")`，`canProceed` 适配 |
| Frontend | `configforge-web/src/components/step3/ProcessorCard.vue` | 抽取内容，`v-if` 分支渲染 |
| Frontend | `configforge-web/src/components/step3/SqlProcessorContent.vue` | **新建** SQL 编辑器子组件（从 ProcessorCard 抽取） |
| Frontend | `configforge-web/src/components/step3/PythonProcessorContent.vue` | **新建** Python 编辑器子组件 |
| Frontend | `configforge-web/src/components/step3/SqlEditorTab.vue` | 新增"+ Python 步骤"按钮 |
| Frontend | `configforge-web/src/utils/serialization.ts` | `stateToSnakeCase` 适配 discriminated union |
| 测试 | `tests/test_python_processor.py` | Python 插件测试 |
| 测试 | `configforge/tests/test_yaml_builder.py` | Python 步骤 YAML 序列化 |
| 测试 | `configforge-web/tests/...` | Python 卡片渲染测试 |

---

## 十、非目标

- 沙箱/安全隔离（采用信任模型 + 受限 builtins）
- Monaco Editor 代码编辑器（v0.4.1）
- AI 编排生成 Python 步骤（v0.4.1，先支持 SQL 编排）
- Python 步骤独立预览 API（复用 dry-run）

---

## 十一、验证策略

- PipeForge：Python 插件注册、exec 超时、异常传播
- ConfigForge：YAML Python 步骤序列化/反序列化
- Frontend：Python 卡片渲染、与 SQL 步骤混合链、预览结果保持一致
- 全量回归：现有 257 backend + 113 frontend tests
