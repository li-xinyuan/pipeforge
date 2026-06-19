# ConfigForge 详细实施方案

> 基于：[PROJECT_STATUS_AND_ROADMAP.md](PROJECT_STATUS_AND_ROADMAP.md)  
> 编制日期：2026-06-18  
> 版本范围：v0.5.2 → v0.7.0

---

## 总览

| Phase | 版本 | 核心目标 | 子任务数 |
|-------|------|----------|----------|
| 3A | v0.5.2 | 技术债务清理 + 基础设施 | 17 |
| 3B | v0.6.0 | 推送分发 | 12 |
| 3C | v0.6.1 | AI 自愈 | 10 |
| 3D | v0.6.2 | 数据源扩展 | 9 |
| 3E | v0.7.0 | 配置市场 | 7 |
| **合计** | | | **55** |

---

## Phase 3A：技术债务清理（v0.5.2）

### T-3A-01 删除根目录 package.json

**问题**：根目录 `/package.json` 与 `configforge-web/package.json` 存在版本冲突（pinia ^3.0.4 vs ^2.2.0、vue-router ^5.0.7 vs ^4.4.0、happy-dom ^20.9.0 vs ^14.0.0），可能导致依赖解析混乱。

**方案**：
1. 确认根目录 package.json 无独立用途（无根目录 npm 脚本、无 monorepo 配置）
2. 删除根目录 `/package.json` 和 `/node_modules/`（如存在）
3. 确认 `configforge-web/package.json` 是唯一前端依赖声明
4. 运行 `cd configforge-web && npm install && npx vitest run` 验证

**涉及文件**：
- 删除：`/package.json`
- 可能删除：`/node_modules/`、`/package-lock.json`

**验证标准**：
- [ ] `npm install` 无版本冲突警告
- [ ] 前端 143 个测试全部通过
- [ ] `npm run dev` 正常启动

---

### T-3A-02 pyproject.toml 补充数据库驱动依赖

**问题**：`pyproject.toml` 的 `dependencies` 未声明 `pymysql` 和 `psycopg2-binary`，仅 `requirements.txt` 有声明，`uv sync` 无法安装数据库驱动。

**方案**：
1. 在 `pyproject.toml` 的 `[project.dependencies]` 中添加：
   ```
   pymysql>=1.1.0
   psycopg2-binary>=2.9.0
   ```
2. 验证 `requirements.txt` 与 `pyproject.toml` 依赖一致
3. 运行 `uv sync` 验证安装成功

**涉及文件**：
- 修改：`/pyproject.toml`

**验证标准**：
- [ ] `uv sync` 成功安装 pymysql 和 psycopg2-binary
- [ ] 后端 237 个测试全部通过
- [ ] 数据库连接功能正常（MySQL/PG）

---

### T-3A-03 统一 Python 版本要求

**问题**：`pyproject.toml` 要求 `python>=3.10`，README 标注 `3.13`。

**方案**：
1. 确认项目实际最低兼容 Python 版本（检查是否使用了 3.10+ 特性如 match/case、TypeAlias 等）
2. 将 `pyproject.toml` 的 `requires-python` 设为实际最低版本
3. 更新 README 中的 Python 版本说明为"Python >= 3.10（推荐 3.13）"

**涉及文件**：
- 修改：`/pyproject.toml`（`requires-python`）
- 修改：`/README.md`（Python 版本说明）

**验证标准**：
- [ ] pyproject.toml 与 README 版本说明一致
- [ ] Python 3.10 环境下 `uv run pytest` 通过

---

### T-3A-04 创建 Dockerfile

**问题**：无 Docker 支持，无法容器化部署。

**方案**：
1. 创建多阶段构建 Dockerfile：
   ```
   Stage 1 (build-frontend): node:20-alpine
     - COPY configforge-web/ → npm ci → npm run build
   
   Stage 2 (runtime): python:3.13-slim
     - COPY pyproject.toml → uv sync --no-dev
     - COPY configforge/ → 后端代码
     - COPY --from=build-frontend → 静态资源
     - EXPOSE 8000
     - CMD ["uvicorn", "configforge.server:app", "--host", "0.0.0.0", "--port", "8000"]
   ```
2. 创建 `.dockerignore`（排除 node_modules、.git、data/、tmp/、__pycache__）
3. 本地构建验证：`docker build -t configforge .`
4. 本地运行验证：`docker run -p 8000:8000 -v ./data:/app/data configforge`

**涉及文件**：
- 新建：`/Dockerfile`
- 新建：`/.dockerignore`

**验证标准**：
- [ ] `docker build` 成功
- [ ] `docker run` 后访问 `http://localhost:8000` 可正常使用
- [ ] 前端静态资源正确提供
- [ ] 数据持久化（volume 挂载 data/ 目录）

---

### T-3A-05 创建 docker-compose.yml

**问题**：无编排配置，无法一键启动完整环境。

**方案**：
1. 创建 `docker-compose.yml`：
   ```yaml
   services:
     configforge:
       build: .
       ports: ["8000:8000"]
       volumes: ["./data:/app/data", "./tmp:/app/tmp"]
       environment:
         - CONFIGFORGE_API_KEY=${API_KEY:-}
         - CORS_ORIGINS=http://localhost:8000
       env_file: .env
       restart: unless-stopped
   ```
2. 验证 `docker compose up` 一键启动

**涉及文件**：
- 新建：`/docker-compose.yml`

**验证标准**：
- [ ] `docker compose up` 成功启动
- [ ] 访问 `http://localhost:8000` 正常
- [ ] 数据持久化（重启后配置不丢失）

---

### T-3A-06 创建 .env.example

**问题**：环境变量散落在代码中，无配置模板。

**方案**：
1. 扫描代码中所有环境变量引用：
   - `CONFIGFORGE_API_KEY` — API Key 认证（空=开发模式）
   - `CONFIGFORGE_UPLOAD_DIR` — 上传目录（默认 tmp/uploads）
   - `CONFIGFORGE_ENCRYPTION_KEY` — Fernet 加密密钥（空=自动生成）
   - `CORS_ORIGINS` — CORS 允许源（默认 localhost:5173,5174）
2. 创建 `.env.example`，每个变量附带注释说明和默认值
3. 确认 `.gitignore` 包含 `.env`

**涉及文件**：
- 新建：`/.env.example`
- 修改：`/.gitignore`（确保 `.env` 被忽略）

**验证标准**：
- [ ] `.env.example` 包含所有环境变量及注释
- [ ] `cp .env.example .env && docker compose up` 正常启动
- [ ] `.env` 不被 git 跟踪

---

### T-3A-07 创建 Makefile

**问题**：无统一构建脚本，开发/测试/部署命令分散。

**方案**：
1. 创建 Makefile，包含以下目标：
   ```makefile
   .PHONY: dev dev-be dev-fe test test-be test-fe test-e2e build clean
   
   dev:          # 同时启动前后端
   dev-be:       # uv run uvicorn configforge.server:app --reload
   dev-fe:       # cd configforge-web && npm run dev
   test:         # 运行所有测试
   test-be:      # uv run pytest configforge/tests/ -x -q
   test-fe:      # cd configforge-web && npx vitest run
   test-e2e:     # cd configforge-web && npx playwright test
   build:        # docker build
   clean:        # 清理临时文件、缓存
   install:      # uv sync + npm install
   lint:         # 前端类型检查 + 后端 ruff
   ```
