# Naive UI 迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ConfigForge 前端从纯 Tailwind 手写样式迁移到 Naive UI 组件库。

**Architecture:** App.vue 用 NConfigProvider > NMessageProvider > NModalProvider > NDialogProvider 包裹应用；逐页替换组件；保留 FloatingGear 拖拽逻辑（内部 Naive UI 化）；SettingsPage 成为唯一设置入口；最后删除被替代的自定义组件文件。

**Tech Stack:** Vue 3 + Naive UI + highlight.js + DOMPurify + Pinia + Tailwind（仅布局类）

---

### Task 1: 安装依赖

**Files:**
- Modify: `configforge-web/package.json`

- [ ] **Step 1: 安装 naive-ui、highlight.js、dompurify**

```bash
cd configforge-web && npm install naive-ui highlight.js dompurify
```

- [ ] **Step 2: 验证安装**

```bash
node -e "require('naive-ui'); require('highlight.js'); require('dompurify'); console.log('OK')"
```

---

### Task 2: App.vue 设置 Provider 层级 + 主题

**Files:**
- Modify: `configforge-web/src/App.vue`（全部重写）

- [ ] **Step 1: 重写 App.vue**

将 `App.vue` 改为以下内容——挂载 Provider 层级，引入 highlight.js yaml 语言，FloatingGear 改为路由跳转，移除 SettingsModal：

```vue
<template>
  <NConfigProvider :theme-overrides="themeOverrides">
    <NMessageProvider>
      <NModalProvider>
        <NDialogProvider>
          <div class="min-h-screen">
            <router-view />
            <FloatingGear @click="router.push('/settings')" />
          </div>
        </NDialogProvider>
      </NModalProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  NConfigProvider,
  NMessageProvider,
  NModalProvider,
  NDialogProvider,
} from 'naive-ui'
import 'highlight.js/lib/languages/yaml'
import FloatingGear from './components/FloatingGear.vue'

const router = useRouter()

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
</script>
```

移除 `ref`、`useAiStatus`、`SettingsModal` 等旧 import。删除原有的 `showSettings` / `onSettingsSaved` 逻辑。

- [ ] **Step 2: 验证开发服务器启动无报错**

```bash
cd configforge-web && npx vite --host 2>&1 | head -5
```

---

### Task 3: Step1SceneView + SceneInfoForm — NSteps + NInput + NButton

**Files:**
- Modify: `configforge-web/src/views/Step1SceneView.vue`
- Modify: `configforge-web/src/components/step1/SceneInfoForm.vue`

- [ ] **Step 1: 重写 SceneInfoForm.vue**

用 NCard 包裹，input → NInput，保留双向绑定 `v-model:value`：

```vue
<template>
  <NCard>
    <div class="grid grid-cols-2 gap-4 mb-4">
      <div>
        <label class="block text-sm font-medium mb-1">场景名称</label>
        <NInput v-model:value="store.scene.name" placeholder="输入场景名称" />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">版本</label>
        <NInput v-model:value="store.scene.version" placeholder="1.0" />
      </div>
    </div>
    <div>
      <label class="block text-sm font-medium mb-1">场景描述</label>
      <NInput v-model:value="store.scene.description" placeholder="可选，描述此流水线的用途" />
    </div>
  </NCard>
</template>

<script setup lang="ts">
import { NCard, NInput } from 'naive-ui'
import { useWizardStore } from '../../stores/wizard'

const store = useWizardStore()
</script>
```

label 保留 `<label class="block text-sm font-medium mb-1">` 用 Tailwind 布局。

- [ ] **Step 2: 重写 Step1SceneView.vue**

替换 StepIndicator → NSteps，按钮 → NButton：

```vue
<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <NSteps :current="store.currentStep - 1" @update:current="onStepClick">
      <NStep title="场景信息" description="基本信息" />
      <NStep title="数据源配置" description="上传与解析" />
      <NStep title="数据转换/处理" description="SQL 编写" />
      <NStep title="输出定义" description="格式与映射" />
      <NStep title="预览与导出" description="YAML 查看" />
    </NSteps>

    <div class="mb-6 mt-8">
      <h2 class="text-lg font-semibold mb-1">场景信息</h2>
      <p class="text-sm text-slate-500">填写场景的基本信息，名称用于标识流水线配置。</p>
    </div>

    <SceneInfoForm />

    <div class="flex justify-between items-center pt-6">
      <NButton text @click="router.push('/')">取消</NButton>
      <NButton type="primary" :disabled="!store.canProceed" @click="onNext">下一步</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import { NSteps, NStep, NButton } from 'naive-ui'
import SceneInfoForm from '../components/step1/SceneInfoForm.vue'

const router = useRouter()
const store = useWizardStore()

onMounted(() => { store.currentStep = 1 })

function onStepClick(step: number) {
  const s = step + 1  // NSteps 0-indexed → store 1-indexed
  if (s <= store.currentStep) {
    store.goToStep(s); router.push(`/step/${s}`)
  } else if (s === store.currentStep + 1 && store.canProceed) {
    store.goToStep(s); router.push(`/step/${s}`)
  }
}

function onNext() {
  if (store.canProceed) { store.nextStep(); router.push('/step/2') }
}
</script>
```

