# PipeForge 设计文档

> 对应产品版本: v0.1 (MVP)  
> 文档版本: v0.3  
> 日期: 2026-05-03  
> 状态: 设计完成，待实现

---

## 1. 愿景

构建一个 **场景固化 → 可重复执行 → 结果稳定** 的数据流水线框架。

解决的核心痛点：AI 助手每次都能帮忙解决数据处理问题，但解决方案无法固化，下次同样的场景还得重新描述需求。PipeForge 通过配置文件将输入-处理-输出的过程固定下来，让后续执行只需提供输入数据即可得到格式固定、目标一致的结果。

---

## 2. 目标用户与使用场景

### 2.1 用户角色

PipeForge 有两个不同的用户角色，不要混淆：

| 角色 | 技能要求 | 做的事 |
|------|---------|--------|
| **配置创建者** | 能写 SQL、理解 YAML 配置、知道数据映射关系 | 定义场景、编写 SQL、设计输出模板 |
| **配置执行者** | 不需要任何技能 | 根据提示提供输入文件、查看结果 |

这两个角色可以是同一个人，也可以不同。典型的协作模式是：配置创建者（如数据分析师或开发者）定义好场景后，配置执行者（如业务人员）每月只需上传文件即可得到格式固定的报表。

### 2.2 两个独立阶段

**阶段一：配置创建（可借助 AI）**
```
创建者描述需求 → AI 辅助生成 YAML 配置 + SQL → 创建者 review 调整 → 保存到 pipelines/
```

这个阶段可以借助 AI 加速，但产物是纯 YAML + SQL，不依赖任何 AI 运行时。

**阶段二：配置执行（纯 CLI，独立运行）**
```
执行者运行: pipeforge run pipelines/xxx.yaml
→ CLI 解析配置，提示需要的输入文件
→ 执行者提供文件路径
→ CLI 调用引擎执行 → 输出结果
```

这个阶段完全独立，不依赖 AI，不依赖网络，只要有 Python 就能运行。

### 2.3 典型场景

- 从 A 系统导出 Excel，经过字段映射/格式转换后，生成 B 系统要求的导入模板
- 从多个数据源（多个 Excel）汇总数据，生成统计报表
- 对现有数据进行查询、统计、分析，形成固定格式的报表文件

---

## 3. 架构设计

### 3.1 三段式流水线

```
[Input 1] ──┐
[Input 2] ──┼──→ SQLite (临时库) ──→ [SQL Processor] ──→ [Output]
[Input N] ──┘
```

- **Input**：多输入，将不同来源的数据读取后写入 SQLite 的不同临时表
- **Processor**：用 SQL 处理数据（JOIN、聚合、CASE 表达式等）
- **Output**：单输出，从 SQLite 查询结果，套用 Excel 模板输出

> 多输出场景可以通过定义多个 Pipeline 解决。

### 3.2 核心设计模式

| 模式 | 应用场景 |
|------|---------|
| **策略模式** | 每个 Input/Output 插件是 Strategy 接口的不同实现 |
| **模板方法** | Pipeline 引擎定义执行骨架（init → execute → cleanup），插件实现具体步骤 |
| **工厂模式** | PluginFactory 根据配置中的 `plugin` 字段创建对应插件实例 |
| **注册模式** | 插件通过装饰器注册到全局注册中心，支持扩展 |

> 多处理器链式执行（责任链模式）作为 v0.2+ 预留。MVP 阶段 `processors` 字段为列表但只执行一个，后续无需破坏性变更即可启用多处理器。

### 3.3 接口设计

#### 插件基类

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel


C = TypeVar("C", bound=BaseModel)


class Plugin(ABC, Generic[C]):
    """所有插件的抽象基类"""

    name: str  # 插件标识名，用于注册和日志

    # 以下属性由引擎在实例化后注入，所有插件共享
    label: str = ""       # 人类可读名称（来自配置的 name 字段）

    @classmethod
    @abstractmethod
    def config_model(cls) -> type[C]:
        """返回该插件的配置 Pydantic 模型，引擎据此做类型校验"""
        ...

    @abstractmethod
    def execute(self, context: "Context", config: C) -> None:
        """执行插件逻辑"""
        ...


