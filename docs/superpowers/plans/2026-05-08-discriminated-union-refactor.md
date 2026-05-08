# Pydantic Discriminated Union 泛型化重构 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `InputSpec.config`、`ProcessorSpec.config`、`OutputSpec.config` 从硬编码具体类型改为 Pydantic v2 discriminated union，为 Phase 1 新增 CSV 插件扫清架构障碍。

**Architecture:** 在每个 config 子模型增加 `type: Literal["xxx"]` 判别字段，在父 Spec 模型的 `config` 字段上使用 `Annotated[T, Field(discriminator="type")]` 语法。当前只有单一变体，但扩展新类型时只需：1) 定义新 config 模型（含 `type` 字面量）2) 在 union 中追加类型。所有现有 YAML 和测试向后兼容——`type` 字段带默认值，不会破坏已有配置。

**Tech Stack:** Pydantic v2 `Annotated` + `Field(discriminator=...)` + `Literal` discriminator pattern

**关键约束：**
- 所有现有 YAML（demo/ 和 tests/ 中的）不含 `type` 字段，必须继续可用
- PipeForge 67 个测试 + ConfigForge 26 个测试全通过
- `openpyxl` 写出的 xlsx 文件不受影响

---

## 受影响文件清单

```
PipeForge 核心:
  Modify: src/pipeforge/config/models.py      # 加 type 字段 + 改 union 类型
  Modify: src/pipeforge/core/engine.py         # config.file 赋值可能受影响

PipeForge 测试:
  Modify: tests/test_config_models.py          # 验证 type 默认值 + union 行为
  Modify: tests/test_integration.py            # YAML 不含 type，确保向后兼容

ConfigForge 核心:
  Modify: configforge/models/wizard.py         # InputSource.config / OutputTarget.config → union
  Modify: configforge/services/yaml_builder.py # 确保序列化正确处理 type 字段

ConfigForge 测试:
  Modify: configforge/tests/test_api_wizard.py     # 可能需更新 type 字段
  Modify: configforge/tests/test_services.py       # 确保 yaml 构建正确
  Modify: configforge/tests/test_input_generator.py
  Modify: configforge/tests/test_output_generator.py
  Modify: configforge/tests/test_processor_generator.py
```

---

### Task 1: PipeForge 配置模型增加 type 判别字段

**Files:**
- Modify: `src/pipeforge/config/models.py:12-27`
- Modify: `tests/test_config_models.py:32-51`

- [ ] **Step 1: 给 ExcelInputConfig / SqlProcessorConfig / ExcelOutputConfig 加 type 字段**

`src/pipeforge/config/models.py` — 在每个 config 子模型上加 `type: Literal["xxx"]` 判别字段：

```python
from typing import Literal, Annotated

class ExcelInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["excel"] = "excel"
    file: str | None = None
    sheet: str = "Sheet1"


class InputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    plugin: str
    table: str
    param_key: str
    config: Annotated[ExcelInputConfig, Field(discriminator="type")]
```

SqlProcessorConfig 也加 `type`：

```python
class SqlProcessorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["sql"] = "sql"
    sql: str
    # -- field_validator 不变 --
```

ExcelOutputConfig 也加 `type`，ProcessorSpec / OutputSpec 的 config 字段改写为 annotated union：

```python
class ProcessorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    plugin: str
    output_tables: list[str] = []
    config: Annotated[SqlProcessorConfig, Field(discriminator="type")]


class ExcelOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["excel"] = "excel"
    template: str
    sheet: str = "Sheet1"
    output_dir: str = "./output/"
    source_table: str
    filename: str | None = None
    columns: list[ColumnMapping]
    # -- field_validator 不变 --


class OutputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plugin: str
    config: Annotated[ExcelOutputConfig, Field(discriminator="type")]
```

需要在文件头部新增 import：
```python
from typing import Annotated, Literal
```

从 pydantic 新增 `Field` 的 import（当前 models.py 只从 pydantic import `BaseModel, ConfigDict, field_validator`）：
```python
from pydantic import BaseModel, ConfigDict, Field, field_validator
```

- [ ] **Step 2: 跑现有测试确认向后兼容**

```bash
python3 -m pytest tests/test_config_models.py -v
```