2. 验证所有目标可正常执行

**涉及文件**：
- 新建：`/Makefile`

**验证标准**：
- [ ] `make install` 成功安装所有依赖
- [ ] `make test` 通过所有测试
- [ ] `make dev` 成功启动前后端

---

### T-3A-08 创建 GitHub Actions CI

**问题**：无 CI/CD，代码质量无自动化保障。

**方案**：
1. 创建 `.github/workflows/ci.yml`：
   ```yaml
   name: CI
   on: [push, pull_request]
   jobs:
     backend:
       runs-on: ubuntu-latest
       steps: [checkout, setup-python, uv sync, pytest]
     frontend:
       runs-on: ubuntu-latest
       steps: [checkout, setup-node, npm ci, vitest, vue-tsc]
   ```
2. 触发条件：push to master / pull_request
3. 后端：Python 3.13 + uv + pytest
4. 前端：Node 20 + npm ci + vitest + vue-tsc --noEmit

**涉及文件**：
- 新建：`/.github/workflows/ci.yml`

**验证标准**：
- [ ] push 后 GitHub Actions 自动触发
- [ ] 后端测试 job 通过
- [ ] 前端测试 + 类型检查 job 通过

---

### T-3A-09 拆分 useWizardApi.ts

**问题**：`useWizardApi.ts` 包含 3 个 composable（useWizardApi / useAiApi / useConnectionApi），职责过重。

**方案**：
1. 将 `useAiApi` 提取到 `composables/useAiApi.ts`
2. 将 `useConnectionApi` 提取到 `composables/useConnectionApi.ts`
3. `useWizardApi.ts` 仅保留向导相关 API（initScene / fetchPreview / generateYaml / executeSql / dryRun / executePipeline）
4. 更新所有 import 引用（ConfigWizardView.vue、InputSourceCard.vue、OutputConfigTab.vue、SqlProcessorContent.vue 等）
5. 运行前端测试验证无回归

**涉及文件**：
- 新建：`configforge-web/src/composables/useAiApi.ts`
- 新建：`configforge-web/src/composables/useConnectionApi.ts`
- 修改：`configforge-web/src/composables/useWizardApi.ts`（移除两个 composable）
- 修改：所有 import 引用

**验证标准**：
- [ ] 3 个 composable 独立文件，职责清晰
- [ ] 前端 143 个测试全部通过
- [ ] 无 import 错误

---

### T-3A-10 统一 HTTP 请求封装

**问题**：`useApi.ts` 提供了通用 `request` 封装，但 `useConfigApi.ts` 和 `useWizardApi.ts` 各自重复实现了 fetch + 错误处理。

**方案**：
1. 审查 `useApi.ts` 的 `request()` 方法签名和错误处理逻辑
2. 将 `useConfigApi.ts` 中的 fetch 调用替换为 `useApi().request()`
3. 将 `useWizardApi.ts` 中的 fetch 调用替换为 `useApi().request()`
4. 统一错误处理：HTTP 错误、网络错误、JSON 解析错误
5. 保持现有 API 方法签名不变（仅改内部实现）

**涉及文件**：
- 修改：`configforge-web/src/composables/useConfigApi.ts`
- 修改：`configforge-web/src/composables/useWizardApi.ts`
- 可能修改：`configforge-web/src/composables/useApi.ts`（补充缺失功能）

**验证标准**：
- [ ] 所有 API 调用通过 `useApi().request()` 发出
- [ ] 前端 143 个测试全部通过
- [ ] 手动测试：配置保存、AI 建议、文件上传功能正常

---

### T-3A-11 补充前端单元测试

**问题**：前端约 58% 组件无单元测试（19/33），核心组件如 CodeEditor、ConfigVersionPanel、AiTriggerButton 缺测试。

**方案**：
1. 优先补充核心组件测试：
   - `CodeEditor.vue`：测试 modelValue 双向绑定、language 切换、fallback 模式
   - `ConfigVersionPanel.vue`：测试版本列表加载、对比、回滚
   - `AiTriggerButton.vue`：测试 label/loading/disabled 状态、click 事件
2. 次要组件测试：
   - `AppNavBar.vue`：测试导航链接、主题切换
   - `AiSuggestPanel.vue`：测试 visible/content/accept/regenerate
3. 目标：组件测试覆盖率从 42% 提升到 70%+

**涉及文件**：
- 新建：`configforge-web/tests/components/CodeEditor.test.ts`
- 新建：`configforge-web/tests/components/ConfigVersionPanel.test.ts`
- 新建：`configforge-web/tests/components/AiTriggerButton.test.ts`
- 新建：`configforge-web/tests/components/AppNavBar.test.ts`
- 新建：`configforge-web/tests/components/AiSuggestPanel.test.ts`

**验证标准**：
- [ ] 新增测试全部通过
- [ ] 组件测试覆盖率 ≥ 70%
- [ ] 前端测试总数 ≥ 170

---

### T-3A-12 补充 scheduler 单元测试

**问题**：scheduler 测试覆盖不足，定时任务可靠性风险。

**方案**：
1. 补充边界场景测试：
   - 无效 cron 表达式（6 段、空值、非法字符）
   - 执行回调异常（配置不存在、Pipeline 执行失败）
   - 并发启停（快速 toggle）
   - 时区处理
2. 目标：scheduler 测试从 8 个提升到 15+

**涉及文件**：
- 修改：`configforge/tests/test_scheduler.py`

**验证标准**：
- [ ] scheduler 测试 ≥ 15 个
- [ ] 覆盖 cron 校验、启停、执行回调、异常处理
- [ ] 后端测试全部通过

---

### T-3A-13 清理 optimization-plan.md

**问题**：optimization-plan.md 状态与 CHANGELOG 不同步，安全修复已标记完成但文档仍列为"待执行"。

**方案**：
1. 逐项对照 CHANGELOG.md，将已完成的 BLOCKER/HIGH 项标记为 ✅
2. 将 MEDIUM/LOW 中已完成项标记为 ✅
3. 将未完成项标注当前状态和计划版本
4. 在文档顶部添加"最后更新日期"和"状态说明"

**涉及文件**：
- 修改：`/docs/optimization-plan.md`

**验证标准**：
- [ ] 文档状态与代码实际一致
- [ ] 未完成项有明确的计划版本

---

### T-3A-14 向导布局移动端适配

**问题**：向导页面在移动端布局不合理，步骤导航和编辑器难以操作。

**方案**：
1. 步骤导航：WizardProgress 在移动端改为下拉选择器或折叠式标签
2. 编辑区域：CodeMirror 编辑器移动端适配（虚拟键盘弹出时调整高度）
3. GuidePanel：移动端改为底部可展开面板
4. 表格组件：DataPreviewTable 移动端改为卡片列表
5. 使用 `useBreakpoint` composable 的 `isMobile` 判断

