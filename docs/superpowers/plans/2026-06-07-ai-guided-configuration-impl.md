# AI 引导式配置 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ConfigForge 从手动填表模式改造为 AI 手把手引导模式——首页双入口，进入向导后右侧固定 AI 面板逐步引导用户完成 5 步配置。

**Architecture:** 增强现有 `AiChatPanel.vue` 新增 `guide` 模式作为右侧固定面板；新增 `useAiGuide` composable 封装引导逻辑，复用现有 `suggest` API；首页 `HomeView.vue` 改为双入口（AI 引导 + 手动创建）；向导中 AI 自动填入表单字段，用户审核确认。

**Tech Stack:** Vue 3 + TypeScript + Pinia + Naive UI + Tailwind CSS, FastAPI + Python

---

## 文件结构

| 文件 | 状态 | 职责 |
|------|------|------|
| `configforge-web/src/composables/useAiGuide.ts` | **新建** | AI 引导逻辑：步骤推进、消息构造、prefill 解析 |
| `configforge-web/src/composables/useAiStatus.ts` | 改动 | 将 `aiConfigured` 改为全局单例，支持首页和向导共享 |
| `configforge-web/src/composables/useConversationHistory.ts` | **新建** | 对话历史持久化：localStorage 存取，50 条截断 |
| `configforge-web/src/stores/wizard.ts` | 改动 | 新增 `aiPrefilledFields` Map、`markAiPrefilled`、`markUserEdited` |
| `configforge-web/src/types/wizard.ts` | 改动 | 新增 `ChatMessage.type/step/actions/prefill`、`GuideAction`、`GuideResponse` |
| `configforge-web/src/views/HomeView.vue` | 改动 | 双入口设计 + AI 可用性判断 + 降级状态 |
| `configforge-web/src/views/ConfigWizardView.vue` | 改动 | 右侧固定 AI 面板（guide 模式）、步骤级 AI 触发 |
| `configforge-web/src/components/wizard/AiChatPanel.vue` | **增强** | 新增 `mode="guide"`、`currentStep` prop、引导消息渲染、折叠功能 |
| `configforge-web/src/views/Step1SceneView.vue` | 改动 | AI 填入检测 + 标记 badge |
| `configforge-web/src/views/Step2InputView.vue` | 改动 | 与 AI 面板联动（选类型） |
| `configforge-web/src/views/Step3ProcessView.vue` | 改动 | 代码生成 + 步骤切换时列变更检测 |
| `configforge-web/src/views/Step4OutputView.vue` | 改动 | 列映射自动完成 |
| `configforge-web/src/composables/useColumnDiff.ts` | **新建** | SQL SELECT 列名提取 + 与输出列映射比较 |
| `configforge/api/ai.py` | 改动 | suggest prompt 模板增强：支持 `current_step` + `wizard_state` context |

---

### Task 1: 类型定义扩展

**Files:**
- Modify: `configforge-web/src/types/wizard.ts:34-39`

- [ ] **Step 1: 新增 ChatMessage 扩展字段和 GuideAction/GuideResponse 类型**

`ChatMessage` 接口位于 `wizard.ts` 第 34 行，现有字段为 `role, content, code?, orchestration?`。

追加 `step, type, actions, prefill, timestamp` 字段（均为可选，不破坏现有引用）：

```typescript
// 第 34 行，追加字段
export interface ChatMessage {
  role: 'user' | 'ai'
  content: string
  code?: string
  orchestration?: OrchestrationResult
  // --- 新增字段 ---
  step?: number              // 关联步骤编号 1-5
  type?: 'guide' | 'chat' | 'warning' | 'suggestion'
  actions?: GuideAction[]
  prefill?: Record<string, any>
  timestamp?: number
}

// 新增类型
export interface GuideAction {
  label: string
  value: string
  style?: 'primary' | 'default' | 'warning'
}

export interface GuideResponse {
  message: string
  actions?: GuideAction[]
  prefill?: Record<string, any>
}
```

- [ ] **Step 2: 运行类型检查确认无破坏性变更**

```bash
cd configforge-web && npx vue-tsc --noEmit
```

Expected: 0 errors（新增字段均为可选，不影响现有代码）

- [ ] **Step 3: 提交**

```bash
git add configforge-web/src/types/wizard.ts
git commit -m "feat: add ChatMessage guide fields and GuideAction/GuideResponse types"
```

---

### Task 2: AI 可用性状态提升为全局单例

**Files:**
- Modify: `configforge-web/src/composables/useAiStatus.ts`

`aiConfigured` 已经是模块级 `const aiConfigured = ref(false)`，所有调用者共享同一状态。

需要改进的是：当前 `ref(false)` 无法区分"未检测"和"检测后确认不可用"——两者都是 falsy。改为 `Ref<boolean | null>`，`null` 表示未检测。

- [ ] **Step 1: 将 aiConfigured 改为三态**

```typescript
// configforge-web/src/composables/useAiStatus.ts
import { ref } from 'vue'

// 模块级，三态：null = 未检测，true = 已配置可用，false = 已检测不可用
const aiConfigured = ref<boolean | null>(null)
const checking = ref(false)
const checking = ref(false)

export function useAiStatus() {
  async function checkStatus() {
    if (checking.value) return
    checking.value = true
    try {
      const resp = await fetch('/api/ai/settings')
      if (resp.ok) {
        const data = await resp.json()
        aiConfigured.value = !!(data.enabled && data.api_key && data.api_key.length > 0)
      } else {
        aiConfigured.value = false
      }
    } catch {
      aiConfigured.value = false
    } finally {
      checking.value = false
    }
  }

  function markConfigured() {
    aiConfigured.value = true
  }

  return { aiConfigured, checking, checkStatus, markConfigured }
}
```

改 `aiConfigured` 为 `Ref<boolean | null>`，`null` 表示尚未检测。

- [ ] **Step 2: 验证现有 AiStatusBanner 未破坏**

```bash
cd configforge-web && npx vue-tsc --noEmit
```

Expected: 0 errors。`AiStatusBanner.vue` 当前直接 `import { useAiStatus }` 并读取 `aiConfigured`，需确认兼容。若 `AiStatusBanner` 中行 `v-if="!aiConfigured"` 在 `null` 时行为不符合预期，追加一步修改 `AiStatusBanner.vue` 的条件判断：

```html
<!-- AiStatusBanner.vue 条件改为 -->
v-if="aiConfigured === false"
```

- [ ] **Step 3: 提交**

```bash
git add configforge-web/src/composables/useAiStatus.ts
git commit -m "refactor: promote aiConfigured to module-level singleton in useAiStatus"
```

---

### Task 3: Store 字段追踪

**Files:**
- Modify: `configforge-web/src/stores/wizard.ts`

- [ ] **Step 1: 新增 aiPrefilledFields 和标记方法**

在 `wizard.ts` 的 store 定义中追加（约 `uploadedFiles` 之后）：

