<template>
  <div v-if="diagnosis" class="diagnosis-panel" :class="borderClass">
    <div class="diagnosis-panel__header">
      <span class="diagnosis-panel__icon">{{ severityIcon }}</span>
      <span class="diagnosis-panel__title">AI 诊断</span>
      <span class="diagnosis-panel__severity" :class="severityClass">{{ severityLabel }}</span>
    </div>

    <div class="diagnosis-panel__cause">
      <strong>根因：</strong>{{ diagnosis.cause }}
    </div>

    <div v-if="diagnosis.impact" class="diagnosis-panel__impact">
      <span class="diagnosis-panel__impact-icon">⚠️</span>
      <span>{{ diagnosis.impact }}</span>
    </div>

    <div v-if="diagnosis.suggestions?.length" class="diagnosis-panel__suggestions">
      <p class="diagnosis-panel__label">修复建议：</p>
      <ul>
        <li v-for="(s, i) in diagnosis.suggestions" :key="i">
          {{ s }}
          <button
            v-if="diagnosis.step && diagnosis.step > 0"
            class="diagnosis-panel__goto"
            @click="$emit('gotoStep', diagnosis.step)"
          >
            前往修复
          </button>
        </li>
      </ul>
    </div>

    <slot name="actions" />

    <!-- Anomaly visualization -->
    <AnomalyChart v-if="anomalies?.length" :anomalies="anomalies" :stats="anomalyStats" />

    <div v-if="!hideAutofix" class="diagnosis-panel__autofix">
      <button
        class="diagnosis-panel__autofix-btn"
        :disabled="autofixLoading"
        @click="$emit('autofix')"
      >
        {{ autofixLoading ? 'AI 修复中...' : '✨ AI 自动修复' }}
      </button>
      <button
        class="diagnosis-panel__rewrite-btn"
        :disabled="rewriteLoading"
        @click="$emit('aiRewrite')"
      >
        {{ rewriteLoading ? 'AI 重写中...' : '🔄 让 AI 帮我重写' }}
      </button>
      <button
        class="diagnosis-panel__chat-btn"
        @click="showChat = !showChat"
      >
        {{ showChat ? '收起对话' : '💬 继续对话' }}
      </button>
    </div>

    <!-- Inline chat for follow-up questions -->
    <div v-if="showChat" class="diagnosis-panel__chat">
      <div v-if="chatMessages.length" class="diagnosis-panel__chat-messages">
        <div
          v-for="(msg, i) in chatMessages"
          :key="i"
          class="diagnosis-panel__chat-msg"
          :class="'diagnosis-panel__chat-msg--' + msg.role"
        >
          <span class="diagnosis-panel__chat-role">{{ msg.role === 'user' ? '我' : 'AI' }}</span>
          <span class="diagnosis-panel__chat-text">{{ msg.content }}</span>
        </div>
      </div>
      <div class="diagnosis-panel__chat-input">
        <input
          v-model="chatInput"
          placeholder="追问诊断结果，例如：这个错误怎么避免？"
          class="diagnosis-panel__chat-field"
          @keydown.enter="sendChat"
        />
        <button
          class="diagnosis-panel__chat-send"
          :disabled="!chatInput.trim() || chatLoading"
          @click="sendChat"
        >
          {{ chatLoading ? '...' : '发送' }}
        </button>
      </div>
    </div>

    <!-- Autofix result -->
    <div v-if="autofixResult" class="diagnosis-panel__fixes">
      <template v-if="autofixResult.fixable && autofixResult.fixes?.length">
        <p class="diagnosis-panel__label">AI 建议的修复：</p>
        <div v-for="(fix, i) in autofixResult.fixes" :key="i" class="diagnosis-panel__fix">
          <div class="diagnosis-panel__fix-header">
            <span>步骤 {{ fix.step }} · {{ fix.field }}</span>
            <span class="diagnosis-panel__fix-reason">{{ fix.reason }}</span>
          </div>
          <div class="diagnosis-panel__diff">
            <div class="diagnosis-panel__diff-old"><code>- {{ fix.old }}</code></div>
            <div class="diagnosis-panel__diff-new"><code>+ {{ fix.new }}</code></div>
          </div>
        </div>
        <button class="diagnosis-panel__apply-btn" @click="$emit('applyFixes', autofixResult.fixes)">
          应用修复
        </button>
      </template>
      <template v-else-if="autofixResult.fixable && !autofixResult.fixes?.length">
        <p class="diagnosis-panel__label">AI 认为可以修复，但未生成具体修复方案。</p>
      </template>
      <template v-else>
        <p class="diagnosis-panel__label">此问题较复杂，无法自动修复。建议：</p>
        <ul v-if="autofixResult.suggestions?.length">
          <li v-for="(s, i) in autofixResult.suggestions" :key="i">{{ s }}</li>
        </ul>
        <p v-else class="diagnosis-panel__label">暂无修复建议，请手动检查配置。</p>
      </template>
    </div>

    <!-- Technical detail (collapsed by default) -->
    <div v-if="rawError" class="diagnosis-panel__tech">
      <button class="diagnosis-panel__tech-toggle" @click="showTechDetail = !showTechDetail">
        {{ showTechDetail ? '▼ 技术详情' : '▶ 查看技术详情' }}
      </button>
      <div v-if="showTechDetail" class="diagnosis-panel__tech-content">
        <code>{{ rawError }}</code>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAiApi } from '../../composables/useAiApi'
