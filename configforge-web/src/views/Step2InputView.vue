<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <NSteps :current="store.currentStep" @update:current="onStepClick">
      <NStep title="场景信息" description="基本信息" />
      <NStep title="数据源配置" description="上传与解析" />
      <NStep title="数据转换/处理" description="SQL 编写" />
      <NStep title="输出定义" description="格式与映射" />
      <NStep title="预览与导出" description="YAML 查看" />
    </NSteps>

    <div class="mb-6 mt-8">
      <h2 class="text-lg font-semibold mb-1">数据源配置</h2>
      <p class="text-sm text-slate-500">点击「添加输入源」选择文件，上传后自动解析工作表和列信息，确认表名和参数键即可。</p>
      <p v-if="store.inputs.length === 0" class="text-xs text-red-500 mt-1">* 至少需要添加一个输入源</p>
      <NTooltip>
        <template #trigger>
          <NButton
            size="small"
            class="mt-2"
            :disabled="suggesting || !hasAnyFile || !aiConfigured"
            :loading="suggesting"
            @click="onRegenerate"
          >{{ suggesting ? '分析中...' : 'AI 分析列' }}</NButton>
        </template>
        {{ aiTooltip }}
      </NTooltip>
    </div>

    <InputSourceList @file-ready="onFileReady" />

    <!-- AI Analysis Modal -->
    <AiColumnAnalysisModal
      :visible="showModal"
      :suggesting="suggesting"
      :inputs="store.inputs"
      :uploaded-files="store.uploadedFiles"
      :analysis="analysis"
      @confirm="onConfirm"
      @regenerate="onRegenerate"
      @close="showModal = false"
    />

    <div class="flex justify-between items-center pt-6 mt-6">
      <NButton text @click="router.push('/step/1')">上一步</NButton>
      <NButton type="primary" :disabled="!store.canProceed" @click="onNext">下一步</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import type { ConfirmedAnalysis } from '../types/wizard'
import { NSteps, NStep, NButton, NTooltip, useMessage } from 'naive-ui'
import InputSourceList from '../components/step2/InputSourceList.vue'
import AiColumnAnalysisModal from '../components/step2/AiColumnAnalysisModal.vue'
import { useAiApi } from '../composables/useWizardApi'

const router = useRouter()
const store = useWizardStore()
const message = useMessage()
const { askSuggestion, suggesting, aiError, getAiSettings } = useAiApi()
const showModal = ref(false)
const analysis = reactive<Record<string, any>>({})
const pageMounted = ref(false)
const aiConfigured = ref(false)
let pageMountedTimer: ReturnType<typeof setTimeout> | null = null
let autoTriggerTimer: ReturnType<typeof setTimeout> | null = null

const hasAnyFile = computed(() => {
  return Object.values(store.uploadedFiles).some(f => f.columns && f.columns.length > 0)
})

const aiTooltip = computed(() => {
  if (!aiConfigured.value) return '请先在 AI 设置中配置 API Key'
  if (!hasAnyFile.value) return '请先上传文件'
  return 'AI 将分析列信息，建议表名和参数键'
})

onMounted(async () => {
  store.currentStep = 2
  const settings = await getAiSettings()
  aiConfigured.value = !!(settings?.enabled && settings?.api_key)
  pageMountedTimer = setTimeout(() => { pageMounted.value = true }, 100)
})

onUnmounted(() => {
  if (pageMountedTimer) clearTimeout(pageMountedTimer)
  if (autoTriggerTimer) clearTimeout(autoTriggerTimer)
})

function onStepClick(step: number) {
  const s = step
  if (s <= store.currentStep) {
    store.goToStep(s); router.push(`/step/${s}`)
  } else if (s === store.currentStep + 1 && store.canProceed(store.currentStep)) {
    store.goToStep(s); router.push(`/step/${s}`)
  }
}

function parseAnalysis(content: string) {
  analysis.rawText = ''
  try {
    const parsed = JSON.parse(content)
    if (parsed.is_json === false && parsed.raw) {
      analysis.rawText = parsed.raw
      analysis.columnTypes = {}
      analysis.joinKeys = []
      analysis.suggestedTableNames = []
      analysis.suggestedParamKeys = []
      return
    }
    analysis.columnTypes = parsed.columnTypes || {}
    analysis.joinKeys = parsed.joinKeys || []
    analysis.suggestedTableNames = parsed.suggestedTableNames || []
    analysis.suggestedParamKeys = parsed.suggestedParamKeys || []
  } catch {
    analysis.rawText = content
    analysis.columnTypes = {}
    analysis.joinKeys = []
    analysis.suggestedTableNames = []
    analysis.suggestedParamKeys = []
  }
}

async function analyzeColumns(fileColumns: Record<string, string[]>, sampleRows: any[]) {
  const content = await askSuggestion('columns', { fileColumns, sampleRows })
  if (content) {
    parseAnalysis(content)
    showModal.value = true
  } else {
    message.warning(aiError.value || 'AI 分析请求失败，请稍后重试')
  }
}

function onConfirm(results: Array<{ sourceIndex: number; confirmed: ConfirmedAnalysis }>) {
  for (const { sourceIndex, confirmed } of results) {
    const input = store.inputs[sourceIndex]
    store.updateInput(sourceIndex, {
      ...input,
      table: confirmed.tableName,
      paramKey: confirmed.paramKeys.join(','),
      confirmedAnalysis: confirmed,
    })
  }
  showModal.value = false
}

function onFileReady(_fileId: string) {
  if (!pageMounted.value) return
  if (autoTriggerTimer) clearTimeout(autoTriggerTimer)
  autoTriggerTimer = setTimeout(() => {
    if (!showModal.value && !suggesting.value && hasAnyFile.value) {
      onRegenerate()
    }
  }, 600)
}

function onNext() {
  if (store.canProceed(store.currentStep)) {
    store.nextStep()
    router.push('/step/3')
  }
}

async function onRegenerate() {
  showModal.value = false

  // Refresh AI config status before attempting the call
  const settings = await getAiSettings()
  aiConfigured.value = !!(settings?.enabled && settings?.api_key)
  if (!aiConfigured.value) {
    message.warning('AI 未配置，请先在设置中启用并填写 API Key')
    return
  }

  const fileColumns: Record<string, string[]> = {}
  const sampleRows: any[] = []
  for (const [id, meta] of Object.entries(store.uploadedFiles)) {
    if (meta.columns) fileColumns[meta.originalName || id] = meta.columns
    if (meta.sampleRows) {
      for (const row of meta.sampleRows) {
        if (sampleRows.length >= 10) break
        sampleRows.push(row)
      }
    }
  }
  analyzeColumns(fileColumns, sampleRows)
}
</script>
