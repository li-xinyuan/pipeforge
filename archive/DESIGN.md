# PipeForge 设计文档

> 版本: v0.1  
> 日期: 2026-05-03  
> 状态: 设计完成，待实现

---

## 1. 愿景

构建一个 **场景固化 → 可重复执行 → 结果稳定** 的数据流水线框架。

解决的核心痛点：AI 助手每次都能帮忙解决数据处理问题，但解决方案无法固化，下次同样的场景还得重新描述需求。PipeForge 通过配置文件将输入-处理-输出的过程固定下来，让后续执行只需提供输入数据即可得到格式固定、目标一致的结果。

---

## 2. 使用场景

日常办公数据处理，例如：
- 从 A 系统导出 Excel，经过字段映射/格式转换后，生成 B 系统要求的导入模板
- 从多个数据源（Excel + API + 数据库查询）汇总数据，生成统计报表
- 对现有数据进行查询、统计、分析，形成固定格式的报表文件

### 核心用户旅程

**第一次（场景创建）**：
```
AI 问：你想做什么？
你描述：从 A 系统导 Excel，转换后导入 B 系统
AI 问：要保留哪些字段？转换规则是什么？
你回答...
AI 问：输出格式要求？
你回答...
→ 生成 PipeForge 配置 + Excel 模板
→ 保存到 pipelines/
```

**后续使用（场景执行）**：
```
用户选择场景 "人员数据月报"
AI：请上传本月人员明细 Excel
AI：请上传本月考勤数据 Excel
→ 执行配置
→ 输出格式一致的报表文件
（不需要重新解释需求）
```

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
| **工厂模式** | PluginFactory 根据配置中的 `type` 创建对应插件实例 |
| **责任链** | 多个 Processor 串联执行，前一个输出是后一个输入 |
| **建造者模式** | 从 YAML 配置构建可执行的 Pipeline |
| **注册模式** | 插件通过装饰器注册到全局注册中心，支持扩展 |

### 3.3 接口设计

```python
# 插件基类 — 所有插件实现统一的生命周期
class Plugin(ABC):
    name: str  # 插件标识名

    @abstractmethod
    def execute(self, context: Context, config: dict) -> None:
        pass

# 执行上下文
class Context:
    db: SQLiteManager          # 统一的 SQLite 操作层
    params: dict               # 运行时参数（文件路径等）
    variables: dict            # 流程变量（时间、环境变量等）
    logger: Logger
    result: dict               # 执行结果统计（行数、耗时）
```

### 3.4 类图

```
PluginRegistry (注册中心)
    │
    ├── register(name, cls)
    └── get(name) → Plugin 实例

Context (执行上下文)
    ├── db: SQLiteManager
    ├── params: dict
    └── logger

PipelineEngine (引擎)
    ├── load_config(yaml) → SceneConfig
    ├── resolve_params()  # 收集运行时所需参数
    ├── execute()
    │   ├── input.execute()   # N 次，多源
    │   ├── processor.execute()
    │   └── output.execute()
    └── cleanup()         # 清理临时 .db
```

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
      - 姓名
      - 部门
      - 岗位
      - 出勤天数
      - 迟到次数
      - 考勤状态
