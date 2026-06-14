# Changelog

All notable changes to ConfigForge / PipeForge will be documented in this file.

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
