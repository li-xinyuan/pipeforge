<template>
  <div class="settings">
    <!-- Nav bar -->
    <header class="settings__nav">
      <div class="settings__nav-inner">
        <div class="settings__brand" @click="router.push('/')">
          <span class="settings__brand-icon">⚡</span>
          <span class="settings__brand-text">ConfigForge</span>
        </div>
        <nav class="settings__nav-links">
          <router-link to="/" class="settings__nav-link">首页</router-link>
          <span class="settings__nav-link settings__nav-link--active">设置</span>
        </nav>
        <button class="settings__theme-toggle" @click="toggleTheme" :title="isDark ? '切换到亮色模式' : '切换到暗色模式'">
          {{ isDark ? '☀' : '☾' }}
        </button>
      </div>
    </header>

    <!-- Page content -->
    <div class="settings__body">
      <h1 class="settings__title">设置</h1>

      <NTabs type="segment" animated>
        <NTabPane name="ai" tab="AI 模型">
          <div class="settings__card">
            <!-- Enable switch -->
            <div class="settings__row">
              <span class="settings__label">启用 AI</span>
              <NSwitch :value="form.enabled" @update:value="form.enabled = $event" />
            </div>

            <div class="settings__divider" />

            <!-- Provider -->
            <div class="settings__field">
              <label class="settings__field-label">提供商</label>
              <NSelect v-model:value="form.provider" :options="providerOptions" />
            </div>

            <!-- Model -->
            <div class="settings__field">
              <label class="settings__field-label">模型</label>
              <NInput v-model:value="form.model" :placeholder="defaultModel" />
              <p class="settings__hint">留空使用默认：{{ defaultModel }}</p>
            </div>

            <!-- API Key -->
            <div class="settings__field">
              <label class="settings__field-label">API Key</label>
              <NInput v-model:value="form.api_key" type="password" placeholder="sk-..." show-password-toggle />
              <p v-if="maskedKey" class="settings__hint">当前：{{ maskedKey }}</p>
            </div>

            <!-- Base URL -->
            <div class="settings__field">
              <label class="settings__field-label">Base URL</label>
              <NInput v-model:value="form.base_url" :placeholder="form.provider === 'openai' ? 'https://api.openai.com/v1（默认）' : '必填'" />
            </div>

            <!-- Temperature -->
            <div class="settings__field">
              <label class="settings__field-label">Temperature: {{ form.temperature }}</label>
              <NSlider v-model:value="form.temperature" :min="0" :max="2" :step="0.1" />
            </div>

            <!-- Max Tokens -->
            <div class="settings__field">
              <label class="settings__field-label">Max Tokens</label>
              <NInputNumber v-model:value="form.max_tokens" :min="256" :max="65536" class="w-full" />
            </div>

            <div class="settings__divider" />

            <!-- Actions -->
            <div class="settings__actions">
              <NButton :loading="testing" @click="testConnection">测试连接</NButton>
              <NButton type="primary" class="btn-primary" :loading="saving" @click="saveSettings">保存设置</NButton>
            </div>
            <p v-if="testResult" class="settings__result" :class="testResult.ok ? 'settings__result--ok' : 'settings__result--error'">
              {{ testResult.msg }}
            </p>
            <p v-if="saveMsg" class="settings__result settings__result--ok">{{ saveMsg }}</p>
          </div>
        </NTabPane>

        <NTabPane name="database" tab="数据库连接">
          <div class="settings__card">
            <ConnectionManager />
          </div>
        </NTabPane>
      </NTabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAiApi } from '../composables/useWizardApi'
import { useTheme } from '../composables/useTheme'
import { NButton, NInput, NSelect, NSwitch, NSlider, NInputNumber, NTabs, NTabPane } from 'naive-ui'
import ConnectionManager from '../components/common/ConnectionManager.vue'

interface AiSettingsForm {
  provider: string
  api_key: string
  base_url: string
  model: string
  temperature: number
  max_tokens: number
  enabled: boolean
}

const router = useRouter()
const { isDark, toggleTheme } = useTheme()
const { getAiSettings, updateAiSettings, testAiConnection } = useAiApi()

