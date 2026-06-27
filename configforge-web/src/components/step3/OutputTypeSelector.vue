<template>
  <div>
    <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 12px;">选择输出格式，配置数据的导出方式</p>
    <div class="grid grid-cols-3 gap-3 mb-5">
      <div
        :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-green-900/30',
                 props.pulseCta ? 'pulse-cta' : '',
                 'border-green-600 bg-green-50']"
        @click="$emit('select', 'excel')"
      >
        <span class="text-2xl block mb-2">📊</span>
        <span class="text-sm font-semibold">Excel</span>
        <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">.xlsx 模板输出</span>
      </div>
      <div
        :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-blue-900/30',
                 props.pulseCta ? 'pulse-cta' : '',
                 'border-blue-600 bg-blue-50']"
        @click="$emit('select', 'csv')"
      >
        <span class="text-2xl block mb-2">🗄</span>
        <span class="text-sm font-semibold">CSV</span>
        <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">.csv / .tsv 导出</span>
      </div>
      <div
        :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-purple-900/30',
                 props.pulseCta ? 'pulse-cta' : '',
                 'border-purple-600 bg-purple-50']"
        @click="$emit('select', 'database')"
      >
        <span class="text-2xl block mb-2">🔌</span>
        <span class="text-sm font-semibold">Database</span>
        <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">MySQL / PostgreSQL</span>
      </div>
      <div class="text-center opacity-55 bg-slate-50 dark:bg-slate-800 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-lg p-3 relative">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.3</NTag>
        <span class="text-2xl block mb-2">📄</span>
        <span class="text-sm font-semibold">PDF</span>
      </div>
      <div class="text-center opacity-55 bg-slate-50 dark:bg-slate-800 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-lg p-3 relative">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.4</NTag>
        <span class="text-2xl block mb-2">🖥</span>
        <span class="text-sm font-semibold">PPT</span>
      </div>
      <div class="text-center opacity-55 bg-slate-50 dark:bg-slate-800 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-lg p-3 relative">
        <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.5</NTag>
        <span class="text-2xl block mb-2">🌐</span>
        <span class="text-sm font-semibold">API</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NTag } from 'naive-ui'

const props = defineProps<{ pulseCta?: boolean }>()
defineEmits<{ select: [plugin: 'excel' | 'csv' | 'database'] }>()
</script>