class InputPlugin(Plugin[C], ABC):
    """输入插件基类 — 特有属性由引擎注入"""
    table_name: str = ""  # 数据写入 SQLite 的表名（来自配置的 table 字段）


class ProcessorPlugin(Plugin[C], ABC):
    """处理插件基类 — MVP 与 Plugin 相同，预留扩展"""


class OutputPlugin(Plugin[C], ABC):
    """输出插件基类 — MVP 与 Plugin 相同，预留扩展"""
```

每个插件实现自己的 Pydantic 配置模型，引擎在调用 `execute` 前自动完成校验：

```python
class ExcelInputConfig(BaseModel):
    file: str              # 运行时会被解析为实际路径
    sheet: str = "Sheet1"


@register_plugin("excel", "input")
class ExcelInputPlugin(InputPlugin[ExcelInputConfig]):
    name = "excel"

    @classmethod
    def config_model(cls) -> type[BaseModel]:
        return ExcelInputConfig

    def execute(self, context: Context, config: ExcelInputConfig) -> None:
        # config 已经是强类型，不是裸 dict
        # self.table_name 由引擎注入
        with context.db.transaction():
            for row in read_excel_rows(config.file, config.sheet):
                context.db.insert_row(self.table_name, row)
```

#### 插件注册装饰器

```python
# 模块级装饰器，内部委托给 PluginRegistry
def register_plugin(name: str, plugin_type: str):
    """注册插件到全局注册中心"""
    def decorator(cls: type[Plugin]) -> type[Plugin]:
        PluginRegistry.register(name, plugin_type, cls)
        return cls
    return decorator


class PluginRegistry:
    _plugins: dict[tuple[str, str], type[Plugin]] = {}

    @classmethod
    def register(cls, name: str, plugin_type: str, plugin_cls: type[Plugin]) -> None:
        cls._plugins[(name, plugin_type)] = plugin_cls

    @classmethod
    def get(cls, name: str, plugin_type: str) -> type[Plugin]:
        if (name, plugin_type) not in cls._plugins:
            raise PluginNotFoundError(
                f"Unknown {plugin_type} plugin: '{name}'. "
                f"Available: {[n for n, t in cls._plugins.keys() if t == plugin_type]}"
            )
        return cls._plugins[(name, plugin_type)]
```

#### 执行上下文

```python
class Context:
    db: SQLiteManager
    params: dict[str, str]     # 运行时参数（文件路径等），由 CLI 传入引擎
    logger: Logger
    result: ExecutionResult    # 结构化的执行结果统计


class ExecutionResult(BaseModel):
    """结构化的执行结果统计"""
    inputs: dict[str, InputStats]     # key = input name
    processors: list[ProcessorStats]  # 按执行顺序
    output: OutputStats | None = None


class InputStats(BaseModel):
    name: str
    rows_loaded: int
    elapsed_ms: float


class ProcessorStats(BaseModel):
    name: str
    tables_created: list[str]
    elapsed_ms: float


class OutputStats(BaseModel):
    rows_written: int
    file_path: str
    elapsed_ms: float
