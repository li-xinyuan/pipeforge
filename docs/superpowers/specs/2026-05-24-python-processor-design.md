# ConfigForge Python 处理器 v0.4.0 设计

> 日期: 2026-05-24（第二轮审查修订）
> 当前基线: v0.3.1（SQL 多步管道 + AI 编排）

---

## 一、目标

新增 Python Processor，用户可编写 Python 脚本作为处理步骤，与 SQL 步骤在 DAG 中自由串联。

---

## 二、执行模型与实现方案

### 2.1 加载与执行

采用 **纯信任模型**：不限制 `__builtins__`，用户可使用任意 Python 语法和模块。通过 `signal.alarm` 做超时控制。

> **信任模型风险文档化**：用户 Python 代码可以访问文件系统、网络、导入任意模块。适用于内部工具/可信团队场景。

```python
class PythonProcessorPlugin(ProcessorPlugin):
    """Python 代码处理器 — 信任执行模型。"""
    TIMEOUT_SECONDS = 30

    @classmethod
    def config_model(cls):
        return PythonProcessorConfig

    def execute(self, context, config: PythonProcessorConfig):
        local_ns = {}
        exec(config.script, {}, local_ns)

        process_fn = local_ns.get("process")
        if not process_fn or not callable(process_fn):
            raise ValueError("Python 脚本必须定义 process(ctx) 函数")

        import sys, signal
        if sys.platform != "win32":
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Python 脚本执行超时（{self.TIMEOUT_SECONDS}秒）")
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.TIMEOUT_SECONDS)

        try:
            process_fn(context)
        finally:
            if sys.platform != "win32":
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            # 确保 Python 脚本中的写操作已提交
            context.db.connection.commit()
```

### 2.2 平台兼容性

`signal.SIGALRM` 仅 Unix/macOS 可用。Windows 跳过超时控制（后续用 `threading.Timer` 补充）。

---

## 三、ctx API

Python 脚本通过 `context` 参数与管道交互：

```python
def process(ctx):
    # ctx.db — SQLiteManager 实例
    conn = ctx.db.connection        # 原始 sqlite3.Connection
    ctx.db.execute("CREATE TABLE result AS ...")
    rows = ctx.db.query("SELECT * FROM person")
    tables = ctx.db.list_tables()

    # ctx.params — dict[str, str]，运行时参数
    threshold = int(ctx.params.get("min_age", 18))

    # ctx.yaml_dir — YAML 所在目录
    # ctx.scene_name — 场景名称
    # ctx.logger — 日志
    ctx.logger.info(f"处理了 {len(rows)} 行")
```

**关键决策**：输出表通过 YAML `output_tables` 声明，Python 脚本通过 `CREATE TABLE` 写入。

---

## 四、PipeForge 模型

### 4.1 PythonProcessorConfig

```python
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
config: Annotated[SqlProcessorConfig | PythonProcessorConfig, Field(discriminator="type")]
```

### 4.3 _inject_type_defaults

```python
def _inject_type_defaults(config_dict: dict, plugin: str) -> None:
    if plugin == "sql" and "type" not in config_dict:
        config_dict["type"] = "sql"
    elif plugin == "python" and "type" not in config_dict:
        config_dict["type"] = "python"
```

### 4.4 pipeline.py SQL 自动包装 — 跳过 Python 步骤

`execute_pipeline()` 和 `dry_run()` 中两处 SQL 自动包装循环需添加 `plugin` 判断：

```python
for proc in _get_processors(exec_state):
    if proc.plugin == "python":
        continue  # Python 步骤不需要 SQL 自动包装
    if proc.output_tables and proc.sql.strip():
        if not _has_ddl(proc.sql):
            ...
```

---

## 五、后端模型（ConfigForge wizard.py）