- [ ] **Step 3: 验证 NSteps 交互**

启动 dev server，访问 `/step/1`，确认：
- 步骤条显示当前在 Step 1
- NInput 输入正常
- NButton hover/click 正常
- 点击已完成的步骤可回跳

---

### Task 4: HomeView — NList + NCard + NButton + NSkeleton + NModal

**Files:**
- Modify: `configforge-web/src/views/HomeView.vue`

- [ ] **Step 1: 重写 HomeView.vue**

完整替换为 Naive UI 组件。保持业务逻辑不变（`listConfigs`/`loadConfigState`/`deleteConfig`/`downloadConfigYaml`），只替换模板和组件引用：

- 简介卡片：NCard (bordered, size="small")
- 「开始创建新配置」：NButton (type="primary", size="large")
- 加载态：NSkeleton (3 行 text)
- 错误态：NAlert (type="error")
- 空态：NResult (status="info", title="暂无已保存的配置")
- 列表：NList + NListItem
- 操作按钮：NButton (text, size="tiny")
- 删除确认：NModal + useMessage()

完整代码见文件。关键 import：
```ts
import { NCard, NButton, NSkeleton, NAlert, NResult, NList, NListItem, NModal, NTag, useMessage } from 'naive-ui'
```

删除确认弹窗用 `NModal` 替代 `ConfirmDeleteModal`（`preset="card"`, `title="确认删除"`, 内嵌 `NButton` 取消/确认）。

- [ ] **Step 2: 验证 HomeView**

访问 `/`，确认：加载态骨架屏 → 列表展示 → 点击配置加载 → 下载/执行/删除按钮交互。

---

### Task 5: Step2InputView + InputSourceCard + InputSourceList — NUpload + NTag + NButton

**Files:**
- Modify: `configforge-web/src/views/Step2InputView.vue`
- Modify: `configforge-web/src/components/step2/InputSourceCard.vue`
- Modify: `configforge-web/src/components/step2/InputSourceList.vue`

- [ ] **Step 1: 重写 InputSourceCard.vue**

文件上传区用 NUpload + customRequest 对接 `/api/files/upload`：
```ts
const uploadProps = {
  accept: '.xlsx,.xls,.csv',
  max: 1,
  customRequest: async ({ file, onFinish, onError }: any) => {
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

表名/参数键 input → NInput。预览表格保留手写 `<table>`（不引入 NDataTable）。按钮 → NButton。

- [ ] **Step 2: 重写 InputSourceList.vue**

「添加输入源」按钮 → NButton (dashed)。移除按钮 → NButton (text, type="error")。

- [ ] **Step 3: 重写 Step2InputView.vue**

StepIndicator → NSteps。AI 分析列按钮 → NButton。AiColumnAnalysisModal 的 Modal 部分改用 NModal。

- [ ] **Step 4: 验证 Step 2**

上传文件、填写表名/参数键、AI 分析列弹窗。

---

### Task 6: Step3ProcessView + SqlEditorTab — NInput + NTag + NButton

**Files:**
- Modify: `configforge-web/src/views/Step3ProcessView.vue`
- Modify: `configforge-web/src/components/step3/SqlEditorTab.vue`

- [ ] **Step 1: 重写 SqlEditorTab.vue**

- SQL textarea → NInput (type="textarea", rows=10, 添加 monospace 字体和深色背景)
- 输出表名 input → NInput
- AI 生成 SQL 按钮 → NButton
- 自然语言输入面板 → NCollapseTransition
- 处理方式选择器卡片 → NCard (selectable)
- 折叠态 → NTag + NButton (text)
- AiSuggestPanel → NAlert + DOMPurify 消毒

```vue
<NAlert v-if="safeSuggestion" type="info" closable>
  <span v-html="safeSuggestion" />