**涉及文件**：
- 修改：`configforge-web/src/components/wizard/WizardProgress.vue`
- 修改：`configforge-web/src/components/wizard/GuidePanel.vue`
- 修改：`configforge-web/src/components/step4/DataPreviewTable.vue`
- 修改：`configforge-web/src/views/ConfigWizardView.vue`

**验证标准**：
- [ ] 375px 宽度下向导可正常操作
- [ ] 步骤导航可切换
- [ ] 编辑器可输入
- [ ] 表格数据可查看

---

### T-3A-15 配置列表页面移动端适配

**问题**：配置列表、执行历史、定时任务页面在移动端布局不合理。

**方案**：
1. HomeView：配置卡片网格改为单列，搜索框全宽
2. ExecutionHistoryView：表格改为卡片列表，关键信息（名称/状态/时间）优先显示
3. SchedulesPage：同上
4. SettingsPage：Tab 标签改为下拉选择

**涉及文件**：
- 修改：`configforge-web/src/views/HomeView.vue`
- 修改：`configforge-web/src/views/ExecutionHistoryView.vue`
- 修改：`configforge-web/src/views/SchedulesPage.vue`
- 修改：`configforge-web/src/views/SettingsPage.vue`

**验证标准**：
- [ ] 375px 宽度下所有页面可正常浏览和操作
- [ ] 关键信息优先显示
- [ ] 无水平滚动条

---

### T-3A-16 清理 processor/processors 兼容逻辑

**问题**：wizard store 中 `processor`（单数旧格式）与 `processors`（复数新格式）并存兼容逻辑，属历史遗留。

**方案**：
1. 确认 `processor` 字段不再被任何前端代码引用
2. 从 `loadFromConfigState()` 中移除 `normalized.processor` 兼容代码
3. 从 store 的 `WizardState` 类型中移除 `processor` 字段
4. 确认后端 API 返回的数据不含 `processor` 字段（仅 `processors`）

**涉及文件**：
- 修改：`configforge-web/src/stores/wizard.ts`
- 修改：`configforge-web/src/types/wizard.ts`

**验证标准**：
- [ ] store 中无 `processor` 字段
- [ ] 前端 143 个测试全部通过
- [ ] 加载旧配置时自动迁移（`processor` → `processors`）

---

### T-3A-17 将 full-wizard.script.ts 纳入标准测试体系

**问题**：`e2e/full-wizard.script.ts` 是独立 Playwright 脚本，不被 `playwright.config.ts` 收集。

**方案**：
1. 将 `full-wizard.script.ts` 重命名为 `full-wizard.spec.ts`
2. 将脚本逻辑改为标准 Playwright test 格式（`test('full wizard flow', ...)`)
3. 确认 `npx playwright test` 能自动收集并执行

**涉及文件**：
- 重命名：`configforge-web/e2e/full-wizard.script.ts` → `full-wizard.spec.ts`

**验证标准**：
- [ ] `npx playwright test` 包含 full-wizard 测试
- [ ] 测试可正常执行

---

## Phase 3B：推送分发（v0.6.0）

### T-3B-01 Webhook 推送后端 — 核心服务

**目标**：实现 HTTP POST 推送能力，支持钉钉/企微/飞书机器人格式。

**方案**：
1. 新建 `configforge/services/notifier/` 包：
   ```
   notifier/
   ├── __init__.py
   ├── base.py          # NotifierBase 抽象类
   ├── webhook.py       # WebhookNotifier
   └── formatters.py    # 钉钉/企微/飞书消息格式化
   ```
2. `NotifierBase` 接口：
   ```python
   class NotifierBase(ABC):
       @abstractmethod
       async def send(self, context: NotifyContext) -> NotifyResult: ...
   
   @dataclass
   class NotifyContext:
       execution_id: str
       config_name: str
       status: str          # success / failed
       summary: str
       output_files: list[str]
       started_at: str
       finished_at: str
       error_message: str | None
   
   @dataclass
   class NotifyResult:
       success: bool
       message: str
       provider: str
   ```
3. `WebhookNotifier`：
   - 支持 HTTP POST JSON 推送
   - 支持自定义 Headers
   - 超时 10 秒
   - 重试 1 次（仅网络错误时）
4. `formatters.py`：
   - `format_dingtalk(context)` → 钉钉 markdown 消息格式
   - `format_wecom(context)` → 企微 markdown 消息格式
   - `format_feishu(context)` → 飞书 interactive card 格式
   - `format_generic(context)` → 通用 JSON 格式

**涉及文件**：
- 新建：`configforge/services/notifier/__init__.py`
- 新建：`configforge/services/notifier/base.py`
- 新建：`configforge/services/notifier/webhook.py`
- 新建：`configforge/services/notifier/formatters.py`

**验证标准**：
- [ ] 单元测试覆盖 WebhookNotifier 发送逻辑
- [ ] 钉钉/企微/飞书格式化输出正确
- [ ] 超时和重试逻辑正确

---

### T-3B-02 Webhook 推送后端 — API 端点

**目标**：提供推送配置 CRUD + 手动触发 API。

**方案**：
1. 新建 `configforge/api/notifications.py`：
   ```
   POST   /api/notifications/configs          # 创建推送配置
   GET    /api/notifications/configs          # 列出推送配置
   GET    /api/notifications/configs/{id}     # 获取单个配置
   PUT    /api/notifications/configs/{id}     # 更新配置
   DELETE /api/notifications/configs/{id}     # 删除配置
   POST   /api/notifications/test/{id}        # 测试推送
   GET    /api/notifications/history          # 推送历史
   ```
2. 推送配置数据模型：
   ```python
   class NotificationConfig(BaseModel):
       id: str
       name: str
       type: Literal["webhook", "email"]
       enabled: bool = True
       # Webhook 配置
       webhook_url: str | None
       webhook_provider: Literal["dingtalk", "wecom", "feishu", "generic"] | None
       webhook_headers: dict[str, str] | None
       # 邮件配置（Phase 3B 后续）
       email_to: list[str] | None
       email_subject_template: str | None
       email_body_template: str | None
       # 触发条件
       trigger_on_success: bool = True
       trigger_on_failure: bool = True
       # 关联配置
       config_ids: list[str] | None  # None=所有配置
   ```
3. 推送配置持久化：`data/notifications.json`（复用 file_lock 机制）
4. 在 `server.py` 中注册路由

**涉及文件**：
- 新建：`configforge/api/notifications.py`
- 修改：`configforge/server.py`（注册路由）
- 新建：`configforge/models/notification.py`

**验证标准**：
- [ ] CRUD 端点测试通过
- [ ] 测试推送端点返回正确结果
- [ ] 推送历史可查询

---

### T-3B-03 Webhook 推送 — Pipeline 执行后自动触发

**目标**：Pipeline 执行完成后自动触发已启用的推送配置。

