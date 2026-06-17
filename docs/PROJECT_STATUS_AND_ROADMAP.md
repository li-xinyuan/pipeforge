# ConfigForge 项目状态报告与下一步工作计划

> 扫描日期：2026-06-17  
> 当前版本：v0.5.0  
> 代码统计：后端 103 个 Python 文件（pipeforge 25 + configforge 78）/ 前端 40 个 Vue + 15 个 TS 文件  
> 测试覆盖：后端 405 个测试（pipeforge 168 + configforge 237）/ 前端 143 个单元测试 + 12 个 E2E 测试

---

## 一、项目目标

**ConfigForge（PipeForge）** 是一个数据管道配置向导，核心使命是：

> 让不懂代码的人也能创建可重复的数据处理流程

### 核心护城河

| 护城河 | 说明 |
|--------|------|
| 可视化向导 | 5 步配置向导，零代码创建数据处理配置 |
| YAML 配置文件 | 可版本控制、可审计、可共享的配置格式 |
| 多格式输出 | Excel / CSV / Database，贴近业务人员工作方式 |
| AI 辅助 | 自然语言生成 SQL/Python、列分析、列映射、步骤编排、预检 |

### 三层架构

```
configforge-web (Vue 3)  →  configforge (FastAPI)  →  pipeforge (Python 引擎)
  向导 UI / 配置管理          API 服务 / AI 编排          YAML 驱动流水线运行时
```

---

## 二、现阶段实现情况

### 2.1 已完成功能清单

#### 数据输入（3 种）
- [x] Excel 输入（.xlsx，自动读取工作表）
- [x] CSV 输入（自定义分隔符、编码自动检测）
- [x] Database 输入（SQLite / MySQL / PostgreSQL，连接管理）

#### 数据处理（2 种，支持多步 DAG 链式）
- [x] SQL 处理器（多步 Pipeline + DAG 拓扑排序）
- [x] Python 处理器（exec 沙箱 + 超时 + ctx API）
- [x] SQL + Python 混合 DAG

#### 数据输出（3 种）
- [x] Excel 输出（模板填充 + 自动生成模板）
- [x] CSV 输出
- [x] Database 输出（append / replace / upsert，MySQL/PG/SQLite）

#### AI 辅助（8 个 category）
- [x] `scene` — 场景描述推断
- [x] `columns` — 列类型/表名/参数键/关联键推荐
- [x] `sql` — 自然语言转 SQL
- [x] `mapping` — 列映射推断
- [x] `diagnose` — 执行后错误诊断
- [x] `precheck` — 执行前配置完整性审查（v0.5.1 新增）
- [x] `orchestrate` — 多步骤处理链规划
- [x] `chat` — 向导内嵌对话助手

#### AI 交互体验（v0.5.1 新增）
- [x] 统一 AI 触发按钮组件（AiTriggerButton，✨ 渐变虚线样式）
- [x] GuidePanel 指路式引导（每步提示 AI 功能位置）
- [x] Step 5 AI 预检配置（issues 分色显示 + 步骤标注）

#### 配置管理
- [x] 配置 CRUD + 分页搜索
- [x] 版本管理（自动递增、版本对比、回滚）
- [x] 执行历史（分页查询、输出下载、记录删除）
- [x] 定时任务（Cron 表达式、启停切换、下次运行时间）

#### 安全特性（12 项）
- [x] SQL 注入防护（SELECT-only 白名单 + DDL/DML 正则拦截）
- [x] 路径遍历防护（URL 编码检测 + realpath 校验）
- [x] SQL 标识符校验（safe_identifier）
- [x] SQLite 路径白名单（data/ 或 tmp/ 目录）
- [x] 密码脱敏（连接串 + 错误信息 + API Key）
- [x] 凭证加密存储（Fernet 对称加密）
- [x] 文件上传安全（扩展名白名单 + 魔数校验 + 50MB 限制 + 流式写入）
- [x] API Key 认证中间件（可选启用）
- [x] AI 速率限制（60 秒窗口 10 次）
- [x] AI 提示词注入防护（输入截断 + 模式过滤）
- [x] 文件锁（fcntl.flock 共享/排他锁）
- [x] Pipeline 执行超时（SIGALRM 300 秒）

