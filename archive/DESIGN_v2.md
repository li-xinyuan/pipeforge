# PipeForge 设计文档

> 版本: v0.2  
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
→ 引擎解析配置，提示需要的输入文件
→ 执行者提供文件路径
→ 执行完毕，输出结果
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

> 注意：多处理器链式执行（责任链模式）作为 v0.2+ 预留，MVP 阶段只支持单个 processor。但 `processors` 字段设计为列表，后续无需破坏性变更即可启用多处理器。

### 3.3 接口设计

#### 插件基类

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

# 每个插件声明自己的配置模型
C = TypeVar("C", bound=BaseModel)


class Plugin(ABC, Generic[C]):
    """所有插件的抽象基类"""

    name: str  # 插件标识名，用于注册和日志

    @classmethod
    @abstractmethod
    def config_model(cls) -> type[C]:
        """返回该插件的配置 Pydantic 模型，引擎据此做类型校验"""
        ...

    @abstractmethod
    def execute(self, context: "Context", config: C) -> None:
        """执行插件逻辑"""
        ...
```

每个插件实现自己的 Pydantic 配置模型，引擎在调用 `execute` 前自动完成校验：

```python
# Excel 输入插件的配置模型
class ExcelInputConfig(BaseModel):
    file: str              # 运行时会被解析为实际路径
    sheet: str = "Sheet1"  # 默认 Sheet


@register_plugin("excel", "input")
class ExcelInputPlugin(InputPlugin):
    name = "excel"

    @classmethod
    def config_model(cls) -> type[BaseModel]:
        return ExcelInputConfig

    def execute(self, context: Context, config: ExcelInputConfig) -> None:
        # config 已经是强类型，不是裸 dict
        df = read_excel(config.file, config.sheet)
        context.db.insert_table(self.table_name, df)
```

#### 执行上下文

```python
class Context:
    db: SQLiteManager          # 统一的 SQLite 操作层
    params: dict[str, str]     # 运行时参数（文件路径等），由引擎注入
    logger: Logger
    result: ExecutionResult    # 结构化的执行结果统计


class ExecutionResult(BaseModel):
    """结构化的执行结果统计"""
    inputs: dict[str, InputStats]    # key = input name
    processors: list[ProcessorStats] # 按执行顺序
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

### 3.4 类图

```
PluginRegistry (注册中心)
    │
    ├── register(name, plugin_type, cls)
    └── get(name, plugin_type) → Plugin 实例

Context (执行上下文)
    ├── db: SQLiteManager
    ├── params: dict[str, str]
    └── result: ExecutionResult

PipelineEngine (引擎)
    ├── load_config(yaml) → SceneConfig
    ├── collect_params() → list[str]  # 收集所有 param_key
    ├── execute()
    │   ├── for each input: input_plugin.execute()
    │   ├── for each processor: processor_plugin.execute()
    │   └── output_plugin.execute()
    └── cleanup()  # 清理临时 .db
```

### 3.5 错误处理策略

#### 错误分类

| 类别 | 示例 | 处理 |
|------|------|------|
| **配置错误** | YAML 格式错误、缺少必填字段、插件类型不存在 | 启动阶段报错，不执行任何操作 |
| **输入错误** | 文件不存在、文件格式损坏、sheet 不存在 | 终止执行，保留临时 .db 用于调试 |
| **处理错误** | SQL 语法错误、表不存在 | 终止执行，保留临时 .db 用于调试 |
| **输出错误** | 模板文件不存在、磁盘空间不足 | 终止执行，保留临时 .db 用于调试 |

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
  description: 汇总 A 系统人员明细和 B 系统考勤数据，生成月度人员统计报表
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
    source_table: report_data
    columns:
      - source: 姓名
        target: 姓名
      - source: 部门
        target: 部门
      - source: 岗位
        target: 岗位
      - source: 出勤天数
        target: 出勤天数
      - source: 迟到次数
        target: 迟到次数
      - source: 考勤状态
        target: 考勤状态
```

### 4.2 关键字段说明

| 字段 | 说明 |
|------|------|
| `scene.name` | 场景名称，用户选择场景时展示 |
| `scene.version` | 配置版本号，用于未来的配置迁移 |
| `inputs[].name` | 输入名称，用于日志和错误信息 |
| `inputs[].param_key` | 运行时参数名，引擎据此引导用户提供输入文件 |
| `inputs[].table` | 数据写入 SQLite 的表名，SQL 中引用此名 |
| `inputs[].plugin` | 插件类型，对应注册中心中的插件名 |
| `output.config.template` | Excel 模板文件路径，样式由模板定义 |
| `output.config.source_table` | 数据源表名，必须是 processor 创建的表 |
| `output.config.columns` | 列映射列表，`source` 为 SQL 结果列名，`target` 为模板列头名 |

### 4.3 列映射健壮性

- `source` 列必须在 `source_table` 的查询结果中存在，否则 **启动阶段报错终止**
- `target` 列必须与模板文件首行列头匹配，否则 **启动阶段报错终止**
- 列的顺序由配置中 `columns` 的顺序决定，写入模板时按此顺序从左到右填充
- 数据行从模板的第 2 行开始写入（第 1 行为表头，保持不变）

### 4.4 表名冲突检测

配置加载时执行以下校验：

1. 所有 `inputs[].table` 互不相同
2. `inputs[].table` 不与 processor 中 `CREATE TABLE` 的表名冲突
3. `output.config.source_table` 必须存在于 processor 创建的表中

校验失败则报错，不执行。

### 4.5 运行时参数引导

执行时，引擎收集所有 `param_key` 并引导用户提供：

```
$ pipeforge run pipelines/person_monthly_report.yaml

