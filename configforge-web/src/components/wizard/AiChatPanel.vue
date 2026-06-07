<template>
  <!-- Guide mode: fixed right panel -->
  <div v-if="mode === 'guide'" class="ai-guide-panel" :class="{ 'ai-guide-panel--collapsed': collapsed }">
    <div v-if="collapsed" class="ai-guide-collapsed" @click="collapsed = false">
      <span class="ai-guide-collapsed-icon">🤖</span>
      <span class="ai-guide-collapsed-text">Forge AI 助手</span>
    </div>
    <template v-else>
      <div class="ai-guide-header">
        <span class="ai-guide-header-icon">🤖</span>
        <span class="ai-guide-header-title">Forge · AI 助手</span>
        <button class="ai-guide-collapse-btn" @click.stop="collapsed = true" title="收起面板">◀</button>
      </div>
      <div class="ai-guide-msgs" ref="guideMsgsEl">
        <div v-for="(msg, i) in messages" :key="i" class="ai-guide-msg" :class="`ai-guide-msg--${msg.role}`">
          <div class="ai-guide-msg-bubble" :class="msg.type ? `ai-guide-msg-bubble--${msg.type}` : ''">
            <span v-if="msg.step" class="ai-guide-msg-step">步骤 {{ msg.step }}</span>
            <span class="ai-guide-msg-text" v-html="getGuideDisplayContent(msg, i)"></span>
            <div v-if="msg.actions?.length" class="ai-guide-msg-actions">
              <button v-for="(act, ai) in msg.actions" :key="ai"
                class="ai-guide-action-btn"
                :class="{ 'ai-guide-action-btn--primary': act.style === 'primary' }"
                @click="$emit('guideAction', act.value)">{{ act.label }}</button>
            </div>
          </div>
        </div>
        <div v-if="loading" class="ai-guide-typing">
          <span class="ai-guide-typing-dots"><span>.</span><span>.</span><span>.</span></span>
          <span class="ai-guide-typing-text">AI 正在思考...</span>
          <span v-if="showLongWait" class="ai-guide-typing-hint">生成较复杂的代码可能需要更长时间</span>
          <button v-if="showCancel" class="ai-guide-cancel-btn" @click="$emit('cancelGuide')">取消</button>
        </div>
      </div>
      <div class="ai-guide-input">
        <input v-model="guideInput" placeholder="告诉 Forge 你需要什么..." @keydown.enter="sendGuideMsg" />
        <button class="ai-guide-send-btn" @click="sendGuideMsg">发送</button>
      </div>
    </template>
  </div>

  <!-- Original modes (sidebar / overlay / fullscreen) -->
  <aside v-else-if="visible" class="ai-panel" :class="`ai-panel--${mode || 'sidebar'}`" @click.self="onBackdropClick">
    <div class="ai-panel__inner">
      <div class="ai-panel__header">
        <div class="ai-panel__title">
          <span class="ai-panel__title-icon" aria-hidden="true">⚡</span>
          <span>AI 助手</span>
        </div>
        <button type="button" class="ai-panel__collapse" aria-label="收起面板" @click="$emit('toggle')">
          {{ (mode || 'sidebar') === 'fullscreen' ? '✕' : '−' }}
        </button>
      </div>

      <div class="ai-panel__messages" ref="messagesEl" role="log" aria-live="polite">
        <TransitionGroup name="msg">
          <div
            v-for="(msg, i) in messages"
            :key="i"
            class="ai-panel__bubble"
            :class="msg.role === 'ai' ? 'ai-panel__bubble--ai' : 'ai-panel__bubble--user'"
          >
            <div class="ai-panel__bubble-content" v-html="sanitize(getDisplayContent(msg, i))" />
            <div v-if="msg.code" class="ai-panel__code-block">
              <pre>{{ msg.code }}</pre>
            </div>
            <OrchestrationResultCard
              v-if="msg.orchestration"
              :result="msg.orchestration"
              @confirm="$emit('orchestrate-confirm', msg.orchestration)"
              @regenerate="$emit('orchestrate-regenerate')"
            />
          </div>
        </TransitionGroup>

        <div v-if="loading" class="ai-panel__loading">
          <span class="ai-panel__loading-dot"></span>
          <span class="ai-panel__loading-dot"></span>
          <span class="ai-panel__loading-dot"></span>
        </div>

        <div v-if="quickActions.length" class="ai-panel__actions">
          <p class="ai-panel__actions-label">快捷操作</p>
          <button
            v-for="action in quickActions"
            :key="action"
            type="button"
            class="ai-panel__quick-action"
            @click="$emit('quickAction', action)"
          >› {{ action }}</button>
        </div>
      </div>

      <div class="ai-panel__input" :class="{ 'ai-panel__input--disabled': loading }">
        <span aria-hidden="true" class="ai-panel__input-icon" :class="{ 'ai-panel__input-icon--loading': loading }">{{ loading ? '⏳' : '💬' }}</span>
        <input
          v-model="inputText"
          type="text"
          aria-label="向 AI 提问"
          :placeholder="loading ? 'AI 正在处理...' : '向 AI 提问...'"
          :disabled="loading"
          @keyup.enter="sendMessage"
        />
        <button type="button" class="ai-panel__send-btn" :disabled="loading" @click="sendMessage">发送</button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed, onUnmounted } from 'vue'
