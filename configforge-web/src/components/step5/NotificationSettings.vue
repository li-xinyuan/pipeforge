<template>
  <div class="notification-settings">
    <div class="flex items-center justify-between mb-3">
      <h4 class="text-sm font-semibold">推送设置</h4>
      <NButton size="small" type="primary" @click="showAddModal = true">+ 添加推送</NButton>
    </div>

    <!-- Config list -->
    <div v-if="loading" class="text-xs text-slate-400 dark:text-slate-500 text-center py-3">加载中...</div>
    <div v-else-if="!configs.length" class="text-xs text-slate-400 dark:text-slate-500 text-center py-3">
      暂无推送配置，点击"添加推送"创建
    </div>
    <div v-else class="space-y-2">
      <div
        v-for="cfg in configs"
        :key="cfg.id"
        class="border rounded-lg p-3 flex items-center gap-3"
        :class="cfg.enabled ? 'border-teal-200 dark:border-teal-800' : 'border-slate-200 dark:border-slate-700 opacity-60'"
      >
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium truncate">{{ cfg.name }}</span>
            <span class="text-xs px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
              {{ providerLabel(cfg.webhook_provider) }}
            </span>
            <span v-if="!cfg.enabled" class="text-xs text-slate-400">已禁用</span>
          </div>
          <div class="text-xs text-slate-400 dark:text-slate-500 truncate mt-0.5">{{ cfg.webhook_url }}</div>
        </div>
        <div class="flex items-center gap-1 flex-shrink-0">
          <NButton size="tiny" :title="cfg.enabled ? '禁用' : '启用'" @click="toggleEnabled(cfg)">
            {{ cfg.enabled ? '禁用' : '启用' }}
          </NButton>
          <NButton size="tiny" :disabled="testingId === cfg.id || !cfg.enabled" @click="testNotify(cfg)">
            {{ testingId === cfg.id ? '测试中...' : '测试' }}
          </NButton>
          <NButton size="tiny" @click="editConfig(cfg)">编辑</NButton>
          <NButton size="tiny" type="error" @click="confirmDelete(cfg)">删除</NButton>
        </div>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <div v-if="showAddModal || editingConfig" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="closeModal">
      <div class="bg-[var(--color-surface)] rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto p-5">
        <h3 class="text-base font-semibold mb-4">{{ editingConfig ? '编辑推送' : '添加推送' }}</h3>

        <div class="space-y-3">
          <!-- Name -->
          <div>
            <label class="block text-xs font-medium mb-1">名称 <span class="text-red-500">*</span></label>
            <input v-model="form.name" class="cf-input" placeholder="如：钉钉群机器人">
          </div>

          <!-- Type -->
          <div>
            <label class="block text-xs font-medium mb-1">类型</label>
            <select v-model="form.type" class="cf-input">
              <option value="webhook">Webhook</option>
              <option value="email">邮件</option>
            </select>
          </div>

          <!-- Webhook URL -->
          <div v-if="form.type === 'webhook'">
            <label class="block text-xs font-medium mb-1">Webhook URL <span class="text-red-500">*</span></label>
            <input v-model="form.webhook_url" class="cf-input" placeholder="https://oapi.dingtalk.com/robot/send?access_token=...">
          </div>

          <!-- Provider -->
          <div v-if="form.type === 'webhook'">
            <label class="block text-xs font-medium mb-1">推送平台</label>
            <select v-model="form.webhook_provider" class="cf-input">
              <option value="dingtalk">钉钉</option>
              <option value="wecom">企业微信</option>
              <option value="feishu">飞书</option>
              <option value="generic">通用 JSON</option>
            </select>
          </div>

          <!-- Email recipients -->
          <div v-if="form.type === 'email'">
            <label class="block text-xs font-medium mb-1">收件人 <span class="text-red-500">*</span></label>
            <input v-model="emailToText" class="cf-input" placeholder="admin@example.com, ops@example.com">
            <p class="text-xs text-slate-400 mt-1">多个收件人用逗号分隔</p>
          </div>

          <!-- Email subject template -->
          <div v-if="form.type === 'email'">
            <label class="block text-xs font-medium mb-1">邮件主题模板</label>
            <input v-model="form.email_subject_template" class="cf-input" placeholder="ConfigForge 执行通知: {status_text}">
            <p class="text-xs text-slate-400 mt-1">可用变量: {config_name}, {status}, {status_text}, {summary}</p>
          </div>

          <!-- SMTP hint -->
          <div v-if="form.type === 'email'" class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded p-2">
            邮件推送需要先配置 SMTP 服务器。
            <button class="underline font-medium ml-1" @click="showSmtpModal = true">立即配置 →</button>
          </div>

          <!-- Trigger conditions -->
          <div>
            <label class="block text-xs font-medium mb-1">触发条件</label>
            <div class="flex gap-4">
              <label class="flex items-center gap-1.5 text-xs">
                <input v-model="form.trigger_on_success" type="checkbox"> 执行成功时推送
              </label>
              <label class="flex items-center gap-1.5 text-xs">
                <input v-model="form.trigger_on_failure" type="checkbox"> 执行失败时推送
              </label>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-5">
          <NButton @click="closeModal">取消</NButton>
          <NButton type="primary" :disabled="!canSave" @click="saveConfig">
            {{ editingConfig ? '保存' : '创建' }}
          </NButton>
        </div>
      </div>
    </div>

    <!-- Inline SMTP settings modal -->
    <div v-if="showSmtpModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showSmtpModal = false">
      <div class="bg-[var(--color-surface)] rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-base font-semibold">配置 SMTP 邮件服务</h3>
          <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300" aria-label="关闭" @click="showSmtpModal = false">✕</button>
        </div>
        <div class="space-y-3">
          <div>
            <label class="block text-xs font-medium mb-1">SMTP 服务器</label>
            <input v-model="smtpForm.host" class="cf-input" placeholder="smtp.gmail.com">
          </div>
          <div>
            <label class="block text-xs font-medium mb-1">端口</label>
            <input v-model.number="smtpForm.port" type="number" class="cf-input" placeholder="587">
          </div>
          <div>
            <label class="block text-xs font-medium mb-1">用户名</label>
            <input v-model="smtpForm.user" class="cf-input" placeholder="your@gmail.com">
          </div>
          <div>
            <label class="block text-xs font-medium mb-1">密码 / 授权码</label>
            <input v-model="smtpForm.password" type="password" class="cf-input" placeholder="SMTP 密码或应用专用密码">
            <p v-if="smtpMaskedPwd" class="text-xs text-slate-400 mt-1">当前：{{ smtpMaskedPwd }}</p>
          </div>
          <div>
            <label class="block text-xs font-medium mb-1">发件人地址</label>
            <input v-model="smtpForm.sender" class="cf-input" placeholder="留空则使用用户名作为发件人">
          </div>
          <label class="flex items-center gap-2 text-xs">
            <input v-model="smtpForm.use_tls" type="checkbox"> 启用 TLS
          </label>
          <div class="flex gap-2 pt-2">
            <NButton size="small" :disabled="smtpSaving" @click="saveSmtpInline">
              {{ smtpSaving ? '保存中...' : '保存 SMTP 设置' }}
            </NButton>
            <NButton size="small" :disabled="smtpTesting" @click="testSmtpInline">
              {{ smtpTesting ? '测试中...' : '测试连接' }}
            </NButton>
          </div>
          <p v-if="smtpInlineMsg" class="text-xs" :class="smtpInlineOk ? 'text-green-600' : 'text-red-500'">{{ smtpInlineMsg }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed, watch } from 'vue'
