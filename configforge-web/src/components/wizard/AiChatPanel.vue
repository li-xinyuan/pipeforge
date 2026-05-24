<template>
  <aside v-if="visible" class="ai-panel" :class="`ai-panel--${mode || 'sidebar'}`" @click.self="onBackdropClick">
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
  mode?: 'sidebar' | 'overlay' | 'fullscreen'
  loading?: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
  quickAction: [action: string]
  toggle: []
  'orchestrate-confirm': [result: any]
  'orchestrate-regenerate': []
}>()

const currentMode = computed(() => props.mode || 'sidebar')

const inputText = ref('')
const messagesEl = ref<HTMLElement>()

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
</style>
