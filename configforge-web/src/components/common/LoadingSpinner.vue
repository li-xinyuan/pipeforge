<template>
  <div class="flex flex-col items-center justify-center py-8 gap-3">
    <div class="w-8 h-8 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
    <span v-if="label" class="text-sm text-slate-500">{{ label }}</span>
  </div>
</template>
<script setup lang="ts">
defineProps<{ label?: string }>()
</script>