场景: 人员数据月报
汇总 A 系统人员明细和 B 系统考勤数据，生成月度人员统计报表

需要以下输入文件:
  1. person_file (人员明细): ./data/2024-05-persons.xlsx
  2. attendance_file (考勤数据): ./data/2024-05-attendance.xlsx

开始执行...
  [1/4] 读取 人员明细 → 156 行
  [2/4] 读取 考勤数据 → 142 行
  [3/4] 数据合并与统计 → 生成表: report_data
  [4/4] 输出 Excel → ./output/人员月报_202405.xlsx

执行完成，耗时 1.2s
```

也可以通过命令行直接传入参数：

```
$ pipeforge run pipelines/person_monthly_report.yaml \
    --param person_file=./data/persons.xlsx \
    --param attendance_file=./data/attendance.xlsx
```

### 4.6 配置版本兼容

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
│   ├── cli.py                  # CLI 入口
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py           # PipelineEngine 主引擎
│   │   ├── context.py          # 执行上下文
│   │   ├── registry.py         # 插件注册中心
│   │   └── sqlite.py           # SQLite 临时库管理
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── loader.py           # YAML 加载
│   │   └── models.py           # Pydantic 配置模型
│   │
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── base.py             # 抽象基类（泛型 + Pydantic Config）
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
| Excel 读写 | openpyxl | 支持保留模板样式，可逐行读取避免大内存 |
| SQLite | sqlite3 (内置) | 零依赖 |
| CLI | click | 简洁易用 |

> **关于 pandas**：MVP 不使用 pandas。Excel 读取通过 openpyxl 逐行读取，`sqlite3.executemany` 批量写入。好处是依赖小（openpyxl ~2MB vs pandas ~100MB），且避免了将整个 Excel 加载到内存的问题。

> **关于 Jinja2**：移入 v0.2+ 计划。MVP 阶段 SQL 中不使用变量替换，需要动态值时通过 Python 字符串预渲染。

---

## 7. 非功能性需求

| 指标 | 目标 | 说明 |
|------|------|------|
| 数据规模 | 单表 ≤ 10 万行 | openpyxl 逐行读取 + SQLite 批量写入，内存可控 |
| 性能 | 1 万行数据 ≤ 3 秒 | 主要耗时在 openpyxl 读取，SQL 执行极快 |
| 内存 | ≤ 50MB | 不加载整个 Excel 到内存，逐行处理 |
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
| Input | Excel（支持指定 sheet） |
| Processor | SQL（单个，SQLite 执行） |
| Output | Excel（套用模板文件，显式列映射） |
| 配置 | YAML + Pydantic 校验（含表名冲突检测、列映射校验） |
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
| 12 | 列映射显式定义 | `source → target` 映射，启动时校验列存在性和模板匹配 |
| 13 | 临时 .db 存放在 `tempfile` 自动管理 | 使用 Python `tempfile` 模块，执行后自动定位路径 |
| 14 | MVP 单处理器 | `processors` 为列表但只执行一个，v0.2 启用链式遍历 |
| 15 | 无断点重跑（MVP） | 保留临时 .db 足够排查，断点重跑复杂度高于收益 |

---

## 11. 实现计划

| 步骤 | 内容 | 文件 |
|------|------|------|
| 1 | 项目骨架 + 依赖 | `pyproject.toml` |
| 2 | 插件基类（泛型 + Pydantic）+ 注册中心 | `plugins/base.py`, `core/registry.py` |
| 3 | 配置模型（Pydantic）+ YAML 加载 + 表名冲突检测 | `config/models.py`, `config/loader.py` |
| 4 | SQLite 管理（tempfile）+ 上下文 | `core/sqlite.py`, `core/context.py` |
| 5 | 引擎主流程 + 参数收集 + 错误处理 | `core/engine.py` |
| 6 | Excel 输入插件（openpyxl 逐行读取） | `plugins/input/excel.py` |
| 7 | SQL 处理插件 | `plugins/processor/sql.py` |
| 8 | Excel 模板输出插件（显式列映射） | `plugins/output/excel.py` |
| 9 | CLI 入口（交互式引导 + --param） | `cli.py` |
| 10 | 集成测试（含错误路径测试） | `tests/` |

---

## 12. 已解决的待明确事项（来自 v0.1）

| 原问题 | 决策 |
|--------|------|
| SQL 中是否需要变量替换？ | MVP 不需要，v0.2 引入 Jinja2，区分安全变量和用户输入变量 |
| 列映射是纯列名匹配还是配置到单元格坐标？ | 显式 `source → target` 映射，按列顺序从左到右填充，从第 2 行开始写数据 |
| 临时 .db 存放在哪个目录？ | Python `tempfile` 模块自动管理 |
| 是否需要支持处理器依赖关系？ | MVP 单处理器，v0.2 链式执行（顺序依赖） |
