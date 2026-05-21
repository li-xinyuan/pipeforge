# ConfigForge / PipeForge

数据管道配置平台 — 通过可视化向导将多种数据源（Excel、CSV、数据库）加工转换为标准化输出。

## 架构

```
configforge-web (Vue 3)  →  configforge (FastAPI)  →  pipeforge (Python 引擎)
  向导 UI / 配置管理          API 服务 / 编排            YAML 驱动的流水线运行时
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

### SQL 处理

- 编写 SQL 查询语句对输入数据进行加工
- 支持 CREATE TABLE AS SELECT、INSERT INTO 等 DDL
- 裸 SELECT 语句自动包装为 CREATE TABLE AS

### AI 辅助

- AI 生成 SQL — 自然语言描述查询需求
- 场景推断 — 自动识别字段含义
- 列映射建议 — 智能匹配输入/输出列

支持 OpenAI、Anthropic 及兼容接口。

### 输出格式

- Excel (.xlsx) — 支持模板、自定义列名和 Sheet 名
- CSV — 自定义分隔符

### 数据库连接管理

在「设置 → 数据库连接」页签中管理连接：

- 支持 SQLite（文件路径）、MySQL、PostgreSQL
- 密码使用 Fernet 加密存储
- 连接测试一键验证
- 连接可被多个配置引用

## 项目结构

```
├── src/pipeforge/         # PipeForge 运行时引擎
│   ├── config/            # YAML 配置模型
│   ├── core/              # 引擎、SQLite 管理器、上下文
│   └── plugins/           # 输入/处理/输出插件
├── configforge/           # ConfigForge API 服务
│   ├── api/               # REST API 路由
│   ├── core/              # 流水线编排
│   ├── generators/        # 配置生成器
│   ├── models/            # Pydantic 数据模型
│   └── services/          # 连接存储、AI 设置、YAML 构建
├── configforge-web/       # Vue 3 前端
│   ├── src/
│   │   ├── components/    # UI 组件
│   │   ├── composables/   # API 封装
│   │   ├── stores/        # Pinia 状态管理
│   │   └── types/         # TypeScript 类型定义
│   └── tests/             # Vitest 测试
└── docs/                  # 设计文档和规格说明
```

## 测试

```bash
# 后端测试
uv run pytest configforge/tests/ -v

# 前端测试
cd configforge-web && npx vitest run

# 类型检查
cd configforge-web && npx vue-tsc --noEmit
```

## 技术栈

- **后端**: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy, openpyxl, Jinja2
- **前端**: Vue 3, TypeScript, Naive UI, Pinia, Vite, Vitest
- **AI**: OpenAI / Anthropic SDK
- **安全**: Fernet 加密 (cryptography), 路径遍历防护