**预期：12 个测试全通过。** 现有测试构造 `ExcelInputConfig(sheet="人员列表")` 时，`type` 有默认值 `"excel"`，不应报错。

- [ ] **Step 3: 新增测试验证 type 默认值和 discriminator 行为**

`tests/test_config_models.py` — 在 `TestInputSpec` 类中新增：

```python
def test_type_field_defaults_to_excel(self):
    """ExcelInputConfig 的 type 字段默认为 'excel'"""
    cfg = ExcelInputConfig(sheet="Sheet1")
    assert cfg.type == "excel"

def test_config_rejects_wrong_type(self):
    """discriminator 拒绝不匹配的 type 值"""
    with pytest.raises(ValidationError):
        InputSpec(
            name="test",
            plugin="excel",
            table="t",
            param_key="p",
            config={"type": "csv", "sheet": "s"},  # type="csv" 不在当前 union 中
        )

def test_yaml_without_type_field_still_works(self):
    """向后兼容：不含 type 的 YAML dict 仍可正常加载"""
    spec = InputSpec(
        name="test",
        plugin="excel",
        table="t",
        param_key="p",
        config={"sheet": "Sheet1"},  # 无 type 字段，靠默认值
    )
    assert spec.config.type == "excel"
    assert spec.config.sheet == "Sheet1"
```

在 `TestProcessorSpec` 类中新增：

```python
def test_processor_config_type_defaults_to_sql(self):
    cfg = SqlProcessorConfig(sql="SELECT 1")
    assert cfg.type == "sql"
```

在 `TestSceneConfig` 类中新增：

```python
def test_output_config_type_defaults_to_excel(self):
    cfg = ExcelOutputConfig(
        template="t.xlsx",
        source_table="t",
        columns=[ColumnMapping(source="a", target="b")],
    )
    assert cfg.type == "excel"
```

- [ ] **Step 4: 跑全部 67 个 PipeForge 测试确认无回归**

```bash
python3 -m pytest tests/ -v
```

**预期：67 个测试全通过。**

- [ ] **Step 5: Commit**

```bash
git add src/pipeforge/config/models.py tests/test_config_models.py
git commit -m "refactor(pipeforge): add type discriminator to config models for discriminated union"
```

---

### Task 2: 更新 PipeForge engine 确保 config 属性访问不变

**Files:**
- Modify: `src/pipeforge/core/engine.py:49-50,79-81,91-97,107-115`

`engine.py` 中直接访问 `config` 的属性——`config.file`、`config.sheet`、`config.sql`、`config.source_table`、`config.columns` 等。由于 discriminated union 只在类型标注层面变化（运行时仍是具体类型的实例），这些属性访问**理论上不需要修改**。

- [ ] **Step 1: 检查 engine.py 中对 config 的访问，确认无需改动**

关键代码路径：

```python
# _execute_input (line 79-80)
config = inp_spec.config          # 类型现在是 Annotated[ExcelInputConfig, ...]
config.file = context.params[...] # 运行时仍是 ExcelInputConfig 实例，属性访问不变

# _execute_processor (line 97)
plugin.execute(context, proc_spec.config)  # 传递 config 对象，不变

# _execute_output (line 113-115)
plugin.execute(context, out_spec.config)
rows = context.db.query(f'SELECT COUNT(*) FROM "{out_spec.config.source_table}"')
# source_table 属性访问不变
```

**预期：无需修改任何 engine.py 代码。** 若类型检查器报错，仅需调整类型注解，不影响运行时行为。

- [ ] **Step 2: 确认集成测试通过**

```bash
python3 -m pytest tests/test_engine.py tests/test_integration.py -v
```

**预期：7 个测试全通过。**

- [ ] **Step 3: Commit**

```bash
git add src/pipeforge/core/engine.py  # 如果有修改
git commit -m "refactor(pipeforge): verify engine works with discriminated union config types"
```

---

### Task 3: ConfigForge 模型转换为 discriminated union

**Files:**
- Modify: `configforge/models/wizard.py:11-24`
- Modify: `configforge/models/wizard.py:36-49`
- Modify: `configforge/models/__init__.py`

