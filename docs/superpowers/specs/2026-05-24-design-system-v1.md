# ConfigForge 设计系统 v1.0

> 日期: 2026-05-24
> 基于: UI UX Pro Max 技能推荐 + 脑爆确认
> 当前基线: v0.3.1

---

## 一、配色体系

| Token | 值 | 用途 |
|-------|-----|------|
| `--color-primary` | `#1e40af` | 主按钮、链接、选中态 |
| `--color-primary-light` | `#3b82f6` | 悬停态、聚焦环 |
| `--color-primary-lighter` | `#60a5fa` | 浅色边框 |
| `--color-primary-bg` | `#eff6ff` | 选中背景、标签底 |
| `--color-accent` | `#f59e0b` | CTA 强调色 |
| `--color-success` | `#10b981` | 成功、完成态 |
| `--color-error` | `#ef4444` | 错误、删除、危险操作 |
| `--color-warning` | `#f59e0b` | 警告（复用 accent） |

暗色模式对应值在 CSS 变量 `[data-theme="dark"]` 中定义。

---

## 二、字体体系

| Token | 字体 | 用途 |
|-------|------|------|
| UI 文字 | **Noto Sans SC** (思源黑体) | 全局 UI：按钮、标签、正文、标题 |
| 代码 | **JetBrains Mono** | SQL 编辑器、YAML 预览、代码块 |
| 回退 | `system-ui, -apple-system, sans-serif` | 字体加载失败时 |

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

**4px 基准间距**：4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48

**圆角 Token**：

| Token | 值 | 用途 |
|-------|-----|------|
| `sm` | 4px | 输入框、标签、小按钮 |
| `md` | 8px | 按钮、卡片 |
| `lg` | 12px | 大卡片、面板 |
| `xl` | 16px | 模态框 |
| `full` | 9999px | 头像、徽章 |

---

## 四、图标

- **图标库**：Lucide Icons (`lucide-vue-next`)
- **渲染方式**：Naive UI `<NIcon>` 组件包裹
- **迁移范围**：全部 Emoji → Lucide SVG（约 15 处）

---

## 五、按钮统一

- 移除自定义 `btn-primary` CSS 类
- 统一使用 Naive UI `<NButton>` + `type` 属性
- `type="primary"` 替代 `class="btn-primary"`
- 所有操作按钮使用一致的 `size` prop

---

## 六、改动文件清单

| 文件 | 改动 |
|------|------|
| `configforge-web/index.html` | 添加 Google Fonts link |
| `configforge-web/src/style.css` | CSS 变量重定义（配色/字体/间距/圆角） |
| `configforge-web/src/views/ConfigWizardView.vue` | btn-primary → NButton type=primary，emoji → Lucide |
| `configforge-web/src/components/step2/InputSourceCard.vue` | emoji 图标 → Lucide |
| `configforge-web/src/components/step2/InputSourceList.vue` | emoji 图标 → Lucide |
| `configforge-web/src/components/step3/ProcessorCard.vue` | emoji → Lucide |
| `configforge-web/src/components/step3/SqlEditorTab.vue` | emoji → Lucide |
| `configforge-web/src/components/wizard/WizardStepCard.vue` | emoji → Lucide |
| `configforge-web/src/components/wizard/AiChatPanel.vue` | emoji → Lucide |
| `configforge-web/src/views/HomeView.vue` | emoji → Lucide |
| `configforge-web/src/views/SettingsPage.vue` | emoji → Lucide |

---

## 七、非目标

- 暗色模式完全重构（当前 CSS 变量体系满足需求，仅调整色值）
- 移动端适配（非 v1.0 范围）
- 组件库替换（保持 Naive UI）
- 无障碍完整合规（后续版本）

---

## 八、验证策略

- 视觉回归：配色/字体/间距在亮色和暗色模式下手动对比
- 图标替换：每个 Lucide 图标确认语义正确
- 按钮统一：全局搜索 `btn-primary` 确认 0 残留
- 自动化测试：现有 113 frontend tests + vue-tsc 0 errors 不变
