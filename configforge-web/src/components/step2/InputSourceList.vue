<template>
  <div class="space-y-4">
    <InputSourceCard
      v-for="(input, idx) in store.inputs"
      :key="idx"
      :input="input"
      :index="idx"
      @update="(val) => store.updateInput(idx, val)"
      @remove="store.removeInput(idx)"
    />

    <!-- Add area -->
    <template v-if="showAddSelector">
      <div class="grid grid-cols-3 gap-2 mt-2">
        <button
          @click="addInput('excel')"
          class="flex items-center gap-2 px-3 py-2 text-sm font-medium border border-blue-300 rounded-md bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
          Excel
        </button>
        <span class="flex items-center gap-2 px-3 py-2 text-sm font-medium border border-slate-100 rounded-md bg-slate-50 text-slate-400 cursor-not-allowed">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7M4 7c0-2 1-3 3-3h10c2 0 3 1 3 3M4 7h16" /></svg>
          CSV
        </span>
        <span class="flex items-center gap-2 px-3 py-2 text-sm font-medium border border-slate-100 rounded-md bg-slate-50 text-slate-400 cursor-not-allowed">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" /></svg>
          数据库
        </span>
        <span class="flex items-center gap-2 px-3 py-2 text-sm font-medium border border-slate-100 rounded-md bg-slate-50 text-slate-400 cursor-not-allowed">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
          PDF
        </span>
        <span class="flex items-center gap-2 px-3 py-2 text-sm font-medium border border-slate-100 rounded-md bg-slate-50 text-slate-400 cursor-not-allowed">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          PPT
        </span>
        <span class="flex items-center gap-2 px-3 py-2 text-sm font-medium border border-slate-100 rounded-md bg-slate-50 text-slate-400 cursor-not-allowed">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          API
        </span>
      </div>
    </template>

    <button
      v-if="!showAddSelector"
      @click="showAddSelector = true"
      class="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-slate-200 rounded-lg text-sm text-slate-500 hover:border-blue-300 hover:text-blue-600 transition-colors"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
      添加输入源
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useWizardStore } from '../../stores/wizard'
import type { InputSource } from '../../types/wizard'
import InputSourceCard from './InputSourceCard.vue'

const store = useWizardStore()
const showAddSelector = ref(false)

function addInput(plugin: string) {
  const input: InputSource = {
    name: '', plugin: plugin as 'excel', table: '', paramKey: '', fileId: '',
    config: { type: 'excel', sheet: '' }
  }
  store.addInput(input)
  showAddSelector.value = false
}
</script>
