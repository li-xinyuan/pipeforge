# ConfigForge 系统现状分析文档

> 生成日期：2026-06-26
> 版本：v1.0.0 (Phase 5D 完成)

---

## 一、项目概述

ConfigForge 是一个 Pipeline 配置管理平台，提供可视化的向导式配置流程，支持多种数据输入源（CSV/Excel/JSON/XML/Parquet/REST API/Database）、SQL/Python 数据处理、以及多种输出格式（Excel/CSV/Database）。系统包含 AI 辅助、模板市场、定时调度、版本管理等功能。

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Naive UI + Pinia + vue-i18n |
| 后端 | FastAPI + Python 3.12+ + APScheduler + Prometheus |
| 存储 | JSON 文件（configs/、data/） |
| 认证 | JWT (HS256) + 可选 API Key |
| 测试 | Playwright e2e + 后端 API 测试 |
| PWA | vite-plugin-pwa + CodeMirror |

---

## 二、Phase 5D 完成状态

### T-5D-01 监控与可观测性 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| Prometheus 指标定义 | ✅ | 6 个指标：HTTP 计数/延迟、Pipeline 计数/延迟、活跃连接、配置总数 |
| `/api/metrics` 端点 | ✅ | 无认证访问，标准 Prometheus 文本格式 |
| HTTP 请求中间件 | ✅ | 自动记录，排除自身避免递归 |
| Pipeline 执行指标 | ✅ | `record_pipeline_execution()` 在成功/失败路径中调用 |
| 活跃连接 Gauge | ✅ | `active_connections` 在执行前后 inc/dec |
| 配置总数 Gauge | ✅ | `configs_total` 在 `_save_index()` 中更新 |
| 前端错误上报 | ✅ | 批量队列 + 全局捕获 + Vue errorHandler |
| `/api/error-report` 端点 | ✅ | 无认证访问，记录到日志 |
| JSON 结构化日志 | ✅ | 含 request_id 关联，级别可配置 |

**修复记录**：
- `/api/metrics` 和 `/api/error-report` 加入 PUBLIC_PATHS（之前被 401 拦截）
- `record_pipeline_execution()` 从未被调用 → 在 `_handle_success/_handle_failure` 中调用
- `active_connections` / `configs_total` 从未被 set → 在执行生命周期和 `_save_index()` 中更新

### T-5D-02 数据备份与恢复 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| 备份创建 | ✅ | 打包 configs/ + data/ 到 zip，排除 backups 子目录 |
| 备份恢复 | ✅ | 从 zip 恢复，跳过元数据和 backups 目录 |
| 备份列表 | ✅ | 按时间倒序，含文件名/大小/创建时间 |
| 备份下载 | ✅ | application/zip，含路径穿越防护 |
| 定时备份 | ✅ | 每日凌晨 2:00，APScheduler CronTrigger |
| 保留策略 | ✅ | 默认保留最近 7 个，自动清理 |
| API 鉴权 | ✅ | admin 角色 + 审计日志 |

**实测结果**：创建/列表/下载/恢复全部正常，保留策略实测 9→7 清理正常。

### T-5D-03 配置导入导出 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| YAML/JSON 导出 | ✅ | RFC 5987 filename* 编码支持中文文件名 |
| YAML/JSON 导入 | ✅ | 5MB 限制 + UTF-8 校验 + WizardState 模型校验 |
| 格式验证 | ✅ | 仅支持 yaml/json，无效格式返回 400 |
| 导入安全 | ✅ | 自动生成新 ID、清除 fileId、审计日志 |
| 前端导入按钮 | ✅ | 首页"导入配置"按钮 |
| 前端导出菜单 | ✅ | "导出配置" + "导出为 JSON" |
| 前端下载修复 | ✅ | 检测 Content-Disposition: attachment 返回 Blob |

**修复记录**：
- 中文场景名导出 `latin-1` 编码失败 → `safe_name` 使用 `c.isascii()` + RFC 5987 `filename*`
- JSON 导出前端静默失败 → `useApi.ts` 检测 `Content-Disposition: attachment` 返回 Blob

### T-5D-04 Pipeline 执行通知增强 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| 增强字段 | ✅ | duration_seconds、row_count、error_type、stack_summary |
| 自定义模板 | ✅ | 12 个 `{{variable}}` 占位符，含 stack_summary |
| 频率控制 | ✅ | 5 分钟冷却期，三元组去重 |
| 格式化器 | ✅ | 钉钉/企微/飞书/通用（全部渲染 stack_summary） |

**修复记录**：
- `stack_summary` 字段定义了但未渲染 → 四种格式化器 + `render_template` + `get_template_variables` 全部补上

