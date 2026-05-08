<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="4" />

    <div class="mb-6">
      <h2 class="text-lg font-semibold text-slate-900 mb-1">输出定义</h2>
      <p class="text-sm text-slate-500">上传 Excel 模板文件并定义输出列映射，模板首行列名会自动填充，同名列自动匹配数据源。</p>
    </div>

    <div class="bg-white border border-slate-200 rounded-lg shadow-sm p-6">
      <OutputConfigTab />
    </div>

    <div class="flex justify-between items-center pt-6 mt-6">
      <button
        @click="router.push('/step/3')"
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
import OutputConfigTab from '../components/step3/OutputConfigTab.vue'

const router = useRouter()
const store = useWizardStore()

onMounted(() => { store.currentStep = 4 })

function onNext() {
  if (store.canProceed) {
    store.nextStep()
    router.push('/step/5')
  }
}
</script>
