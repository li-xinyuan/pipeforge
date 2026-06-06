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
      <div class="flex items-center justify-between mb-2 mt-2">
        <span class="text-sm font-semibold text-slate-700">选择输入源类型</span>
        <NButton text type="error" size="small" @click="showAddSelector = false">取消</NButton>
      </div>
      <div class="grid grid-cols-3 gap-3">
        <div :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30', pulseCta && store.inputs.length === 0 ? 'pulse-cta' : '', 'border-green-600 bg-green-50']" @click="addInput('excel')">
          <span class="text-2xl block mb-2">📊</span>
          <span class="text-sm font-semibold">Excel</span>
          <span class="text-xs text-slate-500 mt-1 block">.xlsx / .xls</span>
        </div>
        <div :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30', pulseCta && store.inputs.length === 0 ? 'pulse-cta' : '', 'border-blue-600 bg-blue-50']" @click="addInput('csv')">
          <span class="text-2xl block mb-2">🗄</span>
          <span class="text-sm font-semibold">CSV</span>
          <span class="text-xs text-slate-500 mt-1 block">.csv / .tsv</span>
        </div>
        <div :class="['cursor-pointer text-center border-2 rounded-lg p-3 transition-colors hover:border-teal-400 hover:bg-teal-50/30', pulseCta && store.inputs.length === 0 ? 'pulse-cta' : '', 'border-purple-600 bg-purple-50']" @click="addInput('database')">
          <span class="text-2xl block mb-2">🔌</span>
          <span class="text-sm font-semibold">Database</span>
          <span class="text-xs text-slate-500 mt-1 block">SQLite / MySQL / PG</span>
        </div>
        <div class="text-center opacity-55 bg-slate-50 border-2 border-dashed border-slate-200 rounded-lg p-3 relative">
          <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.3</NTag>
          <span class="text-2xl block mb-2">📄</span>
          <span class="text-sm font-semibold">PDF</span>
        </div>
        <div class="text-center opacity-55 bg-slate-50 border-2 border-dashed border-slate-200 rounded-lg p-3 relative">
          <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.4</NTag>
          <span class="text-2xl block mb-2">🖥</span>
          <span class="text-sm font-semibold">PPT</span>
        </div>
        <div class="text-center opacity-55 bg-slate-50 border-2 border-dashed border-slate-200 rounded-lg p-3 relative">
          <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.5</NTag>
          <span class="text-2xl block mb-2">🌐</span>
          <span class="text-sm font-semibold">API</span>
        </div>
      </div>
      <p v-if="store.inputs.length === 0" class="text-xs text-slate-400 mt-3 text-center">选择类型后开始配置输入源</p>
    </template>

    <NButton
      v-if="!showAddSelector"
      dashed
      block
      :class="{ 'pulse-cta': pulseCta && store.inputs.length === 0 }"
      @click="showAddSelector = true"
    >添加输入源</NButton>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { NButton, NTag } from 'naive-ui'
import InputSourceCard from './InputSourceCard.vue'

const store = useWizardStore()
const showAddSelector = ref(store.inputs.length === 0)

defineProps<{ pulseCta?: boolean }>()
const emit = defineEmits<{ 'file-ready': [fileId: string] }>()

watch(() => store.inputs.length, (len) => {
  if (len === 0) showAddSelector.value = true
})

function addInput(plugin: 'excel' | 'csv' | 'database' = 'excel') {
  store.addInput(plugin)
  showAddSelector.value = false
}
</script>
