<template>
  <div class="max-w-2xl mx-auto py-8 px-4">
    <h1 class="text-2xl font-bold text-slate-900 mb-6">AI 设置</h1>

    <div class="bg-white border border-slate-200 rounded-lg p-6 space-y-5">
      <!-- Enable switch -->
      <div class="flex items-center justify-between">
        <label class="text-sm font-medium text-slate-900">启用 AI</label>
        <button
          @click="form.enabled = !form.enabled"
          :class="form.enabled ? 'bg-blue-600' : 'bg-slate-300'"
          class="relative w-11 h-6 rounded-full transition-colors"
        >
          <span :class="form.enabled ? 'translate-x-5' : 'translate-x-0.5'" class="inline-block w-5 h-5 bg-white rounded-full shadow transition-transform translate-y-0.5" />
        </button>
      </div>

      <!-- Provider -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">提供商</label>
        <select v-model="form.provider" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none bg-white">
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="custom">Custom (OpenAI-compatible)</option>
        </select>
      </div>

      <!-- Model -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">模型</label>
        <input v-model="form.model" :placeholder="defaultModel" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
        <p class="text-xs text-slate-400 mt-1">留空使用默认：{{ defaultModel }}</p>
      </div>

      <!-- API Key -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">API Key</label>
        <input v-model="form.api_key" type="password" placeholder="sk-..." class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
        <p v-if="maskedKey" class="text-xs text-slate-400 mt-1">当前：{{ maskedKey }}</p>
      </div>

      <!-- Base URL -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">Base URL</label>
        <input v-model="form.base_url" :placeholder="form.provider === 'openai' ? 'https://api.openai.com/v1（默认）' : '必填'" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
      </div>

      <!-- Temperature -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">Temperature: {{ form.temperature }}</label>
        <input v-model.number="form.temperature" type="range" min="0" max="2" step="0.1" class="w-full" />
      </div>

      <!-- Max Tokens -->
      <div>
        <label class="block text-sm font-medium text-slate-900 mb-1">Max Tokens</label>
        <input v-model.number="form.max_tokens" type="number" min="256" max="65536" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-md focus:border-blue-600 outline-none" />
      </div>

      <!-- Actions -->
      <div class="flex gap-3 pt-2">
        <button @click="testConnection" :disabled="testing" class="px-4 py-2 text-sm font-medium border border-slate-200 rounded-md hover:bg-slate-50 disabled:opacity-50">{{ testing ? '测试中...' : '测试连接' }}</button>
        <button @click="saveSettings" :disabled="saving" class="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50">{{ saving ? '保存中...' : '保存设置' }}</button>
      </div>
      <p v-if="testResult" :class="testResult.ok ? 'text-green-600' : 'text-red-500'" class="text-sm">{{ testResult.msg }}</p>
      <p v-if="saveMsg" class="text-sm text-green-600">{{ saveMsg }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue'
import { useAiApi } from '../composables/useWizardApi'

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

const form = reactive<AiSettingsForm>({
  provider: 'openai', api_key: '', base_url: '', model: '',
  temperature: 0.7, max_tokens: 4096, enabled: false,
})

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
    // 输入框为空 → 发送 null 表示保留已有 Key
    if (!body.api_key) body.api_key = null
    const ok = await updateAiSettings(body)
    if (ok) {
      saveMsg.value = '设置已保存'
      // 重新加载脱敏 Key
      const data = await getAiSettings()
      if (data) maskedKey.value = data.api_key
      setTimeout(() => saveMsg.value = '', 3000)
    }
  } finally {
    saving.value = false
  }
}
</script>
