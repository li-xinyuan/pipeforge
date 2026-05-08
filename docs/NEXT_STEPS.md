# PipeForge + ConfigForge 下一步开发方向

> 日期: 2026-05-03  
> 基于对项目设计文档（6 轮审核）+ 代码实现 + 测试的深度理解

---

## 一、数据源扩展（从 Excel 到万物）

**现状**：只支持 Excel 输入，所有数据最终汇入 SQLite。

| 数据源 | 场景 | 技术方案 | 价值 |
|--------|------|---------|------|
| **CSV/TSV** | 日志文件、数据导出 | Python csv 模块，逐行读取 | 低门槛，覆盖最常见格式 |
| **数据库直连** | MySQL/PostgreSQL/Oracle 企业数据 | sqlalchemy + 连接池 | 打通企业数据孤岛，不需要先导出再导入 |
| **API 拉取** | ERP/CRM 系统数据 | httpx + 分页 + 认证 | 自动化数据采集，消除手工导出 |
| **JSON/XML** | API 返回值、配置文件 | ijson 流式解析 | 半结构化数据处理 |
| **Google Sheets** | 协作表格 | Google Sheets API v4 | 团队协作场景，实时数据 |
| **邮件附件** | 定期报表自动提取 | imaplib + 附件解析 | 自动化周期性报表处理 |

**核心挑战**：不是技术实现，而是**统一的数据模型**。当前 `read_excel_rows` 返回 `(columns, rows)` 元组，所有数据源都需要适配这个接口。建议抽象出 `DataSource` 协议：

```python
class DataSource(Protocol):
    def columns(self) -> list[str]: ...
    def rows(self) -> Iterator[tuple]: ...
    def close(self) -> None: ...
```

---

## 二、处理能力升级（从 SQL 到混合处理）

**现状**：只有 SQL 处理器，所有逻辑必须用 SQL 表达。

| 处理器 | 解决的痛点 | 示例场景 |
|--------|----------|---------|
| **Jinja2 模板** | SQL 中硬编码条件 | `WHERE month = {{current_month}}` 动态参数 |
| **Python 脚本** | SQL 难以表达的复杂逻辑 | 数据清洗、正则提取、自定义计算 |
| **多步 Pipeline** | 单条 SQL 不够，需要链式处理 | 先清洗 → 再聚合 → 再格式化 |
| **条件分支** | 根据数据特征走不同路径 | 如果有"离职日期"列走 A 逻辑，否则走 B |
| **跨库 JOIN** | 数据来自不同系统 | MySQL 用户表 JOIN Excel 订单表 |

**核心升级：Pipeline DAG**

多步 Pipeline 是最核心的升级。当前 `processors` 设计为列表但 MVP 只执行第一个。实现链式执行需要解决：

1. **中间表命名**：Step 1 输出 `step1_result`，Step 2 从 `step1_result` 读取
2. **错误传播**：Step 3 失败时，Step 1/2 的结果是否保留？
3. **性能**：每步都写 SQLite 再读出来，N 步就是 N 次 I/O
4. **调试**：用户如何查看中间步骤的结果？

建议引入 **Pipeline DAG**（有向无环图），而非简单的线性列表：

```yaml
processors:
  - name: 清洗人员数据
    plugin: sql
    output_tables: [clean_person]
    config:
      sql: "CREATE TABLE clean_person AS SELECT * FROM person WHERE ..."

  - name: 清洗考勤数据
    plugin: sql
    output_tables: [clean_attendance]
    config:
      sql: "CREATE TABLE clean_attendance AS SELECT * FROM attendance WHERE ..."

  - name: 合并统计
    plugin: sql
    depends_on: [clean_person, clean_attendance]  # 显式依赖
    output_tables: [monthly_report]
    config:
      sql: "CREATE TABLE monthly_report AS SELECT ... FROM clean_person JOIN clean_attendance ..."
```

---

## 三、输出格式扩展（从 Excel 到多渠道分发）

**现状**：只支持 Excel 模板输出。

| 输出格式 | 场景 | 技术方案 |
|---------|------|---------|
| **CSV** | 数据交换、导入其他系统 | Python csv 模块 |
| **PDF** | 正式报告、打印 | reportlab 或 WeasyPrint |
| **Word/Docx** | 公文、合同 | python-docx + 模板 |
| **PPT** | 汇报演示 | python-pptx + 模板 |
| **HTML 邮件** | 定期报表推送 | Jinja2 HTML 模板 + SMTP |
| **数据库写入** | ETL 入仓 | sqlalchemy INSERT |
| **API 推送** | 写回 ERP/CRM | httpx POST |
| **钉钉/企微/飞书** | 国内企业通知 | Webhook + Markdown 卡片 |