</NAlert>
```

```ts
import DOMPurify from 'dompurify'
const safeSuggestion = computed(() => {
  const content = store.aiSuggestions['sql']?.content
  return content ? DOMPurify.sanitize(content) : null
})
```

- [ ] **Step 2: 重写 Step3ProcessView.vue**

StepIndicator → NSteps。按钮 → NButton。

- [ ] **Step 3: 验证 Step 3**

输入 SQL、输出表名、AI 生成 SQL、自然语言输入面板展开/折叠。

---

### Task 7: Step4OutputView + OutputConfigTab + ColumnMapping + ExportActions

**Files:**
- Modify: `configforge-web/src/views/Step4OutputView.vue`
- Modify: `configforge-web/src/components/step3/OutputConfigTab.vue`
- Modify: `configforge-web/src/components/step3/ColumnMapping.vue`
- Modify: `configforge-web/src/components/step4/ExportActions.vue`

- [ ] **Step 1: 重写 ColumnMapping.vue**

每行：NInput (source) + NInput (target) + NButton (删除, text, type="error")。添加列按钮 → NButton (dashed)。

- [ ] **Step 2: 重写 OutputConfigTab.vue**

- 输出格式选择器：同 Step3 处理方式选择器模式（NCard + 折叠态 NTag）
- 模板上传：NUpload + customRequest
- sourceTable 下拉：NSelect
- Sheet/文件名/outputDir：NInput
- CSV 分隔符/编码：NInput / NSelect
- 列映射：引用 ColumnMapping
- AI 映射/从 SQL 推断列：NButton

switch 按钮 → NSwitch（如果 Naive UI 有）。或保留手动 toggle。

- [ ] **Step 3: 重写 ExportActions.vue**

按钮 → NButton。

- [ ] **Step 4: 重写 Step4OutputView.vue**

StepIndicator → NSteps。「试运行并下载」→ NButton (type="success", :loading="executing")。执行中骨架屏 → NSkeleton（替换 loading 文字）。

- [ ] **Step 5: 验证 Step 4**

选择输出格式、上传模板、配置列映射、试运行。

---

### Task 8: Step5ExportView — NCode + NButton + useMessage

**Files:**
- Modify: `configforge-web/src/views/Step5ExportView.vue`

- [ ] **Step 1: 重写 Step5ExportView.vue**

- StepIndicator → NSteps
- YAML 预览 → NCode (language="yaml", show-line-numbers, word-wrap)
- 按钮 → NButton
- 成功/失败提示 → useMessage() 替代行内 `saveMsg` 文字

```vue
<NCode :code="yamlContent" language="yaml" show-line-numbers word-wrap />
```

`yamlContent` 通过现有的 fetch `/api/wizard/yaml` 获取。

「保存配置」成功/失败使用 `message.success('配置已保存')` / `message.error('保存失败：' + err)`。

移除 `saveMsg` / `saveError` ref，改用 `useMessage()`。

- [ ] **Step 2: 验证 Step 5**

YAML 预览渲染、保存配置 toast、下载 YAML。

---

### Task 9: ExecuteConfigModal — NModal + NUpload + NButton

**Files:**
- Modify: `configforge-web/src/components/ExecuteConfigModal.vue`

- [ ] **Step 1: 重写为 NModal 包裹的内容**

Teleport → NModal (preset="card")。文件上传用 NUpload。按钮用 NButton。预览表格保留手写 `<table>`。业务逻辑（fileStates/upload/preview/execute）完全保留。

关键变化：`v-if="visible"` → NModal `:show="visible"`，`@click.self="$emit('close')"` → NModal `@update:show`。

---

### Task 10: FloatingGear — 内部 Naive UI 化

**Files:**
- Modify: `configforge-web/src/components/FloatingGear.vue`

- [ ] **Step 1: 替换内部样式**

保留所有 Pointer Events 拖拽逻辑（`onPointerDown`/`onPointerMove`/`onPointerUp`/`resetPosition`/`clampPosition`）。只替换模板中的 div 为 NButton + NBadge：

```vue
<template>
  <div
    ref="btnRef"
    @pointerdown="onPointerDown"
    @dblclick="resetPosition"
    class="fixed z-40 select-none touch-none"
    :style="{ left: pos.x + 'px', top: pos.y + 'px' }"
  >
    <NBadge :value="aiConfigured ? '✓' : ''" dot type="success">
      <NButton circle size="large" :secondary="!aiConfigured" :type="aiConfigured ? 'primary' : 'default'">
        <template #icon>
          <span class="text-lg">⚙</span>
        </template>
      </NButton>
    </NBadge>
  </div>
</template>