**方案**：
1. 在 `core/pipeline.py` 的 `execute_pipeline()` 返回结果后，调用通知服务
2. 新建 `configforge/services/notifier/dispatcher.py`：
   ```python
   async def dispatch_notifications(execution_result: dict):
       """Pipeline 执行完成后分发通知"""
       configs = load_enabled_configs()
       context = build_notify_context(execution_result)
       for config in configs:
           if should_trigger(config, context):
               notifier = create_notifier(config)
               result = await notifier.send(context)
               save_history(config, context, result)
   ```
3. 在 `api/wizard.py` 的 `/execute` 和 `api/configs.py` 的 `/{config_id}/execute` 端点中，执行完成后调用 `dispatch_notifications()`
4. 通知发送为异步，不阻塞执行结果返回

**涉及文件**：
- 新建：`configforge/services/notifier/dispatcher.py`
- 修改：`configforge/api/wizard.py`
- 修改：`configforge/api/configs.py`

**验证标准**：
- [ ] Pipeline 执行成功后自动触发 Webhook 推送
- [ ] Pipeline 执行失败后自动触发 Webhook 推送
- [ ] 通知发送不阻塞执行结果返回
- [ ] 推送历史正确记录

---

### T-3B-04 Webhook 推送前端 — 配置界面

**目标**：前端提供 Webhook 推送配置界面。

**方案**：
1. Step 5 新增"推送设置"折叠区域（位于 AI 预检下方）
2. 推送设置区域内容：
   - 已配置的推送列表（名称 + 类型 + 状态开关）
   - "添加推送"按钮 → 弹出配置弹窗
3. 推送配置弹窗：
   - 名称输入
   - 类型选择：Webhook / 邮件（邮件暂时 disabled）
   - Webhook URL 输入
   - 推送平台选择：钉钉 / 企微 / 飞书 / 通用
   - 自定义 Headers（key-value 对）
   - 触发条件：成功时推送 / 失败时推送（复选框）
   - "测试推送"按钮
4. 新建 composable：`useNotificationApi.ts`

**涉及文件**：
- 新建：`configforge-web/src/composables/useNotificationApi.ts`
- 新建：`configforge-web/src/components/step4/NotificationSettings.vue`
- 新建：`configforge-web/src/components/step4/NotificationConfigModal.vue`
- 修改：`configforge-web/src/views/ConfigWizardView.vue`（Step 5 添加推送设置区域）

**验证标准**：
- [ ] 可添加/编辑/删除 Webhook 推送配置
- [ ] 测试推送按钮可触发测试通知
- [ ] 推送配置持久化
- [ ] 暗色模式适配

---

### T-3B-05 邮件推送后端

**目标**：实现 SMTP 邮件推送，支持附件。

**方案**：
1. 新建 `configforge/services/notifier/email.py`：
   ```python
   class EmailNotifier(NotifierBase):
       def __init__(self, smtp_host, smtp_port, smtp_user, smtp_password, use_tls=True):
           ...
       
       async def send(self, context: NotifyContext) -> NotifyResult:
           msg = MIMEMultipart()
           msg["From"] = self.smtp_user
           msg["To"] = ", ".join(context.recipients)
           msg["Subject"] = render_template(context, self.subject_template)
           body = render_template(context, self.body_template)
           msg.attach(MIMEText(body, "html"))
           # 附件：输出文件（如有）
           for file_path in context.output_files:
               msg.attach(attach_file(file_path))
           # 发送
           with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
               server.starttls()
               server.login(self.smtp_user, self.smtp_password)
               server.send_message(msg)
   ```
2. SMTP 配置存储在 `data/notifications.json` 中（密码 Fernet 加密）
3. 在 `api/notifications.py` 中新增 SMTP 设置端点：
   ```
   GET    /api/notifications/smtp-settings     # 获取 SMTP 设置（密码脱敏）
   PUT    /api/notifications/smtp-settings     # 更新 SMTP 设置
   POST   /api/notifications/test-smtp         # 测试 SMTP 连接
   ```

**涉及文件**：
- 新建：`configforge/services/notifier/email.py`
- 修改：`configforge/api/notifications.py`
- 修改：`configforge/models/notification.py`

**验证标准**：
- [ ] 邮件发送成功（mock SMTP 测试）
- [ ] 附件正确附加
- [ ] SMTP 密码加密存储
- [ ] SMTP 设置端点测试通过

---

### T-3B-06 邮件推送前端

**目标**：前端提供邮件推送配置界面。

**方案**：
1. 在 NotificationConfigModal 中启用邮件类型选项
2. 邮件配置字段：
   - 收件人（多值输入，支持逗号分隔）
   - 主题模板（Jinja2 变量可用）
   - 正文模板（Jinja2 变量可用，HTML 格式）
   - 附件开关（是否附带输出文件）
3. 设置页面新增 SMTP 配置 Tab：
   - SMTP 服务器 / 端口 / 用户名 / 密码 / TLS 开关
   - "测试连接"按钮

**涉及文件**：
- 修改：`configforge-web/src/components/step4/NotificationConfigModal.vue`
- 修改：`configforge-web/src/views/SettingsPage.vue`（新增 SMTP Tab）

**验证标准**：
- [ ] 可配置邮件推送
- [ ] SMTP 设置可保存和测试
- [ ] 暗色模式适配

---

### T-3B-07 推送模板引擎

**目标**：Jinja2 模板引擎渲染推送内容，支持变量注入。

**方案**：
1. 新建 `configforge/services/notifier/template_engine.py`：
   ```python
   def render_template(context: NotifyContext, template: str) -> str:
       env = Jinja2Environment(autoescape=True)
       tpl = env.from_string(template)
       return tpl.render(**context.__dict__)
   ```
2. 内置变量：
   - `{{ config_name }}` — 配置名称
   - `{{ status }}` — 执行状态（success/failed）
   - `{{ summary }}` — 执行摘要
   - `{{ started_at }}` / `{{ finished_at }}` — 时间
   - `{{ duration }}` — 执行耗时
   - `{{ output_files }}` — 输出文件列表
   - `{{ error_message }}` — 错误信息（失败时）
3. 默认模板：
   - 邮件主题：`[ConfigForge] {{ config_name }} {{ status }}`
   - 邮件正文：HTML 格式，含执行摘要和输出文件链接
   - Webhook 消息：对应平台 markdown 格式

**涉及文件**：
- 新建：`configforge/services/notifier/template_engine.py`

**验证标准**：
- [ ] 模板渲染正确
- [ ] 变量注入完整
- [ ] 默认模板格式正确

---

### T-3B-08 推送历史查看

**目标**：前端可查看推送历史记录。

**方案**：
1. 后端：推送历史持久化到 `data/notification_history.json`
2. 后端：`GET /api/notifications/history` 支持分页查询
3. 前端：设置页面新增"推送历史"Tab 或独立页面
4. 历史记录字段：时间、配置名称、推送类型、状态（成功/失败）、耗时、错误信息

**涉及文件**：
- 修改：`configforge/api/notifications.py`
- 新建：`configforge-web/src/views/NotificationHistoryView.vue`（或在 SettingsPage 中新增 Tab）
- 修改：`configforge-web/src/router/index.ts`（如新增路由）

