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
        <span :class="{ 'pulse-cta': pulseCta && store.inputs.length === 0 }" style="display:inline-block;border-radius:8px;">
          <NCard hoverable class="cursor-pointer text-center border-2 border-green-600 bg-green-50" @click="addInput('excel')">
            <span class="text-2xl block mb-2">📊</span>
            <span class="text-sm font-semibold">Excel</span>
            <span class="text-xs text-slate-500 mt-1 block">.xlsx / .xls</span>
          </NCard>
        </span>
        <span :class="{ 'pulse-cta': pulseCta && store.inputs.length === 0 }" style="display:inline-block;border-radius:8px;">
          <NCard hoverable class="cursor-pointer text-center border-2 border-blue-600 bg-blue-50" @click="addInput('csv')">
            <span class="text-2xl block mb-2">🗄</span>
            <span class="text-sm font-semibold">CSV</span>
            <span class="text-xs text-slate-500 mt-1 block">.csv / .tsv</span>
          </NCard>
        </span>
        <span :class="{ 'pulse-cta': pulseCta && store.inputs.length === 0 }" style="display:inline-block;border-radius:8px;">
          <NCard hoverable class="cursor-pointer text-center border-2 border-purple-600 bg-purple-50" @click="addInput('database')">
            <span class="text-2xl block mb-2">🔌</span>
            <span class="text-sm font-semibold">Database</span>
            <span class="text-xs text-slate-500 mt-1 block">SQLite / MySQL / PG</span>
          </NCard>
        </span>
        <NCard class="text-center opacity-55 bg-slate-50 relative" size="small">
          <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.3</NTag>
          <span class="text-2xl block mb-2">📄</span>
          <span class="text-sm font-semibold">PDF</span>
        </NCard>
        <NCard class="text-center opacity-55 bg-slate-50 relative" size="small">
          <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.4</NTag>
          <span class="text-2xl block mb-2">🖥</span>
          <span class="text-sm font-semibold">PPT</span>
        </NCard>
        <NCard class="text-center opacity-55 bg-slate-50 relative" size="small">
          <NTag class="absolute top-1 right-1" size="tiny" :bordered="false">v0.5</NTag>
          <span class="text-2xl block mb-2">🌐</span>
          <span class="text-sm font-semibold">API</span>
        </NCard>
      </div>
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
import { ref } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import { NCard, NButton, NTag } from 'naive-ui'
import InputSourceCard from './InputSourceCard.vue'

const store = useWizardStore()
const showAddSelector = ref(false)

defineProps<{ pulseCta?: boolean }>()
const emit = defineEmits<{ 'file-ready': [fileId: string] }>()

function addInput(plugin: 'excel' | 'csv' | 'database' = 'excel') {
  store.addInput(plugin)
  showAddSelector.value = false
}
</script>