**最有价值的扩展不是更多文件格式，而是推送能力**。当前 PipeForge 是「拉」模式（用户主动执行），加上推送就变成「推」模式（定时执行 + 自动分发）。这直接打开了**自动化报表**场景：

```
cron 定时触发 → PipeForge 执行 → 生成 Excel + PDF
  → 邮件发送给管理层
  → 钉钉群推送摘要
  → 写入数据库存档
```

---

## 四、调度与自动化（从手动到自动）

**现状**：用户手动执行 `pipeforge run pipeline.yaml`。

| 能力 | 说明 |
|------|------|
| **Cron 调度** | 内置定时执行，`pipeforge schedule "0 9 * * 1" pipeline.yaml`（每周一早9点） |
| **文件监控** | 监控目录，新文件到达自动触发 |
| **事件驱动** | API 触发执行，与其他系统集成 |
| **执行历史** | 每次执行的日志、耗时、行数统计 |
| **失败重试** | 自动重试 + 告警通知 |
| **依赖调度** | Pipeline A 完成后触发 Pipeline B |

**调度是 PipeForge 从「工具」升级为「平台」的关键**。但自建调度器是坑（时区、分布式、幂等性），建议：

- **轻量方案**：集成系统 cron + `pipeforge run`，不自己造轮子
- **中等方案**：内置 APScheduler，支持简单定时 + 文件监控
- **重量方案**：对接 Airflow/Prefect/Dagster，PipeForge 作为其中的一个 Operator

---

## 五、AI 深度集成（从辅助到智能）

**现状**：ConfigForge 有 AI 建议框架但返回 no-op。

| AI 能力 | 场景 | 实现难度 |
|---------|------|---------|
| **SQL 生成** | 用户描述需求 → AI 生成 SQL | 中 |
| **列映射推荐** | 上传模板后自动匹配源列 | 低（规则 + 少量 AI） |
| **异常检测** | 执行后检测数据异常（空值率激增、数值越界） | 中 |
| **配置补全** | 用户填了 Step 1/2 → AI 推断 Step 3/4 | 中 |
| **自然语言查询** | "帮我找出本月出勤率低于80%的部门" → 自动生成完整 Pipeline | 高 |
| **数据解读** | 执行后 AI 生成数据摘要和洞察 | 中 |
| **错误修复建议** | SQL 报错 → AI 分析原因并建议修复 | 中 |

**AI 集成的关键不是技术，而是信任**。用户不敢让 AI 直接改数据，所以最佳模式是 **AI 建议 + 人工确认**：

1. AI 生成 SQL → 用户在 ConfigForge 中预览效果 → 确认后写入配置
2. AI 推荐列映射 → 用户检查匹配正确性 → 一键采纳
3. AI 检测异常 → 标记可疑数据 → 用户决定是否处理

建议引入 **Dry-Run 模式**：AI 生成的处理逻辑先在临时 SQLite 上试运行，展示前 N 行结果，用户确认后才正式执行。

---

## 六、协作与共享（从个人到团队）

**现状**：单机工具，配置文件本地管理。

| 能力 | 说明 |
|------|------|
| **配置市场** | 社区共享 Pipeline 模板（如「月度考勤报表」「财务对账」） |
| **团队空间** | 多人共享配置、模板、数据源连接 |
| **版本管理** | 配置变更历史、回滚、diff |
| **权限控制** | 谁能创建配置、谁能执行、谁能修改 |
| **审批流程** | 配置修改需审批后生效 |

**配置市场是最有差异化的方向**。想象一个场景：

> 新来的 HR 不需要从零配置「月度考勤报表」，只需要从市场搜索"考勤"，选择一个评分最高的模板，上传自己的 Excel 文件，一键执行。

这需要：
1. **模板标准化**：定义模板元数据（适用行业、输入格式、输出格式）
2. **质量评分**：基于使用量、评分、成功率
3. **适配检测**：自动检测用户的 Excel 是否匹配模板的输入要求

---

## 七、企业级能力（从工具到平台）