import AnomalyChart from './AnomalyChart.vue'

interface Diagnosis {
  cause: string
  impact?: string
  suggestions: string[]
  severity: 'error' | 'warning'
  step?: number
}

interface AutofixFix {
  step: number
  field: string
  old: string
  new: string
  reason: string
}

interface AutofixResult {
  fixable: boolean
  fixes?: AutofixFix[]
  suggestions?: string[]
}

interface AnomalyItem {
  type: string
  column: string
  detail: string
  severity: 'error' | 'warning' | 'info'
}

const props = defineProps<{
  diagnosis: Diagnosis | null
  hideAutofix?: boolean
  autofixLoading?: boolean
  autofixResult?: AutofixResult | null
  rawError?: string
  rewriteLoading?: boolean
  anomalies?: AnomalyItem[]
  anomalyStats?: Record<string, Record<string, number>>
}>()
defineEmits<{
  gotoStep: [step: number]
  autofix: []
  applyFixes: [fixes: AutofixFix[]]
  aiRewrite: []
}>()

const showTechDetail = ref(false)
const showChat = ref(false)
const chatInput = ref('')
const chatLoading = ref(false)
const chatMessages = ref<{ role: 'user' | 'ai'; content: string }[]>([])

const { askSuggestion } = useAiApi()

async function sendChat() {
  const msg = chatInput.value.trim()
  if (!msg || chatLoading.value) return
  chatMessages.value.push({ role: 'user', content: msg })
  chatInput.value = ''
  chatLoading.value = true
  try {
    const content = await askSuggestion('chat', {
      diagnosis_cause: props.diagnosis?.cause,
      diagnosis_suggestions: props.diagnosis?.suggestions,
      diagnosis_severity: props.diagnosis?.severity,
      error_message: props.rawError,
      user_question: msg,
    })
    chatMessages.value.push({ role: 'ai', content: content || '抱歉，暂时无法回答这个问题。' })
  } catch {
    chatMessages.value.push({ role: 'ai', content: '网络异常，请稍后再试。' })
  } finally {
    chatLoading.value = false
  }
}

const severityLabel = computed(() => {
  if (!props.diagnosis) return ''
  return props.diagnosis.severity === 'error' ? '严重' : '警告'
})

const severityIcon = computed(() => {
  if (!props.diagnosis) return ''
  return props.diagnosis.severity === 'error' ? '🔴' : '🟡'
})

const severityClass = computed(() => {
  if (!props.diagnosis) return ''
  return props.diagnosis.severity === 'error' ? 'diagnosis-panel__severity--error' : 'diagnosis-panel__severity--warning'
})

const borderClass = computed(() => {
  if (!props.diagnosis) return ''
  return props.diagnosis.severity === 'error' ? 'diagnosis-panel--error' : 'diagnosis-panel--warning'
})
</script>

<style scoped>
.diagnosis-panel {
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 12px;
}

.diagnosis-panel--error {
  border: 1px solid #ef4444;
  background: rgba(239, 68, 68, 0.05);
}

.diagnosis-panel--warning {
  border: 1px solid #f59e0b;
  background: rgba(245, 158, 11, 0.05);
}

:root.dark .diagnosis-panel--error {
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
}

:root.dark .diagnosis-panel--warning {
  border-color: #d97706;
  background: rgba(217, 119, 6, 0.1);
}

.diagnosis-panel__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.diagnosis-panel__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.diagnosis-panel__severity {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.diagnosis-panel__severity--error {
  background: #fecaca;
  color: #991b1b;
}

.diagnosis-panel__severity--warning {
  background: #fef3c7;
  color: #92400e;
}

:root.dark .diagnosis-panel__severity--error {
  background: rgba(220, 38, 38, 0.2);
  color: #fca5a5;
}

:root.dark .diagnosis-panel__severity--warning {
  background: rgba(217, 119, 6, 0.2);
  color: #fcd34d;
}

.diagnosis-panel__cause {
  font-size: 13px;
  color: var(--color-text);
  margin-bottom: 8px;
}

.diagnosis-panel__impact {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: #b45309;
  background: rgba(245, 158, 11, 0.08);
  border-radius: 4px;
  padding: 6px 10px;
  margin-bottom: 8px;
}

:root.dark .diagnosis-panel__impact {
  color: #fbbf24;
  background: rgba(217, 119, 6, 0.12);
}

.diagnosis-panel__impact-icon {
  flex-shrink: 0;
}

.diagnosis-panel__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin: 0 0 4px;
}

