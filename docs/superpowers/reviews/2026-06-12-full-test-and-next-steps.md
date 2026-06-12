# ConfigForge 全面测试报告与下一步工作建议

> 日期：2026-06-12
> 版本：v0.4+（P0-P1 全部完成，P2-P4 部分完成）

---

## 一、自动化测试结果

### 1.1 后端测试

| 测试套件 | 结果 | 说明 |
|----------|------|------|
| pipeforge 核心测试 | **168 passed / 0 failed** | 全部通过 |
| configforge API 测试 | **196 passed / 3 failed** | 3 个失败均为 API 响应格式变更（`list` → `{items, page, total}` 分页格式） |

**失败测试详情：**
- `test_config_versions.py::test_first_save_has_current_version_1` — API 返回分页格式，测试期望纯列表
- `test_config_versions.py::test_second_save_creates_version_history` — 同上
- `test_api_configs.py::test_list_configs_empty` — `assert isinstance(resp.json(), list)` 应改为 `assert "items" in resp.json()`

### 1.2 前端测试

| 测试套件 | 结果 | 说明 |
|----------|------|------|
| vue-tsc 类型检查 | **0 errors** | 全部通过 |
| vitest 单元测试 | **151 passed / 11 failed** | 4 个测试文件失败，均为 happy-dom 网络请求问题（`fetch /api/ai/settings` 超时） |

### 1.3 E2E 功能测试（Playwright）

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 首页"开始新配置"按钮 | ✅ 通过 | 按钮可见且可点击 |
| GuidePanel 步骤标签 | ✅ 通过 | "步骤 1 · 场景信息" 正确显示 |
| GuidePanel 提示文本 | ✅ 通过 | "请填写场景名称..." 正确显示 |
| AI 组件已移除 | ✅ 通过 | AiChatPanel / AiInlineTip / AI FAB 均不存在 |
| 步骤切换（1→2） | ✅ 通过 | GuidePanel 自动更新为"步骤 2 · 输入源" |
| 返回上一步 | ✅ 通过 | 步骤2→步骤1 正常回退，步骤2数据被清空 |
| 暗色模式 | ✅ 通过 | `data-theme="dark"` 切换后背景色变化 |
| 后端 API 健康 | ✅ 通过 | /api/configs(200), /api/schedules(200), /api/connections(200) |
| 步骤卡片状态 | ✅ 通过 | Step1=active, Step2-5=locked |
| 进度条 | ✅ 通过 | 可见且正确 |
| 设置页 | ✅ 通过 | 正常加载 |
| 定时任务页 | ✅ 通过 | 正常加载 |
| 执行历史页 | ✅ 通过 | 正常加载 |

---

## 二、代码扫描发现的问题

### 2.1 严重问题（P0 — 影响核心功能）

| # | 问题 | 文件 | 影响 |
|---|------|------|------|
| **S-1** | **插件注册不完整** | `src/pipeforge/__init__.py` | 只导入了 3/7 个插件。通过 configforge Web API 执行 pipeline 时，csv 输入、database 输入、python 处理器、csv 输出、database 输出将抛出 `PluginNotFoundError` |
| **S-2** | **requirements.txt 缺少 3 个运行时依赖** | `configforge/requirements.txt` | 缺少 `apscheduler`、`sqlalchemy`、`deepdiff`，按此文件安装后调度器、数据库连接、版本对比功能将失败 |

### 2.2 高优先级问题（P1 — 影响重要功能）

| # | 问题 | 文件 | 影响 |
|---|------|------|------|
| **H-1** | **Database 输出前端未启用** | `OutputConfigTab.vue:24-28` | 后端 database.py 已完整实现，前端类型定义已就绪，但 UI 中 Database 选项被禁用 |
| **H-2** | **数据库驱动未声明** | `pyproject.toml` / `requirements.txt` | `pymysql`、`psycopg2` 在代码中被引用但未声明依赖 |
| **H-3** | **调度器完全缺乏测试** | `configforge/tests/` | scheduler.py 和 api/schedules.py 无任何测试覆盖 |
| **H-4** | **DataPreviewTable 在活跃代码中未使用** | `DataPreviewTable.vue` | 仅被孤立的 Step5ExportView 引用，ConfigWizardView 中 Step5 未集成数据预览 |

### 2.3 中优先级问题（P2 — 影响代码质量/稳定性）

