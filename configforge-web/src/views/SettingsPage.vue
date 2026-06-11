<template>
  <div class="settings">
    <!-- Nav bar -->
    <AppNavBar current-route="settings" />

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
            <p v-if="!form.enabled && !maskedKey" class="settings__guide">首次使用？配置 AI 提供商和 API Key 后即可启用智能辅助功能，如自动生成代码、列映射和场景描述。</p>

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
              <div class="settings__field-label-row">
                <label class="settings__field-label">Temperature</label>
                <span class="settings__field-value">{{ form.temperature }}</span>
              </div>
              <NSlider v-model:value="form.temperature" :min="0" :max="2" :step="0.1" />
            </div>

            <!-- Max Tokens -->
            <div class="settings__field">
              <label class="settings__field-label">Max Tokens</label>
              <NInputNumber v-model:value="form.max_tokens" :min="256" :max="65536" class="w-full" placeholder="最大令牌数" />
            </div>

            <div class="settings__divider" />

            <!-- Actions -->
            <div class="settings__actions">
              <NButton :loading="testing" @click="testConnection">保存并测试</NButton>
              <NButton type="primary" class="btn-primary" :loading="saving" @click="saveSettings">保存设置</NButton>
            </div>
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
import { NButton, NInput, NSelect, NSwitch, NSlider, NInputNumber, NTabs, NTabPane, useMessage } from 'naive-ui'
import ConnectionManager from '../components/common/ConnectionManager.vue'
import AppNavBar from '../components/common/AppNavBar.vue'

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
const message = useMessage()
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
  try {
    await saveSettings()
    const { ok, data } = await testAiConnection()
    if (ok && data) {
      message.success(`连接成功！${data.provider}/${data.model}，延迟 ${data.latency_ms}ms`)
    } else {
      message.error(data?.detail || '连接失败')
    }
  } catch (e) {
    message.error('网络请求失败')
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
  background: var(--color-surface-glass);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border-light);
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

.settings__field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.settings__field-label-row .settings__field-label {
  margin-bottom: 0;
}

.settings__field-value {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}

.settings__guide {
  margin: 8px 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  line-height: 1.5;
  padding: 8px 12px;
  background: var(--color-primary-bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-primary-border);
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