```

### 3.4 类图与职责边界

```
┌─────────────────────────────────────────┐
│  CLI Layer (cli.py)                     │
│  ┌───────────────────────────────────┐  │
│  │ required_params() → list[dict]    │  │  从引擎获取需要哪些参数
│  │ collect_params() → dict[str,str]  │  │  CLI 负责终端 I/O (--param 或 input())
│  │ engine.execute(params)            │  │  将收集到的参数传入引擎
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  Engine (core/engine.py)                │
│  ┌───────────────────────────────────┐  │
│  │ load_config(yaml) → SceneConfig   │  │  解析 + 校验配置
│  │ required_params() → list[dict]    │  │  声明需要哪些 param_key
│  │ execute(params: dict)             │  │  执行流水线
│  │   ├── input_plugin.execute() × N  │  │
│  │   ├── processor_plugin.execute()  │  │
│  │   └── output_plugin.execute()     │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  Plugins (plugins/)                     │
│  每个插件只关注自己的 config + execute   │
│  通过 Context.db 读写 SQLite            │
└─────────────────────────────────────────┘
```

**职责边界**：
- CLI 层：负责所有终端 I/O（参数收集、进度展示、错误输出）
- 引擎层：负责配置解析、流程编排、插件调度
- 插件层：负责单一功能（读文件、执行 SQL、写文件）

引擎不直接调用 `input()` 或 `print()`，保持纯逻辑层。

### 3.5 错误处理策略

#### 错误分类

| 类别 | 示例 | 处理 |
|------|------|------|
| **配置错误** | YAML 格式错误、缺少必填字段、插件类型不存在、表名冲突 | 启动阶段报错，不执行任何操作 |
| **输入错误** | 文件不存在、.xls 格式不支持、文件被占用 (PermissionError)、sheet 不存在、Excel 密码保护 | 终止执行，保留临时 .db 用于调试 |
| **处理错误** | SQL 语法错误、引用的表不存在 | 终止执行，保留临时 .db 用于调试 |
| **输出错误** | 模板文件不存在、目标列在查询结果中缺失、磁盘空间不足 | 终止执行，保留临时 .db 用于调试 |

#### 失败后行为

- 任何阶段失败，引擎捕获异常并输出结构化错误信息（阶段名、错误类型、具体原因）
- **临时 .db 默认保留**（输出到日志中路径），方便调试排查问题
- 提供 `--cleanup` 标志强制清理临时文件
- 不提供断点重跑（MVP），但保留的 .db 可以手动排查数据状态

#### 事务

- SQLite 层面：每个 input 写入使用独立事务，失败自动回滚
- Pipeline 层面：不做跨阶段事务回滚（MVP 足够），因为临时 .db 在失败后保留，用户可排查

---

## 4. 配置设计

### 4.1 配置格式：YAML + Pydantic 校验

完整示例：

```yaml
scene:
  name: 人员数据月报
  description: 汇总 A 系统人员明细和考勤数据，生成月度人员统计报表
  version: "1.0"

inputs:
  - name: 人员明细
    plugin: excel
    table: person_detail
    param_key: person_file
    config:
      sheet: 人员列表

  - name: 考勤数据
    plugin: excel
    table: attendance
    param_key: attendance_file
    config:
      sheet: 考勤统计

processors:
  - name: 数据合并与统计
    plugin: sql
    output_tables:
      - report_data          # 声明此处理器会创建哪些表
    sql: |
      CREATE TABLE report_data AS
      SELECT
        p.姓名,
        p.部门,
        p.岗位,
        a.出勤天数,
        a.迟到次数,
        CASE
          WHEN a.迟到次数 > 3 THEN '预警'
          ELSE '正常'
        END as 考勤状态
      FROM person_detail p
      LEFT JOIN attendance a ON p.工号 = a.工号

output:
  plugin: excel
  config:
    template: templates/person_report_template.xlsx
    sheet: 报表                  # 目标 Sheet 名，默认为第一个 Sheet
    source_table: report_data
    filename: "人员月报_{{date:YYYYMM}}.xlsx"
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 所属部门
      - source: 岗位
        target: 岗位
      - source: 出勤天数
        target: 本月出勤天数
      - source: 迟到次数
        target: 迟到次数
      - source: 考勤状态
        target: 状态
