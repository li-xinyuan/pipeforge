<template>
  <div class="settings">
    <AppNavBar current-route="settings" />

    <!-- Page content -->
    <div class="settings__body">
      <h1 class="settings__title">设置</h1>

      <NTabs type="segment" animated>
        <NTabPane name="ai" tab="AI 模型">
          <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; padding: 12px; background: var(--color-primary-bg); border-radius: var(--radius-md); border: 1px solid var(--color-primary-border);">
            配置 AI 模型后，可在向导中使用 AI 辅助生成 SQL、自动列映射和场景描述等功能。
          </p>
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
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <label class="settings__field-label" style="margin-bottom: 0;">Temperature</label>
                <span style="font-size: var(--font-size-sm); font-weight: 600; color: var(--color-primary);">{{ form.temperature }}</span>
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
              <NButton :loading="testing" @click="testConnection">测试连接</NButton>
              <span style="font-size: var(--font-size-xs); color: var(--color-text-muted); margin-left: 8px;">测试前将自动保存当前设置</span>
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

        <NTabPane name="smtp" tab="邮件推送">
          <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; padding: 12px; background: var(--color-primary-bg); border-radius: var(--radius-md); border: 1px solid var(--color-primary-border);">
            配置 SMTP 邮件服务后，可在步骤 5 中添加邮件推送通知。
          </p>
          <div class="settings__card">
            <!-- Host -->
            <div class="settings__field">
              <label class="settings__field-label">SMTP 服务器</label>
              <NInput v-model:value="smtpForm.host" placeholder="smtp.gmail.com" />
            </div>

            <!-- Port -->
            <div class="settings__field">
              <label class="settings__field-label">端口</label>
              <NInputNumber v-model:value="smtpForm.port" :min="1" :max="65535" class="w-full" placeholder="587" />
            </div>

            <!-- User -->
            <div class="settings__field">
              <label class="settings__field-label">用户名</label>
              <NInput v-model:value="smtpForm.user" placeholder="your@gmail.com" />
            </div>

            <!-- Password -->
            <div class="settings__field">
              <label class="settings__field-label">密码 / 授权码</label>
              <NInput v-model:value="smtpForm.password" type="password" placeholder="SMTP 密码或应用专用密码" show-password-toggle />
              <p v-if="smtpMaskedPwd" class="settings__hint">当前：{{ smtpMaskedPwd }}</p>
            </div>

            <!-- Sender -->
            <div class="settings__field">
              <label class="settings__field-label">发件人地址</label>
              <NInput v-model:value="smtpForm.sender" placeholder="留空则使用用户名作为发件人" />
            </div>

            <!-- TLS -->
            <div class="settings__row">
              <span class="settings__label">启用 TLS</span>
              <NSwitch :value="smtpForm.use_tls" @update:value="smtpForm.use_tls = $event" />
            </div>

            <div class="settings__divider" />

            <!-- Actions -->
            <div class="settings__actions">
              <NButton :loading="smtpTesting" @click="testSmtpConnection">测试连接</NButton>
              <span style="font-size: var(--font-size-xs); color: var(--color-text-muted); margin-left: 8px;">测试前将自动保存当前设置</span>
              <NButton type="primary" class="btn-primary" :loading="smtpSaving" @click="saveSmtpSettings">保存设置</NButton>
            </div>
            <p v-if="smtpTestResult" class="settings__result" :class="smtpTestResult.ok ? 'settings__result--ok' : 'settings__result--error'">
              {{ smtpTestResult.msg }}
            </p>
            <p v-if="smtpSaveMsg" class="settings__result settings__result--ok">{{ smtpSaveMsg }}</p>
          </div>
        </NTabPane>
      </NTabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue'
import { useAiApi } from '../composables/useWizardApi'
import { useApi } from '../composables/useApi'
import { NButton, NInput, NSelect, NSwitch, NSlider, NInputNumber, NTabs, NTabPane, useMessage } from 'naive-ui'
import AppNavBar from '../components/common/AppNavBar.vue'
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

const { getAiSettings, updateAiSettings, testAiConnection } = useAiApi()
const message = useMessage()

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

