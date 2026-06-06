# ConfigForge 前端 UX 优化清单

> 日期：2026-06-06
> 视角：第一次使用、不熟悉系统的用户
> 维度：易用性、人机工程、风格统一性、一致性

---

## P0 — 必须修复（暗色模式不可用 / 严重不一致）

| # | 问题 | 位置 | 优化建议 |
|---|------|------|---------|
| 1 | 锁屏遮罩硬编码白色，暗色模式视觉错误 | `WizardStepCard.vue:86` | 改为 `background: var(--color-surface); opacity: 0.6` |
| 2 | WizardProgress 背景硬编码白色 | `WizardProgress.vue:55` | 改为 `background: var(--color-surface)` |
| 3 | OrchestrationResult 硬编码 Tailwind 颜色，暗色模式不适配 | `OrchestrationResult.vue:2-12` | 替换为 CSS 变量 |
| 4 | PipelineAnimation 大量硬编码颜色 | `PipelineAnimation.vue` 多处 | 替换为 CSS 变量 |
| 5 | ConnectionManager 硬编码 Tailwind 颜色，暗色模式不适配 | `ConnectionManager.vue:4,11,15,19,29,53` | 替换为 CSS 变量 |
| 6 | 代码编辑器 textarea 硬编码暗色内联样式 | `SqlProcessorContent.vue:63`, `PythonProcessorContent.vue:52` | 提取为 CSS class，适配暗色主题 |
| 7 | 品牌图标跨页不一致（首页 ⚡ vs 向导 ⚙️） | `HomeView.vue:7` vs `ConfigWizardView.vue:7` | 统一为 ⚡ |

## P1 — 强烈建议（影响新用户可用性 / 视觉一致性）

### 导航与页面框架

| # | 问题 | 位置 | 优化建议 |
|---|------|------|---------|
| 8 | 导航栏样式跨页不统一（高度54/56px、透明度0.72/0.78、边框色不同） | `HomeView.vue` vs `ConfigWizardView.vue` | 提取为共享组件，统一高度56px、透明度0.78 |
| 9 | 导航链接文案不一致（"首页"vs"我的配置"、"AI 模型设置"vs"设置"） | 多处 | 统一为"我的配置"+"AI 设置" |
| 10 | 主题切换按钮样式跨页不一致（尺寸36/30px、圆角8px/var） | `HomeView.vue` vs `ConfigWizardView.vue` | 提取为共享组件 |
| 11 | 主题切换图标不一致（☀/☾ 文字字符 vs ☀️/🌙 emoji） | 同上 | 统一使用 SVG 图标 |
| 12 | 向导页品牌区域不可点击返回首页 | `ConfigWizardView.vue:6-9` | 添加 `@click="router.push('/')"` |
| 13 | 编辑已有配置时 badge 仍显示"新配置" | `ConfigWizardView.vue:9` | 根据 `route.query.load` 动态切换 |
| 14 | 移动端导航链接完全隐藏 | `HomeView.vue:558-559` | 添加汉堡菜单或底部导航 |
| 15 | 设置页导航缺少"向导"入口 | `SettingsPage.vue:10-13` | 添加"我的配置"链接 |

### 表单与输入

| # | 问题 | 位置 | 优化建议 |
|---|------|------|---------|
| 16 | 表单标签样式严重不一致（text-xs slate-500 vs text-sm slate-900） | Step 2/3/4 多处 | 统一为 `text-xs font-medium text-slate-500 mb-1` |
| 17 | 必填字段标记缺失（表名、数据库连接等） | `InputSourceCard.vue:148`, `DatabaseForm.vue` | 统一添加红色星号 |
| 18 | 输入框 size 不一致（small vs medium） | Step 2/3/4 多处 | 统一为 `size="small"` |
| 19 | "保存并继续"文案误导（实际未保存到服务器） | `ConfigWizardView.vue:76` | 改为"下一步" |
| 20 | 版本号字段无默认值 | `ConfigWizardView.vue:58` | 设置默认值 "1.0" |
| 21 | 非必填字段未标注"(可选)" | `ConfigWizardView.vue:53-68` | 在版本号、描述旁加"(可选)" |

### 卡片与类型选择器