```

### 4.2 关键字段说明

| 字段 | 说明 |
|------|------|
| `scene.name` | 场景名称，用户选择场景时展示 |
| `scene.version` | 配置版本号，用于未来的配置迁移 |
| `inputs[].name` | 输入名称，用于日志和错误信息 |
| `inputs[].param_key` | 运行时参数名，引擎据此声明需要的参数 |
| `inputs[].table` | 数据写入 SQLite 的表名，SQL 中引用此名 |
| `inputs[].plugin` | 插件类型，对应注册中心中的插件名 |
| `processors[].output_tables` | 声明该处理器创建的表名列表，用于配置校验 |
| `output.config.template` | Excel 模板文件路径，样式由模板定义 |
| `output.config.sheet` | 目标 Sheet 名称，默认为模板的第一个 Sheet |
| `output.config.source_table` | 数据源表名，必须在 `output_tables` 中声明过 |
| `output.config.filename` | 输出文件名模板，支持 `{{date:YYYYMM}}` 等变量 |
| `output.config.columns` | 列映射列表，`source` 为 SQL 结果列名，`target` 为模板列头名 |

### 4.3 输出文件名规则

`filename` 字段支持以下变量（MVP 范围）：

| 变量 | 说明 | 示例 |
|------|------|------|
| `{{date:FORMAT}}` | 当前日期，按 strftime 格式 | `{{date:YYYYMM}}` → `202405` |
| `{{scene_name}}` | 场景名称（`scene.name`） | `人员数据月报` |
| `{{timestamp}}` | Unix 时间戳 | `1714700000` |

如果 `filename` 未配置，默认使用 `{scene_name}_{date:YYYYMMDD}.xlsx`。

### 4.4 列映射规则

- `source` 列必须在 `source_table` 的查询结果中存在，否则 **在 Processor 执行完成后、Output 写入前报错**
- `target` 列必须与模板目标 Sheet 首行列头匹配，否则 **在配置加载阶段报错**（因为模板文件在启动时可读取）
- 列的顺序由配置中 `columns` 的顺序决定，写入模板时按此顺序从左到右填充
- 数据行从模板目标 Sheet 的第 2 行开始写入（第 1 行为表头，保持不变）
- 模板中第 2 行及之后的已有数据会被 **覆盖**

### 4.5 模板规范

模板 Excel 文件应遵循以下规范：

- 目标 Sheet 第 1 行为表头（列名），必须与 `columns[].target` 完全匹配
- 第 2 行起为空，由 PipeForge 填入数据
- 表头行可设置样式（背景色、字体、边框），样式会被保留
- 可以包含其他 Sheet（如说明页、数据源），不会被修改
- **不支持**：合并单元格覆盖数据区域、数据验证规则影响写入区域（v0.2 将增强处理）
- 仅支持 `.xlsx` 格式，不支持旧版 `.xls`

### 4.6 表名冲突检测

配置加载时执行以下校验（均为静态检查，不需要运行时数据）：

1. 所有 `inputs[].table` 互不相同
2. `inputs[].table` 不与任何 processor 的 `output_tables` 中的表名冲突
3. `output.config.source_table` 必须存在于某个 processor 的 `output_tables` 中

校验失败则报错，不执行。

> 这样设计避免了 SQL 解析——创建者显式声明 `output_tables`，引擎据此做静态校验。如果声明与实际 SQL 不符，会在运行时 SQL 执行阶段报错。

### 4.7 配置版本兼容

- `scene.version` 字段标记配置版本
- Pydantic 配置模型使用 `model_config = ConfigDict(extra="ignore")`，忽略未知字段，保证旧配置在新版本中不会报错
- 未来如果配置结构发生破坏性变更，引擎根据 `version` 字段执行自动迁移或提示用户迁移

---

## 5. 包结构

```
pipeforge/
├── pyproject.toml              # 项目元数据 + 依赖
├── README.md
│
├── src/pipeforge/
│   ├── __init__.py
│   ├── cli.py                  # CLI 入口（参数收集、进度展示）
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py           # PipelineEngine 主引擎
│   │   ├── context.py          # 执行上下文
│   │   ├── registry.py         # 插件注册中心 + register_plugin 装饰器
│   │   └── sqlite.py           # SQLite 临时库管理
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── loader.py           # YAML 加载
│   │   └── models.py           # Pydantic 配置模型
│   │
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── base.py             # 抽象基类（泛型 + Pydantic Config + 子类型）
│   │   ├── input/
│   │   │   ├── __init__.py
│   │   │   ├── excel.py        # Excel 输入
│   │   │   └── csv.py          # CSV 输入（v0.2 预留）
│   │   ├── processor/
│   │   │   ├── __init__.py
│   │   │   └── sql.py          # SQL 处理
│   │   └── output/
│   │       ├── __init__.py
│   │       └── excel.py        # Excel 模板输出
│   │
│   └── utils/
│       └── __init__.py
│
├── pipelines/                  # 用户场景配置
│   └── .gitkeep
│
├── templates/                  # Excel 模板
│   └── .gitkeep
│
└── tests/
    ├── test_engine.py
    ├── test_excel_input.py
    ├── test_sql_processor.py
    └── test_excel_output.py
