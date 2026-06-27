<template>
  <div class="space-y-4">
    <InputSourceCard
      v-for="(input, idx) in store.inputs"
      :key="idx"
      :input="input"
      :index="idx"
      :pulse-upload="pulseCta && input.plugin && !input.fileId"
      @update="(val) => store.updateInput(idx, val)"
      @remove="store.removeInput(idx)"
      @file-ready="(fileId) => emit('file-ready', fileId)"
    />

    <!-- Add area -->
    <template v-if="showAddSelector">
      <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 12px;">选择数据源类型并上传文件，作为管道的输入</p>
      <div class="flex items-center justify-between mb-2 mt-2">
        <span class="text-sm font-semibold text-slate-700 dark:text-slate-200">选择输入源类型</span>
        <NButton text type="error" size="small" @click="showAddSelector = false">取消</NButton>
      </div>
      <div class="grid grid-cols-3 gap-3">
        <div :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-green-900/30', pulseCta && store.inputs.length === 0 ? 'pulse-cta' : '', 'border-green-600 bg-green-50']" @click="addInput('excel')">
          <span class="text-2xl block mb-2">📊</span>
          <span class="text-sm font-semibold">Excel</span>
          <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">.xlsx / .xls</span>
        </div>
        <div :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-blue-900/30', pulseCta && store.inputs.length === 0 ? 'pulse-cta' : '', 'border-blue-600 bg-blue-50']" @click="addInput('csv')">
          <span class="text-2xl block mb-2">🗄</span>
          <span class="text-sm font-semibold">CSV</span>
          <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">.csv / .tsv</span>
        </div>
        <div :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-purple-900/30', pulseCta && store.inputs.length === 0 ? 'pulse-cta' : '', 'border-purple-600 bg-purple-50']" @click="addInput('database')">
          <span class="text-2xl block mb-2">🔌</span>
          <span class="text-sm font-semibold">Database</span>
          <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">SQLite / MySQL / PG</span>
        </div>
        <div :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-amber-900/30', 'border-amber-600 bg-amber-50']" @click="addInput('json')">
          <span class="text-2xl block mb-2">📋</span>
          <span class="text-sm font-semibold">JSON</span>
          <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">.json</span>
        </div>
        <div :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-orange-900/30', 'border-orange-600 bg-orange-50']" @click="addInput('xml')">
          <span class="text-2xl block mb-2">📰</span>
          <span class="text-sm font-semibold">XML</span>
          <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">.xml</span>
        </div>
        <div :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30 dark:bg-cyan-900/30', 'border-cyan-600 bg-cyan-50']" @click="addInput('parquet')">
          <span class="text-2xl block mb-2">📦</span>
          <span class="text-sm font-semibold">Parquet</span>
          <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">.parquet</span>
        </div>
        <div class="text-center opacity-55 border-2 border-dashed border-rose-300 dark:border-rose-700 bg-rose-50/50 dark:bg-rose-900/20 rounded-lg p-3 relative cursor-not-allowed" title="此输入源当前仅支持预览，暂不可执行">
          <NTag class="absolute top-1 right-1" size="tiny" type="warning" :bordered="false">仅预览</NTag>
          <span class="text-2xl block mb-2">🌐</span>
          <span class="text-sm font-semibold">REST API</span>
          <span class="text-xs text-slate-500 dark:text-slate-400 mt-1 block">HTTP 接口</span>
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
      </div>
    </template>

    <NButton
      v-if="!showAddSelector"
      dashed
      block
      :class="{ 'pulse-cta': pulseCta && store.inputs.length === 0 }"
      @click="showAddSelector = true"
    >
      添加输入源
    </NButton>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { NButton, NTag } from 'naive-ui'
import InputSourceCard from './InputSourceCard.vue'
import type { InputSource } from '../../types/wizard'

const store = useWizardStore()
const showAddSelector = ref(store.inputs.length === 0)

defineProps<{ pulseCta?: boolean }>()
const emit = defineEmits<{ 'file-ready': [fileId: string] }>()

watch(() => store.inputs.length, (len) => {
  if (len === 0) showAddSelector.value = true
})

function addInput(plugin: InputSource['plugin'] = 'excel') {
  store.addInput(plugin)
  showAddSelector.value = false
}
</script>