.diagnosis-panel__suggestions ul {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: var(--color-text);
}

.diagnosis-panel__suggestions li {
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.diagnosis-panel__goto {
  font-size: 11px;
  color: #0d9488;
  background: none;
  border: 1px solid #0d9488;
  border-radius: 4px;
  padding: 1px 8px;
  cursor: pointer;
  white-space: nowrap;
}

.diagnosis-panel__goto:hover {
  background: #0d9488;
  color: white;
}

.diagnosis-panel__autofix {
  margin-top: 10px;
}

.diagnosis-panel__autofix-btn {
  font-size: 12px;
  color: #0d9488;
  background: none;
  border: 1px dashed #0d9488;
  border-radius: 6px;
  padding: 4px 12px;
  cursor: pointer;
}

.diagnosis-panel__autofix-btn:hover:not(:disabled) {
  background: rgba(13, 148, 136, 0.1);
}

.diagnosis-panel__autofix-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.diagnosis-panel__rewrite-btn {
  font-size: 12px;
  color: #6366f1;
  background: none;
  border: 1px dashed #6366f1;
  border-radius: 6px;
  padding: 4px 12px;
  cursor: pointer;
  margin-left: 8px;
}

.diagnosis-panel__rewrite-btn:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.1);
}

.diagnosis-panel__rewrite-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.diagnosis-panel__fixes {
  margin-top: 10px;
  border-top: 1px solid var(--color-border-light);
  padding-top: 10px;
}

.diagnosis-panel__fix {
  margin-bottom: 8px;
  padding: 8px;
  background: var(--color-surface-hover);
  border-radius: 6px;
}

.diagnosis-panel__fix-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
  color: var(--color-text-secondary);
}

.diagnosis-panel__fix-reason {
  color: #0d9488;
}

.diagnosis-panel__diff {
  font-size: 12px;
}

.diagnosis-panel__diff-old {
  color: #ef4444;
}

.diagnosis-panel__diff-new {
  color: #22c55e;
}

.diagnosis-panel__diff code {
  font-family: monospace;
  font-size: 11px;
}

.diagnosis-panel__apply-btn {
  margin-top: 8px;
  font-size: 12px;
  color: white;
  background: #0d9488;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  cursor: pointer;
}

.diagnosis-panel__apply-btn:hover {
  background: #0f766e;
}

.diagnosis-panel__tech {
  margin-top: 10px;
  border-top: 1px solid var(--color-border-light);
  padding-top: 8px;
}

.diagnosis-panel__tech-toggle {
  font-size: 11px;
  color: var(--color-text-muted);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 0;
}

.diagnosis-panel__tech-toggle:hover {
  color: var(--color-text-secondary);
}

.diagnosis-panel__tech-content {
  margin-top: 6px;
  padding: 6px 8px;
  background: var(--color-surface-hover);
  border-radius: 4px;
  font-size: 11px;
  color: var(--color-text-muted);
  word-break: break-all;
}

.diagnosis-panel__tech-content code {
  font-family: monospace;
}

.diagnosis-panel__chat-btn {
  font-size: 12px;
  color: #0ea5e9;
  background: none;
  border: 1px dashed #0ea5e9;
  border-radius: 6px;
  padding: 4px 12px;
  cursor: pointer;
  margin-left: 8px;
}

.diagnosis-panel__chat-btn:hover {
  background: rgba(14, 165, 233, 0.1);
}

.diagnosis-panel__chat {
  margin-top: 10px;
  border-top: 1px solid var(--color-border-light);
  padding-top: 10px;
}

.diagnosis-panel__chat-messages {
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 8px;
}

.diagnosis-panel__chat-msg {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  line-height: 1.5;
}

.diagnosis-panel__chat-role {
  flex-shrink: 0;
  font-weight: 600;
  min-width: 24px;
}

.diagnosis-panel__chat-msg--user .diagnosis-panel__chat-role {
  color: #6366f1;
}

.diagnosis-panel__chat-msg--ai .diagnosis-panel__chat-role {
  color: #0d9488;
}

.diagnosis-panel__chat-text {
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.diagnosis-panel__chat-input {
  display: flex;
  gap: 6px;
}

.diagnosis-panel__chat-field {
  flex: 1;
  font-size: 12px;
  padding: 4px 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-surface);
  color: var(--color-text);
  outline: none;
}

.diagnosis-panel__chat-field:focus {
  border-color: #0ea5e9;
}

.diagnosis-panel__chat-send {
  font-size: 12px;
  color: white;
  background: #0ea5e9;
  border: none;
  border-radius: 4px;
  padding: 4px 12px;
  cursor: pointer;
  white-space: nowrap;
}

.diagnosis-panel__chat-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