| # | 问题 | 位置 | 优化建议 |
|---|------|------|---------|
| 22 | 子卡片 body padding 不一致（p-3 gap-3 mb-4 / p-3 space-y-3 / p-3 space-y-4） | Step 2/3/4 子卡片 | 统一为 `p-3 space-y-3` |
| 23 | 子卡片间距不一致（16px vs 8px） | `InputSourceList.vue:2` vs `ProcessorCard.vue:70` | 统一为 `space-y-3`（12px） |
| 24 | 类型选择卡片选中态颜色无统一映射 | Step 2/3/4 | 建立品牌色映射：CSV=蓝、Excel=绿、DB=紫、SQL=蓝、Python=橙 |
| 25 | Step card 激活时边框宽度变化导致布局抖动 | `WizardStepCard.vue:60 vs 66` | 默认态也用2px边框（透明色） |
| 26 | CheckpointSection 使用 scoped CSS 而其他组件用 Tailwind | `CheckpointSection.vue:157-210` | 统一为 Tailwind |

### 术语一致性

| # | 问题 | 位置 | 优化建议 |
|---|------|------|---------|
| 27 | "输入源"vs"数据源"vs"可用表"vs"输入表"混用 | Step 2/3/4 多处 | 统一：Step 2/4 用"输入源"，Step 3 用"输入表" |
| 28 | "处理步骤"vs"处理器"vs"步骤"混用 | Step 3 多处 | 用户可见文案统一为"处理步骤" |
| 29 | "列映射"vs"映射"vs"推断列"混用 | Step 4 多处 | 统一为"列映射" |

### 操作反馈

| # | 问题 | 位置 | 优化建议 |
|---|------|------|---------|
| 30 | 错误提示样式不统一（mt-1/mb-2/无margin，纯文字/提示框混用） | Step 2/3/4 多处 | 统一为 `text-xs text-red-500 mt-1` |
| 31 | AI 错误展示方式不一致（红框/带图标/琥珀框） | Step 2 多处 | 统一为一种错误提示组件 |
| 32 | 加载指示器不统一（NSpin+遮罩/emoji⏳/NSkeleton/按钮loading） | 全局 | 局部→按钮loading，全区域→遮罩+NSpin，内容→NSkeleton |
| 33 | ConnectionManager 删除无确认弹窗 | `ConnectionManager.vue:24` | 添加确认弹窗 |
| 34 | 测试连接隐式保存设置 | `SettingsPage.vue:158` | 改为"保存并测试"或添加提示 |
| 35 | AI 设置测试结果用行内文本而非 Toast | `SettingsPage.vue:80-83` | 统一使用 `useMessage()` Toast |

### 空状态与引导

| # | 问题 | 位置 | 优化建议 |
|---|------|------|---------|
| 36 | Step 2/4 空状态缺少引导文字 | `InputSourceList.vue`, `OutputConfigTab.vue` | 添加引导文字 |
| 37 | 首页无配置时"最近配置"区域完全隐藏 | `HomeView.vue:54` | 始终显示，空状态加引导 |
| 38 | ConnectionManager 空状态过于简陋 | `ConnectionManager.vue:11-13` | 添加图标+引导文案+操作按钮 |
| 39 | Step 1 AI 提示仅在输入后才出现 | `ConfigWizardView.vue:71-74` | 始终显示轻量提示 |

## P2 — 建议优化（提升专业感和细节体验）

