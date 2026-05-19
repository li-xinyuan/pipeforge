# ConfigForge 修复与改进记录

> 日期: 2026-05-19  
> 基于: PROJECT_STATUS_REPORT_20260513.md 审查报告

---

## 一、构建与基础设施

### 修复前端构建失败 (P1)

**问题**：`npm run build` 因 `enhanced-resolve` 等依赖缺失而失败。

**原因**：`vite.config.ts` 使用了 `@tailwindcss/vite`，但该包及其传递依赖（`tailwindcss`、`@tailwindcss/node`、`@tailwindcss/oxide`、`lightningcss`、`jiti`、`enhanced-resolve` 等）未在 `package.json` 中声明。

**修复**：
- `package.json` — 新增 `@tailwindcss/vite` 到 devDependencies，`tailwindcss` 到 dependencies
- 补全缺失的传递依赖到 `node_modules`

### 添加测试运行脚本 (P10)

**问题**：`package.json` 缺少 `test` 命令。

**修复**：添加 `"test": "vitest"` 到 scripts，现在可以通过 `npm test` 运行前端测试。

### 更新静态构建产物 (P3)

**问题**：`configforge/static/` 中包含旧版步骤视图（`Step1SceneView` 等）的 JS 文件。

**修复**：重新执行 `npm run build && cp -R dist/* configforge/static/`，旧组件已清除，新版单页滚动视图正确部署。

---

## 二、功能修复

### 保存配置不再重复创建

**问题**：每次点击"保存配置"都生成新记录，同一条配置保存多次会得到多个条目。

**修复（5 处改动）**：

| 文件 | 改动 |
|------|------|
| `configforge/models/wizard.py` | `SaveConfigRequest` 新增可选字段 `config_id` |
| `configforge/api/configs.py` | `save_config` 使用 `req.config_id` 替代强制新建 UUID |
| `configforge-web/src/composables/useConfigApi.ts` | `saveConfig` 接受并传递 `configId` |
| `configforge-web/src/components/step4/ExportActions.vue` | 传 `store.configId`，保存后 `store.setConfigId(id)` |
| `configforge-web/src/views/ConfigWizardView.vue` | 加载已有配置时调用 `store.setConfigId(loadId)` |

**行为**：首次保存创建新配置并记住 ID，再次保存更新同一配置。

### AI 生成场景描述不生效

**问题**：点击"生成场景描述"后，AI 返回了 JSON `{"description": "..."}` 但场景描述字段没有更新。

**修复**：`ConfigWizardView.vue` — 解析 AI 返回的 JSON，提取 `description` 写入 `store.scene.description`，并在聊天框显示确认消息。

### 快捷提示词可点击 (P6)

**问题**：首页"试试这样说"下方的 3 个提示胶囊是纯 `<span>` 标签，无点击事件。

**修复**：
- `HomeView.vue` — `<span>` 改为 `<button>`，点击后跳转 `/config/new?prompt=...`
- `ConfigWizardView.vue` — `onMounted` 中读取 `route.query.prompt`，自动填入场景描述

### 下载文件名使用实际执行时间

**问题**：输出文件名中的日期是配置创建时的固定值，不会随执行时间更新。

**修复**：
- `ExportActions.vue` — 新增 `buildExecutionFilename()`，下载时实时生成 `{场景名}_{YYYYMMDD_HHmmss}.{ext}` 格式的文件名
- `OutputConfigTab.vue` — 文件名输入框下增加提示"执行下载时将自动替换文件名为实际执行时间（精确到秒）"

### 下载结果文件报错 "Missing required parameters"

**问题**：`param_key` 为空时，pipeforge 引擎的 `_validate_params()` 将空字符串当作必填参数，报错 "Missing required parameters: . "。

**修复**：
- `src/pipeforge/core/engine.py` — `required_params()` 过滤掉 `param_key` 为空的输入
- `src/pipeforge/core/engine.py` — `_execute_input()` 使用 `.get()` 安全获取参数，缺失时跳过并记录日志
- `ExportActions.vue` — 错误提示改为显示 API 返回的具体错误信息

---

## 三、新增页面

### 使用指南页面 (P5)

**路由**：`/guide`

**文件**：`src/views/GuideView.vue`

**内容**：覆盖完整 5 步向导（场景信息 → 输入源 → SQL 处理 → 输出配置 → 预览导出）、AI 助手使用、设置说明、暗色模式与响应式、安全说明等。页面包含导航栏和响应式布局。

**入口**：首页 Hero 区域"📖 使用指南"按钮。

---

## 四、待处理项

以下问题已核实但未在此次修改中处理：

| # | 问题 | 原因 |
|---|------|------|
| P2 | AI 列分析缺少 `sampleRows` | 后端已兼容新格式，只是缺少样本数据降低分析质量，影响不大 |
| P7 | 每步独立色彩标识 | 视觉设计细节，需要设计决策 |
| P8 | AI 内联建议覆盖不足 | Step2-5 无内联 AI 提示 |
| P9 | `as any` 类型断言 | `OutputTarget` 联合类型需要改进类型定义 |
| P11 | Fernet key 零填充回退 | 用户决定暂不强制要求 |
| P12 | 硬编码 system prompt | 灵活性改进，影响小 |
| P13 | 步骤解锁脉冲动画 | 视觉细节 |
| P14-P17 | 其他轻微项 | 低优先级 |
