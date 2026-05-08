# PipeForge + ConfigForge 发展路线图

> 版本: v1.1
> 日期: 2026-05-08
> 状态: 路线图制定完成（经 ROADMAP_REVIEW.md 审核后修订）
> 定位: 开源项目 — 面向社区的数据流水线工具集
>
> **v1.1 变更**: 采纳 ROADMAP_REVIEW.md 6/8 建议 — Phase 1 增加测试加固、Cron 调度边界明确化、补充技术指标、模板市场增加技术方案、时间线调整为 Q2-Q3

---

## 1. 项目定位

PipeForge + ConfigForge 是一个**开源数据流水线工具集**，核心价值是：

> 让不懂代码的人也能通过可视化向导创建可重复执行的数据处理流程。

**护城河**：

1. **ConfigForge 可视化向导** — 零代码创建 Pipeline 配置
2. **YAML 配置文件** — 可版本控制、可审计、可共享
3. **Excel 模板输出** — 贴近业务人员的日常工作方式
4. **插件架构** — 社区可扩展的数据源、处理器、输出格式
5. **AI 辅助** — 降低 SQL 编写和列映射的门槛

**不是**：
- 不是 Pandas/dbt/Airflow 的替代品（面向不同用户群）
- 不是大数据处理引擎（数据处理在 SQLite 中完成，适合中小规模数据）

---

## 2. 当前状态（v0.1）

### PipeForge（CLI 引擎）

| 维度 | 状态 |
|------|------|
| 插件 | Excel 输入 + SQL 处理器 + Excel 输出（3 插件） |
| 测试 | 67 个，全部通过 |
| CLI | `pipeforge run <config.yaml> --param key=value` |
| 设计文档 | 6 轮审核，零缺陷 |

**已知技术债**：

| 问题 | 影响 |
|------|------|
| `InputSpec.config` 硬编码为 `ExcelInputConfig` | 加新输入类型前必须泛型化 |
| `OutputSpec.config` 硬编码为 `ExcelOutputConfig` | 同上 |
| 多步 Pipeline 未实现（列表支持但只执行第一个） | 复杂场景需链式处理 |

### ConfigForge（Web 配置界面）

| 维度 | 状态 |
|------|------|
| 向导 | 5 步：场景信息 → 数据源配置 → 数据处理 → 输出定义 → 预览导出 |
| 后端 API | 8 个端点，26 个测试 |
| 前端 | Vue 3 + Pinia + Vue Router，12 个 E2E 场景 |
| AI | 框架完整，但 LLM 后端未接入（返回 no-op） |

---

## 3. 三阶段路线图

### Phase 1：降低门槛（v0.2，目标：让更多人能用）

**核心目标**：覆盖最常见的数据格式，提供可复用的配置能力，落地 AI 差异化。

| 优先级 | 事项 | 产品 | 说明 |
|--------|------|------|------|
| 🔴 P0 | **CSV 输入插件** | PipeForge | 覆盖第二常见的数据格式。同时重构 `InputSpec.config` 为 Pydantic discriminated union |
| 🔴 P0 | **CSV 输出插件** | PipeForge | 输入/输出对称。CSV 入 → CSV 出是常见轻量场景 |
| 🔴 P0 | **Jinja2 变量替换** | PipeForge | SQL 配置支持 `{{param}}` 模板变量。配置从「一次性」变「可复用」，同一份配置可应对不同月份/参数 |
| 🔴 P0 | **ConfigForge 适配新插件** | ConfigForge | 向导中支持选择 CSV 输入/输出类型，自动推断分隔符和编码 |
| 🟡 P1 | **AI SQL 生成落地** | ConfigForge | 接入真实 LLM 后端（至少一个提供商），用户输入自然语言需求 → AI 生成 SQL 草稿 |
| 🟡 P1 | **Dry-Run 模式** | PipeForge/ConfigForge | AI 生成的 SQL 先在临时 SQLite 试跑，展示前 N 行结果，用户确认后才写入配置 |
| 🟡 P1 | **ConfigForge 测试加固** | ConfigForge | 后端 26 个测试全部通过（已验证）+ 前端关键路径 Vitest 单元测试 |
| 🟡 P1 | **开源门面** | 工程 | README、快速开始指南、示例配置、录屏 GIF |

