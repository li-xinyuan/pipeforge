<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="2" />

    <div class="mb-6">
      <h2 class="text-lg font-semibold text-slate-900 mb-1">数据源配置</h2>
      <p class="text-sm text-slate-500">配置数据输入源，选择 Excel 文件并指定工作表和列映射。</p>
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
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import StepIndicator from '../components/common/StepIndicator.vue'
import AiSuggestPanel from '../components/common/AiSuggestPanel.vue'
import InputSourceList from '../components/step2/InputSourceList.vue'

const router = useRouter()
const store = useWizardStore()

function onNext() {
  if (store.canProceed) {
    store.nextStep()
    router.push('/step/3')
  }
}

function onRegenerate() {
  // TODO: trigger AI column suggestion regeneration
}
</script>