```typescript
// UI 层临时标记，不持久化，刷新后消失
const aiPrefilledFields = ref<Map<string, boolean>>(new Map())

function markAiPrefilled(fieldPath: string) {
  aiPrefilledFields.value.set(fieldPath, true)
}

function markUserEdited(fieldPath: string) {
  aiPrefilledFields.value.delete(fieldPath)
}

function isAiPrefilled(fieldPath: string): boolean {
  return aiPrefilledFields.value.has(fieldPath)
}
```

在 store 的 return 对象中追加 `aiPrefilledFields, markAiPrefilled, markUserEdited, isAiPrefilled`。

- [ ] **Step 2: 运行现有测试确认无回归**

```bash
cd configforge-web && npx vitest run
```

Expected: 现有测试全通过（仅新增导出，无破坏性改动）。

- [ ] **Step 3: 提交**

```bash
git add configforge-web/src/stores/wizard.ts
git commit -m "feat: add aiPrefilledFields Map and mark methods to wizard store"
```

---

### Task 4: 对话历史持久化

**Files:**
- Create: `configforge-web/src/composables/useConversationHistory.ts`

- [ ] **Step 1: 编写测试**

创建 `configforge-web/tests/composables/useConversationHistory.test.ts`：

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { useConversationHistory } from '../../src/composables/useConversationHistory'
import type { ChatMessage } from '../../src/types/wizard'