| # | 问题 | 位置 | 优化建议 |
|---|------|------|---------|
| 40 | 圆角值未使用设计令牌（硬编码12px） | `HomeView.vue:437,621` | 使用 `var(--radius-md)` 或 `var(--radius-lg)` |
| 41 | btn-primary 在两页面重复定义且略有差异 | `HomeView.vue:499` vs `ConfigWizardView.vue:948` | 提取到全局 `style.css` |
| 42 | AI 开关使用自定义实现而非 NSwitch | `ConfigWizardView.vue:17-23` | 替换为 `<NSwitch />` |
| 43 | Step 5 缺少配置摘要 | `ConfigWizardView.vue:163-183` | 添加摘要卡片（输入源×N、步骤×N、输出格式） |
| 44 | OutputConfigTab "删除"按钮语义应为"重置/更换类型" | `OutputConfigTab.vue:49` | 改为"更换类型" |
| 45 | Step 5 ExportActions 按钮缺少主次区分 | `ExportActions.vue:3-8` | 仅"下载结果文件"用 primary，其余默认 |
| 46 | ColumnPreview 分页器用原生 button 而非 NButton | `ColumnPreview.vue:23-24` | 替换为 `<NButton size="tiny">` |
| 47 | ColumnMapping 源列可编辑但无视觉提示 | `ColumnMapping.vue:13-14` | 添加 hover 效果和编辑图标 |
| 48 | OutputConfigTab 输出文件名编辑交互过于复杂 | `OutputConfigTab.vue:112-133` | 简化为输入框+插入标签下拉 |
| 49 | Step 4 已有输出配置时仍显示类型选择器 | `OutputConfigTab.vue:212` | `ref(!store.output?.plugin)` |
| 50 | InputSourceCard 自动弹出文件选择器可能困惑 | `InputSourceCard.vue:265-276` | 移除自动弹出，改为用户主动点击 |
| 51 | Hero 副标题术语"流水线配置"对新手不友好 | `HomeView.vue:30-32` | 改为更通俗表述 |
| 52 | Step 1 验证消息位置远离输入框 | `ConfigWizardView.vue:77` | 移至输入框正下方 |
| 53 | 锁屏遮罩与 badge 信息冗余（双锁图标） | `WizardStepCard.vue:33-36` | badge 去掉 emoji，仅保留文字 |
| 54 | pulse-cta 动画过于激进 | `style.css:243-264` | 去掉 scale，仅保留微弱 shadow 脉冲 |
| 55 | 配置名称按钮交互模式混乱（NButton text 渲染为链接样式） | `HomeView.vue:71` | 改为 `<router-link>` |
| 56 | 菜单按钮(···)点击区域过小 | `HomeView.vue:86` | 增大至 44×44px |
| 57 | 设置页表单间距与 ConnectionManager 不一致（14px vs 8px） | `SettingsPage.vue:320` vs `ConnectionManager.vue:29` | 统一为 14px |
| 58 | ConnectionManager 表单字段无 label 仅靠 placeholder | `ConnectionManager.vue:31-43` | 添加 `<label>` 元素 |
| 59 | 连接列表信息过于简略（缺少主机/端口/库名） | `ConnectionManager.vue:15-25` | 显示 `MySQL · localhost:3306 · mydb` |
| 60 | 连接验证状态仅用文字无图标 | `ConnectionManager.vue:19` | 已验证→绿色勾号，未验证→橙色警告 |
| 61 | 连接列表项无 hover 效果 | `ConnectionManager.vue:15` | 添加 hover 边框色变化 |
| 62 | AI 面板气泡文字暗色模式对比度不足 | `AiChatPanel.vue:233` | 暗色模式改为 `var(--color-text)` |
| 63 | AiColumnAnalysisModal 和 AiColumnConfirmModal 功能重叠 | 两个弹窗组件 | 统一为一个弹窗 |
| 64 | 类型选择卡片外层多余 `<span>` 包裹 | `InputSourceList.vue:21,28,35` | 移除，直接使用内部 div |
| 65 | InputSourceCard AI 分析遮罩有重复 div | `InputSourceCard.vue:201-205` | 合并为一个遮罩 div |
| 66 | Step 3 验证消息用 NAlert 而其他步骤用纯文字 | `SqlEditorTab.vue:85-89` | 统一为 `wizard__validation-msg` |
| 67 | 首页 Hero 渐变与向导页背景渐变不一致 | `HomeView.vue:312` vs `ConfigWizardView.vue:863` | 统一渐变方案 |
| 68 | 设置页导航栏边框色与向导页不同 | `SettingsPage.vue:200` | 统一使用 `var(--color-primary-border)` |
| 69 | 设置页导航栏高度/模糊度与向导页不同 | `SettingsPage.vue:211,199` | 统一为 56px、blur(14px) |
| 70 | Temperature 滑块值嵌入 label 文本会跳动 | `SettingsPage.vue:63` | 数值单独显示在右侧 |
| 71 | 设置页初始加载无 Loading 状态 | `SettingsPage.vue:141-152` | 添加 loading/骨架屏 |
| 72 | AI 设置首次访问无引导说明 | `SettingsPage.vue` 整体 | 添加简要说明 |

---

## 统计

| 优先级 | 数量 | 核心主题 |
|--------|------|---------|
| **P0** | 7 | 暗色模式不可用、品牌不一致 |
| **P1** | 32 | 导航统一、表单一致性、术语统一、操作反馈、空状态引导 |
| **P2** | 33 | 细节体验、专业感提升 |
| **合计** | **72** | |

## 建议优化顺序

1. **第一批：暗色模式适配**（P0 #1-6）— 修复所有硬编码颜色
2. **第二批：导航框架统一**（P1 #8-15）— 提取共享导航组件
3. **第三批：表单一致性**（P1 #16-21）— 统一标签/尺寸/必填标记
4. **第四批：卡片与类型选择器**（P1 #22-26）— 统一间距/颜色映射
5. **第五批：术语与反馈**（P1 #27-35）— 统一术语/错误提示/加载状态
6. **第六批：空状态与引导**（P1 #36-39）— 补全引导文字
7. **第七批：P2 细节优化** — 逐步打磨