```python
class ProcessorConfig(BaseModel):
    plugin: Literal["sql", "python"] = "sql"
    name: str = ""
    sql: str = ""
    script: str = ""
    input_tables: list[str] = []
    output_tables: list[str] = []

    @model_validator(mode="after")
    def validate_plugin_fields(self):
        if self.plugin == "sql" and not self.sql.strip():
            raise ValueError("SQL 步骤的 sql 字段不能为空")
        if self.plugin == "python" and not self.script.strip():
            raise ValueError("Python 步骤的 script 字段不能为空")
        return self
```

后端使用扁平结构（非 discriminated union），由 `plugin` 字段区分。

---

## 六、前端类型

### 6.1 ProcessorStep — discriminated union

```typescript
export type ProcessorStep =
  | { name: string; plugin: 'sql'; sql: string; inputTables: string[]; outputTables: string[] }
  | { name: string; plugin: 'python'; script: string; inputTables: string[]; outputTables: string[] }
```

### 6.2 散落的 `.sql` 引用适配（共约 16 处）

| 文件 | 位置 | 适配方式 |
|------|------|---------|
| `stores/wizard.ts:20` | `canProceed` | `p.plugin==='sql'?p.sql.trim():p.script.trim()` |
| `stores/wizard.ts:33` | `stepValidation` | 同上 |
| `stores/wizard.ts:75` | `setProcessors` | 检查 `p.plugin` 分别验证 |
| `stores/wizard.ts:9)` | `addProcessor` | 新增 `addProcessor('python')` |
| `stores/wizard.ts:100` | `resetAll` | 默认 SQL 步骤 |
| `stores/wizard.ts:141` | `loadFromConfigState` | 检查 `raw.plugin` 反序列化 |
| `ConfigWizardView.vue:113` | 脉冲 CTA | `p.plugin==='sql'?p.sql:p.script` |
| `ConfigWizardView.vue:122` | disabled | 同上 |
| `ConfigWizardView.vue:123-124` | 校验消息 | 同上 |
| `ConfigWizardView.vue:263` | AI 提示条件 | `p.plugin==='sql'?!p.sql.trim():!p.script.trim()` |
| `ConfigWizardView.vue:373` | AI 上下文 | `p.plugin=='sql'?p.sql:p.script` |
| `ConfigWizardView.vue:552` | `onOrchestrateConfirm` | `s.plugin \|\| 'sql'` 预留 Python |
| `ExportActions.vue:101` | 保存配置 | `p.plugin=='sql'?{sql:p.sql}:{script:p.script}` |
| `serialization.ts:103-107` | `stateToSnakeCase` | 分支处理 `p.plugin` |
| `OutputConfigTab.vue:235` | watch SQL | `p.plugin==='sql'?p.sql:p.script` |
| `OutputConfigTab.vue:273` | onMounted | `store.processors[0].plugin==='sql'?store.processors[0].sql.trim():store.processors[0].script.trim()` |
| `OutputConfigTab.vue:274` | prevSql | 同上 |
| `OutputConfigTab.vue:320` | 推断 SQL | 同上 |

---

## 七、前端 UI

### 7.1 组件拆分

```
src/components/step3/
├── ProcessorCard.vue           # 卡片容器（v-if 分支渲染）【修改】
├── SqlProcessorContent.vue     # SQL 编辑器【从 ProcessorCard 抽取】
└── PythonProcessorContent.vue  # Python 编辑器【新建】
```

### 7.2 Python 编辑器

`<NInput type="textarea">` + `highlight.js` 语法高亮（项目已有依赖），Monaco Editor 延后至 v0.4.1。

### 7.3 按钮栏

新增"+ Python 步骤"（橙色 `type="warning"`），与"+ SQL 步骤"并列。

---

## 八、YAML 序列化

**向后兼容分支也需适配**：
```python
# yaml_builder.py 向后兼容单处理器分支
elif state.processor.plugin == "python" and state.processor.script.strip():
    d["processors"].append({
        "name": state.processor.name or state.scene.name + "处理",
        "plugin": "python",
        "input_tables": state.processor.input_tables,
        "output_tables": state.processor.output_tables,
        "config": {"type": "python", "script": state.processor.script},
    })
elif state.processor.sql.strip() or state.processor.output_tables:
    # 原有 SQL 分支不变
```

