<template>
  <div v-if="visible" class="bg-gradient-to-br from-sky-50 to-blue-50 dark:from-sky-900/30 dark:to-blue-900/30 border border-sky-200 dark:border-sky-800 rounded-lg p-4 mt-4">
    <div class="flex items-center gap-2 text-sm font-semibold text-sky-700 dark:text-sky-300 mb-3">🤖 AI 建议</div>
    <div class="text-sm text-slate-900 dark:text-slate-100 mb-3 leading-relaxed" v-html="sanitizedContent" />
    <div class="flex gap-2">
      <button class="inline-flex items-center justify-center gap-2 px-2.5 py-1 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700" @click="$emit('accept')">采纳</button>
      <button class="inline-flex items-center justify-center gap-2 px-2.5 py-1 text-xs font-medium bg-[var(--color-surface)] text-[var(--color-text-secondary)] border border-[var(--color-border-light)] dark:border-[var(--color-border)] rounded-md hover:bg-[var(--color-surface-hover)]" @click="$emit('regenerate')">重新生成</button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'

const props = defineProps<{ visible: boolean; content: string }>()
defineEmits<{ accept: []; regenerate: [] }>()

const sanitizedContent = computed(() => DOMPurify.sanitize(props.content))
</script>