<script setup lang="ts">
// ... 保留所有现有逻辑代码 ...
import { NButton, NBadge } from 'naive-ui'
```

---

### Task 11: SettingsPage — NCard + NInput + NSelect + NButton

**Files:**
- Modify: `configforge-web/src/views/SettingsPage.vue`
- Delete: `configforge-web/src/components/SettingsModal.vue`

- [ ] **Step 1: 重写 SettingsPage.vue**

- 卡片 → NCard
- input → NInput
- select → NSelect
- API Key → NInput (type="password", show-password-on="click")
- temperature slider → NInput + NSlider
- 按钮 → NButton (测试连接 → default, 保存设置 → primary)
- switch → NSwitch
- 成功/失败提示 → useMessage()

保留 SettingsPage 的所有业务逻辑和 `useAiApi()` composable 调用。

- [ ] **Step 2: 删除 SettingsModal.vue**

```bash
rm configforge-web/src/components/SettingsModal.vue
```

- [ ] **Step 3: 验证设置页**

访问 `/settings`，配置 AI、测试连接、保存。

---

### Task 12: 删除被替代的自定义组件

**Files (delete):**
- `configforge-web/src/components/common/StepIndicator.vue`
- `configforge-web/src/components/common/LoadingSpinner.vue`
- `configforge-web/src/components/common/ErrorBanner.vue`
- `configforge-web/src/components/common/ConfirmDeleteModal.vue`
- `configforge-web/src/components/common/AiSuggestPanel.vue`
- `configforge-web/src/components/step4/YamlPreview.vue`
- `configforge-web/src/components/SettingsModal.vue`（已在 Task 11 删除）

- [ ] **Step 1: 确认所有引用已消除**

```bash
cd configforge-web
grep -r "StepIndicator\|LoadingSpinner\|ErrorBanner\|ConfirmDeleteModal\|AiSuggestPanel\|YamlPreview\|SettingsModal" src/ --include="*.vue" --include="*.ts"
```

预期无输出（或仅 `SettingsModal` 出现在 `SettingsPage.vue` 中作为注释）。

- [ ] **Step 2: 删除文件**

```bash
rm src/components/common/StepIndicator.vue
rm src/components/common/LoadingSpinner.vue
rm src/components/common/ErrorBanner.vue
rm src/components/common/ConfirmDeleteModal.vue
rm src/components/common/AiSuggestPanel.vue
rm src/components/step4/YamlPreview.vue
```

- [ ] **Step 3: 验证编译通过**

```bash
npx vue-tsc --noEmit 2>&1 | grep -c "error TS"
```

预期：只有既有的 15 个 InputSourceCard/OutputConfigTab 类型错误。

---

### Task 13: Tailwind 第二阶段的非布局类清理

**Files (modify):**
- 所有 `.vue` 文件中逐页移除装饰性 Tailwind 类

- [ ] **Step 1: 逐页清理非布局 Tailwind**

按顺序清理以下页面中已被 Naive UI 覆盖的装饰类（颜色、阴影、边框、圆角）：
1. Step1SceneView + SceneInfoForm
2. HomeView
3. Step2InputView + InputSourceCard + InputSourceList
4. Step3ProcessView + SqlEditorTab
5. Step4OutputView + OutputConfigTab + ColumnMapping
6. Step5ExportView
7. SettingsPage
8. FloatingGear
9. ExecuteConfigModal

保留：`flex`, `grid`, `gap-*`, `px-*`, `py-*`, `max-w-*`, `mx-auto`, `w-*`, `h-*`, `min-h-*`。

典型清理示例：
```diff
- <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
+ <NCard>
- <input class="w-full px-3 py-1.5 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
+ <NInput />
```

---

### Task 14: 最终验证

- [ ] **Step 1: 后端测试**

```bash
cd /Users/lixinyuan/code/CCTEST && python3 -m pytest configforge/tests/ -v
```

预期：56 passed。

- [ ] **Step 2: 前端类型检查**

```bash
cd configforge-web && npx vue-tsc --noEmit 2>&1 | grep -v "InputSourceCard\|OutputConfigTab"
```

预期：除既有 15 个 discriminated union 错误外无新增。

- [ ] **Step 3: 手动烟雾测试**

启动前后端，完整走通：
1. `/` → 首页加载配置列表
2. 点击「开始创建新配置」→ Step 1 → 填写场景信息
3. Step 2 → 上传文件 → 配置输入源
4. Step 3 → 编写 SQL → 设置输出表名
5. Step 4 → 上传模板 → 列映射 → 试运行下载
6. Step 5 → YAML 预览 → 保存配置 → Toast 提示
7. 返回首页 → 配置出现在列表中 → 加载/下载/执行/删除
8. `/settings` → 配置 AI → 测试连接
