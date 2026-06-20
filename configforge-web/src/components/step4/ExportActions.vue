<template>
  <ConfettiBurst ref="confettiRef" />
  <div class="flex gap-2">
    <NButton @click="copyYaml">复制</NButton>
    <NButton @click="downloadYaml">下载 YAML</NButton>
    <NButton type="primary" class="btn-primary" :loading="executing" @click="downloadResult">下载结果文件</NButton>
    <NButton :loading="saving" @click="saveConfigHandler">保存配置</NButton>
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
import { NButton, useMessage, useDialog } from 'naive-ui'
import type { ExcelOutputConfig, CsvOutputConfig, DatabaseOutputConfig } from '../../types/wizard'
import { useWizardStore } from '../../stores/wizard'
import { useWizardApi } from '../../composables/useWizardApi'
import { useConfigApi } from '../../composables/useConfigApi'
import { useAiApi } from '../../composables/useAiApi'
import ConfettiBurst from '../ConfettiBurst.vue'
import DiagnosisPanel from '../common/DiagnosisPanel.vue'

defineEmits<{ gotoStep: [step: number] }>()

const props = defineProps<{ yaml?: string }>()
const message = useMessage()
const dialog = useDialog()
const router = useRouter()
const store = useWizardStore()
const { executePipeline, error: apiError } = useWizardApi()
const { saveConfig } = useConfigApi()
const { askSuggestion } = useAiApi()
const executing = ref(false)
const saving = ref(false)
const confettiRef = ref<InstanceType<typeof ConfettiBurst>>()

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
  return store.scene.name.replace(/[\/\\:*?"<>|]/g, '-').trim() || 'output'
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
  try {
    const state = store.getWizardState()
    const result = await executePipeline(state)
    if (result) {
      if (result instanceof Blob) {
        const url = URL.createObjectURL(result)
        const a = document.createElement('a')
        const storedFilename = (store.output?.plugin !== 'database' ? (store.output?.config as ExcelOutputConfig | CsvOutputConfig)?.filename : '') || 'output.xlsx'
        a.href = url; a.download = buildExecutionFilename(storedFilename); a.click()
        URL.revokeObjectURL(url)
        confettiRef.value?.burst()
        message.success('结果文件下载成功')
      } else {
        // Database output: JSON response with success message
        confettiRef.value?.burst()
        message.success(result.message || '执行成功')
      }
    } else {
      execError.value = apiError.value?.message || '执行失败，请检查配置'
      // Try to extract diagnosis from API error
      const errData = apiError.value?.data as Record<string, unknown> | undefined
      if (errData && typeof errData.diagnosis === 'object' && errData.diagnosis) {
        const diag = errData.diagnosis as { cause: string; impact?: string; suggestions: string[]; severity: 'error' | 'warning'; step?: number }
        execDiagnosis.value = diag
      }
    }
  } catch (e: unknown) {
    execError.value = e instanceof Error ? e.message : '执行失败'
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
.export-actions__diagnosis {
  margin-top: 12px;
}
</style>