import { NButton } from 'naive-ui'
import { useNotificationApi, type NotificationConfig } from '../../composables/useNotificationApi'
import { useApi } from '../../composables/useApi'

const { loading, listConfigs, createConfig, updateConfig, deleteConfig, testConfig } = useNotificationApi()

const configs = ref<NotificationConfig[]>([])
const showAddModal = ref(false)
const editingConfig = ref<NotificationConfig | null>(null)
const testingId = ref<string | null>(null)

const defaultForm: {
  name: string
  type: 'webhook' | 'email'
  webhook_url: string
  webhook_provider: 'dingtalk' | 'wecom' | 'feishu' | 'generic'
  trigger_on_success: boolean
  trigger_on_failure: boolean
  email_to: string[]
  email_subject_template: string
  email_body_template: string
} = {
  name: '',
  type: 'webhook',
  webhook_url: '',
  webhook_provider: 'dingtalk',
  trigger_on_success: true,
  trigger_on_failure: true,
  email_to: [],
  email_subject_template: '',
  email_body_template: '',
}

const form = reactive({ ...defaultForm })

// Reset type-specific fields when switching type
watch(() => form.type, (newType) => {
  if (newType === 'webhook') {
    form.email_to = []
    form.email_subject_template = ''
    form.email_body_template = ''
  } else {
    form.webhook_url = ''
    form.webhook_provider = 'dingtalk'
  }
})

// Computed for email_to text input (comma-separated string ↔ array)
const emailToText = computed({
  get: () => form.email_to.join(', '),
  set: (val: string) => {
    form.email_to = val.split(',').map(s => s.trim()).filter(Boolean)
  },
})