#### UX 特性
- [x] CodeMirror 6 代码编辑器（SQL/Python/YAML 语法高亮）
- [x] 暗色模式全组件适配
- [x] 步骤类型选择风格统一
- [x] 脉冲引导动画（pulse-cta）
- [x] 打字机效果 + 庆祝彩带

### 2.2 API 端点清单（38 个）

| 模块 | 端点数 | 路径前缀 |
|------|--------|----------|
| AI | 6 | `/api/ai` |
| 向导 | 6 | `/api/wizard` |
| 配置管理 | 10 | `/api/configs` |
| 数据库连接 | 8 | `/api/connections` |
| 文件上传 | 1 | `/api/files` |
| 预览 | 2 | `/api/preview` |
| 执行历史 | 4 | `/api/executions` |
| 定时任务 | 5 | `/api/schedules` |
| 健康/静态 | 2 | `/` |

### 2.3 测试覆盖

| 层 | 测试数 | 框架 |
|----|--------|------|
| pipeforge 引擎测试 | 168 | pytest + pytest-mock |
| configforge API/服务测试 | 237 | pytest + pytest-mock |
| 前端单元测试 | 143 | Vitest + happy-dom + @vue/test-utils |
| E2E 测试 | 12 | Playwright |
| **合计** | **560** | |

### 2.4 技术栈

| 层 | 技术 |
|----|------|
| 运行时引擎 | Python 3.13, Pydantic v2, SQLite, openpyxl, Jinja2 |
| API 服务 | FastAPI, SQLAlchemy, OpenAI/Anthropic SDK, APScheduler |
| 前端 | Vue 3.5, TypeScript 5.5, Vite 6, Pinia, Naive UI, CodeMirror 6, Tailwind CSS 4 |

---

## 三、现存问题与技术债务

### 3.1 代码层面

| 优先级 | 问题 | 位置 | 影响 |
|--------|------|------|------|
| 高 | 根目录 package.json 与 configforge-web/package.json 版本冲突（pinia ^3.0.4 vs ^2.2.0、vue-router ^5.0.7 vs ^4.4.0、happy-dom ^20.9.0 vs ^14.0.0） | `/package.json` | 依赖解析混乱 |
| 高 | pyproject.toml 未声明 pymysql/psycopg2-binary（仅 requirements.txt 有） | `pyproject.toml` | `uv sync` 无法安装数据库驱动 |
| 中 | useWizardApi.ts 职责过重（3 个 composable 在一个文件） | `composables/useWizardApi.ts` | 可维护性差 |
| 中 | HTTP 请求逻辑重复（useApi 未被 useConfigApi/useWizardApi 复用） | `composables/` | 错误处理不一致风险 |
| 中 | wizard store 约 230 行未拆分 | `stores/wizard.ts` | 状态管理偏臃肿 |
| 中 | 前端约 58% 组件无单元测试（19/33） | `tests/` | 核心组件如 CodeEditor/ConfigVersionPanel 缺测试 |
| 中 | scheduler 测试覆盖不足 | `configforge/tests/` | 定时任务可靠性风险 |
| 低 | processor/processors 并存兼容逻辑 | `stores/wizard.ts` | 历史遗留 |
| 低 | full-wizard.script.ts 未纳入标准测试体系 | `e2e/` | 可能被忽略 |
| 低 | 速率限制器多 worker 下失效（内存存储，多 worker 乘以 worker 数） | `api/ai.py` | 已知限制，有注释 |

### 3.2 基础设施层面

| 项目 | 状态 | 影响 |
|------|------|------|
| Docker 化 | **完全缺失** | 无法容器化部署 |
| CI/CD | **完全缺失** | 无自动化测试/构建/发布 |
| .env.example | **完全缺失** | 环境变量配置无文档 |
| Makefile | **完全缺失** | 无统一构建脚本 |
| 数据存储 | JSON 文件 | 未迁移到数据库，并发性能有限 |
| API 版本化 | 无 `/api/v1/` 前缀 | 未来 breaking change 难以兼容 |
| 日志系统 | 部分模块用 `logging`，部分用 `print` | 无统一结构化日志 |

### 3.3 文档层面

| 问题 | 说明 |
|------|------|
| optimization-plan.md 状态过时 | 安全修复在 CHANGELOG 标记完成，但 optimization-plan 仍列为"待执行" |
| MEDIUM/LOW 项未完成 | optimization-plan 中 21 项 MEDIUM + 10 项 LOW 部分未处理 |