import DOMPurify from 'dompurify'
import OrchestrationResultCard from './OrchestrationResult.vue'
import type { ChatMessage } from '../../types/wizard'

const props = defineProps<{
  visible: boolean
  messages: ChatMessage[]
  quickActions: string[]
  mode?: 'sidebar' | 'overlay' | 'fullscreen' | 'guide'
  currentStep?: number
  loading?: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
  quickAction: [action: string]
  toggle: []
  'orchestrate-confirm': [result: any]
  'orchestrate-regenerate': []
  guideAction: [value: string]
  cancelGuide: []
}>()

const currentMode = computed(() => props.mode || 'sidebar')

const inputText = ref('')
const messagesEl = ref<HTMLElement>()
const guideMsgsEl = ref<HTMLElement>()

// Guide mode state
const collapsed = ref(false)

// Typewriter state for guide mode
const guideTypedTexts = ref<Record<number, string>>({})
const guideTypingTimers = new Map<number, ReturnType<typeof setInterval>>()

// Auto-scroll to bottom when new messages arrive or typewriter updates
function scrollGuideToBottom() {
  nextTick(() => {
    if (guideMsgsEl.value) {
      guideMsgsEl.value.scrollTop = guideMsgsEl.value.scrollHeight
    }
  })
}

watch(() => props.messages.length, scrollGuideToBottom)

// Also scroll on each typewriter tick (content height grows gradually)
watch(
  () => guideTypedTexts.value[props.messages.length - 1]?.length || 0,
  scrollGuideToBottom
)
const guideInput = ref('')
const showCancel = ref(false)
const showLongWait = ref(false)
let cancelTimer: ReturnType<typeof setTimeout> | null = null
let fiveSecTimer: ReturnType<typeof setTimeout> | null = null

onUnmounted(() => {
  if (cancelTimer) clearTimeout(cancelTimer)
  if (fiveSecTimer) clearTimeout(fiveSecTimer)
})

function sendGuideMsg() {
  const text = guideInput.value.trim()
  if (!text) return
  guideInput.value = ''
  emit('send', text)
}

// Watch guide messages for typewriter effect
watch(() => props.messages.length, (newLen, oldLen) => {
  if (props.mode !== 'guide') return
  if (newLen > 0 && newLen > (oldLen || 0)) {
    const idx = newLen - 1
    const msg = props.messages[idx]
    if (msg.role === 'ai' && msg.content) {
      startGuideTyping(idx, msg.content)
    }
  }
})

function startGuideTyping(idx: number, text: string) {
  stopGuideTyping(idx)
  guideTypedTexts.value[idx] = ''
  let i = 0
  guideTypingTimers.set(idx, setInterval(() => {
    i++
    guideTypedTexts.value[idx] = text.slice(0, i)
    if (i >= text.length) stopGuideTyping(idx)
  }, 12))
}