describe('useConversationHistory', () => {
  beforeEach(() => { localStorage.clear() })

  it('saves and loads messages', () => {
    const { saveMessages, loadMessages } = useConversationHistory()
    const configId = 'test-config-1'
    const msgs: ChatMessage[] = [
      { role: 'ai', content: 'Hello', timestamp: Date.now() },
      { role: 'user', content: 'Hi', timestamp: Date.now() },
    ]
    saveMessages(msgs, configId)
    const loaded = loadMessages(configId)
    expect(loaded).toHaveLength(2)
    expect(loaded[0].content).toBe('Hello')
  })

  it('isolates history per config', () => {
    const { saveMessages, loadMessages } = useConversationHistory()
    saveMessages([{ role: 'ai', content: 'Config A', timestamp: Date.now() }], 'config-a')
    saveMessages([{ role: 'ai', content: 'Config B', timestamp: Date.now() }], 'config-b')
    expect(loadMessages('config-a')[0].content).toBe('Config A')
    expect(loadMessages('config-b')[0].content).toBe('Config B')
  })

  it('truncates to 50 messages', () => {
    const { saveMessages, loadMessages } = useConversationHistory()
    const msgs: ChatMessage[] = Array.from({ length: 60 }, (_, i) => ({
      role: i % 2 === 0 ? 'ai' as const : 'user' as const,
      content: `msg ${i}`,
      timestamp: Date.now() + i,
    }))
    saveMessages(msgs, 'test')
    const loaded = loadMessages('test')
    expect(loaded).toHaveLength(50)
    expect(loaded[0].content).toBe('msg 10')
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd configforge-web && npx vitest run tests/composables/useConversationHistory.test.ts
```

Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 useConversationHistory**

```typescript
// configforge-web/src/composables/useConversationHistory.ts
import type { ChatMessage } from '../types/wizard'

const STORAGE_KEY_PREFIX = 'configforge-chat-history'
const MAX_MESSAGES = 50

function getStorageKey(configId?: string | null): string {
  return configId ? `${STORAGE_KEY_PREFIX}-${configId}` : `${STORAGE_KEY_PREFIX}-new`
}

function estimateSize(messages: ChatMessage[]): number {
  return new Blob([JSON.stringify(messages)]).size
}

export function useConversationHistory() {
  function saveMessages(messages: ChatMessage[], configId?: string | null) {
    try {
      let toSave = messages.slice(-MAX_MESSAGES)
      while (estimateSize(toSave) > 4 * 1024 * 1024 && toSave.length > 10) {
        toSave = toSave.slice(-Math.floor(toSave.length / 2))
      }
      localStorage.setItem(getStorageKey(configId), JSON.stringify(toSave))
    } catch { /* ignore */ }
  }

  function loadMessages(configId?: string | null): ChatMessage[] {
    try {
      const raw = localStorage.getItem(getStorageKey(configId))
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  }

  function clearHistory(configId?: string | null) {
    try { localStorage.removeItem(getStorageKey(configId)) } catch { /* ignore */ }
  }

  return { saveMessages, loadMessages, clearHistory }
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd configforge-web && npx vitest run tests/composables/useConversationHistory.test.ts
```

Expected: 4 tests PASS

- [ ] **Step 5: 提交**

```bash
git add configforge-web/src/composables/useConversationHistory.ts configforge-web/tests/composables/useConversationHistory.test.ts
git commit -m "feat: add useConversationHistory with localStorage persistence and 50-msg truncation"
```

---

### Task 5: useAiGuide composable

**Files:**
- Create: `configforge-web/src/composables/useAiGuide.ts`

引导逻辑的核心：步骤推进、调用 suggest、解析 GuideResponse、预填表单。

- [ ] **Step 1: 编写测试**

创建 `configforge-web/tests/composables/useAiGuide.test.ts`：

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAiGuide } from '../../src/composables/useAiGuide'
import { setActivePinia, createPinia } from 'pinia'

describe('useAiGuide', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('parseGuideResponse extracts JSON from markdown code block', () => {
    const { parseGuideResponse } = useAiGuide()
    const aiText = '好的！```json\n{"message":"test","actions":[{"label":"OK","value":"ok"}]}\n```'
    const result = parseGuideResponse(aiText)
    expect(result.message).toBe('test')
    expect(result.actions).toHaveLength(1)
  })

  it('parseGuideResponse falls back to whole text as message when no JSON', () => {
    const { parseGuideResponse } = useAiGuide()
    const result = parseGuideResponse('Hello, this is plain text')
    expect(result.message).toBe('Hello, this is plain text')
    expect(result.actions).toBeUndefined()
  })

  it('startGuide returns scene info for step 1', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ content: '场景名称：订单报表' }), { status: 200 })
    )
    const { startGuide } = useAiGuide()
    const result = await startGuide('订单统计')
    expect(result).toHaveProperty('message')
  })

  it('stepGuide returns guidance for current step context', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({
        content: '```json\n{"message":"请选择输入源","actions":[{"label":"Excel","value":"excel"}]}\n```'
      }), { status: 200 })
    )
    const { stepGuide } = useAiGuide()
    const result = await stepGuide(2, { inputs: [] })
    expect(result.message).toBe('请选择输入源')
    expect(result.actions![0].label).toBe('Excel')
  })
  // 注：useAiGuide 内部调用 useAiApi.askSuggestion，
  // 该函数通过 fetch('/api/ai/suggest') 发送请求，mock 仍为 fetch
})
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd configforge-web && npx vitest run tests/composables/useAiGuide.test.ts
```

Expected: FAIL

- [ ] **Step 3: 实现 useAiGuide**

```typescript
// configforge-web/src/composables/useAiGuide.ts
import { useWizardStore } from '../stores/wizard'
import { useAiApi } from './useWizardApi'
import type { GuideAction, GuideResponse, ChatMessage } from '../types/wizard'

const STEP_CATEGORY_MAP: Record<number, string> = {
  1: 'scene',
  2: 'chat',
  3: 'sql',
  4: 'mapping',
  5: 'chat',
}

export function useAiGuide() {
  const store = useWizardStore()
  const { askSuggestion } = useAiApi()
  // askSuggestion 已有：速率限制、错误清洗、超时控制、AbortController 支持

  function parseGuideResponse(aiText: string): GuideResponse {
    const jsonMatch = aiText.match(/```json\s*([\s\S]*?)\s*```/)
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[1])
        return {
          message: parsed.message || aiText,
          actions: parsed.actions,
          prefill: parsed.prefill,
        }
      } catch { /* fall through */ }
    }
    return { message: aiText }
  }

  async function startGuide(userInput: string): Promise<GuideResponse> {
    const content = await askSuggestion('scene', { description: userInput })
    if (!content) {
      return { message: '抱歉，AI 暂时不可用。你可以手动填写表单，或者先去设置页配置 AI。' }
    }
    const guide = parseGuideResponse(content)
    if (!guide.prefill) {
      guide.prefill = { 'scene.name': extractSceneName(userInput) }
    }
    return guide
  }

  async function stepGuide(step: number, context: Record<string, any>): Promise<GuideResponse> {
    const category = STEP_CATEGORY_MAP[step] || 'chat'
    const content = await askSuggestion(category, {
      current_step: step,
      ...context,
    })
    if (!content) {
      return { message: 'AI 暂不可用，请手动完成此步骤。' }
    }
    return parseGuideResponse(content)
  }

  function extractSceneName(userInput: string): string {
    return userInput.length > 30 ? userInput.slice(0, 30) + '...' : userInput
  }

  return { parseGuideResponse, startGuide, stepGuide }
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd configforge-web && npx vitest run tests/composables/useAiGuide.test.ts
```

Expected: 3 tests PASS

- [ ] **Step 5: 提交**

```bash
git add configforge-web/src/composables/useAiGuide.ts configforge-web/tests/composables/useAiGuide.test.ts
git commit -m "feat: add useAiGuide composable with suggest-based step guidance"
```

---

### Task 6: 首页双入口设计

**Files:**
- Modify: `configforge-web/src/views/HomeView.vue`

- [ ] **Step 1: 改写 Hero 区域模板**

将当前 Hero 区域改为双入口布局。找到 `<section class="home__hero">` 部分（约第 7-36 行），替换为：

```html
<section class="home__hero">
  <div class="home__hero-inner">
    <div class="home__hero-badge">⚡ AI 驱动 · 你说需求，AI 填配置</div>
    <h1 class="home__hero-title">
      描述你的数据处理需求<br>
      <span class="home__hero-gradient">Forge 帮你自动生成配置</span>
    </h1>
    <p class="home__hero-subtitle">
      用自然语言告诉我你想做什么<br>进入向导后，我会一步步引导你完成配置
    </p>

    <!-- AI 可用：输入框 + 引导按钮 -->
    <template v-if="aiConfigured !== false">
      <div class="home__prompt-input-wrap">
        <input
          class="home__prompt-input"
          v-model="promptText"
          placeholder="例如：把订单表和用户表关联，按城市统计订单金额，导出 Excel"
          @keydown.enter="startAiGuide"
        />
        <button class="home__prompt-mic" @click="onVoicePlaceholder" title="语音输入（下版本支持）">🎤</button>
      </div>
      <button class="home__cta" @click="startAiGuide">✨ AI 引导配置</button>

      <div class="home__prompt-chips">
        <span class="home__prompt-label">试试这样说</span>
        <button class="home__prompt-chip" @click="startWithPrompt('把用户表的 ID、名称和邮箱导出到 CSV')">把用户表导出到 CSV</button>
        <button class="home__prompt-chip" @click="startWithPrompt('合并订单表和用户表，按城市统计订单金额')">合并并统计订单</button>
        <button class="home__prompt-chip" @click="startWithPrompt('从数据库读取销售数据，按月份汇总，写入数据库')">月度销售汇总</button>
      </div>
    </template>

    <!-- AI 不可用：灰掉输入框 + 引导到设置 -->
    <template v-else>
      <div class="home__prompt-input-wrap">
        <input
          class="home__prompt-input home__prompt-input--disabled"
          disabled
          placeholder="需先配置 AI 才能使用智能引导"
        />
      </div>
      <button class="home__cta home__cta--secondary" @click="router.push('/settings')">前往设置 →</button>
    </template>

    <!-- 手动创建入口始终可见 -->
    <router-link to="/config/new" class="home__manual-link" @click="store.resetAll()">
      或 手动创建 →
    </router-link>
  </div>
</section>
```

- [ ] **Step 2: 添加 script 逻辑**

在 `<script setup>` 中追加：

```typescript
import { useAiStatus } from '../composables/useAiStatus'

const { aiConfigured, checkStatus } = useAiStatus()
const promptText = ref('')

onMounted(() => { checkStatus() })

function startAiGuide() {
  if (!promptText.value.trim()) return
  store.resetAll()
  // 将首页输入文字带入向导
  store.scene.name = promptText.value.trim().length > 30
    ? promptText.value.trim().slice(0, 30) + '...'
    : promptText.value.trim()
  router.push('/config/new?guide=' + encodeURIComponent(promptText.value.trim()))
}

function startWithPrompt(text: string) {
  promptText.value = text
  startAiGuide()
}

import { useMessage } from 'naive-ui'
const message = useMessage()

function onVoicePlaceholder() {
  message.info('语音输入即将在下一版本支持')
}
```

- [ ] **Step 3: 添加 CSS**

在 `<style scoped>` 中追加：

```css
.home__prompt-input-wrap {
  position: relative;
  max-width: 520px;
  margin: 0 auto 14px;
}
.home__prompt-input {
  width: 100%;
  padding: 14px 48px 14px 16px;
  border-radius: 12px;
  border: 2px solid var(--color-border-light);
  background: var(--color-surface);
  font-size: 15px;
  color: var(--color-text);
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s;
}
.home__prompt-input:focus { border-color: var(--color-primary); }
.home__prompt-input--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.home__prompt-mic {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
  color: var(--color-text-muted);
}
.home__prompt-mic:hover { background: var(--color-surface-hover); }
.home__cta {
  padding: 12px 40px;
  border-radius: 12px;
  border: none;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  color: #fff;
  margin-bottom: 16px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.home__cta:hover { transform: translateY(-2px); box-shadow: 0 6px 24px rgba(13, 148, 136, 0.3); }
.home__cta--secondary { background: var(--color-surface); color: var(--color-text); border: 1px solid var(--color-border-light); }
.home__manual-link {
  display: inline-block;
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  text-decoration: none;
  padding: 4px 0;
}
.home__manual-link:hover { color: var(--color-primary); }
```

移除旧的 `startNewConfig` 和 `startWithPrompt` 中不再需要的逻辑（保留现有配置列表部分不变）。

- [ ] **Step 4: 运行检查**

```bash
cd configforge-web && npx vue-tsc --noEmit && npx vitest run
```

Expected: 0 type errors, existing tests pass

- [ ] **Step 5: 提交**

```bash
git add configforge-web/src/views/HomeView.vue
git commit -m "feat: dual-entry home page with AI guide + manual create paths"
```

---

### Task 7: AiChatPanel 增强 —— guide 模式

**Files:**
- Modify: `configforge-web/src/components/wizard/AiChatPanel.vue`

- [ ] **Step 1: 新增 guide 模式模板**

在现有模板顶部（约第 2 行 `<aside>` 之前），增加 guide 模式的 wrapper：

```html
<template>
  <!-- Guide mode: fixed right panel -->
  <div v-if="mode === 'guide'" class="ai-guide-panel" :class="{ 'ai-guide-panel--collapsed': collapsed }">
    <!-- Collapsed narrow strip -->
    <div v-if="collapsed" class="ai-guide-collapsed" @click="collapsed = false">
      <span class="ai-guide-collapsed-icon">🤖</span>
    </div>
    <!-- Expanded panel -->
    <template v-else>
      <div class="ai-guide-header">
        <span class="ai-guide-header-icon">🤖</span>
        <span class="ai-guide-header-title">Forge · AI 助手</span>
        <button class="ai-guide-collapse-btn" @click="collapsed = true" title="收起面板">◀</button>
      </div>
      <div class="ai-guide-msgs" ref="msgsEl">
        <div v-for="(msg, i) in messages" :key="i" class="ai-guide-msg" :class="`ai-guide-msg--${msg.role}`">
          <div class="ai-guide-msg-bubble" :class="msg.type ? `ai-guide-msg-bubble--${msg.type}` : ''">
            <!-- Step badge -->
            <span v-if="msg.step" class="ai-guide-msg-step">步骤 {{ msg.step }}</span>
            <span class="ai-guide-msg-text" v-html="renderMsgContent(msg)"></span>
            <!-- Action buttons -->
            <div v-if="msg.actions?.length" class="ai-guide-msg-actions">
              <button
                v-for="(act, ai) in msg.actions" :key="ai"
                class="ai-guide-action-btn"
                :class="{ 'ai-guide-action-btn--primary': act.style === 'primary' }"
                @click="$emit('guideAction', act.value)"
              >{{ act.label }}</button>
            </div>
          </div>
        </div>
        <!-- Typing indicator -->
        <div v-if="loading" class="ai-guide-typing">
          <span class="ai-guide-typing-dots"><span>.</span><span>.</span><span>.</span></span>
          <span class="ai-guide-typing-text">AI 正在思考...</span>
          <button v-if="showCancel" class="ai-guide-cancel-btn" @click="$emit('cancelGuide')">取消</button>
        </div>
      </div>
      <div class="ai-guide-input">
        <input
          v-model="guideInput"
          placeholder="告诉 Forge 你需要什么..."
          @keydown.enter="sendGuideMsg"
        />
        <button class="ai-guide-send-btn" @click="sendGuideMsg">发送</button>
      </div>
    </template>
  </div>

  <!-- Original sidebar/overlay/fullscreen modes (unchanged) -->
  <aside v-else-if="visible" class="ai-panel" ...>
    <!-- existing template -->
  </aside>
</template>
```

- [ ] **Step 2: 新增 script 逻辑**

在 `<script setup>` 中追加：

```typescript
// 新增 props
const props = defineProps<{
  // ...existing...
  mode?: 'sidebar' | 'overlay' | 'fullscreen' | 'guide'
  currentStep?: number
  loading?: boolean
}>()

const emit = defineEmits<{
  // ...existing...
  guideAction: [value: string]
  cancelGuide: []
}>()

// Guide mode state
const collapsed = ref(false)
const guideInput = ref('')
const showCancel = ref(false)
let cancelTimer: ReturnType<typeof setTimeout> | null = null

function sendGuideMsg() {
  const text = guideInput.value.trim()
  if (!text) return
  guideInput.value = ''
  emit('send', text)
}

function renderMsgContent(msg: ChatMessage): string {
  // XSS 防护：转义 HTML 标签后替换换行
  const escaped = msg.content
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return escaped.replace(/\n/g, '<br>')
}

// Watch loading: show cancel button after 30s
watch(() => props.loading, (val) => {
  showCancel.value = false
  if (cancelTimer) clearTimeout(cancelTimer)
  if (val) {
    cancelTimer = setTimeout(() => { showCancel.value = true }, 30000)
  }
})

onUnmounted(() => {
  if (cancelTimer) clearTimeout(cancelTimer)
})
```

- [ ] **Step 3: 新增 guide 模式 CSS**

在 `<style scoped>` 中追加：

```css
/* ───── Guide mode ───── */
.ai-guide-panel {
  width: 320px;
  flex-shrink: 0;
  background: var(--color-surface);
  border-left: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  overflow: hidden;
}
.ai-guide-panel--collapsed {
  width: 32px;
}
.ai-guide-collapsed {
  width: 32px;
  height: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 16px;
  cursor: pointer;
  background: var(--color-primary-bg);
  border-left: 1px solid var(--color-border-light);
}
.ai-guide-collapsed-icon { font-size: 20px; }
.ai-guide-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(13, 148, 136, 0.06);
  border-bottom: 1px solid var(--color-border-light);
  flex-shrink: 0;
}
.ai-guide-header-icon { font-size: 18px; }
.ai-guide-header-title { font-size: 13px; font-weight: 600; color: var(--color-primary); flex: 1; }
.ai-guide-collapse-btn {
  width: 24px; height: 24px; border-radius: 4px; border: none;
  background: transparent; cursor: pointer; font-size: 12px; color: var(--color-text-muted);
}
.ai-guide-collapse-btn:hover { background: var(--color-surface-hover); }
.ai-guide-msgs { flex: 1; overflow-y: auto; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
.ai-guide-msg { display: flex; max-width: 95%; }
.ai-guide-msg--ai { align-self: flex-start; }
.ai-guide-msg--user { align-self: flex-end; }
.ai-guide-msg-bubble {
  padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.6;
  background: var(--color-surface-hover); border: 1px solid var(--color-border-light);
  color: var(--color-text);
}
.ai-guide-msg--user .ai-guide-msg-bubble { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.ai-guide-msg-bubble--suggestion { border-color: var(--color-primary); background: rgba(13,148,136,0.04); }
.ai-guide-msg-bubble--warning { border-color: #f59e0b; background: rgba(245,158,11,0.04); }
.ai-guide-msg-step { font-size: 10px; color: var(--color-text-muted); display: block; margin-bottom: 4px; }
.ai-guide-msg-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.ai-guide-action-btn {
  padding: 5px 12px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--color-primary); background: transparent; color: var(--color-primary);
  transition: all 0.2s; font-family: inherit;
}
.ai-guide-action-btn:hover { background: var(--color-primary); color: #fff; }
.ai-guide-action-btn--primary { background: var(--color-primary); color: #fff; }
.ai-guide-action-btn--primary:hover { background: var(--color-primary-light); }
.ai-guide-typing { display: flex; align-items: center; gap: 8px; padding: 8px 12px; font-size: 12px; color: var(--color-text-muted); }
.ai-guide-typing-dots span { animation: guide-dot-bounce 1.4s infinite ease-in-out both; font-weight: bold; }
.ai-guide-typing-dots span:nth-child(1) { animation-delay: 0s; }
.ai-guide-typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.ai-guide-typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes guide-dot-bounce { 0%,80%,100% { opacity: 0 } 40% { opacity: 1 } }
.ai-guide-cancel-btn { margin-left: auto; font-size: 11px; padding: 4px 10px; border-radius: 6px; border: 1px solid #ef4444; background: transparent; color: #ef4444; cursor: pointer; }
.ai-guide-cancel-btn:hover { background: #ef4444; color: #fff; }
.ai-guide-input { display: flex; gap: 8px; padding: 10px 14px; border-top: 1px solid var(--color-border-light); flex-shrink: 0; }
.ai-guide-input input { flex: 1; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--color-border-light); background: var(--color-bg); font-size: 13px; color: var(--color-text); outline: none; font-family: inherit; }
.ai-guide-input input:focus { border-color: var(--color-primary); }
.ai-guide-send-btn { padding: 6px 14px; border-radius: 8px; border: none; background: var(--color-primary); color: #fff; font-size: 13px; cursor: pointer; font-weight: 600; }
.ai-guide-send-btn:hover { background: var(--color-primary-light); }
```

- [ ] **Step 4: 运行检查**

```bash
cd configforge-web && npx vue-tsc --noEmit
```

Expected: 0 errors

- [ ] **Step 5: 提交**

```bash
git add configforge-web/src/components/wizard/AiChatPanel.vue
git commit -m "feat: add guide mode to AiChatPanel with collapsible sidebar and action buttons"
```

---

### Task 8: ConfigWizardView 集成 guide 模式

**Files:**
- Modify: `configforge-web/src/views/ConfigWizardView.vue`

这是最大的一处改动——将侧边栏 overlay AI 面板改为右侧固定的 guide 面板。

- [ ] **Step 1: 调整布局为左右分栏**

找到 wizard 主体模板（约第 168-170 行 `<div class="wizard">`），将结构和 AI 面板部分替换：

```html
<div class="wizard__body" :class="{ 'wizard__body--with-ai': isGuideMode }">
  <!-- Left: 5-step content -->
  <div class="wizard__steps" ref="stepsEl">
    <!-- 现有 5 个 WizardStepCard 保留，略 -->
  </div>

  <!-- Right: AI guide panel -->
  <AiChatPanel
    v-if="isGuideMode"
    mode="guide"
    :visible="true"
    :messages="aiMessages"
    :current-step="currentStep"
    :loading="suggesting"
    @send="onGuideSend"
    @guide-action="onGuideAction"
    @cancel-guide="onCancelGuide"
  />
</div>
```

- [ ] **Step 2: 添加 script 逻辑**

```typescript
import { useRoute } from 'vue-router'
import { useAiGuide } from '../composables/useAiGuide'
import { useConversationHistory } from '../composables/useConversationHistory'

const route = useRoute()
const { startGuide, stepGuide, parseGuideResponse } = useAiGuide()
const { saveMessages, loadMessages } = useConversationHistory()

// Guide mode: 当 URL 带 ?guide= 参数时启用
// 替换现有 ?prompt= 参数（功能重叠），统一为 ?guide=
const isGuideMode = computed(() => !!route.query.guide)
const guidePrompt = computed(() => (route.query.guide as string) || '')

// 编排模式与 guide 模式互斥
// guide 模式中隐藏编排快捷操作（"AI 编排步骤链"按钮不出现）
// 手动进入（无 ?guide=）时保留现有 sidebar/overlay 模式和编排功能
const aiQuickActions = computed(() => {
  if (isGuideMode.value) {
    // guide 模式下不显示编排，只显示与步骤相关的快捷操作
    const actions = []
    if (currentStep.value === 1) actions.push('确认场景信息')
    if (currentStep.value === 3) actions.push('解释代码', '优化代码')
    return actions
  }
  // 非 guide 模式保留现有行为
  const actions = ['生成场景描述', 'AI 分析列', 'AI 生成代码', 'AI 自动映射']
  if (store.inputs.length > 0) actions.unshift('AI 编排步骤链')
  return actions
})

// 替换旧的 aiMessages 初始值
const aiMessages = ref<ChatMessage[]>([])

// 步骤级 AI 引导触发
// 复用现有的 currentStep（第 209 行已定义 const currentStep = ref(1)）
const lastGuidedStep = ref(0)

watch(currentStep, async (step) => {
  if (!isGuideMode.value || step === lastGuidedStep.value) return
  lastGuidedStep.value = step
  await triggerStepGuide(step)
})

async function triggerStepGuide(step: number) {
  suggesting.value = true
  const context = buildStepContext(step)
  const result = await stepGuide(step, context)
  suggesting.value = false

  const msg: ChatMessage = {
    role: 'ai',
    content: result.message,
    step,
    type: 'guide',
    actions: result.actions,
    prefill: result.prefill,
    timestamp: Date.now(),
  }
  aiMessages.value.push(msg)
  saveMessages(aiMessages.value)

  // 应用 prefill
  if (result.prefill) {
    applyPrefill(result.prefill, step)
  }
}

function buildStepContext(step: number): Record<string, any> {
  return {
    current_step: step,
    scene_name: store.scene.name,
    scene_description: store.scene.description,
    inputs_count: store.inputs.length,
    input_plugins: store.inputs.map(i => i.plugin), // 不暴露 fileId/连接字符串
    processors_count: store.processors.length,
    processor_plugins: store.processors.map(p => p.plugin), // 不暴露代码内容
    output_plugin: store.output?.plugin,
    has_columns: !!(store.output?.config as any)?.columns?.length,
  }
}

function applyPrefill(prefill: Record<string, any>, step: number) {
  if (step === 1 && prefill['scene.name']) {
    store.scene.name = prefill['scene.name']
    store.markAiPrefilled('scene.name')
  }
  if (step === 1 && prefill['scene.description']) {
    store.scene.description = prefill['scene.description']
    store.markAiPrefilled('scene.description')
  }
  // Step 2 prefill: input type selection handled in Task 9 (onGuideAction bridge)
  // Step 3 prefill: SQL code applied via suggest(category='sql') response
  // Step 4 prefill: column mapping applied via suggest(category='mapping') response
}

function onGuideSend(text: string) {
  aiMessages.value.push({ role: 'user', content: text, timestamp: Date.now() })
  saveMessages(aiMessages.value)
  triggerStepGuide(currentStep.value)
}

function onGuideAction(value: string) {
  onGuideSend(value)
}

function onCancelGuide() {
  suggesting.value = false
}

// 初始化 guide 模式 — 防重复触发
const guideInitialized = ref(false)

onMounted(async () => {
  if (isGuideMode.value && !guideInitialized.value) {
    guideInitialized.value = true

    // 恢复对话历史
    const history = loadMessages(store.configId)
    if (history.length > 0) {
      aiMessages.value = history
      return
    }

    // 首次进入：触发初始引导
    suggesting.value = true
    const result = await startGuide(guidePrompt.value)
    suggesting.value = false

    aiMessages.value.push({
      role: 'ai',
      content: result.message,
      step: 1,
      type: 'guide',
      actions: result.actions,
      prefill: result.prefill,
      timestamp: Date.now(),
    })
    saveMessages(aiMessages.value, store.configId)
    if (result.prefill) applyPrefill(result.prefill, 1)
  }
})
```

- [ ] **Step 3: 添加 CSS**

```css
.wizard__body {
  display: flex;
  height: calc(100vh - 56px);
}
.wizard__body--with-ai {
  /* AI panel is 320px wide, rest for steps */
}
.wizard__steps {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
```

- [ ] **Step 4: 运行检查**

```bash
cd configforge-web && npx vue-tsc --noEmit && npx vitest run
```

Expected: 0 type errors, existing tests pass

- [ ] **Step 5: 提交**

```bash
git add configforge-web/src/views/ConfigWizardView.vue
git commit -m "feat: integrate guide-mode AiChatPanel into ConfigWizardView"
```

---

### Task 9: 步骤 2 AI 联动 —— 输入类型选择

**Files:**
- Modify: `configforge-web/src/components/step2/InputSourceList.vue`
- Modify: `configforge-web/src/views/ConfigWizardView.vue`

注意：`Step2InputView.vue` 是旧版独立路由页面（`/step/2`），与 `ConfigWizardView` 中的 Step 2 是两套独立实现。ConfigWizardView 中的 Step 2 使用 `InputSourceList` 组件（第 60 行），应在此处实现 AI 联动。

- [ ] **Step 1: InputSourceList 暴露 addInput 并支持外部触发**

在 `InputSourceList.vue` 的 `<script setup>` 中，确认 `addInput` 函数可被父组件调用：

```typescript
// InputSourceList.vue 中已有的 addInput 函数（约第 49 行）
function addInput(plugin: 'excel' | 'csv' | 'database' = 'excel') {
  store.addInput(plugin)
}

// 暴露给父组件通过 ref 调用
defineExpose({ addInput })
```

- [ ] **Step 2: ConfigWizardView 中桥接 guide action**

在 ConfigWizardView 的 `<script setup>` 中（Task 8 新增的 `onGuideAction` 函数内），增加 Step 2 类型选择处理：

```typescript
const inputSourceListRef = ref<InstanceType<typeof InputSourceList>>()

function onGuideAction(value: string) {
  // Step 2: 输入类型选择 — 直接操作 store 触发卡片高亮
  if (currentStep.value === 2 && ['excel', 'csv', 'database'].includes(value)) {
    store.addInput(value as 'excel' | 'csv' | 'database')
    aiMessages.value.push({ role: 'user', content: value, step: 2, timestamp: Date.now() })
    saveMessages(aiMessages.value)
    return
  }
  // 其他步骤的 action 处理...
  onGuideSend(value)
}
```

- [ ] **Step 3: 提交**

```bash
git add configforge-web/src/components/step2/InputSourceList.vue configforge-web/src/views/ConfigWizardView.vue
git commit -m "feat: bridge AI panel input type selection to Step 2 cards via store"
```

---

### Task 10: 列变更检测 composable

**Files:**
- Create: `configforge-web/src/composables/useColumnDiff.ts`

- [ ] **Step 1: 编写测试**

创建 `configforge-web/tests/composables/useColumnDiff.test.ts`：

```typescript
import { describe, it, expect } from 'vitest'
import { useColumnDiff } from '../../src/composables/useColumnDiff'

describe('useColumnDiff', () => {
  const { extractSelectColumns, diffColumns } = useColumnDiff()

  it('extracts columns from simple SELECT', () => {
    const cols = extractSelectColumns('SELECT city, COUNT(id) AS cnt FROM t')
    expect(cols).toEqual(['city', 'cnt'])
  })

  it('extracts columns from SELECT with JOIN', () => {
    const cols = extractSelectColumns('SELECT u.city, COUNT(o.id) AS order_count, SUM(o.amount) AS total FROM users u JOIN orders o')
    expect(cols).toEqual(['city', 'order_count', 'total'])
  })

  it('handles SELECT *', () => {
    const cols = extractSelectColumns('SELECT * FROM t')
    expect(cols).toEqual(['*'])
  })

  it('diffs columns: added and removed', () => {
    const diff = diffColumns(['city', 'order_count'], ['city', 'order_count', 'total_amount'])
    expect(diff.added).toEqual(['total_amount'])
    expect(diff.removed).toEqual([])
  })

  it('diffs columns: removed', () => {
    const diff = diffColumns(['city', 'order_count', 'total_amount'], ['city', 'order_count'])
    expect(diff.added).toEqual([])
    expect(diff.removed).toEqual(['total_amount'])
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd configforge-web && npx vitest run tests/composables/useColumnDiff.test.ts
```

Expected: FAIL

- [ ] **Step 3: 实现 useColumnDiff**

```typescript
// configforge-web/src/composables/useColumnDiff.ts

export function useColumnDiff() {
  /**
   * 从 SQL SELECT 语句中提取输出列名。
   * 简单版本：匹配 SELECT ... FROM 之间的列定义。
   */
  function extractSelectColumns(sql: string): string[] {
    try {
      const upper = sql.toUpperCase().trim()
      const selectIdx = upper.indexOf('SELECT')
      const fromIdx = upper.indexOf('FROM', selectIdx + 6)
      if (selectIdx === -1 || fromIdx === -1) return []

      const columnsStr = sql.slice(selectIdx + 6, fromIdx).trim()
      if (columnsStr === '*') return ['*']

      // 按逗号分割，但需处理括号
      const columns: string[] = []
      let depth = 0, current = ''
      for (const ch of columnsStr) {
        if (ch === '(') depth++
        else if (ch === ')') depth--
        if (ch === ',' && depth === 0) {
          columns.push(current.trim())
          current = ''
        } else {
          current += ch
        }
      }
      if (current.trim()) columns.push(current.trim())

      // 提取别名或列名
      return columns.map(col => {
        const parts = col.trim().split(/\s+AS\s+/i)
        const lastPart = parts[parts.length - 1].trim()
        // 如果最后一段包含 . 取点后的部分
        const dotIdx = lastPart.lastIndexOf('.')
        return dotIdx > -1 ? lastPart.slice(dotIdx + 1) : lastPart
      })
    } catch {
      return []
    }
  }

  /**
   * 比较两组列名，返回差异。
   */
  function diffColumns(oldCols: string[], newCols: string[]) {
    const oldSet = new Set(oldCols)
    const newSet = new Set(newCols)
    return {
      added: newCols.filter(c => !oldSet.has(c)),
      removed: oldCols.filter(c => !newSet.has(c)),
      hasChanges: oldCols.length !== newCols.length || newCols.some(c => !oldSet.has(c)),
    }
  }

  return { extractSelectColumns, diffColumns }
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd configforge-web && npx vitest run tests/composables/useColumnDiff.test.ts
```

Expected: 5 tests PASS

- [ ] **Step 5: 提交**

```bash
git add configforge-web/src/composables/useColumnDiff.ts configforge-web/tests/composables/useColumnDiff.test.ts
git commit -m "feat: add useColumnDiff for SQL SELECT column extraction and comparison"
```

---

### Task 11: 步骤切换时列变更检测（ConfigWizardView 中的联动）

**Files:**
- Modify: `configforge-web/src/views/ConfigWizardView.vue:281-295`

在现有 `completeStep` 函数（第 281 行）中**追加**列变更检测逻辑，不替换原有内容。

- [ ] **Step 1: 在现有 completeStep 中追加列变更检测**

```typescript
import { useColumnDiff } from '../composables/useColumnDiff'

const { extractSelectColumns, diffColumns } = useColumnDiff()
let lastKnownSelectColumns: string[] = []

// 第 281 行的现有函数，追加 Step 3→4 列变更检测
function completeStep(n: number) {
  // --- 新增：Step 3 → 4 时检测列变更 ---
  if (n === 3 && isGuideMode.value) {
    const sqlProcessor = store.processors.find(p => p.plugin === 'sql')
    if (sqlProcessor?.sql) {
      const currentCols = extractSelectColumns(sqlProcessor.sql)
      const outputCols = ((store.output?.config as any)?.columns || []).map((c: any) => c.source)

      if (lastKnownSelectColumns.length > 0 && outputCols.length > 0) {
        const diff = diffColumns(lastKnownSelectColumns, currentCols)
        if (diff.hasChanges) {
          aiMessages.value.push({
            role: 'ai',
            content: `SQL 输出列已变更（新增 ${diff.added.length} 列，移除 ${diff.removed.length} 列），是否更新列映射？`,
            step: 4,
            type: 'warning',
            actions: [
              { label: '更新列映射', value: 'update_column_mapping', style: 'primary' },
              { label: '保持不变', value: 'keep_columns' },
            ],
            timestamp: Date.now(),
          })
          saveMessages(aiMessages.value)
        }
      }
      lastKnownSelectColumns = currentCols
    }
  }
  // --- 新增结束 ---

  // 原有逻辑不变
  if (n < 5) {
    currentStep.value = n + 1
    scrollToStep(n + 1)
    if (n === 2) {
      sqlEditorRef.value?.checkTableRenames()
    }
    if (n === 4) {
      nextTick(() => {
        yamlPreviewRef.value?.loadYaml()
        showStep5Tip.value = true
      })
    }
  }
}
```

- [ ] **Step 2: 提交**

```bash
git add configforge-web/src/views/ConfigWizardView.vue
git commit -m "feat: add SQL column change detection on Step 3→4 transition"
```

---

### Task 12: 后端 suggest API prompt 增强

**Files:**
- Modify: `configforge/api/ai.py`

- [ ] **Step 1: 增强 suggest 端点 context 解析**

在 `suggest` 函数中（约第 80 行），增加对 `current_step` 和 `wizard_state` 的支持：

```python
# 在 suggest 函数中解析 context
context = request.context or ""

# 尝试从 context 中提取 wizard_state JSON
wizard_state = {}
if isinstance(context, str) and context.strip().startswith("{"):
    try:
        parsed = json.loads(context)
        current_step = parsed.get("current_step")
        wizard_state = parsed
        context = json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        pass

# 根据 current_step 选择 prompt 模板
if current_step == 1:
    # Step 1: 从用户需求中提取场景信息
    prompt = f"""你是一个数据流水线配置助手。用户正在创建新的数据处理流水线配置。
当前步骤：步骤 1（场景信息）

用户需求：{context}

请分析用户需求，返回 JSON 格式：
{{"message": "引导消息", "actions": [{{"label": "确认,下一步", "value": "confirm"}}], "prefill": {{"scene.name": "提取的场景名称", "scene.description": "生成的场景描述"}}}}

场景名称应简洁（15字以内），场景描述应包含主要的数据处理步骤。"""
elif current_step == 2:
    # Step 2: 引导用户选择输入源类型
    prompt = f"""你是一个数据流水线配置助手。
当前步骤：步骤 2（输入源）

配置状态：{context}

请引导用户选择数据输入来源类型，返回 JSON：
{{"message": "引导消息", "actions": [{{"label": "📊 Excel", "value": "excel"}}, {{"label": "🗄 CSV", "value": "csv"}}, {{"label": "🔌 数据库", "value": "database"}}]}}"""
else:
    # 使用现有 prompt 构建逻辑（各 category 已有对应模板）
    prompt = _build_prompt(request.category, context)
```

- [ ] **Step 2: 运行后端测试确认无回归**

```bash
cd configforge && python3 -m pytest tests/ -q
```

Expected: 141 passed

- [ ] **Step 3: 提交**

```bash
git add configforge/api/ai.py
git commit -m "feat: enhance suggest API prompt for step-based wizard guidance"
```

---

### Task 13: AI 填写标记视觉实现

**Files:**
- Modify: `configforge-web/src/views/Step1SceneView.vue`
- Modify: `configforge-web/src/views/ConfigWizardView.vue`
- Modify: `configforge-web/src/style.css`

设计规格 6.1 定义的 AI 填写视觉标记需要落实到表单组件上。

- [ ] **Step 1: 添加 CSS 类**

在 `style.css` 中追加：

```css
.ai-prefilled {
  border-color: var(--color-primary) !important;
  background: var(--color-primary-bg) !important;
}
.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(13,148,136,0.1);
  color: var(--color-primary);
  font-weight: 600;
}
.ai-badge--edited {
  background: rgba(100,116,139,0.1);
  color: var(--color-text-muted);
}
```

- [ ] **Step 2: Step 1 场景名称添加标记**

在 Step1SceneView.vue 中，场景名称输入框添加 AI 标记：

```html
<div>
  <label class="block text-xs font-medium text-slate-500 mb-1">
    场景名称
    <span v-if="store.isAiPrefilled('scene.name')" class="ai-badge">AI 已填写</span>
    <span v-else-if="sceneEdited" class="ai-badge ai-badge--edited">已编辑</span>
  </label>
  <input
    class="scene-input"
    :class="{ 'ai-prefilled': store.isAiPrefilled('scene.name') }"
    v-model="store.scene.name"
    @input="onSceneNameInput"
  />
</div>
```

在 `<script setup>` 中追加：

```typescript
const sceneEdited = ref(false)

function onSceneNameInput() {
  if (store.isAiPrefilled('scene.name')) {
    store.markUserEdited('scene.name')
    sceneEdited.value = true
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add configforge-web/src/style.css configforge-web/src/views/Step1SceneView.vue
git commit -m "feat: add AI-prefilled visual badge and border to form fields"
```

---

### Task 14: translate-checkpoint 接入

**Files:**
- Modify: `configforge-web/src/views/ConfigWizardView.vue`

设计规格 7.4 节：Step 3 引导中接入自然语言转检查点规则。

- [ ] **Step 1: 在 triggerStepGuide 的 Step 3 分支中添加检查点引导**

```typescript
async function triggerStepGuide(step: number) {
  suggesting.value = true
  const context = buildStepContext(step)
  const result = await stepGuide(step, context)
  suggesting.value = false

  const msg: ChatMessage = {
    role: 'ai',
    content: result.message,
    step,
    type: 'guide',
    actions: result.actions,
    prefill: result.prefill,
    timestamp: Date.now(),
  }
  aiMessages.value.push(msg)

  // Step 3: 主动建议检查点
  if (step === 3 && store.processors.length > 0) {
    aiMessages.value.push({
      role: 'ai',
      content: '需要我帮你设置数据检查点吗？比如确保输出行数不为零、关键列不重复等。你可以用自然语言描述检查规则。',
      step: 3,
      type: 'suggestion',
      actions: [
        { label: '💡 帮我推荐', value: 'suggest_checkpoints', style: 'primary' },
        { label: '⏭ 先跳过', value: 'skip_checkpoints' },
      ],
      timestamp: Date.now(),
    })
  }

  saveMessages(aiMessages.value, store.configId)
  if (result.prefill) applyPrefill(result.prefill, step)
}

// 处理检查点建议
async function handleCheckpointSuggestion(userInput: string) {
  const content = await askSuggestion('checkpoint', {
    description: userInput,
    processors: store.processors.map(p => ({ plugin: p.plugin, outputTables: p.outputTables })),
  })
  if (content) {
    aiMessages.value.push({ role: 'ai', content, step: 3, type: 'guide', timestamp: Date.now() })
    // 尝试解析并填入 CheckpointSection
  }
}
```

- [ ] **Step 2: 提交**

```bash
git add configforge-web/src/views/ConfigWizardView.vue
git commit -m "feat: integrate translate-checkpoint suggestions in Step 3 guide"
```

---

### Task 15: 面板 5 秒追加提示 + 暗色模式适配

**Files:**
- Modify: `configforge-web/src/components/wizard/AiChatPanel.vue`

- [ ] **Step 1: 5 秒追加提示**

在 Task 7 已有的 loading watcher 中增加 5 秒提示：

```typescript
let fiveSecTimer: ReturnType<typeof setTimeout> | null = null

watch(() => props.loading, (val) => {
  showCancel.value = false
  showLongWait.value = false
  if (cancelTimer) clearTimeout(cancelTimer)
  if (fiveSecTimer) clearTimeout(fiveSecTimer)

  if (val) {
    fiveSecTimer = setTimeout(() => { showLongWait.value = true }, 5000)
    cancelTimer = setTimeout(() => { showCancel.value = true }, 30000)
  }
})
```

模板中追加（在 typing indicator 内）：

```html
<span v-if="showLongWait" class="ai-guide-typing-hint">生成较复杂的代码可能需要更长时间</span>
```

- [ ] **Step 2: 暗色模式适配**

将 Task 7 中硬编码颜色改为 CSS 变量：

```css
/* 改前 */
background: rgba(13, 148, 136, 0.06);
border-color: #f59e0b;
background: #ef4444;

/* 改后 */
background: var(--color-primary-bg);
border-color: var(--color-warning, #f59e0b);
background: var(--color-error, #ef4444);
```

- [ ] **Step 3: 提交**

```bash
git add configforge-web/src/components/wizard/AiChatPanel.vue
git commit -m "feat: add 5s wait hint + CSS variable color for dark mode in guide panel"
```

---

### Task 16: 集成测试与最终验证

**Files:**
- 所有已修改文件

- [ ] **Step 1: 运行全部测试**

```bash
cd configforge-web && npx vue-tsc --noEmit && npx vitest run
cd .. && python3 -m pytest tests/ -q
```

Expected: 0 type errors, all tests pass

- [ ] **Step 2: 手动验证关键路径（共 14 项）**

1. 首页 → 输入需求 → "AI 引导配置" → 确认进入向导 + AI 面板显示
2. 首页 → "手动创建" → 正常进入向导（无 AI 面板）→ 完整 5 步正常
3. 首页 → 断网/AI 不可用 → 输入框灰掉 + "前往设置" 按钮 + "手动创建" 突出
4. 首页输入文字 → "手动创建" → Step 1 场景名称预填输入文字
5. 向导 Step 1 → AI 填入场景名称 + 绿色边框 + "AI 已填写" badge
6. 用户修改场景名称 → badge 变为灰色"已编辑" + 绿色边框消失
7. 向导 Step 2 → AI 面板询问输入类型 → 点击 Excel 按钮 → 卡片高亮
8. 向导 Step 3 → AI 生成代码 + 面板主动建议检查点
9. 向导 Step 3→4 → 如果 SQL 列变更 → AI 弹列映射更新提示
10. 刷新页面 → 对话历史保留（同一配置不丢失）
11. 切换不同配置 → 对话历史隔离（不同配置独立存储）
12. 面板折叠（◀）→ 32px 窄条 → 单击恢复
13. AI 响应超过 5 秒 → 显示"可能需要更长时间"提示
14. 暗色模式切换 → 面板颜色协调，无硬编码色问题

- [ ] **Step 3: 提交最终变更**

```bash
git add -A
git commit -m "feat: complete AI-guided configuration — 16 tasks, all 5 steps with guide panel"
```

---

## 验证清单

| 验证项 | 命令/方式 | 预期 |
|--------|----------|------|
| TypeScript 类型检查 | `npx vue-tsc --noEmit` | 0 errors |
| 前端单元测试 | `npx vitest run` | 全部通过 |
| 后端测试 | `python3 -m pytest tests/ -q` | 141 passed |
| 首页 AI 可用 | 手动 | 输入框高亮 + 引导按钮 + chips |
| 首页 AI 不可用 | 手动 | 灰掉 + 设置链接 + 手动创建突出 |
| 首页 → 手动创建 | 手动 | 无 AI 面板，5 步正常 |
| 输入文字带入 Step 1 | 手动 | 场景名称预填 |
| AI 填写 badge | 手动 | 绿色边框 + badge，编辑后消失 |
| 引导面板折叠 | 手动 | 320px → 32px → 单击恢复 |
| 对话历史保留 | 手动 | 刷新后同配置消息仍在 |
| 对话历史隔离 | 手动 | 不同配置独立存储 |
| 暗色模式 | 手动切换 | 面板颜色无硬编码 |
| 5 步引导完成 | 手动 | 每步 AI 消息 + 预填 |
