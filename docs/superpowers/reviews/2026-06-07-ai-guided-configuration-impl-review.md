# AI 引导式配置实现计划 — 审查报告

> 审查日期：2026-06-07
> 审查对象：`docs/superpowers/plans/2026-06-07-ai-guided-configuration-impl.md`
> 审查结论：**计划整体方向正确，但存在 6 个 Bug 级问题 + 5 个设计问题 + 4 个遗漏项，需修正后方可开发**

---

## 一、总体评价

| 维度 | 评价 | 说明 |
|------|------|------|
| 任务拆分 | ✅ 合理 | 13 个 Task 逐步递进，依赖关系清晰 |
| 测试覆盖 | ✅ 良好 | 新增 composable 都有 TDD 流程 |
| 提交粒度 | ✅ 合理 | 每个 Task 独立提交，便于回滚 |
| 代码假设 | ❌ 多处与实际不符 | 6 个 Bug 级问题源于未验证现有代码 |
| 与现有功能兼容 | ⚠️ 部分冲突 | 编排模式、现有 AI 交互未考虑 |
| 设计规格覆盖 | ⚠️ 部分遗漏 | 4 项设计规格内容未在计划中体现 |

---

## 二、Bug 级问题（必须修正）

### Bug 1：`useAiStatus` 已经是模块级单例，改写理由错误

**计划 Task 2 说**："useAiStatus 当前每次调用创建独立 aiConfigured ref"

**实际代码**（[useAiStatus.ts](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/composables/useAiStatus.ts)）：

```typescript
const aiConfigured = ref(false)  // ← 模块级，所有调用者共享
export function useAiStatus() { ... }
```

`aiConfigured` 已经是模块级 `ref`，所有组件调用 `useAiStatus()` 共享同一个状态。计划中的改写理由不成立。

**但 `Ref<boolean | null>` 改进本身是合理的**——当前 `ref(false)` 无法区分"未检测"和"检测后确认不可用"。建议保留 `null` 状态改进，但修正 Task 2 的描述。

---

### Bug 2：`ChatMessage` 接口位置错误

**计划 Task 1 说**："在 wizard.ts 中 ChatMessage 接口（约第 225 行）追加字段"

