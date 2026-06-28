# ConfigForge UI/UX 设计审查报告

> **审查日期**：2026-06-28  
> **审查范围**：前端全页面（登录、首页、向导、设置、历史、模板）  
> **审查维度**：布局、配色、交互设计、操作体验、无障碍、响应式  
> **审查人**：UI Designer

---

## 目录

1. [总体评价](#1-总体评价)
2. [布局设计分析](#2-布局设计分析)
3. [配色系统设计](#3-配色系统设计)
4. [交互设计评估](#4-交互设计评估)
5. [操作体验分析](#5-操作体验分析)
6. [组件设计细节](#6-组件设计细节)
7. [响应式设计](#7-响应式设计)
8. [无障碍访问](#8-无障碍访问)
9. [问题清单与优化建议](#9-问题清单与优化建议)
10. [优先级行动清单](#10-优先级行动清单)

---

## 1. 总体评价

| 维度 | 评分 | 说明 |
|------|------|------|
| 布局设计 | **85/100** | 清晰的视觉层次，向导式布局出色，但部分页面内容密度不均 |
| 配色系统 | **88/100** | 设计 Token 体系完善，暗色模式支持好，但对比度需验证 |
| 交互设计 | **82/100** | 微交互丰富，但部分反馈不够及时，Loading 状态不统一 |
| 操作体验 | **80/100** | 向导流程清晰，但部分操作路径过长，缺少快捷操作 |
| 组件质量 | **87/100** | 组件库较完整，但 NButton 与自定义 .cf-btn 混用 |
| 响应式 | **90/100** | 移动端适配到位，触摸目标 44px 符合要求 |
| 无障碍 | **75/100** | 有基础支持，但 ARIA 标签不完整，对比度未验证 |
| **综合评分** | **84/100** | **良好**，有明显可优化的空间 |

---

## 2. 布局设计分析

### ✅ 做得好的地方

#### 2.1 向导式布局（5 步流水线）
```
┌─────────────────────────────────────────┐
│  NavBar（固定顶部，毛玻璃效果）          │
├─────────────────────────────────────────┤
│  Step 1 场景信息  [✓]               │
│  ┌─────────────────────────────────┐  │
│  │  (可折叠，显示摘要)              │  │
│  └─────────────────────────────────┘  │
│  Step 2 输入源  [✓]                 │
│  ┌─────────────────────────────────┐  │
│  │  (展开，表单内容)                │  │
│  └─────────────────────────────────┘  │
│  Step 3 处理步骤 [→]                 │
│  Step 4 输出配置 [🔒]                 │
│  Step 5 预览导出 [🔒]                 │
│                                         │
│  [← 上一步]  [下一步 ↓]  [提示信息] │
├──────────────────┬──────────────────────┤
│                  │  AI 助手面板（右侧）  │
└──────────────────┴──────────────────────┘
```

**优点**：
- 步骤卡片可折叠，已完成步骤显示摘要，减少视觉干扰
- 当前步骤高亮，锁定步骤有视觉提示（🔒）
- 右侧 AI 面板常驻，随时可获取帮助
- 毛玻璃背景（`backdrop-filter: blur`）提升现代感

#### 2.2 导航栏设计
- 固定顶部 + 毛玻璃效果，滚动时始终可见
- 当前页面高亮（`app-nav-bar__link--active`）
- 移动端自动切换为汉堡菜单 + 抽屉式导航
- 用户头像菜单设计简洁

#### 2.3 首页配置列表
- 工具栏（搜索、批量操作）与列表分离清晰
- 卡片式配置项，信息层次分明
- 分页组件位置合理

---

### ⚠️ 可以优化的地方

#### 2.4 向导步骤的视觉连接
**问题**：步骤之间缺少视觉连接线，用户难以感知"步骤 1 → 步骤 2"的流向。

**建议**：
```css
/* 在 WizardProgress 组件中添加步骤连接线 */
.wizard-progress__step {
  position: relative;
}
.wizard-progress__step:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 18px; /* 步骤圆点中心 */
  top: 36px; /* 圆点底部 */
  width: 2px;
  height: calc(100% + var(--space-section-gap));
  background: var(--color-border-light);
  transition: background var(--transition-normal);
}
.wizard-progress__step--completed:not(:last-child)::after {
  background: var(--color-primary-lighter);
}
```

#### 2.5 首页内容区最大宽度
**问题**：首页 `.home__configs` 没有最大宽度限制，超宽屏幕上配置列表会过度拉伸。

**建议**：
```css
.home__configs {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}
```

#### 2.6 向导页面左右分栏
**问题**：AI 面板宽度固定 `340px`，在小屏幕上（1024px）会挤压主内容区。

**建议**：
```css
/* 在 style.css 中添加 */
@media (max-width: 1100px) {
  .wizard__main {
    flex-direction: column;
  }
  .ai-panel {
    width: 100%;
    max-width: none;
    margin-top: 16px;
  }
}
```

---

## 3. 配色系统设计

### ✅ 做得好的地方

#### 3.1 设计 Token 体系
`style.css` 中定义了完整的 CSS 变量体系：

```css
/* 主色系：Teal */
--color-primary: #0f766e;        /* 深 Teal */
--color-primary-light: #14b8a6;  /* 亮 Teal */
--color-primary-lighter: #5eead4; /* 更亮 */

/* AI 辅助色：Purple */
--color-ai: #7c3aed;
--color-ai-light: #8b5cf6;

/* 语义色 */
--color-success: #059669;
--color-warning: #d97706;
--color-error: #dc2626;
--color-info: #0284c7;
```

**优点**：
- 主色（Teal #0f766e）传达"工具、可靠"的情感
- AI 辅助色（Purple）与主色形成二次色对比，区分度高
- 暗色模式 Token 完整，切换平滑

#### 3.2 暗色模式实现
```css
[data-theme="dark"] {
  --color-primary: #14b8a6;  /* 暗色下使用更亮的 Teal */
  --color-bg: #1c1917;        /* Stone 900 */
  --color-surface: #292524;     /* Stone 800 */
  /* ... */
}
```

**优点**：不仅反转颜色，而是重新设计暗色下的色彩关系，避免纯黑背景。

---

### ⚠️ 可以优化的地方

#### 3.3 色彩对比度未验证
**问题**：未看到 WCAG AA 对比度验证。以下组合需要检查：

| 前景 | 背景 | 需要验证 |
|------|------|----------|
| `--color-text: #292524` | `--color-surface: #ffffff` | ✅ 应该通过（14.5:1） |
| `--color-text-secondary: #78716c` | `--color-surface: #ffffff` | ⚠️ 需验证（约 4.8:1，刚好通过 AA） |
| `--color-primary: #0f766e` | `white` | ⚠️ 白色文字在主色背景上需验证（约 4.1:1，可能不通过） |

**建议**：使用 [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) 验证所有文本/背景组合，确保 AA 标准（4.5:1）。

#### 3.4 主色在白色背景上的可读性
**问题**：按钮 `.btn-primary` 使用渐变 `rgba(15,118,110,0.88)` 到 `rgba(20,184,166,0.85)`，文字为白色。在浅色背景下，按钮文字对比度可能不足。

**建议**：
```css
/* 验证按钮文字对比度，如不足则调整背景或文字色 */
.cf-btn--primary {
  /* 选项 1：加深背景 */
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  /* 选项 2：使用深色文字 */
  color: #ffffff;
  text-shadow: 0 1px 2px rgba(0,0,0,0.2); /* 增强可读性 */
}
```

#### 3.5 状态色彩的一致性
**问题**：在 `App.vue` 的 Naive UI 主题配置中，`common.primaryColor` 是 `#0d9488`，但 `style.css` 中定义的是 `#0f766e`。两处主色不一致！

**建议**：统一使用一个主色值，建议以 `style.css` 的 Token 为单一真相源：

```css
/* App.vue 中改为引用 CSS 变量 */
const lightThemeOverrides = {
  common: {
    primaryColor: 'var(--color-primary)',  /* 而不是硬编码 #0d9488 */
    primaryColorHover: 'var(--color-primary-light)',
    /* ... */
  },
}
```

---

## 4. 交互设计评估

### ✅ 做得好的地方

#### 4.1 微交互设计
```css
/* 按钮按压缩放 */
button:active:not([disabled]) {
  transform: scale(0.97);
}

/* 卡片悬停抬起 */
.card-lift:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-active);
}

/* AI 按钮霓虹脉冲 */
@keyframes ai-neon-pulse {
  0%, 100% { box-shadow: 0 0 0 0 var(--color-ai-glow); }
  50% { box-shadow: 0 0 0 5px rgba(139,92,246,0); }
}
```

**优点**：微交互增强了"可感知的可用性"，让用户感觉界面有响应。

#### 4.2 向导步骤完成反馈
- 完成步骤后显示 ✓ 徽章
- 折叠后显示摘要（如"3 个输入源"）
- 下一步按钮有脉冲动画提示（`pulse-cta`）

#### 4.3 表单验证反馈
```html
<p v-if="currentStep === 1 && !store.canProceed(1)" 
   class="wizard__validation-msg">
  {{ store.stepValidation(1).join('；') }}
</p>
```

**优点**：实时验证，错误提示紧跟在相关字段下方。

---

### ⚠️ 可以优化的地方

#### 4.4 Loading 状态不统一
**问题**：不同操作的 Loading 状态样式不一致：
- 登录按钮：使用旋转 spinner（`.login__spinner`）
- 保存配置：使用 Naive UI 的 `:loading="saving"` 属性
- AI 生成：可能没有明确的 Loading 提示

**建议**：统一使用 Naive UI 的 Loading 样式，或自定义统一的 Loading 组件：

```vue
<!-- components/common/LoadingOverlay.vue -->
<template>
  <Transition name="fade">
    <div v-if="visible" class="loading-overlay">
      <NSpin size="large" />
      <p class="loading-overlay__text">{{ text || '处理中...' }}</p>
    </div>
  </Transition>
</template>

<style scoped>
.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 10;
  border-radius: inherit;
}
[data-theme="dark"] .loading-overlay {
  background: rgba(41,37,36,0.8);
}
</style>
```

#### 4.5 操作成功反馈不够明显
**问题**：保存配置成功后，仅显示 `saveMsg` 文字，没有更明显的成功反馈。

**建议**：使用 Naive UI 的 `useMessage` 全局提示，或添加 Confetti 庆祝效果（已有 `ConfettiBurst.vue` 组件）：

```typescript
import { useMessage } from 'naive-ui'
const message = useMessage()

// 保存成功后
message.success('配置已保存')
// 或者触发 Confetti
confettiBurst()
```

#### 4.6 AI 生成结果的预览不足
**问题**：AI 生成 SQL/代码后，仅填入编辑器，没有显示"AI 生成结果 vs 原内容"的对比预览。

**建议**：添加 AI 建议面板，显示建议的变更：

```vue
<AiSuggestPanel
  :suggestion="aiSuggestion"
  :original="currentCode"
  @accept="applySuggestion"
  @reject="dismissSuggestion"
/>
```

---

## 5. 操作体验分析

### ✅ 做得好的地方

#### 5.1 向导流程清晰
5 步向导逻辑清晰：
1. 场景信息 → 2. 输入源 → 3. 处理步骤 → 4. 输出配置 → 5. 预览导出

每步都有：
- 标题 + 描述
- 表单验证
- 上一步/下一步导航
- 右侧 AI 帮助

#### 5.2 键盘快捷键
登录页支持 `Enter` 提交（通过 `@submit.prevent`）。

#### 5.3 撤回确认
删除配置前有确认弹窗，防止误操作。

---

### ⚠️ 可以优化的地方

#### 5.4 向导步骤无法直接跳转
**问题**：虽然已完成步骤可以折叠/展开，但用户可能无法快速跳转到任意步骤。

**当前行为**（从代码看）：
```typescript
function onStepHeaderClick(step: number) {
  if (props.status === 'completed') {
    emit('header-click')  // 只允许点击已完成步骤
  }
}
```

**建议**：允许点击任意**已完成或后续未锁定**的步骤进行跳转，提升操作灵活性。

#### 5.5 缺少操作进度保存提示
**问题**：用户在向导中填写了大量信息，如果意外关闭页面，可能会丢失进度。

**建议**：
1. 使用 `beforeunload` 事件提示用户：
```typescript
onMounted(() => {
  window.addEventListener('beforeunload', (e) => {
    if (store.hasUnsavedChanges) {
      e.preventDefault()
      e.returnValue = '你有未保存的更改，确定要离开吗？'
    }
  })
})
```

2. 定期自动保存到 `localStorage`，恢复时提示"是否恢复上次编辑"。

#### 5.6 批量操作的反馈不足
**问题**：批量删除配置后，仅显示消息提示，没有显示"已删除 X 个配置"的具体反馈。

**建议**：
```typescript
message.success(`已删除 ${selectedIds.size} 个配置`)
```

#### 5.7 缺少键盘快捷键
**问题**：向导操作只能使用鼠标点击，没有键盘快捷键。

**建议**：添加键盘快捷键支持：

```typescript
onMounted(() => {
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter: 下一步
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      completeStep(currentStep.value)
    }
    // Ctrl/Cmd + S: 保存
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault()
      saveConfig()
    }
  })
})
```

---

## 6. 组件设计细节

### ✅ 做得好的地方

#### 6.1 按钮设计
```css
.cf-btn--primary {
  background: linear-gradient(135deg, 
    rgba(15,118,110,0.88), 
    rgba(20,184,166,0.85));
  backdrop-filter: blur(8px);
  box-shadow: var(--shadow-button);
}
.cf-btn--primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px ..., 0 4px 20px ...;
}
```

**优点**：
- 毛玻璃效果 + 渐变背景，现代感强
- 悬停时轻微上浮 + 阴影增强，反馈明确
- 按压缩放 `scale(0.97)`，触感真实

#### 6.2 表单输入框
```css
.cf-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(15,118,110,0.08);
  background: var(--color-surface-input-focus);
}
```

**优点**：焦点状态清晰，阴影光晕效果优雅。

#### 6.3 向导步骤卡片
```css
.wizard-step-card--active {
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-active);
}
.wizard-step-card--completed {
  opacity: 0.85;  /* 完成的步骤降低不透明度 */
}
.wizard-step-card--locked {
  /* 锁定步骤有遮罩 + 提示 */
}
```

**优点**：步骤状态通过多种视觉手段（边框色、阴影、不透明度、遮罩）区分，清晰易懂。

---

### ⚠️ 可以优化的地方

#### 6.4 NButton 与 .cf-btn 混用
**问题**：代码中同时使用了 Naive UI 的 `<NButton>` 和自定义 `<button class="cf-btn">`，导致样式不一致。

**示例**（从代码中提取）：
```vue
<!-- 使用 NButton -->
<NButton type="primary" class="btn-primary" @click="save">保存</NButton>

<!-- 使用自定义按钮 -->
<button class="cf-btn cf-btn--primary" @click="execute">执行</button>
```

**建议**：统一使用一种按钮体系。如果 Naive UI 能满足需求，优先使用 `<NButton>`，并通过 `n-button` class 覆盖样式：

```css
/* 全局统一 NButton 样式 */
.n-button--primary-type {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light)) !important;
  border: none !important;
}
```

#### 6.5 图标使用不一致
**问题**：部分按钮使用 emoji 图标（如 📂、⚡），部分使用图标库，部分没有图标。

**建议**：统一使用图标库（如 [Iconify](https://iconify.design/) 或 [Naive UI Icons](https://www.naiveui.com/en-US/os-theme/icons)），提升专业感：

```vue
<script setup lang="ts">
import { Add as AddIcon, Download as DownloadIcon } from '@vicons/ionicons5'
</script>

<template>
  <NButton>
    <template #icon><AddIcon /></template>
    添加输入源
  </NButton>
</template>
```

#### 6.6 Toast 提示的位置和时长
**问题**：Naive UI 的 `useMessage` 默认在顶部居中显示，可能被导航栏遮挡。

**建议**：配置 Naive Message 的位置：

```typescript
// main.ts 或 App.vue
import { createDiscreteApi } from 'naive-ui'

const { message } = createDiscreteApi(['message'], {
  messageProviderProps: {
    placement: 'top-right',  /* 右上角，不遮挡导航栏 */
    duration: 3000,           /* 3秒后自动消失 */
    max: 3,                   /* 最多同时显示 3 条 */
  },
})
```

---

## 7. 响应式设计

### ✅ 做得好的地方

#### 7.1 移动端适配
```css
/* style.css */
@media (max-width: 767px) {
  .cf-form-grid {
    grid-template-columns: 1fr;  /* 表单改为单列 */
  }
  button:not([disabled]),
  a:not([disabled]),
  [role="button"] {
    min-height: 44px;  /* 触摸目标最小 44px */
  }
}
```

**优点**：
- 触摸目标符合 WCAG 标准（44x44px）
- 表单在移动端自动改为单列
- 导航栏切换为汉堡菜单

#### 7.2 断点设计
```css
--breakpoint-mobile: 768px;
--breakpoint-tablet: 1024px;
```

**优点**：使用标准断点（Bootstrap 风格），覆盖主流设备。

---

### ⚠️ 可以优化的地方

#### 7.3 平板端（768px - 1023px）的布局优化不足
**问题**：在 768px - 1023px 之间，向导页面可能过于拥挤。

**建议**：为平板端添加专门的布局调整：

```css
@media (min-width: 768px) and (max-width: 1023px) {
  .wizard__main {
    flex-direction: column;
  }
  .ai-panel {
    width: 100%;
    margin-top: 16px;
  }
  .wizard-step-card {
    padding: 12px;  /* 减少内边距 */
  }
}
```

#### 7.4 表格在移动端的显示
**问题**：执行历史页面的表格在移动端可能横向溢出。

**建议**：表格添加水平滚动或改为卡片式布局：

```css
/* 移动端表格改为卡片式 */
@media (max-width: 767px) {
  .execution-table table {
    display: none;  /* 隐藏表格 */
  }
  .execution-cards {
    display: block;  /* 显示卡片 */
  }
}
```

---

## 8. 无障碍访问

### ✅ 做得好的地方

#### 8.1 基础支持
```css
*:focus-visible {
  outline: 2px solid var(--color-primary-lighter);
  outline-offset: 2px;
}
```

```html
<button :aria-label="t('nav.toggleDark')" ...>
```

**优点**：
- `focus-visible` 样式清晰
- 部分按钮有 `aria-label`
- 支持 `prefers-reduced-motion`

---

### ⚠️ 可以优化的地方

#### 8.2 对比度未验证
**问题**：如前所述，多个文本/背景组合可能未通过 WCAG AA 标准。

**行动**：使用自动化工具（如 [axe DevTools](https://www.deque.com/axe/)）扫描对比度问题。

#### 8.3 ARIA 标签不完整
**问题**：部分交互元素缺少 `aria-label` 或 `aria-describedby`。

**示例**：
```vue
<!-- 缺少 aria-label -->
<NButton @click="deleteConfig">
  <template #icon><TrashIcon /></template>
</NButton>

<!-- 应改为 -->
<NButton @click="deleteConfig" aria-label="删除配置">
  <template #icon><TrashIcon /></template>
</NButton>
```

#### 8.4 表单标签关联不完整
**问题**：部分输入框与 `<label>` 的 `for` 属性未正确关联。

**建议**：
```vue
<label for="scene-name" class="cf-label">场景名称</label>
<NInput id="scene-name" v-model:value="store.scene.name" />

<!-- 或者 -->
<NFormItem :label="t('wizard.sceneName')" required>
  <NInput v-model:value="store.scene.name" />
</NFormItem>
```

#### 8.5 错误信息未关联
**问题**：表单验证错误信息通过 `v-if` 显示，但未使用 `aria-describedby` 关联到输入框。

**建议**：
```vue
<NInput
  v-model:value="store.scene.name"
  :aria-describedby="validationError ? 'scene-name-error' : undefined"
  :aria-invalid="!!validationError"
/>
<p v-if="validationError" id="scene-name-error" role="alert" class="wizard__validation-msg">
  {{ validationError }}
</p>
```

#### 8.6 键盘导航顺序
**问题**：向导步骤之间的 Tab 顺序可能不符合逻辑。

**建议**：使用 `tabindex` 明确指定 Tab 顺序，或使用 `teleport` 将焦点管理逻辑集中处理。

---

## 9. 问题清单与优化建议

### 🔴 P0 - 必须修复（影响可用性）

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 1 | 主色值不一致（`App.vue` #0d9488 vs `style.css` #0f766e） | 品牌色不统一 | 统一使用 `style.css` 的 CSS 变量 |
| 2 | 按钮体系混用（NButton + .cf-btn） | 样式不一致 | 统一使用 NButton 并覆盖样式 |
| 3 | 对比度未验证 | 可能未通过 WCAG AA | 使用 axe DevTools 扫描并修复 |

### 🟡 P1 - 强烈建议（明显提升体验）

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 4 | 向导步骤之间缺少视觉连接线 | 步骤关系不够直观 | 添加步骤连接线 |
| 5 | Loading 状态不统一 | 用户反馈不一致 | 创建统一的 Loading 组件 |
| 6 | 操作成功反馈不够明显 | 用户不确定是否成功 | 使用 Toast + Confetti |
| 7 | 缺少键盘快捷键 | 高级用户效率低 | 添加 Ctrl+Enter、Ctrl+S 等 |
| 8 | ARIA 标签不完整 | 屏幕阅读器用户无法使用 | 补充 aria-label、aria-describedby |

### 🟢 P2 - 建议优化（锦上添花）

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 9 | 平板端布局优化不足 | 平板用户体验一般 | 添加 768-1023px 专用样式 |
| 10 | 图标使用不一致 | 视觉风格不统一 | 统一使用图标库 |
| 11 | 表格在移动端可能溢出 | 移动端体验差 | 添加水平滚动或卡片布局 |
| 12 | 向导无法直接跳转步骤 | 操作不够灵活 | 允许跳转到已完成步骤 |
| 13 | 缺少进度自动保存 | 意外关闭可能丢失数据 | 定期保存到 localStorage |

---

## 10. 优先级行动清单

### 第一周（P0 修复）
- [ ] **统一主色值**：将 `App.vue` 中的硬编码颜色改为引用 `style.css` 的 CSS 变量
- [ ] **统一按钮体系**：决定使用 NButton 或 .cf-btn，全局替换
- [ ] **对比度验证**：使用 axe DevTools 扫描，修复不通过的组合

### 第二周（P1 优化）
- [ ] **添加步骤连接线**：在 `WizardProgress` 组件中实现
- [ ] **统一 Loading 状态**：创建 `LoadingOverlay.vue` 组件
- [ ] **增强操作反馈**：保存/删除成功后显示 Confetti 或 Toast
- [ ] **添加键盘快捷键**：向导页面支持 Ctrl+Enter、Ctrl+S
- [ ] **补充 ARIA 标签**：为所有交互元素添加 aria-label

### 第三周（P2 优化）
- [ ] **平板端布局优化**：添加 768-1023px 媒体查询
- [ ] **统一图标体系**：引入 @vicons/ionicons5，替换 emoji
- [ ] **移动端表格优化**：执行历史页面添加卡片式布局
- [ ] **向导步骤跳转**：允许跳转到已完成步骤
- [ ] **自动保存进度**：使用 localStorage 定期保存向导状态

---

## 附录：设计系统改进建议

### A. 补充缺失的设计 Token

```css
/* style.css */

/* === Animation Duration === */
--duration-instant: 0ms;
--duration-fast: 150ms;
--duration-normal: 250ms;
--duration-slow: 400ms;

/* === Z-Index Scale === */
--z-dropdown: 100;
--z-sticky: 200;
--z-modal: 300;
--z-toast: 400;
--z-tooltip: 500;

/* === Border Width === */
--border-width-thin: 1px;
--border-width-normal: 1.5px;
--border-width-thick: 2px;

/* === Opacity Levels === */
--opacity-disabled: 0.4;
--opacity-hover: 0.8;
--opacity-active: 0.6;
--opacity-subtle: 0.1;
```

### B. 创建组件使用文档

建议为每个组件创建使用示例：

```markdown
# Button 组件使用指南

## 主要按钮
<NButton type="primary" @click="handleClick">
  保存配置
</NButton>

## 次要按钮
<NButton @click="handleClick">
  取消
</NButton>

## 危险按钮
<NButton type="error" @click="handleDelete">
  删除
</NButton>

## 加载状态
<NButton :loading="saving" @click="save">
  保存
</NButton>
```

---

**报告结束**

> 这份报告基于 2026-06-28 的代码快照。建议定期（每季度）进行 UI/UX 审查，确保设计质量持续提升。