### T-5D-05 AI 辅助增强 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| suggest-checkpoint | ✅ | AI + 规则引擎双路径，15 组规则 |
| suggest-mapping | ✅ | AI + 规则引擎，同义词/规范化/子串匹配 |
| optimize-suggestions | ✅ | AI + 规则引擎，5 维度优化建议 |
| 限流 | ✅ | 10 次/60s/IP，429 响应 |
| 降级 | ✅ | AI 超时/失败 → 规则引擎兜底 |

**实测结果**：三个端点全部返回正确数据，规则引擎兜底正常。

### T-5D-06 国际化（i18n）✅

| 功能 | 状态 | 说明 |
|------|------|------|
| vue-i18n 框架 | ✅ | Composition API 模式，legacy: false |
| 语言文件 | ✅ | zh-CN.json / en-US.json，6 大分区 |
| 4 个高频页面 | ✅ | LoginView、AppNavBar、HomeView、SettingsPage |
| 语言切换器 | ✅ | SettingsPage 语言 Tab，NSelect，立即生效 |
| 语言持久化 | ✅ | configforge_locale localStorage |
| html lang 同步 | ✅ | setLocale() 和初始化时同步 |

**修复记录**：
- "刷新后生效"提示不准确 → 改为"立即生效"（vue-i18n 响应式切换无需刷新）

### T-5D-07 PWA 离线支持 ✅

| 功能 | 状态 | 说明 |
|------|------|------|
| vite-plugin-pwa | ✅ | autoUpdate 模式，生产环境注册 |
| Manifest | ✅ | standalone + 完整图标集 |
| 静态资源缓存 | ✅ | js/css/html/svg/png/fonts，2MB 上限 |
| 运行时缓存 | ✅ | Fonts (StaleWhileRevalidate) + API (NetworkFirst) |
| 离线回退 | ✅ | navigateFallback: index.html，API 排除 |
| 更新提示 UI | ✅ | PwaUpdatePrompt 组件 |
| 离线就绪通知 | ✅ | 5 秒自动消失的绿色提示 |

**修复记录**：
- `offlineReady` 状态有但未接入 UI → PwaUpdatePrompt 添加通知

---

## 三、测试覆盖

### Playwright e2e 测试（33 个）

| 测试文件 | 测试数 | 状态 |
|----------|--------|------|
| home.spec.ts | 8 | ✅ 全部通过 |
| login.spec.ts | 5 | ✅ 全部通过 |
| templates.spec.ts | 4 | ✅ 全部通过 |
| wizard.spec.ts | 7 | ✅ 全部通过 |
| full-wizard.spec.ts | 9 | ✅ 全部通过 |

### 用户视角浏览器测试（13 个）

| 测试 | 说明 | 状态 |
|------|------|------|
| Login | 登录流程 | ✅ |
| Home Page | 配置列表展示 | ✅ |
| New Config | 向导创建配置 | ✅ |
| Step 1 | 场景信息填写 | ✅ |
| Step 2 | CSV 文件上传 | ✅ |
| Step 3 | SQL 处理器添加 | ✅ |
| Step 4 | Excel 输出 + 列映射 | ✅ |
| Step 5 | YAML 预览（CodeMirror .cm-content） | ✅ |
| Save Config | 保存配置返回首页 | ✅ |
| Settings | 设置页面可访问 | ✅ |
| /api/metrics | 无认证访问 | ✅ |
| /api/error-report | 无认证访问 | ✅ |
| Home with Config | 配置保存后首页展示 | ✅ |

### 后端 API 实测

| API | 状态 |
|-----|------|
| POST /api/auth/login | ✅ |
| GET /api/health | ✅ |
| GET /api/metrics | ✅ |
| POST /api/error-report | ✅ |
| GET /api/backup | ✅ |
| POST /api/backup | ✅ |
| POST /api/backup/restore | ✅ |
| GET /api/configs/{id}/export?format=yaml | ✅ |
| GET /api/configs/{id}/export?format=json | ✅ |
| POST /api/configs/import | ✅ |
| POST /api/ai/suggest-checkpoint | ✅ |
| POST /api/ai/suggest-mapping | ✅ |
| POST /api/ai/optimize-suggestions | ✅ |

---

## 四、本次验证发现的 Bug 及修复

