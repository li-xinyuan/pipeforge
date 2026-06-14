# ConfigForge / PipeForge

让不懂代码的人也能创建可重复的数据处理流程。

## 核心价值

PipeForge 不是另一个数据处理框架——它的护城河是：

1. **ConfigForge 可视化向导** — 零代码创建数据处理配置
2. **YAML 配置文件** — 可版本控制、可审计、可共享
3. **Excel/CSV/Database 输出** — 贴近业务人员的日常工作方式
4. **AI 辅助** — 自然语言描述需求，AI 生成 SQL/Python、规划步骤链

## 架构

```
configforge-web (Vue 3)  →  configforge (FastAPI)  →  pipeforge (Python 引擎)
  向导 UI / 配置管理          API 服务 / AI 编排          YAML 驱动的流水线运行时
```

| 模块 | 技术栈 | 说明 |
|------|--------|------|
| **PipeForge** | Python 3.13, Pydantic v2, SQLite, openpyxl, Jinja2 | CLI 数据管道框架，插件架构 |
| **ConfigForge** | FastAPI, SQLAlchemy, OpenAI/Anthropic SDK | Web API 服务 + AI 编排 |
| **ConfigForge Web** | Vue 3, TypeScript, Naive UI, CodeMirror 6, Pinia, Vite, Vitest | 前端向导 + 配置管理 |

## 快速开始

### 环境要求