**Phase 1 交付物**：

```
PipeForge v0.2:
  - 5 插件（Excel 入/出 + CSV 入/出 + SQL 处理器）
  - Jinja2 模板变量
  - Dry-Run 模式
  - 泛型化的 InputSpec/OutputSpec 配置模型

ConfigForge v0.2:
  - 向导支持 CSV 类型
  - AI SQL 生成可用（至少 OpenAI 后端）
  - Dry-Run 预览
  - 后端 26 个测试全部通过 + 前端关键路径 Vitest 测试

工程:
  - README.md（中英双语）
  - docs/getting-started.md
  - demo/ 录屏
  - 测试覆盖率 ≥80%
```

---

### Phase 2：扩展能力（v0.3，目标：让更多人留下来）

**核心目标**：从单步到多步，从手动到自动，从封闭到开放。

| 优先级 | 事项 | 产品 | 说明 |
|--------|------|------|------|
| 🔴 P0 | **多步 Pipeline** | PipeForge | 链式执行多个处理器。引入 `depends_on` 显式依赖声明。中间结果可调试查看 |
| 🔴 P0 | **Plugin SDK** | PipeForge | 标准化的插件开发包：脚手架命令 `pipeforge plugin create`、基类文档、测试工具、示例插件 |
| 🔴 P0 | **数据库输入** | PipeForge | 从 PostgreSQL/MySQL 直接读取数据（sqlalchemy + 连接配置） |
| 🟡 P1 | **Python 脚本处理器** | PipeForge | SQL 无法表达的复杂逻辑（数据清洗、正则提取、自定义计算），沙箱执行 |
| 🟡 P1 | **ConfigForge 适配新能力** | ConfigForge | 向导中支持多步 Pipeline 可视化编排、数据库连接配置 |
| 🟡 P1 | **Cron 调度** | PipeForge | `pipeforge schedule add/list/remove` 管理系统 crontab 条目。不做执行历史、重试、告警、Web 管理。本质是 crontab 的 CLI 封装，不是自建调度器 |

**Phase 2 交付物**：

```
PipeForge v0.3:
  - 多步 Pipeline + DAG 依赖
  - Plugin SDK（脚手架 + 文档 + 示例）
  - 数据库输入插件（PostgreSQL / MySQL）
  - Python 脚本处理器
  - Cron 调度（crontab 封装，不建调度器）

ConfigForge v0.3:
  - 多步 Pipeline 可视化编辑器
  - 数据库连接配置向导
  - 插件安装/管理界面

工程:
  - CONTRIBUTING.md（插件开发指南）
  - 示例插件仓库（作为第三方开发者的参考模板）
```

---

### Phase 3：社区效应（v0.4+，目标：让项目自己生长）

**核心目标**：社区贡献内容、社区贡献代码、社区互相帮助。

| 优先级 | 事项 | 产品 | 说明 |
|--------|------|------|------|
| 🔴 P0 | **配置模板市场** | ConfigForge/Web | 最小可用版：上传/搜索/下载 Pipeline 模板。用户不需要从零配置，搜索「考勤」→ 选择模板 → 上传数据 → 执行 |
| 🔴 P0 | **PipeForge REST API** | PipeForge | PipeForge 作为 HTTP 服务运行，提供远程触发执行和结果查询 |
| 🟡 P1 | **通知推送** | PipeForge | 邮件 + Webhook 输出插件。执行完成后自动分发结果 |
| 🟡 P1 | **多语言支持** | ConfigForge | 界面国际化（至少中英双语），降低非英语用户的入门门槛 |
| 🟢 P2 | **CI/CD 集成** | 生态 | GitHub Action / GitLab CI 插件，`pipeforge run` 作为 CI 步骤 |
| 🟢 P2 | **Python/JS SDK** | 生态 | 编程式创建和执行 Pipeline |