**验证标准**：
- [ ] 推送历史可查看
- [ ] 支持分页
- [ ] 失败记录显示错误信息

---

### T-3B-09 推送功能集成测试

**目标**：端到端验证推送功能。

**方案**：
1. 后端测试：
   - WebhookNotifier 发送测试（mock httpx）
   - EmailNotifier 发送测试（mock SMTP）
   - 推送配置 CRUD 测试
   - dispatcher 自动触发测试
2. 前端测试：
   - NotificationConfigModal 组件测试
   - useNotificationApi composable 测试
3. E2E 测试：
   - 配置 Webhook → 执行 Pipeline → 验证推送触发

**涉及文件**：
- 新建：`configforge/tests/test_notifier.py`
- 新建：`configforge/tests/test_api_notifications.py`
- 新建：`configforge-web/tests/components/NotificationConfigModal.test.ts`
- 新建：`configforge-web/tests/composables/useNotificationApi.test.ts`

**验证标准**：
- [ ] 后端推送测试 ≥ 15 个
- [ ] 前端推送测试 ≥ 5 个
- [ ] E2E 推送测试通过

---

### T-3B-10 Webhook 推送钉钉格式验证

**目标**：验证钉钉机器人消息格式正确。

**方案**：
1. 按钉钉开放文档验证 markdown 消息格式
2. 确认消息标题、正文、链接格式
3. 编写格式化单元测试

**涉及文件**：
- 修改：`configforge/services/notifier/formatters.py`
- 修改：`configforge/tests/test_notifier.py`

**验证标准**：
- [ ] 钉钉 markdown 消息格式符合文档
- [ ] 单元测试通过

---

### T-3B-11 Webhook 推送企微格式验证

**目标**：验证企微机器人消息格式正确。

**方案**：同 T-3B-10，按企微文档验证。

**涉及文件**：
- 修改：`configforge/services/notifier/formatters.py`
- 修改：`configforge/tests/test_notifier.py`

**验证标准**：
- [ ] 企微 markdown 消息格式符合文档

---

### T-3B-12 Webhook 推送飞书格式验证

**目标**：验证飞书机器人消息格式正确。

**方案**：同 T-3B-10，按飞书文档验证。

**涉及文件**：
- 修改：`configforge/services/notifier/formatters.py`
- 修改：`configforge/tests/test_notifier.py`

**验证标准**：
- [ ] 飞书 interactive card 消息格式符合文档

---

## Phase 3C：AI 自愈（v0.6.1）

### T-3C-01 执行失败自动调用 diagnose

**目标**：Pipeline 执行失败时自动调用 AI diagnose category。

**方案**：
1. 在 `api/wizard.py` 的 `/execute` 端点中，捕获 Pipeline 执行异常
2. 异常时自动调用 `orchestrator.ask("diagnose", {"yaml": yaml_text, "errorLog": error_message})`
3. 将诊断结果附加到执行历史记录中
4. 前端执行结果中新增 `diagnosis` 字段

**涉及文件**：
- 修改：`configforge/api/wizard.py`
- 修改：`configforge/api/configs.py`
- 修改：`configforge/models/wizard.py`（ExecutionRecord 新增 diagnosis 字段）

**验证标准**：
- [ ] 执行失败时自动生成诊断
- [ ] 诊断结果保存在执行历史中
- [ ] 诊断不影响执行结果返回

---

### T-3C-02 执行失败弹窗显示 AI 诊断

**目标**：前端执行失败时弹窗显示 AI 诊断结果。

**方案**：
1. 修改 `ExecuteConfigModal.vue`：
   - 执行失败时，如果返回了 `diagnosis`，显示诊断弹窗
   - 弹窗内容：根因（cause）、修复建议（suggestions）、严重级别（severity）
   - 建议列表可点击，跳转到对应步骤
2. 诊断弹窗样式：
   - severity=error：红色边框
   - severity=warning：橙色边框
   - 修复建议列表：每条建议有"前往修复"按钮

**涉及文件**：
- 修改：`configforge-web/src/components/ExecuteConfigModal.vue`
- 新建：`configforge-web/src/components/common/DiagnosisPanel.vue`

**验证标准**：
- [ ] 执行失败时显示诊断弹窗
- [ ] 诊断结果清晰展示根因和建议
- [ ] "前往修复"按钮跳转到正确步骤
- [ ] 暗色模式适配

---

### T-3C-03 AI 自动修复 — 简单场景

**目标**：诊断后提供"AI 自动修复"按钮，适用于简单场景。

**方案**：
1. 后端新增 `autofix` category：
   - system prompt：根据诊断结果和当前配置，生成修复后的配置 diff
   - 返回格式：`{"fixes": [{"step": 1, "field": "sql", "old": "...", "new": "...", "reason": "..."}]}`
   - 限制：仅修复简单场景（列名拼写、缺少引号、表名不匹配）
2. 后端新增端点：`POST /api/ai/autofix`
   - 输入：config_id + diagnosis
   - 输出：修复 diff 列表
3. 前端：
   - 诊断弹窗中新增"AI 自动修复"按钮
   - 点击后展示修复 diff（old → new 高亮对比）
   - 用户确认后应用修复（更新 store 对应字段）

**涉及文件**：
- 修改：`configforge/services/ai/orchestrator.py`（新增 autofix prompt）
- 修改：`configforge/models/ai.py`（新增 autofix category）
- 新建：`configforge/api/ai_autofix.py`（或合并到 ai.py）
- 修改：`configforge-web/src/components/common/DiagnosisPanel.vue`
- 新建：`configforge-web/src/components/common/AutofixDiffPanel.vue`

**验证标准**：
- [ ] 简单场景（列名拼写错误）可自动修复
- [ ] 修复 diff 清晰展示
- [ ] 用户确认后才应用修复
- [ ] 复杂场景不提供自动修复按钮

---

### T-3C-04 AI 修复建议 — 复杂场景

**目标**：复杂场景（如 SQL 逻辑错误）仅展示建议，不自动修复。

**方案**：
1. 后端 `autofix` prompt 中增加判断逻辑：
   - 如果修复涉及 SQL 逻辑变更，返回 `{"fixable": false, "suggestions": [...]}`
   - 如果修复仅涉及标识符/格式，返回 `{"fixable": true, "fixes": [...]}`
2. 前端：
   - `fixable=false` 时，诊断弹窗仅展示建议列表
   - 每条建议有"手动修复"按钮，跳转到对应步骤
   - 修复后可再次运行 AI 预检

**涉及文件**：
- 修改：`configforge/services/ai/orchestrator.py`
- 修改：`configforge-web/src/components/common/DiagnosisPanel.vue`

**验证标准**：
- [ ] 复杂场景不显示自动修复按钮
- [ ] 建议列表清晰展示
- [ ] "手动修复"按钮跳转到正确步骤

---

### T-3C-05 数据异常检测

**目标**：Pipeline 执行后 AI 分析输出数据，检测异常。

