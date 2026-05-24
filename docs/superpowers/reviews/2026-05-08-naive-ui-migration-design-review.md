# ConfigForge UI/HCI 升级 — Naive UI 迁移设计审核报告

**审核日期**: 2026-05-08
**审核文件**: `docs/superpowers/specs/2026-05-12-naive-ui-migration-design.md`
**对照代码**: `configforge-web/src/` 全部前端源码

---

## 总体评价

设计方向正确，组件映射表覆盖全面（16 个映射），交互反馈体系设计合理（7 个场景对比），实施策略"自底向上、一次一页"稳妥。但存在 3 个 P0 级问题需在实施前明确，6 个 P1 级问题建议在设计中补充。

---

## 🔴 P0 — 必须修复

### P0-1：SettingsModal 和 SettingsPage 的去留未明确

**位置**: 逐页改动 > SettingsModal；移除清单

**问题**: 移除清单没有列出 `SettingsModal.vue` 和 `SettingsPage.vue`，逐页改动中只提到 SettingsModal 改为 NModal + NCard。当前代码中这两个文件有 **~90% 代码重复**：

| 文件 | 行数 | 触发方式 | API 调用方式 |
|------|------|---------|-------------|
| SettingsModal.vue | 146 | FloatingGear 点击打开弹窗 | 直接 `fetch('/api/ai/...')` |
| SettingsPage.vue | 156 | `/settings` 路由 | 通过 `useAiApi()` composable |

两者表单字段、逻辑、甚至 `testConnection()` 的"先保存再测试"行为完全一致，但 API 调用方式不同（一个用 composable，一个直接 fetch），迁移时必须统一。

**建议**: 明确去留策略。推荐方案：
- 保留 SettingsPage 作为唯一设置入口（路由 `/settings`）
- FloatingGear 点击后 `router.push('/settings')` 而非打开弹窗
- 删除 SettingsModal.vue，消除代码重复
- 在移除清单中补充 `SettingsModal.vue`

---

### P0-2：FloatingGear 替换为 NButton 会丢失拖拽功能

**位置**: 组件映射表最后一行

**问题**: 映射写 `FloatingGear.vue → NButton（圆形 + icon）`，但现有 FloatingGear 支持：

| 功能 | 现有实现 | NButton 能否支持 |
|------|---------|-----------------|
| 拖拽移动位置 | Pointer Events + setPointerCapture | ❌ 不支持 |
| 双击重置位置 | @dblclick 事件 | ❌ 不支持 |
| AI 配置状态指示 | 绿色 ✓ 角标 | ❌ 需额外 NBadge |
| 窗口 resize 自适应 | resize 事件监听 + clampPosition | ❌ 需自行实现 |
| 拖拽与点击区分 | moved 标志位，3px 阈值 | ❌ 需自行实现 |

**建议**: 保留 FloatingGear.vue 的拖拽逻辑，仅替换内部样式为 Naive UI 风格：

```html
<!-- 内部使用 NButton 圆形样式 + NBadge 角标 -->
<NButton circle size="large" quaternary>
  <template #icon><NIcon><SettingsIcon /></NIcon></template>
</NButton>
<NBadge v-if="aiConfigured" dot />
```

或使用 Naive UI 2.38+ 的 `n-float-button` 组件（如有）。

---

### P0-3：NDataTable 可编辑列映射的实现难度被低估

**位置**: 逐页改动 > Step4OutputView

**问题**: 设计写"列映射表用 NDataTable（可编辑）"，但 Naive UI 的 NDataTable **原生不支持单元格内联编辑**。需要通过 `render` 函数自定义列模板，手动管理编辑状态：

```ts
// 预期实现复杂度示例
const columns = [
  {
    title: '源列',
    key: 'source',
    render: (row, index) => h(NInput, {
      value: row.source,
      'onUpdate:value': (v) => { columns.value[index].source = v }
    })
  },
  // ... target 列 + 删除按钮列
]
```

还需处理：添加行、删除行、拖拽排序、空行校验等。实现复杂度远超"替换组件"的范畴。