function stopGuideTyping(idx: number) {
  const t = guideTypingTimers.get(idx)
  if (t) { clearInterval(t); guideTypingTimers.delete(idx) }
}

function getGuideDisplayContent(msg: ChatMessage, idx: number): string {
  const full = sanitizeGuideContent(msg.content || '')
  const typed = guideTypedTexts.value[idx]
  if (typed !== undefined && typed.length < full.length) {
    return typed + '<span class="typing-cursor">|</span>'
  }
  return full
}

function sanitizeGuideContent(text: string): string {
  let cleaned = text
    // 1. XSS escape first
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  // 2. Try to extract just the message/response from JSON if present
  const msgMatch = cleaned.match(/"(?:message|response)"\s*:\s*"((?:[^"\\]|\\.)*)"/)
  if (msgMatch) {
    cleaned = msgMatch[1]
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, '\\')
  } else {
    // No JSON message field found — strip JSON-like blobs
    cleaned = cleaned
      .replace(/\{[^}]*"message"[^}]*\}/g, '')
      .replace(/\{[^}]*"actions"[^}]*\}/g, '')
      .replace(/\{[^}]*"prefill"[^}]*\}/g, '')
      .replace(/^\s*[\[\{]\s*/g, '')
      .replace(/\s*[\]\}]\s*$/g, '')
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
  }

  // 3. Convert newlines to <br>, collapse excess
  cleaned = cleaned
    .replace(/\n/g, '<br>')
    .replace(/(<br>\s*){3,}/g, '<br><br>')
    .trim()

  return cleaned || text.replace(/[{}]/g, '').replace(/\\n/g, '<br>')
}

// Keep old function for backward compat
function renderGuideContent(msg: ChatMessage): string {
  return sanitizeGuideContent(msg.content || '')
}

// Watch loading for cancel/timeout UI
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

// Typewriter state
const typedTexts = ref<Record<number, string>>({})
const typingTimers = new Map<number, ReturnType<typeof setInterval>>()

watch(() => props.messages.length, (newLen, oldLen) => {
  if (newLen > 0 && newLen > (oldLen || 0)) {
    const idx = newLen - 1
    const msg = props.messages[idx]
    if (msg.role === 'ai' && msg.content && !msg.orchestration) {
      startTyping(idx, msg.content)
    }
  }
})

function startTyping(idx: number, text: string) {
  stopTyping(idx)
  typedTexts.value[idx] = ''
  let i = 0
  typingTimers.set(idx, setInterval(() => {
    i++
    typedTexts.value[idx] = text.slice(0, i)
    if (i >= text.length) stopTyping(idx)
  }, 15))
}

function stopTyping(idx: number) {
  const t = typingTimers.get(idx)
  if (t) { clearInterval(t); typingTimers.delete(idx) }
}

function getDisplayContent(msg: ChatMessage, idx: number): string {
  if (typedTexts.value[idx] !== undefined) {
    return typedTexts.value[idx] + (typedTexts.value[idx].length < msg.content.length ? '<span class="typing-cursor">|</span>' : '')
  }
  return msg.content
}

onUnmounted(() => typingTimers.forEach(t => clearInterval(t)))

function sanitize(html: string): string {
  return DOMPurify.sanitize(html)
}

function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text)
  inputText.value = ''
}

function onBackdropClick() {
  if (currentMode.value === 'overlay') {
    emit('toggle')
  }
}

watch(() => props.messages.length, async () => {
  await nextTick()
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
})
</script>

<style scoped>
.ai-panel {
  width: var(--ai-panel-width);
  background: var(--color-surface);
  border-left: 1px solid var(--color-primary-border);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-normal);
}

.ai-panel__inner {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ai-panel__header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-primary-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.ai-panel__title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-text);
}