**方案**：
1. 后端新增 `anomaly` category：
   - system prompt：分析输出数据的统计特征，检测异常
   - 输入：输出数据样本（前 100 行）+ 统计摘要（行数、空值率、数值范围）
   - 返回格式：`{"anomalies": [{"type": "null_rate_spike", "column": "...", "detail": "...", "severity": "warning"}], "summary": "..."}`
2. 在 Pipeline 执行成功后，可选调用 anomaly 检测
3. 前端：执行成功弹窗中新增"AI 数据检测"标签页

**涉及文件**：
- 修改：`configforge/services/ai/orchestrator.py`
- 修改：`configforge/models/ai.py`
- 修改：`configforge-web/src/components/ExecuteConfigModal.vue`

**验证标准**：
- [ ] 执行成功后可触发异常检测
- [ ] 异常检测结果清晰展示
- [ ] 严重级别分色显示

---

### T-3C-06 异常报告推送通知

**目标**：异常检测结果通过推送系统通知用户。

**方案**：
1. 在 dispatcher 中新增 `trigger_on_anomaly` 条件
2. 异常检测完成后，如果存在 warning/error 级别异常，触发推送
3. 推送内容包含异常摘要

**涉及文件**：
- 修改：`configforge/services/notifier/dispatcher.py`
- 修改：`configforge/models/notification.py`

**验证标准**：
- [ ] 异常检测触发推送通知
- [ ] 推送内容包含异常摘要

---

### T-3C-07 AI 自愈功能测试

**目标**：AI 自愈功能测试覆盖。

**方案**：
1. 后端测试：
   - diagnose 自动触发测试
   - autofix 简单场景测试
   - autofix 复杂场景测试（返回 fixable=false）
   - anomaly 检测测试
2. 前端测试：
   - DiagnosisPanel 组件测试
   - AutofixDiffPanel 组件测试
3. 集成测试：执行失败 → 诊断 → 修复 → 重新执行

**涉及文件**：
- 新建：`configforge/tests/test_ai_autofix.py`
- 新建：`configforge-web/tests/components/DiagnosisPanel.test.ts`
- 新建：`configforge-web/tests/components/AutofixDiffPanel.test.ts`

**验证标准**：
- [ ] 后端 AI 自愈测试 ≥ 10 个
- [ ] 前端诊断组件测试 ≥ 5 个

---

### T-3C-08 AI 诊断 prompt 优化

**目标**：优化 diagnose prompt，提高诊断准确率。

**方案**：
1. 扩展 diagnose context：除 YAML + errorLog 外，增加输入源列信息、处理步骤代码、输出配置
2. 增加"常见错误模式"知识注入（如 SQLite 语法差异、列名大小写、表名不存在等）
3. 要求 AI 返回结构化的步骤定位（step number + field path）

**涉及文件**：
- 修改：`configforge/services/ai/orchestrator.py`

**验证标准**：
- [ ] 诊断结果包含准确的步骤定位
- [ ] 常见错误模式可被识别

---

### T-3C-09 执行历史页面显示诊断结果

**目标**：执行历史详情中可查看历史诊断结果。

**方案**：
1. 执行历史详情 API 返回 `diagnosis` 字段
2. 前端 ExecutionHistoryView 详情弹窗中新增"AI 诊断"标签页
3. 展示历史诊断的根因、建议、严重级别

**涉及文件**：
- 修改：`configforge/api/executions.py`
- 修改：`configforge-web/src/views/ExecutionHistoryView.vue`

**验证标准**：
- [ ] 执行历史详情可查看诊断结果
- [ ] 暗色模式适配

---

### T-3C-10 AI 自愈 E2E 测试

**目标**：端到端验证 AI 自愈流程。

**方案**：
1. E2E 测试场景：
   - 创建配置 → 故意写错 SQL → 执行 → 验证诊断弹窗出现
   - 点击"AI 自动修复" → 验证 diff 展示 → 确认修复 → 重新执行 → 验证成功

**涉及文件**：
- 新建：`configforge-web/e2e/ai-selfheal.spec.ts`

**验证标准**：
- [ ] E2E 测试通过

---

## Phase 3D：数据源扩展（v0.6.2）

### T-3D-01 JSON 文件输入后端

**目标**：支持 JSON 文件作为输入源。

**方案**：
1. 新建 `configforge/services/readers/json_reader.py`：
   - 读取 JSON 文件（支持对象数组格式）
   - 嵌套对象展平为 `parent.child` 列名
   - 自动推断列类型
2. 在 `api/files.py` 中扩展上传白名单：添加 `.json`
3. 在 `api/wizard.py` 的 `infer-input` 中支持 JSON 推断
4. 在 `generators/input.py` 中添加 JSON 输入生成器

**涉及文件**：
- 新建：`configforge/services/readers/json_reader.py`
- 修改：`configforge/api/files.py`
- 修改：`configforge/api/wizard.py`
- 修改：`configforge/generators/input.py`

**验证标准**：
- [ ] JSON 文件上传成功
- [ ] 列推断正确
- [ ] Pipeline 执行正确

---

### T-3D-02 JSON 文件输入前端

**目标**：前端支持 JSON 文件上传和配置。

**方案**：
1. InputSourceCard 中文件上传支持 `.json`
2. InputSourceList 类型选择中添加 JSON 选项
3. JSON 输入配置：展平策略（点号分隔 / 下划线分隔）

**涉及文件**：
- 修改：`configforge-web/src/components/step2/InputSourceCard.vue`
- 修改：`configforge-web/src/components/step2/InputSourceList.vue`

**验证标准**：
- [ ] JSON 文件可上传
- [ ] 展平策略可配置

---

### T-3D-03 XML 文件输入后端

**目标**：支持 XML 文件作为输入源。

**方案**：
1. 新建 `configforge/services/readers/xml_reader.py`：
   - 使用 `xml.etree.ElementTree` 解析
   - 支持 attribute 和 element 值提取
   - 重复元素自动展开为行
2. 上传白名单添加 `.xml`
3. 输入生成器添加 XML 支持

**涉及文件**：
- 新建：`configforge/services/readers/xml_reader.py`
- 修改：`configforge/api/files.py`
- 修改：`configforge/generators/input.py`

**验证标准**：
- [ ] XML 文件上传和解析正确
- [ ] 属性和元素值正确提取

---

### T-3D-04 XML 文件输入前端

**目标**：前端支持 XML 文件上传和配置。

**方案**：
1. InputSourceCard 支持 `.xml` 上传
2. XML 输入配置：行元素路径（XPath）

**涉及文件**：
- 修改：`configforge-web/src/components/step2/InputSourceCard.vue`
- 修改：`configforge-web/src/components/step2/InputSourceList.vue`

**验证标准**：
- [ ] XML 文件可上传
- [ ] 行元素路径可配置

---

### T-3D-05 Parquet 文件输入后端

**目标**：支持 Parquet 文件作为输入源（大数据场景）。

**方案**：
1. 新建 `configforge/services/readers/parquet_reader.py`：
   - 使用 `pyarrow.parquet` 读取
   - 自动推断 schema 和列类型
   - 支持列裁剪和行数限制