---

## 四、下一步工作计划

### Phase 3A：技术债务清理（v0.5.2）

> 目标：清理已知技术债务，为 v0.6 新功能开发扫清障碍  
> 注：Docker 和 CI/CD 可并行推进，不需要等待依赖修复完成

#### 4.1 依赖管理修复
- [ ] 删除根目录 package.json 或与 configforge-web/package.json 统一
- [ ] pyproject.toml 补充 pymysql/psycopg2-binary 依赖声明
- [ ] 统一 Python 版本要求（pyproject.toml vs README）

#### 4.2 基础设施搭建（可与 4.1 并行）
- [ ] 创建 Dockerfile（多阶段构建：前端 build + 后端 runtime）
- [ ] 创建 docker-compose.yml（含 volume 挂载 data/ 目录）
- [ ] 创建 .env.example（列出所有环境变量及默认值）
- [ ] 创建 Makefile（统一 dev/test/build/deploy 命令）
- [ ] 创建 .github/workflows/ci.yml（自动运行前后端测试）

#### 4.3 代码质量
- [ ] 拆分 useWizardApi.ts 为 useWizardApi.ts + useAiApi.ts + useConnectionApi.ts
- [ ] useConfigApi/useWizardApi 复用 useApi 的 request 封装
- [ ] 补充 CodeEditor/ConfigVersionPanel/AiTriggerButton 单元测试
- [ ] 补充 scheduler 单元测试（cron 校验、启停、执行回调边界场景）
- [ ] 清理 optimization-plan.md 状态（标记已完成项或归档）

#### 4.4 移动端响应式适配
- [ ] 向导布局移动端适配（步骤导航、编辑器、表格）
- [ ] 配置列表/执行历史/定时任务页面移动端适配
- [ ] 使用 useBreakpoint composable 实现响应式断点

### Phase 3B：推送分发（v0.6.0）

> 目标：从"手动取文件"到"数据自动推到面前"  
> 注：先做 Webhook（实现简单、价值高），再做邮件（SMTP 配置复杂、依赖多）

#### 4.5 Webhook 推送（P0，先做）
- [ ] 后端：`services/notifier/webhook.py`（HTTP POST 推送）
- [ ] 支持钉钉/企微/飞书机器人格式
- [ ] 前端：Webhook URL 配置 + 消息模板
- [ ] Pipeline 执行后自动触发推送（可配置）

#### 4.6 邮件推送（P0，后做）
- [ ] 后端：`services/notifier/email.py`（SMTP 发送，支持附件）
- [ ] 后端：`api/notifications.py`（推送配置 CRUD + 手动触发）
- [ ] 前端：Step 5 新增"推送设置"区域（收件人/主题/正文模板）
- [ ] 前端：推送历史查看

#### 4.7 推送模板
- [ ] Jinja2 模板引擎渲染推送内容
- [ ] 变量注入：执行结果摘要、输出文件链接、统计数据

### Phase 3C：AI 自愈（v0.6.1）

> 目标：从"AI 帮你建管道"到"AI 帮你维护管道"  
> 设计参考：[AI 顾问模式设计](superpowers/specs/2026-06-14-ai-consultant-mode-design.md)

#### 4.8 AI 错误诊断增强（P0）
- [ ] 执行失败时自动调用 `diagnose` category
- [ ] 前端：执行失败弹窗显示 AI 诊断结果（根因 + 修复建议）
- [ ] 前端：一键跳转到对应步骤修复

#### 4.9 AI 自动修复 — 简单场景（P1）
- [ ] 诊断后提供"AI 自动修复"按钮（仅简单场景）
- [ ] 适用场景：列名拼写错误、缺少引号、表名不匹配等
- [ ] AI 生成修复后的配置 diff
- [ ] 用户确认后应用修复

#### 4.10 AI 修复建议 — 复杂场景（P2）
- [ ] 复杂场景（如 SQL 逻辑错误）仅展示建议，不自动修复
- [ ] AI 解释问题原因 + 推荐修复方向
- [ ] 用户手动修改后可再次预检

#### 4.11 数据异常检测（P1）
- [ ] Pipeline 执行后 AI 分析输出数据
- [ ] 检测异常值、空值率突增、数据量异常
- [ ] 异常报告推送通知

### Phase 3D：数据源扩展（v0.6.2）

