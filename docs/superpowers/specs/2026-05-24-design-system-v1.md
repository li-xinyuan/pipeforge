# ConfigForge 设计系统 v1.0

> 日期: 2026-05-24（审查修订）
> 基于: UI UX Pro Max 技能推荐 + 脑爆确认 + 审查反馈
> 当前基线: v0.3.1
> 审查结论: 保持 Teal 主色，聚焦高价值低风险改动

---

## 一、配色体系

**保持现有 Teal 主色不变。** 审查指出换色解决不了核心 UX 问题，且 Teal 已有用户认知。

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-primary` | `#0d9488`（保持不变） | 主按钮、链接、选中态 |
| `--color-primary-light` | `#14b8a6`（保持不变） | 悬停态、聚焦环 |
| `--color-primary-lighter` | `#5eead4`（保持不变） | 浅色边框 |
| `--color-primary-bg` | `#f0fdfa`（保持不变） | 选中背景、标签底 |
| `--color-accent` | `#f59e0b` | CTA 强调色（与 warning 分离） |
| `--color-warning` | `#f97316` | 警告色（独立，不与 accent 混淆） |
| `--color-success` | `#10b981`（保持不变） | 成功、完成态 |
| `--color-error` | `#ef4444`（保持不变） | 错误、删除、危险操作 |

暗色模式对应值在 CSS 变量 `[data-theme="dark"]` 中定义。

---

## 二、字体体系

审查指出应采用 "Inter", "Noto Sans SC" 双字体栈。Inter 优先渲染拉丁字符，Noto Sans SC 渲染中文。

| Token | 字体 | 用途 |
|-------|------|------|
| UI 文字 | `"Inter", "Noto Sans SC", system-ui, -apple-system, sans-serif` | 全局 UI |
| 代码 | `"JetBrains Mono", monospace` | SQL 编辑器、YAML 预览、代码块 |

字号层级（4px 递增）：

| Token | 字号 | 行高 | 用途 |
|-------|------|------|------|
| `text-xs` | 12px | 1.5 | 标签、占位符、辅助文字 |
| `text-sm` | 14px | 1.5 | 正文、输入框、按钮 |
| `text-base` | 16px | 1.6 | 卡片标题 |
| `text-lg` | 18px | 1.4 | 步骤标题 |
| `text-xl` | 20px | 1.3 | 页面标题 |

---

## 三、间距与圆角

**4px 基准间距**：4 / 8 / 12 / 16 / 20 / 24 / 32

**圆角 Token**：

| Token | 值 | 用途 |
|-------|-----|------|
| `sm` | 4px | 输入框、标签、小按钮 |
| `md` | 8px | 按钮、卡片 |
| `lg` | 12px | 大卡片、面板 |
| `xl` | 16px | 模态框 |
| `full` | 9999px | 头像、徽章 |

---

## 四、图标迁移

- **图标库**：Lucide Icons (`lucide-vue-next`)
- **渲染方式**：Naive UI `<NIcon>` 组件包裹
- **迁移范围**：约 15 处 Emoji → Lucide SVG

---

## 五、按钮统一

### 主按钮
- 移除自定义 `btn-primary` CSS 类
- 统一使用 Naive UI `<NButton type="primary">`
- Naive UI 主题覆盖 `--color-primary` 确保按钮颜色一致

### 次级按钮
- 新增统一的 `btn-secondary` 方案：`<NButton>` 默认样式（无 type 或 type="default"）
- 不需要自定义 CSS 类

### 危险按钮
- `<NButton type="error">` 替代

---

## 六、Naive UI 主题覆盖

CSS 变量只能控制自定义样式。Naive UI 组件内部颜色需通过 `NConfigProvider` 的 `themeOverrides` 覆盖，尤其是：

```typescript
const themeOverrides = {
  common: {
    primaryColor: '#0d9488',
    primaryColorHover: '#14b8a6',
  },
  Button: {
    colorPrimary: '#0d9488',
    colorHoverPrimary: '#14b8a6',
  },
}
```

在 `App.vue` 中包裹 `<NConfigProvider :theme-overrides="themeOverrides">`。

---

## 七、改动文件清单（审查补全后）

| 文件 | 改动 |
|------|------|
| `configforge-web/index.html` | Google Fonts link（Inter + Noto Sans SC + JetBrains Mono） |
| `configforge-web/src/style.css` | CSS 变量调整（accent/warning 分离、字体栈、间距圆角 Token） |
| `configforge-web/src/App.vue` | 新增 `NConfigProvider` + `themeOverrides` |
| `configforge-web/src/views/ConfigWizardView.vue` | btn-primary → NButton type=primary，emoji → Lucide |
| `configforge-web/src/views/HomeView.vue` | emoji → Lucide |
| `configforge-web/src/views/SettingsPage.vue` | emoji → Lucide |
| `configforge-web/src/components/step2/InputSourceCard.vue` | emoji → Lucide |
| `configforge-web/src/components/step2/InputSourceList.vue` | emoji → Lucide |
| `configforge-web/src/components/step3/ProcessorCard.vue` | emoji → Lucide |
| `configforge-web/src/components/step3/SqlEditorTab.vue` | emoji → Lucide |
| `configforge-web/src/components/step3/OutputConfigTab.vue` | emoji → Lucide（审查补） |
| `configforge-web/src/components/step4/ExportActions.vue` | emoji → Lucide（审查补） |
| `configforge-web/src/components/step4/YamlPreview.vue` | emoji → Lucide（审查补） |
| `configforge-web/src/components/wizard/WizardStepCard.vue` | emoji → Lucide |
| `configforge-web/src/components/wizard/WizardProgress.vue` | emoji → Lucide（审查补） |
| `configforge-web/src/components/wizard/AiChatPanel.vue` | emoji → Lucide |
| `configforge-web/src/components/wizard/AiInlineTip.vue` | emoji → Lucide（审查补） |

---

## 八、非目标

- 配色大改（保持 Teal）
- 暗色模式完全重构
- 移动端适配
- 组件库替换（保持 Naive UI）
- 步骤堆叠/折叠架构改动

---

## 九、验证策略

- 视觉回归：图标/按钮/间距在亮色+暗色模式下对比
- 图标替换：每个 Lucide 语义正确
- 按钮统一：`btn-primary` 全局搜索 0 残留
- Naive UI 覆盖：`themeOverrides` 生效确认
- 自动化：113 frontend tests + vue-tsc 0 errors 不变