**建议**:
- **方案 A（推荐）**: 保持现有的 ColumnMapping.vue 列表形式（每行一个 source NInput + target NInput + 删除 NButton），仅将手写 input/button 替换为 NInput/NButton
- **方案 B**: 使用 NDataTable + 自定义 render 列，但需在设计中补充详细的 render 函数实现方案和交互规格

---

## 🟡 P1 — 建议修复

### P1-1：NCode 组件需要额外依赖 highlight.js

**位置**: 组件映射表 > YamlPreview.vue → NCode

**问题**: Naive UI 的 NCode 组件依赖 `highlight.js` 作为 peer dependency，设计中未提及。且 `language="yaml"` 需要额外引入：

```ts
import 'highlight.js/lib/languages/yaml'
```

**建议**: 在实施策略第 1 步中补充：

```
npm install naive-ui highlight.js
```

并在主题配置中添加 NCode 的深色主题设置。

---

### P1-2：useMessage() 需要在 NMessageProvider 内使用

**位置**: 交互反馈体系；实施策略第 1 步

**问题**: Naive UI 的 `useMessage()` 必须在 `NMessageProvider` 包裹的组件内调用。设计中只提了"在 App.vue 挂 NConfigProvider + NMessageProvider + NModalProvider"，但需注意：
- `NMessageProvider` 必须在调用 `useMessage()` 的组件的**祖先**位置
- 不能在 App.vue 自身的 `setup()` 中调用 `useMessage()`（因为 Provider 还未挂载）

**建议**: 在 App.vue 中正确组织组件层级：

```html
<!-- App.vue -->
<NConfigProvider :theme-overrides="themeOverrides">
  <NMessageProvider>
    <NModalProvider>
      <NDialogProvider>
        <router-view />
        <FloatingGear />
      </NDialogProvider>
    </NModalProvider>
  </NMessageProvider>
</NConfigProvider>
```

各子组件中通过 `useMessage()` 获取 message 实例。如果需要在非组件上下文（如 composable 顶层）使用，需创建 `window.$message` 全局引用。

---

### P1-3：AiSuggestPanel 替换为 NAlert 的 v-html 问题未解决

**位置**: 组件映射表 > AiSuggestPanel.vue → NAlert + NButton

**问题**: 现有 AiSuggestPanel 使用 `v-html="content"` 渲染 AI 返回内容（包含 `<strong>` 等 HTML 标签）。白盒测试已发现这是 XSS 风险。替换为 NAlert 时需明确：
- NAlert 的默认插槽支持 HTML，但同样存在 XSS 风险
- 纯文本渲染会丢失 AI 返回的格式（加粗、列表等）

**建议**: 使用 NAlert + DOMPurify 消毒：

```ts
import DOMPurify from 'dompurify'

const safeContent = computed(() => DOMPurify.props.content)
```

并在依赖中添加 `dompurify`。

---

### P1-4：NSteps 需配合路由守卫

**位置**: 逐页改动 > StepIndicator → NSteps

**问题**: 设计写 `onUpdate:current` 触发 `store.goToStep() + router.push()`，但 NSteps 允许点击任意步骤跳转，未完成的步骤不应被跳到。当前代码没有路由守卫，白盒测试已确认用户可以直接访问 `/step/5`。

**建议**: 在 `onUpdate:current` 中添加校验：

```ts
function onStepClick(step: number) {
  if (step <= store.currentStep) {
    store.goToStep(step)
    router.push(`/step/${step}`)
  } else if (step === store.currentStep + 1 && store.canProceed) {
    store.goToStep(step)
    router.push(`/step/${step}`)
  }
}
```

同时为 NSteps 的未完成步骤添加 `status="wait"` 禁止点击样式。

---

### P1-5：NUpload 缺少文件类型和大小限制说明

**位置**: 逐页改动 > Step2InputView, Step4OutputView

**问题**: 设计只写了"文件上传区用 NUpload（accept='.xlsx,.xls,.csv'）"，但未说明：
- 文件大小限制（当前后端无限制，白盒测试确认 5.7MB 文件可上传）
- 上传失败的处理方式（NUpload 的 @error 事件）
- 如何对接现有的 `/api/files/upload` 端点（NUpload 默认发送 multipart，需 customRequest）

**建议**: 补充 NUpload 配置：

