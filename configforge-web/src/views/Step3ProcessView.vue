<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="3" />

    <div class="mb-6">
      <h2 class="text-lg font-semibold text-slate-900 mb-1">数据转换/处理</h2>
      <p class="text-sm text-slate-500">编写 SQL 对第二步导入的数据源进行处理，例如多表关联、字段计算、数据过滤等。</p>
    </div>

    <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
      <SqlEditorTab />
    </div>

    <div class="flex justify-between items-center pt-6 mt-6">
      <button
        @click="router.push('/step/2')"
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
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import StepIndicator from '../components/common/StepIndicator.vue'
import SqlEditorTab from '../components/step3/SqlEditorTab.vue'

const router = useRouter()
const store = useWizardStore()

onMounted(() => {
  store.currentStep = 3

  // 自动生成默认 SQL，outputTables 由 SqlEditorTab 的 watch 统一推断
  if (!store.processor.sql.trim() && store.inputs.length > 0) {
    const firstTable = store.inputs[0]?.table
    if (firstTable) store.processor.sql = `SELECT * FROM ${firstTable}`
  }
})

function onNext() {
  if (store.canProceed) {
    store.nextStep()
    router.push('/step/4')
  }
}
</script>