> 目标：连接更多数据源

#### 4.12 文件格式扩展（P1）
- [ ] JSON 文件输入
- [ ] XML 文件输入
- [ ] Parquet 文件输入（大数据场景）

#### 4.13 REST API 输入（P1）
- [ ] 后端：`plugins/input/api.py`（HTTP GET 拉取数据）
- [ ] 前端：API 输入配置（URL/Method/Headers/Pagination）

#### 4.14 云服务集成（P2）
- [ ] Google Sheets 输入
- [ ] 邮件附件输入
- [ ] FTP/SFTP 输入

### Phase 3E：配置市场（v0.7.0）

> 目标：从"工具"到"平台"

#### 4.15 模板系统
- [ ] 后端：`api/templates.py`（模板 CRUD + 分类 + 搜索）
- [ ] 后端：`templates/` 目录（内置模板库）
- [ ] 前端：模板市场页面（分类浏览 + 搜索 + 预览）
- [ ] 前端：一键从模板创建配置

#### 4.16 适配检测
- [ ] 模板适配检测（检查当前环境是否满足模板要求）
- [ ] 缺失依赖提示（如未配置数据库连接）

### Phase 3F：企业级就绪（v1.0.0）

> 目标：生产可信

#### 4.17 数据存储迁移
- [ ] JSON 文件 → SQLite（默认） / PostgreSQL（生产）
- [ ] 数据迁移脚本
- [ ] SQLAlchemy ORM 模型

#### 4.18 认证与权限
- [ ] SSO 集成（OAuth2 / SAML / LDAP）
- [ ] 用户角色（Admin / Editor / Viewer）
- [ ] 配置权限控制

#### 4.19 可观测性
- [ ] 结构化日志（structlog / loguru）
- [ ] 审计日志（谁在什么时候做了什么操作）
- [ ] 数据血缘（列级追溯）
- [ ] 执行可视化 DAG

#### 4.20 部署
- [ ] Docker 镜像发布到 GHCR
- [ ] Kubernetes Helm Chart
- [ ] API 版本化（`/api/v1/`）

---

## 五、优先级矩阵

| 优先级 | 任务 | 版本 | 价值 | 工作量 |
|--------|------|------|------|--------|
| P0 | 技术债务清理 + 基础设施 | v0.5.2 | 高 | 中 |
| P0 | Webhook 推送（先做） | v0.6.0 | 高 | 低 |
| P0 | 邮件推送（后做） | v0.6.0 | 高 | 中 |
| P0 | AI 错误诊断增强 | v0.6.1 | 高 | 低 |
| P1 | AI 自动修复（简单场景） | v0.6.1 | 中 | 中 |
| P1 | JSON/XML/REST API 输入 | v0.6.2 | 中 | 中 |
| P1 | 配置模板系统 | v0.7.0 | 高 | 高 |
| P2 | AI 修复建议（复杂场景） | v0.6.1 | 中 | 中 |
| P2 | 数据异常检测 | v0.6.1 | 中 | 中 |
| P2 | 云服务集成 | v0.6.2 | 低 | 高 |
| P2 | 数据血缘 + 审计日志 | v0.7.x | 中 | 高 |
| P3 | 数据存储迁移 | v1.0.0 | 高 | 高 |
| P3 | SSO + 权限 | v1.0.0 | 中 | 高 |
| P3 | Docker + K8s | v1.0.0 | 高 | 中 |

---

## 六、成功指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 数据源类型 | 3 | 8+ |
| 输出/推送方式 | 3 | 10+ |
| AI 能力 | 8 | 13+ |
| 测试数量 | 560 | 800+ |
| 部署方式 | 源码 | Docker + K8s |
| CI/CD | 无 | GitHub Actions |

---

## 七、建议的近期执行顺序

1. **v0.5.2**：技术债务清理 + Docker + CI/CD + .env.example + 移动端适配
2. **v0.6.0**：Webhook 推送 + 邮件推送 + 推送模板
3. **v0.6.1**：AI 错误诊断增强 + AI 自动修复（简单场景）+ 数据异常检测
4. **v0.6.2**：JSON/XML 输入 + REST API 输入
5. **v0.7.0**：配置模板系统 + 适配检测

> 核心原则：每一步都要让用户感受到"ConfigForge 变得更聪明了"，而不是"变得更复杂了"