**主分支**：
```python
elif proc.plugin == "python":
    d["processors"].append({
        "name": proc.name or f"step_{i+1}",
        "plugin": "python",
        "input_tables": proc.input_tables,
        "output_tables": proc.output_tables,
        "config": {"type": "python", "script": proc.script},
    })
```

多行字符串处理：Python 脚本通过 `yaml.dump` 序列化。如需强制块标量（`|`），用自定义 Representer：

```python
class LiteralStr(str): pass
yaml.add_representer(LiteralStr, lambda d, s: d.represent_scalar('tag:yaml.org,2002:str', s, style='|'))
```

---

## 九、预览执行

复用 `/api/wizard/dry-run`——`execute_dry_run()` 通过插件注册自动路由到 `PythonProcessorPlugin.execute()`。

---

## 十、改动清单（完整）

| 层 | 文件 | 改动 |
|-----|------|------|
| PipeForge | `src/pipeforge/config/models.py` | 新增 `PythonProcessorConfig`，`ProcessorSpec` union 扩展 |
| PipeForge | `src/pipeforge/config/__init__.py` | `_inject_type_defaults` 添加 python |
| PipeForge | `src/pipeforge/plugins/processor/python.py` | **新建** |
| ConfigForge | `configforge/models/wizard.py` | `ProcessorConfig.plugin` + `script` 字段 |
| ConfigForge | `configforge/core/pipeline.py` | SQL 自动包装跳过 Python 步骤 |
| ConfigForge | `configforge/services/yaml_builder.py` | Python 序列化 + 向后兼容分支适配 |
| ConfigForge | `configforge/generators/processor/python_processor.py` | **新建** PythonGenerator（AST 校验 process 函数） |
| Frontend | `configforge-web/src/types/wizard.ts` | `ProcessorStep` discrim union |
| Frontend | `configforge-web/src/stores/wizard.ts` | 6 处 `.sql` 适配 |
| Frontend | `configforge-web/src/utils/serialization.ts` | `stateToSnakeCase` 分支 |
| Frontend | `configforge-web/src/components/step3/ProcessorCard.vue` | v-if 分支渲染 |
| Frontend | `configforge-web/src/components/step3/SqlProcessorContent.vue` | **新建（抽取）** |
| Frontend | `configforge-web/src/components/step3/PythonProcessorContent.vue` | **新建** |
| Frontend | `configforge-web/src/components/step3/SqlEditorTab.vue` | "+ Python 步骤"按钮 |
| Frontend | `configforge-web/src/views/ConfigWizardView.vue` | 5 处 `.sql` 适配 + `onOrchestrateConfirm` 预留 |
| Frontend | `configforge-web/src/components/step4/ExportActions.vue` | `.sql` 适配 |
| Frontend | `configforge-web/src/components/step3/OutputConfigTab.vue` | 4 处 `.sql` 适配 |
| 测试 | `tests/test_python_processor.py` | 插件测试 |
| 测试 | `configforge/tests/test_yaml_builder.py` | YAML 序列化 |
| 测试 | 前端 vitest | 类型适配 |

---

## 十一、非目标

- 沙箱/安全隔离（纯信任模型）
- Monaco Editor（v0.4.1）
- AI 编排生成 Python 步骤（v0.4.1）
- Windows 超时控制（后续补 `threading.Timer`）

---

## 十二、验证策略

- PipeForge：Python 插件注册、exec 超时、异常传播
- ConfigForge：SQL 自动包装跳过 Python、YAML 序列化
- Frontend：TypeScript 编译 0 errors（discriminated union 强制所有 `.sql` 引用正确适配）
- 全量回归：257 backend + 113 frontend tests
