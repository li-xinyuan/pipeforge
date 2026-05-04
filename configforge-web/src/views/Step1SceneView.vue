<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="1" />
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
import { useRouter } from 'vue-router'
import { useWizardStore } from '../stores/wizard'
import StepIndicator from '../components/common/StepIndicator.vue'
import SceneInfoForm from '../components/step1/SceneInfoForm.vue'

const router = useRouter()
const store = useWizardStore()

function onNext() {
  if (store.canProceed) {
    store.nextStep()
    router.push('/step/2')
  }
}
</script>