const form = reactive<AiSettingsForm>({
  provider: 'openai', api_key: '', base_url: '', model: '',
  temperature: 0.7, max_tokens: 4096, enabled: false,
})

const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Custom (OpenAI-compatible)', value: 'custom' },
]

const maskedKey = ref('')
const testing = ref(false)
const saving = ref(false)
const testResult = ref<{ ok: boolean; msg: string } | null>(null)
const saveMsg = ref('')

const defaultModel = computed(() => {
  if (form.provider === 'anthropic') return 'claude-sonnet-4-6'
  return 'gpt-4o'
})

onMounted(async () => {
  const data = await getAiSettings()
  if (data) {
    form.provider = data.provider
    form.base_url = data.base_url
    form.model = data.model
    form.temperature = data.temperature
    form.max_tokens = data.max_tokens
    form.enabled = data.enabled
    maskedKey.value = data.api_key
  }
})

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    await saveSettings()
    const { ok, data } = await testAiConnection()
    if (ok && data) {
      testResult.value = { ok: true, msg: `连接成功！${data.provider}/${data.model}，延迟 ${data.latency_ms}ms` }
    } else {
      testResult.value = { ok: false, msg: data?.detail || '连接失败' }
    }
  } catch (e) {
    testResult.value = { ok: false, msg: '网络请求失败' }
  } finally {
    testing.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveMsg.value = ''
  try {
    const body: Record<string, any> = { ...form }
    if (!body.api_key) body.api_key = null
    const ok = await updateAiSettings(body)
    if (ok) {
      saveMsg.value = '设置已保存'
      const data = await getAiSettings()
      if (data) maskedKey.value = data.api_key
      setTimeout(() => saveMsg.value = '', 3000)
    }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* Nav bar — same as HomeView */
.settings__nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border-light);
}

[data-theme="dark"] .settings__nav {
  background: rgba(10, 28, 20, 0.72);
}

.settings__nav-inner {
  max-width: 960px;
  margin: 0 auto;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.settings__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.settings__brand-icon {
  font-size: 20px;
}

.settings__brand-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.02em;
}

.settings__nav-links {
  display: flex;
  align-items: center;
  gap: 24px;
}

.settings__nav-link {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  cursor: pointer;
  text-decoration: none;
  transition: color 0.2s;
}

.settings__nav-link:hover {
  color: var(--color-text);
}

.settings__nav-link--active {
  color: var(--color-primary);
  font-weight: 600;
}

.settings__theme-toggle {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border-light);
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  color: var(--color-text-muted);
  transition: all 0.2s;
}

.settings__theme-toggle:hover {
  border-color: var(--color-border);
  color: var(--color-text);
}

/* Page body */
.settings__body {
  max-width: 600px;
  margin: 0 auto;
  padding: 40px 24px 80px;
}

.settings__title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 24px;
}

/* Card */
.settings__card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  padding: var(--space-card-padding);
  box-shadow: var(--shadow-md);
}

.settings__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}

.settings__label {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
}

.settings__divider {
  height: 1px;
  background: var(--color-border-light);
  margin: 14px 0;
}

.settings__field {
  margin-bottom: 14px;
}

.settings__field:last-of-type {
  margin-bottom: 0;
}

.settings__field-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: 6px;
}

.settings__hint {
  margin: 4px 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.settings__actions {
  display: flex;
  gap: 10px;
  padding-top: 4px;
}

.settings__result {
  margin-top: 10px;
  font-size: var(--font-size-sm);
}

.settings__result--ok {
  color: var(--color-success);
}

.settings__result--error {
  color: var(--color-error);
}

/* Button overrides */
:deep(.btn-primary) {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light)) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 700 !important;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  box-shadow: var(--shadow-button) !important;
  border-radius: var(--radius-sm) !important;
}

:deep(.btn-primary:hover) {
  opacity: 0.92;
}

/* Responsive */
@media (max-width: 767px) {
  .settings__nav-inner {
    padding: 0 16px;
  }
  .settings__body {
    padding: 24px 16px 64px;
  }
  .settings__card {
    padding: 16px;
    border-radius: var(--radius-lg);
  }
  .settings__actions {
    flex-direction: column;
  }
}
</style>
