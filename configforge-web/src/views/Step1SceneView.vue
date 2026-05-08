<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="1" />

    <div class="mb-6">
      <h2 class="text-lg font-semibold text-slate-900 mb-1">场景信息</h2>
      <p class="text-sm text-slate-500">填写场景的基本信息，名称用于标识流水线配置，版本和描述便于后续管理。</p>
    </div>

    <SceneInfoForm />
    <div class="flex justify-between items-center pt-6 border-t border-slate-100 mt-6">
      <router-link
        to="/"
        class="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md"
      >取消</router-link>
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
import SceneInfoForm from '../components/step1/SceneInfoForm.vue'

const router = useRouter()
const store = useWizardStore()

onMounted(() => { store.currentStep = 1 })

function onNext() {
  if (store.canProceed) {
    store.nextStep()
    router.push('/step/2')
  }
}
</script>
