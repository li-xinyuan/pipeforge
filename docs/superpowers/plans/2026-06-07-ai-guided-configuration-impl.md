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
- Modify: `configforge-web/src/types/wizard.ts`

- [ ] **Step 1: 新增 ChatMessage 扩展字段和 GuideAction/GuideResponse 类型**

在 `wizard.ts` 中 `ChatMessage` 接口（约第 225 行）追加字段，新增类型：

```typescript
// 追加到 ChatMessage 接口中
export interface ChatMessage {
  role: 'user' | 'ai'
  content: string
  orchestration?: any
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

`useAiStatus` 当前每次调用创建独立 `aiConfigured` ref。引导模式需要首页和向导共享同一状态。

- [ ] **Step 1: 改写 useAiStatus 为模块级单例**

```typescript
// configforge-web/src/composables/useAiStatus.ts
import { ref } from 'vue'

// 模块级单例，所有调用者共享
const aiConfigured = ref<boolean | null>(null) // null = 未检测，true/false = 已检测
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
    const msgs: ChatMessage[] = [
      { role: 'ai', content: 'Hello', timestamp: Date.now() },
      { role: 'user', content: 'Hi', timestamp: Date.now() },
    ]
    saveMessages(msgs)
    const loaded = loadMessages()
    expect(loaded).toHaveLength(2)
    expect(loaded[0].content).toBe('Hello')
  })

  it('truncates to 50 messages', () => {
    const { saveMessages, loadMessages } = useConversationHistory()
    const msgs: ChatMessage[] = Array.from({ length: 60 }, (_, i) => ({
      role: i % 2 === 0 ? 'ai' as const : 'user' as const,
      content: `msg ${i}`,
      timestamp: Date.now() + i,
    }))
    saveMessages(msgs)
    const loaded = loadMessages()
    expect(loaded).toHaveLength(50)
    expect(loaded[0].content).toBe('msg 10') // 前 10 条被截断
  })

  it('returns empty array when no history', () => {
    const { loadMessages } = useConversationHistory()
    expect(loadMessages()).toEqual([])
  })

  it('clears history', () => {
    const { saveMessages, loadMessages, clearHistory } = useConversationHistory()
    saveMessages([{ role: 'ai', content: 'test', timestamp: Date.now() }])
    clearHistory()
    expect(loadMessages()).toEqual([])
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

const STORAGE_KEY = 'configforge-chat-history'
const MAX_MESSAGES = 50

function estimateSize(messages: ChatMessage[]): number {
  return new Blob([JSON.stringify(messages)]).size
}

export function useConversationHistory() {
  function saveMessages(messages: ChatMessage[]) {
    try {
      // 保留最近 MAX_MESSAGES 条
      let toSave = messages.slice(-MAX_MESSAGES)
      // 如果超过 5MB 限制，进一步截断
      while (estimateSize(toSave) > 4 * 1024 * 1024 && toSave.length > 10) {
        toSave = toSave.slice(-Math.floor(toSave.length / 2))
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
    } catch {
      // localStorage 不可用或 quota 超出时静默忽略
    }
  }

  function loadMessages(): ChatMessage[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  }

  function clearHistory() {
    try { localStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
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

  function parseGuideResponse(aiText: string): GuideResponse {
    // 尝试从 AI 回复中提取 JSON 块
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
    // 无 JSON → 整个文本作为 message
    return { message: aiText }
  }

  async function callSuggest(category: string, context: string): Promise<string | null> {
    try {
      const resp = await fetch('/api/ai/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, context }),
      })
      if (!resp.ok) return null
      const data = await resp.json()
      return data.content || null
    } catch {
      return null
    }
  }

  /**
   * 首页进入向导时调用。传入用户需求描述，返回初始引导消息。
   */
  async function startGuide(userInput: string): Promise<GuideResponse> {
    const context = `用户需求描述：${userInput}`
    const content = await callSuggest('scene', context)
    if (!content) {
      return {
        message: '抱歉，AI 暂时不可用。你可以手动填写表单，或者先去设置页配置 AI。',
      }
    }
    const guide = parseGuideResponse(content)
    // 从 content 中提取场景名称作为 prefill
    if (!guide.prefill) {
      guide.prefill = { 'scene.name': extractSceneName(userInput, content) }
    }
    return guide
  }

  /**
   * 步骤切换时调用。传入当前步骤和 wizard 状态，返回引导消息。
   */
  async function stepGuide(step: number, context: Record<string, any>): Promise<GuideResponse> {
    const category = STEP_CATEGORY_MAP[step] || 'chat'
    const ctxStr = JSON.stringify({ current_step: step, ...context })
    const content = await callSuggest(category, ctxStr)
    if (!content) {
      return { message: 'AI 暂不可用，请手动完成此步骤。' }
    }
    return parseGuideResponse(content)
  }

  function extractSceneName(userInput: string, aiResponse: string): string {
    // 简单策略：取用户输入前 30 字符作为场景名
    return userInput.length > 30 ? userInput.slice(0, 30) + '...' : userInput
  }

  return { parseGuideResponse, startGuide, stepGuide, callSuggest }
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

function onVoicePlaceholder() {
  // 下版本实现语音输入
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
  return msg.content.replace(/\n/g, '<br>')
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
const isGuideMode = computed(() => !!route.query.guide)
const guidePrompt = computed(() => (route.query.guide as string) || '')

// 替换旧的 aiMessages 初始值
const aiMessages = ref<ChatMessage[]>([])

// 步骤级 AI 引导触发
const currentStep = ref(1)
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
    input_types: store.inputs.map(i => i.plugin),
    processors_count: store.processors.length,
    processor_plugins: store.processors.map(p => p.plugin),
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

// 初始化 guide 模式
onMounted(async () => {
  if (isGuideMode.value) {
    // 恢复对话历史
    const history = loadMessages()
    if (history.length) aiMessages.value = history

    // 触发初始引导
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
    saveMessages(aiMessages.value)
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
- Modify: `configforge-web/src/views/Step2InputView.vue`
- Modify: `configforge-web/src/components/step2/InputSourceList.vue`

使 AI 面板中的输入类型选择（Excel/CSV/数据库）能触发页面上的卡片高亮和表单切换。

- [ ] **Step 1: Step2InputView 暴露选中方法**

在 `Step2InputView.vue` 的 `<script setup>` 中追加：

```typescript
import { useWizardStore } from '../stores/wizard'

const store = useWizardStore()
const inputSourceListRef = ref<InstanceType<typeof InputSourceList>>()

// 由 AI 面板触发：选择输入类型
function selectInputType(plugin: 'excel' | 'csv' | 'database') {
  store.addInput(plugin)
}

defineExpose({ selectInputType })
```

- [ ] **Step 2: ConfigWizardView 中桥接 guide action**

在 `onGuideAction` 中增加对 Step 2 类型选择的处理：

```typescript
function onGuideAction(value: string) {
  // Step 2: 输入类型选择
  if (currentStep.value === 2 && ['excel', 'csv', 'database'].includes(value)) {
    step2El.value?.selectInputType(value as 'excel' | 'csv' | 'database')
    aiMessages.value.push({ role: 'user', content: value, step: 2, timestamp: Date.now() })
    saveMessages(aiMessages.value)
    return
  }
  onGuideSend(value)
}
```

- [ ] **Step 3: 提交**

```bash
git add configforge-web/src/views/Step2InputView.vue configforge-web/src/views/ConfigWizardView.vue
git commit -m "feat: bridge AI panel input type selection to Step 2 cards"
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
        const parts = col.trim().split(/\s+(?i)AS\s+/)
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
- Modify: `configforge-web/src/views/ConfigWizardView.vue`

在 `completeStep` 函数中，当从 Step 3 切换到 Step 4 时检测列变更。

- [ ] **Step 1: 在 completeStep 中添加列变更检测**

```typescript
import { useColumnDiff } from '../composables/useColumnDiff'

const { extractSelectColumns, diffColumns } = useColumnDiff()
let lastKnownSelectColumns: string[] = []

function completeStep(step: number) {
  // Step 3 → 4: 检测列变更
  if (step === 3 && isGuideMode.value) {
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
        }
      }
      lastKnownSelectColumns = currentCols
    }
  }

  // 原有步骤完成逻辑...
  currentStep.value = Math.min(step + 1, 5)
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
    # 使用现有 prompt 模板
    prompt = existing_prompt_logic(request.category, context)
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

### Task 13: 集成测试与最终验证

**Files:**
- 所有已修改文件

- [ ] **Step 1: 运行全部测试**

```bash
cd configforge-web && npx vue-tsc --noEmit && npx vitest run
cd .. && python3 -m pytest tests/ -q
```

Expected: 0 type errors, all tests pass

- [ ] **Step 2: 手动验证关键路径**

1. 首页 → 输入需求 → "AI 引导配置" → 确认进入向导 + AI 面板显示
2. 首页 → 断网/AI 不可用 → 输入框灰掉 + "前往设置" 按钮
3. 首页 → "手动创建" → 正常进入向导（无 AI 面板）
4. 向导 Step 1 → AI 填入场景名称
5. 向导 Step 2 → AI 面板询问输入类型 → 点击按钮 → 卡片高亮
6. 向导 Step 3 → AI 生成代码
7. 向导 Step 3→4 → AI 检测列变更 → 弹提示
8. 刷新页面 → 对话历史保留
9. 面板折叠 → 展开 → 消息保留

- [ ] **Step 3: 提交最终变更**

```bash
git add -A
git commit -m "feat: complete AI-guided configuration — all 5 steps with guide panel"
```

---

## 验证清单

| 验证项 | 命令 | 预期 |
|--------|------|------|
| TypeScript 类型检查 | `npx vue-tsc --noEmit` | 0 errors |
| 前端单元测试 | `npx vitest run` | 全部通过 |
| 后端测试 | `python3 -m pytest tests/ -q` | 141 passed |
| 首页 AI 可用 | 手动 | 输入框高亮 + 引导按钮 |
| 首页 AI 不可用 | 手动 | 灰掉 + 设置链接 |
| 引导面板折叠 | 手动 | 320px → 32px → 恢复 |
| 对话历史保留 | 手动 | 刷新后消息仍在 |
| 5 步引导完成 | 手动 | 每步 AI 消息 + 预填 |