.ai-panel__title-icon {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.ai-panel__collapse {
  background: none;
  border: none;
  font-size: 16px;
  color: var(--color-text-muted);
  cursor: pointer;
}

.ai-panel__messages {
  flex: 1;
  padding: 12px 14px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-panel__bubble {
  max-width: 92%;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: var(--font-size-xs);
  line-height: 1.5;
}

.ai-panel__bubble--ai {
  align-self: flex-start;
  background: linear-gradient(135deg, var(--color-primary-bg), var(--color-primary-bg-light));
  color: var(--color-primary);
  border-radius: 12px 12px 12px 3px;
}

.ai-panel__bubble--user {
  align-self: flex-end;
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
  border-radius: 12px 12px 3px 12px;
}

.ai-panel__code-block {
  margin-top: 6px;
  background: var(--color-surface);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-family: monospace;
  font-size: var(--font-size-xs);
  white-space: pre-wrap;
  overflow-x: auto;
}

.ai-panel__actions {
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}

.ai-panel__actions-label {
  margin: 0 0 6px;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

.ai-panel__quick-action {
  display: block;
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  cursor: pointer;
  padding: 2px 0;
  width: 100%;
  text-align: left;
}

.ai-panel__quick-action:hover {
  text-decoration: underline;
}

.ai-panel__input {
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  margin: 8px 12px 12px;
  border: 1px solid var(--color-border-light);
  flex-shrink: 0;
}

.ai-panel__input input {
  flex: 1;
  border: none;
  background: none;
  outline: none;
  font-size: var(--font-size-xs);
  color: var(--color-text);
}

.ai-panel__input input::placeholder {
  color: var(--color-text-muted);
}

.ai-panel__send-btn {
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  font-size: var(--font-size-xs);
  font-weight: 500;
  cursor: pointer;
}

.ai-panel__send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.ai-panel__input--disabled {
  opacity: 0.7;
}

.ai-panel__input-icon--loading {
  animation: cf-pulse 1.2s ease-in-out infinite;
}

/* ───── AI Loading indicator ───── */
.ai-panel__loading {
  align-self: flex-start;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 14px;
  background: linear-gradient(135deg, var(--color-primary-bg), var(--color-primary-bg-light));
  border-radius: 12px 12px 12px 3px;
  margin-top: 4px;
}

.ai-panel__loading-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-primary);
  opacity: 0.3;
  animation: cf-loading-bounce 1.2s ease-in-out infinite;
}

.ai-panel__loading-dot:nth-child(1) { animation-delay: 0s; }
.ai-panel__loading-dot:nth-child(2) { animation-delay: 0.2s; }
.ai-panel__loading-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes cf-loading-bounce {
  0%, 60%, 100% { opacity: 0.3; transform: scale(1); }
  30% { opacity: 1; transform: scale(1.4); }
}

@keyframes cf-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ───── Message entrance animation ───── */
.msg-enter-active {
  animation: cf-message-enter 0.3s ease-out;
}

.msg-leave-active {
  animation: cf-fade-in 0.2s ease-in reverse;
}

/* ───── Overlay mode ───── */
.ai-panel--overlay {
  position: fixed;
  inset: 0;
  width: 100%;
  z-index: 200;
  background: rgba(0, 0, 0, 0.25);
  border-left: none;
  cursor: pointer;
}

[data-theme="dark"] .ai-panel--overlay {
  background: rgba(0, 0, 0, 0.45);
}

.ai-panel--overlay .ai-panel__inner {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: var(--ai-panel-width);
  background: var(--color-surface);
  border-left: 1px solid var(--color-primary-border);
  cursor: default;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.1);
}

/* ───── Fullscreen mode ───── */
.ai-panel--fullscreen {
  position: fixed;
  inset: 0;
  width: 100vw;
  z-index: 200;
  border-left: none;
}

/* ───── Responsive ───── */
@media (max-width: 1023px) {
  .ai-panel {
    --ai-panel-width: 320px;
  }
}