2. 添加 `pyarrow` 依赖到 pyproject.toml
3. 上传白名单添加 `.parquet`

**涉及文件**：
- 新建：`configforge/services/readers/parquet_reader.py`
- 修改：`pyproject.toml`（添加 pyarrow 依赖）
- 修改：`configforge/api/files.py`

**验证标准**：
- [ ] Parquet 文件上传和读取正确
- [ ] 列类型推断正确

---

### T-3D-06 REST API 输入后端

**目标**：支持从 REST API 拉取数据作为输入源。

**方案**：
1. 新建 `configforge/services/readers/api_reader.py`：
   ```python
   class ApiReader:
       def read(self, config: ApiInputConfig) -> list[dict]:
           # HTTP GET/POST 请求
           # 分页支持（offset/limit 或 cursor）
           # 响应 JSON 解析
           # 列推断
   ```
2. API 输入配置模型：
   ```python
   class ApiInputConfig(BaseModel):
       url: str
       method: Literal["GET", "POST"]
       headers: dict[str, str]
       params: dict[str, str] | None
       body: dict | None
       pagination: Literal["none", "offset", "cursor"] | None
       page_size: int = 100
       max_pages: int = 10
       data_path: str = ""  # JSON 响应中数据路径，如 "data.items"
   ```
3. 输入生成器添加 API 输入
4. 安全：URL 白名单校验、请求超时 30 秒

**涉及文件**：
- 新建：`configforge/services/readers/api_reader.py`
- 修改：`configforge/generators/input.py`
- 修改：`configforge/models/wizard.py`（新增 ApiInputConfig）

**验证标准**：
- [ ] REST API 数据拉取正确
- [ ] 分页支持正确
- [ ] 超时和错误处理正确

---

### T-3D-07 REST API 输入前端

**目标**：前端提供 REST API 输入配置界面。

**方案**：
1. InputSourceList 新增"REST API"类型选项
2. API 输入配置表单：
   - URL 输入
   - Method 选择（GET/POST）
   - Headers 编辑（key-value 对）
   - 分页配置（类型、页大小、最大页数）
   - 数据路径（JSON Path）
3. "测试连接"按钮：发送请求并预览前 5 行数据

**涉及文件**：
- 新建：`configforge-web/src/components/step2/ApiInputForm.vue`
- 修改：`configforge-web/src/components/step2/InputSourceList.vue`
- 修改：`configforge-web/src/types/wizard.ts`（新增 ApiInputConfig 类型）

**验证标准**：
- [ ] API 输入配置可填写
- [ ] 测试连接可预览数据
- [ ] 暗色模式适配

---

### T-3D-08 数据源扩展测试

**目标**：新增数据源测试覆盖。

**方案**：
1. 后端测试：
   - JSON reader 测试（对象数组、嵌套展平）
   - XML reader 测试（属性、元素、重复元素）
   - Parquet reader 测试
   - API reader 测试（mock httpx）
2. 前端测试：
   - ApiInputForm 组件测试
3. E2E 测试：上传 JSON/XML → 配置 Pipeline → 执行

**涉及文件**：
- 新建：`configforge/tests/test_json_reader.py`
- 新建：`configforge/tests/test_xml_reader.py`
- 新建：`configforge/tests/test_parquet_reader.py`
- 新建：`configforge/tests/test_api_reader.py`
- 新建：`configforge-web/tests/components/ApiInputForm.test.ts`

**验证标准**：
- [ ] 每种数据源 ≥ 5 个测试
- [ ] 前端 API 输入测试 ≥ 3 个

---

### T-3D-09 数据源扩展文档更新

**目标**：更新文档反映新增数据源。

**方案**：
1. 更新 README.md：数据源类型 3 → 6+
2. 更新 GuideView.vue：新增 JSON/XML/Parquet/API 输入说明
3. 更新 GuidePanel Step 2 文案

**涉及文件**：
- 修改：`/README.md`
- 修改：`configforge-web/src/views/GuideView.vue`
- 修改：`configforge-web/src/components/wizard/GuidePanel.vue`

**验证标准**：
- [ ] 文档与功能一致

---

## Phase 3E：配置市场（v0.7.0）

### T-3E-01 模板数据模型与后端 API

**目标**：定义模板数据模型，实现模板 CRUD API。

**方案**：
1. 新建 `configforge/models/template.py`：
   ```python
   class Template(BaseModel):
       id: str
       name: str
       description: str
       category: str  # "sales" / "finance" / "hr" / "ops" / "custom"
       tags: list[str]
       author: str
       version: str
       config_state: dict  # 完整的 WizardState JSON
       requirements: list[TemplateRequirement]  # 适配检测用
       created_at: str
       updated_at: str
   
   class TemplateRequirement(BaseModel):
       type: Literal["database", "ai", "input_format"]
       description: str
   ```
2. 新建 `configforge/api/templates.py`：
   ```
   GET    /api/templates              # 模板列表（支持 category/search 过滤）
   GET    /api/templates/{id}         # 模板详情
   POST   /api/templates              # 创建模板（从已有配置）
   PUT    /api/templates/{id}         # 更新模板
   DELETE /api/templates/{id}         # 删除模板
   POST   /api/templates/{id}/instantiate  # 从模板创建配置
   ```
3. 内置模板目录 `configforge/templates/`：
   - `monthly_sales_report.json`
   - `user_data_cleaning.json`
   - `financial_summary.json`
   - `inventory_tracking.json`

**涉及文件**：
- 新建：`configforge/models/template.py`
- 新建：`configforge/api/templates.py`
- 新建：`configforge/templates/`（内置模板目录）
- 修改：`configforge/server.py`（注册路由）

**验证标准**：
- [ ] 模板 CRUD 端点测试通过
- [ ] 内置模板可加载
- [ ] 从模板创建配置功能正确

---

### T-3E-02 模板市场前端页面

**目标**：前端模板市场页面，支持分类浏览、搜索、预览。

**方案**：
1. 新建 `TemplateMarketView.vue`：
   - 分类标签栏（全部 / 销售 / 财务 / 人力 / 运维 / 自定义）
   - 搜索框
   - 模板卡片网格（名称、描述、标签、作者）
   - 点击卡片 → 预览弹窗
2. 预览弹窗：
   - 模板详情（描述、输入源、处理步骤、输出配置）
   - "使用此模板"按钮 → 跳转到向导并加载配置
   - 适配检测结果（绿色/红色标记）
3. 首页 Hero 区域新增"浏览模板市场"入口

**涉及文件**：
- 新建：`configforge-web/src/views/TemplateMarketView.vue`
- 新建：`configforge-web/src/components/template/TemplateCard.vue`
- 新建：`configforge-web/src/components/template/TemplatePreviewModal.vue`
- 修改：`configforge-web/src/router/index.ts`
- 修改：`configforge-web/src/views/HomeView.vue`

**验证标准**：
- [ ] 模板市场页面可浏览
- [ ] 分类过滤和搜索正常
- [ ] 预览弹窗展示模板详情
- [ ] "使用此模板"正确加载配置
- [ ] 暗色模式适配

