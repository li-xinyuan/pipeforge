# Changelog

All notable changes to ConfigForge / PipeForge will be documented in this file.

## [v0.7.0] - 2026-06-19

### Phase 3E：配置市场

- **模板市场页面**：分类浏览（销售/财务/人力/运维/通用）、搜索、预览弹窗
- **4 个内置模板**：月度销售报表、财务汇总报表、库存跟踪管理、用户数据清洗（中文）
- **使用模板**：一键加载模板配置到向导，从步骤 1 开始逐步检查
- **保存为模板**：向导 Step 5 新增"保存为模板"按钮，将当前配置保存为可复用模板
- **兼容性检查**：模板详情中检查数据库连接、AI 配置等环境依赖
- **模板 API**：7 个端点（CRUD + 实例化 + 兼容性检查）
- **导航集成**：首页"浏览模板市场"按钮、导航栏"模板市场"入口

### Phase 3D：数据源扩展

- **JSON 输入**：支持 .json 文件，自动展平嵌套字段，可配置展平分隔符
- **XML 输入**：支持 .xml 文件，自动检测行元素，可手动指定 XPath 路径
- **Parquet 输入**：支持 .parquet 大数据文件，自动推断 schema
- **REST API 输入**：从 HTTP 接口拉取数据，支持 GET/POST、自定义请求头和参数、数据路径、三种分页模式
- **文件上传白名单扩展**：支持 .json / .xml / .parquet 格式
- **API 推断端点**：新增 `/api/wizard/infer-api-input/{input_name}` 专门处理 REST API 输入
- **Preview 端点扩展**：文件预览和 SQL 预览支持新文件类型

### Phase 3C：AI 自愈

- **自动诊断**：Pipeline 执行失败时自动调用 AI 诊断，返回错误原因和修复建议
- **一键修复**：诊断结果可直接应用到配置（SQL 修正、参数调整等）
- **诊断趋势**：执行历史页面新增诊断趋势标签页，含 AnomalyChart 异常图表
- **DiagnosisPanel 组件**：展示错误分析、影响评估、修复建议、AI 对话
- **LRU 缓存**：诊断结果缓存（100 条，1 小时 TTL），避免重复调用 AI

### Phase 3B：推送分发

- **通知推送系统**：邮件（SMTP）和 Webhook 两种通知渠道
- **通知配置管理**：创建/编辑/删除/测试通知规则
- **Pipeline 执行通知**：执行成功/失败后自动推送通知
- **SMTP 设置**：独立的 SMTP 服务器配置和测试
- **通知历史**：查看已发送的通知记录
- **NotificationSettings 组件**：向导 Step 5 集成通知设置

### Phase 3A：技术债务清理

- **删除根目录 package.json**：消除版本冲突
- **pyproject.toml 补充依赖**：pymysql、psycopg2-binary 声明
- **Dockerfile / docker-compose.yml / .env.example / Makefile**：生产部署基础设施
- **CI/CD**：GitHub Actions（后端 pytest + 前端 vitest + vue-tsc）
- **前端 API 拆分**：useConfigApi / useConnectionApi / useAiApi / useNotificationApi / useTemplateApi
- **前端测试扩展**：24 个测试文件，201 个测试用例
- **移动端适配**：@media 响应式布局

### Bug 修复

- 修复 XML 文件上传返回 "Unsupported format" 错误
- 修复 `sample_values` 按列取值错误（所有列返回相同值）
- 修复模板实例化后数据被 `onMounted` 的 `resetAll()` 清空
- 修复分类筛选值不匹配（前端中文 vs 后端英文）
- 修复 API 推断端点 URL 错误

## [v0.5.0] - 2026-06-14

### Security (BLOCKER)