| # | 问题 | 文件 | 影响 |
|---|------|------|------|
| **M-1** | **5 个旧版 View 文件完全孤立** | `Step1SceneView.vue` ~ `Step5ExportView.vue` | 未在路由中注册，属于死代码 |
| **M-2** | **5 个 Composable 文件完全未使用** | `useColumnDiff.ts` 等 | 孤立代码 |
| **M-3** | **AiChatPanel/AiInlineTip/OrchestrationResult 在主应用中未使用** | `components/wizard/` | AI 重构后遗留组件 |
| **M-4** | **调度器 JSON 文件无文件锁** | `scheduler.py` | 并发调度操作可能导致数据损坏 |
| **M-5** | **数据库输出插件 SQL 注入风险** | `database.py:110-115` | `source_table` 直接拼入 SQL |
| **M-6** | **MySQL 标识符引用方式不兼容** | `database.py:30-33` | `_quote()` 使用双引号，MySQL 默认需要反引号 |
| **M-7** | **MySQL `VALUES()` 函数已弃用** | `database.py:73` | MySQL 8.0.20+ 中 `ON DUPLICATE KEY UPDATE ... VALUES(col)` 已弃用 |
| **M-8** | **replace 模式事务一致性** | `database.py:131-136` | DROP TABLE 和数据插入不在同一事务中 |
| **M-9** | **3 个后端测试失败** | `test_config_versions.py`, `test_api_configs.py` | API 响应格式变更后测试未更新 |
| **M-10** | **11 个前端测试失败** | vitest | happy-dom 网络请求超时 |

### 2.4 低优先级问题（P3 — 改进建议）

| # | 问题 | 文件 | 影响 |
|---|------|------|------|
| **L-1** | 大量 `as any` 类型断言 | `Step5ExportView.vue` 等 | 削弱 TypeScript 类型安全 |
| **L-2** | 插件发现机制缺失 | `pipeforge/__init__.py` | 无自动发现，依赖手动导入 |
| **L-3** | 数据库输出插件缺少连接重试 | `database.py` | 远程数据库网络抖动可能一次性失败 |
| **L-4** | `CheckRule` 前向引用 | `config/models.py` | 可读性差 |
| **L-5** | AiStatusBanner 重复实现 useAiStatus 逻辑 | `AiStatusBanner.vue` | 代码重复 |

---

## 三、项目目标实现情况

### 3.1 路线图完成度

| 优先级 | 已完成 | 总计 | 完成率 |
|--------|--------|------|--------|
| P0 硬阻塞修复 | 5 | 5 | **100%** |
| P1 核心体验优化 | 7 | 7 | **100%** |
| P2 平台化 | 1 | 4 | **25%** |
| P3 数据能力扩展 | 2 | 4 | **50%** |
| P4 降低门槛 | 1 | 4 | **25%** |
| TD 技术债务 | 3 | 8 | **38%** |

### 3.2 已完成功能清单

- ✅ P0-1: 中文列名支持（`safe_identifier` + `re.UNICODE`）
- ✅ P0-2: 序列化 bug 修复（`stateToSnakeCase` + DatabaseOutputConfig）
- ✅ P0-3: Python exec 三层沙箱（AST + builtins + signal.alarm）
- ✅ P0-4: 临时文件泄漏修复（输出持久化 + atexit 清理）
- ✅ P0-5: deepdiff 依赖声明
- ✅ P1-3: GuidePanel 固定提示面板（替代 AI 聊天）
- ✅ P1-4: Database 输入自动列表/列
- ✅ P1-5: 列映射全部映射 + 智能匹配
- ✅ P1-6: YAML 可编辑模式 + js-yaml
- ✅ P1-7: 暗色模式（Tailwind CSS v4 @custom-variant）
- ✅ P2-1: 定时调度（APScheduler + CronTrigger + REST API）
- ✅ P3-1: Database 输出（SQLAlchemy + MySQL/PostgreSQL/SQLite）
- ✅ P3-4: 数据预览组件（DataPreviewTable）
- ✅ P4-2: SQL 模板库（6 类 9 个模板）

### 3.3 未完成功能清单

- ❌ P2-2: 执行监控（WebSocket + 日志流）
- ❌ P2-3: 执行告警（邮件/Webhook）
- ❌ P2-4: 管道依赖（DAG 编排）
- ❌ P3-2: API 输入/输出插件
- ❌ P3-3: JSON/XML 输入插件
- ❌ P4-1: 模板市场
- ❌ P4-3: AI 引导配置（增强版）
- ❌ P4-4: 新用户 Onboarding

