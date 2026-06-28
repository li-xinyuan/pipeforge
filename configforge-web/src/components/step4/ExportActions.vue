<template>
  <ConfettiBurst ref="confettiRef" />
  <div class="flex gap-2">
    <NButton @click="copyYaml">复制</NButton>
    <NButton @click="downloadYaml">下载 YAML</NButton>
    <NButton type="primary" class="btn-primary" :loading="executing" @click="downloadResult">下载结果文件</NButton>
    <NButton :loading="saving" @click="saveConfigHandler">保存配置</NButton>
  </div>

  <!-- Execution progress panel -->
  <div v-if="executionStage" class="export-actions__progress">
    <div class="flex items-center gap-3 mb-2">
      <NSpin v-if="executing" :size="16" />
      <span v-else-if="execError" class="text-red-500 text-base">&#10060;</span>
      <span v-else class="text-green-500 text-base">&#9989;</span>
      <span class="text-sm font-medium">{{ executionMessage }}</span>
    </div>
    <NProgress
      :percentage="executionProgress"
      :status="execError ? 'error' : undefined"
      :show-indicator="false"
      :height="6"
      :border-radius="3"
    />
    <div class="flex justify-between mt-1">
      <span
        v-for="s in stageSteps"
        :key="s.key"
        class="text-xs"
        :class="stageStepClass(s.key)"
      >{{ s.label }}</span>
    </div>
  </div>

  <!-- AI Diagnosis on execution failure -->
  <div v-if="execError || execDiagnosis" class="export-actions__diagnosis">
    <DiagnosisPanel
      v-if="execDiagnosis"
      :diagnosis="execDiagnosis"
      :autofix-loading="autofixLoading"
      :autofix-result="autofixResult"
      :raw-error="execError"
      :rewrite-loading="rewriteLoading"
      @goto-step="$emit('gotoStep', $event)"
      @autofix="onAutofix"
      @apply-fixes="onApplyFixes"
      @ai-rewrite="onAiRewrite"
    />
    <p v-else class="text-xs text-red-500">{{ execError }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NProgress, NSpin, useMessage, useDialog } from 'naive-ui'
import type { ExcelOutputConfig, CsvOutputConfig } from '../../types/wizard'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi } from '../../composables/useWizardApi'
import { useConfigApi } from '../../composables/useConfigApi'
import { useAiApi } from '../../composables/useAiApi'
import { useAuthStore } from '../../stores/auth'
import { stateToSnakeCase } from '../../utils/serialization'
import ConfettiBurst from '../ConfettiBurst.vue'
import DiagnosisPanel from '../common/DiagnosisPanel.vue'

defineEmits<{ gotoStep: [step: number] }>()

const props = defineProps<{ yaml?: string }>()
const message = useMessage()
const dialog = useDialog()
const router = useRouter()
const store = useWizardStore()
const { error: _apiError } = useWizardApi()
const { saveConfig } = useConfigApi()
const { askSuggestion } = useAiApi()
const executing = ref(false)
const saving = ref(false)
const confettiRef = ref<InstanceType<typeof ConfettiBurst>>()

// SSE execution progress state
type ExecutionStage = 'input' | 'processor' | 'output' | 'complete' | 'error' | ''
const executionStage = ref<ExecutionStage>('')
const executionProgress = ref(0)
const executionMessage = ref('')

const stageSteps = [
  { key: 'input', label: '输入' },
  { key: 'processor', label: '处理' },
  { key: 'output', label: '输出' },
] as const

function stageStepClass(key: string): string {
  const order = ['input', 'processor', 'output']
  const currentIdx = order.indexOf(executionStage.value)
  const stepIdx = order.indexOf(key)
  if (stepIdx < currentIdx) return 'text-green-500'
  if (stepIdx === currentIdx) return 'text-blue-500 font-semibold'
  return 'text-gray-400'
}

// AI diagnosis state
const execError = ref('')
const execDiagnosis = ref<{ cause: string; impact?: string; suggestions: string[]; severity: 'error' | 'warning'; step?: number } | null>(null)
const autofixLoading = ref(false)
const autofixResult = ref<{ fixable: boolean; fixes?: { step: number; field: string; old: string; new: string; reason: string }[]; suggestions?: string[] } | null>(null)
const rewriteLoading = ref(false)

function buildExecutionFilename(storedFilename: string): string {
  const now = new Date()
  const ts = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
  const ext = storedFilename.includes('.') ? storedFilename.split('.').pop()! : 'xlsx'
  const base = safeSceneName()
  return `${base}_${ts}.${ext}`
}