- Python ≥ 3.10
- Node.js ≥ 18
- [uv](https://docs.astral.sh/uv/)

### 安装依赖

```bash
uv sync
cd configforge-web && npm install
```

### 启动服务

```bash
# 后端 (默认端口 8000)
uv run uvicorn configforge.server:app --port 8000

# 前端 (默认端口 5173)
cd configforge-web && npm run dev
```

访问 http://localhost:5173 开始使用。

## 功能

### 5 步向导

| 步骤 | 名称 | 说明 |
|------|------|------|
| Step 1 | 场景信息 | 填写场景名称和描述 |
| Step 2 | 输入源 | 上传 Excel/CSV 文件或连接数据库，AI 列分析 |
| Step 3 | 处理步骤 | SQL 查询 / Python 脚本，CodeMirror 语法高亮编辑器，支持多步链式 |
| Step 4 | 输出配置 | Excel/CSV/Database 输出、列映射、文件名 |
| Step 5 | 预览导出 | YAML 语法高亮预览、编辑、下载、执行 |

### 数据源

| 类型 | 说明 |
|------|------|
| Excel (.xlsx/.xls) | 拖拽上传，自动解析列名和样本数据，预览列类型 |
| CSV | 自定义分隔符和编码（UTF-8/GBK），含表头选项 |
| Database | SQLite / MySQL / PostgreSQL，选择表或编写 SQL |

### 处理步骤

| 类型 | 说明 |
|------|------|
| **SQL** | SQLite 查询/过滤/聚合/JOIN/窗口函数，支持多步 DAG 链式执行，快速模板插入 |
| **Python** | `def process(ctx):` 脚本，ctx.db/ctx.params/ctx.logger API，30s 超时保护 |

### 多步管道

```
Input → [Python 清洗] → [SQL 过滤] → [SQL 聚合] → Output
```

- 步骤自由串联，引擎按 DAG 拓扑排序自动执行
- 上一步输出自动作为下一步输入
- 输出表名自动串联（result1 → result2 → result3）
- 预览结果查看每一步的中间数据

### AI 辅助

| 能力 | 说明 |
|------|------|
| **AI 编排步骤链** | 自然语言描述 → AI 规划多步 SQL 处理链 → 确认填入 |
| **AI 生成 SQL** | 描述查询需求，AI 生成 SQLite SQL |
| **AI 分析列** | 分析文件列结构，推荐类型和表名 |
| **AI 列映射** | 智能匹配输入/输出列 |
| **AI 聊天** | 向导内嵌 AI 对话面板 |

支持 OpenAI、Anthropic 及兼容接口。

### 输出格式

| 类型 | 说明 |
|------|------|
| Excel (.xlsx) | 模板输出，自定义列名和 Sheet 名 |
| CSV | 自定义分隔符 |
| Database | MySQL / PostgreSQL / SQLite，支持 append/replace/upsert 模式 |

文件名支持占位符：`{{scene_name}}`、`{{date:%Y%m%d}}`、`{{time:%H%M%S}}`

### 数据库连接管理

设置 → 数据库连接页签：

- SQLite（文件路径）、MySQL、PostgreSQL
- 密码 Fernet 加密存储
- 连接测试一键验证
- 连接可被多个配置引用

### 配置管理

- 配置列表、搜索、复制、删除
- 版本管理（自动保存历史版本，可回滚）
- 执行历史（查看每次执行的状态、时间、日志）
- 定时任务（Cron 表达式调度，支持启用/禁用）

### 安全特性

- SQL 注入防护（SELECT-only 白名单 + DDL/DML 拦截）
- 路径遍历防护（`validate_id()` 校验所有文件路径参数）
- 连接字符串密码脱敏（API 返回时自动隐藏密码）
- 文件上传流式写入（避免大文件 OOM）
- 文件锁（`fcntl.flock` 防止并发读写竞态）
- API Key 认证中间件（可选，默认关闭）
- Pipeline 执行超时保护（signal.alarm）

### UX 特性

- **CodeMirror 6 编辑器** — SQL/Python/YAML 语法高亮、行号、自动补全、暗色主题
- **暗色模式** — 亮色/暗色一键切换，全组件适配（17+ 组件 dark: 变体）
- **脉冲引导动画** — 当前步骤的下一步操作自动闪烁
- **Typewriter 效果** — AI 回复逐字显示
- **Confetti 庆祝** — 成功执行管道时动画
- **列类型预览** — 上传文件后自动显示 INT/NUM/BOOL/DATE/TEXT 颜色标签
- **自动填充** — 文件名、步骤名、SQL 模板自动生成
- **拖拽上传** — 文件拖拽到上传区域直接上传
- **步骤类型统一风格** — Step 2/3/4 类型选择卡片视觉一致

## 项目结构

```
├── src/pipeforge/              # PipeForge 运行时引擎
│   ├── config/                 # YAML 配置模型
│   ├── core/                   # 引擎、SQLite 管理器、上下文、注册表、检查点
│   └── plugins/                # 输入(excel/csv/database)/处理(sql/python)/输出(excel/csv/database)
├── configforge/                # ConfigForge API 服务
│   ├── api/                    # REST 路由 (preview/files/ai/wizard/configs/connections/executions/schedules)
│   ├── core/                   # 流水线编排 (pipeline)
│   ├── generators/             # 配置生成器 (processor/yaml)
│   ├── middleware/              # 中间件 (auth)
│   ├── models/                 # Pydantic 数据模型 (wizard/ai)
│   ├── services/               # AI 设置/orchestrator/yaml_builder/csv_reader/excel_reader
│   ├── utils/                  # 工具 (security/file_lock/error_messages)
│   └── scheduler.py            # APScheduler 定时调度
├── configforge-web/            # Vue 3 前端
│   ├── src/
│   │   ├── components/         # wizard/step2/step3/step4/common/config/ConfettiBurst
│   │   ├── composables/        # useWizardApi/useConfigApi/useFileUpload/useErrorHandler/useApi/useTheme
│   │   ├── stores/             # wizard (Pinia)
│   │   ├── types/              # wizard (TypeScript)
│   │   └── utils/              # serialization/sql/transform
│   ├── tests/                  # Vitest (18 files, 143 tests)
│   └── e2e/                    # Playwright E2E 测试
├── tests/                      # PipeForge pytest
├── configforge/tests/          # ConfigForge pytest
└── docs/                       # 设计文档和规格说明 (superpowers/)
```

## 测试

```bash
# 全部后端测试
uv run pytest configforge/tests/ tests/ -v

# 前端单元测试 (143 tests)
cd configforge-web && npx vitest run

# 前端 E2E 测试
cd configforge-web && npx playwright test

# TypeScript 类型检查
cd configforge-web && npx vue-tsc --noEmit
```

## 版本历史

| 版本 | 内容 |
|------|------|
| **v0.5.0** | 安全加固（47项优化：SQL注入/路径遍历/密码脱敏/文件锁/超时保护）、CodeMirror 6 编辑器（SQL/Python/YAML语法高亮）、暗色模式全组件适配、数据库输出（MySQL/PG/SQLite）、配置版本管理、执行历史、定时任务、步骤类型风格统一、主题持久化修复 |
| **v0.4.0** | Python 处理器（exec + 超时 + ctx API）、SQL+Python 混合 DAG、文件名标签、步骤 3 操作统一 |
| **v0.3.1** | AI 编排步骤链（自然语言 → 多步 SQL）、Typewriter 效果、Confetti 庆祝 |
| **v0.3.0** | 多步 SQL Pipeline + DAG 拓扑排序、处理步骤卡片列表、错误中文提示 |
| **v0.2.1** | 数据库输入源（SQLite/MySQL/PG）、安全加固（31 项缺陷修复） |
| **v0.2.0** | 前端重设计（单页滚动向导）、AI SQL 生成、暗色模式、配置管理、CSV 支持 |

## 路线图

| 阶段 | 状态 | 内容 |
|------|------|------|
| Phase 1 — 夯实基础 | ✅ 完成 | CSV 输入/输出、Jinja2 变量、AI 框架、安全加固、全面测试 |
| Phase 2 — 能力扩展 | ✅ 完成 | 多步 Pipeline、数据库输入/输出、AI 编排、Python 处理器、安全加固、CodeMirror 编辑器 |
| Phase 3 — 平台化 | 📋 计划中 | 配置市场、数据血缘、审计日志、Cron 调度增强、输出格式扩展（PDF/Word/API推送） |
