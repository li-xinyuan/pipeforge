<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="4" @goto="(s: number) => { store.goToStep(s); router.push(`/step/${s}`) }" />
    <div class="bg-white border border-slate-200 rounded-lg p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-base font-semibold">pipeline.yaml</h2>
        <div class="flex gap-2">
          <button @click="refreshPreview" class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">🔄 刷新预览</button>
          <button class="px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">📋 复制</button>
          <button class="px-2.5 py-1 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700">📥 下载</button>
        </div>
      </div>
      <YamlPreview />
    </div>
    <ExportActions />
    <div class="flex justify-between items-center pt-6 border-t border-slate-100 mt-6">
      <button @click="store.prevStep(); router.push('/step/3')" class="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md">&larr; 上一步</button>
      <router-link to="/" class="inline-flex items-center justify-center gap-2 px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700">✓ 完成</router-link>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import StepIndicator from '../components/common/StepIndicator.vue'
import YamlPreview from '../components/step4/YamlPreview.vue'
import ExportActions from '../components/step4/ExportActions.vue'

const router = useRouter()
const store = useWizardStore()

onMounted(() => { store.currentStep = 4 })

function refreshPreview() { /* trigger re-render */ }
</script>
