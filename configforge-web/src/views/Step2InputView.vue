<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="2" />

    <div class="mb-6">
      <h2 class="text-lg font-semibold text-slate-900 mb-1">数据源配置</h2>
      <p class="text-sm text-slate-500">点击「添加输入源」选择 Excel 文件，上传后自动解析工作表和列信息，确认表名和参数键即可。</p>
      <button @click="onRegenerate" class="mt-2 px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">🤖 AI 分析列</button>
    </div>

    <InputSourceList />

    <AiSuggestPanel
      :visible="!!store.aiSuggestions['columns']"
      :content="store.aiSuggestions['columns']?.content || ''"
      @accept="store.acceptSuggestion('columns')"
      @regenerate="onRegenerate"
    />

    <div class="flex justify-between items-center pt-6 border-t border-slate-100 mt-6">
      <router-link
        to="/step/1"
        class="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md"
      >上一步</router-link>
      <button
        @click="onNext"
        :disabled="!store.canProceed"
        class="inline-flex items-center justify-center gap-2 px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >下一步 &rarr;</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import StepIndicator from '../components/common/StepIndicator.vue'
import AiSuggestPanel from '../components/common/AiSuggestPanel.vue'
import InputSourceList from '../components/step2/InputSourceList.vue'
import { useAiApi } from '../composables/useWizardApi'

const router = useRouter()
const store = useWizardStore()
const { askSuggestion } = useAiApi()

onMounted(() => { store.currentStep = 2 })

async function analyzeColumns(fileColumns: Record<string, string[]>, sampleRows: any[]) {
  const content = await askSuggestion('columns', { fileColumns, sampleRows })
  if (content) {
    store.setSuggestion('columns', { category: 'columns', status: 'pending', content, timestamp: Date.now() })
  }
}

function onNext() {
  if (store.canProceed) {
    store.nextStep()
    router.push('/step/3')
  }
}

function onRegenerate() {
  const fileColumns: Record<string, string[]> = {}
  const sampleRows: any[] = []
  for (const [id, meta] of Object.entries(store.uploadedFiles)) {
    if (meta.columns) fileColumns[meta.originalName || id] = meta.columns
    if (meta.sampleRows) sampleRows.push(...meta.sampleRows)
  }
  analyzeColumns(fileColumns, sampleRows)
}
</script>
