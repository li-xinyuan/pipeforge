<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="3" />

    <div class="bg-white border border-slate-200 rounded-lg shadow-sm">
      <!-- Tab bar -->
      <div class="flex border-b border-slate-200">
        <button
          @click="activeTab = 'processor'"
          class="flex-1 px-4 py-3 text-sm font-medium text-center border-b-2 transition-colors"
          :class="activeTab === 'processor' ? 'border-blue-600 text-blue-600 bg-blue-50/50' : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'"
        >SQL 处理</button>
        <button
          @click="activeTab = 'output'"
          class="flex-1 px-4 py-3 text-sm font-medium text-center border-b-2 transition-colors"
          :class="activeTab === 'output' ? 'border-blue-600 text-blue-600 bg-blue-50/50' : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'"
        >输出配置</button>
      </div>

      <!-- Tab content -->
      <div class="p-6">
        <SqlEditorTab v-if="activeTab === 'processor'" />
        <OutputConfigTab v-if="activeTab === 'output'" />
      </div>
    </div>

    <div class="flex justify-between items-center pt-6 mt-6">
      <button
        @click="onPrev"
        class="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md"
      >上一步</button>
      <button
        @click="onNext"
        :disabled="!store.canProceed"
        class="inline-flex items-center justify-center gap-2 px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >下一步 &rarr;</button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import StepIndicator from '../components/common/StepIndicator.vue'
import SqlEditorTab from '../components/step3/SqlEditorTab.vue'
import OutputConfigTab from '../components/step3/OutputConfigTab.vue'

const router = useRouter()
const store = useWizardStore()
const activeTab = ref<'processor' | 'output'>('processor')

onMounted(() => { store.currentStep = 3 })

function onPrev() {
  router.push('/step/2')
}

function onNext() {
  if (store.canProceed) {
    store.nextStep()
    router.push('/step/4')
  }
}
</script>
