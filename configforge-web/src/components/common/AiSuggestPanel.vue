<template>
  <div v-if="visible" class="bg-gradient-to-br from-sky-50 to-blue-50 border border-sky-200 rounded-lg p-4 mt-4">
    <div class="flex items-center gap-2 text-sm font-semibold text-sky-700 mb-3">🤖 AI 建议</div>
    <div class="text-sm text-slate-900 mb-3 leading-relaxed" v-html="content"></div>
    <div class="flex gap-2">
      <button @click="$emit('accept')" class="inline-flex items-center justify-center gap-2 px-2.5 py-1 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700">采纳</button>
      <button @click="$emit('regenerate')" class="inline-flex items-center justify-center gap-2 px-2.5 py-1 text-xs font-medium bg-white text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">重新生成</button>
    </div>
  </div>
</template>
<script setup lang="ts">
defineProps<{ visible: boolean; content: string }>()
defineEmits<{ accept: []; regenerate: [] }>()
</script>
