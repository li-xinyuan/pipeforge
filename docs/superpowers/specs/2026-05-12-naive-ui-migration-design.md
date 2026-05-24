# ConfigForge UI/HCI 升级 — Naive UI 迁移设计

> **Goal:** 将 ConfigForge 前端从纯 Tailwind 手写样式迁移到 Naive UI 组件库，全面提升视觉一致性、操作反馈质感和信息层级清晰度。

**Architecture:** 安装 `naive-ui` + `highlight.js` + `dompurify`，在 `App.vue` 用 `NConfigProvider > NMessageProvider > NModalProvider > NDialogProvider` 包裹应用。逐页用 Naive UI 组件替换自定义组件，保留 Tailwind 仅用于布局。最终删除被替代的自定义组件。

**Tech Stack:** Vue 3 + Naive UI + highlight.js + DOMPurify + Pinia + Tailwind（仅布局类）

**审核状态:** P0-1/P0-2/P0-3 及 P1-1~P1-6 已修正，P2-1~P2-5 已采纳。

---

## 组件映射表

| 现有（移除） | Naive UI 替代 | 说明 |
|---|---|---|
| StepIndicator.vue | **NSteps** | 5 步向导，自带已完成/当前/待处理状态和动效 |
| 手写 `<button>` + Tailwind 类 | **NButton** | type: primary/success/warning/error，统一 loading 态 |
| 手写 `<input>` / `<textarea>` | **NInput** | focus 光环动效，clearable，不同 size |
| 手写卡片 `div` + border | **NCard** | 统一阴影、圆角、header/footer 插槽 |
| LoadingSpinner.vue | **NSkeleton** / **NSpin** | 列表/表单用骨架屏，局部操作用 NSpin |
| ErrorBanner.vue | **NAlert** | 自带 icon、可关闭、type: error/warning/info |
| ConfirmDeleteModal.vue | **NModal** + **NCard** | 自带遮罩动效、ESC 关闭、body 滚动锁定 |
| ExecuteConfigModal.vue | **NModal** + **NCard** | 同上。保留现有业务逻辑（fileStates/upload/preview/execute） |
| 手写虚线文件上传区 | **NUpload**（customRequest） | 对接 `/api/files/upload` 端点 |
| 行内成功/失败文字 | **useMessage()** | 顶部弹出 Toast，3 秒自动消失 |
| YamlPreview.vue | **NCode** | 语法高亮（需 `import 'highlight.js/lib/languages/yaml'`）、行号、复制按钮 |
| 手写 `<select>` | **NSelect** | 搜索、自定义渲染 |
| CSV/Excel Badge（蓝色/绿色小标签） | **NTag** | 预设颜色，圆角一致 |
| AiSuggestPanel.vue | **NAlert** + **NButton** | 内容经 DOMPurify 消毒后渲染 |
| 手写 `<table>` 预览（ExecuteConfigModal 内） | 保留手写 `<table>` 或使用 NDataTable | 详见 P0-3 决策 |
| FloatingGear.vue | **保留**，内部改用 NButton + NBadge | 保留拖拽/双击重置/resize 自适应逻辑，仅样式 Naive UI 化 |

---

## App.vue Provider 层级

```html
<NConfigProvider :theme-overrides="themeOverrides">
  <NMessageProvider>
    <NModalProvider>
      <NDialogProvider>
        <router-view />
        <FloatingGear />  <!-- 保留拖拽逻辑，内部用 NButton + NBadge -->
      </NDialogProvider>
    </NModalProvider>
  </NMessageProvider>
</NConfigProvider>
```

各子组件内通过 `useMessage()` 获取 message 实例调用 toast。

---

## 全局主题（NConfigProvider）

```ts
const themeOverrides = {
  common: {
    primaryColor: '#2563eb',
    borderRadius: '8px',
    fontFamily: '"Inter", "PingFang SC", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  Button: { borderRadiusMedium: '8px' },
  Card: { borderRadius: '12px' },
  Steps: { stepHeaderFontSize: '13px' },
}
```

---

## Tailwind 清理策略

**第一阶段（迁移中）：** 只替换组件，保留所有现有 Tailwind 类。Naive UI 组件样式优先级高于 Tailwind，不会冲突。

**第二阶段（迁移后）：** 逐页移除非布局类 Tailwind（颜色、阴影、边框、圆角等由 NConfigProvider 统一管理）。

**最终状态：** Tailwind 只保留 `flex`, `grid`, `gap-*`, `px-*`, `py-*`, `max-w-*`, `mx-auto`, `w-*`, `h-*`, `min-h-*` 等布局类。

---

## 逐页改动

### Step1SceneView（实施顺序第 1 页，验证主题）
- SceneInfoForm 改为 NCard 内嵌 NInput
- NInput size="large"，placeholder 清晰
- 下一步 / 取消用 NButton
- NSteps 换 StepIndicator

### HomeView
- 标题使用 NTag/NBadge 装饰
- 简介用 NCard（bordered, size="small"）
- 「开始创建新配置」用 NButton type="primary" size="large"
- 配置列表加载态用 NSkeleton（3 行骨架）
- 错误态用 NAlert type="error"
- 空态用 NResult status="info"
- 配置列表用 **NList + NListItem**（语义优于 NCard）
- 操作按钮用 NButton（text / size="tiny"），删除用 type="error"
- 删除确认用 NModal + useMessage() 反馈