**Phase 3 交付物**：

```
PipeForge v0.4+:
  - REST API 服务模式
  - 邮件/Webhook 推送输出插件

ConfigForge v0.4+:
  - 配置模板市场 Web 页面
  - 国际化（中英双语）

生态:
  - GitHub Action 官方插件
  - pipeforge-sdk (Python)
```

---

## 4. 每阶段的架构影响

### Phase 1 关键架构变更

**Pydantic Discriminated Union**（解决 `InputSpec.config` 硬编码问题）：

```python
# 当前（v0.1）
class InputSpec(BaseModel):
    config: ExcelInputConfig  # 硬编码

# Phase 1（v0.2）
class InputSpec(BaseModel):
    config: ExcelInputConfig | CsvInputConfig  # discriminated union
```

```python
# CsvInputConfig
class CsvInputConfig(BaseModel):
    type: Literal["csv"] = "csv"
    file: str | None = None
    delimiter: str = ","
    encoding: str = "utf-8"
    has_header: bool = True
```

**Jinja2 模板变量**：

```yaml
# 之前：SQL 硬编码
processors:
  - plugin: sql
    config:
      sql: "SELECT * FROM person WHERE month = '2026-05'"

# 之后：模板变量
processors:
  - plugin: sql
    config:
      sql: "SELECT * FROM person WHERE month = '{{target_month}}'"

# 执行时注入
pipeforge run pipeline.yaml --param target_month=2026-05
```

### Phase 2 关键架构变更

**Pipeline DAG**：

```yaml
processors:
  - name: 清洗人员数据
    plugin: sql
    output_tables: [clean_person]
    config:
      sql: "CREATE TABLE clean_person AS SELECT * FROM person WHERE status = 'active'"

  - name: 清洗考勤数据
    plugin: sql
    output_tables: [clean_attendance]
    config:
      sql: "CREATE TABLE clean_attendance AS SELECT * FROM attendance WHERE year = {{year}}"

  - name: 合并统计
    plugin: sql
    depends_on: [clean_person, clean_attendance]
    output_tables: [monthly_report]
    config:
      sql: >
        CREATE TABLE monthly_report AS
        SELECT p.name, p.dept, a.attendance_rate
        FROM clean_person p
        LEFT JOIN clean_attendance a ON p.id = a.person_id
```

**Plugin SDK 脚手架**：

```bash
$ pipeforge plugin create --type input --name mongodb

Generated: plugins/input/mongodb/
├── __init__.py       # @register_plugin("mongodb", "input")
├── config.py         # MongodbInputConfig(BaseModel)
├── plugin.py         # MongodbInputPlugin(InputPlugin[MongodbInputConfig])
└── tests/
    └── test_mongodb.py
```

### Phase 3 关键架构变更

**配置模板市场**：

采用 **Git 仓库 + CLI 分发** 的最小可用方案，不建 Web 服务：

1. **存储**：独立 Git 仓库 `pipeforge-templates`，Monorepo 结构
2. **元数据**：每个模板目录下的 `metadata.yaml` 定义标签、适用场景、输入格式
3. **分发**：`pipeforge template search "考勤"` / `pipeforge template install monthly-attendance`
4. **适配检测**：上传用户 Excel 后，计算列名与模板期望列的 Jaccard 相似度，≥60% 视为匹配