---

### T-3E-03 从已有配置创建模板

**目标**：用户可将已保存的配置保存为模板。

**方案**：
1. 配置详情页新增"保存为模板"按钮
2. 弹窗填写：模板名称、描述、分类、标签
3. 后端：从配置 state 创建模板，自动提取 requirements
4. requirements 提取逻辑：
   - 检测是否使用数据库输入/输出 → 添加 database requirement
   - 检测是否使用 AI → 添加 ai requirement
   - 检测输入文件格式 → 添加 input_format requirement

**涉及文件**：
- 新建：`configforge-web/src/components/template/SaveAsTemplateModal.vue`
- 修改：`configforge-web/src/views/HomeView.vue`
- 修改：`configforge/api/templates.py`

**验证标准**：
- [ ] 可从已有配置创建模板
- [ ] requirements 自动提取正确
- [ ] 创建的模板出现在模板市场

---

### T-3E-04 适配检测

**目标**：使用模板前检测当前环境是否满足要求。

**方案**：
1. 后端新增 `POST /api/templates/{id}/check-compatibility`：
   - 检查 requirements：
     - database requirement → 检查是否有匹配类型的数据库连接
     - ai requirement → 检查 AI 是否已配置
     - input_format requirement → 检查是否支持该文件格式
   - 返回：`{"compatible": bool, "issues": [{"requirement": "...", "status": "missing/met", "suggestion": "..."}]}`
2. 前端：模板预览弹窗中显示适配检测结果
   - 绿色：所有要求满足
   - 红色：有缺失要求，显示修复建议

**涉及文件**：
- 修改：`configforge/api/templates.py`
- 修改：`configforge-web/src/components/template/TemplatePreviewModal.vue`

**验证标准**：
- [ ] 适配检测正确识别缺失依赖
- [ ] 修复建议清晰

---

### T-3E-05 模板市场测试

**目标**：模板市场功能测试覆盖。

**方案**：
1. 后端测试：
   - 模板 CRUD 测试
   - 从配置创建模板测试
   - 适配检测测试
   - 内置模板加载测试
2. 前端测试：
   - TemplateCard 组件测试
   - TemplatePreviewModal 组件测试
3. E2E 测试：浏览模板 → 预览 → 使用模板创建配置

**涉及文件**：
- 新建：`configforge/tests/test_api_templates.py`
- 新建：`configforge-web/tests/components/TemplateCard.test.ts`
- 新建：`configforge-web/e2e/template-market.spec.ts`

**验证标准**：
- [ ] 后端模板测试 ≥ 10 个
- [ ] 前端模板测试 ≥ 5 个
- [ ] E2E 模板测试通过

---

### T-3E-06 模板市场文档更新

**目标**：更新文档反映模板市场功能。

**方案**：
1. 更新 README.md：新增模板市场章节
2. 更新 GuideView.vue：新增模板市场使用说明
3. 更新 CHANGELOG.md

**涉及文件**：
- 修改：`/README.md`
- 修改：`configforge-web/src/views/GuideView.vue`

**验证标准**：
- [ ] 文档与功能一致

---

### T-3E-07 版本号更新与发布

**目标**：更新版本号，发布 v0.7.0。

**方案**：
1. 更新 pyproject.toml 版本号
2. 更新 package.json 版本号
3. 更新 CHANGELOG.md
4. 创建 git tag v0.7.0
5. 推送到 GitHub

**涉及文件**：
- 修改：`/pyproject.toml`
- 修改：`/configforge-web/package.json`
- 修改：`/CHANGELOG.md`

**验证标准**：
- [ ] 版本号一致
- [ ] CHANGELOG 完整
- [ ] git tag 创建成功

---

## 附录 A：任务依赖关系

```
Phase 3A（可并行）:
  T-3A-01~03 依赖管理 → 无依赖
  T-3A-04~08 基础设施 → 无依赖，可与 01~03 并行
  T-3A-09~10 代码质量 → 依赖 T-3A-01（删除根 package.json 后再拆分）
  T-3A-11~12 测试补充 → 无依赖
  T-3A-13 文档清理 → 无依赖
  T-3A-14~15 移动端 → 无依赖
  T-3A-16~17 清理 → 无依赖

Phase 3B（顺序）:
  T-3B-01 → T-3B-02 → T-3B-03（后端核心链路）
  T-3B-04（前端，依赖 T-3B-02）
  T-3B-05~06（邮件，依赖 T-3B-01）
  T-3B-07（模板，依赖 T-3B-01）
  T-3B-08（历史，依赖 T-3B-03）
  T-3B-09~12（测试+验证，依赖 T-3B-03）

Phase 3C（顺序）:
  T-3C-01 → T-3C-02（诊断链路）
  T-3C-03 → T-3C-04（修复链路，依赖 T-3C-02）
  T-3C-05 → T-3C-06（异常检测链路，依赖 Phase 3B 推送）
  T-3C-07~10（测试+优化，依赖 T-3C-04）

Phase 3D（可并行）:
  T-3D-00（pyarrow 依赖）→ T-3D-05（Parquet）依赖此
  T-3D-01~02（JSON）→ 独立
  T-3D-03~04（XML）→ 独立
  T-3D-05（Parquet）→ 依赖 T-3D-00
  T-3D-06~07（REST API）→ 独立
  T-3D-08~09（测试+文档）→ 依赖 00~07

Phase 3E（顺序）:
  T-3E-01 → T-3E-02 → T-3E-03 → T-3E-04（核心链路）
  T-3E-05~07（测试+文档+发布）→ 依赖 T-3E-04
```

---

## 附录 B：每个 Phase 的验收检查清单

### Phase 3A 验收
- [ ] `make install && make test` 全部通过
- [ ] `docker compose up` 一键启动
- [ ] GitHub Actions CI 绿色
- [ ] 375px 宽度下所有页面可操作
- [ ] 前端测试 ≥ 170 个
- [ ] 后端测试 ≥ 250 个

### Phase 3B 验收
- [ ] Webhook 推送可配置和测试
- [ ] 邮件推送可配置和测试
- [ ] Pipeline 执行后自动推送
- [ ] 推送历史可查看
- [ ] 钉钉/企微/飞书格式验证通过
- [ ] 后端推送测试 ≥ 15 个

### Phase 3C 验收
- [ ] 执行失败自动诊断
- [ ] 诊断弹窗显示根因和建议
- [ ] 简单场景可自动修复
- [ ] 复杂场景仅展示建议
- [ ] 数据异常检测可触发
- [ ] 异常推送通知正常

### Phase 3D 验收
- [ ] JSON/XML/Parquet 文件可上传和解析
- [ ] REST API 输入可配置和测试
- [ ] 每种数据源 ≥ 5 个测试
- [ ] 文档更新完整

### Phase 3E 验收
- [ ] 模板市场可浏览和搜索
- [ ] 可从模板创建配置
- [ ] 可从配置创建模板
- [ ] 适配检测正确
- [ ] 内置模板 ≥ 4 个
- [ ] 版本号 v0.7.0 发布