function safeSceneName(): string {
  return store.scene.name.replace(/[/\\:*?"<>|]/g, '-').trim() || 'output'
}

async function copyYaml() {
  if (!props.yaml) return
  await navigator.clipboard.writeText(props.yaml)
  message.success('已复制到剪贴板')
}

function downloadYaml() {
  if (!props.yaml) return
  const blob = new Blob([props.yaml], { type: 'text/yaml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const name = store.scene.name.trim() || 'pipeline'
  a.href = url; a.download = `${name}_pipeline.yaml`; a.click()
  URL.revokeObjectURL(url)
}

/** Parse SSE text stream and yield events */
function parseSSEStream(reader: ReadableStreamDefaultReader<Uint8Array>) {
  const decoder = new TextDecoder()
  let buffer = ''

  return {
    async *[Symbol.asyncIterator]() {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // 兼容 \r\n 和 \n 两种行尾分隔符
        const lines = buffer.split(/\r?\n/)
        buffer = lines.pop() || ''

        let currentEvent = ''
        let currentData = ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            currentData = line.slice(6)
          } else if (line === '' && currentEvent) {
            yield { event: currentEvent, data: currentData }
            currentEvent = ''
            currentData = ''
          }
        }
      }
    },
  }
}

/** Execute pipeline with SSE progress streaming */
async function downloadResultWithProgress() {
  const state = store.getWizardState()
  const auth = useAuthStore()

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (auth.token) headers['Authorization'] = `Bearer ${auth.token}`

  // SSE 流式响应需要直接连接后端，避免 Vite proxy 缓冲导致前端收不到流数据
  const apiUrl = import.meta.env.DEV ? 'http://localhost:8000/api/wizard/execute/stream' : '/api/wizard/execute/stream'
  const response = await fetch(apiUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify({ state: stateToSnakeCase(state) }),
  })

  if (!response.ok) {
    // Fall back to non-streaming error handling
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const errBody = await response.json()
      // FastAPI 422 验证错误: detail 是数组 [{loc, msg, ...}]
      if (Array.isArray(errBody.detail)) {
        const msgs = errBody.detail.map((e: { loc?: unknown[]; msg?: string }) => `${(e.loc || []).join('.')}: ${e.msg || ''}`).join('; ')
        throw new Error(msgs || `执行失败 (${response.status})`)
      }
      throw new Error(errBody.detail || errBody.error || `执行失败 (${response.status})`)
    }
    throw new Error(`执行失败 (${response.status})`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('无法读取响应流')

  let lastCompleteData: Record<string, unknown> | null = null

  const sseStream = parseSSEStream(reader)
  for await (const { event, data } of sseStream) {
    let parsed: Record<string, unknown> | null = null
    try { parsed = JSON.parse(data) } catch { /* ignore */ }

    switch (event) {
      case 'start':
        executionStage.value = 'input'
        executionProgress.value = 5
        executionMessage.value = '准备执行...'
        break

      case 'input_start':
        executionStage.value = 'input'
        executionProgress.value = 10
        executionMessage.value = `读取输入：${parsed?.name || ''}`
        break

      case 'input_done':
        executionProgress.value = 30
        executionMessage.value = `输入完成：${parsed?.rows || 0} 行`
        break

      case 'processor_start':
        executionStage.value = 'processor'
        executionProgress.value = 40
        executionMessage.value = `执行处理：${parsed?.name || ''}`
        break

      case 'processor_done':
        executionProgress.value = 65
        executionMessage.value = `处理完成：${parsed?.name || ''}`
        break

      case 'output_start':
        executionStage.value = 'output'
        executionProgress.value = 75
        executionMessage.value = '写入输出...'
        break

      case 'output_done':
        executionProgress.value = 90
        executionMessage.value = `输出完成：${parsed?.rows || 0} 行`
        break

      case 'complete':
        executionStage.value = 'complete'
        executionProgress.value = 100
        executionMessage.value = '执行完成'
        lastCompleteData = parsed
        break

      case 'error':
        executionStage.value = 'error'
        executionMessage.value = '执行失败'
        if (parsed) {
          execError.value = (parsed.message as string) || '执行失败'
          if (parsed.diagnosis && typeof parsed.diagnosis === 'object') {
            execDiagnosis.value = parsed.diagnosis as { cause: string; impact?: string; suggestions: string[]; severity: 'error' | 'warning'; step?: number }
          }
          if (parsed.checks) {
            // Checkpoint failure
            execError.value = '数据检查点未通过'
          }
        }
        break
    }
  }

  return lastCompleteData
}

async function downloadResult() {
  // Validate config completeness before executing
  if (!store.inputs.length) {
    dialog.warning({ title: '配置不完整', content: '请先在步骤 2 添加输入源。', positiveText: '知道了' })
    return
  }
  if (!store.processors.length) {
    dialog.warning({ title: '配置不完整', content: '请先在步骤 3 添加处理步骤。', positiveText: '知道了' })
    return
  }
  if (!store.output) {
    dialog.warning({ title: '配置不完整', content: '请先在步骤 4 配置输出。', positiveText: '知道了' })
    return
  }

  // Check if any file-based input source is missing its uploaded file
  const missingFileInputs = store.inputs.filter(
    inp => inp.plugin !== 'database' && !inp.fileId
  )
  if (missingFileInputs.length > 0) {
    const names = missingFileInputs.map(inp => inp.table || inp.paramKey).join('、')
    dialog.warning({
      title: '文件需要重新上传',
      content: `以下输入源的文件未上传（编辑已保存的配置时，上传文件不会保留）：${names}。请返回第 2 步重新上传文件后再执行。`,
      positiveText: '知道了',
    })
    return
  }

  executing.value = true
  execError.value = ''
  execDiagnosis.value = null
  executionStage.value = ''
  executionProgress.value = 0
  executionMessage.value = ''

  try {
    // SSE 执行 pipeline 并返回 complete 事件的 data（含 exec_id 和 output_file_name）
    const completeData = await downloadResultWithProgress() as { exec_id?: string; output_file_name?: string } | null

    const stage = executionStage.value as ExecutionStage
    if (stage === 'complete' && !execError.value) {
      confettiRef.value?.burst()

      if (store.output?.plugin === 'database') {
        message.success('执行成功，数据已写入目标数据库')
      } else {
        // SSE 执行已生成结果文件（保存在 data/executions/{exec_id}/），
        // 通过 exec_id 下载已生成的文件，避免二次执行 pipeline
        const execId = completeData?.exec_id
        if (!execId) {
          throw new Error('执行完成但未返回 exec_id，无法下载结果文件')
        }
        const auth = useAuthStore()
        const downloadUrl = import.meta.env.DEV
          ? `http://localhost:8000/api/executions/${execId}/download`
          : `/api/executions/${execId}/download`
        const resp = await fetch(downloadUrl, {
          headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {},
        })
        if (!resp.ok) {
          const text = await resp.text().catch(() => '')
          throw new Error(text || `下载结果文件失败 (${resp.status})`)
        }
        const blob = await resp.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        const storedFilename = (store.output?.config as ExcelOutputConfig | CsvOutputConfig)?.filename || 'output.xlsx'
        a.href = url; a.download = buildExecutionFilename(storedFilename); a.click()
        URL.revokeObjectURL(url)
        message.success('结果文件下载成功')
      }
    }
  } catch (e: unknown) {
    execError.value = e instanceof Error ? e.message : '执行失败'
    executionStage.value = 'error'
    executionMessage.value = '执行失败'
    execDiagnosis.value = null
  } finally {
    executing.value = false
  }
}

async function saveConfigHandler() {
  saving.value = true
  try {
    const state = store.getWizardState()
    const id = await saveConfig(state, store.configId)
    if (id) {
      store.setConfigId(id)
      dialog.success({
        title: '保存成功',
        content: '配置已保存。是否跳转到首页？',
        positiveText: '去首页',
        negativeText: '留在当前页',
        onPositiveClick: () => { router.push('/') },
      })
    } else {
      message.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

async function onAutofix() {
  if (!execDiagnosis.value) return
  autofixLoading.value = true
  autofixResult.value = null
  try {
    const result = await askSuggestion('autofix', {
      diagnosis: JSON.stringify(execDiagnosis.value),
      errorLog: execError.value,
    })
    if (result) {
      try {
        autofixResult.value = JSON.parse(result)
      } catch {
        autofixResult.value = { fixable: false, suggestions: ['AI 返回了无法解析的结果'] }
      }
    } else {
      autofixResult.value = { fixable: false, suggestions: ['AI 未返回修复建议'] }
    }
  } catch {
    autofixResult.value = { fixable: false, suggestions: ['AI 修复请求失败'] }
  } finally {
    autofixLoading.value = false
  }
}

function onApplyFixes(fixes: { step: number; field: string; old: string; new: string; reason: string }[]) {
  if (fixes.length > 0) {
    store.applyAutofixes(fixes)
  }
  execError.value = ''
  execDiagnosis.value = null
  autofixResult.value = null
}

async function onAiRewrite() {
  if (!execDiagnosis.value) return
  rewriteLoading.value = true
  try {
    await askSuggestion('orchestrate', {
      currentStep: 3,
      naturalLanguage: `修复执行错误：${execDiagnosis.value.cause}。错误信息：${execError.value}`,
      inputs: store.inputs.map(i => ({ name: i.table, plugin: i.plugin })),
      processors: [{ plugin: 'sql', name: 'query' }],
      outputColumns: [],
    })
  } catch {
    // AI rewrite failed
  } finally {
    rewriteLoading.value = false
  }
}

defineExpose({
  saveConfigHandler,
  downloadResult,
})
</script>

<style scoped>
.export-actions__progress {
  margin-top: 12px;
  padding: 12px 16px;
  background: var(--n-color-modal, #f9fafb);
  border-radius: 8px;
  border: 1px solid var(--n-border-color, #e5e7eb);
}

.export-actions__diagnosis {
  margin-top: 12px;
}
</style>