```

### 4.2 关键字段说明

| 字段 | 说明 |
|------|------|
| `scene.name` | 场景名称，用户选择场景时展示 |
| `inputs[].param_key` | 运行时参数名，引擎据此引导用户提供输入文件 |
| `inputs[].table` | 数据写入 SQLite 的表名 |
| `output.config.template` | Excel 模板文件路径，样式由模板定义 |
| `output.config.columns` | 输出列的顺序，对应模板的列头 |

### 4.3 运行时参数引导

执行时，引擎收集所有 `param_key` 并引导用户提供：

```
PipeForge 执行 person_monthly_report.yaml
→ 需要参数: person_file (人员明细Excel)
→ 需要参数: attendance_file (考勤数据Excel)
→ 请提供 person_file 路径: ./data/2024-05-persons.xlsx
→ 请提供 attendance_file 路径: ./data/2024-05-attendance.xlsx
→ 执行中...
→ 输出: ./output/人员月报_202405.xlsx
```

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
│   │   ├── base.py             # 抽象基类
│   │   ├── input/
│   │   │   ├── __init__.py
│   │   │   ├── excel.py        # Excel 输入
│   │   │   └── csv.py          # CSV 输入（预留）
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
| 配置解析 | Pydantic v2 | 强类型校验，AI 生成代码质量高 |
| YAML | PyYAML | 标准方案 |
| Excel 读写 | openpyxl | 支持保留模板样式 |
| SQLite | sqlite3 (内置) | 零依赖 |
| DataFrame | pandas | 读 Excel → 写 SQLite 的标准方案 |
| CLI | click | 简洁易用，AI 生成质量高 |
| 模板变量 | Jinja2 | SQL 中支持 `{{param}}` 变量替换 |

---

## 7. 可扩展性设计

| 扩展点 | 方案 |
|--------|------|
| 新输入源 | 实现 `InputPlugin` 基类，注册到 registry |
| 新输出格式 | 实现 `OutputPlugin` 基类，注册到 registry |
| 新处理器 | 实现 `ProcessorPlugin` 基类，注册到 registry |
| 插件自动发现 | Python `importlib` + entry_points |
| 变量替换 | SQL 中支持 `{{param}}`、`{{date}}`、`{{env.VAR}}` |
| 数据校验 | 未来集成 Pydantic schema 或 Great Expectations |
| 增量处理 | Context 中维护 checkpoint |
| 可视化配置 | 未来基于 YAML schema 生成前端表单 |

---

## 8. 版本规划

### v0.1 MVP（第一个版本）

| 阶段 | 实现 |
|------|------|
| Input | Excel（支持指定 sheet） |
| Processor | SQL（SQLite 执行） |
| Output | Excel（套用模板文件，按列映射输出） |
| 配置 | YAML + Pydantic 校验 |
| CLI | `pipeforge run <scene.yaml>` |

### v0.2+ 后续迭代

- CSV 输入/输出
- API 输入/输出
- SQL 中的 Jinja2 变量替换
- 多处理器链式执行
- 执行日志与结果统计
- 数据校验

---

## 9. 决策记录

| # | 决策 | 理由 |
|---|------|------|
| 1 | 项目名：PipeForge | 管道锻造，暗示将输入-处理-输出"锻造"成稳定流程 |
| 2 | 项目形态：CLI + 配置文件 | 独立于 AI 工具运行，任何人/任何模型都能复用配置 |
| 3 | 技术栈：Python | 数据处理生态成熟，AI coding 能力最强 |
| 4 | 配置文件生产：AI 生成 → 逐步优化到可视化 | 先用 AI 降低门槛，后续降低使用成本 |
| 5 | 复杂逻辑：SQL 处理 | SQL 天然支持筛选、JOIN、聚合、CASE，比 YAML 规则更强大 |
| 6 | SQLite 临时库：每次执行新建临时 .db，执行后清理 | 隔离、安全、无残留 |
| 7 | 多输入、单输出 | 多输入是常见场景；多输出可用多个 Pipeline 解决 |
| 8 | Excel 模板输出：方式 A（用户提供真实模板） | 样式完全由用户控制，结果格式固定 |
| 9 | 配置校验：Pydantic | 启动前发现配置错误，避免运行时崩溃 |
| 10 | 使用者假设有基础编程技能 | 可以编写 SQL，理解 YAML 配置 |

---

## 11. 实现计划

| 步骤 | 内容 | 文件 |
|------|------|------|
| 1 | 项目骨架 + 依赖 | `pyproject.toml` |
| 2 | 插件基类 + 注册中心 | `plugins/base.py`, `core/registry.py` |
| 3 | 配置模型（Pydantic）| `config/models.py`, `config/loader.py` |
| 4 | SQLite 管理 + 上下文 | `core/sqlite.py`, `core/context.py` |
| 5 | 引擎主流程 | `core/engine.py` |
| 6 | Excel 输入插件 | `plugins/input/excel.py` |
| 7 | SQL 处理插件 | `plugins/processor/sql.py` |
| 8 | Excel 模板输出插件 | `plugins/output/excel.py` |
| 9 | CLI 入口 | `cli.py` |
| 10 | 集成测试 | `tests/` |

---

## 12. 待明确事项

以下事项在实现过程中逐步明确：

- [ ] SQL 中是否需要变量替换（如 `{{date}}`）支持？MVP 可以暂时不需要
- [ ] Excel 模板输出的列映射是纯列名匹配，还是需要配置到模板单元格坐标？
- [ ] 临时 .db 文件存放在哪个目录？（建议 `tempfile` 自动管理）
- [ ] 是否需要支持处理器的执行顺序/依赖关系？（MVP 假设单处理器）