- **B-1** SQL 注入防护：`_is_read_only_sql()` 白名单检查，仅允许 SELECT 语句执行
- **B-1b** 数据库输出 `source_table` 注入防护：`safe_identifier()` 校验 SQL 标识符
- **B-2/B-3/B-4** 路径遍历防护：`validate_id()` 校验 connections/executions/schedules 的 ID 参数
- **B-6** 密码脱敏：`sanitize_connection_string()` 隐藏 API 返回中的数据库密码
- **B-7** DDL/DML 正则扩展：拦截 ATTACH/DETACH/PRAGMA/VACUUM/REINDEX 等操作
- **B-8** 文件上传流式写入：大文件分块写入，避免 OOM

### Stability (HIGH)

- **H-1** 文件操作竞态条件：`read_json_locked()`/`write_json_locked()` 统一文件锁（fcntl.flock）
- **H-2** SQL 预览样本提示：前端显示"预览基于样本数据"提示文案
- **H-3** 废弃 Step 视图清理：移除未使用的旧组件
- **H-4** MySQL 兼容性：反引号引用 + ON DUPLICATE KEY UPDATE 语法
- **H-5** replace 模式事务一致性：使用 `engine.begin()` 确保事务
- **H-6** DataPreviewTable 集成到 Step 5
- **H-7** Pipeline 执行超时：`PipelineTimeoutError` + signal.alarm 保护
- **H-8** API Key 认证中间件：`AuthMiddleware`（可选，默认关闭）

### Features (MEDIUM)

- **M-1~M-21** 21 项中等优先级优化：类型系统改进、死代码清理、测试修复、错误消息完善等
- 数据库输出（MySQL/PostgreSQL/SQLite）：支持 append/replace/upsert 模式
- 配置版本管理：自动保存历史版本，可查看和回滚
- 执行历史：查看每次执行的状态、时间、日志
- 定时任务：APScheduler Cron 调度，支持启用/禁用
- Pipeline `infer_output()` 基于输入源推断输出列

### UI/UX

- **CodeMirror 6 编辑器**：替换 SQL/Python/YAML 的 textarea 为语法高亮编辑器
  - SQL：蓝色关键字、绿色字符串、橙色数字、粉红运算符
  - Python：紫色关键字、蓝色函数名、橙色装饰器
  - YAML：紫色键名、绿色字符串、蓝色关键字
  - 亮色/暗色双主题，自动跟随系统切换
  - 行号、自动补全、括号匹配、代码折叠
  - happy-dom 测试环境自动降级为 textarea
- **暗色模式全组件适配**：17+ 个 Vue 组件添加 `dark:` Tailwind 变体
- **步骤类型选择风格统一**：Step 2/3/4 类型选择卡片统一为实线边框+背景色+描述文字
- **主题持久化修复**：`AppNavBar` 改用 `useTheme()` 共享状态，localStorage 正确保存
- **按钮大小统一**："上一步"/"下一步"/导出操作按钮统一为默认大小
- **GuideView 文档补充**：数据库输入/输出、多步骤处理、版本管理、执行历史等

### Quality (LOW)

- **L-1~L-10** 10 项低优先级改进：无障碍性、响应式、测试覆盖等
- 后端 `_periodic_cleanup()` 定时清理临时文件/日志
- Playwright E2E 测试框架搭建（home + wizard 测试用例）
- 前端测试从 113 增至 143 个

## [v0.4.0] - 2026-05-xx

- Python 处理器（exec + 超时 + ctx API）
- SQL+Python 混合 DAG
- 文件名标签
- 步骤 3 操作统一

## [v0.3.1] - 2026-05-xx

- AI 编排步骤链（自然语言 → 多步 SQL）
- Typewriter 效果
- Confetti 庆祝动画

## [v0.3.0] - 2026-04-xx

- 多步 SQL Pipeline + DAG 拓扑排序
- 处理步骤卡片列表
- 错误中文提示

## [v0.2.1] - 2026-04-xx

- 数据库输入源（SQLite/MySQL/PG）
- 安全加固（31 项缺陷修复）

## [v0.2.0] - 2026-03-xx

- 前端重设计（单页滚动向导）
- AI SQL 生成
- 暗色模式
- 配置管理
- CSV 支持