---

## 四、下一步工作建议

### 阶段一：修复阻塞性问题（预计 1-2 天）

| 序号 | 任务 | 优先级 | 说明 |
|------|------|--------|------|
| 1 | **修复插件注册** | P0 | 在 `pipeforge/__init__.py` 中导入所有 7 个插件，或实现自动发现机制 |
| 2 | **更新 requirements.txt** | P0 | 添加 `apscheduler`、`sqlalchemy`、`deepdiff`、`pymysql`、`psycopg2-binary` |
| 3 | **修复 3 个后端测试** | P1 | 更新测试以匹配分页 API 响应格式 |
| 4 | **修复前端测试** | P1 | 为 happy-dom 环境添加 API mock |

### 阶段二：启用 Database 输出 + 数据预览集成（预计 2-3 天）

| 序号 | 任务 | 优先级 | 说明 |
|------|------|--------|------|
| 5 | **启用 Database 输出前端** | P1 | 在 OutputConfigTab.vue 中启用 Database 选项，添加连接选择、目标表名、写入模式等配置表单 |
| 6 | **修复 Database 输出插件** | P1 | MySQL 引号改为反引号、VALUES() 改为别名引用、replace 模式事务一致性、source_table 使用 safe_identifier |
| 7 | **集成 DataPreviewTable 到 ConfigWizardView** | P1 | 在 Step 5 添加"数据预览"区域，调用 dry-run API 展示结果 |
| 8 | **添加调度器测试** | P2 | scheduler.py 和 api/schedules.py 的单元测试 |

### 阶段三：清理死代码 + 技术债务（预计 1-2 天）

| 序号 | 任务 | 优先级 | 说明 |
|------|------|--------|------|
| 9 | **删除旧版 View 文件** | P2 | 删除 Step1SceneView ~ Step5ExportView（5 个文件） |
| 10 | **删除未使用的 Composable** | P2 | 删除 useColumnDiff、useAiStatus、useTypewriter、useConversationHistory、useErrorHandler |
| 11 | **处理 AI 遗留组件** | P2 | 评估 AiChatPanel/AiInlineTip/OrchestrationResult 是否保留（可能后续 P4-3 需要），如不保留则删除 |
| 12 | **调度器文件锁** | P2 | 为 _load_schedules/_save_schedules 添加 fcntl 文件锁 |

### 阶段四：功能扩展（按业务需求排优先级）

| 序号 | 任务 | 优先级 | 说明 |
|------|------|--------|------|
| 13 | **执行监控** | P2 | WebSocket + 日志流，实时查看 pipeline 执行进度 |
| 14 | **执行告警** | P2 | 邮件/Webhook 通知执行结果 |
| 15 | **新用户 Onboarding** | P3 | 首次使用引导，帮助新用户快速上手 |
| 16 | **JSON/XML 输入插件** | P3 | 扩展数据源支持 |
| 17 | **API 输入/输出插件** | P3 | 支持 REST API 作为数据源和输出目标 |
| 18 | **管道依赖** | P3 | DAG 编排多管道依赖关系 |
| 19 | **模板市场** | P4 | 预置常用配置模板 |
| 20 | **AI 引导配置（增强版）** | P4 | 基于固定提示的经验，重新设计 AI 辅助方案 |

---

## 五、关键风险提示

1. **插件注册问题（S-1）是当前最大的运行时风险**：如果用户选择 CSV 输入、Database 输入、Python 处理器、CSV 输出或 Database 输出，pipeline 执行将直接报错。建议立即修复。
2. **Database 输出前端未启用**：后端已完整实现但前端禁用，用户无法使用此功能。建议阶段二优先处理。
3. **DataPreviewTable 未集成**：组件已开发但未接入 ConfigWizardView，用户在 Step 5 无法预览数据。
4. **MySQL 兼容性问题**：当前 `_quote()` 使用双引号在默认 MySQL 配置下会报错，`VALUES()` 函数在 MySQL 8.0.20+ 已弃用。

---

## 六、测试环境信息

- 后端：Python 3.13 + FastAPI + Uvicorn（端口 8000）
- 前端：Vite 6.4.2 + Vue 3 + Naive UI（端口 5173）
- 浏览器测试：Playwright Chromium headless（1440x900）
- 后端测试：pytest（168 + 196 = 364 用例，3 failed）
- 前端测试：vitest（162 用例，11 failed）+ vue-tsc（0 errors）
