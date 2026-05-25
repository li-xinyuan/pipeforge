# ConfigForge Python 处理器设计审核报告（第三轮）

**审核日期**: 2026-05-24
**审核文档**: `docs/superpowers/specs/2026-05-24-python-processor-design.md`（第二轮修订版）
**对比基线**: 第二轮审核报告 `docs/superpowers/reviews/2026-05-24-python-processor-review-r2.md`
**审核结论**: ✅ **可以开发** — 上轮所有问题已修复，仅剩 4 个轻微建议

---

## 一、上轮问题修复状态

| 上轮问题 | 严重程度 | 修复状态 | 评价 |
|---------|---------|---------|------|
| 重要1: `pipeline.py` SQL 自动包装崩溃 | 🟡 重要 | ✅ 已修复 | 第四节 4.4 给出了 `if proc.plugin == "python": continue` 方案 |
| 重要2: `serialization.ts` 硬编码 SQL | 🟡 重要 | ✅ 已修复 | 第六节 6.2 清单中已列出适配方式 |
| 遗漏1: `wizard.ts` 6 处 `.sql` | 🟢 轻微 | ✅ 已修复 | 第六节 6.2 逐条列出 |
| 遗漏2: `ConfigWizardView.vue` 5 处 `.sql` | 🟢 轻微 | ✅ 已修复 | 第六节 6.2 逐条列出 |
| 遗漏3: `ExportActions.vue` `.sql` | 🟢 轻微 | ✅ 已修复 | 第六节 6.2 已列出 |
| 遗漏4: `onOrchestrateConfirm` 硬编码 | 🟢 轻微 | ✅ 已修复 | `s.plugin \|\| 'sql'` 预留 |
| 3.1 信号量平台兼容性 | ⚠️ 建议 | ✅ 已修复 | 添加了 `sys.platform != "win32"` 检测 |
| 3.2 `ctx.db.connection` 提交 | ⚠️ 建议 | ✅ 已修复 | `finally` 中添加 `context.db.connection.commit()` |
| 3.3 信任模型 vs 受限 builtins 矛盾 | ⚠️ 建议 | ✅ 已修复 | 改为纯信任模型，移除受限 builtins |
| 3.4 后端 `ProcessorConfig` 模型 | ⚠️ 建议 | ✅ 已修复 | 第五节给出扁平结构定义 |
| 3.5 YAML 多行字符串 | ⚠️ 建议 | ✅ 已修复 | 第八节给出 LiteralStr Representer 方案 |
| 改动清单遗漏 | ⚠️ 建议 | ✅ 已修复 | 第十节补充了 `pipeline.py`、`ConfigWizardView.vue`、`ExportActions.vue` |

**总计**：上轮 12 个问题全部修复。设计文档从 94 行扩展到 272 行，覆盖面显著提升。

---

## 二、新发现的问题

### 🟢 轻微问题 1：`OutputConfigTab.vue` 中 4 处 `.sql` 引用未列入适配清单

设计文档第六节 6.2 的 `.sql` 适配清单遗漏了 [OutputConfigTab.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/components/step3/OutputConfigTab.vue) 中的 4 处引用：

| 行号 | 代码 | 影响 |
|------|------|------|
| 235 | `store.processors.map(p => p.sql)` | watch SQL 变化触发列推断 |
| 273 | `store.processors[0].sql.trim()` | onMounted 条件判断 |
| 274 | `store.processors[0].sql` | 记录 prevSql |
| 320 | `store.processors[0].sql` | 获取 SQL 用于推断 |

**问题**：Python 步骤没有 `sql` 字段，TypeScript 编译会报错。但这些代码的语义是"获取处理步骤的代码内容用于列推断"，Python 步骤的 `script` 也需要同样的推断能力。

**建议**：添加到适配清单，适配方式为 `p.plugin === 'sql' ? p.sql : p.script`。改动清单第十节也需补充此文件。

### 🟢 轻微问题 2：`SqlProcessorGenerator` 需要对应的 `PythonProcessorGenerator`