```

---

## 6. 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| Python | 3.10+ | f-string 高级特性，类型注解完善 |
| 配置解析 | Pydantic v2 | 强类型校验，泛型支持好 |
| YAML | PyYAML | 标准方案 |
| Excel 读 | openpyxl (`read_only=True`) | 流式逐行读取，内存可控 |
| Excel 写 | openpyxl (普通模式 + 两阶段优化) | 保留模板样式，详见 §6.1 |
| SQLite | sqlite3 (内置) | 零依赖 |
| CLI | click | 简洁易用 |

### 6.1 openpyxl 样式保留与性能方案

openpyxl 的 `write_only=True` 模式可以高效写入大数据但无法保留模板样式；普通模式保留样式但逐单元格写入很慢。MVP 采用 **两阶段写入** 方案：

```
阶段 1 (read_only):  加载模板 → 读取目标 Sheet 首行（表头）→ 提取每个单元格的 style 对象
阶段 2 (write_only):  打开新 workbook → 写入数据行 → 将阶段 1 提取的样式应用到首行
```

具体实现：
- `read_only=True` 加载模板，`iter_rows(min_row=1, max_row=1)` 读取表头行，保存每个单元格的 `font`、`fill`、`border`、`alignment`、`number_format`
- `write_only=True` 创建新文件，先写入带样式的表头行（`WriteOnlyCell` + 样式对象），再逐行写入数据（不设置样式）
- 数据行从第 2 行开始，纯数据不设置样式

**性能预期**（两阶段方案）：

| 指标 | 目标 |
|------|------|
| 数据规模 | 单表 ≤ 10 万行 |
| 1 万行性能 | ≤ 5 秒（含读模板样式 + 写数据） |
| 内存 | ≤ 50MB |

> 10 万行以上的场景留给 v0.2 优化（如分块写入或考虑替代方案）。

---

## 7. 非功能性需求

| 指标 | 目标 | 说明 |
|------|------|------|
| 数据规模 | 单表 ≤ 10 万行 | openpyxl 逐行读取 + SQLite 批量写入，内存可控 |
| 性能 | 1 万行数据 ≤ 5 秒 | 两阶段写入方案，含读模板样式开销 |
| 内存 | ≤ 50MB | read_only 模式读取，write_only 模式写入 |
| 临时文件 | 执行后保留（默认），可手动清理 | 失败时用于调试，成功后可由用户决定 |

---

## 8. 可扩展性设计

| 扩展点 | 方案 |
|--------|------|
| 新输入源 | 实现 `InputPlugin` 基类，注册到 registry |
| 新输出格式 | 实现 `OutputPlugin` 基类，注册到 registry |
| 新处理器 | 实现 `ProcessorPlugin` 基类，注册到 registry |
| 多处理器链式执行 | v0.2+，`processors` 已设计为列表，启用遍历执行即可 |
| 插件自动发现 | Python `importlib` + entry_points |
| 变量替换 | v0.2+，Jinja2 模板引擎，区分安全变量和用户输入变量 |
| 数据校验 | 未来集成 Pydantic schema 或 Great Expectations |
| 增量处理 | 未来在 Context 中维护 checkpoint |
| 可视化配置 | 未来基于 YAML schema 生成前端表单 |

---

## 9. 版本规划

### v0.1 MVP（第一个版本）

| 阶段 | 实现 |
|------|------|
| Input | Excel（支持指定 sheet，read_only 流式读取） |
| Processor | SQL（单个，SQLite 执行） |
| Output | Excel（两阶段写入：保留表头样式，按显式列映射输出） |
| 配置 | YAML + Pydantic 校验（含表名冲突检测、列映射校验、output_tables 声明） |
| CLI | `pipeforge run <scene.yaml>`，支持 `--param` 直接传参和交互式引导 |
| 错误处理 | 结构化错误输出，失败后保留临时 .db |

### v0.2+ 后续迭代

- CSV 输入/输出
- API 输入/输出
- SQL 中的 Jinja2 变量替换（安全变量 vs 用户输入变量转义）
- 多处理器链式执行
- 执行日志持久化
- 数据校验（schema validation）
- 配置迁移工具
- 模板合并单元格/数据验证规则增强处理

---

## 10. 决策记录

| # | 决策 | 理由 |
|---|------|------|
| 1 | 项目名：PipeForge | 管道锻造，暗示将输入-处理-输出"锻造"成稳定流程 |
| 2 | 项目形态：CLI + 配置文件 | 独立于 AI 工具运行，配置创建可借助 AI，执行阶段完全独立 |
| 3 | 技术栈：Python | 数据处理生态成熟，AI coding 能力最强 |
| 4 | 配置文件生产：AI 生成 → 逐步优化到可视化 | 先用 AI 降低创建门槛，后续降低使用成本 |
| 5 | 复杂逻辑：SQL 处理 | SQL 天然支持筛选、JOIN、聚合、CASE，比 YAML 规则更强大 |
| 6 | SQLite 临时库：每次执行新建临时 .db，失败后保留用于调试 | 隔离、安全、可排查 |
| 7 | 多输入、单输出 | 多输入是常见场景；多输出可用多个 Pipeline 解决 |
| 8 | Excel 模板输出：用户提供真实模板文件 | 样式完全由用户控制，结果格式固定 |
| 9 | 配置校验：Pydantic 泛型模型 | 启动前发现配置错误，插件配置类型安全 |
| 10 | 使用者角色分离 | 配置创建者（懂 SQL）vs 配置执行者（零门槛） |
| 11 | MVP 不使用 pandas | openpyxl 逐行读取 + sqlite3 executemany，依赖小、内存可控 |
| 12 | 列映射显式定义 | `source → target` 映射，运行时校验列存在性，启动时校验模板匹配 |
| 13 | 临时 .db 存放在 `tempfile` 自动管理 | 使用 Python `tempfile` 模块，执行后自动定位路径 |
| 14 | MVP 单处理器 | `processors` 为列表但只执行一个，v0.2 启用链式遍历 |
| 15 | 无断点重跑（MVP） | 保留临时 .db 足够排查，断点重跑复杂度高于收益 |
| 16 | processor 通过 `output_tables` 显式声明创建的表 | 避免 SQL 解析，用声明式配置做静态校验 |
| 17 | openpyxl 两阶段写入 | read_only 取表头样式 + write_only 写数据，平衡样式保留与性能 |
| 18 | CLI 与引擎职责分离 | CLI 负责终端 I/O，引擎只接收已解析的 params dict |

---

## 11. 实现计划

| 步骤 | 内容 | 文件 |
|------|------|------|
| 1 | 项目骨架 + 依赖 | `pyproject.toml` |
| 2 | 插件基类（泛型 + 子类型）+ 注册中心 + 装饰器 | `plugins/base.py`, `core/registry.py` |
| 3 | 配置模型（Pydantic）+ YAML 加载 + 表名冲突检测 | `config/models.py`, `config/loader.py` |
| 4 | SQLite 管理（tempfile）+ 上下文 | `core/sqlite.py`, `core/context.py` |
| 5 | 引擎主流程 + 参数声明 + 错误处理 | `core/engine.py` |
| 6 | Excel 输入插件（openpyxl read_only 逐行读取） | `plugins/input/excel.py` |
| 7 | SQL 处理插件 | `plugins/processor/sql.py` |
| 8 | Excel 模板输出插件（两阶段写入 + 显式列映射） | `plugins/output/excel.py` |
| 9 | CLI 入口（交互式引导 + --param，职责与引擎分离） | `cli.py` |
| 10 | 集成测试（含错误路径测试） | `tests/` |