**实际代码**（[wizard.ts](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/types/wizard.ts#L34-L39)）：

```typescript
// 第 34-39 行
export interface ChatMessage {
  role: 'user' | 'ai'
  content: string
  code?: string
  orchestration?: OrchestrationResult
}
```

ChatMessage 在第 34 行，不是第 225 行。第 225 行附近是 `CheckRule` 相关类型。计划中的行号会误导开发者。

另外，计划新增字段时**遗漏了现有 `code` 字段**，且新增的 `prefill` 字段与现有 `orchestration` 字段可能冲突（两者都是 AI 返回的结构化数据）。

---

### Bug 3：`useAiGuide` 直接调用 `fetch`，绕过现有 `useAiApi`

**计划 Task 5 的 `callSuggest` 方法**：

```typescript
async function callSuggest(category: string, context: string): Promise<string | null> {
  const resp = await fetch('/api/ai/suggest', { ... })
}
```

**问题**：项目已有 `useAiApi` composable 封装了 `/api/ai/suggest` 调用，包含：
- 速率限制处理
- 错误清洗
- 超时控制
- AbortController 支持

直接用 `fetch` 绕过了所有这些基础设施，会导致：
1. 速率限制失效（用户快速操作时可能被后端 429）
2. 错误信息未清洗（可能泄露 API key）
3. 无超时控制（请求可能挂起 90 秒）
4. 无法取消请求（设计规格要求 30 秒后可取消）

**建议**：`useAiGuide` 内部应调用 `useAiApi` 的 `askSuggestion` 方法，而非直接 `fetch`。

---

### Bug 4：`extractSelectColumns` 正则语法错误

**计划 Task 10 的代码**：

```typescript
const parts = col.trim().split(/\s+(?i)AS\s+/)
```

JavaScript 正则不支持内联 `(?i)` 标志。这行代码会抛出 `SyntaxError`。

**修正**：

```typescript
const parts = col.trim().split(/\s+AS\s+/i)
```

---

### Bug 5：`ConfigWizardView` 中 `currentStep` 双重定义

**计划 Task 8 新增**：

```typescript
const currentStep = ref(1)
```

**现有代码**（[ConfigWizardView.vue](file:///Users/lixinyuan/code/CCTEST/configforge-web/src/views/ConfigWizardView.vue#L209)）：

```typescript
const currentStep = ref(1)  // 已存在
```

计划新增的 `currentStep` 与现有的重复，会导致 `vue-tsc` 报错或运行时行为不可预测。

---

### Bug 6：`Step2InputView.vue` 是旧版路由页面，不是向导内的 Step 2

**计划 Task 9 修改** `Step2InputView.vue`。

**实际**：`Step2InputView.vue` 是旧版独立路由页面（使用 `/step/2` 路由 + `NSteps` 组件），与 `ConfigWizardView` 中的 Step 2 是**两套独立实现**。

`ConfigWizardView` 中的 Step 2 内容是内联渲染的（第 51-72 行），使用 `InputSourceList` 组件。Task 9 应修改 `InputSourceList.vue` 或在 `ConfigWizardView` 中处理 Step 2 的 AI 联动，而非修改 `Step2InputView.vue`。

---

## 三、设计问题（建议修正）

### 设计 1：Guide 模式与编排模式共存未处理

**现有 `ConfigWizardView`** 已有完整的编排模式（`orchestrateMode`、`doOrchestrate`、`onOrchestrateConfirm`），通过 AI 面板的"AI 编排步骤链"快捷操作触发。

**计划新增** guide 模式，但未说明两者如何共存：

| 场景 | 当前行为 | 计划行为 | 冲突 |
|------|---------|---------|------|
| 用户从首页 AI 引导进入 | 不存在 | guide 模式 | — |
| 用户从首页手动进入 | 可用编排模式 | 无 AI 面板 | — |
| guide 模式中用户说"帮我编排全部步骤" | 不适用 | 应切换到编排？ | 未定义 |
| 编排模式中用户想逐步引导 | 不支持 | 应切换到 guide？ | 未定义 |

**建议**：在 `ConfigWizardView` 中增加模式判断：
- `?guide=` 参数 → guide 模式（右侧固定面板）
- 无参数 → 现有 sidebar/overlay 模式（含编排功能）
- guide 模式中隐藏编排快捷操作
- 两种模式共享 `aiMessages`，但渲染方式不同

---

### 设计 2：首页 `?guide=` 与现有 `?prompt=` 参数冲突

**现有 `HomeView.vue`**（第 179-182 行）：

```typescript
function startWithPrompt(prompt: string) {
  store.resetAll()
  router.push('/config/new?prompt=' + encodeURIComponent(prompt))
}
```

**计划新增**：

```typescript
router.push('/config/new?guide=' + encodeURIComponent(promptText.value.trim()))
```

两个参数 `?prompt=` 和 `?guide=` 功能重叠。`ConfigWizardView` 中已有对 `?prompt=` 的处理逻辑。

**建议**：统一为 `?guide=` 参数，移除 `?prompt=`。在 `ConfigWizardView` 中将 `?prompt=` 的处理迁移到 guide 模式初始化逻辑中。

---

### 设计 3：对话历史按配置 ID 隔离

**计划 Task 4** 使用固定 key `configforge-chat-history` 存储对话历史。

**问题**：用户创建多个配置时，所有配置共享同一份对话历史。切换配置后看到的是上一个配置的 AI 对话，体验混乱。

**建议**：key 改为 `configforge-chat-history-${configId}`，每个配置独立存储。当 `configId` 为 `null`（新建）时使用 `configforge-chat-history-new`。

---

### 设计 4：`onMounted` 中 `startGuide` 缺少防重复触发

**计划 Task 8**：

```typescript
onMounted(async () => {
  if (isGuideMode.value) {
    const result = await startGuide(guidePrompt.value)
    // ...
  }
})
```

**问题**：`ConfigWizardView` 可能在多种场景下 mount（如浏览器前进/后退、热更新），每次都会触发 `startGuide`，导致重复的 AI 请求和消息。

**建议**：增加 guard：

```typescript
const guideInitialized = ref(false)

onMounted(async () => {
  if (isGuideMode.value && !guideInitialized.value) {
    guideInitialized.value = true
    // 恢复历史或初始化引导
    const history = loadMessages()
    if (history.length > 0) {
      aiMessages.value = history
    } else {
      await startGuide(guidePrompt.value)
    }
  }
})
```

---

### 设计 5：`completeStep` 函数冲突

**计划 Task 11 新增** `completeStep` 函数，但 `ConfigWizardView` 已有 `completeStep`（第 281-295 行），包含步骤完成逻辑和滚动行为。

计划的新代码只处理列变更检测，没有保留原有的步骤完成逻辑。

**建议**：在现有 `completeStep` 函数中**追加**列变更检测逻辑，而非替换。

---

## 四、遗漏项（设计规格有但计划无）

### 遗漏 1：AI 填写标记的视觉实现

设计规格 6.1 节定义了"AI 已填写"视觉标记：

| 填写来源 | 样式 |
|---------|------|
| AI 填写 | 绿色边框 + 浅绿背景 + "AI 已填写" badge |
| 用户手动修改 | 恢复默认边框 + "已编辑" badge |

计划 Task 3 添加了 `aiPrefilledFields` Map 和标记方法，但**没有任何 Task 实现视觉标记**。需要在 Step 1-4 的表单字段上添加条件样式和 badge。

**建议**：新增 Task（或在 Task 8 中补充），为 `NInput`/`NSelect` 等表单组件添加：
- `:class="{ 'ai-prefilled': store.isAiPrefilled('scene.name') }"` 条件样式
- `<span class="ai-badge">AI 已填写</span>` 标记
- `@input` 事件触发 `store.markUserEdited('scene.name')`

---

### 遗漏 2：`translate-checkpoint` 接入

设计规格 7.4 节明确要求："Step 3 引导中，AI 面板可主动建议设置数据检查点"。后端 `translate-checkpoint` API 已实现，但计划中没有 Task 接入。

**建议**：在 Task 8（ConfigWizardView 集成）或新增 Task 中，当 guide 模式进入 Step 3 时，AI 面板主动建议添加检查点，用户用自然语言描述后调用 `POST /api/ai/translate-checkpoint`。

---

### 遗漏 3：5 秒追加提示 + 30 秒取消按钮

设计规格 5.5 节定义了 AI 响应延迟的分级处理：

- 0-5 秒：三点动画 + "AI 正在思考..."
- 5-30 秒：追加提示 "生成较复杂的代码可能需要更长时间"
- 超过 30 秒：显示"取消"按钮

计划 Task 7 只实现了 30 秒取消按钮，**缺少 5 秒追加提示**。

---

### 遗漏 4：暗色模式适配

计划 Task 7 的 CSS 中存在硬编码颜色：

```css
background: rgba(13, 148, 136, 0.06);  /* 硬编码 primary 色 */
border-color: #f59e0b;                  /* 硬编码警告色 */
background: #ef4444;                    /* 硬编码危险色 */
```

这些颜色在暗色模式下会显得不协调。应使用 CSS 变量。

---

## 五、小问题汇总

| # | 问题 | 建议 |
|---|------|------|
| 1 | Task 6 的 `onVoicePlaceholder()` 函数体为空 | 添加 `message.info('语音输入即将支持')` 提示 |
| 2 | Task 6 的 `store.scene.name = promptText.value` 直接赋值 | `scene` 是 `SceneInfo` 类型，应确认 `name` 字段可写 |
| 3 | Task 7 的 `renderMsgContent` 用 `v-html` 渲染 | 需 XSS 防护，应复用现有 `DOMPurify.sanitize()` |
| 4 | Task 8 的 `buildStepContext` 暴露了 `processor_plugins` | 可能泄露敏感信息（如数据库连接名），应脱敏 |
| 5 | Task 12 的 `existing_prompt_logic` 函数不存在 | 应引用实际的 `build_prompt` 函数 |
| 6 | Task 13 验证清单缺少"手动创建路径"测试 | 应增加：首页 → 手动创建 → 无 AI 面板 → 正常完成 5 步 |
| 7 | 计划未处理 `AiChatPanel` 现有的打字机效果 | guide 模式消息是否需要打字机效果？建议保留 |
| 8 | Task 8 的 `applyPrefill` 只处理 Step 1 | Step 2/3/4 的 prefill 应用逻辑标注为"在 Task 9 处理"但 Task 9 只处理了类型选择 |

---

## 六、修正建议汇总

| 优先级 | 问题 | 修正建议 |
|--------|------|---------|
| **P0** | Bug 3: `useAiGuide` 直接 fetch | 改为调用 `useAiApi.askSuggestion`，复用速率限制/错误清洗/超时/取消 |
| **P0** | Bug 4: 正则语法错误 | `(?i)AS` → `/AS/i` |
| **P0** | Bug 5: currentStep 重复定义 | 复用现有 `currentStep` ref，不新建 |
| **P0** | Bug 6: Step2InputView 是旧页面 | 改为修改 `InputSourceList.vue` 或在 `ConfigWizardView` 中处理 |
| **P1** | Bug 1: useAiStatus 描述错误 | 保留 null 状态改进，修正描述 |
| **P1** | Bug 2: ChatMessage 行号错误 | 修正为第 34 行，补充 `code` 字段保留 |
| **P1** | 设计 1: 编排模式共存 | 增加 guide/sidebar 模式切换逻辑 |
| **P1** | 设计 2: ?guide= 与 ?prompt= 冲突 | 统一为 `?guide=`，移除 `?prompt=` |
| **P1** | 设计 3: 对话历史按配置隔离 | key 改为 `configforge-chat-history-${configId}` |
| **P1** | 设计 4: startGuide 防重复 | 增加 `guideInitialized` guard |
| **P1** | 设计 5: completeStep 冲突 | 在现有函数中追加逻辑，不替换 |
| **P2** | 遗漏 1: AI 填写视觉标记 | 新增 Task 或在 Task 8 中补充 |
| **P2** | 遗漏 2: translate-checkpoint | 新增 Task 接入 |
| **P2** | 遗漏 3: 5 秒追加提示 | Task 7 补充 |
| **P2** | 遗漏 4: 暗色模式 | 硬编码颜色改为 CSS 变量 |
| **P3** | 小问题 1-8 | 逐一修正 |

---

## 七、建议的任务顺序调整

当前 Task 1-13 顺序基本合理，但建议调整：

1. **Task 2 应先于 Task 1**：`useAiStatus` 的 `null` 状态影响首页（Task 6）的 `v-if="aiConfigured !== false"` 判断，应先确立类型
2. **Task 7 和 Task 8 应合并或紧邻**：AiChatPanel 的 guide 模式和 ConfigWizardView 的集成高度耦合，分开提交可能导致中间状态不可用
3. **新增 Task 14**：AI 填写视觉标记（遗漏 1）
4. **新增 Task 15**：translate-checkpoint 接入（遗漏 2）
5. **Task 13 之前增加 Task 16**：暗色模式适配（遗漏 4）