```
pipeforge-templates/              # Git 仓库（社区贡献）
├── monthly-attendance/           # 月度考勤报表
│   ├── pipeline.yaml             # 模板配置（含 {{param}} 变量）
│   ├── template.xlsx             # 输出模板
│   ├── metadata.yaml             # 元数据
│   │    标签: [考勤, HR, 月度]
│   │    场景: 汇总人员明细和考勤数据，生成月度报表
│   │    输入: [人员明细.xlsx, 考勤数据.xlsx]
│   │    期望列: {人员明细: [工号, 姓名, 部门], 考勤数据: [工号, 出勤天数]}
│   └── README.md                 # 使用说明
├── financial-reconciliation/     # 财务对账
│   └── ...
```

---

## 5. 与 NEXT_STEPS.md 的主要差异

| 维度 | NEXT_STEPS.md | 本路线图 | 理由 |
|------|-------------|---------|------|
| Plugin SDK 优先级 | Phase 2 🟢（最低） | Phase 2 🔴（最高） | 没有 SDK 永远不会有社区贡献者 |
| 配置市场时机 | Phase 3 🔴 | Phase 3 🔴 | 一致。但本路线图强调「最小可用版」而非完整社区平台 |
| 企业功能 | Phase 3 含多个企业项 | 全部移除 | 开源阶段不需要审计/SSO/多租户。商业化时再考虑 |
| 调度方案 | 三选一（cron/APScheduler/Airflow） | 只选系统 cron | 不自建调度器，不自找运维麻烦 |
| 数据血缘 | 「最有价值的企业功能」 | 不纳入路线图 | 实现复杂度极高，ROI 不适合开源阶段 |
| Jinja2 变量替换 | Phase 1 | Phase 1 | 一致。但本路线图强调它与「配置可复用」的直接关系 |
| Dry-Run 模式 | §五 AI 部分 | Phase 1 P1 | 重要性提升。开源项目用户信任建立在「预览后确认」上 |

---

## 6. 里程碑节点

```
2026 Q2-Q3 ── v0.2 Phase 1 ── CSV 入/出 + Jinja2 + AI SQL + Dry-Run（预计 2-3 个月）
                                    ↓
2026 Q4 ──── v0.3 Phase 2 ── 多步 Pipeline + Plugin SDK + DB 输入
                                    ↓
2027 Q1 ──── v0.4 Phase 3 ── 配置模板市场 + REST API + 通知推送
```

> 时间线为粗略估计，实际进度取决于贡献者的参与程度。Phase 1 由核心团队完成，Phase 2 起需要社区贡献者参与。

---

## 7. 不做的事情（明确排除）

| 事项 | 理由 |
|------|------|
| **大数据处理**（Spark/Flink 集成） | 定位为中小规模数据处理，不和已有大数据生态竞争 |
| **实时流处理** | PipeForge 是批处理工具，不是流处理引擎 |
| **自建调度器** | 运维负担重。优先集成系统 cron，未来对接 Airflow/Prefect |
| **PDF/PPT 输出** | 依赖重、场景窄。让社区通过 Plugin SDK 自行开发 |
| **内网部署方案** | 先做好单机体验。云化/容器化是商业化的方向 |
| **数据血缘追踪** | 工程复杂度极高，ROI 不在开源阶段体现 |
| **SSO/LDAP 集成** | 企业功能，非开源核心 |

---

## 8. 成功指标

| 阶段 | 社区指标 | 技术指标 |
|------|---------|---------|
| Phase 1 | GitHub 100+ stars，5+ 外部 issue/PR，5 分钟跑通第一个 demo | PipeForge 测试覆盖率 ≥80%，ConfigForge 后端 26 个测试全部通过，前端关键路径 Vitest 测试通过 |
| Phase 2 | 3+ 社区贡献的插件，Plugin SDK 文档被外部引用 | `pipeforge plugin create` 到可运行 < 10 分钟，SDK 文档覆盖全部公开 API |
| Phase 3 | 配置模板市场 20+ 模板，10+ 活跃社区贡献者 | REST API 响应时间 < 500ms（不含 SQL 执行），模板搜索 < 1s |