| # | 严重度 | Bug 描述 | 修复方案 | 涉及文件 |
|---|--------|---------|----------|----------|
| 1 | 高 | `/api/metrics` 和 `/api/error-report` 被 JWT 认证拦截 | 加入 `PUBLIC_PATHS` | `middleware/auth.py` |
| 2 | 高 | `record_pipeline_execution()` 从未被调用 | 在 `_handle_success/_handle_failure` 中调用 | `services/execution_service.py` |
| 3 | 高 | `active_connections` / `configs_total` Gauge 从未更新 | `active_connections` 在执行生命周期 inc/dec；`configs_total` 在 `_save_index()` 中 set | `execution_service.py`、`api/configs.py` |
| 4 | 高 | 中文场景名导出 `latin-1` 编码失败 | `safe_name` 使用 `c.isascii()` + RFC 5987 `filename*` | `api/configs.py` |
| 5 | 高 | JSON 导出前端静默失败 | `useApi.ts` 检测 `Content-Disposition: attachment` 返回 Blob | `composables/useApi.ts` |
| 6 | 中 | `stack_summary` 未渲染、未加入模板变量 | 四种格式化器 + `render_template` + `get_template_variables` 补上 | `services/notifier/formatters.py` |
| 7 | 低 | 语言切换提示"刷新后生效"不准确 | 改为"立即生效" | `locales/zh-CN.json`、`en-US.json` |
| 8 | 低 | `offlineReady` 通知未接入 UI | `PwaUpdatePrompt` 添加通知，5 秒自动消失 | `PwaUpdatePrompt.vue` |

---

## 五、已知限制与后续工作

### 已知限制

1. **i18n 覆盖范围**：仅 4 个高频页面完成翻译（LoginView、AppNavBar、HomeView、SettingsPage），向导等页面仍为硬编码中文（T-5E-06 处理）
2. **PWA 开发环境**：`devOptions.enabled: false`，开发时无法测试 SW 注册和离线缓存
3. **API 离线体验**：NetworkFirst 策略下 API 调用网络超时 10 秒后才 fallback 到缓存
4. **前端错误上报静默失败**：fetch 失败被完全忽略（设计合理，但调试困难）
5. **语言切换器位置**：仅在 SettingsPage 中，无导航栏快速切换

### Phase 5E 后续任务

| 任务 | 优先级 | 说明 |
|------|--------|------|
| T-5E-01 存储层抽象 | P4 | 定义 Protocol 接口，JSON/SQLite 双后端 |
| T-5E-06 i18n 剩余翻译 | P3 | 向导、通知等 80% 页面翻译 |
| T-5E-02 SQLite 后端 | P4 | SQLite 实现 + 数据迁移 |

---

## 六、系统架构概览

```
┌─────────────────────────────────────────────────┐
│                   Frontend (Vue 3)               │
│  ┌──────┐ ┌────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Login│ │ Home   │ │ Wizard   │ │ Settings │ │
│  │ i18n │ │ i18n   │ │ Step 1-5 │ │ i18n+Lang│ │
│  └──────┘ └────────┘ └──────────┘ └──────────┘ │
│  ┌──────────────┐ ┌────────────┐ ┌────────────┐ │
│  │ Error Report │ │ PWA/SW     │ │ CodeEditor │ │
│  │ (批量上报)   │ │ (autoUpdate)│ │ (CodeMirror)│ │
│  └──────────────┘ └────────────┘ └────────────┘ │
└───────────────────────┬─────────────────────────┘
                        │ Vite Proxy (/api)
┌───────────────────────┼─────────────────────────┐
│                   Backend (FastAPI)               │
│  ┌──────────────────────────────────────────────┐│
│  │ Auth Middleware (JWT + API Key)               ││
│  │ PUBLIC: / /api/health /api/metrics            ││
│  │         /api/error-report /api/auth/login     ││
│  └──────────────────────────────────────────────┘│
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐│
│  │ Configs │ │ Wizard   │ │ Backup   │ │ AI   ││
│  │ CRUD    │ │ Execute  │ │ /Restore │ │ APIs ││
│  │ Import  │ │ SSE      │ │ Schedule │ │      ││
│  │ Export  │ │          │ │ Cleanup  │ │      ││
│  └─────────┘ └──────────┘ └──────────┘ └──────┘│
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐│
│  │ Metrics │ │ Notifier │ │ Logging  │ │Audit ││
│  │(6指标)  │ │(4渠道)   │ │(JSON+rid)│ │Log   ││
│  └─────────┘ └──────────┘ └──────────┘ └──────┘│
│  ┌──────────────────────────────────────────────┐│
│  │ Storage Layer (JSON Files)                    ││
│  │ configs/  data/  templates/  backups/         ││
│  └──────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
```

---

## 七、结论

Phase 5D 全部 7 个任务已完成，系统功能稳定。通过全面验证发现了 8 个 Bug（3 高/2 中/3 低），全部已修复并通过：

- **33/33 Playwright e2e 测试通过**
- **13/13 用户视角浏览器测试通过**
- **14/14 后端 API 端点实测通过**

系统已达到 v1.0.0 发布标准，可进入 Phase 5E（架构演进）阶段。