ConfigForge 有一个 Generator 层（[generators/processor/sql_processor.py](file:///Users/lixinyuan/code/CCTEST/configforge/generators/processor/sql_processor.py)），通过 `GeneratorRegistry.register("sql", "processor")` 注册。这个 Generator 负责：
- `infer_config` — 推断默认配置
- `build_config` — 从向导状态构建配置
- `validate_config` — 校验配置（当前用 `sqlite3.connect(":memory:")` 执行 SQL 验证语法）

Python 处理器需要对应的 `PythonProcessorGenerator`，但改动清单未提及。

**建议**：新增 `configforge/generators/processor/python_processor.py`，`validate_config` 可以检查 `process(ctx)` 函数是否存在（通过 AST 解析，无需实际执行）：

```python
import ast

class PythonProcessorGenerator(ConfigGenerator[ProcessorConfig]):
    def validate_config(self, config: ProcessorConfig) -> list[str]:
        errors = []
        if not config.script or not config.script.strip():
            errors.append("Python 脚本不能为空")
            return errors
        try:
            tree = ast.parse(config.script)
            has_process = any(
                isinstance(node, ast.FunctionDef) and node.name == "process"
                for node in ast.walk(tree)
            )
            if not has_process:
                errors.append("Python 脚本必须定义 process(ctx) 函数")
        except SyntaxError as e:
            errors.append(f"Python 语法错误: {e}")
        return errors
```

改动清单需补充：
- `configforge/generators/processor/python_processor.py` — **新建**
- `configforge/tests/test_processor_generator.py` — 添加 Python Generator 测试

### 🟢 轻微问题 3：`yaml_builder.py` 向后兼容分支也硬编码了 SQL

[yaml_builder.py](file:///Users/lixinyuan/code/CCTEST/configforge/services/yaml_builder.py) 第 41-48 行有向后兼容的单处理器分支：

```python
elif state.processor.sql.strip() or state.processor.output_tables:
    d["processors"].append({
        ...
        "config": {"type": "sql", "sql": state.processor.sql},
    })
```

`ProcessorConfig` 改为扁平结构后 `sql` 字段有默认值 `""`，Python 步骤时 `sql=""` 但 `script` 有值。这个分支需要同步适配：

```python
elif state.processor.plugin == "python" and state.processor.script.strip():
    d["processors"].append({
        "name": state.processor.name or state.scene.name + "处理",
        "plugin": "python",
        "input_tables": state.processor.input_tables,
        "output_tables": state.processor.output_tables,
        "config": {"type": "python", "script": state.processor.script},
    })
elif state.processor.sql.strip() or state.processor.output_tables:
    # 原有 SQL 分支
```

改动清单中 `yaml_builder.py` 已列出，但需确保向后兼容分支也被覆盖。

### 🟢 轻微问题 4：`ProcessorConfig` 扁平结构的 Pydantic 校验

设计文档第五节给出的后端模型：

```python
class ProcessorConfig(BaseModel):
    plugin: Literal["sql", "python"] = "sql"
    sql: str = ""     # SQL 步骤时必填
    script: str = ""  # Python 步骤时必填
```

当前 `ProcessorConfig.sql` 是必填字段（无默认值），改为 `sql: str = ""` 后是可选的。但需要添加 `model_validator` 确保交叉校验：

```python
@model_validator(mode="after")
def validate_plugin_fields(self):
    if self.plugin == "sql" and not self.sql.strip():
        raise ValueError("SQL 步骤的 sql 字段不能为空")
    if self.plugin == "python" and not self.script.strip():
        raise ValueError("Python 步骤的 script 字段不能为空")
    return self
```

没有这个校验，`ProcessorConfig(plugin="python", sql="", script="")` 会通过验证，导致运行时错误。

---

## 三、设计质量评分

| 维度 | 第一轮 | 第二轮 | 第三轮 | 变化趋势 |
|------|-------|-------|-------|---------|
| 阻断性问题 | 3 | 0 | 0 | ✅ 稳定 |
| 重要问题 | 5 | 2 | 0 | ✅ 全部修复 |
| 轻微/遗漏 | 3 | 5 | 4 | ⬇️ 持续减少 |
| 可开发性 | 有条件可行 | 基本可行 | ✅ 可以开发 | ✅ 达标 |

---

## 四、总结

设计文档经过两轮修订已达到**可开发状态**。上轮 12 个问题全部修复，当前仅剩 4 个轻微问题：

1. `OutputConfigTab.vue` 4 处 `.sql` 未列入适配清单 — 开发时 TypeScript 编译器会自动报错
2. 缺少 `PythonProcessorGenerator` — 可在开发中补充，不影响核心功能
3. `yaml_builder.py` 向后兼容分支需适配 — 已在改动清单中，确保覆盖即可
4. `ProcessorConfig` 缺少交叉校验 — 添加 `model_validator` 即可

**建议**：这 4 个轻微问题可以在开发过程中直接修复，无需再等待设计修订。可以开始编码了。