function providerLabel(provider: string): string {
  const map: Record<string, string> = { dingtalk: '钉钉', wecom: '企微', feishu: '飞书', generic: '通用', email: '邮件' }
  return map[provider] || provider
}

const canSave = computed(() => {
  if (!form.name) return false
  if (form.type === 'webhook') {
    if (!form.webhook_url) return false
    try { new URL(form.webhook_url) } catch { return false }
  }
  if (form.type === 'email' && !form.email_to.length) return false
  return true
})

async function loadConfigs() {
  configs.value = await listConfigs()
}

async function toggleEnabled(cfg: NotificationConfig) {
  await updateConfig(cfg.id, { enabled: !cfg.enabled })
  await loadConfigs()
}

async function testNotify(cfg: NotificationConfig) {
  testingId.value = cfg.id
  try {
    const result = await testConfig(cfg.id)
    alert(result.ok ? `测试推送成功 (${result.provider})` : `测试推送失败: ${result.message}`)
  } finally {
    testingId.value = null
  }
}

function editConfig(cfg: NotificationConfig) {
  editingConfig.value = cfg
  Object.assign(form, {
    name: cfg.name,
    type: cfg.type,
    webhook_url: cfg.webhook_url,
    webhook_provider: cfg.webhook_provider,
    trigger_on_success: cfg.trigger_on_success,
    trigger_on_failure: cfg.trigger_on_failure,
    email_to: cfg.email_to || [],
    email_subject_template: cfg.email_subject_template || '',
    email_body_template: cfg.email_body_template || '',
  })
}

async function confirmDelete(cfg: NotificationConfig) {
  if (!confirm(`确定删除推送配置"${cfg.name}"？`)) return
  await deleteConfig(cfg.id)
  await loadConfigs()
}

async function saveConfig() {
  try {
    if (editingConfig.value) {
      await updateConfig(editingConfig.value.id, { ...form })
    } else {
      await createConfig({ ...form })
    }
    closeModal()
    await loadConfigs()
  } catch {
    alert('保存失败，请重试')
  }
}

function closeModal() {
  showAddModal.value = false
  editingConfig.value = null
  Object.assign(form, defaultForm)
}

onMounted(loadConfigs)

// ─── Inline SMTP Settings ─────────────────────────────────
const { request: smtpRequest } = useApi()
const showSmtpModal = ref(false)
const smtpSaving = ref(false)
const smtpTesting = ref(false)
const smtpInlineMsg = ref('')
const smtpInlineOk = ref(false)
const smtpMaskedPwd = ref('')

const smtpForm = reactive({
  host: '', port: 587, user: '', password: '', sender: '', use_tls: true,
})

// Load SMTP settings when modal opens
watch(showSmtpModal, async (visible) => {
  if (visible) {
    smtpInlineMsg.value = ''
    const data = await smtpRequest<Record<string, unknown>>('GET', '/api/notifications/smtp-settings')
    if (data) {
      smtpForm.host = (data.host as string) || ''
      smtpForm.port = (data.port as number) ?? 587
      smtpForm.user = (data.user as string) || ''
      smtpForm.sender = (data.sender as string) || ''
      smtpForm.use_tls = (data.use_tls as boolean) ?? true
      smtpForm.password = ''
      smtpMaskedPwd.value = (data.password as string) || ''
    }
  }
})

async function saveSmtpInline() {
  smtpSaving.value = true
  smtpInlineMsg.value = ''
  try {
    const body: Record<string, unknown> = { ...smtpForm }
    if (!body.password) body.password = null
    const result = await smtpRequest<Record<string, unknown>>('PUT', '/api/notifications/smtp-settings', body)
    if (result) {
      smtpInlineOk.value = true
      smtpInlineMsg.value = 'SMTP 设置已保存'
      smtpMaskedPwd.value = (result.password as string) || ''
      smtpForm.password = ''
    } else {
      smtpInlineOk.value = false
      smtpInlineMsg.value = '保存失败'
    }
  } catch {
    smtpInlineOk.value = false
    smtpInlineMsg.value = '保存失败'
  } finally {
    smtpSaving.value = false
  }
}

async function testSmtpInline() {
  smtpTesting.value = true
  smtpInlineMsg.value = ''
  try {
    await saveSmtpInline()
    const result = await smtpRequest<Record<string, unknown>>('POST', '/api/notifications/smtp-test')
    if (result) {
      smtpInlineOk.value = !!result.success
      smtpInlineMsg.value = (result.message as string) || '测试完成'
    } else {
      smtpInlineOk.value = false
      smtpInlineMsg.value = '测试失败'
    }
  } catch {
    smtpInlineOk.value = false
    smtpInlineMsg.value = '测试失败'
  } finally {
    smtpTesting.value = false
  }
}
</script>
