<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <StepIndicator :current-step="4" />
    <div class="py-8 text-center text-slate-500 text-sm">
      预览与导出（建设中）
    </div>
    <div class="flex justify-between items-center pt-6 border-t border-slate-100 mt-6">
      <router-link
        to="/step/3"
        class="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md"
      >上一步</router-link>
      <router-link
        to="/"
        class="inline-flex items-center justify-center gap-2 px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
      >完成</router-link>
    </div>
  </div>
</template>
<script setup lang="ts">
import StepIndicator from '../components/common/StepIndicator.vue'
</script>