interface AiTestResponse {
  provider?: string
  model?: string
  latency_ms?: number
  detail?: string
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    await saveSettings()
    const { ok, data } = await testAiConnection()
    if (ok && data) {
      const resp = data as AiTestResponse
      const msg = `连接成功！${resp.provider}/${resp.model}，延迟 ${resp.latency_ms}ms`
      testResult.value = { ok: true, msg }
      message.success(msg)
    } else {
      const resp = data as AiTestResponse | null
      const msg = resp?.detail || '连接失败'
      testResult.value = { ok: false, msg }
      message.error(msg)
    }
  } catch (e) {
    const msg = '网络请求失败'
    testResult.value = { ok: false, msg }
    message.error(msg)
  } finally {
    testing.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveMsg.value = ''
  try {
    const body: Record<string, unknown> = { ...form }
    if (!body.api_key) body.api_key = null
    const ok = await updateAiSettings(body)
    if (ok) {
      saveMsg.value = '设置已保存'
      const data = await getAiSettings()
      if (data) maskedKey.value = data.api_key as string
      setTimeout(() => saveMsg.value = '', 3000)
    }
  } finally {
    saving.value = false
  }
}

// ─── SMTP Settings ───────────────────────────────────────
const { request: smtpRequest } = useApi()

interface SmtpSettingsForm {
  host: string
  port: number | null
  user: string
  password: string
  sender: string
  use_tls: boolean
}

const smtpForm = reactive<SmtpSettingsForm>({
  host: '', port: 587, user: '', password: '', sender: '', use_tls: true,
})

const smtpMaskedPwd = ref('')
const smtpTesting = ref(false)
const smtpSaving = ref(false)
const smtpTestResult = ref<{ ok: boolean; msg: string } | null>(null)
const smtpSaveMsg = ref('')

onMounted(async () => {
  // Load AI settings
  const data = await getAiSettings()
  if (data) {
    form.provider = data.provider as string
    form.base_url = data.base_url as string
    form.model = data.model as string
    form.temperature = data.temperature as number
    form.max_tokens = data.max_tokens as number
    form.enabled = data.enabled as boolean
    maskedKey.value = data.api_key as string
  }

  // Load SMTP settings
  const smtpData = await smtpRequest<Record<string, any>>('GET', '/api/notifications/smtp-settings')
  if (smtpData) {
    smtpForm.host = (smtpData.host as string) || ''
    smtpForm.port = (smtpData.port as number) ?? 587
    smtpForm.user = (smtpData.user as string) || ''
    smtpForm.sender = (smtpData.sender as string) || ''
    smtpForm.use_tls = (smtpData.use_tls as boolean) ?? true
    smtpMaskedPwd.value = (smtpData.password as string) || ''
  }
})

async function saveSmtpSettings() {
  smtpSaving.value = true
  smtpSaveMsg.value = ''
  try {
    const body: Record<string, any> = { ...smtpForm }
    if (!body.password) body.password = null
    const result = await smtpRequest<Record<string, any>>('PUT', '/api/notifications/smtp-settings', body)
    if (result) {
      smtpSaveMsg.value = 'SMTP 设置已保存'
      smtpMaskedPwd.value = (result.password as string) || ''
      setTimeout(() => smtpSaveMsg.value = '', 3000)
    }
  } finally {
    smtpSaving.value = false
  }
}

async function testSmtpConnection() {
  smtpTesting.value = true
  smtpTestResult.value = null
  try {
    await saveSmtpSettings()
    const result = await smtpRequest<Record<string, any>>('POST', '/api/notifications/smtp-test')
    if (result) {
      smtpTestResult.value = { ok: !!result.success, msg: (result.message as string) || '测试完成' }
    } else {
      smtpTestResult.value = { ok: false, msg: '测试失败' }
    }
  } catch {
    smtpTestResult.value = { ok: false, msg: '网络请求失败' }
  } finally {
    smtpTesting.value = false
  }
}
</script>

<style scoped>
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

/* Responsive */
@media (max-width: 767px) {
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