### Step2InputView
- 「添加输入源」用 NButton type="primary" dashed
- 「AI 分析列」用 NButton（secondary）
- 文件上传区用 **NUpload + customRequest**（对接 `/api/files/upload`）：

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

- 已上传文件信息用 NTag + NButton（预览/移除）
- AI 分析弹窗用 NModal

### Step3ProcessView
- 处理方式选择器（展开态）：保持 3 列 grid，卡片用 NCard（selectable）
- 折叠态：NTag + 文字 + NButton（text, "重选处理方式"）
- SQL 输入用 NInput type="textarea"（monospace，深色背景）
- AI 生成 SQL 面板用 NCollapseTransition
- 输出表名用 NInput + NTag（冲突提示）
- NSteps 换 StepIndicator
- P2-3 注：CodeMirror 6 作为第二阶段 SQL 编辑器升级

### Step4OutputView
- 输出格式选择器：同 Step3 折叠模式
- 模板上传用 NUpload + customRequest
- sourceTable 下拉用 NSelect
- Sheet/文件名用 NInput
- **列映射保留 ColumnMapping.vue 模式**（每行 NInput source + NInput target + NButton 删除），仅将手写 input/button 替换为 Naive UI 组件。不使用 NDataTable 可编辑模式（实现复杂度过高）
- 「试运行并下载」用 NButton type="success"
- 执行中：NButton loading + NSkeleton 预览区

### Step5ExportView
- YAML 预览用 NCode（language="yaml", show-line-numbers）
- 「自动更新场景描述」用 NButton（secondary）
- 「刷新预览」用 NButton（secondary）
- 「保存配置」用 NButton type="success"
- 「下载 YAML」用 NButton
- 「复制到剪贴板」用 NButton + useMessage() 反馈
- 场景描述更新提示用 useMessage() success

### Settings（唯一设置入口）
- **删除 SettingsModal.vue**（与 SettingsPage 有 ~90% 代码重复）
- SettingsPage 用 Naive UI 重写：NCard + NInput + NSelect
- API Key 用 NInput type="password" show-password-on="click"
- 测试连接用 NButton loading
- API 调用统一通过 `useAiApi()` composable
- FloatingGear 点击后 `router.push('/settings')` 而非打开弹窗

---

## 交互反馈体系

| 场景 | Before | After |
|---|---|---|
| 列表/表单加载 | LoadingSpinner（转圈） | NSkeleton（骨架屏），感知更快 |
| 保存/删除成功 | 行内绿色/红色文字 | useMessage() success/error Toast |
| 执行失败 | 行内红色文字 | useMessage() error + NAlert（可展开详情） |
| 按钮操作中 | 文字变为"⏳ 处理中..." | NButton loading（旋转 icon + 禁用） |
| 弹窗打开/关闭 | 无过渡 | NModal 自带 fade + scale 动效 |
| Steps 切换 | 无过渡 | NSteps 自带进度动效 |
| 上传文件 | 手写状态文字 | NUpload 自带进度条 + 文件列表 |

---

## NSteps 路由守卫

```ts
function onStepClick(step: number) {
  // 已完成的步骤可回跳
  if (step <= store.currentStep) {
    store.goToStep(step)
    router.push(`/step/${step}`)
  }
  // 下一步可达则允许前进
  else if (step === store.currentStep + 1 && store.canProceed) {
    store.goToStep(step)
    router.push(`/step/${step}`)
  }
  // 否则忽略点击（未完成步骤不可跳转）
}
```

---

## AiSuggestPanel 内容消毒

```ts
import DOMPurify from 'dompurify'

const safeContent = computed(() =>
  DOMPurify.sanitize(store.aiSuggestions['sql']?.content || '')
)
```

NAlert 默认插槽使用 `v-html="safeContent"`。

---

## 移除清单

删除以下文件（功能被 Naive UI 替代或代码重复）：
- `src/components/common/StepIndicator.vue` — NSteps 替代
- `src/components/common/LoadingSpinner.vue` — NSkeleton / NSpin 替代
- `src/components/common/ErrorBanner.vue` — NAlert 替代
- `src/components/common/ConfirmDeleteModal.vue` — NModal + NCard 替代
- `src/components/common/AiSuggestPanel.vue` — NAlert + NButton 替代
- `src/components/step4/YamlPreview.vue` — NCode 替代
- `src/components/SettingsModal.vue` — 与 SettingsPage 重复，统一用 SettingsPage

保留 `FloatingGear.vue`（仅内部样式 Naive UI 化），保留 `ExecuteConfigModal.vue` 的业务逻辑（Modal 部分用 NModal 重写）。

---

## 实施策略

1. **安装依赖** — `npm install naive-ui highlight.js dompurify`
2. **设主题 + Provider** — 在 App.vue 按上述层级包裹，配置 themeOverrides，引入 `highlight.js/lib/languages/yaml`
3. **按顺序逐页替换** — Step1 → HomeView → Step2 → Step3 → Step4 → Step5 → Settings。Step1 最简单（NInput + NButton），先做验证主题和 Provider 层级正确
4. **Tailwind 两阶段清理** — 迁移中保留所有类，迁移后逐页移除非布局类
5. **最后删除** — 确认所有引用消除后，删除移除清单中的文件