@media (max-width: 767px) {
  .ai-panel {
    --ai-panel-width: 100vw;
  }
}
.typing-cursor {
  animation: blink 0.7s infinite;
  color: var(--color-primary);
  font-weight: bold;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ───── Guide mode ───── */
.ai-guide-panel {
  width: 320px; flex-shrink: 0;
  background: var(--color-surface);
  border-left: 1px solid var(--color-border-light);
  display: flex; flex-direction: column;
  transition: width 0.3s; overflow: hidden;
  height: calc(100vh - 56px);
}
.ai-guide-panel--collapsed {
  width: 36px;
  min-width: 36px;
}
.ai-guide-collapsed {
  display: flex; flex-direction: column; align-items: center;
  padding: 12px 0; cursor: pointer;
  background: var(--color-primary-bg);
  writing-mode: vertical-rl;
  gap: 8px;
}
.ai-guide-collapsed-icon { font-size: 18px; }
.ai-guide-collapsed-text { font-size: 11px; color: var(--color-primary); }
.ai-guide-header {
  display: flex; align-items: center; gap: 8px; padding: 10px 14px;
  background: var(--color-primary-bg); border-bottom: 1px solid var(--color-border-light);
  flex-shrink: 0;
}
.ai-guide-header-icon { font-size: 18px; }
.ai-guide-header-title { font-size: 13px; font-weight: 600; color: var(--color-primary); flex: 1; }
.ai-guide-collapse-btn {
  width: 28px; height: 28px; border-radius: 50%; border: none;
  background: transparent; cursor: pointer; font-size: 16px; color: var(--color-text-muted);
  display: flex; align-items: center; justify-content: center;
}
.ai-guide-collapse-btn:hover { background: var(--color-surface-hover); }
.ai-guide-msgs { flex: 1; overflow-y: auto; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
.ai-guide-msg { display: flex; max-width: 95%; }
.ai-guide-msg--ai { align-self: flex-start; }
.ai-guide-msg--user { align-self: flex-end; }
.ai-guide-msg-bubble {
  padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.6;
  background: var(--color-surface-hover); border: 1px solid var(--color-border-light); color: var(--color-text);
}
.ai-guide-msg--user .ai-guide-msg-bubble { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.ai-guide-msg-bubble--suggestion { border-color: var(--color-primary); background: var(--color-primary-bg); }
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
.ai-guide-typing { display: flex; align-items: center; gap: 8px; padding: 8px 12px; font-size: 12px; color: var(--color-text-muted); flex-wrap: wrap; }
.ai-guide-typing-dots span { animation: guide-dot-bounce 1.4s infinite ease-in-out both; font-weight: bold; }
.ai-guide-typing-dots span:nth-child(1) { animation-delay: 0s; }
.ai-guide-typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.ai-guide-typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes guide-dot-bounce { 0%,80%,100% { opacity: 0 } 40% { opacity: 1 } }
.ai-guide-typing-hint { color: var(--color-text-muted); font-size: 11px; width: 100%; }
.ai-guide-cancel-btn {
  margin-left: auto; font-size: 11px; padding: 4px 10px; border-radius: 6px;
  border: 1px solid #ef4444; background: transparent; color: #ef4444; cursor: pointer;
}
.ai-guide-input { display: flex; gap: 8px; padding: 10px 14px; border-top: 1px solid var(--color-border-light); flex-shrink: 0; }
.ai-guide-input input {
  flex: 1; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--color-border-light);
  background: var(--color-bg); font-size: 13px; color: var(--color-text); outline: none; font-family: inherit;
}
.ai-guide-input input:focus { border-color: var(--color-primary); }
.ai-guide-send-btn { padding: 6px 14px; border-radius: 8px; border: none; background: var(--color-primary); color: #fff; font-size: 13px; cursor: pointer; font-weight: 600; }
.typing-cursor { display: inline-block; width: 2px; height: 1em; background: var(--color-primary); margin-left: 1px; vertical-align: text-bottom; animation: guide-cursor-blink 0.8s infinite; }
@keyframes guide-cursor-blink { 0%,100% { opacity: 1 } 50% { opacity: 0 } }
</style>