ConfigForge 的 `ExcelInputConfig` 和 `ExcelOutputConfig` 已经有 `type: Literal["excel"] = "excel"` 字段。只需将 `InputSource.config` 和 `OutputTarget.config` 的类型声明改为 annotated union。

- [ ] **Step 1: 更新 InputSource / OutputTarget 的 config 字段类型**

`configforge/models/wizard.py`：

```python
from typing import Annotated
from pydantic import Field
# (BaseModel 和 Literal 已 import)

# InputSource — 改 config 字段
class InputSource(BaseModel):
    name: str
    plugin: Literal["excel"] = "excel"
    table: str
    param_key: str
    file_id: str
    config: Annotated[ExcelInputConfig, Field(discriminator="type")] = Field(
        default_factory=ExcelInputConfig
    )

# OutputTarget — 改 config 字段
class OutputTarget(BaseModel):
    plugin: Literal["excel"] = "excel"
    config: Annotated[ExcelOutputConfig, Field(discriminator="type")]
```

注意 `InputSource.config` 同时有 `Annotated[..., Field(discriminator="type")]` 和 `Field(default_factory=...)`——Pydantic v2 支持这种组合，`discriminator` 只在反序列化时生效，`default_factory` 在缺省时生效。

- [ ] **Step 2: 检查 yaml_builder.py 是否需要调整**

```bash
grep -n 'config\.' /Users/lixinyuan/code/CCTEST/configforge/services/yaml_builder.py
```

yaml_builder 序列化 WizardState 时，会访问 `input.config.sheet`、`output.config.columns` 等属性。类型标注变化不影响运行时属性访问，**预期无需修改**。

- [ ] **Step 3: 检查 configforge/models/__init__.py 导出是否完整**

确认 `__init__.py` 已导出 `InputSource` 和 `OutputTarget`（它们在 wizard.py 中定义，需要确保 re-export 路径正确）。

- [ ] **Step 4: 跑 ConfigForge 全部测试**

```bash
python3 -m pytest configforge/tests/ -v
```

**预期：26 个测试全通过。**

- [ ] **Step 5: Commit**

```bash
git add configforge/models/wizard.py configforge/models/__init__.py
git commit -m "refactor(configforge): convert InputSource/OutputTarget to discriminated union"
```

---

### Task 4: 全量回归测试

**Files:**
- 无新增/修改文件

- [ ] **Step 1: 跑 PipeForge 全部测试**

```bash
python3 -m pytest tests/ -v
```

**预期：67 passed.**

- [ ] **Step 2: 跑 ConfigForge 全部测试**

```bash
python3 -m pytest configforge/tests/ -v
```

**预期：26 passed.**

- [ ] **Step 3: 验证 demo YAML 仍可加载**

```bash
python3 -c "
from pipeforge.config import load_yaml_config
config = load_yaml_config('demo/pipeline.yaml')
print(f'场景: {config.scene.name}')
print(f'输入数: {len(config.inputs)}')
print(f'处理器数: {len(config.processors)}')
print(f'输出: {config.output.plugin if config.output else None}')
print('OK: demo YAML 加载成功')
"
```

**预期：** 打印 demo 配置信息，无报错。

- [ ] **Step 4: 跑 E2E 测试**

```bash
cd configforge-web && npx playwright test e2e/wizard.spec.ts --reporter=line 2>&1 | tail -20
```

**预期：3 个 E2E 场景全通过。**

- [ ] **Step 5: 最终 commit**

```bash
git add -A
git commit -m "refactor: full discriminated union migration — 93 tests passing"
```

---

## 扩展指南：如何新增 CSV 插件

重构完成后，新增 CSV 输入只需（**供后续任务参考，不在本次实现范围内**）：

```python
# 1. 在 models.py 定义新 config
class CsvInputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["csv"] = "csv"
    file: str | None = None
    delimiter: str = ","
    encoding: str = "utf-8"
    has_header: bool = True

# 2. 在 InputSpec.config union 中追加类型
class InputSpec(BaseModel):
    config: Annotated[
        ExcelInputConfig | CsvInputConfig,  # 只需改这一行
        Field(discriminator="type")
    ]

# 3. 实现 CsvInputPlugin 并用 @register_plugin("csv", "input") 注册
```
