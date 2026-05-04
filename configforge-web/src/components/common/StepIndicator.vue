<template>
  <div class="mb-6">
    <div class="flex items-center justify-between">
      <div
        v-for="step in 4"
        :key="step"
        class="flex items-center"
      >
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
          :class="step <= currentStep ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'"
        >
          {{ step }}
        </div>
        <div
          v-if="step < 4"
          class="w-12 h-0.5 mx-1"
          :class="step < currentStep ? 'bg-blue-600' : 'bg-slate-200'"
        ></div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
defineProps<{
  currentStep: number
}>()
</script>
