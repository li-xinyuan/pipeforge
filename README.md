# ConfigForge / PipeForge

数据管道配置平台 — 通过可视化向导将多种数据源（Excel、CSV、数据库）加工转换为标准化输出。

## 架构

```
configforge-web (Vue 3)  →  configforge (FastAPI)  →  pipeforge (Python 引擎)
  向导 UI / 配置管理          API 服务 / AI 编排          YAML 驱动的流水线运行时
```

- **PipeForge** — CLI 数据管道框架，YAML 配置 → SQLite 中间层 → openpyxl/CSV 输出
- **ConfigForge** — Web 向导 + API 服务，提供可视化界面和 AI 辅助
- **ConfigForge Web** — Vue 3 + Naive UI + TypeScript 前端

## 快速开始

### 环境要求

- Python ≥ 3.10
- Node.js ≥ 18
- [uv](https://docs.astral.sh/uv/)

### 安装依赖

```bash
# Python 依赖
uv sync

# 前端依赖
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

### 数据源

| 类型 | 说明 |
|------|------|
| Excel (.xlsx/.xls) | 上传本地 Excel 文件，自动解析列名和样本数据 |
| CSV | 支持自定义分隔符和编码（UTF-8/GBK） |
| Database | 连接外部数据库（SQLite/MySQL/PostgreSQL），选择表或编写 SQL 查询 |

### 处理步骤

| 类型 | 说明 |
|------|------|
| SQL | SQLite 查询/过滤/聚合/JOIN，支持多步 DAG 链式执行 |
| Python | 自定义 Python 脚本（`def process(ctx):`），支持数据清洗/API 调用/正则提取 |

### 多步管道

- 多个处理步骤自由串联，引擎按拓扑排序自动执行
- 每个步骤声明输入表/输出表，自动构建依赖关系
- 上一步输出自动作为下一步输入

### AI 辅助

- **AI 编排步骤链** — 自然语言描述需求，AI 自动规划多步 SQL 处理链
- **AI 生成 SQL** — 描述查询需求，AI 生成 SQLite SQL
- **AI 分析列** — 分析文件列结构，推荐列类型和表名
- **AI 列映射** — 智能匹配输入/输出列

支持 OpenAI、Anthropic 及兼容接口。

### 输出格式

- Excel (.xlsx) — 支持模板、自定义列名和 Sheet 名
- CSV — 自定义分隔符

### 数据库连接管理

在「设置 → 数据库连接」页签中管理连接：

- 支持 SQLite（文件路径）、MySQL、PostgreSQL
- 密码使用 Fernet 加密存储
- 连接测试一键验证

## 项目结构

```
├── src/pipeforge/         # PipeForge 运行时引擎
│   ├── config/            # YAML 配置模型
│   ├── core/              # 引擎、SQLite 管理器、上下文
│   └── plugins/           # 输入/处理/输出插件 (excel/csv/sql/python/database)
├── configforge/           # ConfigForge API 服务
│   ├── api/               # REST API 路由
│   ├── core/              # 流水线编排
│   ├── generators/        # 配置生成器
│   ├── models/            # Pydantic 数据模型
│   └── services/          # AI 设置、YAML 构建、连接存储、CSV/Excel 读取
├── configforge-web/       # Vue 3 前端
│   ├── src/
│   │   ├── components/    # UI 组件 (wizard/step2/step3/step4)
│   │   ├── composables/   # API 封装 (useWizardApi/useConfigApi/useFileUpload)
│   │   ├── stores/        # Pinia 状态管理 (wizard)
│   │   ├── types/         # TypeScript 类型定义 (wizard)
│   │   └── utils/         # 工具函数 (serialization/sql)
│   └── tests/             # Vitest 测试
├── tests/                 # PipeForge pytest
└── docs/                  # 设计文档和规格说明
```

## 版本历史

| 版本 | 内容 |
|------|------|
| v0.4.0 | Python 处理器（exec + 超时）、SQL+Python 混合链、filename 标签 |
| v0.3.1 | AI 编排步骤链（自然语言 → 多步 SQL）、错误体验优化 |
| v0.3.0 | 多步 SQL Pipeline + DAG 拓扑排序、处理步骤卡片列表 |
| v0.2.1 | 数据库输入源、安全加固（31 项缺陷修复） |
| v0.2.0 | 前端重设计（单页滚动）、AI SQL 生成、暗色模式、配置管理 |

## 测试

```bash
# 后端测试
uv run pytest configforge/tests/ tests/ -v

# 前端测试
cd configforge-web && npx vitest run

# 类型检查
cd configforge-web && npx vue-tsc --noEmit
```

## 技术栈

- **后端**: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy, openpyxl, Jinja2
- **前端**: Vue 3, TypeScript, Naive UI, Pinia, Vite, Vitest
- **AI**: OpenAI / Anthropic SDK
- **安全**: Fernet 加密 (cryptography), 路径遍历防护, SQL 注入防护, Prompt Injection 过滤