| 能力 | 说明 |
|------|------|
| **数据安全** | 敏感列脱敏（如身份证号、手机号）、加密存储 |
| **审计日志** | 谁在什么时候执行了什么配置，处理了多少行数据 |
| **数据血缘** | 输出报表的每个数字可以追溯到源数据的哪一行 |
| **合规留存** | 执行结果归档，满足监管要求 |
| **多租户** | 不同部门隔离数据和配置 |
| **SSO 集成** | 对接企业 LDAP/OAuth |

**数据血缘是最有价值的企业功能**。当前 PipeForge 的处理是黑盒——用户只知道「输出了 monthly_report.xlsx」，但不知道「C2 单元格的 95% 出勤率来自 person.xlsx 的第 3 行和 attendance.xlsx 的第 15 行」。实现血缘追踪需要：

1. 在 SQL 执行时记录每行的来源（SQLite 的 `rowid`）
2. 在输出时标记每个单元格的溯源信息
3. 提供溯源查询 UI（点击单元格 → 显示来源链路）

---

## 八、开发者生态（从封闭到开放）

| 方向 | 说明 |
|------|------|
| **Plugin SDK** | 标准化的插件开发包，含脚手架、测试工具、文档 |
| **CLI 插件机制** | `pipeforge plugin install csv-input` 从 PyPI 安装 |
| **Webhook** | 执行完成/失败时回调外部系统 |
| **REST API** | PipeForge 作为服务运行，提供执行/查询 API |
| **SDK（Python/JS）** | 编程式创建和执行 Pipeline |
| **CI/CD 集成** | GitHub Action / GitLab CI 插件 |

**Plugin SDK 是生态的基础**。当前插件开发需要理解 PipeForge 内部结构，门槛高。建议：

```bash
# 脚手架
pipeforge plugin create --type input --name mongodb

# 自动生成：
# plugins/input/mongodb/
# ├── __init__.py        # 注册装饰器
# ├── mongodb.py         # 插件实现
# ├── config.py          # Pydantic 配置模型
# └── tests/             # 测试模板
```

---

## 九、优先级建议

根据**投入产出比**和**战略价值**，建议分三个阶段：

### 第一阶段：夯实基础（1-2 个月）

| 优先级 | 方向 | 理由 |
|--------|------|------|
| 🔴 | **修复 P0-1**（5步vs4步） | 设计一致性 |
| 🔴 | **CSV 输入/输出** | 最低成本的格式扩展，覆盖大量场景 |
| 🔴 | **Jinja2 变量替换** | 解决 SQL 硬编码痛点，是用户最常提的需求 |
| 🟡 | **ConfigForge 测试** | 当前 0 个前端测试，质量无保障 |
| 🟡 | **AI SQL 生成**（MVP） | ConfigForge 的核心差异化功能 |

### 第二阶段：能力扩展（2-4 个月）

| 优先级 | 方向 | 理由 |
|--------|------|------|
| 🔴 | **多步 Pipeline（链式执行）** | 从单步到多步是质变 |
| 🔴 | **数据库输入** | 打通企业数据源 |
| 🟡 | **Cron 调度** | 从手动到自动 |
| 🟡 | **邮件/钉钉推送** | 报表自动分发 |
| 🟡 | **Python 处理器** | SQL 表达不了的逻辑 |
| 🟢 | **Plugin SDK** | 降低扩展门槛 |

### 第三阶段：平台化（4-8 个月）

| 优先级 | 方向 | 理由 |
|--------|------|------|
| 🔴 | **配置市场** | 差异化竞争力，网络效应 |
| 🟡 | **数据血缘** | 企业级核心需求 |
| 🟡 | **审计日志 + 权限** | 企业合规 |
| 🟢 | **REST API + SDK** | 开发者生态 |
| 🟢 | **自然语言查询** | AI 深度集成 |

---

## 十、核心定位思考

PipeForge 的核心价值到底是什么？

如果答案是「数据处理」，那竞争对手是 Pandas/dbt/Airflow，PipeForge 没有优势。

如果答案是**「让不懂代码的人也能创建可重复的数据处理流程」**，那 PipeForge 的护城河是：

1. **ConfigForge 的可视化向导** — 零代码创建配置
2. **YAML 配置文件** — 可版本控制、可审计、可共享
3. **Excel 模板输出** — 贴近业务人员的日常工作方式
4. **配置市场** — 社区知识积累

所以下一步最应该投入的方向是：**让 ConfigForge 的体验足够好，让配置市场足够丰富，让不懂 SQL 的人也能通过 AI + 模板创建 Pipeline。**
