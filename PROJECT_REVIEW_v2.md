# PipeForge 项目复审（调整后）

> 审核范围: 完整项目代码 + 测试 + 配置 + 文档  
> 审核日期: 2026-05-03  
> 测试结果: **67/67 passed** (0.20s)  
> 对比基线: PROJECT_REVIEW.md（首次项目审核）

---

## 一、首次审核问题修复情况

| # | 首次问题 | 修复情况 | 结果 |
|---|---------|---------|------|
| P1-1 | Input 用 `read_only=True` 但设计文档写「普通模式」 | **未修复**：代码仍用 `read_only=True`（正确选择），但设计文档 v7 §6 技术选型和 §11 实现计划仍写「openpyxl 普通模式读」 | ⚠️ 文档未同步 |
| P1-2 | Output 写文件 3 次（性能浪费） | **未修复**：仍为三次 I/O（openpyxl 限制，MVP 可接受） | ⚠️ 已知限制 |
| P1-3 | `executescript` 隐式 COMMIT | **未修复**：仍用 `executescript`（设计已明确不做跨阶段回滚） | ⚠️ 已知限制 |
| P2-1 | `InputSpec.config` 硬编码为 `ExcelInputConfig` | **未修复**：仍为 `config: ExcelInputConfig`（v0.2 再处理） | ⚠️ 预留 |
| P2-2 | Output 插件 label 为空，日志不友好 | ✅ **已修复**：[engine.py:112](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/core/engine.py#L112) 改为 `plugin.label = "output"` | ✅ |
| P2-3 | Context 用 `@dataclass` 而 ExecutionResult 用 Pydantic | **未修复**：仍为 `@dataclass` | ⚠️ 风格不统一 |
| P2-4 | 测试中动态赋值 `context.output_dir` | ✅ **已修复**：[test_excel_output.py](file:///Users/lixinyuan/code/CCTEST/tests/test_excel_output.py) 不再有 `context.output_dir = ...`，改为从 `config.output_dir` 读取 | ✅ |
| P2-5 | `PluginRegistry._plugins` 是类变量 | **未修复**：仍为类变量（当前无问题） | ⚠️ 潜在风险 |
| P3-2 | demo/output 未 gitignore | ✅ **已修复**：[.gitignore](file:///Users/lixinyuan/code/CCTEST/.gitignore) 新增 `demo/output/` | ✅ |
| P3-3 | 根目录 13 个文档版本 | **未修复**：现有 DESIGN.md~v7 + REVIEW.md~v6 共 13 个文件 | ⚠️ 建议归档 |

### 修复总结

- **3 项已修复**：P2-2（Output label）、P2-4（测试动态赋值）、P3-2（gitignore）
- **3 项已知限制**：P1-2（三次 I/O）、P1-3（executescript）、P2-1（硬编码 config 类型）——均属 MVP 设计取舍，v0.2 处理
- **1 项文档未同步**：P1-1（Input read_only vs 文档「普通模式」）
- **2 项风格问题**：P2-3（dataclass vs Pydantic）、P2-5（类变量注册表）
- **1 项建议**：P3-3（文档归档）

---

## 二、代码全面再审

### 逐文件审查

#### `plugins/input/excel.py` ✅
- `read_excel_rows` 返回 `(columns, rows)` 元组，与设计一致
- 首行检测、空文件处理、sheet 不存在处理均到位
- `row_generator` 中正确关闭 workbook
- 唯一问题：`read_only=True` 与设计文档描述不一致（代码更合理）

#### `plugins/output/excel.py` ✅
- 两阶段写入实现完整：提取样式 → write_only 写数据 → 恢复列宽
- `resolve_filename` 支持 `{{scene_name}}`、`{{timestamp}}`、`{{date:FORMAT}}`
- source 列运行时校验（P0-1 修复已验证）
- target 列在 `_extract_template_attrs` 中校验
- `output_dir` 从 config 读取，自动 `makedirs`

#### `plugins/processor/sql.py` ✅
- 极简实现，委托 `context.db.execute()`
- 日志输出包含 `self.label`

#### `core/engine.py` ✅
- 三段执行流程清晰
- 参数注入：`config.file = context.params[inp_spec.param_key]`
- Output label 赋值为 `"output"`（P2-2 修复已验证）
- `processors[:1]` 限制 MVP 只执行第一个 processor
- `tables_created` 从 `list_tables()` 差集计算（决策 #20）
- 异常时保留 .db + 日志输出路径

#### `core/context.py` ✅
- `Context` dataclass 字段完整：db/params/yaml_dir/scene_name/output_path/logger/result
- `ExecutionResult` + 三个 Stats 均为 Pydantic model
- `Logger` 支持 info/error/debug 三级

#### `core/sqlite.py` ✅
- WAL 模式、临时文件、事务支持、`list_tables`/`table_exists`
- `create_table` 所有列默认 TEXT 类型（MVP 简化）

#### `core/registry.py` ✅
- 装饰器 + 类方法注册表，接口清晰
- `PluginNotFoundError` 自定义异常

#### `config/models.py` ✅
- 所有 model 使用 `extra="forbid"`
- `SqlProcessorConfig.sql` 有非空校验
- `ColumnMapping.source` 有非空校验
- `ExcelOutputConfig.columns` 有非空校验

#### `config/__init__.py` ✅
- 三项校验：表名冲突、param_key 去重、source_table 声明
- 与设计文档 §4.6 一致

#### `cli.py` ✅
- 职责边界清晰：参数收集（交互式 + 命令行）→ 引擎执行 → 结果展示
- 不直接操作引擎内部

#### `plugins/base.py` ✅
- 泛型 `Plugin[C]` + 三个子类
- `InputPlugin.table_name` 默认空字符串，引擎注入

---

## 三、新发现的问题

### P2 — 建议优化

#### P2-NEW-1: 设计文档 v7 仍写「Excel 输入插件（openpyxl 普通模式读）」

[DESIGN_v7.md:688](file:///Users/lixinyuan/code/CCTEST/DESIGN_v7.md#L688)：

> | 6 | Excel 输入插件（openpyxl 普通模式读，首行建表，逐行插入） | `plugins/input/excel.py` |

[DESIGN_v7.md:556](file:///Users/lixinyuan/code/CCTEST/DESIGN_v7.md#L556)：

> | Excel 读 | openpyxl（普通模式） | 读取模板需要获取样式和列宽，普通模式才能完整加载 |

代码中 Input 使用 `read_only=True`，这是**正确的**（Input 只需数据，不需要样式，read_only 性能更好）。但设计文档把「Excel 读」统一描述为「普通模式」，没有区分 Input（read_only）和 Output 模板读取（普通模式）。

**建议**：设计文档 §6 技术选型表改为：

```
| Excel 读（Input） | openpyxl（read_only 模式） | 只需数据不需样式，流式读取性能好 |
| Excel 读（Output 模板） | openpyxl（普通模式） | 需要获取样式和列宽 |
```

§11 实现计划第 6 行也同步修改。

---

#### P2-NEW-2: `engine.py:52` 硬编码 `processors[:1]` 但无注释说明

[engine.py:52](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/core/engine.py#L52)：

```python
for proc_spec in self.config.processors[:1]:
```

设计文档明确「MVP 只支持单处理器」，但代码中 `[:1]` 切片没有任何注释解释为什么限制为 1。如果有人看到这行代码，可能会认为是 bug。

**建议**：加一行注释 `# MVP: only first processor is executed`。

---

### P3 — 微小问题

#### P3-NEW-1: `sqlite.py:17` 所有列默认 TEXT 类型

[sqlite.py:17](file:///Users/lixinyuan/code/CCTEST/src/pipeforge/core/sqlite.py#L17)：

```python
cols_def = ", ".join(f'"{c}" TEXT' for c in columns)
```

所有列都是 TEXT，意味着数值比较（如 `WHERE salary > 5000`）会按字符串排序而非数值。这是 MVP 的简化取舍，但用户在写 SQL 时可能踩坑。

**建议**：在文档或 CLI 帮助中提示「Input 数据全部以 TEXT 类型存入 SQLite，数值比较需用 CAST」。

---

## 四、总体评价

### 当前状态

| 维度 | 状态 |
|------|------|
| 测试 | ✅ 67/67 passed |
| 核心功能 | ✅ 完整可用 |
| 设计一致性 | ⚠️ 1 处文档未同步（Input read_only） |
| 已知限制 | 3 项（三次 I/O / executescript / 硬编码 config），均为 MVP 取舍 |
| 新问题 | 2 P2 + 1 P3，均为文档/注释层面 |

### 结论

**项目状态良好，首次审核的 3 个 P1 已有 2 个属于已知限制（设计取舍），1 个属于文档未同步。** 新发现的问题均为 P2/P3 级别，不影响功能。

**项目可以正常使用和交付。** 建议在 v0.2 迭代时：
1. 同步设计文档中 Input 读取模式的描述
2. 给 `processors[:1]` 加注释
3. 归档旧版设计/审核文档