```ts
const uploadProps = {
  accept: '.xlsx,.xls,.csv',
  max: 1,
  customRequest: async ({ file, onFinish, onError }) => {
    const formData = new FormData()
    formData.append('file', file.file)
    try {
      const resp = await fetch('/api/files/upload', { method: 'POST', body: formData })
      const data = await resp.json()
      if (resp.ok) onFinish(data) else onError()
    } catch { onError() }
  },
}
```

---

### P1-6：缺少 Tailwind 清理策略

**位置**: 全局主题章节

**问题**: 设计写"保留 Tailwind 仅用于布局"，但现有代码中有大量非布局类 Tailwind 样式（颜色 `text-slate-900`、阴影 `shadow-lg`、边框 `border-slate-200`、圆角 `rounded-lg` 等）需要逐步替换。设计中未说明两种样式系统共存期间的兼容性。

**建议**: 添加"Tailwind 清理策略"章节：

1. **第一阶段**（迁移中）：只替换组件，保留所有 Tailwind 类。Naive UI 组件的样式优先级高于 Tailwind，不会冲突
2. **第二阶段**（迁移后）：逐页移除非布局类 Tailwind（颜色、阴影、边框、圆角等由 NConfigProvider 统一管理）
3. **最终状态**：Tailwind 只保留 `flex/grid/gap/p/m/max-w/mx-auto/w/h/min-h` 等布局类

---

## 🟢 P2 — 小改进建议

### P2-1：fontFamily 缺少系统字体 fallback

NConfigProvider 的 `fontFamily` 应包含系统字体栈作为 fallback：

```ts
fontFamily: '"Inter", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
```

### P2-2：配置列表建议用 NList

HomeView 的"已保存的配置"列表建议使用 `NList + NListItem` 而非 NCard，语义更准确（列表 vs 卡片）。

### P2-3：SQL 编辑器建议用 CodeMirror

Step3ProcessView 的 SQL 编辑器用 NInput type="textarea" 缺少行号和语法高亮。考虑使用 [CodeMirror 6](https://codemirror.net/) 替代，NInput textarea 体验差距太大。可在第二阶段引入。

### P2-4：实施顺序建议调整

"一次一个页面"的顺序建议调整：先做 **Step1**（最简单，只有 NInput + NButton），验证主题配置和 Provider 层级正确后再做复杂页面。推荐顺序：

```
Step1 → HomeView → Step2 → Step3 → Step4 → Step5 → Settings
```

### P2-5：移除清单遗漏

移除清单中遗漏了 `FloatingGear.vue`（如果按 P0-2 保留拖拽则不移除，如果替换为 NButton 则需移除）。建议根据 P0-2 的决策更新清单。

---

## 审核清单

| # | 级别 | 问题 | 状态 |
|---|------|------|------|
| P0-1 | 🔴 | SettingsModal/SettingsPage 去留未明确 | ❌ 待修复 |
| P0-2 | 🔴 | FloatingGear 替换为 NButton 丢失拖拽 | ❌ 待修复 |
| P0-3 | 🔴 | NDataTable 可编辑实现难度被低估 | ❌ 待修复 |
| P1-1 | 🟡 | NCode 需要 highlight.js 依赖 | ❌ 待修复 |
| P1-2 | 🟡 | useMessage() 需在 NMessageProvider 内 | ❌ 待修复 |
| P1-3 | 🟡 | AiSuggestPanel → NAlert 的 v-html 问题 | ❌ 待修复 |
| P1-4 | 🟡 | NSteps 需配合路由守卫 | ❌ 待修复 |
| P1-5 | 🟡 | NUpload 缺少文件限制说明 | ❌ 待修复 |
| P1-6 | 🟡 | 缺少 Tailwind 清理策略 | ❌ 待修复 |
| P2-1 | 🟢 | fontFamily 缺少系统字体 fallback | 💡 建议 |
| P2-2 | 🟢 | 配置列表建议用 NList | 💡 建议 |
| P2-3 | 🟢 | SQL 编辑器建议用 CodeMirror | 💡 建议 |
| P2-4 | 🟢 | 实施顺序建议从 Step1 开始 | 💡 建议 |
| P2-5 | 🟢 | 移除清单遗漏 FloatingGear | 💡 建议 |
