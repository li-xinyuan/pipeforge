<template>
  <div v-if="message" class="flex items-start gap-2 px-4 py-3 rounded-md text-sm"
       :class="level === 'warning' ? 'bg-amber-50 border border-amber-200 text-amber-800' : level === 'error' ? 'bg-red-50 border border-red-200 text-red-800' : 'bg-red-600 text-white'">
    <span class="flex-shrink-0 mt-0.5">{{ level === 'warning' ? '⚠️' : '✕' }}</span>
    <span>{{ message }}</span>
  </div>
</template>
<script setup lang="ts">
defineProps<{ message: string | null; level?: 'warning' | 'error' | 'fatal' }>()
</script>
